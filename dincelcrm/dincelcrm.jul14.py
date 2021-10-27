from openerp.osv import osv, fields
from datetime import date
#from openerp.addons.base_status.base_state import base_state
import time 
import datetime
import csv
import logging
import config_dcs
#from crm import crm
from time import gmtime, strftime
_logger = logging.getLogger(__name__)

class dincelreport_res_partner(osv.Model):
	_inherit = "res.partner"
	
	def onchange_sitename(self, cr, uid, ids, isproj,sitename, context = None):
		if isproj and sitename:
			return {'value': {'street': sitename}}
		return {}	
	def display_rate(self, cr, uid, ids, values, arg, context):
		x={}
		for record in self.browse(cr, uid, ids):
			cr.execute("select 1 from res_partner where customer='1' and parent_id is null and id=" + str(record.id))
			rows = cr.fetchall()
			if len(rows) > 0:
				active_id = "1"
			else:
				active_id = "0"
			x[record.id]=active_id 
		return x
	
	def cr_limit_over(self, cr, uid, ids, values, arg, context):
			
		x={}
		_over=False
		for record in self.browse(cr, uid, ids):
			if record.credit_limit>0:
				sql ="select sum(amount_total) from sale_order where partner_id='%s' and x_status='open'" % (record.id)
				cr.execute(sql)
				rows = cr.fetchone()
				if rows == None or len(rows)==0:
					_over=False
				else:
					 if rows[0]!=None:
						if record.credit_limit<rows[0]:
							_over=True
		x[record.id] = _over 
		return x
		
	_columns = {
		'x_is_competitor': fields.boolean('Is A Competitor'),
		'x_cr_limit_over': fields.function(cr_limit_over, method=True, string='Cr Limit', type='boolean'),
		'x_is_project': fields.boolean('Is A Project Site'),	#DINCEL specific a client has many projects/sites. and [client] & [site/project] have many contacts
		'x_certifier':fields.boolean('Certifier'),
		'x_builder':fields.boolean('Builder'),
		'x_engineer':fields.boolean('Engineer'),
		'x_architect':fields.boolean('Architect'),
		'x_formwork':fields.boolean('Formwork'),
		'x_architect_id': fields.many2one('res.partner','Architect'),
		'x_formwork_id': fields.many2one('res.partner','Formwork'),
		'x_builder_id': fields.many2one('res.partner', 'Builder'),
		'x_engineer_id': fields.many2one('res.partner', 'Engineer'),
		'x_certifier_id': fields.many2one('res.partner', 'Certifier'),
		'x_source_id': fields.many2one('dincelcrm.leadsource', 'Lead Source'),
		'x_project_value':fields.float('Project Value'),
		'x_project_size':fields.float('Project Size'),
		'x_likely_sale_dt':fields.date("Likely Sale Date"),
		'x_role_partner_ids' : fields.many2many('res.partner', 'rel_partner_roles', 'object_partner_id', '_partner_roles_id', string = "Customers or Contacts"),
		'description': fields.char('Description'),	#v7 compatibility
		'x_role_site_ids' : fields.many2many('res.partner', 'rel_partner_roles', '_partner_roles_id', 'object_partner_id', string = "Sites"),
		'x_phonecall_ids': fields.one2many('crm.phonecall', 'x_project_id','Site History'),
		'x_customer_rate_ids': fields.one2many('dincelcrm.customer.rate', 'partner_id','Rate History'),
		'x_display_rate': fields.function(display_rate, method=True, string='Display Rate',type='char'),
		'x_market_wall_id': fields.many2one('dincelcrm.market.wall.type','Specified Wall'),
		'x_dcs_id': fields.char('DCS ID'),
		'x_acn': fields.char('ACN'),
		'x_ctype':fields.selection([
			('other', 'Other'),
            ('ac', 'Account')
			], 'Contact Type'),
	}

AVAILABLE_STATES = [
    ('draft', 'New'),
    ('cancel', 'Cancelled'),
    ('open', 'In Progress'),
    ('pending', 'Pending'),
    ('done', 'Closed')
]

