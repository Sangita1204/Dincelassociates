import time
from openerp import tools
from openerp.osv import fields, osv
from openerp.tools.translate import _
import logging
_logger = logging.getLogger(__name__)

class saleorder_approve_request(osv.osv_memory):
	_name = "saleorder.approve.request"
	_columns = {
		'date': fields.datetime('Date'),
		'order_id':fields.many2one('sale.order', 'Sale Order'),
		'invoice_id':fields.many2one('account.invoice', 'Invoice'),
		'request_id':fields.many2one('dincelsale.order.approve', 'Request'),
		'request_uid': fields.many2one('res.users', 'Requested By'),
		'partner_ids': fields.many2many('res.partner', string='Notify to'),
		'user_id': fields.many2one('res.users', 'Approved By'),
		'request_text': fields.char('Request Reason'),	
		'subject': fields.char('Subject'),	
		'approve_flag': fields.boolean('Flag'),	
		'approve_pending': fields.boolean('Pending Approval'),	
		'comments': fields.text('Comments'),	
		'notes': fields.text('Notes'),
		'qty':fields.float("Qty test"),
		'type':fields.selection([
			('cancel','Cancellation'),
			('discount','Discount'),
			('credit','Credit/Others'),
			('refund','Refund'),
			('mrp','MRP'),
			], 'Type'),
		'subtype':fields.selection([ #as in dcs open /reject/ approve
			('','None'),
			('order','Order'),
			('invoice','Invoice'),
			], 'Sub Type'),		
		'state':fields.selection([ #as in dcs open /reject/ approve
			('approve','Approved'),
			('reject','Rejected'),
			], 'Status'),		
	}
	
	def _get_init_qty(self, cr, uid, context=None):
		return 1
	_defaults = {
		'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
		'subtype': 'order',
		'qty': _get_init_qty,
		}
		
	def on_change_qty(self, cr, uid, ids,qty,request_id,type,subtype,approve_flag, context=None):
		result={}
		lids4 = []
		if context is None:
			context = {}
		if type in['credit','discount']:
			str1="The order requires approval to proceed due to discount applied. Enter your reason to submit a request and continue."	
		elif type=="cancel":
			if subtype=="invoice":
				str1="The invoice requires approval to proceed due to partial/full produced item(MRP). Enter your reason to submit a request and continue."
			else:
				str1="The order requires approval to proceed due to open/paid invoice/s. Enter your reason to submit a request and continue."
		elif type=="mrp":
			str1="The order requires approval to proceed due to having their outstanding balance over the allowed credit limit. Enter your reason to submit a request and continue."
		else:
			str1=""
			
		if 'o_ids' in context:	
			#str1 += "\n'[%s']"% str(context['o_ids'])
			_ids=""
			for id1 in context['o_ids']:
				_ids+="'%s'," % (id1)
			if len(_ids)>0:	
				_ids= _ids[:-1]
				sql="select distinct name from sale_order where id in (%s) order by name"	 % (_ids)
				cr.execute(sql)
				rows = cr.fetchall()
				#_logger.error("_is_sale_ordersale_ordersale_orderor_sqlsqlsql["+str(sql)+"]")
				_ids=""
				for row in rows:
					_ids+="%s, " % (row[0])
				if len(_ids)>0:	
					_ids= _ids[:-2]	
					str1 += "\n\nFollowing orders related:\n%s\n\n"% str(_ids)
		#for record in self.browse(cr, uid, ids, context=context):
		#approve_flag=False
		
		lids4=[]
		_config_id = self.pool.get('dincelaccount.config.settings').search(cr,uid,[('id', '>', '0')], limit=1)
		if _config_id:
			_conf= self.pool.get('dincelaccount.config.settings').browse(cr, uid, _config_id, context=context)
			if approve_flag:
				if _conf and _conf.authorise_cc:
					lids4.append(_conf.authorise_cc.id)
			#else:
			#	#if _conf and _conf.manager_cc:
			#	#	lids4.append(_conf.manager_cc.id)
					
		return {'value':{'notes':str1,'partner_ids':lids4}}	
		
		
	def submit_request(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		_id=None	
		for record in self.browse(cr, uid, ids, context=context):			
			#_logger.error("submit_requestsubmit_requestnse888["+str(record)+"]partner_ids["+str(record.partner_ids)+"]")
			#return True
			if record.approve_flag:
				_id=record.request_id.id
				vals={'state':record.state,'comments':record.comments,'approve_uid':uid}
				self.pool.get('dincelsale.order.approve').write(cr, uid, _id, vals, context=context)
				if record.state=="approve":
					if record.subtype=="invoice":
						#sql="select 1 from dincelsale_order_approve where order_id='%s' and state='open' and invoice_id='%s'" % (record.order_id.id, record.invoice_id.id)	
						#cr.execute(sql)
						#rows1 = cr.fetchall()
						#if len(rows1) == 0:
						sql="update account_invoice set "
						if record.type=="refund":
							sql+="x_authorise_refund"
						else:
							sql+="x_authorise_cancel"
						#sql="update account_invoice set x_authorise_cancel='t' where id='%s'" % (record.invoice_id.id)
						sql += "='t' where id='%s'" % (record.invoice_id.id)
						cr.execute(sql)
						#_logger.error("dincelsale.order.approvedincelsale.order.sqlsql["+str(sql)+"]") 
					else:
						sql="select 1 from dincelsale_order_approve where order_id='%s' and state='open'" % (record.order_id.id)	
						cr.execute(sql)
						rows1 = cr.fetchall()
						if len(rows1) == 0:
							sql="update sale_order set "
							if record.type=="cancel":
								sql+="x_authorise_cancel"
							elif record.type=="mrp":
								sql+="x_authorise_mrp"
							else:
								sql+="x_authorise_discount"
							sql += "='t' where id='%s'" % (record.order_id.id)
							cr.execute(sql)
				return self.send_mail_notify2(cr, uid, record, _id, context=context)
				#if tf:
					
			else:
				vals = {
					#'order_id': record.order_id.id,
					'name':record.order_id.name,#self.pool.get('ir.sequence').get(cr, uid, 'item.approval'),
					'type': record.type,
					'subtype': record.subtype,
					'date': record.date,
					'request_uid': uid,
					'request_text':record.request_text,
					}
				if record.order_id:
					vals['order_id']=record.order_id.id	
				if record.invoice_id:
					vals['invoice_id']=record.invoice_id.id
				#_logger.error("dincelsale.order.approvedincelsale.order.approve["+str(vals)+"]") 
				_id = self.pool.get('dincelsale.order.approve').create(cr, uid, vals, context=context)
				#self.send_request_notify( cr, uid, record, _id, context=None)
				return self.send_mail_notify2( cr, uid, record, _id,context=context)
			return _id
			 
 	def get_mail_request(self, cr, uid, record, res_ids, context=None):
		results = dict.fromkeys(res_ids, False)
		rendered_values, default_recipients = {}, {}
		rec=self.pool.get('res.users').browse(cr,uid,uid)
		body=""#Approval request added.\n"# % (record.request_id.request_uid.name)
		subj_part=""
		record_name=""
		if record.order_id:
			body+="Order: %s " % (record.order_id.name)
			subj_part="[%s]" % (record.order_id.name)
			record_name=record.order_id.name
		if record.invoice_id:
			if record.invoice_id.number:
				body+="\nInvoice: %s " % (record.invoice_id.number)
				if record_name=="":
					record_name=record.invoice_id.number
					
		body+="\nType: %s " % (record.type.title())
		body+="\nSubtype: %s " % (record.subtype.title())		
		body+="\nRequested By: %s " % (rec.partner_id.name)	
		body+="\nComments: \n%s " % (record.request_text)
		body = tools.plaintext2html(body)
		for res_id in res_ids:
			mail_values = {
				'subject': 'A new approval request added ' + subj_part,
				'body': body,
				#'parent_id': None,
				'partner_ids': [partner.id for partner in record.partner_ids],
				#'attachment_ids': [attach.id for attach in wizard.attachment_ids],
				#'author_id': wizard.author_id.id,
				'email_from': "erp@dincel.com.au",
				'record_name': record_name,
				'no_auto_thread': False,
				'res_id': False,
				'model':'dincelsale.order.approve',#saleorder.approve.request',#'dincelsale.order.approve',
				#'composition_mode':'comment',
				
			}
			
			
			#mail_values['body_html'] = mail_values['body']
			#_logger.error("get_mail_requestget_mail_request["+str(mail_values)+"]")
			results[res_id] = mail_values
		return results
		
	def get_mail_response(self, cr, uid, record, res_ids, context=None):
		results = dict.fromkeys(res_ids, False)
		rendered_values, default_recipients = {}, {}
		# static wizard (mail.message) values
		if record.state=="approve":
			_state="Approved"
		else:
			_state="Rejected"
		'''body="""Hi %s,\nBelow is response to your approval request.
						\n\nStatus: %s 
						\n\nComments:\
						n%s""" % (record.request_id.request_uid.name, _state, record.comments)'''
		body="Hi %s,\nBelow is response to your approval request." % (record.request_id.request_uid.name)
		subj_part=""
		record_name=""
		if record.order_id:
			body+="\nOrder: %s " % (record.order_id.name)
			record_name=record.order_id.name
			subj_part="[%s]" % (record.order_id.name)
			#body+="\n\nOrder: %s " % (record.order_id.name)
		if record.invoice_id:
			if record.invoice_id.number:
				body+="\nInvoice: %s " % (record.invoice_id.number)
				if record_name=="":
					record_name=record.invoice_id.number
		#'subject': 'A new approval request added ' + subj_part,		
		body+="\nType: %s " % (record.type.title())
		body+="\nSubtype: %s " % (record.subtype.title())		
		body+="\nStatus: %s " % (_state)
		body+="\nComments: \n%s " % (record.comments)
		body = tools.plaintext2html(body)
		for res_id in res_ids:
			mail_values = {
				'subject': 'Re your approval request response ' + subj_part,
				'body': body,
				#'parent_id': None,
				'partner_ids': [partner.id for partner in record.partner_ids],
				#'attachment_ids': [attach.id for attach in wizard.attachment_ids],
				#'author_id': wizard.author_id.id,
				'email_from': "erp@dincel.com.au",
				'record_name': record_name,
				'no_auto_thread': False,
				'res_id': res_id,
				#'res_id': False,
				'model':'dincelsale.order.approve',
				#'composition_mode':'comment',
				
			}
			
			
			#mail_values['body_html'] = mail_values['body']
			#_logger.error("get_mail_responseget_mail_response000["+str(mail_values)+"]partner_ids["+str(record.partner_ids)+"]")
			results[res_id] = mail_values
		return results
		
	def send_mail_notify2(self, cr, uid, record, res_id, context=None):
		obj = self.pool['mail.thread']
		if record.approve_flag:
			all_mail_values = self.get_mail_response(cr, uid, record, [res_id], context=context)
		else:
			all_mail_values = self.get_mail_request(cr, uid, record, [res_id], context=context)
		#notif_obj = self.pool.get('mail.notification')
		for res_id, mail_values in all_mail_values.iteritems(): 
			
			#_id=self.pool['mail.mail'].create(cr, uid, mail_values, context=context)
			#if _id:
			subtype=False
			
			msg_id = obj.message_post_dcs(cr, uid, [res_id], type='comment', subtype=subtype, context=context, **mail_values)
			'''#if msg_id:
					#_logger.error("mail_valuesmail_valuespartner_ids.msg_id["+str(msg_id)+"]["+str(mail_values['partner_ids'])+"]")
					#for pid in mail_values['partner_ids']:
					#	id1=notif_obj.create(cr, uid, {'partner_id': pid, 'is_read': False, 'message_id': msg_id}, context=context)
						#_logger.error("mail_valuesmail_valuespartner_ids11["+str(id1)+"]["+str(pid)+"]")
			#_logger.error("send_mail_notifysend_mail_notify.res_id["+str(res_id)+"]["+str(mail_values)+"]")'''
		return {'type': 'ir.actions.act_window_close'}