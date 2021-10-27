from openerp.osv import osv, fields
from datetime import date
#from openerp.addons.base_status.base_state import base_state
import time 
import datetime
from dateutil.relativedelta import relativedelta
import dateutil.parser
import csv
import logging
import config_dcs
import urllib2
import simplejson
from openerp import tools
from openerp.tools.translate import _
import subprocess
from subprocess import Popen, PIPE, STDOUT
from openerp import netsvc, api
#from crm import crm
from time import gmtime, strftime
_logger = logging.getLogger(__name__)

class dincelreport_res_partner(osv.Model):
	_inherit = "res.partner"
	def button_view_quotations(self, cr, uid, ids, context=None):
		if context is None:
			context = {}	
		for record in self.browse(cr, uid, ids, context=context):	
			if record.x_is_project:
				#domain=('x_project_id','=',record.id)
				ctx={'search_default_x_project_id': record.id}
			else:
				#domain=('partner_id','=',record.id)
				ctx={'search_default_partner_id': record.id}
			#_logger.error("button_view_quotationsbutton_view_quotations["+str(ctx)+"]x_is_project["+str(record.x_is_project)+"]")
			value = {
				'type': 'ir.actions.act_window',
				'name': _('Quotations List'),
				'view_type': 'form',
				'view_mode': 'tree,form',
				'res_model': 'account.analytic.account',
				#'domain':[domain],#'domain':[('partner_id','=',partner_id)],
				'context':ctx,#{'search_default_partner_id': partner_id},
				'view_id': False,
				
			}

			return value	
	def button_view_schedules(self, cr, uid, ids, context=None):
		if context is None:
			context = {}	
		for record in self.browse(cr, uid, ids, context=context):	
			if record.x_is_project:
				ctx={'search_default_project_id': record.id}
			else:
				ctx={'search_default_partner_id': record.id}
			
			value = {
				'type': 'ir.actions.act_window',
				'name': _('Component List Schedule'),
				'view_type': 'form',
				'view_mode': 'tree,form',
				'res_model': 'dincelcrm.quote.schedule',
				'context':ctx,
				'view_id': False,
				
			}
			return value
	def _get_total_sqm(self, cr, uid, ids, field_val, arg, context=None):
		res = {}
		#sqm_tot_110 = 0.0
		#sqm_tot_155 = 0.0
		#sqm_tot_200 = 0.0
		#sqm_tot_275 = 0.0
		#qty_lm = 0.0
		ret_val=0.0
		for record in self.browse(cr, uid, ids):
			ret_val=0.0
			sql = "SELECT id from sale_order where state != 'cancel' and "#partner_id = '%s'" %(record.id)
			if record.x_is_project:
				sql+="x_project_id"
			else:
				sql+="partner_id"
			sql+="= '%s'" %(record.id)	
			#_logger.error("_get_total_sqm111["+str(sql)+"]")
			cr.execute(sql)
			rows = cr.dictfetchall()
			for row in rows:
								
				sql="select sum(l.product_uom_qty) as tot from sale_order o,sale_order_line l,product_product p,product_template t"
				sql+=" where o.id=l.order_id and l.product_id=p.id and p.product_tmpl_id=t.id "
				sql+=" and o.id='%s'" % (row['id'])
				
				if(field_val == '110'):
					sql+=" and t.x_dcs_group='P110' and t.x_dcs_itemcode in('110P-1','110P-3')"
				elif(field_val == '155'):
					sql+=" and t.x_dcs_group='P155'and t.x_dcs_itemcode in('155P-1','155P-3')"
				elif(field_val == '200'):
					sql+=" and t.x_dcs_group='P200'and t.x_dcs_itemcode in('200P-1','200P-3')"
				elif(field_val == '275'):
					sql+=" and t.x_dcs_group='P275' and t.x_dcs_itemcode in('275P-1','275P-3')"
				else:
					sql+=" and 2=1"
				#_logger.error("_get_total_sqm111["+str(sql)+"]")
				cr.execute(sql)
				rows_p = cr.dictfetchall()
				for row_p in rows_p:
					try:
						ret_val += float(row_p['tot']) 
					except Exception,e:
						ret_val+=0.0	
				
			res[record.id] =	round(ret_val,2)#round(ret_val/3,2)
			
		return res
		
	def _get_total_sqm_110(self, cr, uid, ids, field_name, arg, context=None):
		return self._get_total_sqm(cr, uid, ids, '110', context)
	def _get_total_sqm_155(self, cr, uid, ids, field_name, arg, context=None):
		return self._get_total_sqm(cr, uid, ids, '155', context)
	def _get_total_sqm_200(self, cr, uid, ids, field_name, arg, context=None):
		return self._get_total_sqm(cr, uid, ids, '200', context)
	def _get_total_sqm_275(self, cr, uid, ids, field_name, arg, context=None):
		return self._get_total_sqm(cr, uid, ids, '275', context)
		
	def open_project_order(self, cr, uid, ids, context=None):
		if context is None:
			context = {}	
		for record in self.browse(cr, uid, ids, context=context):	
			if record.x_is_project:
				domain=('x_project_id','=',record.id)
				ctx={'search_default_x_project_id': record.id}
			else:
				domain=('partner_id','=',record.id)
				ctx={'search_default_partner_id': record.id}
			
			value = {
				'type': 'ir.actions.act_window',
				'name': _('Orders'),
				'view_type': 'form',
				'view_mode': 'tree,form',
				'res_model': 'sale.order',
				'domain':[domain],#('partner_id','=',partner_id)],
				'context':ctx,
				'view_id': False,
				
			}
			return value	
			
	def button_view_activities(self, cr, uid, ids, context=None):
		if context is None:
			context = {}	
		for record in self.browse(cr, uid, ids, context=context):	
			if record.x_is_project:
				#domain=('x_project_id','=',record.id)
				ctx={'search_default_x_project_id': record.id}
			else:
				#domain=('partner_id','=',record.id)
				ctx={'search_default_partner_id': record.id}
			
			value = {
				'type': 'ir.actions.act_window',
				'name': _('Activities'),
				'view_type': 'form',
				'view_mode': 'tree,form',
				'res_model': 'crm.phonecall',
				#'domain':[domain],#('partner_id','=',partner_id)],
				'context':ctx,
				'view_id': False,
				
			}
			return value
	def _openinvoice_count(self, cr, uid, ids, field_name, arg, context=None):
		res = {}
		for record in self.browse(cr, uid, ids):
			_count=0
			sql = "select count(*)   from account_invoice where partner_id = '"+str(record.id)+"' and state='open'"
			cr.execute(sql)
			rows = cr.fetchall()
			for row in rows:
				if(row[0]):
					_count = int(row[0])
			res[record.id] = _count
		return res
		
	def _sale_order_count(self, cr, uid, ids, field_name, arg, context=None):
		res = {}
		for record in self.browse(cr, uid, ids):
			_count=0
			sql = "select count(*)   from sale_order where "
			if record.x_is_project:
				sql += "x_project_id"
			else: 
				sql += "partner_id"
			sql += "='%s'" % (record.id)
			cr.execute(sql)
			rows = cr.fetchall()
			for row in rows:
				if(row[0]):
					_count = int(row[0])
			res[record.id] = _count
		return res	
		
	def _phonecall_count(self, cr, uid, ids, field_name, arg, context=None):
		res = {}
		for record in self.browse(cr, uid, ids):
			if record.x_is_project:
				sql = "select count(*) as total_quot from crm_phonecall where x_project_id = '"+str(record.id)+"'"
			else:
				sql = "select count(*) as total_quot from crm_phonecall where partner_id = '"+str(record.id)+"'"
			cr.execute(sql)
			rows = cr.fetchall()
			_count=0
			for row in rows:
				if(row[0]):
					_count = int(row[0])
			#else:
			res[record.id] = _count
		return res
		
	def _quotation_count(self, cr, uid, ids, field_name, arg, context=None):
		res = {}
		for record in self.browse(cr, uid, ids):
			if record.x_is_project:
				sql = "select count(*) as total_quot from account_analytic_account where x_project_id = '"+str(record.id)+"'"
			else:
				sql = "select count(*) as total_quot from account_analytic_account where partner_id = '"+str(record.id)+"'"
			cr.execute(sql)
			rows = cr.fetchall()
			if(len(rows) > 0):
				#_logger.error("_quotation_count_count:"+str(sql)+", "+str(rows))
				for row in rows:
					if(row[0]):
						res[record.id] = int(row[0])
			else:
				res[record.id] = 0
		return res
	def _schedule_count(self, cr, uid, ids, field_name, arg, context=None):
		res = {}
		for record in self.browse(cr, uid, ids):
			if record.x_is_project:
				sql = "select count(*) as total from dincelcrm_quote_schedule where project_id = '"+str(record.id)+"'"
			else:
				sql = "select count(*) as total from dincelcrm_quote_schedule where partner_id = '"+str(record.id)+"'"
			cr.execute(sql)
			rows = cr.fetchall()
			if(len(rows) > 0):
				#_logger.error("_quotation_count_count:"+str(sql)+", "+str(rows))
				for row in rows:
					if(row[0]):
						res[record.id] = int(row[0])
			else:
				res[record.id] = 0
		return res
		
	def onchange_province(self, cr, uid, ids, suburb_id, state_id, context = None):
		#val={}
		domain={}
		if state_id:
			_ids  = []
			obj		= self.pool.get('res.country.state').browse(cr,uid,state_id,context=context)
			#suburb_list=[]
			id_list=[]
			if obj.code:
				id_list = self.pool.get('dincelbase.suburb').search(cr, uid, [('state', '=', str(obj.code))], context=context)
				'''for _id in _ids:
					obj1 = self.pool.get('dincelbase.suburb').browse(cr,uid,_id,context=context)
					_found=False
					for suburb in suburb_list:
						#if not obj1.name in str(suburb_list):
						if suburb == obj1.name:
							_found = True
							break
					if not _found:		
						suburb_list.append(obj1.name)
						id_list.append(_id)'''
			
			if len(id_list)>0:
				domain  = {'x_suburb_id': [('id','in', (id_list))]}
		else:
			domain  = {'x_suburb_id': [('id','>', 0)]}
		return {'domain': domain}	
			
		#return {'value':val}
	def onchange_suburb_v2(self, cr, uid, ids, suburb_id, state_id, zip, isproj, street, context = None):
		val={}
		if suburb_id:
			obj		= self.pool.get('dincelbase.suburb').browse(cr,uid,suburb_id,context=context)
			val={'city': obj.name,'x_suburb_id':suburb_id}
			if not zip:
				_ids = self.pool.get('dincelbase.postcode').search(cr, uid, [('suburb', '=', str(obj.name))], context=context)
				if len(_ids) > 0:
					obj1 = self.pool.get('dincelbase.postcode').browse(cr,uid,_ids[0],context=context)
					val['zip']=obj1.name
			if isproj and street:
				_name=street + ", " +obj.name
				val['name']=_name
		return {'value':val}	
		
	def onchange_suburb(self, cr, uid, ids, suburb_id, state_id, zip, context = None):
		val={}
		if suburb_id:
			obj		= self.pool.get('dincelbase.suburb').browse(cr,uid,suburb_id,context=context)
			val={'city': obj.name,'x_suburb_id':suburb_id}
			if not zip:
				_ids = self.pool.get('dincelbase.postcode').search(cr, uid, [('suburb', '=', str(obj.name))], context=context)
				if len(_ids) > 0:
					obj1 = self.pool.get('dincelbase.postcode').browse(cr,uid,_ids[0],context=context)
					val['zip']=obj1.name
				
		return {'value':val}
		
	def onchange_postcode(self, cr, uid, ids, suburb_id, zip, city, state_id, context = None):
		domain={}
		val={}
		if zip:
			suburb_list=[]
			#_logger.error("onchange_postcodeonchange_postcode:zipzip["+str(zip)+"]")	
			_ids = self.pool.get('dincelbase.postcode').search(cr, uid, [('name', '=', str(zip))], context=context)
			_suburb=''
			#_logger.error("onchange_postcodeonchange_postcode:_ids_ids["+str(_ids)+"]")	
			#obj = self.pool.get('dincelbase.postcode').browse(cr,uid,_ids[0],context=context)
			if len(_ids)>0:
				#domain  = {'x_suburb_id': [('id','in', (_ids))]}
				for _id in _ids:
					obj1 = self.pool.get('dincelbase.postcode').browse(cr,uid,_id,context=context)
					#_logger.error("onchange_postcodeonchange_postcode:obj1obj1["+str(obj1)+"]")	
					if obj1:
						if not obj1.suburb in str(suburb_list):
							suburb_list.append(obj1.suburb)
							_suburb=obj1.suburb
						#id_list.append(_id)
						
				#_logger.error("onchange_postcodeonchange_postcode:suburb_listsuburb_list["+str(suburb_list)+"]")	
				#obj = self.pool.get('dincelbase.postcode').browse(cr,uid,_ids[0],context=context)
				_ids1=[]
				
				for suburb in suburb_list:#obj.suburb:
					_ids1 = _ids1 + self.pool.get('dincelbase.suburb').search(cr, uid, [('name', '=', suburb)], context=context)
				if suburb_id:
					_ids1 = [suburb_id]+_ids1 
				domain  = {'x_suburb_id': [('id','in', (_ids1))]}
				
				
				val={}
				if not suburb_id or suburb_id==None or suburb_id=="":#or not city:
					val={'x_suburb_id': _ids1[0]}
					obj1 = self.pool.get('dincelbase.suburb').browse(cr,uid,_ids1[0],context=context)
					val['city']=obj1.name
		else:
			if state_id:
				obj		= self.pool.get('res.country.state').browse(cr,uid,state_id,context=context)
				id_list=[]
				if obj.code:
					id_list = self.pool.get('dincelbase.suburb').search(cr, uid, [('state', '=', str(obj.code))], context=context)
		
				if len(id_list)>0:
					domain  = {'x_suburb_id': [('id','in', (id_list))]}
			else:
				domain  = {'x_suburb_id': [('id','>', 0)]}	
			
		return {'domain': domain,'value':val}
	def onchange_address1(self, cr, uid, ids, isproj, street, suburb_id, context = None):
		if isproj:
			_name=street
			if suburb_id:
				obj		= self.pool.get('dincelbase.suburb').browse(cr,uid,suburb_id,context=context)
				_name+=", " + obj.name
			val={'name': _name}
			return {'value':val}
			
	def onchange_sitename(self, cr, uid, ids, isproj, is_client, is_company, sitename, context = None):
		if isproj:# and sitename:
			return {}#'value': {'street': sitename}}
		else:
			id = None
			if (is_client or is_company) and sitename:
				sitename	= sitename.strip().replace("'", r"''")
				for record in self.browse(cr, uid, ids):
					#name		= record.name
					id	= record.id	
				words = sitename.split()  
				kw=sitename
				if len(words)==0:
					kw=sitename
				elif len(words)==1:	
					kw=sitename
				elif len(words)>1:
					kw=words[0] + " " + words[1]
				else: #only process first two letters....
					kw=words[0] + " " + words[1]
					
				sql ="SELECT name FROM res_partner WHERE  customer='1' AND is_company='1' AND lower(name)  like '%"+str(kw.lower())+"%' "
				if id:
					sql += " AND id <> '" + str(id) + "'"
				sql += " order by name"	
				#_logger.error("onchange_sitenameonchange_sitenameonchange_sitename_sql_sql["+str(sql)+"]")	
				cr.execute(sql)
				rows1 = cr.fetchall()
				if len(rows1) > 0:
					li	=[]
					count1=0
					for row in rows1:
						if count1<30:
							li.append(row[0])  
						count1+=1
					str1=', \n'.join(li)	
					raise osv.except_osv(_('Warning'), _('The similar client name already exists: \n'+str1 + '.'))
				'''else:
					words = sitename.split()     
					li	=[]
					count1=0
					
					str1=""
					if len(words)==3:
						str1=words[0] + " " + words[1]
						sql ="SELECT name FROM res_partner WHERE is_company='1' AND customer='1' AND lower(name) like '%"+str(str1.lower())+"%' "
						if id:
							sql += "AND id <> " + str(id) + ""
						cr.execute(sql)
						_logger.error("_create_balance_revised.sqlsqlsql3333["+str(sql)+"]")
						rows = cr.fetchall()
						for row in rows:
							if count1<15:
								li.append(row[0])     
							count1+=1
					#elif len(words)==3:
					#	str1=words[0] + " " + ords[1]
					elif len(words)==4 or len(words)==5:
						str1=words[0] + " " + words[1]
						sql ="SELECT name FROM res_partner WHERE is_company='1' AND customer='1' AND lower(name) like '%"+str(str1.lower())+"%' "
						if id:
							sql += "AND id <> " + str(id) + ""
						cr.execute(sql)
						_logger.error("_create_balance_revised.sqlsqlsql444["+str(sql)+"]")
						rows = cr.fetchall()
						for row in rows:
							if count1<15:
								li.append(row[0])     
							count1+=1
						str1=words[2] + " " + words[3]
						sql ="SELECT name FROM res_partner WHERE is_company='1' AND customer='1' AND lower(name) like '%"+str(str1.lower())+"%' "
						if id:
							sql += "AND id <> " + str(id) + ""
						cr.execute(sql)
						rows = cr.fetchall()
						for row in rows:
							if count1<15:
								li.append(row[0])     
							count1+=1	
					else:
					
						for curr_word in words:
							if curr_word and curr_word<>'' and len(curr_word)>3:
								sql ="SELECT name FROM res_partner WHERE is_company='1' AND customer='1' AND lower(name) like '%"+str(curr_word.lower())+"%' "
								if id:
									sql += "AND id <> " + str(id) + ""
								cr.execute(sql)
								rows = cr.fetchall()
								for row in rows:
									if count1<15:
										li.append(row[0])     
									count1+=1	
					if len(li)>0:
						str1=', \n'.join(li)
						raise osv.except_osv(_('Warning'), _('Similar client already exists: \n'+str1 + '.'))
						'''
		#return res
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
		
	def _get_usergroup_valid(self, cr, uid, _grp, context):
		_ret=False
		cr.execute("select res_id from ir_model_data where name='%s' and model='res.groups'" % (_grp)) #+ str(record.id))
			
		rows = cr.fetchone()
		if rows == None or len(rows)==0:
			_ret	=	False
		else:
			if rows[0]:#!=None:
				sql =	"select 1 from res_groups_users_rel where gid='%s' and uid='%s'" % (str(rows[0]), str(uid))
				cr.execute(sql)
				rows1 = cr.fetchone()
				if rows1 and len(rows1)>0:
					_ret	=	True
		return _ret
		
	def _edit_salesperson(self, cr, uid, ids, values, arg, context):
		x={}
		_edit=False
		for record in self.browse(cr, uid, ids):
			_grp="group_salesperson_editor"
			_edit=self._get_usergroup_valid(cr, uid, _grp, context)
			
			x[record.id]=_edit 
		return x
		
	def _edit_rate(self, cr, uid, ids, values, arg, context):
		x={}
		_edit=False
		for record in self.browse(cr, uid, ids):
			_grp="group_rate_editor"
			_edit=self._get_usergroup_valid(cr, uid, _grp, context)
			'''
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
				#if rows == None or len(rows)==0:'''
			x[record.id]=_edit 
		return x
	
	def _deposit_paid(self, cr, uid, ids, values, arg, context):
		x={}
		_stat=''
		for record in self.browse(cr, uid, ids):
			cr.execute("select 1 from account_invoice where type='out_invoice' and x_sale_order_id='%s'" % (str(record.id)))
			
			rows = cr.fetchone()
			if rows == None or len(rows)==0:
				_stat='NA'
			else:
				_stat=''
			x[record.id]=_stat 	
		return x
		
	def _balance_paid(self, cr, uid, ids, values, arg, context):
		x={}
		
		return x
		
	def cr_limit_over(self, cr, uid, ids, values, arg, context):
			
		x={}
		_over=False
		for record in self.browse(cr, uid, ids):
			_over=False
			if record.credit_limit>0:
				if record.x_over_terms=="red":
					_over=True
				'''
				sql ="select sum(amount_total) from sale_order where partner_id='%s' and x_status='open'" % (record.id)
				cr.execute(sql)
				rows = cr.fetchone()
				if rows == None or len(rows)==0:
					_over=False
				else:
					 if rows[0]!=None:
						if record.credit_limit<rows[0]:
							_over=True'''
			x[record.id] = _over 
		return x
		
	def over_due_invoice(self, cr, uid, ids, _id, context):
		_over=False
		dt_now	= fields.date.context_today(self,cr,uid,context=context)
		sql = "select i.date_due from account_invoice i,account_payment_term t where i.payment_term=t.id and t.x_days>0 and i.partner_id='%s' and i.state = 'open' and i.type='out_invoice' and i.x_inv_type in ('balance','full') and i.date_due<'%s' order by i.date_due asc limit 1" % (_id, dt_now)
		cr.execute(sql)
		rows = cr.fetchall()
		#_logger.error("dincelcrm_due_date111[["+str(sql)+"]")	
		if(len(rows) > 0):
			#dt_due = rows[0][0]
			sql = "select i.id,sum(i.amount_total)-sum(p.amount) as rem from account_invoice i left join account_payment_term t on i.payment_term=t.id left join dincelaccount_voucher_payline p on i.id=p.invoice_id where   t.x_days>0 and i.partner_id='%s' and i.state = 'open' and i.type='out_invoice' and i.x_inv_type in ('balance','full') and i.date_due<'%s' group by i.id   " % (_id, dt_now)
			cr.execute(sql)
			#_logger.error("dincelcrm_due_date222[["+str(sql)+"]")	
			rows1 = cr.fetchall()
			for row1 in rows1:
				if row1[1] and float(row1[1])>0:
					#_logger.error("dincelcrm_due_date222[["+str(row1[0])+"]["+str(row1[1])+"]")	
					_over = True
		return _over
		
	def _due_date_over(self, cr, uid, ids, values, arg, context):
			
		x={}
		for record in self.browse(cr, uid, ids):
			x[record.id]=self.over_due_invoice(cr, uid, ids, record.id, context)  
		return x
		
	#def onchange_name(self, cr, uid, ids, vals, name, context=None):
	#res = super(dincelreport_res_partner, self).write(cr, uid, ids, vals, context=context)
	def _edit_master(self, cr, uid, ids, values, arg, context):
		x={}
		_edit=False
		for record in self.browse(cr, uid, ids):
			cr.execute("select res_id from ir_model_data where name='deposit_ex_editor' and model='res.groups'") #+ str(record.id))
			#cr.execute(sql)
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
	def _cr_limit_read(self, cr, uid, ids, values, arg, context):
		x={}
		for record in self.browse(cr, uid, ids):
			if record.x_is_client or record.is_company:
				cr_lt=record.credit_limit
			else:
				cr_lt=0
			x[record.id]=cr_lt
		return x	
		
	def _deposit_exmpt_read(self, cr, uid, ids, values, arg, context):
		x={}
		for record in self.browse(cr, uid, ids):
			x[record.id]=record.x_deposit_exmpt 
		return x	
		
	def _openinvoice_value(self, cr, uid, ids, values, arg, context):
		x={}
		for record in self.browse(cr, uid, ids):
			#balance=0.0
			balance = self.get_open_invoice_info(cr, uid, ids, record.id, context=context)
			x[record.id]=balance
			
		return x	
		
	def has_valid_rate_default(self, cr, uid, ids, _id, context):
		grp_rate=False
		if _id:
			dcs_group="default"
			dt_sale=datetime.date.today()
			
			grp_rate, _rate_cod, _rate_acct=self.pool.get('dincelcrm.customer.rate').find_rate_group(cr, uid, _id, dcs_group,dt_sale, context=context)
			#_logger.error("has_valid_rate_default.has_valid_rate_default["+str(grp_rate)+"]["+str(dt_sale)+"]")
		return grp_rate
	
	'''def _has_pending_rate(self, cr, uid, ids, values, arg, context):
		x={}
		for record in self.browse(cr, uid, ids):
			_ret=False
			if record.is_company and record.x_is_client and record.x_dcs_id:
				if len(record.x_pending_rate_ids)>0:
					_ret=True 
				else:
					_ret=False
					
				#if record.x_has_valid_rate == False:
				#	_ret = True
				#else:
				#	_ret=False
			else:
				_ret=False	
				#if len(record.x_pending_rate_ids)>0:
				#	_ret=True
				#else:
				#	_ret=False
			x[record.id]=_ret
		return x'''
		
	def _has_valid_rate(self, cr, uid, ids, values, arg, context):
		x={}
		for record in self.browse(cr, uid, ids):
			_ret=False
			if record.is_company and record.x_is_client and record.x_dcs_id:
				_id=record.id
				_ret=self.has_valid_rate_default(cr, uid, ids, _id, context)  
			else:
				_ret=True
			x[record.id]=_ret
		return x
		
	def _openorder_value(self, cr, uid, ids, values, arg, context):
		x={}
		for record in self.browse(cr, uid, ids):
			#balance=0.0
			balance,o_ids=self.get_open_order_info(cr, uid, ids, record.id, context=context)
			'''
			#note>> if invoiced then fully invoiced (*) either deposit + balance OR full balance invoiced after delivery
			#sql="""select id,amount_total,x_del_status from sale_order 
			#		where partner_id='%s' and state not in ('cancel','done') and 
			#		id not in(select distinct x_sale_order_id from account_invoice where partner_id='%s' and x_inv_type not in('balance1','deposit') and #x_sale_order_id is not null) """ %(record.id,record.id)
			sql="""select id,amount_total,x_del_status from sale_order 
					where partner_id='%s' and state not in ('cancel','done') """ %(record.id)		
			cr.execute(sql)
			rows = cr.fetchall()
			for row in rows:
				if row[0] and row[1]:
					balance += float(row[1])
					sql = """SELECT a.id as inv_id, a.amount_total,a.x_sale_order_id 
					FROM account_invoice a left join sale_order o on a.x_sale_order_id = o.id left join res_partner p on a.x_project_id = p.id 
						where a.state not in ('cancel','done') and a.partner_id ='%s' and a.x_sale_order_id ='%s'""" %(record.id, row[0])			
					cr.execute(sql)
					rows1 = cr.dictfetchall()
					for row1 in rows1:
						amt_inv = float(row1['amount_total'])
						balance -= amt_inv'''
			x[record.id]=balance		
		return x
		
	_columns = {
		'x_is_competitor': fields.boolean('Is A Competitor'),
		'x_cr_limit_over': fields.function(cr_limit_over, method=True, string='Cr Limit Over', type='boolean'),
		'x_due_date_over': fields.function(_due_date_over, method=True, string='Due Date Over', type='boolean'),
		'x_cr_limit_read': fields.function(_cr_limit_read, method=True, string='Cr Limit', type='float'),
		'x_openinvoice_value': fields.function(_openinvoice_value, method=True, string='Open Invoices $', type='float'),
		'x_openorder_value': fields.function(_openorder_value, method=True, string='Open Orders $', type='float'),
		'x_deposit_exmpt_read': fields.function(_deposit_exmpt_read, method=True, string='Deposit Ex Readonly', type='boolean'),
		'x_is_project': fields.boolean('Is Project Site'),	#DINCEL specific a client has many projects/sites. and [client] & [site/project] have many contacts
		'x_is_client': fields.boolean('Is an Ordering Client', help="Enable if it is sole trader or a company who placed order."),	#DINCEL specific a client has many projects/sites. and [client] & [site/project] have many contacts
		'x_certifier':fields.boolean('Certifier'),
		'x_builder':fields.boolean('Builder'),
		'x_civil':fields.boolean('Civil'),
		'x_engineer':fields.boolean('Engineer'),
		'x_architect':fields.boolean('Architect'),
		'x_formwork':fields.boolean('Formwork'),
		'x_developer':fields.boolean('Developer'),
		'x_architect_id': fields.many2one('res.partner','Architect'),
		'x_formwork_id': fields.many2one('res.partner','Formwork'),
		'x_builder_id': fields.many2one('res.partner', 'Builder'),
		'x_engineer_id': fields.many2one('res.partner', 'Engineer'),
		'x_certifier_id': fields.many2one('res.partner', 'Certifier'),
		'x_source_id': fields.many2one('dincelcrm.leadsource', 'Lead Source'),
		'x_project_value':fields.float('Project Value'),
		'x_project_size':fields.float('Project Size'),
		'x_likely_sale_dt':fields.date("Likely Sale Date"),
		'x_is_sale_date': fields.boolean('Date Not Applicable?'),	#To set date not mandatory
		'x_role_partner_ids' : fields.many2many('res.partner', 'rel_partner_roles', 'object_partner_id', '_partner_roles_id', string = "Customers or Contacts"),
		'description': fields.char('Description'),	#v7 compatibility
		'x_role_site_ids' : fields.many2many('res.partner', 'rel_partner_roles', '_partner_roles_id', 'object_partner_id', string = "Sites"),
		'x_phonecall_ids': fields.one2many('crm.phonecall', 'x_project_id','Site History'),
		'x_meeting_ids': fields.one2many('crm.phonecall', 'partner_id','Meeting History'),
		'x_complaint_ids': fields.one2many('dincelcrm.complaints', 'project_id','Complaints'),
		'x_customer_rate_ids': fields.one2many('dincelcrm.customer.rate', 'partner_id','Rate History'),
		'x_pending_rate_ids': fields.one2many('dincelcrm.rate.pending', 'partner_id','Pending Rates'),
		'x_display_rate': fields.function(display_rate, method=True, string='Display Rate',type='char'),
		'x_edit_rate': fields.function(_edit_rate, method=True, string='Edit Rate',type='boolean'),
		'x_edit_salesperson': fields.function(_edit_salesperson, method=True, string='Edit Salesperson',type='boolean'),
		'x_deposit_paid': fields.function(_deposit_paid, method=True, string='Deposit Paid',type='char'),
		'x_balance_paid': fields.function(_balance_paid, method=True, string='Balance Paid',type='char'),
		'x_market_wall_id': fields.many2one('dincelcrm.market.wall.type','Specified Wall'),
		'x_dcs_id': fields.char('DCS ID'),
		'x_import_refid': fields.char('Import Ref ID'),
		'x_dcs_clientid': fields.many2one('res.partner', 'DCS Client'), #only for project or when x_is_project is TRUE[5/8/16]
		'x_dcs_contactid': fields.char('DCS Contact ID'), #for Import from dcs 10/11/2016
		'x_suburb_id': fields.many2one('dincelbase.suburb', 'Suburb New'), 
		'x_post_address': fields.char('Postal Address'),
		'x_acn': fields.char('ACN'),
		'x_live_ref': fields.char('Live Id Ref'),
		'x_rate_note': fields.char('Rate Note'),
		'x_over_terms': fields.char('Over Terms?'), #red/green
		'x_approved_by': fields.many2one('res.users','Approved by',track_visibility='onchange'),
		'x_approved_dt': fields.date('Approved Date'),
		'x_expiry_dt': fields.date('PPSR Expiry Date'),#Expiry Date
		'x_rego_dt': fields.date('PPSR Reg. Date'),#Registration date
		'x_crlimit_expiry_dt': fields.date('QBE CR Limit Expiry Date'),#QBE CR Expiry Date
		'x_deposit_exmpt': fields.boolean('Deposit Exempt'),
		'x_deposit_exmpt_dt': fields.date('Deposit Exempt Applied Date'),# Date
		'x_mrp_exmpt': fields.boolean('MRP Schedule Exempt', help="Gives option to bypass deposit payment required for production scheduling e.g. advance payment customers Dasco."),
		'x_delivery_exmpt': fields.boolean('Delivery Exempt'),
		'x_stop_supply': fields.boolean('Stop Supply (if overlimit)'),
		'x_hold_supply': fields.boolean('Hold Supply / Legal (by account/admin)'),
		'x_select_customer': fields.boolean('Select Customer'),
		'x_cr_over': fields.boolean('Over Credit Limit',help='Temporary holds over limit flag (if) to filter in new menu item for f/w'),
		'x_hide_parent': fields.boolean('Hide Parent'),
		'x_has_custref': fields.boolean('Ref. No. in Sale Order',help="By ticking this makes mandatory field in SO to enter customer ref. no."),
		'x_is_not_active': fields.boolean('Is Not Active?'),#boolean field to make customer active/inactive
		'x_is_blocked': fields.boolean('Is Inactive / Blocked'),#boolean field to make customer Inactive / Blocked to process sale order
		'x_accs_m2convert': fields.boolean('Convert Accs to m2'),
		'x_email_contact': fields.boolean('Email Contact?'),
		'x_site_branch': fields.boolean('Site Branch / Site Sales Rep',help='If ticked then order has site spacific sales rep, otherwise customer specific. eg hardware general.'),
		'x_ctype_id': fields.many2one('dincelcrm.contact.type', 'Contact Type'), 
		'user_id': fields.many2one('res.users', 'Salesperson',track_visibility='onchange'), 
		'x_edit_master': fields.function(_edit_master, method=True, string='Edit master',type='boolean'),
		'x_quotation_count': fields.function(_quotation_count, string='Quotations', type='integer'),
		'x_schedule_count': fields.function(_schedule_count, string='Schedules', type='integer'),
		'x_openinvoice_count': fields.function(_openinvoice_count, string='Open Invoices', type='integer'),
		'x_sale_order_count': fields.function(_sale_order_count, string='Orders', type='integer'),
		'x_phonecall_count': fields.function(_phonecall_count, string='Calls', type='integer'),
		'x_sqm_110': fields.function(_get_total_sqm_110, string='Total SQM (110P)', type='float'),
		'x_sqm_155': fields.function(_get_total_sqm_155, string='Total SQM (155P)', type='float'),
		'x_sqm_200': fields.function(_get_total_sqm_200, string='Total SQM (200P)', type='float'),
		'x_sqm_275': fields.function(_get_total_sqm_275, string='Total SQM (275P)', type='float'),
		'x_document_ids': fields.many2many('ir.attachment', string='Documents'),
		'x_has_valid_rate': fields.function(_has_valid_rate, method=True, string='Has valid rate',type='boolean'),
		#'x_has_pending_rate': fields.function(_has_pending_rate, method=True, string='Pending rate',type='boolean'),
		'x_ctype':fields.selection([
			('ac', 'Account'),
			('sc', 'Site Contact'),
			('mg', 'Manager'),
            ('other', 'Other'),
			], 'Contact Type'),
	}
	_defaults={
        'x_cr_over' : False, 
		'x_deposit_exmpt' : False, 
		'x_delivery_exmpt' : False, 
		'x_stop_supply' : False, 
		'x_has_custref':False,
	}
	
	def write(self, cr, uid, ids, vals, context=None):
		res = super(dincelreport_res_partner, self).write(cr, uid, ids, vals, context=context)
		for record in self.browse(cr, uid, ids):
			if record.parent_id and record.parent_id.id==record.id:
				raise Warning(_('You cannot select parent company as itself.'))
			if record.x_is_project and record.x_dcs_clientid:
				self._write_relation_if(cr, uid, record.x_dcs_clientid.id,record.id, context=context) 
			if record.x_is_project:
				sql ="UPDATE res_partner SET x_is_client='0',is_company='0' WHERE id='%s'" % (str(record.id))
			 	cr.execute(sql)
				if record.state_id:
					sql ="UPDATE dincelwarehouse_sale_order_delivery SET state_id='%s' WHERE project_id='%s'" % (record.state_id.id, str(record.id))
					cr.execute(sql)
		return res	
	#def button_view_invoices(self, cr, uid, ids, context=None):
	def create(self, cr, uid, vals, context=None):
		
		_id= super(dincelreport_res_partner, self).create(cr, uid, vals, context=context)
		record = self.browse(cr, uid, _id, context=context)#self.pool.get("").browse(cr, uid, ids)
		if record:
			usr=self.pool.get('res.users').browse(cr, uid, uid,context=context)		 
			sql=""
			if usr.x_salesperson == True:
				sql ="update res_partner set user_id='%s' WHERE id='%s' " % (uid, _id)
				cr.execute(sql)	
			#_logger.error("dincelreport_res_partner.create["+str(usr.x_salesperson)+"]["+str(sql)+"]")
		return _id
		
	def write_relation_if(self, cr, uid, partner_id,project_id, context=None):
		self._write_relation_if(cr, uid, partner_id,project_id, context=context) 
		
	def _write_relation_if(self, cr, uid, partner_id,project_id, context=None):
		if partner_id and project_id:
			
			sql	= "SELECT * from rel_partner_roles  where  object_partner_id='%s' and _partner_roles_id='%s'" % (project_id,partner_id)
			cr.execute(sql)
			
			rows_chk = cr.fetchall()
			if rows_chk == None or len(rows_chk) == 0:
				sql ="insert into rel_partner_roles (object_partner_id,_partner_roles_id) values('%s','%s')" % (project_id,partner_id)
			 	cr.execute(sql)
	def get_open_order_info(self, cr, uid, ids, partner_id, context=None):
		o_ids=[]
		balance=0.0
		sql="""select id,amount_total,x_del_status from sale_order 
					where partner_id='%s' and state not in ('cancel','done') """ %(partner_id)		
		cr.execute(sql)
		rows = cr.fetchall()
		for row in rows:
			if row[0] and row[1]:
				amt_order=float(row[1])
				amt_inv=0.0
				#balance += float(row[1])
				sql = """SELECT a.id as inv_id, a.amount_total,a.x_sale_order_id 
					FROM account_invoice a left join sale_order o on a.x_sale_order_id = o.id left join res_partner p on a.x_project_id = p.id 
					where a.state not in ('cancel','done') and a.partner_id ='%s' and a.x_sale_order_id ='%s'""" %(partner_id, row[0])			
				cr.execute(sql)
				rows1 = cr.dictfetchall()
				for row1 in rows1:
					amt_inv += float(row1['amount_total'])
					#balance -= amt_inv
				amt_bal=amt_order-amt_inv
				if amt_bal and abs(amt_bal)>0.1:	
					o_ids.append(row[0])
					balance+=amt_bal
		return balance, o_ids
		
	def get_open_invoice_info(self, cr, uid, ids, partner_id, context=None):
		balance=0.0
		sql = """SELECT a.id as inv_id, a.amount_total,a.x_sale_order_id 
					FROM account_invoice a left join sale_order o on a.x_sale_order_id = o.id left join res_partner p on a.x_project_id = p.id 
						where a.state ='open' and a.partner_id ='%s' """ %(partner_id)			
		cr.execute(sql)
		rows = cr.dictfetchall()
		for row in rows:
			amt = row['amount_total']
			amt_paid = 0
			sql_line = """select sum(p.amount) as amt_paid from dincelaccount_voucher_payline p,account_invoice a,account_voucher v where a.id = p.invoice_id and p.voucher_id=v.id and p.invoice_id='%s'""" %(row['inv_id'])
			cr.execute(sql_line)
			rows_line = cr.dictfetchall()
			for row_line in rows_line:
				if(row_line['amt_paid']):
					amt_paid = float(row_line['amt_paid'])
				
			bal = amt - amt_paid
			if(bal and abs(bal)>0.1):
				balance = balance + bal		
		return balance
		
	def check_account_terms_valid(self, cr, uid, ids, _id, _termid, context=None):
		if _termid and  _id:
			_code=""
			sql="select x_payterm_code from account_payment_term where id='%s'" % (_termid)
			cr.execute(sql)
			rows = cr.fetchall()
			for row in rows:
				_code=row[0]
			if _code != "COD" and _code != "immediate":
				sql="select credit_limit from res_partner where id='%s'" % (_id)
				cr.execute(sql)
				rows1 = cr.fetchall()
				for row1 in rows1:
					cr_lt=row1[0]
					if cr_lt:
						cr_lt=int(cr_lt)
					if cr_lt <= 0:
						return False
				
		return True 
		
	def abslink_external_dcs(self, cr, uid, ids, context=None):
		_url="http://abr.business.gov.au/"
		return { 'type': 'ir.actions.act_url', 'url': _url, 'nodestroy': True, 'target': 'new' }
	
	def save_n_update_partner_dcs(self, cr, uid, ids, vals, context=None):
		res = super(dincelreport_res_partner, self).write(cr, uid, ids, vals, context=context)
		self.updatelink_partner_dcs(cr, uid, ids, context)
		return {}
	
	def button_open_orders_list(self, cr, uid, ids, context=None):
		if context is None:
			context = {}	
		o_ids=[]	
		for record in self.browse(cr, uid, ids, context=context):	
			balance,o_ids=self.get_open_order_info(cr, uid, ids, record.id, context=context)
			'''#sql="""select id,amount_total,x_del_status from sale_order 
			#			where partner_id='%s' and state not in ('cancel','done') and 
			#			id not in(select distinct x_sale_order_id from account_invoice where partner_id='%s' and x_sale_order_id is not null) """ #%(record.id,record.id)
			sql="""select id,amount_total,x_del_status from sale_order 
						where partner_id='%s' and state not in ('cancel','done')  """ %(record.id)			
			cr.execute(sql)
			rows = cr.fetchall()
			for row in rows:
				if row[0] and row[1]:
					o_ids.append(row[0])'''
		value = {
			'type': 'ir.actions.act_window',
			'name': _('Open Orders'),
			'view_type': 'form',
			'view_mode': 'tree,form',
			'res_model': 'sale.order',
			'domain':[('id','in',o_ids)],
			'context':{},
			#'view_id': view_id,
			
		}

		return value	
		
	def button_download_statement_pdf(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		return self.download_statement_pdf(cr, uid, ids[0], context=context)	
		
	def download_statement_pdf(self, cr, uid, _id, context=None):
		if context is None:
			context = {}
		#datas = {'ids': context.get('active_ids', [])}
		#datas['form']  = self.read(cr, uid, ids, context=context)[0]
		#return self.pool['report'].get_action(cr, uid, [], 'account.report_partner_statement_pdf', data=datas, context=context)	
		_ids=_id
		
				
		url=self.pool.get('dincelaccount.config.settings').report_preview_url(cr, uid, [],"statement","",context=context)		
		#url=self.pool.get('sale.order').report_preview_url(cr, uid, ids,"statement","",context=context)		
		
		if url:
			url=url.replace("erp.dincel.com.au/", "localhost/")
			url+="&ids=%s" % (_ids)	
			fname="statement_"+str(_ids).replace("/","")+".pdf"
			save_path="/var/tmp/odoo/account"
			#_logger.error("error_dincelsale_statement:" + url)
			#_logger.error("error_dincelsale_statement:" + save_path + "/" + fname)
			process=subprocess.Popen(["wkhtmltopdf", 
						"--orientation",'landscape',
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
					'name': 'Report Pdf',
					'res_model': 'ir.actions.act_url',
					'type' : 'ir.actions.act_url',
					'url': '/web/binary/download_file?model=account.invoice&field=datas&id=%s&path=%s&filename=%s' % (str(_ids),save_path,fname),
					'context': context}
					
	def open_invoices_all(self, cr, uid, ids, context=None):
		if context is None:
			context = {}	
		for record in self.browse(cr, uid, ids, context=context):	
			partner_id=record.id 
			
			view_id = self.pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'accout.invoice_tree')], limit=1) 	
	
			value = {
				'type': 'ir.actions.act_window',
				'name': _('All Invoices'),
				'view_type': 'form',
				'view_mode': 'tree,form',
				'res_model': 'account.invoice',
				'domain':[('partner_id','=',partner_id),('state','=','open')],
				'context':{'search_default_partner_id': partner_id},
				'view_id': view_id,
				
			}

			return value	
	def button_approve_rate(self, cr, uid, ids, context=None):
		if context is None:
			context = {}	
		for record in self.browse(cr, uid, ids, context=context):	
			if len(record.x_pending_rate_ids)==0:
				raise osv.except_osv(_('Error'),_('No record found for validation.'))
				#					raise Warning(_('No record found for validation.'))
			#elif len(record.x_pending_rate_ids)>1:
			#	raise osv.except_osv(_('Error'),_('Multiple or ambiguity records found for validation.'))
			#	#raise Warning(_('Multiple or ambiguity records found for validation.'))
			else:
				for line in record.x_pending_rate_ids:
					rate_cod	=line.rate_cod
					rate_acct	=line.rate_acct
					dcs_group	=line.dcs_group
					partner_id	=line.partner_id.id
					_dt			=datetime.datetime.now() 
					sql	= "select id from dincelcrm_customer_rate where partner_id='%s' and dcs_group='%s'" % (partner_id,dcs_group)
					cr.execute(sql)
					rows2 = cr.fetchall()
					for row in rows2:
						sql="update dincelcrm_customer_rate set date_to='%s' where date_to is null and id='%s'" %(datetime.date.today()- datetime.timedelta(days=1), row[0])
						cr.execute(sql)
						
					vals={'rate_cod':rate_cod,
						  'rate_acct':rate_acct,
						  'dcs_group':dcs_group,
						  'partner_id':partner_id,
						  'user_id':uid,
						  'date_from':datetime.date.today(),
						  'date':_dt}
					if line.user_id:
						vals['request_uid']=line.user_id.id 
					self.pool.get('dincelcrm.customer.rate').create(cr, uid, vals, context) 
					
					'''	
					if len(rows2) == 0:
						vals={'rate_cod':rate_cod,
							  'rate_acct':rate_acct,
							  'dcs_group':dcs_group,
							  'partner_id':partner_id,
							  'user_id':uid,
							  'date_from':datetime.date.today(),
							  'date':_dt}
						self.pool.get('dincelcrm.customer.rate').create(cr, uid, vals, context) 	
					else:
						sql="update dincelcrm_customer_rate set rate_cod='%s',rate_acct='%s',user_id='%s',date='%s' where  partner_id='%s' and dcs_group='%s'" % (rate_cod,rate_acct,uid,_dt,partner_id,dcs_group)
						cr.execute(sql)'''
					sql="delete from dincelcrm_rate_pending where id='%s'"	% (line.id)
					cr.execute(sql)
		return True
		
	def updatelink_partner_dcs(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		#order_id = ids[0]
		#request = urllib.urlopen("http://deverp.dincel.com.au/dcsapi/")
		sql ="SELECT dcs_api_url FROM dincelaccount_config_settings";
		cr.execute(sql)
		rows = cr.fetchone()
		if rows and len(rows) > 0:
			url= str(rows[0]) + "?act=contact&id="+str(ids[0])
			#url="http://deverp.dincel.com.au/dcsapi/index.php?id="+str(ids[0])
			f 		 = urllib2.urlopen(url)
			response = f.read()
			str1	 = simplejson.loads(response)
			#@_logger.error("updatelink_order_dcs.updatelink_order_dcs["+str(str1)+"]["+str(response)+"]")
			item 	 = str1['item']
			status1	 = str(item['post_status'])
			dcs_refcode	= str(item['dcs_refcode'])
			if status1 == "success":
				#_logger.error("updatelink_order_dcs.updatelink_order_dcsordercode["+str(ordercode)+"]")	
				sql ="UPDATE res_partner SET x_dcs_id='"+dcs_refcode+"' WHERE id='"+str(ids[0])+"'"
				cr.execute(sql)
				return True
			else:
				if item['errormsg']:
					str1=item['errormsg']
				else:
					str1="Error while updating partner record."
				raise osv.except_osv(_('Error'), _(''+str1))
	
		
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
		non_project=None
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
			#x_lead		= record.x_lead_id
			non_project	= record.x_non_project
			if non_project:
				newname		= record.partner_id and record.partner_id.name
			#_logger.error("dincelcrm_phonecallactivitiesdincelcrm_phonecallactivities00["+str(record)+"]["+str(name)+"]["+str(nextact)+"]["+str(id)+"]["+str(nextdt)+"]")	
		#_logger.error("dincelcrm_phonecallactivitiesdincelcrm_phonecallactivities["+str(name)+"]")	
		_done=False
		if name and name == 'follow-up' and newname and comments and len(comments)>0 and q_obj:
			try:	
				sql="update crm_phonecall set name='%s',state='done' where id=%s " % (newname.replace("'",""),id)
				cr.execute(sql)
				_done=True
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
						#'x_lead_id': x_lead.id,
						'priority':'1',
					 }
					if non_project:
						_vals['x_non_project'] =non_project
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
				_done=True
			#_logger.error("dincelcrm_phonecallactivitiesdincelcrm_phonecallactivities["+str(name)+"]["+str(nextact)+"]["+str(id)+"]["+str(nextdt)+"]")	
			
			if nextact and nextdt and len(nextact)>0:
				
				#sql ="select 1 from crm_phonecall where name = 'follow-up' and x_origin_fw='%s'" %(id)
				#cr.execute(sql)
				#rows = cr.fetchall()
				#if len(rows)==0:
				_obj 	= self.pool.get('crm.phonecall')
				_vals = {
					'x_is_followup': True,
					'name': 'follow-up', 
					'state': 'open', 
					'date': nextdt, 
					'x_instruction': nextact, 
					'priority':'1',
					#'x_lead_id': x_lead.id,
					'x_origin_fw':id,
				}
				if non_project:
					_vals['x_non_project'] =non_project
				if contact_id:
					_vals['x_contact_id'] = contact_id.id
				if partner_id:
					_vals['partner_id'] = partner_id.id
				if project_id:
					_vals['x_project_id'] = project_id.id	
					
				if id and id!=None and id!=0:
					_vals['x_origin_fw'] = id
					sql ="select 1 from crm_phonecall where name = 'follow-up' and x_origin_fw='%s'" %(id)
					cr.execute(sql)
					rows = cr.fetchall()
					if len(rows)==0:#only insert onece..
						new_id 		= _obj.create(cr, uid, _vals, context=context)
				else:
					new_id 		= _obj.create(cr, uid, _vals, context=context)
		
		if _done==False:
			if record.state and record.state=="open" and comments and len(comments)>0:
				_done=True #some reasons there is no f/w flag clear....so double checking to clear it....[due to act/fw merge under my calendar]
				sql="update crm_phonecall set state='done' where id=%s " % (record.id)
				cr.execute(sql)
				
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
		_id= super(dincelcrm_phonecallactivities, self).create(cr, uid, vals, context=context)
		record = self.pool.get('crm.phonecall').browse(cr, uid, _id, context=context)#self.pool.get("").browse(cr, uid, ids)
		if record:
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
			#x_lead		= record.x_lead_id
			if nextact and nextdt and len(nextact)>0:
				
				#sql ="select 1 from crm_phonecall where name = 'follow-up' and x_origin_fw='%s'" %(id)
				#cr.execute(sql)
				#rows = cr.fetchall()
				#if len(rows)==0:
				_obj 	= self.pool.get('crm.phonecall')
				_vals = {
					'x_is_followup': True,
					'name': 'follow-up', 
					'state': 'open', 
					'date': nextdt, 
					'x_instruction': nextact, 
					'priority':'1',
					#'x_lead_id': x_lead.id,
					#'x_origin_fw':id,
				}
				if record.x_non_project:
					_vals['x_non_project'] =record.x_non_project
				if contact_id:
					_vals['x_contact_id'] = contact_id.id
				if partner_id:
					_vals['partner_id'] = partner_id.id
				if project_id:
					_vals['x_project_id'] = project_id.id	
				sql="insert into crm_phonecall(name,date,state,user_id,x_is_followup,priority,x_instruction,active) values('%s','%s','%s','%s','%s','%s','%s','t') RETURNING id"%("follow-up",nextdt,"open",record.user_id.id,"t","1",nextact)
				cr.execute(sql)	
				#_logger.error("dincelcrm_phonecallactivitiesdincelcrm_create111["+str(sql)+"]")	
				_newid=cr.fetchone()[0]
				if _newid:
					sql ="update crm_phonecall set priority='1'"
					if partner_id:
						sql += ",partner_id='%s'" % (partner_id.id)
					if project_id:
						sql += ",x_project_id='%s'" % (project_id.id)
					if contact_id:
						sql += ",x_contact_id='%s'" % (contact_id.id)
					if _id:
						sql += ",x_origin_fw='%s'" % (_id)
					sql += " where id='%s'" % (_newid)	
				#_logger.error("dincelcrm_phonecallactivitiesdincelcrm_update222["+str(sql)+"]")	
				cr.execute(sql)	
				#if id and id!=None and id!=0:
				#	_vals['x_origin_fw'] = id
				#	sql ="select 1 from crm_phonecall where name = 'follow-up' and x_origin_fw='%s'" %(id)
				#	cr.execute(sql)
				#	rows = cr.fetchall()
				#	if len(rows)==0:#only insert onece..
				#		new_id 		= _obj.create(cr, uid, _vals, context=context)
				#else:
				#	new_id 		= _obj.create(cr, uid, _vals, context=context)
				#	
		return _id

		
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
		'x_non_project': fields.boolean('Non-Project Activity'),
		'x_instruction': fields.char('Followup Instruction'),
		'x_next_action': fields.char('Next Action'),
		'x_next_act_date': fields.datetime("Next Action Date"),
		'x_status':fields.selection(config_dcs.QUOTE_STATUS, 'Status'),
		'x_origin_fw':fields.many2one('crm.phonecall','Origin Activity'),
		'x_active_user': fields.related('user_id', 'active', type='boolean', string='active_user',store=False),
		'x_lead_id':fields.many2one('crm.lead','Leads'),
		'x_type': fields.selection([
				('phonecall','Phonecall/Email'),
				('face2face','Face2Face'),
				#('email','Email'),
				#('other','Other'),
				],'Type'),
		'state': fields.selection([('open', 'F/W'),
				('cancel', 'Cancelled'),
				('pending', 'Pending'),
				('done', 'Activity')
				], string='Status', readonly=True, track_visibility='onchange',
				help='The status is set to Confirmed, when a case is created.\n'
				'When the call is over, the status is set to Held.\n'
				'If the callis not applicable anymore, the status can be set to Cancelled.'),		
		}
	_defaults={
        'x_non_project' :False, 
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
	def onchange_client(self, cr, uid, ids, project_id, client_id,is_nonproj=False, context=None):
		if client_id:
			c_ids3  = []
			my_list = []
			obj		= self.pool.get('res.partner').browse(cr,uid,client_id,context=context)
			for item in obj.x_role_site_ids:
				my_list.append(item.id) 
				c_ids3 = c_ids3 + self.pool.get('res.partner').search(cr, uid, [('parent_id', '=', item.id)], context=context)
			
			
			c_ids1 = self.pool.get('res.partner').search(cr, uid, [('parent_id', '=', client_id)], context=context)
			if project_id: #getting the project's contacts...
				c_ids2 = self.pool.get('res.partner').search(cr, uid, [('parent_id', '=', project_id)], context=context)
				c_ids1 = c_ids1+ c_ids2
			else:
				c_ids1 = c_ids3# + obj.child_ids
				for itema in obj.child_ids:#getting partner's contacts
					c_ids1 = c_ids1 + [itema.id]
					
			if len(c_ids1)>0:
				domain  = {'x_project_id': [('id','in', (my_list))],'x_contact_id': [('id','in', (c_ids1))]}#domain['x_contact_id']=[('id','in', (my_list))]
			else:
				domain  = {'x_project_id': [('id','in', (my_list))]}
				
			if is_nonproj:
				val1	= obj.name	
				value   = {'name':val1}
			else:
				value={}
			#else:
			#	val1=""
			return {'domain': domain, 'value': value}	
			
		else:
			
			ids2 = self.pool.get('res.partner').search(cr, uid, [('x_is_project', '=', True)], context=context)
			c_ids1 = self.pool.get('res.partner').search(cr, uid, [('x_is_project', '=', False),('is_company', '=', False)], context=context)
			domain  = {'x_project_id': [('id','in', (ids2))],'x_contact_id': [('id','in', (c_ids1))]}
			return {'domain': domain}	
			
	
					
	def onchange_project(self, cr, uid, ids, project_id, client_id,is_nonproj=False, context=None):
		val1=""
		if client_id and is_nonproj:
			obj		= self.pool.get('res.partner').browse(cr,uid,client_id,context=context)
			val1	= obj.name	
		if project_id:
			obj		= self.pool.get('res.partner').browse(cr,uid,project_id,context=context)
			if val1=="":
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
			c_ids1 	= self.pool.get('res.partner').search(cr, uid, [('x_is_project', '=', False),('is_company', '=', False)], context=context)
			
			ids2 	= self.pool.get('res.partner').search(cr, uid, [('x_is_project', '=', False)], context=context)
            
			value   = {'name':val1}
			
			domain  = {'partner_id': [('id','in', (ids2))],'x_contact_id': [('id','in', (c_ids1))]}
			
			return {'domain': domain,'value': value,}	
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
		
	def add_followups(self, cr, uid, ids, context=None):
		#ctx = dict(context)
		ctx={}
		##	
		#	
		#}
		for record in self.browse(cr, uid, ids, context=context):	
			if record.x_project_id:
				ctx['default_project_id']=record.x_project_id.id 
			if record.partner_id:
				ctx['default_partner_id']=record.partner_id.id 	
			if record.x_contact_id:
				ctx['default_contact_id']=record.x_contact_id.id 
			if record.x_contract_quote_id:
				ctx['default_quote_id']=record.x_contract_quote_id.id 		
		return {
			'type': 'ir.actions.act_window',
			'res_model': 'dincelcrm.followup',
			'view_type': 'form',
			'view_mode': 'form',
			'context':ctx,
			'target': 'new',
		}
		'''
	 
		return {
				'name': _('Add Followups'),
				'type': 'ir.actions.act_window',
				'view_type': 'form',
				'view_mode': 'form',
				'res_model': 'dincelcrm.followup',
				'target': 'new',
				'context': ctx,
			}'''
			
class dincelcrm_contact_type(osv.Model):
	_name="dincelcrm.contact.type"
	_columns={
		'name':fields.char("Name",size=30),
		'code':fields.char("Code",size=5),
	}	
	
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
	
class dincelcrm_rate_pending(osv.Model):
	_name= "dincelcrm.rate.pending"
	_columns={
		'rate_cod':fields.float("COD Rate"),
		'rate_acct':fields.float("Account Rate"),
		'partner_id':fields.many2one("res.partner","Customer"),
		'description': fields.char('Notes'),
		'user_id': fields.many2one('res.users','Requested By'),
		'dcs_group': fields.selection([
			('default', 'Default'),
			('P110', '110mm'),
			('P155', '155mm'),
			('P200', '200mm'),
			('P275', '275mm'),
			], 'Product Group'),
	}
	_defaults = {
		'dcs_group': 'default',
	}
	
class dincelcrm_customer_rate(osv.Model):
	_name= "dincelcrm.customer.rate"
	
	def find_rate_group(self, cr, uid, partner_id=None, dcs_group=None, dt=None, context=None):
		if context is None: context = {}
	
		result = self.find_rate(cr, uid, partner_id, dcs_group, None, dt, context)
		if result:
			_rate	= self.browse(cr, uid, result[0], context=context)
			return True, _rate.rate_cod, _rate.rate_acct
		return False, None, None	
		
	def _getrate_bygrpname(self, cr, uid, partner_id, dcs_group, dt=None, context=None):	
		args 	= [('partner_id', '=', partner_id), ('dcs_group', '=', dcs_group)]
		if not dt:
			dt	= datetime.datetime.today()
			dt1	= datetime.datetime.strptime(str(dt.date()), '%Y-%m-%d')
			#str1+=",2"
		else:
			if len(str(dt))>10: #means it has date and time
				dt1		= self.pool.get('dincelstock.transfer').get_au_date(cr, uid, dt) 
				#cause the date from/to are stored in AU date 
				#but the date in order date is UTC (due to datetimestamp value)
				#-------------------------------------------
				dt=dateutil.parser.parse(str(dt1))
				#str1+=",3"
				#dt 	= dateutil.parser.parse(str(dt))
			else:
				dt1=dt
		args1 	= args + [('date_from', '<=' ,dt), ('date_to', '>=', dt)]
		
		result 	= self.search(cr, uid, args1, context=context)
		if not result:#NOTE: to date is open or blank, so check date_to is NULL....as below SQL
			sql	= "select id from dincelcrm_customer_rate where partner_id='%s' and dcs_group='%s' and date_from<='%s' and date_to is null" % (partner_id, dcs_group, dt1)
			cr.execute(sql)
			rows = cr.fetchone()
			if rows and len(rows)>0:
				result	= [rows[0]]
				#str1+=",4"
		#else:
		if not result:#that means no date at all ....just get data with no date_to or its value as NULL....
			#and date_from<='%s'@
			sql	= "select id from dincelcrm_customer_rate where partner_id='%s' and dcs_group='%s'  and date_to is null" % (partner_id, dcs_group)
			cr.execute(sql)
			rows = cr.fetchone()
			if rows and len(rows)>0:
				result	= [rows[0]]
				#str1+=",5"		
		return result	
		
	def _getrate_bygrp(self, cr, uid, partner_id, dcs_group, dt=None, context=None):	
		result	= None
		if dcs_group:
			result=self._getrate_bygrpname(cr, uid, partner_id, dcs_group, dt, context)
			if not result:
				dcs_group1="default"
				result=self._getrate_bygrpname(cr, uid, partner_id, dcs_group1, dt, context)
		else:
			dcs_group1="default"
			result=self._getrate_bygrpname(cr, uid, partner_id, dcs_group1, dt, context)
		'''	
		if not dcs_group:
			dcs_group="default"
		args 	= [('partner_id', '=', partner_id), ('dcs_group', '=', dcs_group)]
		#result1 = self.search(cr, uid, args, context=context)
		str1=""
		if not partner_id:
			return result
		sql	= "select id from dincelcrm_customer_rate where partner_id='%s' and dcs_group='%s'" % (partner_id, dcs_group)
		cr.execute(sql)
		rows = cr.fetchall()
		if rows and len(rows)>0:
			if len(rows) == 1:#only record....in system...
				result	= [rows[0][0]]
				str1+=",1"
				_logger.error("_getrate_bygrp_getrate_bygrp["+str(context)+"]["+str(args)+"]["+str(result)+"]")	
			else:#more than one means has date...
				if not dt:
					dt	= datetime.datetime.today()
					dt1	= datetime.datetime.strptime(str(dt.date()), '%Y-%m-%d')
					str1+=",2"
				else:
					if len(str(dt))>10: #means it has date and time
						dt1		= self.pool.get('dincelstock.transfer').get_au_date(cr, uid, dt) 
						#cause the date from/to are stored in AU date 
						#but the date in order date is UTC (due to datetimestamp value)
						#-------------------------------------------
						dt=dateutil.parser.parse(str(dt1))
						str1+=",3"
						#dt 	= dateutil.parser.parse(str(dt))
					else:
						dt1=dt
				
				args1 	= args + [('date_from', '<=' ,dt), ('date_to', '>=', dt)]
				
				_logger.error("_getrate_bygrp_getrate_bygrp22333 dt["+str(dt)+"]args1["+str(args1)+"]dt1["+str(dt1)+"]")	
				
				result 	= self.search(cr, uid, args1, context=context)
				if not result:#NOTE: to date is open or blank, so check date_to is NULL....as below SQL
					#dt 	= dateutil.parser.parse(str(dt))
					#dt1	= datetime.datetime.strptime(str(dt.date()), '%Y-%m-%d')
					sql	= "select id from dincelcrm_customer_rate where partner_id='%s' and dcs_group='%s' and date_from<='%s' and date_to is null" % (partner_id, dcs_group, dt1)
					cr.execute(sql)
					rows = cr.fetchone()
					if rows and len(rows)>0:
						result	= [rows[0]]
						str1+=",4"
				#else:
				if not result:#that means no date at all ....just get data with no date_to or its value as NULL....
					#and date_from<='%s'@
					sql	= "select id from dincelcrm_customer_rate where partner_id='%s' and dcs_group='%s'  and date_to is null" % (partner_id, dcs_group)
					cr.execute(sql)
					rows = cr.fetchone()
					if rows and len(rows)>0:
						result	= [rows[0]]
						str1+=",5"
		_logger.error("_getrate_bygrp_getrate_bygrp22333 dt["+str(dt)+"]args1["+str(result)+"]str1["+str(str1)+"]")		'''		
		return result	

	def _getrate_byproduct(self, cr, uid, partner_id, product_id, dt=None, context=None):	
		result	= None
		args 	= [('partner_id', '=', partner_id), ('product_id', '=', product_id)]
		#result1 = self.search(cr, uid, args, context=context)
		if not partner_id or not product_id:
			return result
		sql	= "select id from dincelcrm_customer_rate where partner_id='%s' and product_id='%s'" % (partner_id, product_id)
		cr.execute(sql)
		rows = cr.fetchall()
		if rows and len(rows)>0:
			if len(rows)==1:#only record....in system...
				result	= [rows[0][0]]
				#_logger.error("_getrate_bygrp_getrate_bygrp["+str(context)+"]["+str(args)+"]["+str(result)+"]")	
			else:#more than one means has date...
				if not dt:
					dt= datetime.datetime.today()
					dt1	= datetime.datetime.strptime(str(dt.date()), '%Y-%m-%d')
				else:
					if len(str(dt))>10: #means it has date and time
						dt1		= self.pool.get('dincelstock.transfer').get_au_date(cr, uid, dt) 
						#cause the date from/to are stored in AU date 
						#but the date in order date is UTC (due to datetimestamp value)
						#-------------------------------------------
						dt=dateutil.parser.parse(str(dt1))
					else:
						dt1=dt
						#dt 	= dateutil.parser.parse(str(dt))
					
				
				args1 	= args + [('date_from', '<=' ,dt), ('date_to', '>=', dt)]
				
				#_logger.error("_getrate_bygrp_getrate_bygrp22333 dt["+str(dt)+"]args1["+str(args1)+"]dt1["+str(dt1)+"]")	
				
				result 	= self.search(cr, uid, args1, context=context)
				if not result:#NOTE: to date is open or blank, so check date_to is NULL....as below SQL
					#dt 	= dateutil.parser.parse(str(dt))
					#dt1	= datetime.datetime.strptime(str(dt.date()), '%Y-%m-%d')
					sql	= "select id from dincelcrm_customer_rate where partner_id='%s' and product_id='%s' and date_from<='%s' and date_to is null" % (partner_id, product_id, dt1)
					cr.execute(sql)
					rows = cr.fetchone()
					if rows and len(rows)>0:
						result	= [rows[0]]
				#else:
				if not result:#that means no date at all ....just get data with no date_to or its value as NULL....
					#and date_from<='%s'@
					sql	= "select id from dincelcrm_customer_rate where partner_id='%s' and product_id='%s'  and date_to is null" % (partner_id, product_id)
					cr.execute(sql)
					rows = cr.fetchone()
					if rows and len(rows)>0:
						result	= [rows[0]]
		return result	
		
			
	def find_rate(self, cr, uid, partner_id=None, dcs_group=None, product_id=None, dt=None, context=None):
		if context is None: context = {}
		result	= None
		args1	= []
		args	= []
		if not partner_id or not dcs_group:
			return result
		#log=""
		args 	= [('partner_id', '=', partner_id), ('dcs_group', '=', dcs_group)]
		if dcs_group:
			#args 	= [('partner_id', '=', partner_id), ('dcs_group', '=', dcs_group)]
			#result1 = self.search(cr, uid, args, context=context)
			sql	= "select id from dincelcrm_customer_rate where partner_id='%s' and dcs_group='%s'" % (partner_id, dcs_group)
			cr.execute(sql)
			rows = cr.fetchall()
			if rows and len(rows)>0:
				result=self._getrate_bygrp(cr, uid, partner_id, dcs_group, dt, context)
			else:
				if dcs_group!="P275" or dcs_group=="default":#cause 275mm group works differently....
					dcs_group="default"
					result=self._getrate_bygrp(cr, uid, partner_id, dcs_group, dt, context)
		else:
			if product_id:
				result=self._getrate_byproduct(cr, uid, partner_id, product_id, dt, context)
		#else:	
		#	#args 	= [('partner_id', '=', partner_id)]
		#	#dcs_group="default"
		#	result=self._getrate_bygrp(cr, uid, partner_id, dcs_group, dt, context)
		'''if dt:
			args1 	= args + [('date_from', '<=' ,dt), ('date_to', '>=', dt)]
			result 	= self.search(cr, uid, args1, context=context)

			if not result:#NOTE: to date is open or blank
				dt 	= dateutil.parser.parse(str(dt))
				dt1	= datetime.datetime.strptime(str(dt.date()), '%Y-%m-%d')
				sql	= "select id from dincelcrm_customer_rate where partner_id='%s' and date_from<='%s' and date_to is null" % (partner_id,dt1)
				cr.execute(sql)
				rows = cr.fetchone()
				if rows and len(rows)>0:
					result	= [rows[0]]
					
					#args1 = args + [('date_from', '<=' ,dt), ('date_to', '=', False)]
					#result = self.search(cr, uid, args1, context=context)
		'''		
		
		#if not result:#NOTE: to date is open or blank	
		#	args 	= [('partner_id', '=', partner_id)]
		#	result 	= self.search(cr, uid, args, context=context)	
		#
		#_logger.error("find_ratefind_rate["+str(log)+"]["+str(args1)+"]["+str(args)+"]["+str(result)+"]")
		#if not result:#NOTE: to date is open or blank	
		#	result = self.find(cr, uid,dt,partner_id,context=context)
		return result	
		
	def find(self, cr, uid, dt=None,partner_id=None, context=None):
		if context is None: context = {}
		'''if not dt:
			dt = fields.date.context_today(self, cr, uid, context=context)
		args = [('date_from', '<=' ,dt), ('date_to', '>=', dt),('partner_id', '=', partner_id), ('product_id', '=', False)]
		
		#result = []
		s="1"
		result = self.search(cr, uid, args, context=context)
		if not result:#NOTE: to date is open or blank
			args = [('date_from', '<=' ,dt), ('partner_id', '=', partner_id), ('date_to', '=', False), ('product_id', '=', False)]
			result = self.search(cr, uid, args, context=context)
			s="2"
		if not result:#NOTE: to date is open or blank
			args = [('partner_id', '=', partner_id), ('product_id', '=', False)]
			result = self.search(cr, uid, args, context=context)	
			s="3"'''
		#_logger.error("dincelcrm_customer_rate_findfind["+str(result)+"]["+str(dt)+"]["+str(s)+"]")	
		args 	= [('partner_id', '=', partner_id), ('product_id', '=', False),('dcs_group', '=', 'default')]
		result 	= self.search(cr, uid, args, context=context)	
		#_logger.error("findfind_ratefindfind_rate333["+str(args)+"]["+str(result)+"]")
		return result
		
	_order = 'date_from desc, id'	
	_columns={
		'rate_cod':fields.float("COD Rate"),
		'rate_acct':fields.float("Account Rate"),
		'date_from':fields.date("From Date"),
		'date_to':fields.date("To Date"),
		'date':fields.datetime("Date"),
		'partner_id':fields.many2one("res.partner","Customer"),
		'product_id': fields.many2one('product.product', 'Product'),
		'description': fields.char('Notes'),
		'user_id': fields.many2one('res.users','Last Saved By'),
		'request_uid': fields.many2one('res.users','Requested By'),
		'approve_uid': fields.many2one('res.users','Approved By'),
		'state':fields.selection([ #as in dcs open /reject/ approve
			('open','Open'),
			('approve','Approved'),
			('reject','Rejected'),
			], 'Status'),	#, track_visibility='onchange'
		'dcs_group': fields.selection([
			('default', 'Default'),
			('P110', '110mm'),
			('P155', '155mm'),
			('P200', '200mm'),
			('P275', '275mm'),
			], 'Product Group'),
	}
	_defaults = {
		'dcs_group': 'default',
	}		
	
	def write(self, cr, uid, ids, vals, context=None):
		
		res = super(dincelcrm_customer_rate, self).write(cr, uid, ids, vals, context=context)
		for record in self.browse(cr, uid, ids):
			_dt=datetime.datetime.now() 
			sql="update dincelcrm_customer_rate set user_id='%s',date='%s' where id='%s'" % (uid, _dt, record.id)
			cr.execute(sql)
			
		return res	
		
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
	
class dincelcrm_res_users(osv.Model):
	_inherit = "res.users"
	_columns = {
		'x_code':fields.char("Short Code",size=4),
		'x_warehouse_id': fields.many2one('stock.warehouse','Warehouse'),
		'x_honors':fields.char("Honors",size=200),
		'x_salesperson': fields.boolean('Salesperson?'),
	}
	_defaults={
		'x_salesperson' : False,
	}
	
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
	
	def get_quote_no(self, cr, uid, ids, values, arg, context):
		x={}
		active_id = "-"
		
		for record in self.browse(cr, uid, ids):
			if record.x_project_id:
				cr.execute("select name from account_analytic_account where x_quote_converted=True and x_lead_id=" + str(record.id))
				#_logger.error("get_quote_no111["+str("select name from account_analytic_account where x_quote_converted=True and x_lead_id=" + str(record.id))+"]");
				rows = cr.fetchall()
				if len(rows) > 0:
					active_id = rows[0][0]
				else:	
					active_id = "-"
			x[record.id]=active_id
		return x
	
	def convert_to_quotation(self, cr, uid, ids, context=None):
		lead_obj 		= self.pool.get('account.analytic.account')
		x_project_id =None
		vals = {
					'x_prepared_by': uid,
					'x_stage_id': 5, 
					'state':'open',
					'description':'Open',
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
			if partner_id:
				vals['partner_id']		= partner_id.id
			if x_contact_id:
				vals['x_contact_id']	= x_contact_id.id	
				
			vals['x_lead_id'] = record.id
			vals['type'] = 'normal'
			vals['x_is_quote'] = True
		
		#_logger.error(["convert_to_quotation111["+str(vals)+"]"])
		if x_project_id:
			new_id 		= lead_obj.create(cr, uid, vals, context=context)
			if new_id:
				'''
				_upd = {
					'state': 'quote',
					'x_quotation_id' : [(6, 0, [x_quotation_id.id for x_quotation_id in record.x_quotation_id])],
				}
				'''
				
				cr.execute("update crm_lead set state='quote' where id="+str(record.id))
				
				view_id = self.pool.get('ir.ui.view').search(cr,uid,[('name', '=', 'dincelcrm.contractquote.form.view')], limit=1)
				value 	= {
							'domain': str([('id', 'in', new_id)]),
							'view_type': 'form',
							'view_mode': 'form',
							'res_model': 'account.analytic.account',
							'view_id': view_id,
							'type': 'ir.actions.act_window',
							'name' : _('Quotation'),
							'target' : 'current',
							'res_id': new_id
						}
				
				return value
		return {}
		
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
		#'x_quotation_id': fields.one2many('account.analytic.account', 'x_lead_id', string="Quotation"),
		'x_quotation_id': fields.function(get_quote_no, method=True, string='Quote',type='char'),
		'state': fields.selection([('open', 'Open'),('draft', 'draft'),('quote','Quote')]),
		'x_followups' : fields.one2many("crm.phonecall", 'x_lead_id', 'Follow-Ups'),
		#'x_ref_no':fields.char("RefNumber",size=50),
		#'x_phonecall_id': fields.many2one('crm.phonecall','Phonecall'),
	}	#'x_last_fw_desc': fields.char(compute='last_fw_desc', string='Last follow-up comments'),	
	
	
class dincelcrm_weeklyreport(osv.Model):
	_name="dincelcrm.weeklyreport"
	_inherit = ['mail.thread']
	_order = "entry_dt desc"
	_description = 'DOT Report'
	_columns={
		'name': fields.char('Name',size=64, required=True),
		'user_id': fields.many2one('res.users', 'Salesperson'),
		'sales_update':fields.text("Sales update"),	
		'win_loss':fields.text("Wins / Losses"),	
		'large_quote':fields.text("Large Quote"),	#New large quotes / projects since last update
		'competitor':fields.text("Competitor"),	 	#Competitor intell / market activitiy
		'challanges':fields.text("challenges"),	
		'entry_dt':fields.date("Entry Date"),
	}
	_defaults={
        'entry_dt' : fields.date.context_today, 
		'name' : fields.date.context_today, 
		'user_id': lambda s, cr, uid, c: uid,
    }
	#def onchange_end_date(self, cr, uid, ids, end_dt, context=None):
	#	if end_dt:
	#		str1=dict(config_dcs.QUOTE_STATUS)[_status]#dict(self.fields_get(allfields=['x_status'])['x_status']['selection'])[_status]
	#		value   = {'start_dt':str1}
	#		return {'value': value}
			
class dincelcrm_email_pending(osv.Model):
	_name="dincelcrm.email.pending"			
	_columns={
		'name': fields.char('Name',size=64), #subject of email
		'body_email':fields.text("Email Body"),	 #body of email
		'user_id': fields.many2one('res.users', 'Salesperson'),
		'entry_dt':fields.date("Entry Date"),
		'schedule_dt':fields.datetime("Schedule Date"),
		'sent_flag':fields.boolean('Is Sent'), #if sent then set flag = 1 or TRUE
		'sent_dt':fields.datetime("Sent Date"),
		'email_type':fields.char('Email Type',size=30), #e.g. 'fw-pending'
	}
	
class dincelcrm_country_state(osv.Model):
	_inherit = 'res.country.state'
	_columns={
		'x_warehouse_id': fields.many2one('stock.warehouse', 'Default Warehouse'),
	}	

class dincelcrm_helpdesk(osv.Model):
	_inherit = 'crm.helpdesk'
	_columns = {
		'x_create_uid': fields.many2one('res.users', 'Requested By'),
		'x_verify_uid': fields.many2one('res.users', 'Verified By',track_visibility='onchange'),
		'x_verify':fields.boolean('Verified',track_visibility='onchange'),
	}
	_defaults = {
		'x_create_uid': lambda s, cr, uid, c: uid,
	}	
	
	def btn_verify_item(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		obj		=  self.browse(cr, uid, ids[0], context=context)
		if not obj.x_verify:
			self.write(cr, uid, [ids[0]], {'x_verify':True, 'x_verify_uid': uid})	
		return True	
		
class dincelcrm_warehouse_address(osv.Model):
	_inherit="stock.picking.type"
	_columns={
		'x_warehouse_address': fields.one2many("dincelcrm.warehouse.address", 'address_id', 'Warehouse Address')
	}

class dincelcrm_warehouse_address_line(osv.Model):
	_name="dincelcrm.warehouse.address"
	_description="Warehouse Address"
	
	def _get_address_str(self, cr, uid, ids, values, arg, context=None):
		x={}
		for record in self.browse(cr, uid, ids):
			x[record.id] = str(record.street) + ", " + str(record.suburb) + " " + str(record.postcode)
		return x
		
	_columns={
		'name': fields.function(_get_address_str,method=True,type='char',string='Name'),
		'street': fields.char('Street'),
		'postcode': fields.char('Postcode'),	
		'suburb': fields.char('Suburb'),	
		'state_id': fields.many2one('res.country.state','State'),		
		'country_id': fields.many2one('res.country','Country'),
		'address_id': fields.many2one("stock.picking.type", 'Warehouse Address'),
	}
	_defaults={
		'address_id' : lambda obj, cr, uid, context: uid,
	}	

class dincelcrm_rate_config(osv.Model):
	_name="dincelcrm.rate.config"
	_description="Rate Configuration"
	_columns={
		'rate_cod':fields.float("COD Rate (min.)"),
		'rate_acct':fields.float("Account Rate (min.)"),
		'product_id': fields.many2one('product.product', 'Product'),
		'description': fields.char('Notes'),
		'active': fields.boolean('Active'),
		'dcs_group': fields.selection([
			('default', 'Default'),
			('P110', '110mm'),
			('P155', '155mm'),
			('P200', '200mm'),
			('P275', '275mm'),
			], 'Product Group'),
	}
	_defaults={
		'active' : True,
	}	