'''	
class dincelcrm_sale_order(osv.Model):
	_inherit = "sale.order"
	_columns = {
		'x_project_id': fields.many2one('res.partner','Project / Site'),
	}	
'''	

class dincelcrm_phonecallactivities(osv.Model):
	_inherit = "crm.phonecall"
	
	def get_lead_id(self, cr, uid, ids, values, arg, context):
		x={}
		for record in self.browse(cr, uid, ids):
			cr.execute("select id from crm_lead where x_phonecall_id=" + str(record.id))
			rows = cr.fetchall()
			if len(rows) > 0:
				active_id = "1"
			else:
				active_id = "0"
			x[record.id]=active_id 
		return x
	
	def get_quote_no(self, cr, uid, ids, values, arg, context):
		x={}
		active_id = "-"
		for record in self.browse(cr, uid, ids):
			if record.x_project_id:
				cr.execute("select name from account_analytic_account where x_quote_converted=True and x_project_id=" + str(record.x_project_id.id))
				rows = cr.fetchall()
				if len(rows) > 0:
					active_id = rows[0][0]
				else:	
					active_id = "-"
			x[record.id]=active_id
		return x
	
	def convert2lead(self, cr, uid, ids, context=None):
		lead_obj 		= self.pool.get('account.analytic.account')
		x_project_id =None
		vals = {
					'x_prepared_by': uid,
					'x_stage_id': 1, 
					'state':'open',
				}
					
		for record in self.browse(cr, uid, ids, context=context):
			x_project_id = record.x_project_id
			user_id 	 = record.user_id
			partner_id	 = record.partner_id
			x_contact_id = record.x_contact_id
			if user_id:
				vals['user_id'] =  user_id.id
			if x_project_id:
				vals['x_project_id']  	= x_project_id.id
				vals['name']  			= x_project_id.name
			if partner_id:
				vals['partner_id']		= partner_id.id
			if x_contact_id:
				vals['x_contact_id']	= x_contact_id.id	
		
		if x_project_id:
			new_id 		= lead_obj.create(cr, uid, vals, context=context)
			if new_id:
				view_id = self.pool.get('ir.ui.view').search(cr,uid,[('name', '=', 'dincelcrm.contractquote.form.view')], limit=1)
				value 	= {
							'domain': str([('id', 'in', new_id)]),
							'view_type': 'form',
							'view_mode': 'form',
							'res_model': 'account.analytic.account',
							'view_id': view_id,
							'type': 'ir.actions.act_window',
							'res_id': new_id,
							'target': 'new',
		
						}
				return value
		return {}		
		
	def on_change_userid(self, cr, uid, ids, user_id, context=None):
		if user_id:
			cr.execute("select default_section_id from res_users where id=" + str(user_id))
		
			rows 		= cr.fetchone()
			if rows == None or len(rows)==0:
				return {'value': {}}
			else:
				 if rows[0]!=None:
					return {'value': {'section_id': rows[0]}}
		return {'value': {}}
	
	def write(self, cr, uid, ids, vals, context=None):
		name=None
		id=None
		newname=None
		partner_id=None
		nextdt=fields.date.context_today(self,cr,uid,context=context)
		nextact=None
		q_obj=None
		
		res = super(dincelcrm_phonecallactivities, self).write(cr, uid, ids, vals, context=context)
		for record in self.browse(cr, uid, ids):
			name		= record.name
			id			= record.id	
			comments	= record.description	
			newname		= record.x_project_id and record.x_project_id.name
			nextact		= record.x_next_action
			nextdt		= record.x_next_act_date
			project_id	= record.x_project_id
			contact_id	= record.x_contact_id
			partner_id	= record.partner_id
			q_obj		= record.x_contract_quote_id
			
		#_logger.error("dincelcrm_phonecallactivitiesdincelcrm_phonecallactivities["+str(name)+"]")	
		if name and name == 'follow-up' and newname and comments and len(comments)>0 and q_obj:
			try:	
				sql="update crm_phonecall set name='%s',state='done' where id=%s " % (newname.replace("'",""),id)
				cr.execute(sql)
				
				#update the related quotation status as well
				if project_id and record.x_status and q_obj:
					sql="update account_analytic_account set x_status='%s' where id=%s " % (record.x_status, q_obj.id)
					cr.execute(sql)
					
				if nextact and nextdt and len(nextact)>0 and q_obj:
					_obj 	= self.pool.get('crm.phonecall')
					_vals = {
						'x_is_followup': True,
						'name': 'follow-up', 
						'state': 'open', 
						'date': nextdt, 
						'x_instruction': nextact, 
						'x_contract_quote_id': q_obj.id,
						'priority':'1',
					 }
					
					if contact_id:
						_vals['x_contact_id'] = contact_id.id
					if partner_id:
						_vals['partner_id'] = partner_id.id
					if project_id:
						_vals['x_project_id'] = project_id.id	
					new_id 		= _obj.create(cr, uid, _vals, context=context)
				#else:
				#	if q_obj:
				#		sql="update account_analytic_account set x_has_fw_pending=False where id=%s " % (q_obj.id)
				#		cr.execute(sql)
			except ValueError:
				name=None
		else:
			#comments required to detect drag and drop change event
			if name and name == 'follow-up' and newname and comments and len(comments)>0:
				sql="update crm_phonecall set name='%s',state='done' where id=%s " % (newname.replace("'",""),id)
				cr.execute(sql)
			if nextact and nextdt and len(nextact)>0:
				
				sql ="select 1 from crm_phonecall where name = 'follow-up' and x_origin_fw='%s'" %(id)
				cr.execute(sql)
				rows = cr.fetchall()
				if len(rows)==0:
					_obj 	= self.pool.get('crm.phonecall')
					_vals = {
						'x_is_followup': True,
						'name': 'follow-up', 
						'state': 'open', 
						'date': nextdt, 
						'x_instruction': nextact, 
						'priority':'1',
						'x_origin_fw':id,
					}
					
					if contact_id:
						_vals['x_contact_id'] = contact_id.id
					if partner_id:
						_vals['partner_id'] = partner_id.id
					if project_id:
						_vals['x_project_id'] = project_id.id	
					new_id 		= _obj.create(cr, uid, _vals, context=context)
				
		if partner_id and project_id:
			self._write_relation_if(cr, uid, partner_id.id,project_id.id, context=context) 
			'''sql	= "SELECT * from rel_partner_roles  where  object_partner_id='%s' and _partner_roles_id='%s'" % (project_id.id,partner_id.id)
			cr.execute(sql)
			
			rows_chk = cr.fetchall()
			if rows_chk == None or len(rows_chk)==0:
				sql ="insert into rel_partner_roles (object_partner_id,_partner_roles_id) values('%s','%s')" % (project_id.id,partner_id.id)
			 	cr.execute(sql)
				#cr.commit() //not required
			'''	
		return res	
	
	def _write_relation_if(self, cr, uid, partner_id,project_id, context=None):
		if partner_id and project_id:
			
			sql	= "SELECT * from rel_partner_roles  where  object_partner_id='%s' and _partner_roles_id='%s'" % (project_id,partner_id)
			cr.execute(sql)
			
			rows_chk = cr.fetchall()
			if rows_chk == None or len(rows_chk)==0:
				sql ="insert into rel_partner_roles (object_partner_id,_partner_roles_id) values('%s','%s')" % (project_id,partner_id)
			 	cr.execute(sql)
				
	def create(self, cr, uid, vals, context=None):
		partner_id = vals.get('partner_id',False)
		project_id = vals.get('x_project_id',False)
		self._write_relation_if(cr, uid, partner_id,project_id, context=context) 
		return super(dincelcrm_phonecallactivities, self).create(cr, uid, vals, context=context)

		
	_columns = {
		'x_project_id': fields.many2one('res.partner','Project / Site'),
		'x_contact_id': fields.many2one('res.partner','Site Contact'),
		'x_proj_val': fields.related('x_project_id', 'x_project_value', type='float', string='Project Value',store=False),
		'x_proj_size': fields.related('x_project_id', 'x_project_size', type='float', string='Project Size',store=False),
		'x_likely_sale_dt': fields.related('x_project_id', 'x_likely_sale_dt', type='date', string='Likely Sale Date',store=False),
		'x_phone_partner': fields.related('partner_id', 'phone', type='char', string='Customer Phone',store=False),
		'x_phone': fields.related('x_contact_id', 'phone', type='char', string='Site Contact Phone',store=False),
		'x_mobile': fields.related('x_contact_id', 'mobile', type='char', string='Site Contact Mobile',store=False),
		'x_email': fields.related('x_contact_id', 'email', type='char', string='Site Contact Email',store=False),
		'x_is_coldcall': fields.boolean('Cold Call'),
		'x_ref': fields.char('Lead reference'),
		'x_has_lead': fields.function(get_lead_id, method=True, string='Has Lead',type='char'),
		'x_get_quote': fields.function(get_quote_no, method=True, string='Quote',type='char'),
		'x_date_from':fields.function(lambda *a,**k:{}, method=True, type='date',string="Date Event"),
		'x_date_from_src':fields.function(lambda *a,**k:{}, method=True, type='date',string="Date From"),
		'x_date_to_src':fields.function(lambda *a,**k:{}, method=True, type='date',string="Date To"),
		'x_contract_quote_id': fields.many2one('account.analytic.account','Quote Ref'),
		'x_is_followup': fields.boolean('Followup'),
		'x_instruction': fields.char('Followup Instruction'),
		'x_next_action': fields.char('Next Action'),
		'x_next_act_date': fields.datetime("Next Action Date"),
		'x_status':fields.selection(config_dcs.QUOTE_STATUS, 'Status'),
		'x_origin_fw':fields.many2one('crm.phonecall','Origin Activity'),
		}
	
	def onchange_status_quote(self, cr, uid, ids, _status, context=None):
		if _status:
			str1	= dict(config_dcs.QUOTE_STATUS)[_status]
			value   = {'description':str1}
			return {'value': value}
	#def onchange_client(self, cr, uid, ids, client_id, context=None):
	#	if client_id:
	#		lids=self.pool.get('res.partner').search(cr,uid,[('parent_id','=',client_id),('x_is_project', '=', True)])
	#		return {'domain':{'x_project_id':[('id','in',lids)]}}
	#	return {}
	def onchange_client(self, cr, uid, ids, project_id, client_id, context=None):
		if client_id:
			c_ids3  = []
			my_list = []
			obj		= self.pool.get('res.partner').browse(cr,uid,client_id,context=context)
			for item in obj.x_role_site_ids:
				my_list.append(item.id) 
				c_ids3 = c_ids3 + self.pool.get('res.partner').search(cr, uid, [('parent_id', '=', item.id)], context=context)
			
			
			c_ids1 = self.pool.get('res.partner').search(cr, uid, [('parent_id', '=', client_id)], context=context)
			if project_id:
				c_ids2 = self.pool.get('res.partner').search(cr, uid, [('parent_id', '=', project_id)], context=context)
				c_ids1 = c_ids1+ c_ids2
			else:
				c_ids1 = c_ids3
				
			if len(c_ids1)>0:
				domain  = {'x_project_id': [('id','in', (my_list))],'x_contact_id': [('id','in', (c_ids1))]}#domain['x_contact_id']=[('id','in', (my_list))]
			else:
				domain  = {'x_project_id': [('id','in', (my_list))]}
			return {'domain': domain}	
			
		else:
			
			ids2 = self.pool.get('res.partner').search(cr, uid, [('x_is_project', '=', True)], context=context)
			c_ids1 = self.pool.get('res.partner').search(cr, uid, [('x_is_project', '=', False),('is_company', '=', False)], context=context)
			domain  = {'x_project_id': [('id','in', (ids2))],'x_contact_id': [('id','in', (c_ids1))]}
			return {'domain': domain}	
			
	def onchange_project(self, cr, uid, ids, project_id, client_id, context=None):
		if project_id:
			obj		= self.pool.get('res.partner').browse(cr,uid,project_id,context=context)
			
			val1	= obj.name
			p_val	= obj.x_project_value
			p_size	= obj.x_project_size
			
			dt_sales= obj.x_likely_sale_dt	
			
			my_list = []
			
			for item in obj.x_role_partner_ids:
				my_list.append(item.id) 
			
			c_ids1 = self.pool.get('res.partner').search(cr, uid, [('parent_id', '=', project_id)], context=context)
			if client_id:
				c_ids2 = self.pool.get('res.partner').search(cr, uid, [('parent_id', '=', client_id)], context=context)
				c_ids1 = c_ids1+ c_ids2
				
			if len(my_list)>0:
				domain  = {'partner_id': [('id','in', (my_list))],'x_contact_id': [('id','in', (c_ids1))]}
			else:
				ids2 = self.pool.get('res.partner').search(cr, uid, [('customer', '=', True),('x_is_project', '=', False)], context=context)
				#domain ={}
				domain  = {'partner_id': [('id','in', (ids2))],'x_contact_id': [('id','in', (c_ids1))]}
			
			
			value   = {'name':val1,'x_proj_val':p_val,'x_proj_size':p_size,'x_likely_sale_dt':dt_sales} #,'x_formwork_id': formwork
			return {'value': value, 'domain': domain}
		else:
			c_ids1 = self.pool.get('res.partner').search(cr, uid, [('x_is_project', '=', False),('is_company', '=', False)], context=context)
			ids2 = self.pool.get('res.partner').search(cr, uid, [('x_is_project', '=', False)], context=context)
            
			domain  = {'partner_id': [('id','in', (ids2))],'x_contact_id': [('id','in', (c_ids1))]}
			return {'domain': domain}	
		#return {}	
	
	def onchange_contact(self, cr, uid, ids, contact_id, p_id, context=None):
		if contact_id:
			mobile	= self.pool.get('res.partner').browse(cr,uid,contact_id,context=context).mobile
			phone	= self.pool.get('res.partner').browse(cr,uid,contact_id,context=context).phone
			email	= self.pool.get('res.partner').browse(cr,uid,contact_id,context=context).email
			value   = {'x_phone':phone,'x_mobile':mobile,'x_email':email}
			if p_id:
				cr.execute("update res_partner set parent_id=%s where id=%s and parent_id is null" % (p_id, contact_id))
			return {'value': value}
		return {}		
		
		
		
