from openerp.tools.translate import _
from osv import osv, fields
from datetime import date
from openerp.addons.base_status.base_state import base_state
import time 
import datetime
import csv
from openerp import netsvc
from openerp.osv import fields, osv, orm
import logging
_logger = logging.getLogger(__name__)

class dincelcrm_quotecontract(osv.Model):
	_inherit="account.analytic.account"
	def onchange_quote_qty(self, cr, uid, ids, q1 = 0, q2 = 0, q3 = 0, q4 = 0, q5 = 0, q6 = 0, q7 = 0, q8 = 0, q9 = 0, q10 = 0, context = None):
		tot = q1 + q2 + q3 + q4 + q5 + q6 + q7 + q8 + q9 + q10
		rate1 = 0
		rate2 = 0
		rate3 = 0	
		 
		sql = "select rate1,rate2,rate3 from dincelcrm_quote_rates where %s between from_val and to_val" % tot
		cr.execute(sql)
		rows = cr.fetchall()
		if len(rows)==0:
			rate1 = 0
			rate2 = 0
			rate3 = 0	
		else:
			for row1 in rows:
				rate1 = float(row1[0])
				rate2 = float(row1[1])
				rate3 = float(row1[2])
						
		return {'value': {'x_quote_total': tot, 'x_rate1': rate1, 'x_rate2': rate2, 'x_rate3': rate3 }} 
		
	def get_quote_total(self, cr, uid, ids, values, arg, context):
		x={}
		tot=0
		for record in self.browse(cr, uid, ids):
			tot=record.x_quote_110 + record.x_quote_200+record.x_quote_base_110 + record.x_quote_base_200+record.x_quote_party_110 + record.x_quote_party_200+record.x_quote_lift_110 + record.x_quote_lift_200+record.x_quote_facade_110 + record.x_quote_facade_200
			x[record.id]=tot
		return x	
	
	def get_quote_total_110(self, cr, uid, ids, values, arg, context):
		x={}
		tot=0
		for record in self.browse(cr, uid, ids):
			tot=record.x_quote_110+record.x_quote_base_110+record.x_quote_party_110 +record.x_quote_lift_110+record.x_quote_facade_110 
			x[record.id]=tot
		return x	
	
	def get_quote_total_200(self, cr, uid, ids, values, arg, context):
		x={}
		tot=0
		for record in self.browse(cr, uid, ids):
			tot=record.x_quote_200+ record.x_quote_base_200+ record.x_quote_party_200 + record.x_quote_lift_200+ record.x_quote_facade_200
			x[record.id]=tot
		return x	
	
	def create(self, cr, uid, vals, context=None):
		if vals.get('name','/')=='/':
			vals['name'] = self.pool.get('ir.sequence').get(cr, uid, 'quotation.number') or '/'
		#else:
		#	vals['name'] = "lead"
		return super(dincelcrm_quotecontract, self).create(cr, uid, vals, context=context)
	
	
	def write(self, cr, uid, ids, vals, context=None):
		#tot=0
		probability=0
		res = super(dincelcrm_quotecontract, self).write(cr, uid, ids, vals, context=context)
		for record in self.browse(cr, uid, ids):
			tot		=record.x_quote_total
			rate	=record.x_rate3
			project_id	=record.x_project_id.id
			probability	=record.x_probability
			sale_dt		=record.x_likely_sale_dt
			#_logger.error("quotecontract:update=tot[" + str(tot)+ "][" + str(rate)+ "][" + str(project_id)+ "]")	 
			
		if tot and rate and project_id:
			estimate = tot*rate
			if sale_dt:
				strupdate = ",x_likely_sale_dt='" + sale_dt +"'"
			else:
				strupdate = ""
			try:	
				sql="update res_partner set x_project_size=%s,x_project_value=%s %s where id=%s " % (tot,estimate,strupdate, project_id)
				cr.execute(sql)
			except ValueError:
				probability = 0
			#_logger.error("quoteupdate:update=sql-" + sql)	 
			try:
				cr.execute("update crm_lead set probability=%s,planned_revenue=%s where x_project_id=%s " % (probability,estimate, project_id))
			except ValueError:
				probability = 0
		return res
	
	def onchange_lead_name(self, cr, uid, ids, project_id, context=None):
		
		if project_id:
			obj 	= self.pool.get('res.partner').browse(cr,uid,project_id,context=context)
			val1	= obj.name
			my_list = []
			#val2 	= obj.x_role_partner_ids
			#@_logger.error("lead_name:val2 -" + str(val2))	 
			for item in obj.x_role_partner_ids:
				_logger.error("lead_name:item.id:" + str(item.id))	 
				my_list.append(item.id) 
			domain  = {'partner_id': [('id','in', (my_list))]}
			value   = {'name':val1}
			
			return {'value': value, 'domain': domain}
			
		return {}	
		
	def onchange_project(self, cr, uid, ids, project_id, client_id, context=None):
		
		if project_id:
		
			lids1	= self.pool.get('res.partner').search(cr,uid,[('parent_id','=',project_id),('x_is_project', '=', False)])	#site contacts
			lids2	= self.pool.get('res.partner').search(cr,uid,[('parent_id','=',client_id),('x_is_project', '=', False)])  #client contacts
			domain  = {'x_contact_id': [('id','in', (lids1 + lids2))]}
		
			if client_id:
				cr.execute("update res_partner set parent_id=%s where id=%s and parent_id is null" % (client_id, project_id))
			return {'domain': domain}
		
		return {}
		
	def onchange_contact(self, cr, uid, ids, contact_id, project_id, context=None):
		if contact_id and project_id:
			cr.execute("update res_partner set parent_id=%s where id=%s and parent_id is null" % (project_id, contact_id))
		return {}		
	
	def transport_rate_change(self, cr, uid, ids, rate_id, context=None):
		if rate_id:
			rate1 = 0.0
			rate2 = 0.0
			rate3 = 0.0	
			 
			sql = "select rate1,rate2,rate3 from dincelcrm_quote_transport_rates where id=%s" % rate_id
			cr.execute(sql)
			rows = cr.fetchall()
			if len(rows)==0:
				rate1 = 0.0
				rate2 = 0.0
				rate3 = 0.0	
			else:
				for row1 in rows:
					rate1 = float(row1[0])
					rate2 = float(row1[1])
					rate3 = float(row1[2])
							
			return {'value': {'x_rate_trans1': rate1,'x_rate_trans2': rate2,'x_rate_trans3': rate3 }} 
				
			 
		return {}		
	
	def message_get_suggested_recipients(self, cr, uid, ids, context=None):
		recipients = super(dincelcrm_quotecontract, self).message_get_suggested_recipients(cr, uid, ids, context=context)
		try:
			for quote in self.browse(cr, uid, ids, context=context):
				if quote.partner_id:
					self._message_add_suggested_recipient(cr, uid, recipients, quote, partner=quote.partner_id, reason=_('Customer'))
				if quote.x_contact_id:
					self._message_add_suggested_recipient(cr, uid, recipients, quote, partner=quote.x_contact_id, reason=_('Contact Email'))	

		except (osv.except_osv, orm.except_orm):  # no read access rights -> just ignore suggested recipients because this imply modifying followers
			pass
		return recipients
		
	def _get_quote_est_amt(self, cr, uid, ids, values, arg, context):
		x={}
		tot=0
		for record in self.browse(cr, uid, ids):
			tot=record.x_quote_total
			x[record.id]=tot*record.x_rate3
		return x	
	
	def get_lead_id(self, cr, uid, ids, values, arg, context):
		x={}
		for record in self.browse(cr, uid, ids):
			if record.x_project_id:
				cr.execute("select id from crm_lead where x_project_id=" + str(record.x_project_id.id))
				rows = cr.fetchall()
				if len(rows) > 0:
					found = "1"
				else:
					found = "0"
			else:
				found = "0"
			x[record.id]=found
		return x
		
	_columns = {
		'x_quote_110': fields.integer('Total 110mm'),
		'x_quote_200': fields.integer('Total 200mm'),
		'x_quote_base_lbl': fields.char('Basement Walls Label',size=30),
		'x_quote_party_lbl': fields.char('Party Walls Label',size=30),
		'x_quote_lift_lbl': fields.char('Lift/Stair Walls Label',size=30),
		'x_quote_facade_lbl': fields.char('Facade Walls Label',size=30),
		'x_quote_base_110': fields.integer('Basement Walls 110'),
		'x_quote_base_200': fields.integer('Basement Walls 200'),
		'x_quote_party_110': fields.integer('Party Walls 110'),
		'x_quote_party_200': fields.integer('Party Walls 200'),
		'x_quote_lift_110': fields.integer('Lift/Stair Walls 110'),
		'x_quote_lift_200': fields.integer('Lift/Stair Walls 200'),
		'x_quote_facade_110': fields.integer('Facade Walls 110'),
		'x_quote_facade_200': fields.integer('Facade Walls 200'),
		'x_quote_total':   fields.function(get_quote_total, method=True, string='Project Total',type='integer'),
		'x_quote_total_110':   fields.function(get_quote_total_110, method=True, string='Total 110',type='integer'),
		'x_quote_total_200':   fields.function(get_quote_total_200, method=True, string='Total 200',type='integer'),
		'x_rate1':fields.float("30 Days EOM"),
		'x_rate2':fields.float("14 Days EOM"),
		'x_rate3':fields.float("COD"),
		'x_rate_trans1':fields.float("Transport 30 Days"),
		'x_rate_trans2':fields.float("Transport 14 Days"),
		'x_rate_trans3':fields.float("Transport COD"),
		'x_rate_accs1':fields.float("Accs 30 Days"),
		'x_rate_accs2':fields.float("Accs 14 Days"),
		'x_rate_accs3':fields.float("Accs COD"),
		'x_is_rate1':fields.boolean("Is 30 Days"),
		'x_is_rate2':fields.boolean("Is 14 Days"),
		'x_is_rate3':fields.boolean("Is COD"),
		'x_project':fields.char("Project",size=100),
		'x_site_address':fields.char("Site Address",size=100),
		'x_likely_sale_dt':fields.date("Likely Sale Date"),
		'x_projecttype_ids' : fields.many2many('dincelcrm.projecttype', 'contract_rel_projecttype', 'object_id', 'contract_projecttype_id', string = "Type of Project"),
		'x_project_id': fields.many2one('res.partner','Project / Site'),
		'x_contact_id': fields.many2one('res.partner','Contact'),
		'x_drawing_txt': fields.char("Drawing Components",size=200),
		'x_transport_txt': fields.char("Transport Components",size=200),
		'x_ref_no':fields.char("Reference No",size=100),
		'x_is_quote':fields.boolean("Is Quote"),
		'x_estimate_csv': fields.binary('Estimate CSV File'),
		'x_payment_term': fields.many2one('account.payment.term','Payment Term'),
		'x_stage_id': fields.many2one('crm.case.stage','Stage'),
		'x_transport_rate_id': fields.many2one('dincelcrm.quote.transport.rates','Transport Components'),
		'x_wall_type_id1': fields.many2one('dincelcrm.quote.wall.type','Wall 1'),
		'x_wall_type_id2': fields.many2one('dincelcrm.quote.wall.type','Wall 2'),
		'x_wall_type_id3': fields.many2one('dincelcrm.quote.wall.type','Wall 3'),
		'x_wall_type_id4': fields.many2one('dincelcrm.quote.wall.type','Wall 4'),
		'x_wall_type_id5': fields.many2one('dincelcrm.quote.wall.type','Wall 5'),
		'x_lead_id': fields.many2one('crm.lead','Lead Reference'),
		'x_prepared_by': fields.many2one('res.users','Prepared By'),
		'x_date_quote': fields.date("Quote Date"),
		'x_proj_state':fields.related('x_project_id', 'state_id', string="Project State", type="many2one", relation="res.country.state", store=False),
		'x_quote_est_amt':fields.function(_get_quote_est_amt, method=True,string='Estimate Amount',type='float'),
		'x_probability':fields.float("Likelihood of Sales (%)"),
		'x_phonecall_ids': fields.one2many('crm.phonecall', 'x_contract_quote_id', string="Follow-ups"),
		'x_date_from':fields.function(lambda *a,**k:{}, method=True, type='date',string="Date Event"),
		'x_has_lead_oppr': fields.function(get_lead_id, method=True, string='has lead oppr',type='char'),
	}
	_defaults={
		'x_is_quote': True,
		'date': fields.date.context_today, #time.strftime('%Y-%m-%d'),
		'x_date_quote': fields.date.context_today, #time.strftime('%Y-%m-%d'),
		'x_rate_accs1': 3.0, 
		'x_rate_accs2': 3.0,
		'x_rate_accs3': 3.0,
        'x_rate_trans1': 2.5, 
		'x_rate_trans2': 2.5,
		'x_rate_trans3': 2.5,
		'x_probability': 22.0,
		'x_drawing_txt': "DRAWINGS: Set out and components list - Deposit required prior to commencement. (optional) $2.00 per m2 ex GST",
		'x_transport_txt': "TRANSPORTATION: Minimum quantity 125m2 - Sydney metro areas",
		'user_id': lambda obj, cr, uid, context: uid,
        'name': lambda obj, cr, uid, context: '/',
    }
	_order = 'date desc, id desc'
	
	def print_quotation(self, cr, uid, ids, context=None):
		'''
		This function prints the quotation (3 templates) as at 8/5/2015
		'''
		assert len(ids) == 1, 'This option should only be used for a single id at a time'
		wf_service = netsvc.LocalService("workflow")
		wf_service.trg_validate(uid, 'account.analytic.account', ids[0], 'quotation_sent', cr)
		datas = {
				 'model': 'account.analytic.account',
				 'ids': ids,
				 'form': self.read(cr, uid, ids[0], context=context),
		}
		
		name = "Quote"
		rate1=False
		rate2=False
		rate3=False
		
		for record in self.browse(cr, uid, ids, context=context):
			name = record.name
			rate1 = record.x_is_rate1
			rate2 = record.x_is_rate2
			rate3 = record.x_is_rate3
		
		if rate1 == True and rate3 == False:	
			reportname="account.analytic.account.quote_rate1"
		elif rate1 == False and rate3 == True:
			reportname="account.analytic.account.quote_rate3"
		elif rate2 == True:
			reportname="account.analytic.account.quote_rate2"
		else:
			reportname="account.analytic.account.quote"
		return {'type': 'ir.actions.report.xml', 'report_name': reportname, 'datas': datas, 'name': name , 'nodestroy': True}	
		#return {'type': 'ir.actions.report.xml', 'report_name': 'account.analytic.account.quote', 'datas': datas, 'name': name , 'nodestroy': True}
		
	def confirm_sale(self, cr, uid, ids, context=None):
		
		return {}
	