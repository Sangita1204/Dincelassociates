from openerp.tools.translate import _
from openerp.osv import osv, fields
from datetime import date
from datetime import datetime
import datetime
from datetime import timedelta
import config_dcs
import openerp.addons.decimal_precision as dp
#from dateutil import parser from datetime import date
#from openerp.addons.base_status.base_state import base_state
import subprocess
from subprocess import Popen, PIPE, STDOUT
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
	
	def convert_to_sale_order(self, cr, uid, ids, context=None):
		result 		= {}	
		context 	= context or {}
		vals1 = {}
		vals = {}
		
		obj_so 	= self.pool.get('sale.order')	
		obj_soline	= self.pool.get('sale.order.line')
		
		for record in self.browse(cr, uid, ids, context=context):		
			#for record in self.browse(cr, uid, ids, context=context):		
			vals = {
					'x_quote_id': record.id,
					'x_coststate_id':record.x_proj_state.id,
					'x_project_id':record.x_project_id.id,
					'partner_id':record.partner_id.id,
					#'x_contact_id':record.x_contact_id.id,
					#'payment_term':record.x_payment_term.id,
					'user_id':record.user_id.id,
					'amount_untaxed':record.x_amt_untaxed,
					'amount_tax':record.x_amt_tax,
					'amount_total':record.x_amt_total,
					}
			if record.x_contact_id:
				vals['x_contact_id']=record.x_contact_id.id
			if record.x_payment_term:
				vals['payment_term']=record.x_payment_term.id	
			sale_order_id = obj_so.create(cr, uid, vals, context=context)
			_sn=len(record.x_quote_lines)
			
			if(_sn > 0):
				for line in record.x_quote_lines:
					vals1 ={
						'order_id':sale_order_id,
						'x_coststate_id':record.x_proj_state.id,
						'product_id':line.product_id.id,
						'x_order_length':line.item_length,
						'x_order_qty':line.item_qty,
						'x_total_lm':line.total_lm,
						'product_uom_qty':line.uom_qty,
						'price_unit':line.price_unit,
						#'tax_id':line.tax_id.id,
						'price_subtotal':line.subtotal,
					}
					if line.tax_id:
						vals1['tax_id'] = [(6, 0, [line.tax_id.id])]#tax_id has many to many relationship, contains multiple tax values as array
						
					line_id = obj_soline.create(cr, uid, vals1, context=context)
			
			view_id 		= self.pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'dincelaccount.sale.order.form')], limit=1) 	#redirect to sale order form view
			value = {
				'domain': str([('id', 'in', sale_order_id)]),
				'view_type': 'form',
				'view_mode': 'form',
				'res_model': 'sale.order',
				'view_id': view_id,
				'type': 'ir.actions.act_window',
				'name' : _('Sale Order'),
				'res_id': sale_order_id
			}
			return value
			
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
			#tot=record.x_quote_110 + record.x_quote_200+record.x_quote_base_110 + record.x_quote_base_200+record.x_quote_party_110 + record.x_quote_party_200+record.x_quote_lift_110 + record.x_quote_lift_200+record.x_quote_facade_110 + record.x_quote_facade_200
			tot=record.x_quote_total_110+record.x_quote_total_200+record.x_quote_total_155+record.x_quote_total_275
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
	def get_quote_total_155(self, cr, uid, ids, values, arg, context):
		x={}
		tot=0
		for record in self.browse(cr, uid, ids):
			tot=record.x_quote_155_q1+record.x_quote_155_q2+record.x_quote_155_q3 +record.x_quote_155_q4+record.x_quote_155_q5 
			x[record.id]=tot
		return x	
	
	def get_quote_total_275(self, cr, uid, ids, values, arg, context):
		x={}
		tot=0
		for record in self.browse(cr, uid, ids):
			tot=record.x_quote_275_q1+record.x_quote_275_q2+record.x_quote_275_q3 +record.x_quote_275_q4+record.x_quote_275_q5
			x[record.id]=tot
		return x		
	 
	def onchange_total(self, cr, uid, ids, partner_id, project_id,dt,x_other_rate, q1 = 0, q2 = 0, q3 = 0, _total_275 = 0, context = None):
		tot = q1 + q2 + q3 + _total_275 
		#if x_other_rate:
		#	self.get_rate_calculate( cr, uid, ids,project_id, x_other_rate, _total_275)	
		#else:
		#	self.get_rate_calculate( cr, uid, ids,project_id, x_other_rate, q1 + q2 + q3 + q4 )
		return self.get_rate_calculate( cr, uid, ids,partner_id, project_id,dt, x_other_rate, tot , _total_275)
		#return {'value': {'x_quote_total': tot }} 	
	
	def onchange_qty110(self, cr, uid, ids, project_id, q1 = 0, q2 = 0, q3 = 0, q4 = 0, q5 = 0, context = None):
		tot = q1 + q2 + q3 + q4 + q5 
		return {'value': {'x_quote_total_110': tot }} 	
		
	def onchange_qty200(self, cr, uid, ids, project_id, q1 = 0, q2 = 0, q3 = 0, q4 = 0, q5 = 0, context = None):
		tot = q1 + q2 + q3 + q4 + q5 
		return {'value': {'x_quote_total_200': tot }} 	
		
	def onchange_qty155(self, cr, uid, ids, project_id, q1 = 0, q2 = 0, q3 = 0, q4 = 0, q5 = 0, context = None):
		tot = q1 + q2 + q3 + q4 + q5 
		return {'value': {'x_quote_total_155': tot }} 	
		
	def onchange_qty275(self, cr, uid, ids, project_id, q1 = 0, q2 = 0, q3 = 0, q4 = 0, q5 = 0, context = None):
		tot = q1 + q2 + q3 + q4 + q5 
		return {'value': {'x_quote_total_275': tot }} 	
	def onchange_other_rate(self, cr, uid, ids,partner_id, project_id,dt, x_other_rate, _total, _total_275 = 0, context = None):
		#if x_other_rate:
		#	return self.get_rate_calculate( cr, uid, ids, project_id, x_other_rate, _total_275)
		#else:
			#_logger.error("onchange_other_rate:FFF[" + str(_total)+ "][" + str(_total_275)+ "]")	
		#	return self.get_rate_calculate( cr, uid, ids, project_id, x_other_rate, _total-_total_275)
		#(x_other_rate,x_quote_total,x_quote_total_275)
		return self.get_rate_calculate( cr, uid, ids, partner_id,project_id,dt, x_other_rate, _total,_total_275)
		
	def create(self, cr, uid, vals, context=None):
		if vals.get('name','/')=='/':
			vals['name'] = self.pool.get('ir.sequence').get(cr, uid, 'quotation.number') or '/'
		#else:
		#	vals['name'] = "lead"
		#super(sale_order,self.with_context({'mail_create_nosubscribe':True,'tracking_disable':True})).create(vals)
		#return self.pool.get('account.analytic.account').create(cr, uid, vals, context=context) or '/'
		return super(dincelcrm_quotecontract, self).create(cr, uid, vals, context=context)
		
	def mark_as_won(self, cr, uid, ids, context=None):
		for record in self.browse(cr, uid, ids):
			job_number = None
			if not record.x_job_number:
				job_number = self.pool.get('ir.sequence').get(cr, uid, 'job.number') or ''
			_str = ""
			_obj = self.pool.get('crm.case.stage')
			sids = _obj.search(cr, uid, [('name','=','Won')], context=context)
			if sids:
				_str += ", x_stage_id='%s'" %(str(sids[0]))
			if job_number:
				_str += ", x_job_number='%s'" %(str(job_number))
				
			sql="update account_analytic_account set x_status='won' %s where id='%s' " % (_str, str(record.id))
			cr.execute(sql)
	
	def send_quote_email(self, cr, uid, ids, context=None):
		compose_form_id=False
		#compose_form_id = self.pool.get('ir.ui.view').search(cr,uid,[('name', '=', 'dincelaccount.mail.compose.message.form')], limit=1)
		ctx = dict(context)
		o = self.browse(cr, uid, ids)[0] 
		
		fol_obj = self.pool.get('mail.followers')
		fol_ids = fol_obj.search(cr, uid, [
			('res_id', '=',  ids[0]),
			('res_model', '=', 'account.analytic.account'),
		], context=context)
		
		
		_ids = []
		#def_ids = []
		
		for fol in fol_obj.browse(cr, uid, fol_ids, context=context):	
			_ids.append(fol.partner_id.id)
		if o.partner_id.email:
			_ids.append(o.partner_id.id)
		if o.x_contact_id:
			_ids.append(o.x_contact_id.id)
			
			
		ctx.update({
			'default_model': 'account.analytic.account',
			'default_res_id': ids[0],
			'default_subject': "Re. %s, %s, %s " % (o.name, o.partner_id.name, o.x_project_id.name),
			'default_composition_mode': 'comment',
			'mark_as_sent':True, #see below >>> inserit class >> "accountmail_compose_message"
			#'default_contact_ids':_ids,
			'default_partner_ids':_ids,#for default selection of to email ids (follow ups)
		})
		
		return {
			'name': _('Compose Email'),
			'type': 'ir.actions.act_window',
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'mail.compose.message',
			'views': [(compose_form_id, 'form')],
			'view_id': compose_form_id,
			'target': 'new',#current',#'target': 'new',
			'context': ctx,
		}
		
	def get_rate_calculate(self, cr, uid, ids,partner_id, project_id,dt_sale, x_other_rate, tot = 0, tot_275=0, context = None):
		
		rate1 = 0
		rate2 = 0
		rate3 = 0	
		grp="default"
		grp_rate=False
		if x_other_rate:
			tot1 = tot_275
			grp="P275"
		else:	
			tot1 = tot-tot_275
			grp="default"
		
		rate_obj 	= self.pool.get('dincelcrm.customer.rate') 
		state_id = None
		_xtracost=0.0
		rate_id = None
		if project_id:
			obj 	= self.pool.get('res.partner').browse(cr,uid,project_id,context=context)
			if obj.state_id:
				state_id =obj.state_id.id
				if obj.state_id.x_warehouse_id:
					_xtracost=obj.state_id.x_warehouse_id.x_cost_xtra 
		grp_rate, _rate_cod, _rate_acct=rate_obj.find_rate_group(cr, uid, partner_id, grp,dt_sale, context=context)
		if grp_rate==True:
			_rate_acct = float(_rate_acct)
			_rate_cod = float(_rate_cod)
			if _rate_acct>0.0:
				rate1 = _rate_acct+float(_xtracost) #EOM
				rate2 = _rate_acct+float(_xtracost)	#14 Days
			if _rate_cod>0.0:	
				rate3 = _rate_cod+float(_xtracost)	#COD
		else:
			sql = "select rate1,rate2,rate3,rate_other_ac,rate_other_cod,id from dincelcrm_quote_rates where %s between from_val and to_val" % tot1
			cr.execute(sql)
			rows 	= cr.dictfetchall()
			if len(rows)==0:
				rate1 = 0
				rate2 = 0
				rate3 = 0	
			else:
				for row1 in rows:
					rate_id = str(row1['id'])
					if x_other_rate:
						rate1 = float(row1['rate_other_ac'])
						rate3 = float(row1['rate_other_cod'])
						#_logger.error("get_rate_calculate111[" + str(rate1)+ "][" + str(sql)+ "]")	
					else:
						rate1 = float(row1['rate1'])
						rate2 = float(row1['rate2'])
						rate3 = float(row1['rate3'])
						#_logger.error("get_rate_calculate222[" + str(rate1)+ "][" + str(sql)+ "]")	
				if state_id and rate_id:
					sql = "select rate1,rate2,rate3,id from dincelcrm_quote_state_rates where state_id='%s' and quote_rate_id='%s'" % (str(state_id),rate_id)
					cr.execute(sql)
					rows2 = cr.fetchall()
					for row2 in rows2:
						rate1 += float(row2[0])
						rate2 += float(row2[1])
						rate3 += float(row2[2])
		return {'value': {'x_quote_total': tot, 'x_rate1': rate1, 'x_rate2': rate2, 'x_rate3': rate3 }} 
		
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
			if record.x_status and record.x_status != "" and record.x_status != "open":
				_obj = self.pool.get('crm.case.stage')
				sids = None
				if record.x_status == "won":
					sids = _obj.search(cr, uid, [('name','=','Won')], context=context)
				else:
					sids = _obj.search(cr, uid, [('name','=','Lost')], context=context)
				#@_logger.error("x_phonecall_idsx_phonecall_ids["+str(sids)+"]")
				if sids:
					sql="update account_analytic_account set x_stage_id='%s' where id='%s' " % (str(sids[0]), str(record.id))	
					#_logger.error("x_phonecall_idsx_phonecall_idssql["+str(sql)+"]")
					cr.execute(sql)	
					
			if record.partner_id and record.x_project_id:
				self.pool.get("res.partner").write_relation_if(cr, uid, record.partner_id.id, record.x_project_id.id, context=context)
				
			if record.x_deposit_percent and record.x_quoted_amount:
				deposit = round(float(record.x_deposit_percent)*float(record.x_quoted_amount)/100,2)
				sql="update account_analytic_account set x_deposit_amount='%s' where id='%s' " % (deposit, str(record.id))
				_logger.error("x_deposit_percentsql111["+str(sql)+"]")
				cr.execute(sql)
			
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
				
			if obj.state_id and obj.state_id.code != 'NSW':
				state_code = obj.state_id.code
			else:
				state_code = 'NSW'
				
			value['x_intro_text'] = self.update_acc_to_state(cr, uid, 'intro', state_code)
			value['x_description'] = self.update_acc_to_state(cr, uid, 'description', state_code)
			value['x_engineering_service'] = self.update_acc_to_state(cr, uid, 'engineering_latest', state_code)
			value['x_structural_engineering_service'] = self.update_acc_to_state(cr, uid, 'engineering_structural', state_code)
			value['x_stormwater_engineering_service'] = self.update_acc_to_state(cr, uid, 'engineering_stormwater', state_code)
			value['x_civil_engineering_service'] = self.update_acc_to_state(cr, uid, 'engineering_civil', state_code)
			value['x_mechanical_engineering_service'] = self.update_acc_to_state(cr, uid, 'engineering_mechanical', state_code)
			value['x_construction_engineering_service'] = self.update_acc_to_state(cr, uid, 'engineering_construction', state_code)
			value['x_shop_engineering_service'] = self.update_acc_to_state(cr, uid, 'engineering_shop', state_code)
			value['x_payment_description'] = self.update_acc_to_state(cr, uid, 'payment', state_code)
			value['x_documentation'] = self.update_acc_to_state(cr, uid, 'documentation', state_code)
			value['x_variations'] = self.update_acc_to_state(cr, uid, 'variations', state_code)
			value['x_service_exclusion'] = self.update_acc_to_state(cr, uid, 'service_exclusion', state_code)
			value['x_fee_summary'] = self.update_acc_to_state(cr, uid, 'fee_summary', state_code)
			
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
		
	def onchange_partner(self, cr, uid, ids, partner_id,project_id,  context=None):
		
		if partner_id:
			val={}
			part=self.pool.get('res.partner').browse(cr,uid,partner_id, context)
			if part.property_payment_term:
				val['x_payment_term']=part.property_payment_term.id 
			if part.user_id:
				val['user_id']=part.user_id.id 	
			return {'value':val}	
			
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
					if rows[0] and str(rows[0])!="" and str(rows[0])!="None":
						_from_date 	=  datetime.datetime.strptime(rows[0],"%m/%d/%Y %I:%M:%S %p")
						#_form_date = datetime.today()
						time_zone	='Australia/Sydney'
						tz 			= pytz.timezone(time_zone)
						tzoffset 	= tz.utcoffset(_from_date)
						txt 		= str((_from_date + tzoffset).strftime("%d/%m/%Y"))
					else:
						txt = "-"
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
					if rows[0] and str(rows[0])!="" and str(rows[0])!="None":
						cr.execute("select p.name from res_users r,res_partner p where r.partner_id=p.id and r.id=" + str(rows[0]) + " ")
						rows1 	= cr.fetchone()
						if rows1 == None or len(rows1) == 0:
							txt 	= "-"
						else:	
							txt 	= rows1[0]
					else:
						txt="-"
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
	def _amount_all_wrapper(self, cr, uid, ids, field_name, arg, context=None):
		""" Wrapper because of direct method passing as parameter for function fields """
		return self._amount_all(cr, uid, ids, field_name, arg, context=context)

	def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
		#cur_obj = self.pool.get('res.currency')
		res = {}
		for order in self.browse(cr, uid, ids, context=context):
			res[order.id] = {
				'x_amt_untaxed': 0.0,
				'x_amt_tax': 0.0,
				'x_amt_total': 0.0,
				'x_quoted_amount':0.0,
			}
			val = val1 = 0.0
			
			for line in order.x_quote_lines:
				if(line.x_service_type == 'fixed'):#for variable 
					val1 += round(line.subtotal,2)
					if line.tax_id:
						if line.tax_id.type=="percent":
							val+=round((line.tax_id.amount*round(line.subtotal,2)),2)
						
				#val += self._amount_line_tax(cr, uid, line, context=context)
			res[order.id]['x_amt_tax'] = round(val,2)
			res[order.id]['x_amt_untaxed'] =  round(val1,2)
			res[order.id]['x_amt_total'] = round((val+val1),2)
			res[order.id]['x_quoted_amount'] = round(val1,2)
			
		return res
		
	def _edit_rate(self, cr, uid, ids, values, arg, context):
		x={}
		_edit=False
		for record in self.browse(cr, uid, ids):
			cr.execute("select res_id from ir_model_data where name='group_rate_editor' and model='res.groups'") #+ str(record.id))
			
			rows = cr.fetchone()
			if rows == None or len(rows)==0:
				_edit=False
			else:
				if rows[0]:#!=None:
					sql ="select 1 from  res_groups_users_rel where gid='%s' and uid='%s'" % (str(rows[0]), str(uid))
					cr.execute(sql)
					rows1 = cr.fetchone()
					if rows1 and len(rows1)>0:
						_edit=True
				#if rows == None or len(rows)==0:
			x[record.id]=_edit 
		return x
		
	def _get_items(self, cr, uid, ids, context=None):
		result = {}
		for line in self.pool.get('dincelmrp.quote.line').browse(cr, uid, ids, context=context):
			result[line.quote_id.id] = True
		return result.keys()
		
	def _get_total_amt(self, cr, uid, ids, values, arg, context):
		x={}
		for record in self.browse(cr, uid, ids):
			x[record.id] = record.x_amt_untaxed + record.x_amt_tax 
		return x
	
	def cancel_quotation(self, cr, uid, ids, context=None):
		self.pool.get('account.analytic.account').write(cr, uid, ids, {'state': 'cancel'})
		return True
	
	def approve_quotation(self, cr, uid, ids, context=None):
		
		#compose_form_id=False
		compose_form_id = self.pool.get('ir.ui.view').search(cr,uid,[('name', '=', 'dincelcrm.mail.compose.message.form')], limit=1)
		
		ctx = dict(context)
		o = self.browse(cr, uid, ids)[0]
		
		
		fol_obj = self.pool.get('mail.followers')
		fol_ids = fol_obj.search(cr, uid, [
			('res_id', '=',  ids[0]),
			('res_model', '=', 'account.analytic.account'),
		], context=context)
		
		_ids = []
		
		ir_model_data = self.pool.get('ir.model.data')
		template_id = ir_model_data.get_object_reference(cr, uid, 'dincelcrm', 'approved_reply_email_template')[1]
		#template_id = ir_model_data.get_object_reference(cr, uid, 'dincelaccount', 'email_template_edi_saleorder_invoice')[1]
		
		ctx.update({
			'default_model': 'account.analytic.account',
			'default_res_id': ids[0],
			'default_use_template': bool(template_id),
			'default_template_id': template_id,
			'default_subject': "Quotation %s is Approved. " % (o.name),
			#'default_subject': "",
			'default_composition_mode': 'comment',
			'mark_as_sent':False, #see below >>> inserit class >> "accountmail_compose_message"
			'default_approved':True,
			'mark_as_approved':True,
			#'default_contact_ids':_ids,
			'default_partner_ids':_ids,#for default selection of to email ids (follow ups)
		})
		#self.pool.get('account.analytic.account').write(cr, uid, ids, {'state': 'need_approval'})
		return {
			'name': _('Compose Email'),
			'type': 'ir.actions.act_window',
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'mail.compose.message',
			'views': [(compose_form_id, 'form')],
			'view_id': compose_form_id,
			'target': 'new',#current',#'target': 'new',
			'context': ctx,
		}
		
	def suggest_edit(self, cr, uid, ids, context=None):
		
		#compose_form_id=False
		compose_form_id = self.pool.get('ir.ui.view').search(cr,uid,[('name', '=', 'dincelcrm.mail.compose.message.form')], limit=1)
		
		ctx = dict(context)
		o = self.browse(cr, uid, ids)[0]
		
		
		fol_obj = self.pool.get('mail.followers')
		fol_ids = fol_obj.search(cr, uid, [
			('res_id', '=',  ids[0]),
			('res_model', '=', 'account.analytic.account'),
		], context=context)
		
		_ids = []
		
		ir_model_data = self.pool.get('ir.model.data')
		template_id = ir_model_data.get_object_reference(cr, uid, 'dincelcrm', 'modification_request_email_template')[1]
		#template_id = ir_model_data.get_object_reference(cr, uid, 'dincelaccount', 'email_template_edi_saleorder_invoice')[1]
		
		ctx.update({
			'default_model': 'account.analytic.account',
			'default_res_id': ids[0],
			'default_use_template': bool(template_id),
			'default_template_id': template_id,
			'default_subject': "Quotation %s Requires Modification " % (o.name),
			#'default_subject': "",
			'default_composition_mode': 'comment',
			'mark_as_sent':False, #see below >>> inserit class >> "accountmail_compose_message"
			'default_draft':True,
			'mark_as_draft':True,
			#'default_contact_ids':_ids,
			'default_partner_ids':_ids,#for default selection of to email ids (follow ups)
		})
		#self.pool.get('account.analytic.account').write(cr, uid, ids, {'state': 'need_approval'})
		return {
			'name': _('Compose Email'),
			'type': 'ir.actions.act_window',
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'mail.compose.message',
			'views': [(compose_form_id, 'form')],
			'view_id': compose_form_id,
			'target': 'new',#current',#'target': 'new',
			'context': ctx,
		}
	
	
	def send_approval_request(self, cr, uid, ids, context=None):
		#compose_form_id=False
		compose_form_id = self.pool.get('ir.ui.view').search(cr,uid,[('name', '=', 'dincelcrm.mail.compose.message.form')], limit=1)
		
		ctx = dict(context)
		o = self.browse(cr, uid, ids)[0]
		
		_ids = []
		
		'''
		gid = self.pool.get('res.groups').search(cr,uid,[('name', '=', 'Group Super User Quotation')], limit=1)
		user_id = self.pool.get('res.users').search(cr,uid,[('groups_id', '=', gid)]) 
		for user_o in user_id:
			_user_obj = self.pool.get('res.users').browse(cr,uid,user_o,context=context)
			_ids.append(_user_obj.partner_id.id)
		'''
		
		user_id = self.pool.get('res.users').search(cr,uid,[],context=context)
		for user_o in user_id:
			group_id = self.pool.get('res.users').has_group(cr, user_o, 'base.admin_user_quotation')
			#_logger.error("asasasasaasas111111["+str(user_o)+"]["+str(group_id)+"]")
			if group_id:
				_user_obj = self.pool.get('res.users').browse(cr,uid,user_o,context=context)
				_ids.append(_user_obj.partner_id.id)
		
		ir_model_data = self.pool.get('ir.model.data')
		template_id = ir_model_data.get_object_reference(cr, uid, 'dincelcrm', 'approval_request_email_template')[1]
		
		ctx.update({
			'default_model': 'account.analytic.account',
			'default_res_id': ids[0],
			'default_use_template': bool(template_id),
			'default_template_id': template_id,
			'default_subject': "Quotation %s Needs Approval " % (o.name),
			#'default_subject': "",
			'default_composition_mode': 'comment',
			'mark_as_sent':False, #see below >>> inserit class >> "accountmail_compose_message"
			'default_need_approval':True,
			'mark_need_approval':True,
			'default_partner_ids':[''],#for default selection of to email ids (follow ups)
			'default_contact_ids':[''],#for default selection of to email ids (follow ups)
			'domain_contact_ids':[_ids],
		})
		#self.pool.get('account.analytic.account').write(cr, uid, ids, {'state': 'need_approval'})
		return {
			'name': _('Compose Email'),
			'type': 'ir.actions.act_window',
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'mail.compose.message',
			'views': [(compose_form_id, 'form')],
			'view_id': compose_form_id,
			'target': 'new',#current',#'target': 'new',
			'context': ctx,
		}
		
	def get_deposit(self, cr, uid, ids, amt, percent, context=None):
		result = {}
		deposit = 0.0
		if amt and percent:
			deposit = round(float(amt)*float(percent)/100,2)
			result['x_deposit_amount'] = deposit
		#_logger.error("set_total_quote111["+str(amt)+"]["+str(percent)+"]["+str(deposit)+"]")
		return {'value': result}
		
	def update_acc_to_state(self, cr, uid, arg1, arg2=None):
		template = self.pool.get('dincelcrm.text.template')
		context=None
		args = [('name','=',str(arg1))]
		ret = ''
		
		if arg2 and (arg2 == 'VIC' or arg2 == 'QLD'):
			args.append(('state_code', '=', str(arg2)))
		else:
			args.append(('state_code', '=', 'NSW'))
			
		intro = template.search(cr, uid, args, context=context)
		_intro = template.browse(cr, uid, intro)
		if _intro:
			return _intro.text_description
		else:
			return ret
	
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
		'x_quote_total_155': fields.function(get_quote_total_155, method=True, string='Total 155',type='integer'),
		'x_quote_total_275': fields.function(get_quote_total_275, method=True, string='Total 275',type='integer'),
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
		'x_rate_drawing':fields.float("Drawing Dicsount"),
		'x_project':fields.char("Project",size=100),
		'x_site_address':fields.char("Site Address",size=100),
		'x_likely_sale_dt':fields.date("Likely Sale Date"),
		'x_edit_rate': fields.function(_edit_rate, method=True, string='Edit Rate',type='boolean'),
		'x_projecttype_ids' : fields.many2many('dincelcrm.projecttype', 'contract_rel_projecttype', 'object_id', 'contract_projecttype_id', string = "Type of Project"),
		'x_project_id': fields.many2one('res.partner','Project / Site'),
		'x_proj_val': fields.related('x_project_id', 'x_project_value', type='float', string='Project Value',store=False),
		'x_proj_name': fields.related('x_project_id', 'name', type='char', string='Project Name',store=False),
		'x_proj_zip': fields.related('x_project_id', 'zip', type='char', string='Project Postcode',store=False),
		'x_source_id': fields.related('x_project_id', 'x_source_id',  string='Lead Source', type="many2one", relation="dincelcrm.leadsource",store=False),
		'x_market_wall_id': fields.related('x_project_id', 'x_market_wall_id',  string='Specified Wall', type="many2one", relation="dincelcrm.market.wall.type",store=False),
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
		'x_stage_id': fields.many2one('crm.case.stage','Stage',track_visibility='onchange'),
		'x_stage_value': fields.related('x_stage_id', 'name', type='char', string='Stage Value',store=False), 
		'x_transport_rate_id': fields.many2one('dincelcrm.quote.transport.rates','Transport Components'),
		'x_wall_type_id1': fields.many2one('dincelcrm.quote.wall.type','Wall 1'),
		'x_wall_type_id2': fields.many2one('dincelcrm.quote.wall.type','Wall 2'),
		'x_wall_type_id3': fields.many2one('dincelcrm.quote.wall.type','Wall 3'),
		'x_wall_type_id4': fields.many2one('dincelcrm.quote.wall.type','Wall 4'),
		'x_wall_type_id5': fields.many2one('dincelcrm.quote.wall.type','Wall 5'),
		'x_lead_id': fields.many2one('crm.lead','Lead Reference'),
		'x_manager': fields.many2one('res.users','Manager', domain=lambda self: [( "groups_id", "=", self.env.ref( "base.admin_user_quotation" ).id )]),
		'x_date_quote': fields.date("Quote Date"),
		'x_proj_state':fields.related('x_project_id', 'state_id', string="Project State", type="many2one", relation="res.country.state", store=False),
		'x_quote_est_amt': fields.function(_get_quote_est_amt, method=True, string='Estimate Amount',type='float'),#fields.float(compute='_get_quote_est_amt',string='Estimate Amount'),
		'x_probability':fields.float("Likelihood of Sales (%)"),
		'x_phonecall_ids': fields.one2many('crm.phonecall', 'x_contract_quote_id', string="Follow-ups"),
		'x_date_from':fields.function(lambda *a,**k:{}, method=True, type='date',string="Date Event"),
		'x_has_fw_pending':fields.boolean("has fw pending"),#fields.function(has_fw_pending, method=True, string='has fw pending',type='char'),
		'x_has_lead_oppr': fields.function(get_lead_id, method=True, string='has lead oppr',type='char'),#fields.char(compute='get_lead_id',string='has lead oppr'),
		'x_quote_converted':fields.boolean("Quote converted"),
		
		
		'x_intro_text' : fields.html('Intro Text'),
		'x_show_intro_text' : fields.boolean("Show intro text?"),
		'x_description' : fields.html('Description'),
		'x_show_description' : fields.boolean("Show description?"),
		
		'x_engineering_service' : fields.html('Engineering Service'),
		'x_show_eng_service' : fields.boolean("Show Engineering Service?"),
		
		'x_structural_engineering_service' : fields.html('Structural Engineering'),
		'x_show_eng_service_2a' : fields.boolean("Show Structural Engineering?"),
		
		#'x_stormwater_engineering_service' : fields.html('Stormwater Engineering'),
		#'x_show_eng_service_2b' : fields.boolean("Show Stormwater Engineering?"),
		
		'x_construction_engineering_service' : fields.html('Construction Service'),
		'x_show_eng_service_2b' : fields.boolean("Show Construction Service?"),
		
		'x_civil_engineering_service' : fields.html('Civil Engineering'),
		'x_show_eng_service_2c' : fields.boolean("Show Civil Engineering?"),
		
		'x_mechanical_engineering_service' : fields.html('Mechanical Engineering'),
		'x_show_eng_service_2d' : fields.boolean("Show Mechanical Engineering?"),
		
		#'x_construction_engineering_service' : fields.html('Construction Service'),
		#'x_show_eng_service_2e' : fields.boolean("Show Construction Service?"),
		
		'x_stormwater_engineering_service' : fields.html('Stormwater Engineering'),
		'x_show_eng_service_2e' : fields.boolean("Show Stormwater Engineering?"),
		
		'x_shop_engineering_service' : fields.html('Shop Drawing'),
		'x_show_eng_service_2f' : fields.boolean("Show Shop Drawing?"),
		
		'x_show_payment_desc' : fields.boolean("Show payment description?"),
		'x_payment_description' : fields.html('Payments'),
		
		'x_show_documentation' : fields.boolean("Show Documentation?"),
		'x_documentation' : fields.html('Documentation'),
		
		'x_show_variations' : fields.boolean("Show Variations?"),
		'x_variations' : fields.html('Variations'),
		
		'x_show_service_exclusion' : fields.boolean("Show service exclusions?"),
		'x_service_exclusion' : fields.html('Service Exclusions'),
		'x_fee_summary':fields.html("Fee Summary"),
		
		#'x_quoted_amount':fields.float("Quoted Amount"),
		
		'x_quoted_amount':fields.function(_amount_all_wrapper, digits_compute=dp.get_precision('Account'), string='Amount Quoted',
            store={
                'account.analytic.account': (lambda self, cr, uid, ids, c={}: ids, ['x_quote_lines'], 10),
                'dincelmrp.quote.line': (_get_items, ['price_unit', 'item_qty', 'tax_id', 'uom_qty'], 10),
            },
            multi='sums', help="The total amount"),
			
		'x_deposit_percent':fields.float("% Deposit"),
		'x_deposit_amount':fields.float("Deposit Amount"),
		
		'x_project_name':fields.char("Project Name", size=300),
		'x_job_number':fields.char("Job Number", size=20),
		
		'state': fields.selection([	#>>overwrite the status....for labeling etc...
			('open', 'Open'),
			('need_approval','Need Approval'),
			('approved', 'Approved'),
			('sent', 'Sent'),
			('revised', 'Revised'),
			('cancel', 'Cancelled'),
			('done', 'Done'),
			], 'Status', readonly=True, copy=False, help="Gives the status of the Quotations.", select=True, track_visibility='onchange'),
		
		
		
		'x_last_fw_dt': fields.function(last_fw_dt, method=True, string='Last follow-up date',type='char'),#fields.date(compute='last_fw_dt', string='Last follow-up date'),
		'x_last_fw_by': fields.function(last_fw_by, method=True, string='Last follow-up by',type='char'),#fields.char(compute='last_fw_by', string='Last follow-up by'),
		'x_last_fw_desc': fields.function(last_fw_desc, method=True, string='Last follow-up comments',type='char'),#fields.char(compute='last_fw_desc', string='Last follow-up comments'),
		'x_client_comment': fields.related('partner_id', 'comment', type='text', string='Special Instruction',store=False),
		'x_status':fields.selection(config_dcs.QUOTE_STATUS, 'Status', track_visibility='onchange'),
		'x_stage':fields.selection(config_dcs.QUOTE_STAGE, 'Project Stage'),
		'x_other_rate':fields.boolean("275mm Only Rate"),
		'x_sent':fields.boolean("Email Sent"),
		'x_quote_lines': fields.one2many('dincelmrp.quote.line', 'quote_id', string="Quote Lines"),
		'x_schedule_ids': fields.one2many('dincelcrm.quote.schedule', 'quote_id', string="Schedules"),
		'x_amt_untaxed':fields.function(_amount_all_wrapper, digits_compute=dp.get_precision('Account'), string='Untaxed Amount',
            store={
                'account.analytic.account': (lambda self, cr, uid, ids, c={}: ids, ['x_quote_lines'], 10),
                'dincelmrp.quote.line': (_get_items, ['price_unit', 'item_qty', 'tax_id', 'uom_qty'], 10),
            },
            multi='sums', help="The amount without tax."),
		'x_amt_tax':fields.function(_amount_all_wrapper, digits_compute=dp.get_precision('Account'), string='Tax Amount',
            store={
                'account.analytic.account': (lambda self, cr, uid, ids, c={}: ids, ['x_quote_lines'], 10),
                'dincelmrp.quote.line': (_get_items, ['price_unit', 'item_qty', 'tax_id', 'uom_qty'], 10),
            },
            multi='sums', help="The tax amount."),
		'x_amt_total': fields.function(_amount_all_wrapper, digits_compute=dp.get_precision('Account'), string='Total',
            store={
                'account.analytic.account': (lambda self, cr, uid, ids, c={}: ids, ['x_quote_lines'], 10),
                'dincelmrp.quote.line': (_get_items, ['price_unit', 'item_qty', 'tax_id', 'uom_qty'], 10),
            },
            multi='sums', help="The total amount."),
		'x_comments': fields.text('Comments'),	
	}
	_defaults={
		'x_is_quote': False, #set to true at the time of create....in xml file....
		'x_sent': False,
		'date': fields.date.context_today, #time.strftime('%Y-%m-%d'),
		'x_date_quote': fields.date.context_today, #time.strftime('%Y-%m-%d'),
		'x_rate_accs1': 3.0, 
		'x_rate_accs2': 3.0,
		'x_rate_accs3': 3.0,
        'x_rate_trans1': 2.5, 
		'x_rate_trans2': 2.5,
		'x_rate_trans3': 2.5,
		'x_probability': 22.0,
		'x_rate_drawing': 0.0,
		'x_quote_converted':'t',
		'x_drawing_txt': "DRAWINGS: Set out and components list - Deposit required prior to commencement. (optional) $2.00 per m2 ex GST",
		'x_transport_txt': "TRANSPORTATION: Minimum quantity 125m2 - Sydney metro areas",
		'user_id': lambda obj, cr, uid, context: uid,
        'name': lambda obj, cr, uid, context: '/',
		'x_status':'open',
		#'x_other_rate':True,
		
		'x_show_intro_text':True,
		'x_show_description':True,
		'x_show_eng_service':True,
		'x_show_payment_desc':True,
		'x_show_documentation':True,
		'x_show_variations':True,
		'x_show_service_exclusion':True,
		'state':'open',
    }
	_order = 'id desc'
	
	def button_dummy(self, cr, uid, ids, context=None):
		res = {}
		for order in self.browse(cr, uid, ids, context=context):
			res[order.id] = {
				'x_amt_untaxed': 0.0,
				'x_amt_tax': 0.0,
				'x_amt_total': 0.0,
			}
			val = val1 = 0.0
			
			for line in order.x_quote_lines:
				if(line.x_service_type == 'fixed'):#for variable 
					val1 += round(line.subtotal,2)
					if line.tax_id:
						if line.tax_id.type=="percent":
							val+=round((line.tax_id.amount*round(line.subtotal,2)),2)
			
			x_quoted_amount = round(val1,2)
			
			if(order.x_deposit_percent):
				x_deposit_amount = round(float(x_quoted_amount)*float(order.x_deposit_percent)/100,2)
				cr.execute("update account_analytic_account set x_quoted_amount=%s, x_deposit_amount=%s where id=%s" % (x_quoted_amount, x_deposit_amount, order.id))
		return True
		
	def onchange_status_quote(self, cr, uid, ids, _status, context=None):
		if _status:
			str1=dict(config_dcs.QUOTE_STATUS)[_status]#dict(self.fields_get(allfields=['x_status'])['x_status']['selection'])[_status]
			value   = {'description':str1}
			return {'value': value}
	@api.multi 		
	def print_quotation_lines(self):
		context = self._context.copy() 
		url=self.env['dincelaccount.config.settings'].report_preview_url("quote", self.id)		
		if url:#rows and len(rows) > 0:
			#_logger.error("print_quotation_linesprint_quotation_lines.g" +str(url))
			o=self.browse(self.id)
			fname=""+str(o.name)+".pdf"
			save_path="/var/tmp/odoo/quote"
			
			process=subprocess.Popen(["wkhtmltopdf", 
						'--margin-top','1', 
						'--margin-left','1', 
						'--margin-right','1', 
						'--margin-bottom','1', url, save_path+"/"+fname],stdin=PIPE,stdout=PIPE)
			
			out, err = process.communicate()
			if process.returncode not in [0, 1]:
				raise osv.except_osv(_('Report (PDF)'),
									_('Wkhtmltopdf failed (error code: %s). '
									'Message: %s') % (str(process.returncode), err))
		
			return {
					'name': 'Report',
					'res_model': 'ir.actions.act_url',
					'type' : 'ir.actions.act_url',
					'url': '/web/binary/download_file?model=sale.order&field=datas&id=%s&path=%s&filename=%s' % (str(o.id),save_path,fname),
					'context': context}
		
	def print_quotation_new(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		datas = {'ids': context.get('active_ids', [])}
		datas['form']  = self.read(cr, uid, ids, context=context)[0]
		return self.pool['report'].get_action(cr, uid, [], 'crm.report_quotation_new', data=datas, context=context)		
	
	def print_quotation_new_pdf(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		name="Q111"	
		datas = { 'name': name,'ids': context.get('active_ids', [])}
		datas['form']  = self.read(cr, uid, ids, context=context)[0]
		return self.pool['report'].get_action(cr, uid, [], 'crm.report_quotation_new_pdf', data=datas, context=context)				
		#return self.pool['report'].get_action(cr, uid, [], 'purchase.report_purchase_invoice_pdf', data=datas, context=context)	
	def print_quotation_pdf_test(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		name="Q111"	
		datas = {'name': name,'ids': context.get('active_ids', [])}
		#for record in self.browse(cr, uid, ids, context=context):
		#	name = record.name
		#	#datas['form'] =record
		obj = self.read(cr, uid, ids, context=context)[0]
		name=obj['name']
		#form  = self.read(cr, uid, ids, context=context)
		datas['form'] = obj
		#datas['form']  = self.read(cr, uid, ids, context=context)[0]
		#return self.pool['report'].get_action(cr, uid, [], 'crm.report_quotation_new_pdf', data=datas, context=context)	
		reportname="crm.report_quotation_new_pdf"
		#_logger.info("%s : %s" % (name, obj))
		#return self.download_qweb_pdf(cr, uid, ids, name=name, reportname=rptname, datas=datas, context=context)	
		#return self.pool['report'].get_action(cr, uid, [],rptname, data=datas, context=context)	
		#pdf1 = self.pool.get('ir.actions.report.xml').render_report(cr,uid,ids,reportname,datas,context=context)
		return self.pool['report'].get_action(cr, uid, [],reportname, data=datas, context=context)	
		return True
		
	def print_quotation_pdf(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		name="Q111"	
		for record in self.browse(cr, uid, ids, context=context):
			name = record.name
		datas = {'name': name,'ids': context.get('active_ids', [])}
		#form  = self.read(cr, uid, ids, context=context)
		#datas['form'] = form[0]
		datas['form']  = self.read(cr, uid, ids, context=context)[0]
		#return self.pool['report'].get_action(cr, uid, [], 'crm.report_quotation_new_pdf', data=datas, context=context)
		rptname="crm.report_quotation_new"
		#return self.download_qweb_pdf(cr, uid, ids, name=name, reportname=rptname, datas=datas, context=context)	
		#return self.pool['report'].get_action(cr, uid, [],rptname, data=datas, context=context)
		return self.pool['report'].get_action(cr, uid, [], 'crm.report_quotation_new_pdf', data=datas, context=context)	
		
		
	def download_qweb_pdf(self, cr, uid, ids, name, reportname, datas, context=None):
		_logger.info("datas[%s]" % (datas))
		#reportname="dincelcrm.report_quote_estimate"
		pdf1 = self.pool.get('ir.actions.report.xml').render_report(cr,uid,ids,reportname,datas,context=context)
		_logger.info("pdf1[%s]" % (pdf1))
		fname		=""+str(name)+".pdf"
		save_path	="/var/tmp/odoo/sale"
		file_quote	=save_path+"/"+fname
		
		pdf1tmp 	= pdf1[0]
		
		with open(file_quote, "w+") as _file:
			_file.write("%s" % pdf1tmp)		
			
		
		return {
				'name': 'Report',
				'res_model': 'ir.actions.act_url',
				'type' : 'ir.actions.act_url',
				'url': '/web/binary/download_file?model=sale.order&field=datas&id=%s&path=%s&filename=%s' % (str(ids[0]), save_path, fname),
				'context': context}
				
		#return self.pool['report'].get_action(cr, uid, [], 'purchase.report_purchase_invoice_pdf', data=datas, context=context)	
		
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
		other_rate=False
		for record in self.browse(cr, uid, ids, context=context):
			name = record.name
			rate1 = record.x_is_rate1
			rate2 = record.x_is_rate2
			rate3 = record.x_is_rate3
			other_rate= record.x_other_rate
		if other_rate:
			reportname="account.analytic.account.quote_275"
		else:	
			reportname="account.analytic.account.quote_v2"
		'''if rate1 == True and rate3 == False:	
			reportname="account.analytic.account.quote_rate1"
		elif rate1 == False and rate3 == True:
			reportname="account.analytic.account.quote_rate3"
		elif rate2 == True:
			reportname="account.analytic.account.quote_rate2"
		else:
			reportname="account.analytic.account.quote"'''
		return {'type': 'ir.actions.report.xml', 'report_name': reportname, 'datas': datas, 'name': name , 'nodestroy': True}	
		#return {'type': 'ir.actions.report.xml', 'report_name': 'account.analytic.account.quote', 'datas': datas, 'name': name , 'nodestroy': True}
		
	def print_quotation_qweb(self, cr, uid, ids, context=None):
		name="Q111"	
		datas = { 'name': name,'ids': context.get('active_ids', [])}
		datas['form']  = self.read(cr, uid, ids, context=context)[0]
		#return self.pool['report'].get_action(cr, uid, [], 'crm.report_quotation_new_pdf', data=datas, context=context)
		#_logger.error("print_quotation_qweb111["+str(datas)+"]["+str(ids)+"]")
		
		return self.pool['report'].get_action(cr, uid, [], 'crm.report_quotation_report_new', data=datas, context=context)
		
		#assert len(ids) == 1, 'This option should only be used for a single id at a time'
		#ret_val = self.pool['report'].get_action(cr, uid, ids, 'dincelcrm.report_quotation_report1', context=context)
		#_logger.error("print_quotation_qweb111["+str(ret_val)+"]")
		#return ret_val
	
	
	
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
	def change_payment_term(self, cr, uid, ids, proj_id=False,partner_id=False, payment_term = False, lines= False,dt_sale=False, context=None):
		
		rate		= 0.0
		
		product_obj = self.pool.get('product.product')
		term_obj 	= self.pool.get('account.payment.term')
		
		rate_obj 	= self.pool.get('dincelcrm.customer.rate')
		term_obj 	= term_obj.browse(cr, uid, payment_term)
		code 	 	= term_obj.x_payterm_code
		
		
		line_obj = self.pool.get('dincelmrp.quote.line')
		
		ac_rate=False
		cost_xtra=0.0
		 
		rate_id=0			
		if code:	
			rate_id = rate_obj.find(cr, uid, dt_sale, partner_id, context=context)
			if rate_id:
				rate_id	 = rate_id[0]
				rate1 =  rate_obj.browse(cr, uid, rate_id)
				if rate1:
					if code == "COD" or code=="immediate":
						rate = rate1.rate_cod
					else:
						rate = rate1.rate_acct
						ac_rate=True
		if proj_id:
			#if proj_id:
			sql="""select r.rate1,r.rate2,r.rate3 from 
						dincelcrm_location_rates r ,res_country_state s, res_partner p
						where r.warehouse_id=s.x_warehouse_id and s.id=p.state_id and p.id='%s' """ % (proj_id)
			cr.execute(sql)
			rows2 = cr.fetchall()
			for row2 in rows2:
				if row2[0]:
					cost_xtra = float(row2[0])
					rate+=cost_xtra
		quote_line = []
		#_logger.error("onchange1_stage_id:stage_id %s cost_xtra[%s] " % (rate,cost_xtra))
		 
		
		for line in lines:
			# create    (0, 0,  { fields })
			# update    (1, ID, { fields })
			if line[0] in [0, 1]:
				prod = None
				if line[2].get('product_id'):
					prod = product_obj.browse(cr, uid, line[2]['product_id'], context=context)
				elif line[1]:
					prod =  line_obj.browse(cr, uid, line[1], context=context).product_id
				if prod and prod.x_is_main=='1':
					_found1=False
					if prod.x_dcs_group:
						_found1,_cod,_acc=rate_obj.find_rate_group(cr, uid, partner_id, prod.x_dcs_group,dt_sale, context=context)
						if _found1:
							if ac_rate==True:
								_rate1=_acc
							else:
								_rate1=_cod
							if _rate1<=0.0:
								cost_xtra=0.0
							line[2]['price_unit'] = float(_rate1) + float(cost_xtra)
					if _found1==False:	
						if prod.list_price and prod.list_price > 0.0:#do not overwrite if it has rate setup in product level
							if ac_rate and prod.x_price_account > 0.0:
								line[2]['price_unit'] = prod.x_price_account  + float(cost_xtra)
							else:
								line[2]['price_unit'] = prod.list_price  + float(cost_xtra)
						else:	
							line[2]['price_unit'] = rate#[[6, 0, fiscal_obj.map_tax(cr, uid, fpos, prod.taxes_id)]]
				else:
					if ac_rate and prod.x_price_account > 0.0:
						line[2]['price_unit'] = prod.x_price_account	#  + float(cost_xtra)
					else:
						if prod.list_price:
							line[2]['price_unit'] = prod.list_price  	#+ float(cost_xtra)
				#	if prod and prod.list_price
				quote_line.append(line)

			# link      (4, ID)
			# link all  (6, 0, IDS)
			elif line[0] in [4, 6]:
				line_ids = line[0] == 4 and [line[1]] or line[2]
				for line_id in line_ids:
					prod = line_obj.browse(cr, uid, line_id, context=context).product_id
					found=False
					if prod:
						if prod.x_is_main == '1':#prod.taxes_id:
							_found1=False
							if prod.x_dcs_group:
								_found1,_cod,_acc=rate_obj.find_rate_group(cr, uid, partner_id, prod.x_dcs_group, dt_sale,context=context)
								if _found1:
									if ac_rate==True:
										_rate1=_acc
									else:
										_rate1=_cod
									if _rate1<=0.0:
										cost_xtra=0.0	
									quote_line.append([1, line_id, {'price_unit': float(_rate1) + float(cost_xtra) }])
									found=True
							if _found1==False:
								if prod.list_price and prod.list_price > 0.0:#do not overwrite if it has rate setup in product level
									if ac_rate and prod.x_price_account > 0.0:
										quote_line.append([1, line_id, {'price_unit': float(prod.x_price_account)  + float(cost_xtra) }])
									else:
										quote_line.append([1, line_id, {'price_unit': float(prod.list_price) + float(cost_xtra) }])
								else:
									quote_line.append([1, line_id, {'price_unit': float(rate) + float(cost_xtra)}])
								found=True
						else:
							if ac_rate and prod.x_price_account > 0.0:
								found=True
								quote_line.append([1, line_id, {'price_unit': prod.x_price_account}])
							else: 
								if prod.list_price:
									found=True
									quote_line.append([1, line_id, {'price_unit': prod.list_price}])
					if found==False:# else:
						quote_line.append([4, line_id])
			else:
				quote_line.append(line)
		return {'value': {'x_quote_lines': quote_line}}
		
class dincelcrm_compose_message(osv.Model):#it doesnot work here...
	_inherit = 'mail.compose.message'
	def send_mail(self, cr, uid, ids, context=None):
		if context.get('default_model') == 'account.analytic.account' and context.get('mark_need_approval'):
			if context.get('default_res_id'):
				_id=context.get('default_res_id')
				#self.pool.get('account.analytic.account').write(cr, uid, _id, {'x_sent': True})
				self.pool.get('account.analytic.account').write(cr, uid, _id, {'state':'need_approval'})
		if context.get('default_model') == 'account.analytic.account' and context.get('mark_as_draft'):
			if context.get('default_res_id'):
				_id=context.get('default_res_id')
				#self.pool.get('account.analytic.account').write(cr, uid, _id, {'x_sent': True})
				self.pool.get('account.analytic.account').write(cr, uid, _id, {'state':'open'})
		#_logger.error("dincelcrm_compose_message111["+str(context.get('default_res_id'))+"]["+str(context.get('mark_as_approved'))+"]")
		if context.get('default_model') == 'account.analytic.account' and context.get('mark_as_approved'):
			if context.get('default_res_id'):
				_id=context.get('default_res_id')
				#self.pool.get('account.analytic.account').write(cr, uid, _id, {'x_sent': True})
				self.pool.get('account.analytic.account').write(cr, uid, _id, {'state':'approved'})
				
		if context.get('default_model') == 'account.analytic.account' and context.get('mark_as_sent'):
			if context.get('default_res_id'):
				_id=context.get('default_res_id')
				#self.pool.get('account.analytic.account').write(cr, uid, _id, {'x_sent': True})
				self.pool.get('account.analytic.account').write(cr, uid, _id, {'x_sent': True,'state':'sent'})
		return super(dincelcrm_compose_message, self).send_mail(cr, uid, ids, context=context)

'''
class accountmail_compose_message(osv.Model):
	_inherit = 'mail.compose.message'
	
	#@api.multi #res = super(dincelreport_res_partner, self).write(cr, uid, ids, vals, context=context)
	def send_mail(self, cr, uid, ids, context=None):
		_logger.error("send_email11111["+str(context.get('default_model'))+"]["+str(context.get('default_res_id'))+"]["+str(context.get('mark_need_approval'))+"]["+str(context.get('mark_as_sent'))+"]")
		if context.get('default_model') == 'account.analytic.account' and context.get('mark_need_approval'):
			if context.get('default_res_id'):
				_id=context.get('default_res_id')
				#self.pool.get('account.analytic.account').write(cr, uid, _id, {'x_sent': True})
				self.pool.get('account.analytic.account').write(cr, uid, _id, {'state':'need_approval'})
		if context.get('default_model') == 'account.analytic.account' and context.get('mark_as_sent'):
			if context.get('default_res_id'):
				_id=context.get('default_res_id')
				#self.pool.get('account.analytic.account').write(cr, uid, _id, {'x_sent': True})
				self.pool.get('account.analytic.account').write(cr, uid, _id, {'x_sent': True,'state':'sent'})
		return super(dincelcrm_compose_message, self).send_mail(cr, uid, ids, context=context)
'''
		
class dincelcrm_text_template(osv.Model):
	_name = 'dincelcrm.text.template'
	_columns = {
		'name':fields.char("Name"),
		'state_code':fields.char("State"),
		'text_description': fields.text("Description"),
	}
		
class dincelcrm_quote_line(osv.Model):
	_name = "dincelmrp.quote.line"
	_order = 'x_service_type, id'
	def _total_lm_calc(self, cr, uid, ids, values, arg, context):
		x={}
		_lm=''
		for record in self.browse(cr, uid, ids):
			if record.product_id.x_prod_cat in ['customlength','stocklength']:
				_qty=record.item_qty
				_len=record.item_length
				_lm=_qty*_len*0.001
			else:
				_lm=''
			x[record.id] = _lm 
		return x
	def _amount_line(self, cr, uid, ids, field_name, arg, context=None):
		res = {}
		if context is None:
			context = {}
		for line in self.browse(cr, uid, ids, context=context):
			price = line.price_unit 
			qty=round(line.uom_qty,2)
			#cur = line.order_id.pricelist_id.currency_id
			if(line.x_service_type=='fixed'):
				res[line.id] = round((price*qty),2)
			else:
				res[line.id] = 0.0
		return res
	def product_id_change(self, cr, uid, ids, project_id, product,x_service_type, uom_qty, price_unit, context=None):
		context = context or {}
		
		if not x_service_type:
			x_service_type = ''
			
		product_uom_obj = self.pool.get('product.uom')
	
		product_obj = self.pool.get('product.product')
		price = 0.0
		 
		if not product:
			return {}
	
		result = {}
	
		product_obj = product_obj.browse(cr, uid, product, context=context)

		if product_obj.taxes_id:
			for tax in product_obj.taxes_id:
				if tax:
					result['tax_id']=tax.id 
					
		#result['tax_id'] = self.pool.get('account.fiscal.position').map_tax(cr, uid, fpos, product_obj.taxes_id)
		
		uom_name = product_obj.uom_id.name
		
		#result['x_name_desc'] = "Item 2(....) " + str(product_obj.name) + str(" ( ") + str(uom_qty) + " " + str(uom_name) + " at $" + str(price_unit) + " per " + str(uom_name) + " )"
		
		result['x_name_desc'] = "Item 2(....) " + str(product_obj.name)
		
		result['name'] = product_obj.name
		result['product_uom'] = product_obj.uom_id.id
		result.update({'item_length': product_obj.x_stock_length})
		 
		if price_unit:
			price = price_unit
		else:
			price = product_obj.list_price
			#result.update({'price_unit': price})
		if(x_service_type != 'variable'):
			result['subtotal'] = uom_qty * price
		else:
			result['subtotal'] = 0.0
			
		result.update({'price_unit': price})
		
		return {'value': result}
		
	def product_qty_changed(self, cr, uid, ids, product, qty=0,length=0, partner_id = False, payment_term = False, dt_sale = False,proj_id =False, context=None):
		
		result 		= {}
		context 	= context or {}
		
		if not partner_id:
			raise osv.except_osv(_('No Customer Defined!'), _('Before choosing a product,\n select a customer in the sales form.'))
		#if not payment_term:
		#	raise osv.except_osv(_('No Term Selected!'), _('Before choosing a product,\n select a customer in the sales form.'))
		warning 	= False
		
		domain 		= {}
		code 		= None
		
		#order_id	= None
		
		uom_qty 		= qty
		
		#for record in self.browse(cr, uid, ids, context=context):
		#	order_id = record.order_id.id
		
			
		partner_obj = self.pool.get('res.partner')
		product_obj = self.pool.get('product.product')
		term_obj 	= self.pool.get('account.payment.term')
		
		rate_obj 	= self.pool.get('dincelcrm.customer.rate') 
		
		#order_obj 	= self.pool.get('sale.order')
		#order_obj 	= order_obj.browse(cr, uid, order_id)
		#found_rate  = False
		ac_rate		= False
		grp_rate	= False
		cost_xtra	=0.0
		rate		=0.0
		
					 
		partner 	= partner_obj.browse(cr, uid, partner_id)
		#lang 		= partner.lang
		#context 	= {'lang': lang, 'partner_id': partner_id}
		#context_partner = {'lang': lang, 'partner_id': partner_id}
		
		warning_msgs = ''
		
		product_obj  = product_obj.browse(cr, uid, product, context)
		#if(product_obj.name):
			
		
		
		if(length != 0 and 'customlength' in product_obj.x_prod_cat): #To check custom length and product
			prod_like =product_obj.x_dcs_group
			sql ="SELECT pt.id as prod_id FROM product_template pt, product_product pp WHERE pt.x_stock_length = '" + str(int(length)) + "' AND pt.id = pp.product_tmpl_id AND pt.x_dcs_group = '" + str(prod_like) + "' AND pt.x_prod_cat='stocklength' and pt.x_dcs_itemcode like '%P-1%' and pt.active='t'"
			cr.execute(sql)
			rows = cr.fetchall()
			if(len(rows) > 0):
				#_logger.error("customlengthcustomlength22["+str(sql)+"]")
				raise osv.except_osv(_('Stock Length!'), _('The length you have entered [%s] already exists as a stock length product.' % (int(length))))
		
		#if product_obj.name: 
		if product_obj and "P-1" in product_obj.name:
			if length<1800 or length>7950:
				raise osv.except_osv(_('Product Length!'), _('Product Length must be between 1800 and 7950.'))
				
		#----------------------------------------------------------
		#converting [LM] into [M2]  LM->M2  LMtoM2 LM2M2
		#----------------------------------------------------------
		#rate_src=""
		
		
		if payment_term:
			term_obj = term_obj.browse(cr, uid, payment_term)
			code 	 = term_obj.x_payterm_code
			 
			if code:	
				if code != "COD" and code!="immediate":
					ac_rate		= True
				if product_obj.x_dcs_group:
					#rate_id = rate_obj.find_rate(cr, uid, partner_id,product_obj.x_dcs_group,product,dt_sale, context=context)
					grp_rate, _rate_cod, _rate_acct=rate_obj.find_rate_group(cr, uid, partner_id, product_obj.x_dcs_group,dt_sale, context=context)
					#_logger.error("find_ratefind_rate["+str(grp_rate)+"]["+str(_rate_cod)+"]["+str(_rate_acct)+"]["+str(product_obj.x_dcs_group)+"]")
					if grp_rate == True:
						#grp_rate=True
						if code == "COD" or code=="immediate":#if code == "30EOM":
							rate = _rate_cod
							#found_rate = True #
						else:	
							rate = _rate_acct
							#found_rate = True #order_obj.button_dummy()
							ac_rate		= True
				if grp_rate==False:#then find product rate...
					rate_id = rate_obj.find_rate(cr, uid, partner_id,None,product,dt_sale, context=context)
					
					if rate_id: #customer rate is present #-----------
						rate_id	 = rate_id[0]
					
						rate_obj =  rate_obj.browse(cr, uid, rate_id)
			
						if code == "COD" or code=="immediate":#if code == "30EOM":
							rate = rate_obj.rate_cod# cost_xtra
							#found_rate = True #
						else:	
							rate = rate_obj.rate_acct#+cost_xtra
							#found_rate = True #order_obj.button_dummy()
							ac_rate		= True
		
 
		if proj_id:#find state rate.xtra charge....if any
			#if proj_id:  and rate>0.0
			sql="""select r.rate1,r.rate2,r.rate3 from 
						dincelcrm_location_rates r ,res_country_state s, res_partner p
						where r.warehouse_id=s.x_warehouse_id and s.id=p.state_id and p.id='%s' """ % (proj_id)
			cr.execute(sql)
			rows2 = cr.fetchall()
			for row2 in rows2:
				if row2[0]:
					cost_xtra = float(row2[0])
		if product_obj.x_is_main=='1':#x_is_calcrate:
			if product_obj.x_m2_factor and product_obj.x_m2_factor>0:
				uom_qty = round((length*qty*0.001*product_obj.x_m2_factor),4) 	#M2 
			else:	
				uom_qty = round(((length*qty*0.001)/3),4) 	#M2 
			
			if grp_rate==False and product_obj.list_price and product_obj.list_price>0.0:#do not overwrite if it has rate setup in product level
				if ac_rate and product_obj.x_price_account>0.0:
					_rate=product_obj.x_price_account+cost_xtra
					result.update({'price_unit':_rate})
					#_subtotal= round((_rate*uom_qty),4)
					#result.update({'price_unit':_rate,'subtotal':_subtotal })	
				else:
					if product_obj.list_price<=0.0:
						cost_xtra=0.0
					_rate=product_obj.list_price+cost_xtra
					result.update({'price_unit':_rate})
					#_subtotal= round((_rate*uom_qty),4)
					
					#result.update({'price_unit': product_obj.list_price+cost_xtra})	
					#result.update({'price_unit':_rate,'subtotal':_subtotal })	
			else:
				#result.update({'price_unit': rate+cost_xtra})	
				if rate<=0.0:
					cost_xtra=0.0
				_rate=rate+cost_xtra
				result.update({'price_unit':_rate})
				#_subtotal= round((_rate*uom_qty),4)
				#result.update({'price_unit':_rate,'subtotal':_subtotal })	
			
		else:
			
			uom_qty = qty	
			if partner.x_accs_m2convert:
				if product_obj.x_m2_factor and product_obj.x_m2_factor>0:
					uom_qty = round((qty*product_obj.x_m2_factor),4) 	
					if rate>0:
						_rate=rate+cost_xtra
						result.update({'price_unit':_rate})
						#_subtotal= round((_rate*uom_qty),4)
						#result.update({'price_unit': _rate,'subtotal':_subtotal})
					
	
		result.update({'uom_qty': uom_qty})
		
		return {'value': result, 'domain': domain, 'warning': warning}
		
	_columns = {
		'name':fields.char("Name"),
		'x_name_desc': fields.char("Items Rate/Details", size=200),
		'quote_id': fields.many2one('account.analytic.account', 'Quote', ondelete='cascade',), #delete all this on delete  
		'product_id': fields.many2one('product.product','Product', domain=[('sale_ok', '=', True)]),
		'sequence':fields.integer("Sequence"),
		'item_qty':fields.integer("Qty"),
		'item_length':fields.integer("Length"),
		'product_uom': fields.many2one('product.uom', 'UOM'),
		'total_lm': fields.function(_total_lm_calc, method=True, string='L/M', type='float'),
		'coststate_id':fields.many2one("res.country.state","Cost Centre"),
		'uom_qty':fields.float("M2/Unit"),
		'price_unit':fields.float("Rate"),
		'subtotal':fields.function(_amount_line, method=True, string='Subtotal', type='float'),
		'tax_id': fields.many2one('account.tax','Tax'),
		'x_service_type':fields.selection([
			('fixed', 'Fixed'),
			('variable', 'Variable'),
			], 'Type', default='fixed'),
		'x_quot_state': fields.selection([	#>>overwrite the status....for labeling etc...
			('open', 'Open'),
			('need_approval','Need Approval'),
			('approved', 'Approved'),
			('sent', 'Sent'),
			('revised', 'Revised'),
			('cancel', 'Cancelled'),
			('done', 'Done'),
			], 'Status', readonly=True, copy=False, help="Gives the status of the Quotations.", select=True, track_visibility='onchange'),
		 
	}
	   
	_defaults = {
		'item_qty': 1,
		'sequence': 10,
		}
				