class dincelcrm_quote_rates(osv.Model):
	_name="dincelcrm.quote_rates"
	_columns={
		'name':fields.char("Name",size=300),
		'from_val':fields.integer("From"),
		'to_val':fields.integer("To"),
		'rate1':fields.float("30 Day"),
		'rate2':fields.float("14 Day"),
		'rate3':fields.float("COD"),
		'rate_other_ac':fields.float("275mm Rate AC"),
		'rate_other_cod':fields.float("275mm Rate COD"),
		'rate_line':fields.one2many('dincelcrm.quote_state_rates', 'quote_rate_id', string="State Rates"),
		'location_line':fields.one2many('dincelcrm.location_rates', 'location_rate_id', string="Location Rates"),
	}
	
class dincelcrm_location_rate(osv.Model): 
	_name="dincelcrm.location_rates"
	_columns={
		'name':fields.char("Name",size=100),
		'location_rate_id': fields.many2one('dincelcrm.quote_rates', 'Reference',  select=True),
		'warehouse_id':fields.many2one("stock.warehouse","Location"),
		'rate1':fields.float("+30 Day Rate"),
		'rate2':fields.float("+14 Day Rate"),
		'rate3':fields.float("+COD Rate"),
	}	
	
class dincelcrm_quote_state_rates(osv.Model): 
	_name="dincelcrm.quote_state_rates"
	_columns={
		'name':fields.char("Name",size=100),
		'quote_rate_id': fields.many2one('dincelcrm.quote_rates', 'Reference',  select=True),
		'state_id':fields.many2one("res.country.state","State"),
		'rate1':fields.float("30 Day Rate"),
		'rate2':fields.float("14 Day Rate"),
		'rate3':fields.float("COD Rate"),
	}
	
