from openerp.osv import osv, fields
from datetime import date
import base64
#import urllib
import time 
import datetime
import csv
import logging
import urllib2
import simplejson
#from dinceljournal import dincelaccount_journal
import subprocess
from openerp import tools
from dincel_journal import dincelaccount_journal
from openerp.tools.translate import _
from openerp.exceptions import except_orm, Warning, RedirectWarning
from time import gmtime, strftime
from subprocess import Popen, PIPE, STDOUT
import openerp.addons.decimal_precision as dp
from openerp import api#, tools
from openerp import SUPERUSER_ID

_logger = logging.getLogger(__name__)
'''
TYPE2DATES = {
	'tba': 'TBA',
	'na': 'NA',
	'dt': 'Date',
}'''

class dincelaccount_mail_thread(osv.AbstractModel):
	_inherit="mail.thread"
	@api.cr_uid_ids_context
	def message_post_dcs(self, cr, uid, thread_id, body='', subject=None, type='notification',
					 subtype=None, parent_id=False, attachments=None, context=None,
					 content_subtype='html', **kwargs):
		""" Post a new message in an existing thread, returning the new
			mail.message ID.

			:param int thread_id: thread ID to post into, or list with one ID;
				if False/0, mail.message model will also be set as False
			:param str body: body of the message, usually raw HTML that will
				be sanitized
			:param str type: see mail_message.type field
			:param str content_subtype:: if plaintext: convert body into html
			:param int parent_id: handle reply to a previous message by adding the
				parent partners to the message in case of private discussion
			:param tuple(str,str) attachments or list id: list of attachment tuples in the form
				``(name,content)``, where content is NOT base64 encoded

			Extra keyword arguments will be used as default column values for the
			new mail.message record. Special cases:
				- attachment_ids: supposed not attached to any document; attach them
					to the related document. Should only be set by Chatter.
			:return int: ID of newly created mail.message
		"""
		if context is None:
			context = {}
		if attachments is None:
			attachments = {}
		mail_message = self.pool.get('mail.message')
		#ir_attachment = self.pool.get('ir.attachment')
		'''
		assert (not thread_id) or \
				isinstance(thread_id, (int, long)) or \
				(isinstance(thread_id, (list, tuple)) and len(thread_id) == 1), \
				"Invalid thread_id; should be 0, False, an ID or a list with one ID"
		if isinstance(thread_id, (list, tuple)):
			thread_id = thread_id[0]
		'''
		# if we're processing a message directly coming from the gateway, the destination model was
		# set in the context.
		#_logger.error("message_post_dcsmessage_post_msg_idmsg_id_contextcontextcontext ["+str(context)+"]")
		model = context.get('active_model')#:False
		thread_id= context.get('active_id')
		'''if thread_id:
			model = context.get('thread_model', False) if self._name == 'mail.thread' else self._name
			if model and model != self._name and hasattr(self.pool[model], 'message_post'):
				del context['thread_model']
				return self.pool[model].message_post(cr, uid, thread_id, body=body, subject=subject, type=type, subtype=subtype, parent_id=parent_id, attachments=attachments, context=context, content_subtype=content_subtype, **kwargs)
		'''
		#0: Find the message's author, because we need it for private discussion
		author_id = kwargs.get('author_id')
		if author_id is None:  # keep False values
			author_id = self.pool.get('mail.message')._get_default_author(cr, uid, context=context)

		# 1: Handle content subtype: if plaintext, converto into HTML
		if content_subtype == 'plaintext':
			body = tools.plaintext2html(body)

		# 2: Private message: add recipients (recipients and author of parent message) - current author
		#   + legacy-code management (! we manage only 4 and 6 commands)
		partner_ids = set()
		kwargs_partner_ids = kwargs.pop('partner_ids', [])
		for partner_id in kwargs_partner_ids:
			if isinstance(partner_id, (list, tuple)) and partner_id[0] == 4 and len(partner_id) == 2:
				partner_ids.add(partner_id[1])
			if isinstance(partner_id, (list, tuple)) and partner_id[0] == 6 and len(partner_id) == 3:
				partner_ids |= set(partner_id[2])
			elif isinstance(partner_id, (int, long)):
				partner_ids.add(partner_id)
			else:
				pass  # we do not manage anything else
		if parent_id and not model:
			parent_message = mail_message.browse(cr, uid, parent_id, context=context)
			private_followers = set([partner.id for partner in parent_message.partner_ids])
			if parent_message.author_id:
				private_followers.add(parent_message.author_id.id)
			private_followers -= set([author_id])
			partner_ids |= private_followers

		# 3. Attachments
		#   - HACK TDE FIXME: Chatter: attachments linked to the document (not done JS-side), load the message
		attachment_ids = self._message_preprocess_attachments(cr, uid, attachments, kwargs.pop('attachment_ids', []), model, thread_id, context)

		# 4: mail.message.subtype
		subtype_id = False #-- Do not send to followers automatically....
		#if subtype:
		#	if '.' not in subtype:
		#		subtype = 'mail.%s' % subtype
		#	subtype_id = self.pool.get('ir.model.data').xmlid_to_res_id(cr, uid, subtype)

		# automatically subscribe recipients if asked to
		if context.get('mail_post_autofollow') and thread_id and partner_ids:
			partner_to_subscribe = partner_ids
			if context.get('mail_post_autofollow_partner_ids'):
				partner_to_subscribe = filter(lambda item: item in context.get('mail_post_autofollow_partner_ids'), partner_ids)
			self.message_subscribe(cr, uid, [thread_id], list(partner_to_subscribe), context=context)

		# _mail_flat_thread: automatically set free messages to the first posted message
		if self._mail_flat_thread and model and not parent_id and thread_id:
			message_ids = mail_message.search(cr, uid, ['&', ('res_id', '=', thread_id), ('model', '=', model), ('type', '=', 'email')], context=context, order="id ASC", limit=1)
			if not message_ids:
				message_ids = message_ids = mail_message.search(cr, uid, ['&', ('res_id', '=', thread_id), ('model', '=', model)], context=context, order="id ASC", limit=1)
			parent_id = message_ids and message_ids[0] or False
		# we want to set a parent: force to set the parent_id to the oldest ancestor, to avoid having more than 1 level of thread
		elif parent_id:
			message_ids = mail_message.search(cr, SUPERUSER_ID, [('id', '=', parent_id), ('parent_id', '!=', False)], context=context)
			# avoid loops when finding ancestors
			processed_list = []
			if message_ids:
				message = mail_message.browse(cr, SUPERUSER_ID, message_ids[0], context=context)
				while (message.parent_id and message.parent_id.id not in processed_list):
					processed_list.append(message.parent_id.id)
					message = message.parent_id
				parent_id = message.id

		values = kwargs
		values.update({
			'author_id': author_id,
			#'model': model,
			#'res_id': model and thread_id or False,
			'body': body,
			'subject': subject or False,
			'type': type,
			'parent_id': parent_id,
			'attachment_ids': attachment_ids,
			'subtype_id': subtype_id,
			'partner_ids': [(4, pid) for pid in partner_ids],
		})
		if model:
			values.update({'model': model,})
		if model and thread_id:
			values.update({'res_id': thread_id,})
				
		# Avoid warnings about non-existing fields
		for x in ('from', 'to', 'cc'):
			values.pop(x, None)
		
		#_logger.error("message_post_dcsmessage_post_dcsmessage_post_dcs ["+str(values)+"]")
		# Post the message
		msg_id = mail_message.create(cr, uid, values, context=context) #this is where email msg record created and then email sent....
		#_logger.error("message_post_dcsmessage_post_msg_idmsg_id ["+str(msg_id)+"]")
		
		# Post-process: subscribe author, update message_last_post
		if model and model != 'mail.thread' and thread_id and subtype_id:
			# done with SUPERUSER_ID, because on some models users can post only with read access, not necessarily write access
			self.write(cr, SUPERUSER_ID, [thread_id], {'message_last_post': fields.datetime.now()}, context=context)
		message = mail_message.browse(cr, uid, msg_id, context=context)
		if message.author_id and model and thread_id and type != 'notification' and not context.get('mail_create_nosubscribe'):
			self.message_subscribe(cr, uid, [thread_id], [message.author_id.id], context=context)
		return msg_id 
		#return True
	
