import time
from openerp.osv import fields, osv
from openerp.tools.translate import _
import logging
_logger = logging.getLogger(__name__)

class dincelcrm_followup(osv.osv_memory):
	_name = "dincelcrm.followup"
	_columns = {
		'date': fields.date('Date'),
		'date_from': fields.datetime('Date'),
		'lines':fields.one2many('dincelcrm.followup.line', 'followup_id', 'Fllowups'),
		'interval':fields.integer("Interval"),
		'qty':fields.integer("Qty test"),
		'comments':fields.char("Comments"),
		'partner_id':fields.many2one('res.partner', 'Partner'),
		'project_id':fields.many2one('res.partner', 'Project/Site'),
		'contact_id':fields.many2one('res.partner', 'Contact'),
		'quote_id':fields.many2one('account.analytic.account', 'Quote'),
		'interval_type':fields.selection([ #>>as revise type
			('day','Day'),
			('week','Week'),
			('month','Month'),
			], 'Interval Type'),
	}
	
	def add_items(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		items=[]	
		value={}
		
		for record in self.browse(cr, uid, ids, context=context):
			if not record.date_from:
				raise osv.except_osv(_('Error'), _('Please select date from.'))
			if not record.interval or record.interval==0:
				raise osv.except_osv(_('Error'), _('Please enter a valid number in interval field.'))
			if not record.interval_type:
				raise osv.except_osv(_('Error'), _('Please select a valid Interval Type.'))	
				
			_interval=record.interval
			_type=record.interval_type
			_comments=record.comments
			_dt=record.date_from
			vals={'fw_date':_dt,'notes':_comments}
			items.append(vals)
			value={'lines':items}
		#return {}
		_logger.error("add_itemsadd_itemsadd_items["+str(value)+"]")	
		#raise osv.except_osv(_('Error'), _('['+str(value)+'].'))	
		#return {'value':value,"type": "ir.actions.do_nothing",}
		return self.write(cr, uid, ids, {'value': value}, context=context)
		 
	def confirm_save(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		_obj 	= self.pool.get('crm.phonecall')	
		for record in self.browse(cr, uid, ids, context=context):	#record = self.browse(cr, uid, ids[0], context=context)
			if not record.project_id and not record.partner_id:
				raise osv.except_osv(_('Error'), _('Please select a valid project or a customer.'))	
			for _line in record.lines: 
				nextdt	=	_line.fw_date
				nextact	=	_line.notes
				_vals = {
					'x_is_followup': True,
					'name': 'follow-up', 
					'state': 'open', 
					'date': nextdt, 
					'x_instruction': nextact, 
					'priority':'1',
				}
				#'x_contract_quote_id': q_obj.id, 
				if record.quote_id:
					_vals['x_contract_quote_id'] =record.quote_id.id
					
				#if non_project:
				#	_vals['x_non_project'] =non_project
				if record.contact_id:
					_vals['x_contact_id'] = record.contact_id.id
				if record.partner_id:
					_vals['partner_id'] = record.partner_id.id
				if record.project_id:
					_vals['x_project_id'] = record.project_id.id	
				new_id 		= _obj.create(cr, uid, _vals, context=context)
			return True
			 
		
	 
		
	def _get_init_qty(self, cr, uid, context=None):
		return 1
	_defaults = {
		'qty': _get_init_qty,
		'date': lambda *a: time.strftime('%Y-%m-%d'),
		}
	 
	
class dincelcrm_followup_line(osv.osv_memory):
	_name="dincelcrm.followup.line"
	_columns = {
		'followup_id': fields.many2one('dincelcrm.followup', 'Fw'),
		'sequence': fields.integer('Sequence'),
		'fw_date': fields.datetime('Date'),
		'notes':fields.char("Notes"),	
	}

class dincelcrm_approval_request(osv.Model):
	_name = "dincelcrm.approval.request"
	_columns = {
		'date': fields.date('Date'),
		'name': fields.char('Name'),
		'comments':fields.text("Comments"),
		'partner_id':fields.many2one('res.partner', 'Request to'),
		'quotation_id':fields.many2one('account.analytic.account', 'Quotation'),
	}
	
	def send_approval_request(self, cr, uid, ids, context=None):
		for record in self.browse(cr, uid, ids):
			self.pool.get('account.analytic.account').write(cr, uid, record.quotation_id.id, {'state': 'need_approval'})
			ret_id = None
			'''
			#self.ensure_one()
			#ir_model_data = self.pool.get('ir.model.data')
			template_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'dincelcrm', 'approval_request_email_template')[1]
			#template = self.env.ref('dincelcrm.approval_request_email_template')
			_logger.error("send_approval_request111["+str(template_id)+"]["+str(record.id)+"]")
			ret_id = self.pool.get['email.template'].send_mail(cr, uid, template_id, record.id, force_send=True, context=context)
			if(ret_id):
				return True
			else:
				return False
			'''	
			user_id = record.partner_id.id
			body = record.comments
			mail_details = {'subject': "Message subject",
				 'body': body,
				 'partner_ids': [(record.partner_id)]
				 } 
			mail = self.pool.get['mail.thread']
			mail.message_post(type="notification", subtype="mt_comment", **mail_details)
		return False