class dincelcrm_quote_transport_rates(osv.Model):
	_name="dincelcrm.quote.transport.rates"
	_columns={
		'name':fields.text("Name"),
		'rate1':fields.float("30 Day"),
		'rate2':fields.float("14 Day"),
		'rate3':fields.float("COD"),
		'region':fields.char("Region",size=50),
		'min_order':fields.char("Minimum",size=10),
		'rate_truck':fields.float("Rate Per Load"),
	}
	
class dincelcrm_quote_wall_type(osv.Model):
	_name="dincelcrm.quote.wall.type"
	_columns={
		'name':fields.char("Name",size=200)
	}	
class dincelcrm_market_wall_types(osv.Model):
	_name="dincelcrm.market.wall.type"
	_columns={
		'name': fields.char('Name',size=64, required=True),
	}
	
class dincelcrm_projecttype(osv.Model):
	_name = "dincelcrm.projecttype"
	_columns = {
		'name': fields.char('Name',size=64, required=True),
		'object_id': fields.many2one('ir.model', 'Object Name'),
	}
	
class dincelcrm_customer_rate(osv.Model):
	_name= "dincelcrm.customer.rate"
	
	def find(self, cr, uid, dt=None,partner_id=None, context=None):
		if context is None: context = {}
		if not dt:
			dt = fields.date.context_today(self, cr, uid, context=context)
		args = [('date_from', '<=' ,dt), ('date_to', '>=', dt),('partner_id', '=', partner_id)]
		
		#result = []
		#s="1"
		result = self.search(cr, uid, args, context=context)
		if not result:#NOTE: to date is open or blank
			args = [('date_from', '<=' ,dt), ('partner_id', '=', partner_id), ('date_to', '=', False)]
			result = self.search(cr, uid, args, context=context)
			#s="2"
		#_logger.error("dincelcrm_customer_rate_findfind["+str(result)+"]["+str(dt)+"]["+str(s)+"]")	
		return result
		
	_order = 'date_from desc'	
	_columns={
		'rate_cod':fields.float("COD Rate"),
		'rate_acct':fields.float("Account Rate"),
		'date_from':fields.date("From Date"),
		'date_to':fields.date("To Date"),
		'partner_id':fields.many2one("res.partner","Customer"),
	}		


