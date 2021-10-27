from openerp.tools.translate import _
from openerp.osv import osv, fields
from datetime import date
from datetime import datetime
import datetime
from datetime import timedelta
import config_dcs
#from dateutil import parser from datetime import date
#from openerp.addons.base_status.base_state import base_state
import time 
#import datetime
import csv
from openerp import netsvc, api
from openerp.osv import fields, osv, orm
import logging
import pytz
_logger = logging.getLogger(__name__)
#from openerp import models, fields, api, _
class dincelcrm_quotecontract(osv.Model):
	_inherit="account.analytic.account"
	def onchange_quote_qty(self, cr, uid, ids, q1 = 0, q2 = 0, q3 = 0, q4 = 0, q5 = 0, q6 = 0, q7 = 0, q8 = 0, q9 = 0, q10 = 0, context = None):
		tot = q1 + q2 + q3 + q4 + q5 + q6 + q7 + q8 + q9 + q10
		rate1 = 0
		rate2 = 0
		rate3 = 0	
		 
		sql = "select rate1,rate2,rate3,id from dincelcrm_quote_rates where %s between from_val and to_val" % tot
		state_id = None
		rate_id = None
		#_logger.error("onchange_quote_qty:update=tot[" + str(tot)+ "][" + str(sql)+ "][" + str(q10)+ "]")	
		for record in self.browse(cr, uid, ids):
			if record.x_project_id:
				state_id = record.x_project_id.state_id
				
		cr.execute(sql)
		rows = cr.fetchall()
		if len(rows)==0:
			rate1 = 0
			rate2 = 0
			rate3 = 0	
		else:
			for row1 in rows:
				rate_id = row1[3]
				rate1 = float(row1[0])
				rate2 = float(row1[1])
				rate3 = float(row1[2])
			if state_id and rate_id:
				sql = "select rate1,rate2,rate3,id from dincelcrm_quote_state_rates where state_id='%s'" % str(state_id.id)
				cr.execute(sql)
				#_logger.error("get_quote_total:sqlsql[" + str(sql)+ "]")
				rows2 = cr.fetchall()
				for row2 in rows2:
					#rate_id = row1[3]
					rate1 = float(row2[0])
					rate2 = float(row2[1])
					rate3 = float(row2[2])
		return {'value': {'x_quote_total': tot, 'x_rate1': rate1, 'x_rate2': rate2, 'x_rate3': rate3 }} 
	
	def onchange_quote_qty2(self, cr, uid, ids, project_id, q1 = 0, q2 = 0, q3 = 0, q4 = 0, q5 = 0, q6 = 0, q7 = 0, q8 = 0, q9 = 0, q10 = 0, context = None):
		tot = q1 + q2 + q3 + q4 + q5 + q6 + q7 + q8 + q9 + q10
		rate1 = 0
		rate2 = 0
		rate3 = 0	
		 
		sql = "select rate1,rate2,rate3,id from dincelcrm_quote_rates where %s between from_val and to_val" % tot
		state_id = None
		
		rate_id = None
		if project_id:
			obj 	= self.pool.get('res.partner').browse(cr,uid,project_id,context=context)
			if obj.state_id:
				state_id =obj.state_id.id
				
		#_logger.error("onchange_quote_qty:update=tot[" + str(tot)+ "][" + str(sql)+ "][" + str(q10)+ "]")	
		#for record in self.browse(cr, uid, ids):
		#	if record.x_project_id:
		#		state_id = record.x_project_id.state_id
				
		cr.execute(sql)
		rows = cr.fetchall()
		if len(rows)==0:
			rate1 = 0
			rate2 = 0
			rate3 = 0	
		else:
			for row1 in rows:
				rate_id = str(row1[3])
				rate1 = float(row1[0])
				rate2 = float(row1[1])
				rate3 = float(row1[2])
			if state_id and rate_id:
				sql = "select rate1,rate2,rate3,id from dincelcrm_quote_state_rates where state_id='%s' and quote_rate_id='%s'" % (str(state_id),rate_id)
				cr.execute(sql)
				#_logger.error("get_quote_total:sqlsql[" + str(sql)+ "]")
				rows2 = cr.fetchall()
				for row2 in rows2:
					#rate_id = row1[3]
					rate1 = float(row2[0])
					rate2 = float(row2[1])
					rate3 = float(row2[2])
		return {'value': {'x_quote_total': tot, 'x_rate1': rate1, 'x_rate2': rate2, 'x_rate3': rate3 }} 
		
	def get_quote_total(self, cr, uid, ids, values, arg, context):
		x={}
		tot=0
		#_logger.error("get_quote_total:values[" + str(values)+ "]ids[" + str(ids)+ "]arg[" + str(arg)+ "]")	
		for record in self.browse(cr, uid, ids):
			tot=record.x_quote_110 + record.x_quote_200+record.x_quote_base_110 + record.x_quote_base_200+record.x_quote_party_110 + record.x_quote_party_200+record.x_quote_lift_110 + record.x_quote_lift_200+record.x_quote_facade_110 + record.x_quote_facade_200
			x[record.id]=tot
			#_logger.error("get_quote_total:tottot[" + str(tot)+ "][" + str(record.id)+ "][" + str(record.x_quote_lift_200)+ "]")	
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
			#_logger.error("x_phonecall_idsx_phonecall_ids["+str(record.x_phonecall_ids)+"]")
			for fw in record.x_phonecall_ids:
				if fw.name=="follow-up":
					if record.x_status and record.x_status != "" and record.x_status != "open":
						sname=record.x_project_id.name.replace("'","")
						sdesc=dict(config_dcs.QUOTE_STATUS)[record.x_status]
						sql ="update crm_phonecall set state='done',name='%s',x_status='%s',description='%s' where id = '%s'" % (sname,record.x_status,sdesc,fw.id)
						cr.execute(sql)
					#self.write(cr, uid, ids, {'x_has_fw_pending':True}, context=context)
					#sql="update account_analytic_account set x_has_fw_pending=True where id=%s " % (record.id)
					#cr.execute(sql)
			#datetime.datetime
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
			user_id = obj.user_id
			my_list = []
			#val2 	= obj.x_role_partner_ids
			#@_logger.error("lead_name:val2 -" + str(val2))	 
			for item in obj.x_role_partner_ids:
				#_logger.error("lead_name:item.id:" + str(item.id))	 
				my_list.append(item.id) 
			if len(my_list)>0:
				domain  = {'partner_id': [('id','in', (my_list))]}
			else:
				domain  = {}
				
			value   = {'name':val1}
			if user_id:
				value['user_id'] = user_id
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
		
	def onchange_contact(self, cr, uid, ids, contact_id, p_id, context=None):
		if contact_id and p_id:
			cr.execute("update res_partner set parent_id=%s where id=%s and parent_id is null" % (p_id, contact_id))
		return {}		
	
	def transport_rate_change(self, cr, uid, ids, rate_id, context=None):
		if rate_id:
			rate1 = 0.0
			rate2 = 0.0
			rate3 = 0.0	
			rate_truck = 0.00
			try:			
				sql = "select rate1,rate2,rate3,rate_truck from dincelcrm_quote_transport_rates where id=%s" % rate_id
				cr.execute(sql)
				rows = cr.fetchall()
				if len(rows)==0:
					rate1 = 0.0
					rate2 = 0.0
					rate3 = 0.0	
					rate_truck = 0.00
				else:
					for row1 in rows:
						rate1 = float(row1[0])
						rate2 = float(row1[1])
						rate3 = float(row1[2])
						rate_truck = float(row1[3])
			except (osv.except_osv, orm.except_orm):  # no read access rights -> just ignore suggested recipients because this imply modifying followers
				pass					
			return {'value': {'x_rate_trans1': rate1,'x_rate_trans2': rate2,'x_rate_trans3': rate3,'x_rate_truck': rate_truck}} 
				
			 
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
	def last_fw_dt(self, cr, uid, ids, values, arg, context):
		x={}
		for record in self.browse(cr, uid, ids):
			if record.x_project_id:
				cr.execute("select to_char(date, 'MM/dd/YYYY i:mm:ss am') from crm_phonecall where x_project_id=" + str(record.x_project_id.id) + " order by date desc")
				rows 	= cr.fetchone()
				if rows == None or len(rows) == 0:
					txt = "-"
				else:	
					_from_date 	=  datetime.datetime.strptime(rows[0],"%m/%d/%Y %I:%M:%S %p")
					#_form_date = datetime.today()
					time_zone	='Australia/Sydney'
					tz 			= pytz.timezone(time_zone)
					tzoffset 	= tz.utcoffset(_from_date)
					txt 		= str((_from_date + tzoffset).strftime("%d/%m/%Y"))
			else:
				txt 		= "-"
			x[record.id]	= txt
		return x
	
	def last_fw_by(self, cr, uid, ids, values, arg, context):
		x={}
		for record in self.browse(cr, uid, ids):
			if record.x_project_id:
				cr.execute("select user_id from crm_phonecall where x_project_id=" + str(record.x_project_id.id) + " order by date desc")
				rows 	= cr.fetchone()
				if rows == None or len(rows) == 0:
					txt = "-"
				else:	
					cr.execute("select p.name from res_users r,res_partner p where r.partner_id=p.id and r.id=" + str(rows[0]) + " ")
					rows1 	= cr.fetchone()
					if rows1 == None or len(rows1) == 0:
						txt 	= "-"
					else:	
						txt 	= rows1[0]
			else:
				txt = "-"
			x[record.id]=txt
		return x
		
	def has_fw_pending(self, cr, uid, ids, values, arg, context):
		x={}
		for record in self.browse(cr, uid, ids):
			if record.x_project_id:
				cr.execute("select description from crm_phonecall where x_project_id=" + str(record.x_project_id.id) + " and name='follow-up' ")
				rows 	= cr.fetchone()
				if rows == None or len(rows) == 0:
					txt = "0"
				else:	
					txt = "1"
			else:
				txt = "0"
			x[record.id]=txt
		return x	
		
	def last_fw_desc(self, cr, uid, ids, values, arg, context):
		x={}
		for record in self.browse(cr, uid, ids):
			if record.x_project_id:
				cr.execute("select description from crm_phonecall where x_project_id=" + str(record.x_project_id.id) + " order by date desc")
				rows 	= cr.fetchone()
				if rows == None or len(rows) == 0:
					txt = "-"
				else:	
					txt = rows[0]
			else:
				txt = "-"
			x[record.id]=txt
		return x	
	#tot=record.x_quote_110 + record.x_quote_200+record.x_quote_base_110 + record.x_quote_base_200+record.x_quote_party_110 + record.x_quote_party_200+record.x_quote_lift_110 + record.x_quote_lift_200+record.x_quote_facade_110 + record.x_quote_facade_200
	quote_total = fields.integer(compute='_get_quote_total')	
	
	@api.one
	@api.depends('x_quote_110', 'x_quote_200', 'x_quote_base_110','x_quote_base_200','x_quote_party_110','x_quote_party_200','x_quote_lift_110','x_quote_lift_200','x_quote_facade_110','x_quote_facade_200')
	def _get_quote_total(self):
		for record in self:
			#tot = self.x_quote_110 + self.x_quote_200+self.x_quote_base_110 + self.x_quote_base_200+self.x_quote_party_110 + self.x_quote_party_200+self.x_quote_lift_110 + self.x_quote_lift_200+self.x_quote_facade_110 + self.x_quote_facade_200
			tot=record.x_quote_110 + record.x_quote_200+record.x_quote_base_110 + record.x_quote_base_200+record.x_quote_party_110 + record.x_quote_party_200+record.x_quote_lift_110 + record.x_quote_lift_200+record.x_quote_facade_110 + record.x_quote_facade_200
			self.quote_total = tot
		#return tot
	
	#'cost' : fields.function(get_total, method=True, string='Total',type='float'),
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
		'x_quote_275_q1': fields.integer('Wall 275 - q1'),
		'x_quote_275_q2': fields.integer('Wall 275 - q2'),
		'x_quote_275_q3': fields.integer('Wall 275 - q3'),
		'x_quote_275_q4': fields.integer('Wall 275 - q4'),
		'x_quote_275_q5': fields.integer('Wall 275 - q5'),
		'x_quote_155_q1': fields.integer('Wall 155 - q1'),
		'x_quote_155_q2': fields.integer('Wall 155 - q2'),
		'x_quote_155_q3': fields.integer('Wall 155 - q3'),
		'x_quote_155_q4': fields.integer('Wall 155 - q4'),
		'x_quote_155_q5': fields.integer('Wall 155 - q5'),
		'x_quote_total': fields.function(get_quote_total, method=True, string='Project Total',type='integer'),
		'x_quote_total_110': fields.function(get_quote_total_110, method=True, string='Total 110',type='integer'),
		'x_quote_total_200': fields.function(get_quote_total_200, method=True, string='Total 200',type='integer'),
		'x_rate1':fields.float("30 Days EOM"),
		'x_rate2':fields.float("14 Days EOM"),
		'x_rate3':fields.float("COD"),
		'x_rate_truck':fields.float("Rate Per Load"),
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
		'x_proj_val': fields.related('x_project_id', 'x_project_value', type='float', string='Project Value',store=False),
		'x_proj_name': fields.related('x_project_id', 'name', type='char', string='Project Name',store=False),
		'x_source_id': fields.related('x_project_id', 'x_source_id',  string='Lead Source', type="many2one", relation="dincelcrm.leadsource",store=False),
		'x_phone_partner': fields.related('partner_id', 'phone', type='char', string='Customer Phone',store=False),
		'x_contact_id': fields.many2one('res.partner','Contact'),
		'x_phone': fields.related('x_contact_id', 'phone', type='char', string='Site Contact Phone',store=False),
		'x_mobile': fields.related('x_contact_id', 'mobile', type='char', string='Site Contact Mobile',store=False),
		'x_email': fields.related('x_contact_id', 'email', type='char', string='Site Contact Email',store=False),
		'x_contact_name': fields.related('x_contact_id', 'name', type='char', string='Contact Name',store=False),
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
		'x_quote_est_amt': fields.function(_get_quote_est_amt, method=True, string='Estimate Amount',type='float'),#fields.float(compute='_get_quote_est_amt',string='Estimate Amount'),
		'x_probability':fields.float("Likelihood of Sales (%)"),
		'x_phonecall_ids': fields.one2many('crm.phonecall', 'x_contract_quote_id', string="Follow-ups"),
		'x_date_from':fields.function(lambda *a,**k:{}, method=True, type='date',string="Date Event"),
		'x_has_fw_pending':fields.boolean("has fw pending"),#fields.function(has_fw_pending, method=True, string='has fw pending',type='char'),
		'x_has_lead_oppr': fields.function(get_lead_id, method=True, string='has lead oppr',type='char'),#fields.char(compute='get_lead_id',string='has lead oppr'),
		'x_quote_converted':fields.boolean("Quote converted"),
		'x_last_fw_dt': fields.function(last_fw_dt, method=True, string='Last follow-up date',type='char'),#fields.date(compute='last_fw_dt', string='Last follow-up date'),
		'x_last_fw_by': fields.function(last_fw_by, method=True, string='Last follow-up by',type='char'),#fields.char(compute='last_fw_by', string='Last follow-up by'),
		'x_last_fw_desc': fields.function(last_fw_desc, method=True, string='Last follow-up comments',type='char'),#fields.char(compute='last_fw_desc', string='Last follow-up comments'),
		'x_client_comment': fields.related('partner_id', 'comment', type='text', string='Special Instruction',store=False),
		'x_status':fields.selection(config_dcs.QUOTE_STATUS, 'Status'),
		'x_stage':fields.selection(config_dcs.QUOTE_STAGE, 'Project Stage'),
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
		'x_status':'open',
    }
	_order = 'id desc'
	
	def onchange_status_quote(self, cr, uid, ids, _status, context=None):
		if _status:
			str1=dict(config_dcs.QUOTE_STATUS)[_status]#dict(self.fields_get(allfields=['x_status'])['x_status']['selection'])[_status]
			value   = {'description':str1}
			return {'value': value}
			
	def print_quotation(self, cr, uid, ids, context=None):
		'''
		This function prints the quotation (3 templates) as at 8/5/2015
		'''
		assert len(ids) == 1, 'This option should only be used for a single id at a time'
		#wf_service = netsvc.LocalService("workflow")
		#wf_service.trg_validate(uid, 'account.analytic.account', ids[0], 'quotation_sent', cr)
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
		
	def print_quotation_qweb(self, cr, uid, ids, context=None):
		assert len(ids) == 1, 'This option should only be used for a single id at a time'
		
		return self.pool['report'].get_action(cr, uid, ids, 'dincelcrm.report_quotation_report', context=context)

	def convert2opportunity(self, cr, uid, ids, context=None):
		
		lead_obj 		= self.pool.get('crm.lead')
		has_lead 		= False
		project_id 		= None
		x_name			= ""
		x_userid		= 1
		p_id			= None
		contact_id		= None
		
		for record in self.browse(cr, uid, ids, context=context):
			#has_lead 	 = record.x_has_lead_oppr
			x_project_id = record.x_project_id
			probability	 = record.x_probability
			user_id 	 = record.user_id
			partner_id	 = record.partner_id
			x_contact_id = record.x_contact_id
			if user_id:
				x_userid =user_id.id
				
			if x_project_id:
				proj_id = x_project_id.id
				proj_val= x_project_id.x_project_value
				x_name	= x_project_id.name
				
				cr.execute("select id from crm_lead where x_project_id=" + str(proj_id))
				rows = cr.fetchall()
				if len(rows) > 0:
					has_lead = True
				#else:
				#	found = "0"
			if partner_id:
				p_id	= partner_id.id
			if x_contact_id:
				contact_id	= x_contact_id.id	
				
			#if has_lead==0:
			#	has_lead = False
				
		#_logger.error("convert2opportunity:vals -" + str(has_lead)+"-proj_id" + str(proj_id)+"")	
		
		if has_lead == False and proj_id:
			vals = {
					#'x_stage_id': 1, #new
					'x_project_id': proj_id,
					'name':x_name,
					'probability': probability,
					'planned_revenue': proj_val,
					'user_id': x_userid,
					'type': 'opportunity',
					#'state':None,
					'stage_id': 1,
			}
			if p_id:
				vals['partner_id'] 	 = p_id 
			if contact_id:
				vals['x_contact_id'] = contact_id 
				
			#_logger.error("convert2opportunityvvvvvals -" + str(vals)+"")	
			
			new_id 		= lead_obj.create(cr, uid, vals, context=context)
			
			#_logger.error("convert2opportunity:new_id -" + str(new_id)+"")
			'''
			if new_id:
				view_id 		= self.pool.get('ir.ui.view').search(cr,uid,[('name', '=', 'crm.crm_case_form_view_oppor')], limit=1) 	
				
				#//view_id=277
				value = {
                    'domain': str([('id', 'in', new_id)]),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'crm.lead',
                    'view_id': view_id,
                    'type': 'ir.actions.act_window',
                    'name' : _('Opportunity'),
                    'res_id': new_id
                }
				return value'''
		else:
			raise osv.except_osv(_("Warning!"), _("Please select site address or check if already converted."))
			
		return {}
	
	def convert2quotation(self, cr, uid, ids, context=None):
		_obj = self.pool.get('account.analytic.account')
		
		_from_date 	=  datetime.datetime.strptime(str(datetime.datetime.now()),"%Y-%m-%d %H:%M:%S.%f")
		time_zone	='Australia/Sydney'
		tz 			= pytz.timezone(time_zone)
		tzoffset 	= tz.utcoffset(_from_date)
		
		dtquote 	= str((_from_date + tzoffset).strftime("%Y-%m-%d"))
		#_logger.error("quotecontract:update=datetime.now222[today[" + str(dt2)+ "][" + str(dt22)+ "]")
		vals = {
				'x_stage_id': 5, 
				'x_quote_converted':True,
				'x_date_quote': dtquote,#date.today().strftime('%Y-%m-%d'),#datetime.date.today(),
			}
		vals['name'] = self.pool.get('ir.sequence').get(cr, uid, 'quotation.number')			
		if vals['name'] == False:
			raise osv.except_osv(_("Warning!"), _("Invalid Quotation number, no sequence settings found for 'quotation.number'"))
			return
			
		for record in self.browse(cr, uid, ids, context=context):
			if record.x_project_id:
				dt = record.x_project_id.x_likely_sale_dt
				if dt:
					vals['x_likely_sale_dt'] =	dt
					
		_obj.write(cr, uid, ids, vals, context=context)
		#_logger.error("onchange1_stage_id:stage_id -" + str(vals)+"")
		new_id	= ids[0]
		
		view_id = self.pool.get('ir.ui.view').search(cr,uid,[('name', '=', 'dincelcrm.contractquote.form.view')], limit=1)
		value 	= {
                    'domain': str([('id', 'in', new_id)]),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'account.analytic.account',
                    'view_id': view_id,
                    'type': 'ir.actions.act_window',
                    'name' : _('Quotation'),
                    'res_id': new_id
                }
		return value
		#return {}
	def onchange_stage_id(self, cr, uid, ids, stage_id, context=None):
		'''_logger.error("onchange1_stage_id:stage_id -" + str(stage_id)+"")	
		if not stage_id:
			return {'value':{}}
			
		

		_obj = self.pool.get('account.analytic.account')
		vals = {
			'x_stage_id': stage_id, 
		}
		if stage_id==1:
			vals['state'] = "open"
		elif stage_id==3:	
			vals['state'] = "close"
		_obj.write(cr, uid, ids, vals, context=context)
		
		return {'value':{'x_probability': stage.probability}}'''
		return {'value':{}}
		
	def confirm_sale(self, cr, uid, ids, context=None):
		
		return {}

