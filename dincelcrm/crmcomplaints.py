from openerp.osv import osv, fields
from datetime import date
#from openerp.addons.base_status.base_state import base_state
import time 
import datetime
from openerp import tools
from openerp.tools.translate import _
#from openerp.osv import fields, osv, orm
from time import gmtime, strftime
import logging
_logger = logging.getLogger(__name__)

AVAILABLE_PRIORITIES = [
	('0', 'Very Low'),
	('1', 'Low'),
	('2', 'Normal'),
	('3', 'High'),
	('4', 'Very High'),
]

OPTIONS_COMPLAINTS = [
	('production', 'Production'),
	('delivery', 'Delivery / Collection'),
	('service', 'Customer Service'),
	('other', 'Other'),
]

class dincelcrm_complaints(osv.Model):
	_name="dincelcrm.complaints"
	_inherit = ['mail.thread']
	_order = "entry_dt desc"
	_description = 'Customer Complaint'
	_track = {
		'state': {
			'dincelcrm.mt_complaint_pending': lambda self, cr, uid, obj, ctx=None: obj.state == 'pending',
			'dincelcrm.mt_complaint_closed': lambda self, cr, uid, obj, ctx=None: obj.state == 'close',
			'dincelcrm.mt_complaint_opened': lambda self, cr, uid, obj, ctx=None: obj.state == 'open',
		},
	}

	_columns={
		'name':fields.char("Title",size=300, required=True,track_visibility='onchange'),
		'user_id': fields.many2one('res.users','Entry By'),
		'report_to': fields.many2one('res.users','Report To',track_visibility='onchange'),
		'entry_dt':fields.date("Entry Date"),
		'description':fields.text("Description"),
		'investigation':fields.text("Investigation"),
		'actiontext':fields.text("Preventive Action"),
		'action_rqd':fields.boolean("Action Required?"),
		'action_dt':fields.date("Implementation Date"),
		'completed':fields.boolean("Implementation Completed"),
		'state': fields.selection([('draft','New'),
					('open','In Progress'),
					('close','Closed'), #cancelled
					('cancel', 'Cancelled')],
					'Status', required=True,
					track_visibility='onchange', copy=False),
		'type': fields.selection(OPTIONS_COMPLAINTS, 'Type', select=True),		
		'priority': fields.selection(AVAILABLE_PRIORITIES, 'Priority', select=True),		
		'partner_id': fields.many2one('res.partner','Customer'),		
		'project_id': fields.many2one('res.partner','Project / Site'),
		'contact_id': fields.many2one('res.partner','Site Contact'),		
		'proj_val': fields.related('project_id', 'x_project_value', type='float', string='Project Value',store=False),
		'proj_size': fields.related('project_id', 'x_project_size', type='float', string='Project Size',store=False),
		'phone_partner': fields.related('partner_id', 'phone', type='char', string='Customer Phone',store=False),
		'phone': fields.related('contact_id', 'phone', type='char', string='Site Contact Phone',store=False),
		'mobile': fields.related('contact_id', 'mobile', type='char', string='Site Contact Mobile',store=False),
		'email': fields.related('contact_id', 'email', type='char', string='Site Contact Email',store=False),
		'type_other':fields.char("Other Type",size=100),
	}
	_defaults={
        'entry_dt' : fields.date.context_today, 
		'user_id': lambda s, cr, uid, c: uid,
		'state': 'draft',
	}
	
	def onchange_client(self, cr, uid, ids, project_id, client_id, context=None):
		if client_id:
			c_ids3  = []
			my_list = []
			obj		= self.pool.get('res.partner').browse(cr,uid,client_id,context=context)
			for item in obj.x_role_site_ids:
				my_list.append(item.id) 
				c_ids3 = c_ids3 + self.pool.get('res.partner').search(cr, uid, [('parent_id', '=', item.id)], context=context)
			
			
			contactids = self.pool.get('res.partner').search(cr, uid, [('parent_id', '=', client_id)], context=context)
			if project_id:
				c_ids2 = self.pool.get('res.partner').search(cr, uid, [('parent_id', '=', project_id)], context=context)
				contactids = contactids + c_ids2
			else:
				contactids = c_ids3
				
			if len(contactids)>0:
				domain  = {'project_id': [('id','in', (my_list))],'contact_id': [('id','in', (contactids))]}#domain['x_contact_id']=[('id','in', (my_list))]
			else:
				domain  = {'project_id': [('id','in', (my_list))]}
			return {'domain': domain}	
			
		else:
			
			siteids = self.pool.get('res.partner').search(cr, uid, [('x_is_project', '=', True)], context=context)
			contactids = self.pool.get('res.partner').search(cr, uid, [('x_is_project', '=', False),('is_company', '=', False)], context=context)
			domain  = {'project_id': [('id','in', (siteids))],'contact_id': [('id','in', (contactids))]}
			return {'domain': domain}	
			
	def onchange_contact(self, cr, uid, ids, contact_id, context=None):
		if contact_id:
			obj		= self.pool.get('res.partner').browse(cr,uid,contact_id,context=context)
			email	= obj.email
			phone	= obj.phone
			mobile	= obj.mobile	
			value   = {'email':email,'phone':phone,'mobile':mobile}
			return {'value': value}
			
	def onchange_project(self, cr, uid, ids, project_id, client_id, context=None):
		if project_id:
			obj		= self.pool.get('res.partner').browse(cr,uid,project_id,context=context)
			
			#val1	= obj.name
			#p_val	= obj.x_project_value
			#p_size	= obj.x_project_size
			#dt_sales= obj.x_likely_sale_dt	
			
			my_list = []
			
			for item in obj.x_role_partner_ids:
				my_list.append(item.id) 
			
			contactids = self.pool.get('res.partner').search(cr, uid, [('parent_id', '=', project_id)], context=context)
			if client_id:
				c_ids2 = self.pool.get('res.partner').search(cr, uid, [('parent_id', '=', client_id)], context=context)
				contactids = contactids+ c_ids2
				
			if len(my_list)>0:
				domain  = {'partner_id': [('id','in', (my_list))],'contact_id': [('id','in', (contactids))]}
			else:
				siteids = self.pool.get('res.partner').search(cr, uid, [('customer', '=', True),('x_is_project', '=', False)], context=context)
				#domain ={}
				domain  = {'partner_id': [('id','in', (siteids))],'contact_id': [('id','in', (contactids))]}
			
			
			value   = {}#'name':val1,'x_proj_val':p_val,'x_proj_size':p_size,'x_likely_sale_dt':dt_sales} #,'x_formwork_id': formwork
			return {'value': value, 'domain': domain}
		else:
			contactids = self.pool.get('res.partner').search(cr, uid, [('x_is_project', '=', False),('is_company', '=', False)], context=context)
			siteids = self.pool.get('res.partner').search(cr, uid, [('x_is_project', '=', False)], context=context)
            
			domain  = {'partner_id': [('id','in', (siteids))],'contact_id': [('id','in', (contactids))]}
			return {'domain': domain}	
	'''def message_get_suggested_recipients(self, cr, uid, ids, context=None):
		res = super(dincelcrm_complaints, self).message_get_suggested_recipients(cr, uid, ids, context=context)
		try:
			for record in self.browse(cr, uid, ids, context=context):
				if record.report_to:
					self._message_add_suggested_recipient(cr, uid, res, record, user=record.report_to, reason=_('Manager'))
				#elif issue.email_from:
				#	self._message_add_suggested_recipient(cr, uid, recipients, issue, email=issue.email_from, reason=_('Customer Email'))
		except (osv.except_osv, orm.except_orm):  # no read access rights -> just ignore suggested recipients because this imply modifying followers
			pass
		return res'''
	
	def write(self, cr, uid, ids, vals, context=None):
		 
		res = super(dincelcrm_complaints, self).write(cr, uid, ids, vals, context=context)
		for record in self.browse(cr, uid, ids):
			if record.action_rqd and record.action_rqd == True:
				if record.state == "close" and not record.completed:
					raise osv.except_osv(_('Error'), _('Pleae make sure the implementation is completed before closing the case!!'))
				else:
					if record.completed and not record.action_dt:
						raise osv.except_osv(_('Error'), _('Pleae enter implementation date before closing the case!!'))
			if record.state == "close":
				_id=record.id
				sql="select 1 from dincelbase_notification where res_model='dincelcrm.complaints' and res_id='%s' and code='complaints'" % (str(_id))
				cr.execute(sql)	
				rows = cr.fetchone()
				if rows == None or len(rows)==0:
					val={
						"res_model":"dincelcrm.complaints",
						"name":"",
						"res_id":_id,
						"code":"complaints",
						"state":"",
					}
					self.pool.get('dincelbase.notification').create(cr, uid, val, context=context)
					
		return res
	