class dincelcrm_leadsource(osv.Model):
	_name="dincelcrm.leadsource"
	_order = 'sort_index asc,name  asc'
	_columns={
		'name': fields.char('Name',size=64, required=True),
		'sort_index': fields.integer('Sort Index')
	}

class dincelcrm_salespersonnote(osv.Model):
	_name = "dincelcrm.salespersonnote"
	_columns = {
		'note': fields.text('Note'),
		'notedate': fields.date('Date', required=True),
		'duration' : fields.char('Duration', size=10),
		'crm_lead_id': fields.many2one('crm.lead','CRM Lead'),
		'user_id': fields.many2one('res.users','Salesperson'),
		'email_from': fields.related('crm_lead_id', 'email_from', type='char', size=128, string='Email',store=False),
		'contact_name': fields.related('crm_lead_id', 'contact_name', type='char', size=128, string='Contact Name',store=False),
	}
	_defaults={
        'notedate' : fields.date.context_today, 
		'user_id': lambda s, cr, uid, c: uid,
		'duration' : '1.0',
    }
'''	
class dincelcrm_crm_lead(osv.Model):
	_inherit = "crm.lead"
	_columns = {
		'x_ref_no':fields.char("RefNumber",size=50),
		'x_phonecall_id': fields.many2one('crm.phonecall','Phonecall'),
		'state': fields.related('stage_id', 'state', type="selection", store=True,
                selection=AVAILABLE_STATES, string="Status", readonly=True, select=True,
                help='The Status is set to \'Draft\', when a case is created. If the case is in progress the Status is set to \'Open\'. When the case is over, the Status is set to \'Done\'. If the case needs to be reviewed then the Status is  set to \'Pending\'.'), #backward compatibility for v7
	}	'''	