class dincelaccount_mail(osv.TransientModel):
	_inherit="mail.compose.message"
	_columns = {
		'x_qty':fields.float("Qty test"),
	}
	
	def on_change_qty(self, cr, uid, ids, _qty, context=None):
		if context.get('domain_contact_ids'):
			partner_ids=[]
			#wizard = self.pool.get('mail.compose.message').browse(cr, uid, ids[0], context=context)
			for _id in context.get('domain_contact_ids'):
				partner_ids+=_id
				#partner_ids.append(_id)
			'''	
			fol_obj = self.pool.get('mail.followers')
			fol_ids = fol_obj.search(cr, uid, [
				('res_id', '=', context.get('default_res_id')),
				('res_model', '=', context.get('default_model')),
			], context=context)
			for fol in fol_obj.browse(cr, uid, fol_ids, context=context):	
				#partner_ids+=[fol.partner_id]
				#_logger.error("fol.partner_idfol.partner_idfol.partner_id ["+str(fol.partner_id.id)+"]")
				partner_ids.append(fol.partner_id.id)'''
				
			domain  = {'partner_ids': [('id','in', (partner_ids))]}
			#=domain 
			#_logger.error("default_contact_idsdefault_contact_idsdomain ["+str(domain)+"]")
			return {'domain': domain}	
		#if context and context.get('active_ids'):
	def _get_init_qty(self, cr, uid, context=None):
		return 1
	_defaults = {
		'x_qty': _get_init_qty,
		}
		
	def get_record_data_dcs(self, cr, uid, values, context=None):
		""" Returns a defaults-like dict with initial values for the composition
		wizard when sending an email related a previous email (parent_id) or
		a document (model, res_id). This is based on previously computed default
		values. """
		if context is None:
			context = {}
		result, subject = {}, False
		if values.get('parent_id'):
			parent = self.pool.get('mail.message').browse(cr, uid, values.get('parent_id'), context=context)
			result['record_name'] = parent.record_name,
			subject = tools.ustr(parent.subject or parent.record_name or '')
			if not values.get('model'):
				result['model'] = parent.model
			if not values.get('res_id'):
				result['res_id'] = parent.res_id
			partner_ids = values.get('partner_ids', list()) + [partner.id for partner in parent.partner_ids]
			if context.get('is_private') and parent.author_id:  # check message is private then add author also in partner list.
				partner_ids += [parent.author_id.id]
			result['partner_ids'] = partner_ids
		elif values.get('model') and values.get('res_id'):
			doc_name_get = self.pool[values.get('model')].name_get(cr, uid, [values.get('res_id')], context=context)
			result['record_name'] = doc_name_get and doc_name_get[0][1] or ''
			subject = tools.ustr(result['record_name'])

		re_prefix = _('Re:')
		
		if context.get('default_contact_sel_ids'):
			partner_ids=[]
			for _id in context.get('default_contact_sel_ids'):
				#partner_ids.append(_id)#
				partner_ids+=_id
				#_logger.error("generate_aba_default_contact_idsdefault_contact_ids_id_id ["+str(_id)+"]")
			result['partner_ids'] = partner_ids
			#_logger.error("generate_aba_default_contact_idsdefault_contact111_ids111 ["+str(partner_ids)+"]")
		if context.get('default_subject'):
			subject=context.get('default_subject')
		else:
			if subject and not (subject.startswith('Re:') or subject.startswith(re_prefix)):
				subject = "%s %s" % (re_prefix, subject)
		if subject:
			result['subject'] =  "" + subject

		return result
		
	def default_get(self, cr, uid, fields, context=None):
		#res = super(dincelaccount_mail, self).default_get(cr, uid, ids, vals, context=context)
		if context is None:
			context = {}
		result = super(dincelaccount_mail, self).default_get(cr, uid, fields, context=context)

		# v6.1 compatibility mode
		result['composition_mode'] = result.get('composition_mode', context.get('mail.compose.message.mode', 'comment'))
		result['model'] = result.get('model', context.get('active_model'))
		result['res_id'] = result.get('res_id', context.get('active_id'))
		result['parent_id'] = result.get('parent_id', context.get('message_id'))

		if not result['model'] or not self.pool.get(result['model']) or not hasattr(self.pool[result['model']], 'message_post'):
			result['no_auto_thread'] = True

		# default values according to composition mode - NOTE: reply is deprecated, fall back on comment
		if result['composition_mode'] == 'reply':
			result['composition_mode'] = 'comment'
		vals = {}
		if 'active_domain' in context:  # not context.get() because we want to keep global [] domains
			vals['use_active_domain'] = True
			vals['active_domain'] = '%s' % context.get('active_domain')
		if result['composition_mode'] == 'comment':
			vals.update(self.get_record_data_dcs(cr, uid, result, context=context))

		for field in vals:
			if field in fields:
				result[field] = vals[field]

		# TDE HACK: as mailboxes used default_model='res.users' and default_res_id=uid
		# (because of lack of an accessible pid), creating a message on its own
		# profile may crash (res_users does not allow writing on it)
		# Posting on its own profile works (res_users redirect to res_partner)
		# but when creating the mail.message to create the mail.compose.message
		# access rights issues may rise
		# We therefore directly change the model and res_id
		if result['model'] == 'res.users' and result['res_id'] == uid:
			result['model'] = 'res.partner'
			result['res_id'] = self.pool.get('res.users').browse(cr, uid, uid).partner_id.id
		
		
			
		if fields is not None:
			[result.pop(field, None) for field in result.keys() if field not in fields]
		return result
		
	def _update_flag_model(self, cr, uid, values, context=None):
		if context.get('default_model') == 'sale.order' and context.get('mark_as_sent'):
			if context.get('default_inv_ids'):
				for _id in context.get('default_inv_ids'):
					_obj = self.pool.get('account.invoice').browse(cr, uid, _id, context=context)
					if not _obj.sent:
						self.pool.get('account.invoice').write(cr, uid, _id, {'sent': True})

			if context.get('default_res_id'):
				_id  = context.get('default_res_id')
				_obj = self.pool.get('sale.order').browse(cr, uid, _id, context=context)
				if not _obj.x_sent:
					self.pool.get('sale.order').write(cr, uid, _id, {'x_sent': True, 'state': 'sent'}) 
				
	def send_mail_dcs(self, cr, uid, ids, context=None):
		""" Process the wizard content and proceed with sending the related
			email(s), rendering any template patterns on the fly if needed. """
		context = dict(context or {})
		context.pop('default_email_to', None)
		context.pop('default_partner_ids', None)
		msg_id = False
		for wizard in self.browse(cr, uid, ids, context=context):
			mass_mode = wizard.composition_mode in ('mass_mail', 'mass_post')
			active_model_pool = self.pool[wizard.model if wizard.model else 'mail.thread']
			if not hasattr(active_model_pool, 'message_post'):
				context['thread_model'] = wizard.model
				active_model_pool = self.pool['mail.thread']
			active_model_pool = self.pool['mail.thread']
			
			# wizard works in batch mode: [res_id] or active_ids or active_domain
			if mass_mode and wizard.use_active_domain and wizard.model:
				res_ids = self.pool[wizard.model].search(cr, uid, eval(wizard.active_domain), context=context)
			elif mass_mode and wizard.model and context.get('active_ids'):
				res_ids = context['active_ids']
			else:
				res_ids = [wizard.res_id]

			batch_size = int(self.pool['ir.config_parameter'].get_param(cr, SUPERUSER_ID, 'mail.batch_size')) or self._batch_size

			sliced_res_ids = [res_ids[i:i + batch_size] for i in range(0, len(res_ids), batch_size)]
			for res_ids in sliced_res_ids:
				all_mail_values = self.get_mail_values(cr, uid, wizard, res_ids, context=context)
				for res_id, mail_values in all_mail_values.iteritems():
					if wizard.composition_mode == 'mass_mail':
						self.pool['mail.mail'].create(cr, uid, mail_values, context=context)
					else:
						subtype = 'mail.mt_comment'
						if wizard.is_log or (wizard.composition_mode == 'mass_post' and not wizard.notify):  # log a note: subtype is False
							subtype = False
						if wizard.composition_mode == 'mass_post':
							context = dict(context,
										   mail_notify_force_send=False,  # do not send emails directly but use the queue instead
										   mail_create_nosubscribe=True)  # add context key to avoid subscribing the author
						
						msg_id = active_model_pool.message_post_dcs(cr, uid, [res_id], type='comment', subtype=subtype, context=context, **mail_values)
		if msg_id:
			self._update_flag_model(cr, uid, ids, context=context)	
			
		return {'type': 'ir.actions.act_window_close'}