class dincelcrm_crm_lead(osv.Model):
	_inherit = "crm.lead"
	def onchange_client(self, cr, uid, ids, client_id, context=None):
		if client_id:
			lids=self.pool.get('res.partner').search(cr,uid,[('parent_id','=',client_id),('x_is_project', '=', True)])
			return {'domain':{'x_project_id':[('id','in',lids)]}}
		return {}
	
	def onchange_project(self, cr, uid, ids, project_id, client_id, context=None):
		if project_id:
			obj		= self.pool.get('res.partner').browse(cr,uid,project_id,context=context)
			val1	= obj.name
			#p_val	= self.pool.get('res.partner').browse(cr,uid,project_id,context=context).x_project_value
			#p_size	= self.pool.get('res.partner').browse(cr,uid,project_id,context=context).x_project_size
			'''
			lids1	= self.pool.get('res.partner').search(cr,uid,[('parent_id','=',project_id),('x_is_project', '=', False)])	#site contacts
			lids2	= self.pool.get('res.partner').search(cr,uid,[('parent_id','=',client_id),('x_is_project', '=', False)])  #client contacts
			domain  = {'x_contact_id': [('id','in', (lids1 + lids2))]}
			
			if client_id:
				cr.execute("update res_partner set parent_id=%s where id=%s and parent_id is null" % (client_id, project_id))'''
			my_list = []
			for item in obj.x_role_partner_ids:
				my_list.append(item.id) 
			value   = {'name':val1}	
			domain  = {'partner_id': [('id','in', (my_list))]}	
			return {'value': value, 'domain': domain}
			
		return {}	
		
	def onchange_contact(self, cr, uid, ids, contact_id, project_id, context=None):
		if contact_id and project_id:
			cr.execute("update res_partner set parent_id=%s where id=%s and parent_id is null" % (project_id, contact_id))
		return {}			

	def get_quote_id(self, cr, uid, ids, values, arg, context):
		x={}
		for record in self.browse(cr, uid, ids):
			cr.execute("select id from account_analytic_account where x_lead_id=" + str(record.id))
			rows = cr.fetchall()
			if len(rows) > 0:
				found = "1"
			else:
				found = "0"
			x[record.id]=found
		return x
	

	_columns = {
		'x_project_id': fields.many2one('res.partner','Project / Site'),
		'x_proj_val': fields.related('x_project_id', 'x_project_value', type='float', string='Project Value',store=False),
		'x_likely_sale_dt': fields.related('x_project_id', 'x_likely_sale_dt', type='date', string='Likely Sale Date',store=False),
		'x_proj_size': fields.related('x_project_id', 'x_project_size', type='float', string='Project Size',store=False),
		'x_proj_state':fields.related('x_project_id', 'state_id', string="Project State", type="many2one", relation="res.country.state", store=False),
		'x_source_id': fields.related('x_project_id', 'x_source_id',  string='Lead Source', type="many2one", relation="dincelcrm.leadsource",store=False),
		'x_contact_id': fields.many2one('res.partner','Site Contact'),
		'salespersonnote_ids': fields.one2many('dincelcrm.salespersonnote', 'crm_lead_id', string="Notes"),
		'x_builder_id': fields.many2one('res.partner', 'Builder', domain="[('x_contact_type', '=', 'B')]"),
		'x_engineer_id': fields.many2one('res.partner', 'Engineer', domain="[('x_contact_type', '=', 'E')]"),
		'x_certifier_id': fields.many2one('res.partner', 'Certifier', domain="[('x_contact_type', '=', 'C')]"),
		'x_projecttype_ids' : fields.many2many('dincelcrm.projecttype', 'rel_lead_projecttype', 'object_id', 'lead_projecttype_id', string = "Type of Project"),
		#'competitorstype_ids' : fields.many2many('dincelreport.competitorstype', 'rel_competitorstype', 'crm_lead_id', 'tags_id', string = "Competitors"),
		'x_ref_no':fields.char("RefNumber",size=50),
		'x_phonecall_id': fields.many2one('crm.phonecall','Phonecall'),
		'x_has_quote': fields.char(compute='get_quote_id', string='has quote'),
		'state': fields.selection([('open', 'Open'),('draft', 'draft')]),
		#'x_ref_no':fields.char("RefNumber",size=50),
		#'x_phonecall_id': fields.many2one('crm.phonecall','Phonecall'),
	}	#'x_last_fw_desc': fields.char(compute='last_fw_desc', string='Last follow-up comments'),	