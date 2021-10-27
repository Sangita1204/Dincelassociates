from openerp.osv import osv, fields
from datetime import date
from dateutil.relativedelta import relativedelta
import base64
#import urllib
import time 
import datetime
from datetime import timedelta
import dateutil.parser
import csv
import logging
import urllib2
import socket
import simplejson
from openerp import SUPERUSER_ID, api
#from dinceljournal import dincelaccount_journal
import subprocess
from openerp import tools
from dincel_journal import dincelaccount_journal
from openerp.tools.translate import _
from openerp.exceptions import except_orm, Warning, RedirectWarning
from time import gmtime, strftime
from subprocess import Popen, PIPE, STDOUT
import openerp.addons.decimal_precision as dp
from openerp.tools import config
_logger = logging.getLogger(__name__)
'''
TYPE2DATES = {
	'tba': 'TBA',
	'na': 'NA',
	'dt': 'Date',
}'''
	
class dincelaccount_sale_order(osv.Model):
	_inherit="sale.order"
	#_order = 'id desc'
	def change_pickup_state(self, cr, uid, ids, state_id, pudel, context=None):
		if state_id:# and pudel:# and pudel=="pu":
			obj = self.pool.get('res.country.state').browse(cr, uid, state_id, context=context)
			if obj.x_warehouse_id:
				return {'value':{'x_warehouse_id':obj.x_warehouse_id.id}}
	
	def onchange_partner_id_v2(self, cr, uid, ids, partner_id, project_id, context=None):
		if not partner_id:
			return {'value': {'partner_invoice_id': False, 'partner_shipping_id': False,  'payment_term': False, 'fiscal_position': False}}

		part = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context)
		
		if part.x_is_blocked:
			raise osv.except_osv(_('Blocked customer'),_('Inactive or blocked customer. Please contact account team to proceed.'))
				
		addr = self.pool.get('res.partner').address_get(cr, uid, [part.id], ['delivery', 'invoice', 'contact'])
		pricelist = part.property_product_pricelist and part.property_product_pricelist.id or False
		payment_term = part.property_payment_term and part.property_payment_term.id or False
		dedicated_salesman = part.user_id and part.user_id.id# or uid
		val = {
			'partner_invoice_id': addr['invoice'],
			'partner_shipping_id': addr['delivery'],
			'payment_term': payment_term,
			'user_id': dedicated_salesman,
			'x_credit_limit': part.credit_limit,
			'x_deposit_exmpt': part.x_deposit_exmpt,
			'x_rate_note':part.x_rate_note,
			'x_has_custref':part.x_has_custref,
			}
		#if part.x_deposit_exmpt:
		
			
		delivery_onchange = self.onchange_delivery_id(cr, uid, ids, False, part.id, addr['delivery'], False,  context=context)
		val.update(delivery_onchange['value'])
		if pricelist:
			val['pricelist_id'] = pricelist
		sale_note = self.get_salenote(cr, uid, ids, part.id, context=context)
		if sale_note: val.update({'note': sale_note})  
		
		#c_ids3  = []
		proj_list = []
		#x_role_site_ids
		#obj		= self.pool.get('res.partner').browse(cr,uid,part.id,context=context)
		
		for item in part.x_role_site_ids:
			proj_list.append(item.id) 
		#	c_ids3 = c_ids3 + self.pool.get('res.partner').search(cr, uid, [('parent_id', '=', item.id)], context=context)
		#x_role_site_ids
		
		#c_ids1 = self.pool.get('res.partner').search(cr, uid, [('parent_id', '=', part.id)], context=context)
		#if project_id:
		#	c_ids2 = self.pool.get('res.partner').search(cr, uid, [('parent_id', '=', project_id)], context=context)
		#	c_ids1 = c_ids1 + c_ids2
		#else:
		#	c_ids1 = c_ids3
		c_ids1=	self.get_contact_ids(cr, uid, ids,partner_id,project_id, context)
		if len(c_ids1) > 0:
			domain  = {'x_project_id': [('id','in', (proj_list))],'x_contact_id': [('id','in', (c_ids1))]}#domain['x_contact_id']=[('id','in', (my_list))]
		else:
			domain  = {'x_project_id': [('id','in', (proj_list))]}
			
		return {'value': val,'domain': domain}
	
	def get_contact_ids(self, cr, uid, ids,partner_id,project_id, context=None):
		c_ids1=[]
		if partner_id:
			c_ids2 = self.pool.get('res.partner').search(cr, uid, [('parent_id', '=', partner_id)], context=context)
			c_ids1 = c_ids1 + c_ids2
		if project_id:
			c_ids2 = self.pool.get('res.partner').search(cr, uid, [('parent_id', '=', project_id)], context=context)
			c_ids1 = c_ids1 + c_ids2
		#else:
		#	c_ids1 = c_ids3
		return c_ids1
		
	def onchange_projectsite(self, cr, uid, ids, project_id,partner_id, context=None):
		_obj = self.pool.get('res.partner').browse(cr, uid, project_id, context=context)
		if _obj:
			street=""
			val = {
				#'x_street': str(_obj.street) + " " + str(_obj.street2),
				'x_postcode': _obj.zip,
				'x_suburb': _obj.city,
				}
			if _obj.street:
				street+= str(_obj.street)
			if _obj.street2:
				street+= " " +str(_obj.street2)
			p_dcsid	=_obj.x_dcs_id	
			val['x_street']=street	
			userid=None
			#if _obj.user_id:
			#	userid=_obj.user_id.id 
			#else:
			if partner_id:
				_obj2 = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context)
				if _obj2.x_site_branch:
					if _obj.user_id:
						userid=_obj.user_id.id 
				if userid==None:	
					if _obj2.user_id:
						userid=_obj2.user_id.id 
						
				c_dcsid	=str(_obj2.x_dcs_id)+"-"
				if p_dcsid and c_dcsid not in p_dcsid:
					val['x_site_mismatch']=True
					
			if userid==None:
				obj1 = self.pool.get('res.users').search(cr, uid, [('x_code', '=', "INSL")], context=context)#[0]
				if obj1:
					userid=obj1[0]
			val['user_id']=userid
			
			if _obj.state_id:
				val['x_state_id']=_obj.state_id.id
				val['x_coststate_id']=_obj.state_id.id
			if _obj.country_id:
				val['x_country_id']=_obj.country_id.id	
				
			c_ids1=	self.get_contact_ids(cr, uid, ids,partner_id,project_id, context)
			if len(c_ids1) > 0:	
				domain  = {'x_contact_id': [('id','in', (c_ids1))]}
			else:
				domain={}
			return {'value': val,'domain': domain}
	
	def change_warehouse(self, cr, uid, ids, warehouse_id,partner_id=False, payment_term = False, dt_sale = False, order_lines= False, pudel=False,context=None):
		'''for record in self.browse(cr, uid, ids):
			if record.x_pudel and record.x_pudel=="pu":
			#	if stateid.x_warehouse_id:
			#		if stateid.x_warehouse_id.id != record.x_warehouse_id.id:
			#			raise osv.except_osv(_('Error!'), _('The pickup location is not correct based on selected state.'))
		'''	
		return self._change_payment_term(cr, uid, ids, warehouse_id,partner_id, payment_term , dt_sale , order_lines, context=context)
	
	def change_payment_term(self, cr, uid, ids, warehouse_id,partner_id=False, payment_term = False, dt_sale = False, order_lines= False, context=None):
		_valid=self.pool.get('res.partner').check_account_terms_valid(cr, uid, ids, partner_id, payment_term, context) 
		if _valid==False:			
			raise osv.except_osv(_('Invalid Terms'),_('Invalid terms found. The customer account rate is not activated yet.'))
			return False
		else:
			return self._change_payment_term(cr, uid, ids, warehouse_id,partner_id, payment_term , dt_sale , order_lines, context=context)
	
	def _change_payment_term(self, cr, uid, ids, loc_id,partner_id=False, payment_term = False, dt_sale = False, order_lines= False, context=None):
		#order_id	= None
		rate		= 0.0
		#partner_obj = self.pool.get('res.partner')
		product_obj = self.pool.get('product.product')
		term_obj 	= self.pool.get('account.payment.term')
		
		rate_obj 	= self.pool.get('dincelcrm.customer.rate')
		term_obj 	= term_obj.browse(cr, uid, payment_term)
		code 	 	= term_obj.x_payterm_code
		
		#product_obj = self.pool.get('product.product')
		line_obj = self.pool.get('sale.order.line')
		
		#date_order = False
		
		#pricelist= self.pool.get('product.pricelist').search(cr, uid, [('type', '=', 'sale')], limit=1) 	
		
		#for record in self.browse(cr, uid, ids):
		#	date_order=record.date_order
			
		#if not date_order:
		#	date_order=datetime.today()
		ac_rate=False
		
		#if partner_id:
		#	partner_obj = self.pool.get('res.partner').browse(cr,uid,partner_id,context=context)
		#	acs_c
		if code:	
			if code != "COD" and code!="immediate":
				ac_rate		= True
			#rate_id = rate_obj.find(cr, uid, dt_sale, partner_id, context=context)
			rate_id = rate_obj.find(cr, uid, dt_sale, partner_id, context=context)
			if rate_id:
				rate_id	 = rate_id[0]
				rate1 =  rate_obj.browse(cr, uid, rate_id)
				if rate1:
					#if code == "30EOM":
					#	rate = rate_obj.rate_acct
					if code == "COD" or code=="immediate":
						rate = rate1.rate_cod
						ac_rate=False
					else:
						rate = rate1.rate_acct
						ac_rate=True
		#if not date_order:
		
		#if rate:
		_extra_rate=0.0
		if loc_id:
			loc_obj = self.pool.get('stock.warehouse').browse(cr,uid,loc_id,context=context)
			_extra_rate=loc_obj.x_cost_xtra
		if loc_id and rate>0.0:
			rate = rate+_extra_rate
			
		
		
		
		order_line = []
		for line in order_lines:
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
					#if _found1==False:	
					#if prod.list_price and prod.list_price > 0.0:#do not overwrite if it has rate setup in product level
					#	if ac_rate and prod.x_price_account > 0.0:
					#		line[2]['price_unit'] = prod.x_price_account + _extra_rate
					#	else:
					#		line[2]['price_unit'] = prod.list_price + _extra_rate
					#	#else:
					#	_found1=True
						
					if prod.x_dcs_group  and _found1==False:
						_found1,_cod,_acc=rate_obj.find_rate_group(cr, uid, partner_id, prod.x_dcs_group, dt_sale,context=context)
						#_logger.error("find_ratefind_rate00000["+str(_found1)+"]["+str(_cod)+"]["+str(_acc)+"]["+str(prod.x_dcs_group)+"]")
						if _found1:
							if ac_rate==True:
								_rate1=_acc
							else:
								_rate1=_cod
							if _rate1>0.0:	#if zero then do not update #added 17.4.18
								_found1=False
								line[2]['price_unit'] = float(_rate1) + _extra_rate
					#if _found1==False:	
					#	line[2]['price_unit'] = rate#
					#-----------------------
					if _found1==False:	#no group rate found...
						if prod.list_price and prod.list_price > 0.0:# not found and  if it has rate setup in product level
							if ac_rate and prod.x_price_account > 0.0:
								line[2]['price_unit'] = prod.x_price_account + _extra_rate
							else:
								line[2]['price_unit'] = prod.list_price + _extra_rate
						else:	
							line[2]['price_unit'] = rate#[[6, 0, fiscal_obj.map_tax(cr, uid, fpos, prod.taxes_id)]]-----
				else:#non p-1 products
					if ac_rate and prod.x_price_account > 0.0:
						line[2]['price_unit'] = prod.x_price_account
					else:
						if prod.list_price:
							line[2]['price_unit'] = prod.list_price 
				#	if prod and prod.list_price
				order_line.append(line)

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
							#if prod.list_price and prod.list_price > 0.0:#do not overwrite if it has rate setup in product level
							#	if ac_rate and prod.x_price_account > 0.0:
							#		order_line.append([1, line_id, {'price_unit': prod.x_price_account + _extra_rate}])
							#	else:
							#		order_line.append([1, line_id, {'price_unit': prod.list_price + _extra_rate}])
							#	_found1=True
							#	found=True
								
							if prod.x_dcs_group and _found1==False:
								_found1,_cod,_acc=rate_obj.find_rate_group(cr, uid, partner_id, prod.x_dcs_group, dt_sale,context=context)
								#_logger.error("find_ratefind_rate2222["+str(_found1)+"]["+str(_cod)+"]["+str(_acc)+"]["+str(prod.x_dcs_group)+"]")
								if _found1:
									if ac_rate==True:
										_rate1=_acc
									else:
										_rate1=_cod
									if _rate1>0.0:	#added 17.4.18
										order_line.append([1, line_id, {'price_unit': _rate1 + _extra_rate}])
										found=True
									
							#if _found1==False:
							#	order_line.append([1, line_id, {'price_unit': rate}])
								
							if _found1==False:#no group rate found...
								if prod.list_price and prod.list_price > 0.0:#do not overwrite if it has rate setup in product level
									if ac_rate and prod.x_price_account > 0.0:
										order_line.append([1, line_id, {'price_unit': prod.x_price_account + _extra_rate}])
									else:
										order_line.append([1, line_id, {'price_unit': prod.list_price + _extra_rate}])
								else:
									order_line.append([1, line_id, {'price_unit': rate}])
								found=True
						else:#non p-1 products
							if ac_rate and prod.x_price_account > 0.0:
								found=True
								order_line.append([1, line_id, {'price_unit': prod.x_price_account}])
							else: 
								if prod.list_price:
									found=True
									order_line.append([1, line_id, {'price_unit': prod.list_price}])
					if found==False:# else:
						order_line.append([4, line_id])
			else:
				order_line.append(line)
		return {'value': {'order_line': order_line}}
			
	def has_custom_profile(self, cr, uid, ids, values, arg, context):
		x={}
		has_custom='0'
		for record in self.browse(cr, uid, ids):
			#check if deposit invoice already created. if then do not display create button
			#sql = "select p.id from product_product p,product_template t,account_invoice o,account_invoice_line l where o.id=l.invoice_id and p.id=l.product_id and p.product_tmpl_id=t.id and t.x_prod_cat='deposit' and o.state not in('refund','cancel','offset') and o.x_sale_order_id='%s' "% (record.id)
			#sql += " and o.type='out_invoice'	"
			#cr.execute(sql)
			#if deposit invoice alredy created no need to create again
			#rows1 = cr.fetchall()
			#if len(rows1) > 0:
			#	has_custom = '0'
			#else:	
			_ret= self._has_custom_profile(cr, uid, ids, record.id, context)
			if _ret==True:
				has_custom = '1'
			else:
				has_custom = '0'	
			'''sql = "select p.id from product_product p,product_template t,sale_order_line o where p.id=o.product_id and p.product_tmpl_id=t.id and t.x_prod_cat='customlength' and o.order_id='%s' " % (record.id)
			cr.execute(sql)
			rows = cr.fetchall()
			if len(rows) > 0:
				has_custom = '1'
			else:
				has_custom = '0'  '''
			x[record.id] = has_custom 
		return x
		
	def get_over_limit1(self,cr,uid, partner_id,context):
		_over=False
		sql="select credit_limit from res_partner where id='%s'" % (partner_id)
		cr.execute(sql)
		rows = cr.fetchone()
		if rows and len(rows) > 0:
			_cr_lt = float(rows[0])
			_over=self.get_over_limit2(cr,uid, partner_id, _cr_lt,context)
			
		return _over
	
	def get_over_limit2(self,cr,uid, partner_id, credit_limit,context):
		_over=False
		sql ="""select a.id,sum(a.amount_total) as amt FROM account_invoice a left join sale_order o on a.x_sale_order_id=o.id  
						left join res_partner p on a.x_project_id=p.id 
						where 
						a.state ='open'
						and a.partner_id ='%s' group by a.id""" % (partner_id)
		cr.execute(sql)
		rows = cr.fetchall()
		#if rows == None or len(rows)==0:
		##else:
		amt_total=0.0
		amt_paid=0.0
		for row in rows:
			 if row[0]!=None:
				amt_total+=float(row[1])
				invoice_id=row[0]
				sql="""select sum(p.amount) as amt_paid 
				from dincelaccount_voucher_payline p,account_invoice a,account_voucher v  
				where a.id=p.invoice_id and p.voucher_id=v.id and p.invoice_id='%s'"""	%(invoice_id)	
				cr.execute(sql)
				rows1 = cr.fetchone()
				if rows1 and rows1[0]!=None:
					amt_paid+=float(rows1[0])
		
		amt_balance=amt_total-amt_paid
		
		if credit_limit < amt_balance:
			_over=True
		else:
			_over=False
			#_logger.error("get_over_limit2.get_over_limit2["+str(partner_id)+"]["+str(credit_limit)+"]["+str(amt_total)+"]["+str(amt_balance)+"]")
		return _over
		
	def get_over_limit2xx(self,cr,uid, partner_id, credit_limit,context):
		_over=False
		sql ="select sum(amount_total) from sale_order where partner_id='%s' and state not in ('cancel','done') and x_del_status in('part','delivered')" % (partner_id)
		cr.execute(sql)
		rows = cr.fetchone()
		if rows == None or len(rows)==0:
			_over=False
		else:
			 if rows[0]!=None:
				amt_total=float(rows[0])
				sql="select sum(p.amount) from  dincelaccount_voucher_payline p,account_invoice i where p.invoice_id=i.id and i.state in('open','paid','close') and i.partner_id='%s'" % (partner_id)	
				cr.execute(sql)
				rows1 = cr.fetchone()
				if rows1 and rows1[0]!=None:
					amt_paid=float(rows1[0])
					amt_balance=amt_total-amt_paid
					if credit_limit < amt_balance:
						_over=True
						#_logger.error("get_over_limit2.get_over_limit2["+str(partner_id)+"]["+str(credit_limit)+"]["+str(amt_total)+"]["+str(amt_balance)+"]")
		return _over
		
	def cr_limit_over(self, cr, uid, ids, values, arg, context):
			
		x={}
		_over=False
		for record in self.browse(cr, uid, ids):
			if record.partner_id and record.partner_id.credit_limit>0:
				_over=self.get_over_limit2(cr, uid, record.partner_id.id, record.partner_id.credit_limit,context)
				'''sql ="select sum(amount_total) from sale_order where partner_id='%s' and state not in ('cancel','done')" % (record.partner_id.id)
				cr.execute(sql)
				rows = cr.fetchone()
				if rows == None or len(rows)==0:
					_over=False
				else:
					 if rows[0]!=None:
						amt_total=float(rows[0])
						sql="select p.amount from  dincelaccount_voucher_payline p,account_invoice i where p.invoice_id=i.id and i.state in('open','paid','close') and i.x_sale_order_id='%s'" % (record.id)
						amt_paid=float()
						if record.partner_id.credit_limit<rows[0]:
							_over=True'''
			else:
				_over=False
			x[record.id] = _over 
		return x
	
	def _get_tot_custom_lm(self, cr, uid, ids, _id, context):
		_lm=0.0
		try:
			sql ="SELECT sum(x_order_qty*x_order_length*0.001) FROM sale_order_line l,product_product p,product_template t WHERE l.product_id=p.id AND t.id=p.product_tmpl_id AND l.order_id='%s' AND  t.x_prod_cat in('customlength')" % (_id)
			cr.execute(sql)
			rows = cr.fetchone()
			if rows == None or len(rows)==0:
				_lm=0.0
			else:
				_lm=float(rows[0])
		except Exception, e:
			_lm=0.0
		'''for record in self.browse(cr, uid, ids):
			for line in record.order_line:	
				if line.product_id.x_prod_cat=='customlength':
					_qty=line.x_order_qty
					_len=line.x_order_length
					_lm+= (_qty*_len*0.001)'''
		return _lm
		
	def create_deposit_chk(self, cr, uid, ids, values, arg, context):
		x={}
		_enabled = False
		for record in self.browse(cr, uid, ids):
			has_custom	= record.x_has_custom	 #--> checks if dep inv already created or not as well...
			if has_custom == '1':
				if not record.x_deposit_exmpt:
					sql = "select p.id from product_product p,product_template t,account_invoice o,account_invoice_line l where o.id=l.invoice_id and p.id=l.product_id and p.product_tmpl_id=t.id and t.x_prod_cat='deposit' and o.state not in('refund','cancel','offset') and o.x_sale_order_id='%s' "% (record.id)
					sql += " and o.type='out_invoice'	"
					cr.execute(sql)
					#if deposit invoice alredy created no need to create again
					rows1 = cr.fetchall()
					if len(rows1) > 0:
						_enabled = False#_invoided = True..casuse already invoiced...
					else:
						_tot = self._get_tot_custom_lm(cr, uid, ids, record.id, context)
						
						# if _tot>=200.0:
						if _tot > 0.0: #NOTE: if deposit waiver then tick the option from the form...
							_enabled = True
			x[record.id] = _enabled 
		return x	
	
	def tot_invoiced(self, cr, uid, ids, values, arg, context):
		x={}
		tot_amt = 0
		#id = ids[0]
		for record in self.browse(cr, uid, ids):
			obj_inv = self.pool.get('account.invoice')
			args = [("x_sale_order_id", "=", record.id)]
			#result = obj_inv.search(cr, uid, args, context=context)
			#i=0
			tot_amt = 0.0
			_ids=obj_inv.search(cr, uid, args, context=context)
			for inv_id in _ids:#obj_inv.search(cr, uid, args, context=context):
				#i+=1
				
				_inv 	= obj_inv.browse(cr, uid, inv_id, context)
				#tot_amt	+= _inv.amount_total
				
				#if _inv.state=="close" and _inv.x_inv_type=="refund":#ignore cn closed by advance balanceing out (eg Dasco)
				#	tot_amt	+= 0.0
				#else:
				#	tot_amt	+= _inv.amount_total
				tot_amt	+= _inv.amount_total
			#for record in self.browse(cr, uid, ids):
			x[record.id]= tot_amt
		return x
	
	def tot_balance(self, cr, uid, ids, values, arg, context):
		x={}
		#tot_amt = 0
		#id = ids[0]
		for record in self.browse(cr, uid, ids):
			x[record.id]= record.amount_total-record.x_tot_invoiced
		return x
	
	def open_order_revise(self, cr, uid, ids, context=None):
		ctx = dict(context)
		compose_form_id		= self.pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'dincelaccount.view_dincelsale_order_revise_form')], limit=1) 	
		return {
				'name': _('Revise Order'),
				'type': 'ir.actions.act_window',
				'view_type': 'form',
				'view_mode': 'form',
				'res_model': 'dincelsale.order.revise',
				'views': [(compose_form_id, 'form')],
				'view_id': compose_form_id,
				'target': 'new',#current',#'target': 'new',
				'context': ctx,
			}
	
	def open_order_preview(self, cr, uid, ids, context=None):
		assert len(ids) == 1, 'This option should only be used for a single id at a time.'
		o = self.browse(cr, uid, ids)[0]
		if not o.x_order_attachs:
			self._create_sale_order_pdf(cr, uid, ids, context=context)
		
		#sql ="SELECT odoo_api_url FROM dincelaccount_config_settings"
		#cr.execute(sql)
		#rows = cr.fetchone()
		_settings=self.pool.get('dincelaccount.config.settings')
		url=_settings.report_preview_url(cr, uid, ids,"order",ids[0],context=context)		
		if url:#rows and len(rows) > 0:
			ctx = dict(context)
			#url= str(rows[0]) + "web/index.php?act=order&id="+str(ids[0])
			'''
			if o.x_order_attachs:
				ir_id=o.x_order_attachs.id
			else:
				fname="order_"+str(o.id)+".pdf"
				temp_path="/var/tmp/odoo/"+fname
				
				process=subprocess.Popen(["wkhtmltopdf", url, temp_path],stdin=PIPE,stdout=PIPE)
				
				out, err = process.communicate()
				if process.returncode not in [0, 1]:
					raise osv.except_osv(_('Report (PDF)'),
										_('Wkhtmltopdf failed (error code: %s). '
										'Message: %s') % (str(process.returncode), err))
											
				f=open(temp_path,'r')
			
				_data = f.read()
				_data = base64.b64encode(_data)
				f.close()
				
				ir_attachement_obj=self.pool.get('ir.attachment')
				document_vals = {
					'name': fname,   #                     -> filename.csv
					'datas': _data,    #                                              -> path to my file (under Windows)
					'datas_fname': fname, #           -> filename.csv 
					'res_model': self._name, #                                  -> My object_model
					'res_id': o.id,  #                                   -> the id linked to the attachment.
					'type': 'binary' 
					}
				
				ir_id = ir_attachement_obj.create(cr, uid, document_vals, context) 
				
				try:
					_obj = self.pool.get('sale.order')  
					
				except ValueError:
					ir_id = False #.......
			'''	
			return {
					  'name'     : 'Go to website',
					  'res_model': 'ir.actions.act_url',
					  'type'     : 'ir.actions.act_url',
					  'view_type': 'form',
					  'view_mode': 'form',
					  'target'   : 'current',
					  'url'      : url,
					  'context': ctx
				   }
		
	def open_invoice_preview(self, cr, uid, ids, context=None):
		assert len(ids) == 1, 'This option should only be used for a single id at a time.'
		o = self.browse(cr, uid, ids)[0]
		if o.x_account_ids:
			ctx = dict(context)
			#url="http://deverp.dincel.com.au/odoo/web/index.php?act=order_invoice&id="+str(o.id)
			#sql ="SELECT odoo_api_url FROM dincelaccount_config_settings"
			#cr.execute(sql)
			#rows = cr.fetchone()
			url=self.pool.get('dincelaccount.config.settings').report_preview_url(cr, uid, ids,"order_invoice",ids[0],context=context)		
			if url:#rows and len(rows) > 0:
				#url= str(rows[0]) + "web/index.php?act=order_invoice&id="+str(ids[0])
				if o.x_email_attachs:
					ir_id=o.x_email_attachs.id
				else:
					fname="order_invoice_"+str(o.id)+".pdf"
					temp_path="/var/tmp/odoo/account/"+fname
					
					process=subprocess.Popen(["wkhtmltopdf", url, temp_path],stdin=PIPE,stdout=PIPE)
					
					out, err = process.communicate()
					if process.returncode not in [0, 1]:
						raise osv.except_osv(_('Report (PDF)'),
											_('Wkhtmltopdf failed (error code: %s). '
											'Message: %s') % (str(process.returncode), err))
												
					f=open(temp_path,'r')
					
					_data = f.read()
					_data = base64.b64encode(_data)
					f.close()
					
					ir_attachement_obj=self.pool.get('ir.attachment')
					document_vals = {
						'name': fname,   #                     -> filename.csv
						'datas': _data,    #                                              -> path to my file (under Windows)
						'datas_fname': fname, #           -> filename.csv 
						'res_model': self._name, #                                  -> My object_model
						'res_id': o.id,  #                                   -> the id linked to the attachment.
						'type': 'binary' 
						}
					
					ir_id = ir_attachement_obj.create(cr, uid, document_vals, context) 
					
					try:
						_obj = self.pool.get('sale.order')  
						_obj.write(cr, uid, o.id, {'x_email_attachs': ir_id})  
					except ValueError:
						ir_id = False #.......
				
				return {
						  'name'     : 'Go to website',
						  'res_model': 'ir.actions.act_url',
						  'type'     : 'ir.actions.act_url',
						  'view_type': 'form',
						  'view_mode': 'form',
						  'target'   : 'current',
						  'url'      : url,
						  'context': ctx
					   }
		else:
			raise osv.except_osv(_('Invoice missing'),_('No invoice have been created yet.'))

	def _create_sale_order_pdf(self, cr, uid, ids, context=None):			
		assert len(ids) == 1, 'This option should only be used for a single id at a time.'
		o = self.browse(cr, uid, ids)[0]
		_settings=self.pool.get('dincelaccount.config.settings')
		url=_settings.report_preview_url(cr, uid, ids,"order",ids[0],context=context)		
		_config_id = _settings.search(cr,uid,[('id', '>', '0')], limit=1)
		
			
		#if o.x_account_ids:
		ir_id = False
		if url:#rows and len(rows) > 0:
			ctx = dict(context)
			url=url.replace("erp.dincel.com.au/", "localhost/")
			#url= str(rows[0]) + "web/index.php?act=order&id="+str(ids[0])
			if o.x_order_attachs:
				return o.x_order_attachs.id
			else:
				fname="order_"+str(o.name)+".pdf"
				temp_path="/var/tmp/odoo/sale/"+fname
				
				process=subprocess.Popen(["wkhtmltopdf", url, temp_path],stdin=PIPE,stdout=PIPE)
				
				out, err = process.communicate()
				if process.returncode not in [0, 1]:
					raise osv.except_osv(_('Report (PDF)'),
										_('Wkhtmltopdf failed (error code: %s). '
										'Message: %s') % (str(process.returncode), err))
											
				if _config_id:
					_conf= _settings.browse(cr, uid, _config_id, context=context)
					if _conf and _conf.order_attachment:
						
						#location =self.pool['ir.config_parameter'].get_param(cr, SUPERUSER_ID, 'ir_attachment.location', 'file')
						
						#location = self.pool.get('ir.attachement')._filestore(cr,uid)
						#if not location:
						location = config['data_dir'] + "/filestore/" + str(cr.dbname) #todo user _filstore()...
						_file_terms=location+"/"+_conf.order_attachment.store_fname
						
						
						
						_file_new="/var/tmp/odoo/sale/"+"order-"+str(o.id)+".pdf"
						
						_ret=_settings.merge_pdf_files(temp_path,_file_terms,_file_new)
						if _ret:
							temp_path=_file_new
							
				f=open(temp_path,'r')
			
				_data = f.read()
				_data = base64.b64encode(_data)
				f.close()
				
				ir_attachement_obj=self.pool.get('ir.attachment')
				document_vals = {
					'name': fname,   #                     -> filename.csv
					'datas': _data,    #                                              -> path to my file (under Windows)
					'datas_fname': fname, #           -> filename.csv 
					'res_model': self._name, #                                  -> My object_model
					'res_id': o.id,  #                                   -> the id linked to the attachment.
					'type': 'binary' 
					}
				
				ir_id = ir_attachement_obj.create(cr, uid, document_vals, context) 
				
				try:
					_obj = self.pool.get('sale.order')  
					_obj.write(cr, uid, o.id, {'x_order_attachs': ir_id})  
				except ValueError:
					ir_id = False #......
					
		return ir_id
		
	def download_invoice_pdfxx(self, cr, uid, ids, context=None):
		fname="odoo_test.pdf"
		temp_path="/var/tmp/odoo/"+fname
		#if os.path.exists(temp_path):
		#	os.unlink(temp_path)
		#/f=open(temp_path,'w')
		
		#f.close();
		#_logger.error("generate_aba_testgenerate_aba_test2 ["+str(_str)+"]")
		return {'type' : 'ir.actions.act_url',
				'url': '/web/binary/some_html?f='+str(fname)+'&c=a',
				'target': 'self',}
	
	
	@api.multi 
	def loadsheet_pdf_byid(self, _id):
		o =self.env['sale.order'].browse(_id)
		#o=self.pool.get('sale.order').browse(cr, uid, _id, context)
		context = self._context.copy() 
		#url=self.pool.get('dincelaccount.config.settings').report_preview_url(cr, uid, ids,"loadsheet",_id,context=context)		
		url=self.env['dincelaccount.config.settings'].report_preview_url("loadsheet",_id)		
		if url:#rows and len(rows) > 0:
			
			fname="loadsheet"+str(o.id)+".pdf"
			save_path="/var/tmp/odoo/sale"
			
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
			#/web/binary/download_document?model=wizard.product.stock.report&amp;field=datas&amp;id=%s&amp;filename=product_stock.xls
			'''# 'name'     : 'Go to website',
					'res_model': 'ir.actions.act_url',
					'type'     : 'ir.actions.act_url',
					'view_type': 'form',
					'view_mode': 'form',
					'target'   : 'current',
					'url'      : url,
					'context': ctx'''
			return {
					'name': 'Load Sheet',
					'res_model': 'ir.actions.act_url',
					'type' : 'ir.actions.act_url',
					'url': '/web/binary/download_file?model=sale.order&field=datas&id=%s&path=%s&filename=%s' % (str(o.id),save_path,fname),
					'context': context}
	@api.multi 
	def print_pdf_load_sheet_dcs(self):
	#def print_pdf_load_sheet_dcs(self, cr, uid, ids, context=None):#self, cr, uid,  _id, context=None):
		#view_id = self.env.ref('dincelaccount.view_dincelaccount_voucher_invoice_form').id
		#context = self._context.copy()
		return self.loadsheet_pdf_byid(self.id)
	 
 
	
	def check_discount_allowed(self, cr, uid, ids, _id, context=None):
		o = self.browse(cr, uid, _id)
		for line in o.order_line:
			if line.x_order_qty<0 and o.x_authorise_discount==False:
				return -1
			elif (line.discount and line.discount!=0.0):
				if o.x_authorise_discount==False:
					return 1
			else:
				#_logger.error("check_discount_allowedcheck_discount_allowed["+str(line.name)+"]["+str(line.price_unit )+"]["+str(o.x_authorise_discount )+"]")
				if (not line.price_unit or float(line.price_unit)==0.0):
					#raise osv.except_osv(
					#	_('Discount found!'),
					#	_('The discount applied is not authorised, please contact account or your manager to continue.'))
					if o.x_authorise_discount==False:
						return 1
		return 0
	
	def check_discount_allowed_message(self, cr, uid, ids, _id, context=None):
		chk=self.check_discount_allowed(cr, uid, ids, _id) 
		if chk==-1:
			raise osv.except_osv(
						_('Negative quantity found!'),
						_('Please contact account or your manager to continue.'))
		elif chk==1:
			raise osv.except_osv(
						_('Discount found!'),
						_('The discount applied is not authorised, please contact account or your manager to continue.'))
		return 1
		
	def send_invoice_email(self, cr, uid, ids, context=None):
		#compose_form_id=False
		#compose_form_id='dincelaccount_email_compose_message_form'	#False
		compose_form_id = self.pool.get('ir.ui.view').search(cr,uid,[('name', '=', 'dincelaccount.mail.compose.message.form')], limit=1)
		 
		_inv_ids=[]
		assert len(ids) == 1, 'This option should only be used for a single id at a time.'
		ir_model_data = self.pool.get('ir.model.data')
		o = self.browse(cr, uid, ids)[0]
		try:
			#chk=self.check_discount_allowed_message(cr, uid, ids, o.id) 
			#if chk!=1:
			#	return
			'''chk=self.check_discount_allowed(cr, uid, ids, o.id) 
			if chk==-1:
				raise osv.except_osv(
							_('Negative quantity found!'),
							_('Please contact account or your manager to continue.'))
			elif chk==1:
				raise osv.except_osv(
							_('Discount found!'),
							_('The discount applied is not authorised, please contact account or your manager to continue.'))
			'''				
			template_id = ir_model_data.get_object_reference(cr, uid, 'dincelaccount', 'email_template_edi_saleorder_invoice')[1]
			email_obj   = self.pool.get('email.template')  
			 
			#get the id of the document, stored into field scanned
			#write the new attachment to mail template
			_atths=[]
			for line in o.x_account_ids:
				 
				if not line.x_invoice_attach:
					self.pool.get('account.invoice').create_invoice_pdf(cr, uid, ids,  {}, line.id)
				if line.x_invoice_attach and line.sent == False:
					_atths.append(line.x_invoice_attach.id)
					_inv_ids.append(line.id)
						#no_invoice=False
			if o.x_order_attachs and o.x_order_attachs.id:
				#_atths.append(o.x_order_attachs.id)
				#if o.x_order_attachs and o.x_order_attachs.id:
				#@_atths.append(o.x_order_attachs.id)
				self.pool['ir.attachment'].unlink(cr, uid, [o.x_order_attachs.id], context=context)
			#else:
			_id=self._create_sale_order_pdf(cr, uid, ids, context=context)
			if _id:
				_atths.append(_id)
			#ir_obj = self.pool.get('ir.attachement')
			ir_ids = self.pool['ir.attachment'].search(cr, uid, [('res_id', '=', ids[0]),('res_model', '=', 'sale.order'),], context=context)
			for _id in ir_ids:
				_atths.append(_id)
				
			email_obj.write(cr, uid, template_id, {'attachment_ids': [(6, 0, _atths)]})  #clears if any in session...if array is an empty....

		except ValueError:
			template_id = False #.......
		 
		_contact= self.pool.get('res.partner')
		
		lids1	= _contact.search(cr, uid, [('parent_id','=',o.partner_id.id),('x_is_project', '=', False)])	#site contacts
		lids2	= _contact.search(cr, uid, [('parent_id','=',o.x_project_id.id),('x_is_project', '=', False)])  #client contacts
		#_ids	= [lids1+lids2]
			
		fol_obj = self.pool.get('mail.followers')
		fol_ids = fol_obj.search(cr, uid, [
			('res_id', '=',  ids[0]),
			('res_model', '=', 'sale.order'),
		], context=context)
		
		lids3 = []
		def_ids = []
		'''
		for fol in fol_obj.browse(cr, uid, fol_ids, context=context):	
			lids3.append(fol.partner_id.id)
			def_ids.append(fol.partner_id.id)
		#if o.user_id and o.user_id.partner_id:
		#	if not o.user_id.parent_id.id in lids3:
		#		lids3.append(o.user_id.parent_id.id)
		if o.x_contact_id:
			def_ids.append(o.x_contact_id.id)
			'''
		lids4 = []
		if o.user_id:
			lids4.append(o.user_id.partner_id.id)
		_config_id = self.pool.get('dincelaccount.config.settings').search(cr,uid,[('id', '>', '0')], limit=1)
		if _config_id:
			_conf= self.pool.get('dincelaccount.config.settings').browse(cr, uid, _config_id, context=context)
			if _conf and _conf.invoice_cc_ids:
				#_logger.error("fol.partner_idfol.partner_idfol.partner_id ["+str(_config_id)+"]["+str(_conf.invoice_cc_ids)+"]")
				for _part in _conf.invoice_cc_ids:	
					lids4.append(_part.id)
					#_logger.error("fol.partner_idfol.partner_idfol.partner_id_id_id ["+str(_part.id)+"]")#	lids4.append(_id)
		
		
		#_ids.append(fol.partner_id.id)
		_ids 	= [lids1+lids2+lids3+lids4]		
		#def_ids = [def_ids+lids4] >>removed this conditions...no default [8/5/2017] as per MH request
		
		
		ctx = dict(context)
		if template_id:
			ctx.update({
				'default_model': 'sale.order',
				'default_res_id': ids[0],
				'default_use_template': bool(template_id),
				'default_template_id': template_id,
				'default_subject': "Re. %s [%s] " % (o.x_project_id.name, o.name), 
				'default_composition_mode': 'comment',
				'mark_as_sent':True, #see below >>> inherit class >> "accountmail_compose_message"
				'default_inv_ids':_inv_ids,
				'domain_contact_ids':_ids,
				'default_partner_ids':[''],
				'default_contact_ids':[''],
				'default_contact_sel_ids':[''],
				
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
		#return True
	def button_print_loadsheet_ibt(self, cr, uid, ids, context=None):
		order_id=ids[0]
		fname="ibtorder_"+str(order_id)+".pdf"
		save_path="/var/tmp/odoo/docket/"
		temp_path=save_path+fname
		 
		url=self.pool.get('dincelaccount.config.settings').report_preview_url(cr, uid, ids,"loadsheetibt",order_id,context=context)	
		url+="&loadsheetibt=1" 
		
		#"--orientation",'landscape', 
		process=subprocess.Popen(["wkhtmltopdf",
									'--margin-top','0', 
									'--margin-left','0', 
									'--margin-right','0', 
									'--margin-bottom','0', 
									url, temp_path], stdin=PIPE, stdout=PIPE)
		out, err = process.communicate()
		if process.returncode not in [0, 1]:
			raise osv.except_osv(_('Report (PDF)'),
								_('Wkhtmltopdf failed (error code: %s). '
								'Message: %s') % (str(process.returncode), err))
		
		f=open(temp_path,'r')
		
		_data = f.read()
		_data = base64.b64encode(_data)
		f.close()
		
		 
		return {
				'type' : 'ir.actions.act_url',
				'url': '/web/binary/download_file?model=dincelstock.transfer&field=datas&id=%s&path=%s&filename=%s' % (str(order_id),save_path,fname),
				'target': 'self',
			}
			
		
	def markas_send_email(self, cr, uid, ids, context=None):
		assert len(ids) == 1, 'This option should only be used for a single id at a time.'
		o = self.browse(cr, uid, ids)[0]
		for line in o.x_account_ids:
			if not line.x_invoice_attach:
				self.pool.get('account.invoice').create_invoice_pdf(cr, uid, ids,  {}, line.id)
		return self.pool.get('sale.order').write(cr, uid, ids[0], {'x_sent': True,'state':'sent'}) 
		
	def confirm_delivery_sales_order_xx(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		order_obj 	= self.pool.get('sale.order')
		obj_line 	= self.pool.get('sale.order.line')
		pick_obj 	= self.pool.get('dincelstock.pickinglist')
		line_obj 	= self.pool.get('dincelstock.pickinglist.line')
		ar_items_done 	= {}
		ar_items_rem  	= {}
		
		tot_qty_rem 	= 0
		found			= False
		for record in self.browse(cr, uid, ids, context=context):	
			sql = "select * from dincelstock_pickinglist_line where origin='%s' " % record.name
			cr.execute(sql)
			rows1 	= cr.dictfetchall()
			for row1 in rows1:
				ship_qty = row1['ship_qty']
				product_id = row1['product_id']
				order_length = row1['order_length']
				skey	= str(product_id) + "_" + str(order_length)
				if ar_items_done.has_key(skey) == False:
					ar_items_done[skey] = ship_qty
				else:
					ar_items_done[skey] += ship_qty
			
		
			for line in record.order_line:
				qty = line.x_order_qty
				product_id = line.product_id.id
				order_length = line.x_order_length
				skey	= str(product_id) + "_" + str(order_length)
				if ar_items_done.has_key(skey):
					qty = qty - ar_items_done[skey]
			
				tot_qty_rem += qty		
				
			#only if any remain qty is greater than zero
			if tot_qty_rem > 0 :
				sql = "select 1 from dincelstock_pickinglist  where origin='%s' " % record.name
				cr.execute(sql)
				count1 	= cr.rowcount
			
				sname_deli = record.name + "-" + str(count1+1)#"/"  #todo generated auto number
				vals = {
					'pick_order_id': record.id,
                    'origin': record.name,
                    'partner_id': record.partner_id.id,
					'name':sname_deli,
					'user_id':uid
					}
			
				vals['date_picking']=datetime.datetime.now() 
				#first create the invoice record
				pick_id = pick_obj.create(cr, uid, vals, context=context)
				
				#now loop throught all item lines and create invoice line if net qty remaining is greater than zero
				for line in record.order_line:
					qty = line.x_order_qty
					product_id = line.product_id.id
					order_length= line.x_order_length
					skey	= str(product_id) + "_" + str(order_length)
					if ar_items_done.has_key(skey):
						qty = qty - ar_items_done[skey]		
					if qty > 0:
						
						vals = {
							'product_id': product_id,
							'ship_qty': qty,
							'pickinglist_id': pick_id,
							'origin': record.name,
							'order_length': line.x_order_length,
							'price_unit': line.price_unit,
							'disc_pc':line.discount,
						}
						vals['name']= line.product_id.name
							
						line_obj.create(cr, uid, vals, context=context)
						
				found = True

				view_id = self.pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'dincelstock.delivery.form.view')], limit=1) 	
				#_logger.error("invoice_sales_validate.view_id["+str(view_id)+"]")
				value = {
                    'domain': str([('id', 'in', pick_id)]),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'dincelstock.pickinglist',
                    'view_id': view_id,
                    'type': 'ir.actions.act_window',
                    'name' : _('Delivery'),
                    'res_id': pick_id
                }
				return value				
				#return pick_id
		if found == False:
			raise osv.except_osv(_('No delivery remaining!'), _('No pending delivery found!'))
		return False
	
	def _over_due_check(self, cr, uid, ids, values, arg, context):
		
		x1={}
		_due=''
		for record in self.browse(cr, uid, ids):#for record in self.browse(cr, uid, ids):
			 
			sql ="SELECT i.date_invoice,t.x_payterm_code,t.id FROM account_invoice i,account_payment_term t WHERE i.payment_term=t.id and i.state='open' and i.x_inv_type in ('full','balance') and i.partner_id='%s' " % (str(record.partner_id.id))
			cr.execute(sql)
			
			rows = cr.fetchall()
			if rows == None or len(rows)==0:
				_due= ''
			else:
				for row in rows:
					_dt=row[0]
					_term=row[1] #COD,30EOM,immediate,7DAYS,14DELI,14DAYS
					_termid=row[2] 
					is_due=self._date_due_check(cr, uid, ids, _termid, _dt, context)	
					if is_due:
						_due="Y"
						break
			x1[record.id] = _due 
		return x1
	
	def _date_due_check(self, cr, uid, ids, _termid, _dt, context):
		#dt_due = date.today()
		dt_now = datetime.datetime.strptime(str(date.today()), '%Y-%m-%d')  #date.today()
		#_dt1=datetime.datetime.strptime(_dt, '%Y-%m-%d') 
		#dt_due = self.get_due_date(cr, uid, ids,_term, _dt, _dt)
		dt_due = self.get_due_date_v2(cr, uid, ids,_termid, _dt, _dt)
		#---converting to datetime/date format for compare condition...
		dt_now 	= dateutil.parser.parse(str(dt_now))
		dt_due 	= dateutil.parser.parse(str(dt_due))
		'''
		
		if _term=="30EOM":
			_due = _dt1 + relativedelta(months=+2)
			_due_dt=str(_due.year) +"-"+str(_due.month)+"-1"
			dt_due=datetime.datetime.strptime(_due_dt, '%Y-%m-%d')
			#case "immediate":
			#case "COD":
			#	printf("n is a perfect square\n");
			#	break;
		elif _term=="7DAYS":
			dt_due = _dt1 + relativedelta(days=+7)
		elif _term=="14DELI" or _term=="14DAYS":
			dt_due = _dt1 + relativedelta(days=+14)
		else:
			#dt_due = date.today()
			dt_due=datetime.datetime.strptime(str(date.today()), '%Y-%m-%d')  '''
		if dt_due < dt_now:
			return True
		else:
			return False
	
	def get_colorname(self, cr, uid, ids, values, arg, context):
			
		x1={}
		_colr=''
		for record in self.browse(cr, uid, ids):#for record in self.browse(cr, uid, ids):
			if record.x_colorcode:
				sql ="SELECT name FROM dincelbase_color WHERE color_hex='%s' " % (record.x_colorcode)
				cr.execute(sql)
				rows = cr.fetchone()
				if rows == None or len(rows)==0:
					_colr= ''
				else:
					_colr= rows[0]
			else:
				_colr=''
			x1[record.id] = _colr 
		return x1
		
	def _create_bal_inv(self, cr, uid, ids, values, arg, context):
		x={}
		_ret=True
		for record in self.browse(cr, uid, ids):
			_bal=record.x_tot_balance
			if _bal>0.9:#ignore below 90cents..todo...if rqud make it >0.0....but due to rounding issue it can have issues...
				_ret=True
			else:
				_ret=False
			x[record.id] = _ret 
		return x
		
	def has_invoice(self, cr, uid, ids, values, arg, context):
		x={}
		_ret=False
		for record in self.browse(cr, uid, ids):
			if record.x_revise_sn>0:
				sql ="SELECT 1 FROM account_invoice WHERE x_sale_order_id='%s' AND x_revise_sn='%s' and state not in ('cancel','refund','close')" % (record.id, record.x_revise_sn)
			else:
				sql ="SELECT 1 FROM account_invoice WHERE x_sale_order_id='%s' AND x_inv_type = 'balance' and state not in ('cancel','refund','close') " % (record.id)
			cr.execute(sql)
			#_logger.error("invoice_sales_validate.has_invoicehas_invoice["+str(sql)+"]")
			rows = cr.fetchone()
			if rows:
				if len(rows)> 0:
					_ret = True
			x[record.id] = _ret 
		return x
	
	#donot use but refering in col definition only
	def _pending_invoice(self, cr, uid, ids, values, arg, context):
		x1={}
		#_ret=True
		'''
		for record in self.browse(cr, uid, ids):#for record in self.browse(cr, uid, ids):
			if record.state in ('cancel','done'):
				_ret=False
			else:
				cur_date = datetime.datetime.now().date()
				new_date = cur_date - datetime.timedelta(hours=24)
				entry_dt = dateutil.parser.parse(record.create_date).date()
				#if order_date > new_date:
				#_create_dt=datetime.datetime.strptime(record.create_date,"%Y-%m-%d %H:%M:%S.%f")
				#_inv_date	=  datetime.datetime.strptime(str(_create_dt + timedelta(hours=24)),"%Y-%m-%d %H:%M:%S.%f")
				#_now 	=  datetime.datetime.strptime(str(datetime.datetime.now()),"%Y-%m-%d %H:%M:%S.%f")
				
				#_logger.error("invoice_sales_validate._pending_invoice_pending_invoice[%s][%s][%s][%s]" % (record.id, cur_date,new_date,entry_dt ))
				_ret=True
				if new_date > entry_dt:
					if record.payment_term.x_payterm_code=="COD":
						sql="select 1 from account_invoice where x_sale_order_id='%s' and type='out_invoice' and state in ('draft','open','paid')" % (record.id)
						cr.execute(sql)
						rows = cr.fetchone()
						if rows:
							if len(rows)> 0:
								_ret = False
					else:#account x_create_deposit
						if record.x_create_deposit==True:
							sql="select 1 from account_invoice where x_sale_order_id='%s' and type='out_invoice' and  state in ('draft','open','paid')"  % (record.id)
							cr.execute(sql)
							rows = cr.fetchone()
							if rows:
								if len(rows)> 0:
									_ret = False
		'''
		#x1[record.id] = _ret 
		return x1
		
	def _balance_paid(self, cr, uid, ids, values, arg, context):
		x1={}
		_ret=''
		for record in self.browse(cr, uid, ids):#for record in self.browse(cr, uid, ids):
			
		
			x1[record.id] = _ret 
		return x1
	
	def _deposit_paid(self, cr, uid, ids, values, arg, context):
		x1={}
		_ret=''
		for record in self.browse(cr, uid, ids):#for record in self.browse(cr, uid, ids):
			#_ret = self._update_payment_deposit(cr, uid, ids, record.id, context=context)
			'''if record.x_deposit_exmpt:
				_ret= 'NA'
			else:
				sql ="SELECT 1 FROM sale_order_line l,product_product p,product_template t WHERE l.product_id=p.id AND t.id=p.product_tmpl_id AND l.order_id='%s' AND  t.x_prod_cat in('customlength')" % (record.id)
				cr.execute(sql)
				rows = cr.fetchone()
				if rows == None or len(rows)==0:
					_ret= 'NA'
				else:	
					sql ="SELECT state FROM account_invoice WHERE x_inv_type='deposit' AND type='out_invoice' AND x_sale_order_id='%s' " % (record.id)
					cr.execute(sql)
					rows = cr.fetchone()
					if rows == None or len(rows)==0:
						_ret= ''
					else:
						_ret= rows[0]'''
		
			x1[record.id] = _ret 
		return x1
	
	def _has_custom_profile(self, cr, uid, ids, _id, context):
		 
		sql = "select p.id  from product_product p,product_template t,sale_order_line o where p.id=o.product_id and p.product_tmpl_id=t.id and t.x_prod_cat='customlength' and o.order_id='%s' " % (_id)
		cr.execute(sql)
		rows = cr.fetchall()
		if len(rows) > 0:
			return True
		else:
			return False
	 
		
	def _dep_invoice_rqd(self,cr, uid, ids, _id, _dep_ex, context):
		_enabled=False
		if _dep_ex==True:
			return False
		else:
			has_custom=self._has_custom_profile(cr, uid, ids, _id, context)
			if has_custom==False:
				return False
			else:
				_tot= self._get_tot_custom_lm(cr, uid, ids, _id, context)
				#_tot>=200.0 to 0.0
				if _tot>0.0:#NOTE: if deposit waiver then tick the option from the form...
					return True
		return False
						
	def _deposit_amt(self, cr, uid, ids, values, arg, context):
		x1={}
		_ret=''
		for record in self.browse(cr, uid, ids):#for record in self.browse(cr, uid, ids):
			sql ="select i.check_total from account_invoice i,sale_order o where i.x_sale_order_id=o.id and o.id='%s' and i.x_inv_type in('deposit','balance1') and i.type='out_invoice' and i.state in('open','paid','close') " % (record.id)
			cr.execute(sql)
			rows = cr.fetchall()
			#if str(record.id)=="136":
			#	_logger.error("_dep_invoice_rqd_dep_invoice_rqd["+str(record.id)+"]["+str(rows)+"]")
			if rows and len(rows)>0:#deposit invoice found and return the value
				_ret1=0.0
				for row in rows:
					if row[0]:
						try:
							_ret1+= float(row[0])
						except Exception, e:
							_ret1+=0.0
				_ret=_ret1	
			else:
				_dep=self._dep_invoice_rqd(cr, uid, ids, record.id, record.x_deposit_exmpt, context)
				#if str(record.id)=="136":
				#	_logger.error("_dep_invoice_rqd_dep_invoice_rqd_dep_dep["+str(record.id)+"]["+str(_dep)+"]")
				if _dep==True:#deposit required	 but no invoice yet
					_ret=''
				else:
					_ret='NA' #==NA
			x1[record.id] = _ret 
		return x1
	
	def _balance_amt(self, cr, uid, ids, values, arg, context):
		x1={}
		_ret=0.0
		for record in self.browse(cr, uid, ids):#for record in self.browse(cr, uid, ids):
			sql ="select sum(i.check_total) from account_invoice i,sale_order o where i.x_sale_order_id=o.id and o.id='%s' and i.x_inv_type in('balance','full') and i.type='out_invoice' and i.state in('open','paid','close') " % (record.id)
			cr.execute(sql)
			rows = cr.fetchone()
			if rows and rows[0]:
				_ret= float(rows[0])
			else:
				_ret=0.0
			x1[record.id] = _ret 
		return x1	
		
	def _attach_110_found(self, cr, uid, ids, values, arg, context):
		x1={}
		_ret=False
		for record in self.browse(cr, uid, ids):
			if record.x_attach_110 and len(record.x_attach_110)>0:
				_ret=True
			else:
				_ret=False
			x1[record.id] = _ret 
		return x1	
	
	def _attach_155_found(self, cr, uid, ids, values, arg, context):
		x1={}
		_ret=False
		for record in self.browse(cr, uid, ids):
			if record.x_attach_155 and len(record.x_attach_155)>0:
				_ret=True
			else:
				_ret=False
			x1[record.id] = _ret 
		return x1	
	
	def _attach_200_found(self, cr, uid, ids, values, arg, context):
		x1={}
		_ret=False
		for record in self.browse(cr, uid, ids):
			if record.x_attach_200 and len(record.x_attach_200)>0:
				_ret=True
			else:
				_ret=False
			x1[record.id] = _ret 
		return x1	
	
	def _attach_275_found(self, cr, uid, ids, values, arg, context):
		x1={}
		_ret=False
		for record in self.browse(cr, uid, ids):
			if record.x_attach_275 and len(record.x_attach_275)>0:
				_ret=True
			else:
				_ret=False
			x1[record.id] = _ret 
		return x1		
	
	def _balance_paid_amt(self, cr, uid, ids, values, arg, context):
		x1={}
		_ret=0.0
		for record in self.browse(cr, uid, ids):#for record in self.browse(cr, uid, ids):
			sql ="select sum(p.amount) from dincelaccount_voucher_payline p,account_invoice i,sale_order o where p.invoice_id=i.id and i.x_sale_order_id=o.id and o.id='%s' and i.x_inv_type in('balance','full') and i.type='out_invoice' and i.state in('open','paid','close') " % (record.id)
			cr.execute(sql)
			rows = cr.fetchone()
			if rows and rows[0]:
				_ret= float(rows[0])
			else:
				_ret=0.0
			x1[record.id] = _ret 
		return x1
		
	def _deposit_paid_amt(self, cr, uid, ids, values, arg, context):
		x1={}
		_ret=0.0
		for record in self.browse(cr, uid, ids):#for record in self.browse(cr, uid, ids):
			sql ="select sum(p.amount) from dincelaccount_voucher_payline p,account_invoice i,sale_order o where p.invoice_id=i.id and i.x_sale_order_id=o.id and o.id='%s' and i.x_inv_type in('deposit','balance1') and i.type='out_invoice' and i.state in('open','paid','close') " % (record.id)
			cr.execute(sql)
			rows = cr.fetchone()
			if rows and rows[0]:
				_ret= float(rows[0])
			else:
				_ret=0.0
			x1[record.id] = _ret 
		return x1	
		
	def _update_payment_deposit(self, cr, uid, ids, _id, context=None):
		obj 	= self.pool.get('sale.order').browse(cr, uid, _id, context=context)
		x_dep	= ''
		 
		if obj.x_deposit_exmpt:
			x_dep= 'NA'
		else:
			sql ="SELECT 1 FROM sale_order_line l,product_product p,product_template t WHERE l.product_id=p.id AND t.id=p.product_tmpl_id AND l.order_id='%s' AND  t.x_prod_cat in('customlength')" %  (str(_id))
			cr.execute(sql)
			rows = cr.fetchone()
			if rows == None or len(rows)==0:
				x_dep= 'NA'
			else:	
				_dep_rqd=self._dep_invoice_rqd(cr, uid, ids, obj.id, obj.x_deposit_exmpt, context)
				if _dep_rqd==False:
					x_dep= 'NA'
				else:
					#.ignore offset...invoices...which are cancelled type...
					sql ="SELECT state FROM account_invoice WHERE x_inv_type='deposit' AND type='out_invoice' AND x_sale_order_id='%s' and state !='offset' " %  (str(_id))
					cr.execute(sql)
					rows = cr.fetchone()
					if rows == None or len(rows)==0:
						x_dep= ''
					elif rows[0]=="paid":
						x_dep= rows[0]
					else:
						x_dep= ''
		#if _id <832 and x_dep=="paid":
		#	x_dep="paid"
		#	pass
		#else:
			if x_dep=="paid":
				
				sql="select 1 from dincelbase_notification where res_model='sale.order' and res_id='%s' and code='dep_paid'" % (str(_id))
				cr.execute(sql)	
				rows = cr.fetchone()
				if rows == None or len(rows)==0:
					val={
						"res_model":"sale.order",
						"name":obj.name,
						"res_id":_id,
						"code":"dep_paid",
						"state":"",
					}
					self.pool.get('dincelbase.notification').create(cr, uid, val, context=context)
					
			sql ="UPDATE sale_order SET  x_dep_paid='"+x_dep+"' "	# WHERE id='"+str(ids[0])+"'"
			sql += " WHERE id='"+str(_id)+"'"	
			#	#_logger.error("updatelink_order_dcs.updatelink_sqlsqlsql["+str(sql)+"]")	
			cr.execute(sql)		
		return x_dep  
		
	def _update_payment_balance(self, cr, uid, ids, _id, context=None):
		sql ="SELECT state FROM account_invoice WHERE x_inv_type='balance' AND state in ('open','paid','close') AND type='out_invoice' AND x_sale_order_id='%s' " % (str(_id))
		cr.execute(sql)
		rows_chk = cr.fetchall()
		x_bal=''
		if rows_chk == None or len(rows_chk)==0:
			x_bal= ''
		else:
			for row in rows_chk: #if more than one invoice
				if row[0]=="paid" or row[0]=="close":
					#@_paid=True
					x_bal='paid'
				else:#found open (or not paid) if more than one invoice
					if x_bal=='paid' or row[0]=="close":
						x_bal='part'
					elif x_bal=='part':
						x_bal='part'
					else:	
						x_bal=''
					#x_bal='part'
			#if _id <832 and x_bal=="paid":
			#	x_bal="paid"
			#	pass
			#else:
			sql ="UPDATE sale_order SET x_bal_paid='"+x_bal+"' "	# WHERE id='"+str(ids[0])+"'"
			sql += " WHERE id='"+str(_id)+"'"	
			#	#_logger.error("updatelink_order_dcs.updatelink_sqlsqlsql["+str(sql)+"]")	
			cr.execute(sql)
		return x_bal
	
	def _acct_status(self, cr, uid, ids, values, arg, context):
		x={}
		
		for record in self.browse(cr, uid, ids):
			_ret="N"
			sql="select p.credit_limit from res_partner p,sale_order o where o.partner_id=p.id and o.id='%s' " % (record.id)
			cr.execute(sql)	
			rows = cr.fetchone()
			if rows and len(rows)>0:
				if rows[0] and float(rows[0])>0.0:
					_ret="Y"
			'''
			if record.partner_id and record.partner_id.credit_limit:#error occured due to credit limit not set in someitems..../etc//
				if float(record.partner_id.credit_limit)>0.0:
					_ret="Y"
				else:
					_ret="N"
			else:
				_ret="N"'''
			x[record.id]=_ret 
		return x
		
	#def trucks_mismatch_found(self,cr,uid,ids, _id,context):
	#	_mismatch=False
	#	
	#	return _mismatch
		
	def mrp_missing_found(self,cr,uid,ids, _id,context):
		_missing=False
		obj 	= self.pool.get('sale.order').browse(cr, uid, _id, context=context)
		for line in obj.order_line:
			_cat	=line.product_id.x_prod_cat
			 
			if line.product_id and _cat !='freight' and line.product_id.type !="service":	
				qty_order	= line.x_order_qty
				qty_already	= 0
				_product_id	= line.product_id.id
				_len		= int(line.x_order_length)
				_lenchk		= False
				sql	= "SELECT SUM(reserve_qty) AS qty FROM dincelmrp_production_reserve WHERE product_id='"+str(_product_id)+"' AND order_id ='"+str(_id)+"'"
				if _cat in['stocklength','customlength']:#line.product_id.x_prod_cat=="customlength":
					if  line.product_id.x_prod_type != "acs":#NON P-3 only 
						sql  	= sql + " AND order_length='"+str(_len)+"'"
						_lenchk = True
				sql  	= sql + " UNION ALL "
				sql  	= sql + " SELECT SUM(x_order_qty) AS qty FROM mrp_production WHERE product_id='"+str(_product_id)+"' AND x_sale_order_id ='"+str(_id)+"'"
				if _lenchk:
					sql  	= sql + " AND x_order_length='"+str(_len)+"'"
				cr.execute(sql)
				rows = cr.fetchall()
				for row in rows:
					if row[0]:
						qty_already += int(row[0])
					
				'''	
				sql2res ="select sum(reserve_qty) from dincelmrp_production_reserve where product_id='"+str(_product_id)+"' and order_id ='"+str(_id)+"'"
				sql 	="select sum(x_order_qty) from mrp_production where product_id='"+str(_product_id)+"' and x_sale_order_id ='"+str(_id)+"'"
				if _cat in['stocklength','customlength']:#line.product_id.x_prod_cat=="customlength":
					if  line.product_id.x_prod_type != "acs":#NON P-3 only 
						sql  	=sql + " and x_order_length='"+str(_len)+"'"
						sql2res =sql2res + " and order_length='"+str(_len)+"'"'''
				
				 
				remaining	= qty_order-qty_already
				if remaining != 0:
					_missing = True 
					break
		'''if _missing==False:
			sql="select product_id,order_length,sum(reserve_qty) as qty from dincelmrp_production_reserve where order_id ='"+str(_id)+"' group by product_id,order_length  union all "
			sql+=" select product_id,x_order_length as order_length,sum(x_order_qty) as qty from mrp_production where x_sale_order_id ='"+str(_id)+"' group by product_id,x_order_length "
			cr.execute(sql)
			rows = cr.dictfetchall()
			for row in rows:
				prodid=row['product_id']
				qty=int(row['qty'])
				order_length=int(row['order_length'])
				sql = "select sum(x_order_qty) from sale_order_line where product_id='%s' and order_id='%s' and x_order_length='%s'" %(prodid,_id,order_length)
				cr.execute(sql)
				res1 = cr.fetchone()
				if res1 and res1[0]!= None:  
					qty2=int(res1[0])
				else:
					qty2=0
				if qty2-qty!=0:
					_missing=True 
					break'''
		return _missing	
		
	def _mrp_missing(self, cr, uid, ids, values, arg, context):
		x={}
		for record in self.browse(cr, uid, ids):
			x[record.id] = self.mrp_missing_found(cr, uid, ids, record.id, context) 
		return x
		
	def _trucks_mismatch(self, cr, uid, ids, values, arg, context):
		x={}
		for record in self.browse(cr, uid, ids):
			trucks	 =0
			booked	 =0
			_mismatch=False
			if record.x_pudel=="del":
				for mrp in record.x_mrp_lines_dcs:
					if mrp.trucks:
						trucks+=mrp.trucks
				for line in record.order_line:
					if line.product_id.x_prod_cat=="freight":
						booked+=line.x_order_qty
				if booked != trucks:
					_mismatch = True
			x[record.id] = _mismatch#self.trucks_mismatch_found(cr, uid, ids, record.id, context) 
		return x
		
	def _salesperson(self, cr, uid, ids, values, arg, context):
		x={}
		_ret=''
		for record in self.browse(cr, uid, ids):
			if record.user_id:
				_ret=record.user_id.name
			
			x[record.id]=_ret 
		return x
	def _days_produced(self, cr, uid, ids, values, arg, context):
		x={}
		_ret=''
		for record in self.browse(cr, uid, ids):
			if record.x_date_produced:
				_today=fields.date.context_today(self,cr,uid,context=context)
				dt1=dateutil.parser.parse(str(_today))
				dt2=dateutil.parser.parse(str(record.x_date_produced))
				delta = dt1 - dt2
				_ret = delta.days
			else:
				_ret=''
			x[record.id]=_ret 
		return x
	def _date_deposit(self, cr, uid, ids, values, arg, context):#to get deposit invoice due date
		x={}
		_ret=''
		for record in self.browse(cr, uid, ids):
			if record.id:
				sql = "select date_due from account_invoice where x_sale_order_id = '%s' and x_inv_type = 'deposit' and state = 'open' order by date_due desc limit 1" %(record.id)
				cr.execute(sql)
				rows = cr.dictfetchall()
				for row in rows:
					_ret = row['date_due']
			else:
				_ret=''
			x[record.id]=_ret 
		return x
	
	def _days_deposit_due(self, cr, uid, ids, values, arg, context):#to get deposit invoice overdue days
		x={}
		_ret=''
		for record in self.browse(cr, uid, ids):
			if record.x_date_deposit:
				_today=fields.date.context_today(self,cr,uid,context=context)
				dt1=dateutil.parser.parse(str(_today))
				dt2=dateutil.parser.parse(str(record.x_date_deposit))
				delta = dt1 - dt2
				_ret = delta.days
			else:
				_ret=''
			x[record.id]=_ret 
		return x	
	def get_cod_pending_invoice(self, cr,uid, ids,order_id,context):
		sql ="select i.state from account_invoice i, account_payment_term t where i.payment_term=t.id and i.x_sale_order_id='%s' and t.x_payterm_code in('COD','immediate') and i.type='out_invoice'" % (str(order_id))
		cr.execute(sql)
		rows = cr.dictfetchall()
		for row in rows:
			state=row['state']
			if not state or state=="open" or state=="part":
				return True
		#checking...just in case cod order but not invoiced
		sql ="select 1 from sale_order o, account_payment_term t where o.payment_term=t.id and o.id='%s' and t.x_payterm_code in('COD','immediate')" % (str(order_id))
		cr.execute(sql)
		rows = cr.fetchone()
		if rows and len(rows)>0:
			#found cod sale order....now check invoiced or not//offset is not paid....>>cancel offset only....due to error in entry..
			sql="select i.state from account_invoice i where i.x_sale_order_id='%s' and i.state not in ('draft','cancel','offset') and i.type='out_invoice'"% (str(order_id))
			cr.execute(sql)
			rows1 = cr.dictfetchall()
			if not rows1 or len(rows1)==0:#no invoice valid (open/paid/close) in system.....equals...zero invoice generetad
				return True
			for row1 in rows1:
				state=row1['state']
				if not state or state=="open" or state=="part":
					return True	
		return False
	
	def _admin_super(self, cr, uid, ids, values, arg, context):
		x={}
		for record in self.browse(cr, uid, ids):
			x[record.id]=self.get_admin_super(cr, uid, ids, record.id, context) 
		return x	
		
	def get_admin_super(self, cr,uid, ids,order_id,context):
		_edit=False
		cr.execute("select res_id from ir_model_data where name='admin_super_users' and model='res.groups'") #+ str(record.id))
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
		return	_edit
		
	def get_admin_master(self, cr,uid, ids,order_id,context):
		_edit=False
		cr.execute("select res_id from ir_model_data where name='admin_manager_users' and model='res.groups'") #+ str(record.id))
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
		return	_edit
		
	def get_edit_master(self, cr,uid, ids,order_id,context):
		_edit=False
		cr.execute("select res_id from ir_model_data where name='deposit_ex_editor' and model='res.groups'") #+ str(record.id))
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
		return	_edit
		
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
		
	def _edit_master(self, cr, uid, ids, values, arg, context):
		x={}
		for record in self.browse(cr, uid, ids):
			_edit=self.get_edit_master(cr, uid, ids, record.id, context)
			x[record.id]=_edit 
		return x
		
	def _site_mismatch(self, cr, uid, ids, values, arg, context):
		x={}
		for record in self.browse(cr, uid, ids):
			_mismatch=False
			if record.partner_id and record.x_project_id:
				client	=str(record.partner_id.x_dcs_id) + "-"	
				project	=record.x_project_id.x_dcs_id
				if project and client not in project:
					_mismatch = True
			x[record.id]=_mismatch 
		return x
		
	def _due_date_over(self, cr, uid, ids, values, arg, context):
			
		x={}
		for record in self.browse(cr, uid, ids):
			#dt_now = datetime.datetime.strptime(str(date.today()), '%Y-%m-%d')  #date.today()
			_over=False
			if record.partner_id:
				_id=record.partner_id.id 
				_over=self.pool.get('res.partner').over_due_invoice(cr, uid, ids, _id, context) 
			x[record.id] =	_over
			#else:
			#	_id=0
			'''dt_now	= fields.date.context_today(self,cr,uid,context=context)
			
			#today	= dateutil.parser.parse(str(today))
			
			sql = "select i.date_due from account_invoice i,account_payment_term t where i.payment_term=t.id and t.x_days>0 and i.partner_id='%s' and i.state = 'open' and i.type='out_invoice' and i.x_inv_type in ('balance','full') order by i.date_due asc limit 1" % (_id)
			cr.execute(sql)
			rows = cr.fetchall()
			
			if(len(rows) > 0):
				dt_due = rows[0][0]
			else:
				dt_due = dt_now
			#---converting to datetime/date format for compare condition...
			
			#_logger.error("dincelcrm_due_date["+str(dt_now)+"]["+str(dt_due)+"]["+str(record)+"]["+str(sql)+"]")	
			
			dt_now 	= dateutil.parser.parse(str(dt_now))
			dt_due 	= dateutil.parser.parse(str(dt_due))
			
			if dt_due < dt_now:
				x[record.id] = True
			else:
				x[record.id] = False'''
			
		return x
		
	def _update_deposit_invoice_status(self, cr, uid, ids, _id, context=None):
		sql ="select 1 from account_invoice where x_sale_order_id='%s' and x_inv_type='deposit' and state in ('open')" % (str(_id))
		cr.execute(sql)
		rows_chk = cr.fetchall()
		if(len(rows_chk) > 0):
			sqlUp ="update sale_order SET x_pending_deposits = 't' where id='%s'" % (str(_id))
			cr.execute(sqlUp)
		else:
			sqlUp ="update sale_order SET x_pending_deposits = 'f' where id='%s'" % (str(_id))
			cr.execute(sqlUp)
		return True
		
	def _has_approvals(self, cr, uid, ids, values, arg, context):
		x={}
		
		for record in self.browse(cr, uid, ids):
			_ret=False
			sql = "select 1 from dincelsale_order_approve where order_id='%s' " % str(record.id)
			cr.execute(sql)
			rows = cr.fetchall()
			if len(rows)>0:
				_ret=True
			x[record.id] = _ret 
		return x	
		
	def _ok2cancel(self, cr, uid, ids, values, arg, context):
		x={}
		
		for record in self.browse(cr, uid, ids):
			_ret=True
			if record.x_prod_status in ["part","complete"]:
				_ret=False
			else:
				sql = "select 1 from account_invoice where x_sale_order_id='%s' and state in ('open','paid')" % str(record.id)
				cr.execute(sql)
				rows 	= cr.dictfetchall()
				if len(rows)>0:
					_ret=False
			x[record.id] = _ret 
		return x
	def _is_pudel_state(self, cr, uid, ids, values, arg, context):
		x={}
		
		for record in self.browse(cr, uid, ids):
			_ret=False
			if record.x_coststate_id and record.x_warehouse_id:
				if record.x_coststate_id.x_warehouse_id and record.x_warehouse_id.id == record.x_coststate_id.x_warehouse_id.id:
					_ret=True
				
				#_logger.error("_is_pudel_state_is_pudel_state.invoice_err["+str(record.x_warehouse_id.id)+"]["+str(record.x_coststate_id.x_warehouse_id.id)+"]")	
					
					
			else:
				_ret=False
			x[record.id] = _ret 
		return x
		
	def _has_valid_rate(self, cr, uid, ids, values, arg, context):
		x={}
		
		for record in self.browse(cr, uid, ids):
			_ret=False
			if record.partner_id:
				_id=record.partner_id.id 
				_ret=self.pool.get('res.partner').has_valid_rate_default(cr, uid, ids, _id, context)  
			x[record.id] = _ret 
		return x
		
	def update_payment_order(self, cr, uid, ids, _id, context=None):
		if context is None:
			context = {}
		
		self._update_payment_deposit(cr, uid, ids, _id, context=context)
		self._update_payment_balance(cr, uid, ids, _id, context=context)
		self._update_deposit_invoice_status(cr, uid, ids, _id, context=context)
		
		#-------------------------------------------------------------------------------
		#----added 5/12/2017
		#-------------------------------------------------------------------------------
		_pending=False
		obj = self.browse(cr, uid, _id, context=context)
		if abs(obj.x_tot_balance) <= 1.0:
			for inv in obj.x_account_ids:
				if inv.state=="open" or inv.state=="draft":
					_pending=True
			if obj.x_del_status=="delivered" and obj.state not in ['done','cancel']:
				#done
				if _pending==False: #no inv remaining
					sql="update sale_order set state='done' where id='%s'" % (_id)
					cr.execute(sql)
				else:
					if obj.x_pending==False:
						sql="update sale_order set x_pending='t' where id='%s'" % (_id)
						cr.execute(sql)
				
		return True
	 
	_columns={
		'x_account_ids': fields.one2many('account.invoice', 'x_sale_order_id', 'Invoice/s'),
		'x_credit_limit': fields.related('partner_id', 'credit_limit', type='float', string='Credit Limit', store=False),
		'x_due_date_over': fields.function(_due_date_over, method=True, string='Due Date Over', type='boolean'),
		'x_rate_note': fields.related('partner_id', 'x_rate_note', type='char', string='Rate Note', store=False),
		'x_over_terms': fields.related('partner_id', 'x_over_terms', type='char', string='Over Terms', store=False),
		'x_stop_supply': fields.related('partner_id', 'x_stop_supply', type='boolean', string='Stop Supply', store=False),
		'x_hold_supply': fields.related('partner_id', 'x_hold_supply', type='boolean', string='Hold Supply', store=False),
		'x_has_custref': fields.related('partner_id', 'x_has_custref', type='boolean', string='Customer Ref', store=False),
		'x_qty_tot_profile': fields.float('Total Profile Qty', digits=(16,2)),
		'x_origin_order': fields.many2one('dincelsale.ordersale','Origin Order'),
		#'x_colourname': fields.char('Colour'),	
		'x_cr_limit_over': fields.function(cr_limit_over, method=True, string='Cr Limit', type='boolean'),
		'x_create_deposit': fields.function(create_deposit_chk, method=True, string='create deposit chk', type='boolean'), #-- check if deposit invoice to create...
		#'x_create_balance': fields.function(create_balance_chk, method=True, string='create_balance_chk', type='boolean'),
		'x_has_custom': fields.function(has_custom_profile, method=True, string='Has custom profile', type='char'),
		'x_tot_invoiced': fields.function(tot_invoiced, method=True, string='Total Invoiced',type='float'),
		#'x_2b_invoiced': fields.function(_2b_invoiced, method=True, string='To be Invoiced',type='float'),
		'x_tot_balance': fields.function(tot_balance, method=True, string='Balance Amount',type='float'),
		'x_pickinglist_ids': fields.one2many('dincelstock.pickinglist', 'pick_order_id','Deliveries'),
		'x_ibt_ids':fields.one2many('dincelstock.transfer','order_id','IBT'),
		'x_project_id': fields.many2one('res.partner','Project / Site',track_visibility='onchange', readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}),	
		'x_project_suburb_id': fields.related('x_project_id', 'x_suburb_id',  string='Suburb', type="many2one", relation="dincelbase.suburb",store=True),
		'x_proj_state':fields.related('x_project_id', 'state_id', string="Project State", type="many2one", relation="res.country.state", store=False),		
		'x_contact_id': fields.many2one('res.partner','Contact Person'),		
		'x_quote_id': fields.many2one('account.analytic.account','Quote'),		
		'x_warehouse_id': fields.many2one('stock.warehouse','Dispatch Location'),		
		'x_street': fields.char('Street'),	
		'x_date_produced': fields.date('Date Production Complete'),	
		'x_days_produced': fields.function(_days_produced, method=True, string='Days Produced',type='integer', store=False),
		'x_is_pudel_state': fields.function(_is_pudel_state, method=True, string='Delivery State Mismatch',type='boolean', store=False),
		'x_date_deposit': fields.function(_date_deposit, method=True, string='Deposit Invoice Date',type='date', store=False),#to get
		'x_days_deposit_due': fields.function(_days_deposit_due, method=True, string='Deposit Overdue Days',type='integer', store=False),
		'x_postcode': fields.char('Postcode'),	
		'x_suburb': fields.char('Suburb'),	
		'x_state_id': fields.many2one('res.country.state','State'),		
		'x_country_id': fields.many2one('res.country','Country'),
		'x_deposit_exmpt': fields.boolean('Deposit Exempt'),
		'x_sent': fields.boolean('Sent'),
		'x_salesperson':  fields.function(_salesperson, method=True, string='Salesperson',type='char'), 
		'x_acct_status':  fields.function(_acct_status, method=True, string='Acc. Status',type='char'), 
		'x_acs_status': fields.char('Acs Status'),	
		'x_acs_110': fields.integer('110mm Acs'),	
		'x_acs_155': fields.integer('155mm Acs'),	
		'x_acs_200': fields.integer('200mm Acs'),	
		'x_acs_275': fields.integer('275mm Acs'),	
		'x_panel_110': fields.float('110mm L/M'),	
		'x_panel_155': fields.float('155mm L/M'),	
		'x_panel_200': fields.float('200mm L/M'),	
		'x_panel_275': fields.float('275mm L/M'),	
		'x_pudel':fields.selection([
			('pu','Pickup'),
			('del','Delivery'),
			], 'Pickup/Delivery'),
		'x_ac_status':fields.selection([
			('hold','Hold'),
			('open','Open'),
			('part','Part'),
			('paid','Paid'),
			], 'A/c Status'),	
		'x_prod_status':fields.selection([
			('',''),
			('queue','Queue'),
			('printed','Printed'),
			('confirmed','Confirmed'),
			('part','Part'),
			('complete','Complete'),
			], 'Production Status'),		
		'x_del_status':fields.selection([
			('','None'),
			('none','None'),
			('part','Part'),
			('delivered','Delivered'),
			], 'Delivery Status'),		
		'x_status':fields.selection([ #as in dcs open /close/ cancel
			('open','Open'),
			('close','Closed'),
			('cancel','Cancelled'),
			], 'StatusX'),	
		'x_dt_request':fields.date("Requested Date"),		
		'x_note_request':fields.char("Note Requested Date"),	
		'x_dt_process': fields.datetime("Order Entry Date"),
		'x_dt_anticipate': fields.date("Anticipate Date",track_visibility='onchange'),
		'x_dt_actual': fields.date("Actual Date"),
		'x_type_request': fields.selection([
				#('tba', 'TBA'),
				('asap', 'ASAP'),
				('dt', 'Date')],"Type Requested"),
		'x_type_anticipate': fields.selection([
				('tba', 'TBA'),
				('na', 'NA'),
				('dt', 'Date')],"Type Anticipate"),
		'x_type_actual': fields.selection([
				('tba', 'TBA'),
				('na', 'NA'),
				('dt', 'Date')],"Type Actual"),
		#'x_dt_deposit': fields.date("Deposit Date"), #>> to be done by function...auto calculate date..but make store = true for sorting function
		#'x_dt_balance': fields.date("Balance Date"), #>> to be done by function...auto calculate date..but make store = true for sorting function
		'x_region_id': fields.many2one('dincelaccount.region', 'A/c Region'),
		'x_coststate_id':fields.many2one("res.country.state","Cost Centre"),
		'x_colorcode': fields.char('Colour Code'),	
		'x_colorname': fields.function(get_colorname, method=True, string='Colour Name',type='char'), 
		'x_over_due': fields.function(_over_due_check, method=True, string='Overdue?',type='char'), 
		'x_pending_invoice': fields.function(_pending_invoice, method=True, string='Pending InvoiceX',type='boolean'), 
		'x_pending_inv': fields.boolean('Pending Invoice'),# calc field from scheduled task ... ields.function(_pending_invoice, method=True, string='Pending Invoice',type='boolean'), 
		'x_pending_deposits': fields.boolean('Deposit Invoice'), #  
		'x_pending_inv_bal':fields.boolean('Pending Invoice Bal'),# fields.function(_pending_invoice_bal, method=True, string='Pending Invoice Bal',type='boolean'), 
		'x_pending_delivery':fields.boolean('Produced But Not Delivered'),
		#'x_get_quote': fields.function(get_quote_no, method=True, string='Quote',type='char'),
		#'x_new_lines': fields.one2many('sale.order.line.new', 'order_id', 'New Lines'),
		#'x_old_lines': fields.one2many('sale.order.line.old', 'order_id', 'Old Lines'),
		'x_email_attachs':fields.many2one('ir.attachment','Invoice Attachments'),
		'x_order_attachs':fields.many2one('ir.attachment','Order Attachments'),
		'x_location_id':fields.many2one('stock.location','Stock Location',track_visibility='onchange'),
		'x_date_location':fields.date("Stock Date"),
		'x_origin_id':fields.many2one('sale.order','Order Origin'), #>>in case of revisions orders
		'x_revision_ids': fields.one2many('sale.order', 'x_origin_id','Revision History'),
		'x_revision_bak_ids': fields.one2many('sale.order.bak', 'origin_id','Revision History'),
		'x_revise_sn': fields.integer('Revise SN', size=2),	
		'x_has_invoice': fields.function(has_invoice, method=True, string='has invoice',type='boolean'),#fields.integer('Revise Count', size=2),
		'x_create_bal_inv': fields.function(_create_bal_inv, method=True, string='create bal invoice',type='boolean'),
		'x_trucks_mismatch': fields.function(_trucks_mismatch, method=True, string='Trucks Missing/Mismatch',type='boolean'),
		'x_mrp_missing': fields.function(_mrp_missing, method=True, string='MRP Missing/Mismatch',type='boolean'),
		'x_is_mrp_missing': fields.boolean('MRP Missing/Mismatch',help="MRP Missing/Mismatch"),#to record MRP missing/mismatched order (eg treeview)
		'x_revision': fields.boolean('Is Revision'),
		'x_has_approvals': fields.function(_has_approvals, method=True, string='Has Approvals',type='boolean'),
		'x_approve_ids': fields.one2many('dincelsale.order.approve', 'order_id','Approval History'),
		'x_ok2cancel': fields.function(_ok2cancel, method=True, string='Ok2Cancel', type='boolean'),
		'x_authorise_cancel':fields.boolean('Authorise Cancel'),
		'x_authorise_mrp':fields.boolean('Authorise MRP'),
		'x_cancel_comments':fields.char('Cancel Comments'),
		'x_authorise_discount':fields.boolean('Authorise Discount'),
		'x_discount_comments':fields.char('Discount Comments'),
		'x_authorise_comments':fields.char('Authorise Comments',track_visibility='onchange'),
		'x_authorise_but': fields.boolean('Authorise But',help="Authorised delivery but not paid."),
		'x_authorise_len': fields.boolean('Authorise Length Restriction',help="Authorise length restriction for p-1 custom"),
		'x_revise_type':fields.selection([ #>>as revise type
			('shipment','Shipment'),
			('rate','Price changed'),
			('order','Qty changed'),
			('other','Other'),
			], 'Revise type'),
		'x_type':fields.selection([ #>>as revise, cancel, normal
			('normal','Normal'),
			('revise','Revised'),
			('cancel','Cancelled'),
			], 'Type Revise,Cancel'),
		'state': fields.selection([	#>>overwrite the status....for labeling etc...
			('draft', 'Draft'),
			('sent', 'Sent'),
			('cancel', 'Cancelled'),
			('waiting_date', 'Waiting Schedule'),
			('progress', 'Progress'),
			('manual', 'Manual'),
			('shipping_except', 'Shipping Exception'),
			('invoice_except', 'Invoice Exception'),
			('done', 'Done'),
			], 'Status', readonly=True, copy=False, help="Gives the status of the sales order.\
			\nThe exception status is automatically set when a cancel operation occurs \
			in the invoice validation (Invoice Exception) or in the picking list process (Shipping Exception).\nThe 'Waiting Schedule' status is set when the invoice is confirmed\
			but waiting for the scheduler to run on the order date.", select=True,track_visibility='onchange'),	
		'x_deposit_paid': fields.function(_deposit_paid, method=True, string='Deposit Paid',type='char'), #DO NOT USE
		'x_balance_paid': fields.function(_balance_paid, method=True, string='Balance Paid',type='char'), #DO NOT USE
		'x_dep_amt': fields.function(_deposit_amt, method=True, string='Dep Amt',type='char'), 
		'x_bal_amt': fields.function(_balance_amt, method=True, string='Bal Amt',type='float'), 
		'x_dep_paid_amt': fields.function(_deposit_paid_amt, method=True, string='Dep Paid',type='float'), 
		'x_bal_paid_amt': fields.function(_balance_paid_amt, method=True, string='Bal Paid',type='float'), 
		'x_dep_paid': fields.char('Deposit Paid', size=5),	
		'x_bal_paid': fields.char('Balance Paid', size=5),	
		'x_attach_110': fields.char('Attach 110mm'),	
		'x_attach_155': fields.char('Attach 155mm'),	
		'x_attach_200': fields.char('Attach 200mm'),	
		'x_attach_275': fields.char('Attach 275mm'),	
		'x_attach_110_found': fields.function(_attach_110_found, method=True, string='110_found',type='boolean'), 
		'x_attach_155_found': fields.function(_attach_155_found, method=True, string='155_found',type='boolean'), 
		'x_attach_200_found': fields.function(_attach_200_found, method=True, string='200_found',type='boolean'), 
		'x_attach_275_found': fields.function(_attach_275_found, method=True, string='275_found',type='boolean'), 
		'x_pending': fields.boolean('Payment Pending'),	
		'x_edit_master': fields.function(_edit_master, method=True, string='Edit master',type='boolean'),
		'x_edit_rate': fields.function(_edit_rate, method=True, string='Edit Rate',type='boolean'),
		'x_ref_id': fields.char('Ref ID', size=10),
		'x_ref_name': fields.char('Number', size=20),
		'x_site_mismatch': fields.function(_site_mismatch, method=True, string='Site Mismatch', type='boolean'),
		'x_admin_super': fields.function(_admin_super, method=True, string='Admin Super',type='boolean'),
		'x_has_valid_rate': fields.function(_has_valid_rate, method=True, string='Has valid rate',type='boolean'),
		}
	
	_defaults = {
		'x_authorise_but':False,
		'x_revision':False,
		'x_pending':False,
		'x_revise_sn':0,
		'x_del_status':'',
		'x_prod_status':'',
		'x_status': 'open',
		'x_type': 'normal',
		'x_ac_status': 'hold',
		'x_dt_process' : fields.datetime.now,#fields.date.context_today, 
	}
	
	def copy(self, cr, uid, id, default=None, context=None):
		raise osv.except_osv(_('Forbbiden to duplicate'), _('Is not possible to duplicate the record, please create a new one.'))	
		
	def unlink(self, cr, uid, ids, context=None, check=True):
		context = dict(context or {})
		if context is None:
			context = {}
		lids 	= self.pool.get('account.invoice').search(cr, uid, [('x_sale_order_id', '=', ids[0])])
		if len(lids)>0:
			raise Warning(_('You cannot delete an order after invoice has been generated.'))
			#raise osv.except_osv(_('Error!'), _('You cannot delete a sales order after an invoice has been generated.'))
		else:
			for record in self.browse(cr, uid, ids):
				if record.origin and record.origin !='':
					raise Warning(_('You cannot delete an order after it has recieved the colour.'))
			raise Warning(_('You cannot delete an order, but you can cancel it or contact administrator.'))		
			#result = super(dincelaccount_sale_order, self).unlink(cr, uid, ids, context)
			#return result
	def button_cancel(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		type="cancel"	
		sale_order_line_obj = self.pool.get('sale.order.line')
		account_invoice_obj = self.pool.get('account.invoice')
		for sale in self.browse(cr, uid, ids, context=context):
			if sale.x_prod_status in ["part","complete"]:
				
				if sale.x_authorise_cancel==False:
					#raise osv.except_osv(
					#	_('Cannot cancel this sales order!'),
					#	_('The order has been partially/fully produced.'))
					
					return self.open_popup_approve_request(cr, uid, ids[0],type, None,context)
					
			for inv in sale.x_account_ids:
				#_logger.error("x_account_idsx_account_ids[%s][%s]" % (inv.id,inv.state))
				if inv.state in ['open', 'paid']:
					if sale.x_authorise_cancel==False:
						#raise osv.except_osv(
						#	_('Cannot cancel this sales order!'),
						#	_('The order has been partially/fully produced.'))
						
						return self.open_popup_approve_request(cr, uid, ids[0],type,None, context)
					#raise osv.except_osv(
					#	_('Cannot cancel this sales order!'),
					#	_('First cancel / offset all invoices attached to this sales order.'))
				#inv.signal_workflow('invoice_cancel')
			sale_order_line_obj.write(cr, uid, [l.id for l in  sale.order_line],{'state': 'cancel'})
		self.write(cr, uid, ids, {'state': 'cancel'})
		return True	
	#button_schedule_delivery	
	def button_book_delivery(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		for record in self.browse(cr, uid, ids, context=context):	
		#_obj = self.pool.get('dincelmrp.production').browse(cr, uid, ids[0], context=context)
			if record.state in ['done','cancel']:
				raise osv.except_osv(_('Forbbiden delivery'), _('The order is already closed/cancelled.'))	
			else:
				pending_invoice=self.get_cod_pending_invoice(cr,uid, ids,record.id,context) 
				return {
					'type': 'ir.actions.act_window',
					'res_model': 'dincelmrp.schedule.delivery',
					'view_type': 'form',
					'view_mode': 'form',
					#'res_id': 'id_of_the_wizard',
					'context':{
						'default_order_id':record.id, 
						'default_pudel': record.x_pudel, 
						'default_partner_id': record.partner_id.id, 
						'default_project_id': record.project_id.id,
						'default_pending_invoice': pending_invoice,
						'default_from_order':True,
					},
					'target': 'new',
				}
			
	def check_line_details(self, cr, uid, pid, length,authorise_len=False, context=None):
		if not pid or not length:
			return 0
		err_msg = 0
		#if uid==1:
		#	return err_msg
		#product_obj = self.pool.get('product.product')
		prod_cat=""
		prod_name=""
		dcs_grp=""
		stock_len=3000
		len_min=1800
		len_max=7980
		len_inc=1
		
		sql ="SELECT pt.name, pt.x_prod_cat, pt.x_dcs_group,pt.x_stock_length,pt.x_len_min,pt.x_len_max,pt.x_len_inc FROM product_template pt, product_product pp WHERE pp.id = '" + str(pid) + "' AND pt.id = pp.product_tmpl_id"
		cr.execute(sql)
		rows = cr.dictfetchall()
		
		for row in rows:
			dcs_grp 	= row['x_dcs_group']
			prod_cat 	= row['x_prod_cat']
			prod_name 	= row['name']
			stock_len	= row['x_stock_length']
			
			len_min 	= row['x_len_min']
			len_max 	= row['x_len_max']
			len_inc		= row['x_len_inc']
			
			len_min 	= int(len_min) if len_min else 1800
			len_max 	= int(len_max) if len_max else 7950
			len_inc 	= int(len_inc) if len_inc else 1
			
		#name_part = rows['name'].split("-")
		#sp = name_part[0].split("P")
		#prod_like = "P" + sp[0]
		#_logger.error("Changed Length["+str(sql)+"]["+str(prod_cat)+"]["+dcs_grp+"]["+prod_name+"]")
		
		if(length != 0 and prod_cat == "customlength"): #To check custom length and product
			sql ="SELECT pt.id as prod_id FROM product_template pt, product_product pp WHERE pt.x_stock_length = '" + str(int(length)) + "' AND pt.id = pp.product_tmpl_id AND pt.x_dcs_group = '" + str(dcs_grp) + "' AND pt.x_prod_cat='stocklength' AND pt.x_dcs_itemcode like '%P-1%'"
			cr.execute(sql)
			rows = cr.fetchall()
			if(len(rows) > 0):
				err_msg = 1
				#_logger.error("customlengthcustomlength["+str(sql)+"]")
				#raise osv.except_osv(_('Duplicate length/product!'), _('Duplicate length/product found.  Length [%s] already exists.' % (int(length))))
			#_logger.error("Changed Length["+str(sql)+"]")

		#if product_obj.name:
		if err_msg == 0 and pid and length  and "P-1" in prod_name:
			if length==0.0:
				err_msg = 1
			else:
				if prod_cat == "customlength":
					if length<len_min or length>len_max:
						if authorise_len==False:
							err_msg = 1
					elif len_inc>1:
						if authorise_len==False:
							rem = length % len_inc
							if rem != 0:
								err_msg = 1
				else:
					if length != stock_len:
						err_msg = 1
				
		return err_msg
		
	def create(self, cr, uid, vals, context=None):
		err=0
		if context is None:
			context = {}
		order_length=0	
		if vals.get('name', '/') == '/':
			vals['name'] 		=	self.pool.get('ir.sequence').get(cr, uid, 'sale.order') or '/'
			vals['x_ref_name']	=	vals['name']
		new_id = super(dincelaccount_sale_order, self).create(cr, uid, vals, context=context)
		obj = self.browse(cr, uid, new_id,context=context)
		
		if obj.partner_id and obj.payment_term:
			_valid=self.pool.get('res.partner').check_account_terms_valid(cr, uid, [], obj.partner_id.id, obj.payment_term.id, context) 
			if _valid==False:			
				raise osv.except_osv(_('Invalid Terms'),_('Invalid terms found. The customer account rate is not activated yet.'))
				
		for line in obj.order_line:
			if(self.check_line_details(cr, uid, line.product_id.id, line.x_order_length,obj.x_authorise_len, context=context) == 1):
				order_length = int(line.x_order_length)
				err = 1
				break
		#enable later.....	
		#-------------------------------
		if(err == 1):
			raise osv.except_osv(_('Error!'), _('The length you have entered [%s] already exists as a stock length product. or\nThe entered length is not valid range for production.' %(order_length)))
		#-------------------------------
		
		return new_id
		
	def write(self, cr, uid, ids, vals, context=None):
		#has_custom=None 
		err=0
		#prod=self.pool.get("dincelmrp.production")
		res = super(dincelaccount_sale_order, self).write(cr, uid, ids, vals, context=context)
		for record in self.browse(cr, uid, ids):
			if record.partner_id and record.payment_term:
				_valid=self.pool.get('res.partner').check_account_terms_valid(cr, uid, ids, record.partner_id.id, record.payment_term.id, context) 
				if _valid==False:			
					raise osv.except_osv(_('Invalid Terms'),_('Invalid terms found. The customer account rate is not activated yet.'))
				#@return False
			if record.partner_id and record.partner_id.x_is_blocked:
				raise osv.except_osv(_('Blocked customer'),_('Inactive or blocked customer. Please contact account team to proceed.'))
				
			for line in record.order_line:
				#if line.product_id:
				#_logger.error("Return Value["+str(self.check_line_details(cr, uid, ids, line.product_id.id, line.x_order_length, context=context))+"]")
				if(self.check_line_details(cr, uid, line.product_id.id, line.x_order_length,record.x_authorise_len, context=context) == 1):
					order_length = int(line.x_order_length)
					err = 1
					break
			#enable later.....	
			#-------------------------------
			if(err == 1):
				raise osv.except_osv(_('Error!'), _('The length you have entered [%s] already exists as a stock length product. or\nThe entered length is not valid range for production.' %(order_length)))
			#-------------------------------
			
			id			= record.id	
			
			stateid=record.x_coststate_id
			if not stateid:
				raise osv.except_osv(_('Error!'), _('Project/site state is missing.'))
			
			#if record.x_pudel and record.x_pudel=="pu":
			#	if stateid.x_warehouse_id:
			#		if stateid.x_warehouse_id.id != record.x_warehouse_id.id:
			#			raise osv.except_osv(_('Error!'), _('The pickup location is not correct based on selected state.'))
			
			#qty_acs=0
			acs_110=0
			acs_155=0
			acs_200=0
			acs_275=0		
			
			lm_110=0.0
			lm_155=0.0
			lm_200=0.0
			lm_275=0.0	
			#sql=""
			#sql=""
			try:	
				for line in record.order_line:
					if line.product_id:
						ptype=line.product_id.x_prod_type
						pgrp=line.product_id.x_dcs_group	
						if ptype and ptype=="acs":
							qty_acs=int(line.x_order_qty)
							if pgrp=="P110":
								acs_110+=qty_acs
							elif pgrp=="P155":
								acs_155+=qty_acs
							elif pgrp=="P200":
								acs_200+=qty_acs
							elif pgrp=="P275":
								acs_275+=qty_acs
						else:
							lm=float(line.x_order_qty)*float(line.x_order_length)*0.001
							if pgrp=="P110":
								lm_110+=lm
							elif pgrp=="P155":
								lm_155+=lm
							elif pgrp=="P200":
								lm_200+=lm
							elif pgrp=="P275":
								lm_275+=lm
				sql="update sale_order set x_acs_110='%s',x_panel_110='%s'" %(acs_110,lm_110)
				sql+=",x_acs_200='%s',x_panel_200='%s'" %(acs_200,lm_200)
				sql+=",x_acs_155='%s',x_panel_155='%s'" %(acs_155,lm_155)
				sql+=",x_acs_275='%s',x_panel_275='%s'" %(acs_275,lm_275)
				if not record.x_del_status:
					sql+=",x_del_status=''"
					
				sql+=" where id='%s'" %(record.id)

				cr.execute(sql)	
				
				
				#--making sure the account invoice salesperson align with order form...salesperson	
				if record.user_id:
					sql="update account_invoice set user_id='%s' where  x_sale_order_id='%s' and user_id!='%s'" % (record.user_id.id, record.id, record.user_id.id)
					cr.execute(sql)	
				if record.x_warehouse_id:
					sql="update dincelwarehouse_sale_order_delivery set warehouse_id='%s' where  order_id='%s' " % (record.x_warehouse_id.id, record.id)
					cr.execute(sql)
				#url=self.pool.get('dincelaccount.config.settings').get_dcs_api_url(cr, uid, ids, "getorder", record.id, context=context)	
				#if url and record.origin and record.origin != "":#only if already sync done...
				#	sql="select 1 from dincelbase_scheduletask where state='pending' and url='%s' and write_uid!='1'" % (url)
				#	cr.execute(sql)	
				#	rows = cr.fetchone()
				#	if rows == None or len(rows)==0:
				#		val={
				#			"url":url,
				#			"name":record.name,
				##			"action":"getorder",
				#			"state":"pending",
				#		}
				#		self.pool.get('dincelbase.scheduletask').create(cr, uid, val, context=context)
						
			except Exception, e:
				#pass
				_logger.error("dincelaccount_sale_order.write_error["+str(e)+"]["+str(sql)+"]")	
			#str1="1"	
			#if record.origin and record.origin !="":
			#	self._updatelink_order_dcs(cr, uid, ids, record.id, context=context)
			#	#str1="2" issue...does not include the recent changes...it would be safe ...to add in scheduled task...
			self._update_payment_deposit(cr, uid, ids, id, context=context) 
			if record.partner_id and record.x_project_id:
				self.pool.get("res.partner").write_relation_if(cr, uid, record.partner_id.id, record.x_project_id.id, context=context)	
				#_logger.error("dincelaccount_sale_orderdincelaccount_sale_order.ar_items_donear_items_done["+str(str1)+"]["+str(record.origin)+"]")	
			if record.x_dt_anticipate:
				sql="update dincelmrp_schedule set date_anticipate='%s' where order_id='%s'" % (record.x_dt_anticipate, id)
				cr.execute(sql)	
			if record.x_quote_id:
				if record.x_quote_id.x_status !="won":
					#sql="update account_analytic_account set x_status='won' where id='%s'" % (record.x_quote_id.id)
					#cr.execute(sql)	
					self.pool.get('account.analytic.account').write(cr, uid, record.x_quote_id.id, {'x_status': "won"}, context=context)	
		return res	
	
	def onchange_order_line_dcs(self, cr, uid, ids, order_line, x_region_id, context=None):
		context = context or {}
		#_logger.error("onchange_order_line_dcs.order_line["+str(order_line)+"]["+str(x_region_id)+"]")
		#if not order_line:
		#	return {}
		'''
		line_ids = self.resolve_2many_commands(cr, uid, 'order_line', order_line, ['x_region_id'], context)
		region_id= None
		#_logger.error("onchange_order_line_dcs.line_ids["+str(line_ids)+"]["+str(x_region_id)+"]["+str(order_line)+"]")	  
		for line in line_ids:
			if line['x_region_id']:
				region_id = line['x_region_id']
				#break 
		return {'value': {'x_region_id': region_id}}'''
	def onchange_order_line_dcs(self, cr, uid, ids, order_line, x_region_id, context=None):
		context = context or {}
		
	def last_day_of_month(self, any_day):
		next_month = any_day.replace(day=28) + datetime.timedelta(days=4)  # this will never fail
		return next_month - datetime.timedelta(days=next_month.day)
	
	def _open_pdf_archive(self, cr, uid, ids, pdf, context=None):
		#http://220.233.149.98/dincel_software/dbdincel/
		#//get_dcs_api_url
		url=self.pool.get('dincelaccount.config.settings').get_dcs_archive_url(cr, uid, ids, context=context)	
		if pdf and url:
			url+="/dbdincel/%s" % (pdf)
			return {
				  'name'     : 'Go to website',
				  'res_model': 'ir.actions.act_url',
				  'type'     : 'ir.actions.act_url',
				  'view_type': 'form',
				  'view_mode': 'form',
				  'target'   : 'current',
				  'url'      : url,
				  'context': context
			   }
			   
	
		
	def btn_open_outstanding(self, cr, uid, ids, context=None):
		if context is None:
			context = {}	
		#for record in self.browse(cr, uid, ids, context=context):	
			#partner_id=record.partner_id.id 
			#obj = self.pool.get('sale.order')
			#view_id = self.pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'accout.invoice_tree')], limit=1) 	
		proceed, o_ids =self.is_over_limit_ok(cr, uid, ids, ids[0], context=context)
		value = {
			'type': 'ir.actions.act_window',
			'name': _('Outstanding Orders'),
			'view_type': 'form',
			'view_mode': 'tree,form',
			'res_model': 'sale.order',
			'domain':[('id','in',o_ids)],
			'context':{},
			#'view_id': view_id,
			
		}

		return value	
			
	def btn_delete_origin(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		obj		=  self.browse(cr, uid, ids[0], context=context)
		if not obj.origin:
			raise osv.except_osv(_('Error'), _('Empty or blank DCS Order No. found. Could not continue your request.'))
		else:	
			url=self.pool.get('dincelaccount.config.settings').get_dcs_api_url(cr, uid, ids, "delorder", ids[0], context=context)		
			if url:
				url+="&origin=" + str(obj.origin)
				str1=self._get_url_contents(cr, uid, url, context)
				if str1==None or str1 == "" or  str1=="timeout":
					raise osv.except_osv(_('Error'), _('Server not available, please try again later.'))
				else:
					item 		= str1['item']
					status1		= str(item['post_status'])
					if status1=="success":
						sql ="UPDATE sale_order SET origin='' WHERE id='"+str(ids[0])+"'"	
						cr.execute(sql)
						return True
					else:
						if item['errormsg']:
							str1=item['errormsg']
						else:
							str1="Error while updating order."
						raise osv.except_osv(_('Error'), _(''+str1))
			#except Exception,e:
			#	_logger.error("error_updatelink_order_dcs.error_updatelink_order_dcs["+str(url)+"]uid["+str(uid)+"]["+str(e)+"]")	   
			#	raise osv.except_osv(_('Error'), _(''+str(e[1])+''))	
		return True
		
	def button_attach_110(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		ctx = dict(context)
		pdf=None
		for record in self.browse(cr, uid, ids):
			pdf=record.x_attach_110
		return self._open_pdf_archive(cr, uid, ids, pdf, context=ctx)
		
	def button_attach_155(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		ctx = dict(context)
		pdf=None
		for record in self.browse(cr, uid, ids):
			pdf=record.x_attach_155
		return self._open_pdf_archive(cr, uid, ids, pdf, context=ctx)
		
	def button_attach_200(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		ctx = dict(context)
		pdf=None
		for record in self.browse(cr, uid, ids):
			pdf=record.x_attach_200
		return self._open_pdf_archive(cr, uid, ids, pdf, context=ctx)	
		
	def button_attach_275(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		ctx = dict(context)
		pdf=None
		for record in self.browse(cr, uid, ids):
			pdf=record.x_attach_275
		return self._open_pdf_archive(cr, uid, ids, pdf, context=ctx)
			
	def button_open_partner_form(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		for record in self.browse(cr, uid, ids, context=context):	
			partner_id=record.partner_id.id 
			#//obj = self.pool.get('sale.order')
			view_id = self.pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'dincelaccount.partner.new.form.view')], limit=1) 	
			value = {
				'type': 'ir.actions.act_window',
				'name': _('Partner'),
				'view_type': 'form',
				'view_mode': 'form',
				'res_model': 'res.partner',
				'domain': str([('id', 'in', partner_id)]),
				#'context':{'search_default_id': partner_id},
				'view_id': view_id,
				'res_id':partner_id
			}
			#_logger.error("button_open_partner_form_ididid["+str(view_id)+"]partner_id["+str(partner_id)+"]")	
			return value
			
	def open_invoices_all(self, cr, uid, ids, context=None):
		if context is None:
			context = {}	
		for record in self.browse(cr, uid, ids, context=context):	
			partner_id=record.partner_id.id 
			#obj = self.pool.get('sale.order')
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
			
	def button_sales_orders(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		for record in self.browse(cr, uid, ids, context=context):	
			partner_id=record.partner_id.id 
			#obj = self.pool.get('sale.order')
			view_id = self.pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'dincelmanufacture.dincelmrp_sale_order_tree')], limit=1) 	
	
			value = {
				'type': 'ir.actions.act_window',
				'name': _('Sale Orders'),
				'view_type': 'form',
				'view_mode': 'tree,form',
				'res_model': 'sale.order',
				'domain':[('partner_id','=',partner_id)],
				'context':{'search_default_partner_id': partner_id},
				'view_id': view_id,
				
			}

			return value	
	
	def get_first_dayxx(self, cr, uid, ids, dt, d_years=0, d_months=0, context=None):
		# d_years, d_months are "deltas" to apply to dt
		y, m = dt.year + d_years, dt.month + d_months
		a, m = divmod(m-1, 12)
		return date(y+a, m+1, 1)
		
	#def reset_next_delivery_date(self, cr, uid, ids, _id, sch_id, context=None):	
	def get_next_delivery_date(self, cr, uid, ids, _id, sch_id, is_del, context=None):
		update, dt, state = False, None, None
		try:
			sql="select date_actual,state from dincelwarehouse_sale_order_delivery  where state in ('draft','open','partial','confirm') and order_id='%s'" % (_id)
			if is_del and sch_id:
				sql+=" and id!='%s' " % (sch_id)
			sql+="  order by date_actual limit 1"	
			
			cr.execute(sql)
			rows1 = cr.fetchall()
			if rows1 and len(rows1) >0:
				for row1 in rows1:
					update = True
					dt=row1[0]
					state=row1[1].capitalize()
					
			else: #and id!='%s' order by date_actual limit 1
				sql="select date_actual,state from dincelwarehouse_sale_order_delivery  where order_id='%s' " % (_id)
				if is_del and sch_id:
					sql+=" and id!='%s' " % (sch_id)
				sql+="  order by date_actual limit 1"		
				cr.execute(sql)
				rows2 = cr.fetchall()
				
				if not rows2 or len(rows2) == 0:#none found if all schedule deleted...
					update = True
					dt=None
					state=""
					
				else:
					for row2 in rows2:
						update = True
						dt=row2[0]
						state=row2[1].capitalize()
						
		except Exception,e:
			pass				
		return update, dt, state
		
	def set_next_delivery_date(self, cr, uid, ids, _id, sch_id, is_del, context=None):
		update, dt, state = self.get_next_delivery_date(cr, uid, ids, _id, sch_id, is_del, context)
		if update:
			if dt:
				sql="update sale_order set x_dt_actual='%s' where id='%s'" % (dt, _id)
				cr.execute(sql)
				sql="update dincelmrp_accessories set dt_actual='%s' where order_id='%s'" % (dt, _id)
				cr.execute(sql)
			else:
				sql="update sale_order set x_dt_actual=null where id='%s'" % (_id)
				cr.execute(sql)
				sql="update dincelmrp_accessories set dt_actual=null where order_id='%s'" % (_id)
				cr.execute(sql)
		'''		
		sql="select date_actual,state from dincelwarehouse_sale_order_delivery  where state in ('draft','open','partial','confirm') and order_id='%s'" % (_id)
		if is_del and sch_id:
			sql+=" and id!='%s' " % (sch_id)
		sql+="  order by date_actual limit 1"	
		#_logger.error("dincelwarehouse_sale_order_delivery111["+str(sql)+"]["+str(sch_id)+"]")
		cr.execute(sql)
		rows1 = cr.fetchall()
		if rows1 and len(rows1) >0:
			for row1 in rows1:
				sql="update sale_order set x_dt_actual='%s' where id='%s'" % (row1[0], _id)
				cr.execute(sql)
				sql="update dincelmrp_accessories set dt_actual='%s',deli_status='%s' where order_id='%s'" % (row1[0],row1[1].capitalize(), _id)
				cr.execute(sql)
		else:
			sql="select date_actual,state from dincelwarehouse_sale_order_delivery  where order_id='%s' and id!='%s' order by date_actual limit 1" % (_id, sch_id)
			cr.execute(sql)
			rows2 = cr.fetchall()
			#_logger.error("dincelwarehouse_sale_order_delivery222["+str(sql)+"]["+str(sch_id)+"]")
			if not rows2 or len(rows2) == 0:#none found if all schedule deleted...
				sql="update sale_order set x_dt_actual=null where id='%s'" %(_id)
				cr.execute(sql)
				sql="update dincelmrp_accessories set dt_actual=null,deli_status=' ' where order_id='%s'" % (_id)
				cr.execute(sql)
			else:
				for row2 in rows2:
					date_actual = row2[0]
					sql="update sale_order set x_dt_actual='%s' where id='%s'" %(date_actual, _id)
					cr.execute(sql)
					sql="update dincelmrp_accessories set dt_actual='%s',deli_status='%s' where order_id='%s'" % (date_actual, row2[1].capitalize(), _id)
					cr.execute(sql)
		#else:
		#	#sql="select * from dincelstock_pickinglist where pick_order_id='%s' order by date_picking desc limit 1 " % (_id)
		#	#cr.execute(sql)
		#	#rows2 = cr.fetchall()
		#	#if rows2 and len(rows2) >0:
		#	#	for row2 in rows2:
		#	#		sql="update sale_order set x_dt_actual='%s' where id='%s'" %(row2['date_actual'], _id)
		#	#		cr.execute(sql)
		'''
		return True	
	def get_due_date_v2(self, cr, uid, ids, _termid, dtinv, dtdeli, context=None): 
		
		dtinv2		= datetime.datetime.strptime(str(dtinv), "%Y-%m-%d").strftime("%Y-%m-%d")#.date()
		today_dt 	= datetime.datetime.today().strftime('%Y-%m-%d')
		dt_due		= dtinv
		try:
			today_dt 	= dateutil.parser.parse(str(today_dt))
			dtfrom2 	= dateutil.parser.parse(str(dtinv))
			_term = self.pool.get('account.payment.term').browse(cr, uid, _termid, context=context)
			if _term.x_days:
				_days=_term.x_days
			else:
				_days=0
			if _term.x_eom:
				dtfrom2=dtfrom2+relativedelta(months=+1) #Next Month
				if _term.x_payterm_code=="30EOM":
					#dtfrom2=dtfrom2+relativedelta(months=+1)
					dt_due=self.last_day_of_month(dtfrom2)#get_month_day_range(dtfrom2)
				else:

					dtfrom3 = str(dtfrom2.year) +"-"+str(dtfrom2.month)+"-1"
					dtfrom2 = dateutil.parser.parse(str(dtfrom3))
					if _days>0:
						_days-=1
					dt_due=dtfrom2+timedelta(days=_days)
			else:
				if _days==0:
					dt_due=dtinv
				else:
					dtfrom2 = dateutil.parser.parse(str(dtdeli))
					dt_due	= dtfrom2+timedelta(days=_days) #
		except Exception,e:
			dt_due=dtinv
			_logger.error("invoice_create.get_due_date_v2 [%s] [%s] [%s] " % (_term, dtinv, str(e)))
		return dt_due
		
	def get_due_date(self, cr, uid, ids, _term, dtinv, dtdeli, context=None): 
		
		dtinv2		= datetime.datetime.strptime(str(dtinv), "%Y-%m-%d").strftime("%Y-%m-%d")#.date()
		today_dt 	= datetime.datetime.today().strftime('%Y-%m-%d')
		dt_due		= dtinv
		try:
			today_dt 	= dateutil.parser.parse(str(today_dt))
			dtfrom2 	= dateutil.parser.parse(str(dtinv))
			if _term=="30EOM":
				dtfrom2=dtfrom2+relativedelta(months=+1)
				dt_due=self.last_day_of_month(dtfrom2)#get_month_day_range(dtfrom2)
				#if dtfrom3<today_dt:
				#	_over=True
			elif _term=="30DELI":
				#_ac_term=True
				dtfrom2 = dateutil.parser.parse(str(dtdeli))
				dt_due=dtfrom2+timedelta(days=30) #
			elif _term=="7DAYS":
				#_ac_term=True
				dt_due=dtfrom2+timedelta(days=7) #
				#if dtfrom3<today_dt:
				#	_over=True
			elif _term=="14DELI":
				#_ac_term=True
				dtfrom2 = dateutil.parser.parse(str(dtdeli))
				dt_due=dtfrom2+timedelta(days=14) #
				#if dtfrom3<today_dt:
				#	_over=True
			elif _term=="14DAYS":#14 days eom
				#_ac_term=True
				dtfrom2 = dtfrom2+relativedelta(months=+1)
				dtfrom3 = str(dtfrom2.year) +"-"+str(dtfrom2.month)+"-1"
				dtfrom2 = dateutil.parser.parse(str(dtfrom3))
				#dtfrom2=self.get_first_day(cr, uid, ids, dtfrom2)
				dt_due=dtfrom2+timedelta(days=13) #Note: cause 1 is already added hence (13+1)=14
				#if dtfrom3<today_dt:
				#	_over=True
			else:#cod or other
				dt_due=dtinv
		except Exception,e:
			dt_due=dtinv
			_logger.error("invoice_create.get_due_dateget_due_date [%s] [%s] [%s] " % (_term, dtinv, str(e)))
		return dt_due
		
	def _create_balance_normal(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		obj_inv 	= self.pool.get('account.invoice')	
		obj_invline	= self.pool.get('account.invoice.line')
		product_obj = self.pool.get('product.product')	
		tot_price 	= 0	
		for record in self.browse(cr, uid, ids, context=context):		
			vals = {
					'x_sale_order_id': record.id,
					'x_inv_type':'balance',
                    'origin': record.name,
                    'reference': record.name,
                    'partner_id': record.partner_id.id,
					'user_id':record.user_id.id,
					#'internal_number': record.name, #cannot delete once this value is recorded
					'section_id': 1,
                    'type': 'out_invoice',
					'account_id':record.partner_id.property_account_receivable.id
					}
			today_dt = self.pool.get("account.invoice").get_today_au(cr, uid, ids)#datetime.datetime.today().strftime('%Y-%m-%d')
			vals['date_invoice']=today_dt#datetime.datetime.now() 
			vals['date_due']=vals['date_invoice']
			#_logger.error("invoice_sales_validate.payment_termpayment_term["+str(record.payment_term)+"]")
			if record.payment_term: 
				
				code 	 = record.payment_term.x_payterm_code
				vals['payment_term']=record.payment_term.id
				#if code:	
				#	#vals['date_due']= self.get_due_date(cr, uid, ids,code,vals['date_invoice'],vals['date_invoice'])
				vals['date_due']= self.get_due_date_v2(cr, uid, ids, record.payment_term.id, vals['date_invoice'],vals['date_invoice'])
					
				#	#if code == "30EOM":
				#	#	dt1=vals['date_invoice'] + datetime.timedelta(365/12)
				#	#	vals['date_due']= self.last_day_of_month(dt1)
				#	#_logger.error("invoice_sales_validate.x_payterm_codex_payterm_code["+str(dt1)+"]["+str(vals['date_due'])+"]")
				#	#date_after_month = datetime.today()+ relativedelta(months=1) 
				#	#elif code == "COD":
				#	#	vals['date_due']=vals['date_invoice']
						
			proj_id = record.x_project_id and record.x_project_id.id  or False		
			if proj_id:
				vals['x_project_id']=proj_id
			
			#first create the invoice record
			inv_id = obj_inv.create(cr, uid, vals, context=context)
			
			
			for line in record.order_line:
				qty = line.product_uom_qty
				product_id = line.product_id.id
				#if ar_items_done.has_key(product_id):
				#	qty = qty - ar_items_done[product_id]		
				#-----------------------------------------------------------------------------------
				#if qty > 0:#this condition removed allowing -ve value item (eg discount allowed)...[24/10/17]
				#-----------------------------------------------------------------------------------	
				vals = {
					'product_id': product_id,
					'quantity': qty,
					'invoice_id': inv_id,
					'origin': record.name,
					'discount':line.discount,
					'price_unit': line.price_unit,
					'price_subtotal': line.price_unit*qty,
					'x_order_length':line.x_order_length,
					'x_order_qty':line.x_order_qty,
				}
				vals['name']= line.product_id.name
				
				if line.x_region_id:
					vals['x_region_id']= line.x_region_id.id	
				if line.x_coststate_id:
					vals['x_coststate_id']= line.x_coststate_id.id	
					
				
				#>>> todo...somethiems taxes not being recorded in invoice...14/7/2016 >> 1/3/2017....no isue
				#instead of product settings ...pick from line items....eg nz do not have tax
				#if line.product_id.taxes_id:
				#	vals['invoice_line_tax_id'] = [(6, 0, line.product_id.taxes_id.ids)]
				if line.tax_id:
					vals['invoice_line_tax_id'] = [(6, 0, line.tax_id.ids)]
				obj_invline.create(cr, uid, vals, context=context)
		
			#--------------------------------------------------------------------
			#now create deposit balance, as negative to balance out the total
			#_ids = obj_inv.search(cr, uid, [('x_inv_type', '=', 'deposit'),('x_sale_order_id', '=', record.id),('state', '!=', 'cancel')]) 	
			_ids = obj_inv.search(cr, uid, [('x_sale_order_id', '=', record.id),('state', 'not in', ['cancel','offset']),('id','!=',inv_id)]) 	
			#_logger.error("obj_inv_search_obj_inv_searchobj_inv_search--["+str(_ids)+"]")
			for record1 in obj_inv.browse(cr, uid, _ids, context=context):	
				for line1 in record1.invoice_line:
					vals = {
						'product_id': line1.product_id.id,
						'quantity': -line1.quantity,
						'invoice_id': inv_id,
						'origin': record.name,
						'discount':line1.discount,
						'price_unit': line1.price_unit,
						'price_subtotal': -line1.price_unit*line1.quantity,#qty,
					}
					vals['name']= line1.product_id.name
					
					if line1.x_region_id:
						vals['x_region_id']= line1.x_region_id.id	
					if line1.x_coststate_id:
						vals['x_coststate_id']= line1.x_coststate_id.id		
						 
					
					#todo...somethiems taxes not being recorded in invoice...14/7/2016  >> 1/3/2017....no issue
					#instead of product settings ...pick from line items....eg nz do not have tax
					#if line1.product_id.taxes_id:
					#	vals['invoice_line_tax_id'] = [(6, 0, line1.product_id.taxes_id.ids)]
					if line1.invoice_line_tax_id:
						vals['invoice_line_tax_id'] = [(6, 0, line1.invoice_line_tax_id.ids)]
						
					obj_invline.create(cr, uid, vals, context=context)
			obj_inv = self.pool.get('account.invoice')
			obj_inv = obj_inv.browse(cr, uid, inv_id, context)
			obj_inv.button_compute(True) #For taxes
			
			#--------------
			if record.x_ac_status==None or record.x_ac_status=="hold":
				self.write(cr, uid, [record.id], {'x_ac_status':'open'})	
			#--------------
			
			#str1 = "amttax["+str(obj_inv.amount_tax) + "]amtuntax["+str(obj_inv.amount_untax) + "] calculated["+str(obj_inv.amount_untax*0.1) + "]" 
			
			view_id 		= self.pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'dincelaccount.invoice.form')], limit=1) 	
			#_logger.error("invoice_sales_validate.view_id["+str(view_id)+"]")
			value = {
				'domain': str([('id', 'in', inv_id)]),
				'view_type': 'form',
				'view_mode': 'form',
				'res_model': 'account.invoice',
				'view_id': view_id,
				'type': 'ir.actions.act_window',
				'name' : _('Invoice'),
				'res_id': inv_id
			}
			return value
				
	def _find_in_itemsdone(self, cr, uid, ids, _arr, _item, context=None):
		vals1 ={
				'found':0,
				'qty':0,
				'rate':0,
				'qty1':0,
				'rate1':0,
			}
		
		for _line in _arr:
			if _line['product_id'] ==_item['product_id'] and _line['order_len'] ==_item['order_len']:
				vals1['found']=1
				vals1['qty']=_line['order_qty'] - _item['order_qty']
				vals1['rate']=_line['price_unit'] - _item['price_unit']
				vals1['qty1']= _item['order_qty']
				vals1['rate1']= _item['price_unit']
				
		return vals1
		
	def _create_balance_revised(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		obj_inv 	= self.pool.get('account.invoice')	
		obj_invline	= self.pool.get('account.invoice.line')
		product_obj = self.pool.get('product.product')	
		tot_price 	= 0	
		ar_items_done 	= []
		for record in self.browse(cr, uid, ids, context=context):		
			#for record in self.browse(cr, uid, ids, context=context):		
			vals = {
					'x_sale_order_id': record.id,
					'x_inv_type':'balance',
                    'origin': record.name,
                    'reference': record.name,
                    'partner_id': record.partner_id.id,
					'x_revise_sn': record.x_revise_sn,
					'user_id':record.user_id.id,
					#'internal_number': record.name, #cannot delete once this value is recorded
					'section_id': 1,
                    'type': 'out_invoice',
					'account_id':record.partner_id.property_account_receivable.id
					}
			
			vals['date_invoice']=self.pool.get("account.invoice").get_today_au(cr, uid, ids)#datetime.datetime.now() 
			vals['date_due']=vals['date_invoice']
			#_logger.error("invoice_sales_validate.payment_termpayment_term["+str(record.payment_term)+"]")
			if record.payment_term: 
				
				#code 	 = record.payment_term.x_payterm_code
				vals['payment_term']=record.payment_term.id
				#if code:	
				#	vals['date_due']= self.get_due_date(cr, uid, ids,code,vals['date_invoice'],vals['date_invoice'])
				vals['date_due']= self.get_due_date_v2(cr, uid, ids,record.payment_term.id,vals['date_invoice'],vals['date_invoice'])
				#	#if code == "30EOM":
				#	#dt1=vals['date_invoice'] + datetime.timedelta(365/12)
				#	#vals['date_due']= self.last_day_of_month(dt1)
				#	#_logger.error("invoice_sales_validate.x_payterm_codex_payterm_code["+str(dt1)+"]["+str(vals['date_due'])+"]")
				#	#date_after_month = datetime.today()+ relativedelta(months=1) 
				#	#elif code == "COD":
				#	#	vals['date_due']=vals['date_invoice']
						
			proj_id = record.x_project_id and record.x_project_id.id  or False		
			if proj_id:
				vals['x_project_id']=proj_id
				
			#first create the invoice record
			inv_id = obj_inv.create(cr, uid, vals, context=context)
			#balance out old invoice lines...
			_sn=len(record.order_line)#record1.invoice_line=
			_ids = obj_inv.search(cr, uid, [('x_inv_type', '=', 'balance'),('x_sale_order_id', '=', record.id)]) 	
			for record1 in obj_inv.browse(cr, uid, _ids, context=context):	
				for line1 in record1.invoice_line:
					vals1 ={
						'sequence':_sn,
						'product_id':line1.product_id.id,
						'x_order_length':line1.x_order_length,
						'x_order_qty':-line1.x_order_qty,
						'price_unit':line1.price_unit,
						'quantity':-line1.quantity,
						'invoice_id': inv_id,
						'origin': record.name,
						'name': line1.name + " *[INV " + str(line1.invoice_id.id) +"]",
						'discount':line1.discount,
						'price_subtotal': line1.price_unit*line1.quantity,
					}
					if line1.x_region_id:
						vals1['x_region_id']= line1.x_region_id.id	
					if line1.x_coststate_id:
						vals1['x_coststate_id']= line1.x_coststate_id.id		
					#instead of product settings tax...get from line items
					if line1.invoice_line_tax_id:
						vals['invoice_line_tax_id'] = [(6, 0, line1.invoice_line_tax_id.ids)]	
					#if line1.product_id.taxes_id:
					#	vals1['invoice_line_tax_id'] = [(6, 0, line1.product_id.taxes_id.ids)]	
					#	
					ar_items_done.append(vals1)
					obj_invline.create(cr, uid, vals1, context=context)
					_sn=_sn+1
					
			#new items....			
			_sn=0
			for line in record.order_line:
				qty = line.product_uom_qty
				product_id = line.product_id.id
				
				if qty > 0:
					
					vals = {
						'sequence':_sn,
						'product_id': product_id,
						'quantity': qty,
						'invoice_id': inv_id,
						'origin': record.name,
						'discount':line.discount,
						'price_unit': line.price_unit,
						'price_subtotal': line.price_unit*qty,
						'x_order_length':line.x_order_length,
						'x_order_qty':line.x_order_qty,
					}
					vals['name']= line.product_id.name
					
					if line.x_region_id:
						vals['x_region_id']= line.x_region_id.id	
					if line.x_coststate_id:
						vals['x_coststate_id']= line.x_coststate_id.id		
						 
					
					#todo...somethiems taxes not being recorded in invoice...14/7/2016
					#instead of product setting...get tax from line items 1/3/2017
					if line.tax_id:
						vals['invoice_line_tax_id'] = [(6, 0, line.tax_id.ids)]
					#if line.product_id.taxes_id:
					#	vals['invoice_line_tax_id'] = [(6, 0, line.product_id.taxes_id.ids)]	
					obj_invline.create(cr, uid, vals, context=context)
					_sn=_sn+1
					
			obj_inv = self.pool.get('account.invoice')
			obj_inv = obj_inv.browse(cr, uid, inv_id, context)
			obj_inv.button_compute(True) #For taxes
			if obj_inv.amount_total<0: #then refund invoice
				sql ="UPDATE account_invoice SET type='out_refund' WHERE id=" + str(inv_id)
				cr.execute(sql)
			#--------------
			if record.x_ac_status==None or record.x_ac_status=="hold":
				self.write(cr, uid, [record.id], {'x_ac_status':'open'})	
			#--------------
			
			#str1 = "amttax["+str(obj_inv.amount_tax) + "]amtuntax["+str(obj_inv.amount_untax) + "] calculated["+str(obj_inv.amount_untax*0.1) + "]" 
			
			view_id = self.pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'dincelaccount.invoice.form')], limit=1) 	
			#_logger.error("invoice_sales_validate.view_id["+str(view_id)+"]")
			value = {
				'domain': str([('id', 'in', inv_id)]),
				'view_type': 'form',
				'view_mode': 'form',
				'res_model': 'account.invoice',
				'view_id': view_id,
				'type': 'ir.actions.act_window',
				'name' : _('Invoice'),
				'res_id': inv_id
			}
			return value
		#_logger.error("_create_balance_revised.ar_items_donear_items_done["+str(ar_items_done)+"]")
	def open_popup_approve_request(self, cr, uid, _id,type,subtype=None, context=None):
		#if chk==-1:
		#	type="credit"
		#else:
		#	type="discount"
		if subtype==None:
			subtype="order"
		sql="select 1 from dincelsale_order_approve where order_id='%s' and state='open'" % (_id)	
		cr.execute(sql)
		rows1 = cr.fetchall()
		if len(rows1) > 0:
			_pending=True 
		else:
			_pending=False
		context1={
				'default_order_id': _id, 
				'default_request_uid': uid, 
				'default_type': type, 
				'default_subtype': subtype, 
				'default_approve_pending': _pending, 
				}	
		if 'o_ids' in context:	
			context1['o_ids']=context['o_ids']
		#if 'o_names' in context:	
		#	context1['o_names']=context['o_names']	
		value = {
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'saleorder.approve.request',
			'type': 'ir.actions.act_window',
			'name' : _('Approval request'),
			'context':context1,
			'target': 'new',
		}
		return value
		
	def create_balance_invoice(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		#for record in self.browse(cr, uid, ids, context=context):	
			#gets all invoiced items qty
		#chk=self.check_discount_allowed_message(cr, uid, ids, ids[0]) 
		chk=self.check_discount_allowed(cr, uid, ids, ids[0]) 
		if chk==-1 or chk==1:
			if chk==-1:
				type="credit"
			else:
				type="discount"
			return self.open_popup_approve_request(cr, uid, ids[0],type, None, context)
			#view_id = self.pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'dincelaccount.invoice.form')], limit=1) 	
			
			#	raise osv.except_osv(
			#				_('Negative quantity found!'),
			#				_('Please contact account or your manager to continue.'))
			#elif chk==1:
			
			#if chk!=1:
			#return
		zero_price=False
		for record in self.browse(cr, uid, ids, context=context):	
			deli_found_but=False
			if record.x_pudel=="del":
				deli_found_but=True
			for line in record.order_line:
				if line.product_id and line.product_id.x_is_main=="1":
					if line.price_unit==0.0:
						zero_price=True
				if deli_found_but==True:
					if line.product_id and line.product_id.x_prod_cat	and line.product_id.x_prod_cat=="freight":
						deli_found_but=False
			if zero_price==True:
				raise osv.except_osv(_('Error'),
									_('Zero or invalid rate found.'))
			if deli_found_but == True:
				raise osv.except_osv(_('Delivery charge missing'),
									_('Please enter delivery charge in order lines to continue.'))
			
			if record.x_revise_sn > 0:
				return self._create_balance_revised(cr, uid, ids, context=context)
			else:
				return self._create_balance_normal(cr, uid, ids, context=context)
				
 
	def create_balance_one_invoice(self, cr, uid, ids, context=None):
		if context is None:
			context = {}			
		#ctx = dict(context)
		#compose_form_id		= self.pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'dincelaccount.view_dincelsale_order_balance1_form')], limit=1) 	
		#_obj = self.pool.get('sale.order').browse(cr, uid, ids[0], context=context)
		chk=self.check_discount_allowed(cr, uid, ids, ids[0]) 
		if chk==-1 or chk==1:
			if chk==-1:
				type="credit"
			else:
				type="discount"
			return self.open_popup_approve_request(cr, uid, ids[0],type,None, context)
		return {
				'name': _('Balance 1 Invoice'),
				'type': 'ir.actions.act_window',
				'view_type': 'form',
				'view_mode': 'form',
				'res_model': 'dincelsale.order.balance',
				'context':{
						'default_order_id': ids[0], 
						#'default_pudel': _obj.order_id.x_pudel, 
						
				},
				'target': 'new',
			}		  
	
	@api.multi
	def button_mark_as_done(self):
		return self.write({'state':'done'})
		
	@api.multi
	def button_mark_as_draft(self):
		#vals={'state':'draft'}
		#reset the order to draft...also check if mrp has been cancelled....just in case...
		sql="update mrp_production set state='draft' where state='cancel' and x_sale_order_id='%s'" % (self.id)
		self.env.cr.execute(sql)
		return self.write({'state':'draft'})
		
	@api.multi
	def make_invoice_payment(self):
		view_id = self.env.ref('dincelaccount.view_dincelaccount_voucher_invoice_form').id
		context = self._context.copy()
		so =self.env['sale.order'].browse(self.id)# self.pool['sale.order'].browse(cr, uid, self.id, context=context)
		#_logger.error("_create_balance_revised.make_invoice_paymentmake_invoice_payment["+str(so.partner_id.id)+"]")
		context['partner_id']=so.partner_id.id
		context['type']="receipt"
		return {
			'name':'Invoice Payment',
			'view_type':'form',
			'view_mode':'form',
			'views' : [(view_id,'form')],
			'res_model':'account.voucher',
			'view_id':view_id,
			'type':'ir.actions.act_window',
			#'partner_id':so.partner_id.id,
			#'target':'new',
			'context':context,
		}
		
	'''def open_deposit_invoice(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		view_id 		= self.pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'dincelaccount.invoice.form')], limit=1) 	
		inv_id = 232
		value = {
			'domain': str([('id', 'in', inv_id)]),
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'account.invoice',
			'view_id': view_id,
			'type': 'ir.actions.act_window',
			'name' : _('Invoice'),
			'res_id': inv_id
		}
		return value	
	'''	
		
	def create_deposit_invoice(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		chk=self.check_discount_allowed(cr, uid, ids, ids[0]) 
		if chk==-1 or chk==1:
			if chk==-1:
				type="credit"
			else:
				type="discount"
			return self.open_popup_approve_request(cr, uid, ids[0],type,None, context)
			
		obj_inv 	= self.pool.get('account.invoice')	
		obj_invline	= self.pool.get('account.invoice.line')
		product_obj = self.pool.get('product.product')	
		tot_price = 0
		zero_price=False
		tax_id1=False
		for record in self.browse(cr, uid, ids, context=context):
			#chk=self.check_discount_allowed_message(cr, uid, ids, record.id) 
			#if chk!=1:
			#	return
				
			for line in record.order_line:
				#if line.price_unit>0:
				#	zero_price=False
				if line.product_id.x_prod_cat =='customlength':
					if line.price_unit==0.0:
						zero_price=True
					qty = line.product_uom_qty
					price_unit=line.price_unit 
					tot_price += qty*price_unit
					if line.tax_id:
						tax_id1=line.tax_id
		if zero_price==True:
			raise osv.except_osv(_('Error'),
									_('Zero or invalid rate found.'))
		
		if tot_price > 0:
			tot_price = 0.33*tot_price #33 % of custom length
			
			product_id =  product_obj.find_deposit_product(cr, uid, context=context)
			if product_id:
				
				product_id	 = product_id[0]
				product_obj  =  product_obj.browse(cr, uid, product_id, context)
				vals = {
					'x_sale_order_id': record.id,
					'x_inv_type':'deposit',
                    'origin': record.name,
                    'reference': record.name,
                    'partner_id': record.partner_id.id,
					'user_id':record.user_id.id,
					#'internal_number': record.name,
					'section_id': 1,
                    'type': 'out_invoice',
					'account_id':record.partner_id.property_account_receivable.id
					}
			
				vals['date_invoice']=self.pool.get("account.invoice").get_today_au(cr, uid, ids)# datetime.datetime.now() 
				vals['date_due']=vals['date_invoice']
				
				proj_id = record.x_project_id and record.x_project_id.id  or False		
				if proj_id:
					vals['x_project_id']=proj_id
				#if record.payment_term: 
				#	vals['payment_term']=record.payment_term.id	
				_payterm = 	self.pool.get('account.payment.term').search(cr, uid, [('x_payterm_code', '=', 'immediate')], limit=1)
				if _payterm:
					vals['payment_term']=_payterm[0]	
				
				inv_id = obj_inv.create(cr, uid, vals, context=context)
			
				vals = {
					'product_id': product_id,
					'quantity': '1',
					'invoice_id': inv_id,
					'origin': record.name,
					'price_unit': tot_price,
					'price_subtotal': tot_price,
				}
				vals['name'] = product_obj.name
				 
				
				if tax_id1:
					vals['invoice_line_tax_id'] = [(6, 0, tax_id1.ids)]
				#if product_obj.taxes_id:
				#	vals['invoice_line_tax_id'] = [(6, 0, product_obj.taxes_id.ids)]
							
				obj_invline.create(cr, uid, vals, context=context)
				#for taxes
				#obj_inv = self.pool.get('account.invoice')
				obj_inv = obj_inv.browse(cr, uid, inv_id, context)
				obj_inv.button_compute(True) #For taxes
				
				#--------------
				val_sts={}#'state':'progress'} not valid progress status at this state.....
				if  record.x_ac_status==None or record.x_ac_status=="hold":
					val_sts['x_ac_status']='open'
					self.write(cr, uid, [record.id], val_sts)		
				#if record.x_dep_paid==None or record.x_dep_paid=="":
				#	val_sts['x_ac_status']='open'
					
				
				#self.write(cr, uid, [record.id], val_sts)		
				#--------------
				view_id = self.pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'dincelaccount.invoice.form')], limit=1) 	
				#_logger.error("invoice_sales_validate.view_id["+str(view_id)+"]")
				value = {
                    'domain': str([('id', 'in', inv_id)]),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'account.invoice',
                    'view_id': view_id,
                    'type': 'ir.actions.act_window',
                    'name' : _('Invoice'),
                    'res_id': inv_id
                }
				return value	
				#return inv_id
		return False		
	
	def order_produced_check(self, cr, uid, ids, _id, context=None):
		if context is None:
			context = {}
		sql="select sum(m.x_order_qty-m.x_produced_qty) as rem,sum(m.x_produced_qty) as ytd  from mrp_production m,product_template t,product_product p where m.product_id=p.id and t.id=p.product_tmpl_id and m.x_sale_order_id='%s' " % (str(_id))
		cr.execute(sql)
		rows2   = cr.fetchall()
		if rows2 and len(rows2)>0:
			rem=0.0
			ytd=0.0
			for row2 in rows2:
				rem+=float(row2[0])
				ytd+=float(row2[1])
			if rem<=0.0:
				sql ="UPDATE sale_order set x_prod_status='complete' where id='%s'" %(str(_id))
				cr.execute(sql)
			else:
				if ytd>0.0:
					sql ="UPDATE sale_order set x_prod_status='part' where id='%s'" %(str(_id))
					cr.execute(sql)
				else:
					#_logger.error("Inside Check Function ["+str(_id)+"]")
					checkSql = "select state from dincelmrp_schedule where state in('printed','confirmed') and order_id = '%s'" %(str(_id))
					cr.execute(checkSql)
					rowsCheck   = cr.fetchall()
					if rowsCheck and len(rowsCheck)>0:
						for row in rowsCheck:
							_st=row[0]
							sql ="UPDATE sale_order set x_prod_status='%s',state='progress' where id='%s'" %(_st, str(_id))
							cr.execute(sql)
							#self.pool.get('sale.order').write(cr, uid, _id, {'x_prod_status': _st,'state':'progress'}, context=context)	
							
					else:
						#self.pool.get('sale.order').write(cr, uid, _id, {'x_prod_status': '','state':'draft'}, context=context)	
						sql ="UPDATE sale_order set x_prod_status='',state='draft' where id='%s'" %(str(_id))
						cr.execute(sql)
					#	checkSql = "select 1 from dincelmrp_schedule where state='confirmed' and order_id = '%s'" %(str(_id))
					#	cr.execute(checkSql)
					#	rowsCheck   = cr.fetchall()
					#	if(len(rowsCheck)):
					#		sql ="UPDATE sale_order set x_prod_status='confirmed',state='progress' where id='%s'" %(str(_id))
					#		cr.execute(sql)
		'''			
		sql ="SELECT state from mrp_production where x_sale_order_id='%s'" %(str(_id))
		cr.execute(sql)
		rows = cr.fetchall()
		if rows and len(rows)>0:
			_state=""
			for row in rows:
				_st=row[0]
				if _st=="done" and _state=="":
					_state="complete"
				elif _st=="in_production":## or _st=="ready":
					_state="part"
				else:
					_st=""
			if _state!="":		
				sql ="UPDATE sale_order set x_prod_status='%s' where id='%s'" %(str(_state),str(_id))
				cr.execute(sql)'''
				
	def create_mo_order_dcs(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		#o_bom 	= self.pool.get('mrp.bom')	
		#o_prd 	= self.pool.get('mrp.production')	
	
	def _updatelink_order_dcs(self, cr, uid, ids, _id, context=None):
		if context is None:
			context = {}
		url=self.pool.get('dincelaccount.config.settings').get_dcs_api_url(cr, uid, ids, "getorder", _id, context=context)	
		str1=""	
		if url:#rows and len(rows) > 0:
			#--- check flag of payment before update ---#
			self.pool.get('sale.order').update_payment_order(cr, uid, ids, _id, context=context)		
			#--- check flag of payment before update ---#
			#f = urllib2.urlopen(url)
			#response = f.read()
			#str1= simplejson.loads(response)
			str1=self._get_url_contents(cr, uid, url, context)
		#_logger.error("dincelaccount_sale_orderdincelaccount_sale_order._updatelink_order_dcs["+str(_id)+"]["+str(str1)+"]["+str(url)+"]")	
	
	#todo...apply timeout and this function call in other places as well....7/03/2017
	def _get_url_contents(self,cr, uid, url, context=None):	
		str1=None
		if url:
			try:
				f = urllib2.urlopen(url, timeout = 3) #3 seconds timeout
				response = f.read()
				str1= simplejson.loads(response)
			except urllib2.URLError as e:
				_logger.error("dincelaccount_sale_order_get_url_contents.url["+str(url)+"]uid["+str(uid)+"]["+str(e)+"]_not_catch")	   #catchedprint type(e)    #not catch
				str1="timeout"
			except socket.timeout as e:
				_logger.error("dincelaccount_sale_order_get_url_contents.url["+str(url)+"]uid["+str(uid)+"]["+str(e)+"]")	   #catched
				str1="timeout"
				#pass
		return str1
		
	def updatelink_order_dcs(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		#order_id = ids[0]
		#request = urllib.urlopen("http://deverp.dincel.com.au/dcsapi/")
		#sql ="SELECT dcs_api_url FROM dincelaccount_config_settings";
		#cr.execute(sql)
		#rows = cr.fetchone()
		url=self.pool.get('dincelaccount.config.settings').get_dcs_api_url(cr, uid, ids, "getorder", ids[0], context=context)		
		if url:#rows and len(rows) > 0:
			#--- check flag of payment before update ---#
			self.pool.get('sale.order').update_payment_order(cr, uid, ids, ids[0], context=context)		
			#--- check flag of payment before update ---#
			
			#url="http://deverp.dincel.com.au/odoo/dcsapi/index.php?id="+str(ids[0])
			try:
				#f 			= urllib2.urlopen(url, timeout=3)
				#response 	= f.read()
				#str1		= simplejson.loads(response)
				str1=self._get_url_contents(cr, uid, url, context)
				if str1==None or str1 == "" or  str1=="timeout":
					raise osv.except_osv(_('Error'), _('Server not available, please try again later.'))
				else:
					item 		= str1['item']
					status1		= str(item['post_status'])
					ordercode	= str(item['curr_ordercode'])
					colorcode	= str(item['curr_colourcode'])
					
					#obj		=  self.browse(cr, uid, ids[0], context=context)
					#_name 	=  str(obj.name)
					
					if status1=="success":
						
						sql ="UPDATE sale_order SET origin='"+ordercode+"'  "	# WHERE id='"+str(ids[0])+"'"
						if colorcode:
							sql +=",x_colorcode='"+colorcode+"' "
						sql += " WHERE id='"+str(ids[0])+"'"	
						cr.execute(sql)
						return True
					else:
						if item['errormsg']:
							str1=item['errormsg']
						else:
							str1="Error while updating order."
						raise osv.except_osv(_('Error'), _(''+str1))
			except Exception,e:
				_logger.error("error_updatelink_order_dcs.error_updatelink_order_dcs["+str(url)+"]uid["+str(uid)+"]["+str(e)+"]")	   #catched
				raise osv.except_osv(_('Error'), _(''+str(e[1])))
				
				#@pass
	def dcs_partner_statement_pdf(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		#datas = {'ids': context.get('active_ids', [])}
		#datas['form']  = self.read(cr, uid, ids, context=context)[0]
		#return self.pool['report'].get_action(cr, uid, [], 'account.report_partner_statement_pdf', data=datas, context=context)	
		_ids=""
		#dt=""
		for record in self.browse(cr, uid, ids):
			#dt=record.date_order
			#dt = datetime.datetime.now()
			#dt = date.today()
			if record.partner_id:
				_ids=record.partner_id.id
		return self.pool.get('res.partner').download_statement_pdf(cr, uid, _ids, context=context)			
		'''url=self.pool.get('dincelaccount.config.settings').report_preview_url(cr, uid, ids,"statement","",context=context)		
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
					'url': '/web/binary/download_file?model=account.invoice&field=datas&id=%s&path=%s&filename=%s' % (str(ids[0]),save_path,fname),
					'context': context}'''
					
class dincelaccount_sale_order_line(osv.Model):
	_inherit="sale.order.line"
		
	def region_id_change(self, cr, uid, ids, x_region_id, x_region_id1, context=None):
		
		result 		= {}	
		context 	= context or {}
		result.update({'x_region_id': x_region_id1})
		#_logger.error("onchange_order_line_dcs.region_id_change["+str(result)+"]["+str(x_region_id1)+"]")
		return {'value': result}
		
	def product_qty_changed(self, cr, uid, ids, product, qty=0,length=0, partner_id=False, payment_term = False, dt_sale = False,loc_id =False, context=None):
		
		result 		= {}	
		context 	= context or {}

		if not partner_id:
			raise osv.except_osv(_('No Customer Defined!'), _('Before choosing a product,\n select a customer in the sales form.'))
		
		warning 	= False
		
		domain 		= {}
		code 		= None
		
		order_id	= None
		
		qty_lm 		= qty
		authorise_len=False
		for record in self.browse(cr, uid, ids, context=context):
			order_id = record.order_id.id
			authorise_len=record.order_id.x_authorise_len
			
		partner_obj = self.pool.get('res.partner')
		product_obj = self.pool.get('product.product')
		term_obj 	= self.pool.get('account.payment.term')
		
		rate_obj 	= self.pool.get('dincelcrm.customer.rate') 
		
		order_obj 	= self.pool.get('sale.order')
		order_obj 	= order_obj.browse(cr, uid, order_id)
		#found_rate  = False
		ac_rate		= False
		grp_rate	= False
		
		partner 	= partner_obj.browse(cr, uid, partner_id)
		lang 		= partner.lang
		context 	= {'lang': lang, 'partner_id': partner_id}
		context_partner = {'lang': lang, 'partner_id': partner_id}
		
		warning_msgs = ''
		
		product_obj  = product_obj.browse(cr, uid, product, context=context_partner)
		#if(product_obj.name):
		if(self.pool.get('sale.order').check_line_details(cr, uid, product, length, authorise_len, context=context) == 1):	
			raise osv.except_osv(_('Error!'), _('The length you have entered [%s] already exists as a stock length product. or\nThe entered length is not valid range for production.' %(length)))
		'''
		
		if(length != 0 and 'customlength' in product_obj.x_prod_cat): #To check custom length and product
			prod_like =product_obj.x_dcs_group
			sql ="SELECT pt.id as prod_id FROM product_template pt, product_product pp WHERE pt.x_stock_length = '" + str(int(length)) + "' AND pt.id = pp.product_tmpl_id AND pt.x_dcs_group = '" + str(prod_like) + "' AND pt.x_prod_cat='stocklength' and pt.x_dcs_itemcode like '%P-1%' "
			cr.execute(sql)
			rows = cr.fetchall()
			if(len(rows) > 0):
				#_logger.error("customlengthcustomlength22["+str(sql)+"]")
				raise osv.except_osv(_('Stock Length!'), _('The length you have entered [%s] already exists as a stock length product.' % (int(length))))
		
		#if product_obj.name: 
		if product_obj and "P-1" in product_obj.name:
			if length<1800 or length>7950:
				raise osv.except_osv(_('Product Length!'), _('Product Length must be between 1800 and 7950.'))'''
				
		#----------------------------------------------------------
		#converting [LM] into [M2]  LM->M2  LMtoM2 LM2M2
		#----------------------------------------------------------
		#rate_src=""
		cost_xtra=0.0
		rate=0.0
		
		if loc_id:
			loc_obj = self.pool.get('stock.warehouse').browse(cr,uid,loc_id,context=context)
			if loc_obj.x_cost_xtra and loc_obj.x_cost_xtra>0:
				cost_xtra = loc_obj.x_cost_xtra
		#@_logger.error("onchange_order_line_dcs.cost_xtracost_xtra["+str(cost_xtra)+"]")
		if payment_term:
			term_obj = term_obj.browse(cr, uid, payment_term)
			code 	 = term_obj.x_payterm_code
			
			#found_rate = False
			if code:	
				if code != "COD" and code!="immediate":
					ac_rate		= True
				#if product_obj.list_price and product_obj.list_price>0.0:
				#	grp_rate=False
				#else:
				if product_obj.x_dcs_group:
					#rate_id = rate_obj.find_rate(cr, uid, partner_id,product_obj.x_dcs_group,product,dt_sale, context=context)
					grp_rate, _rate_cod, _rate_acct=rate_obj.find_rate_group(cr, uid, partner_id, product_obj.x_dcs_group,dt_sale, context=context)
					#_logger.error("find_ratefind_ratebbbbb["+str(grp_rate)+"]["+str(_rate_cod)+"]["+str(_rate_acct)+"]["+str(product_obj.x_dcs_group)+"]")
					if grp_rate == True:
						#grp_rate=True
						if code == "COD" or code=="immediate":#if code == "30EOM":
							rate = _rate_cod
							ac_rate		= False
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
							ac_rate		= False
							#found_rate = True #
						else:	
							rate = rate_obj.rate_acct#+cost_xtra
							#found_rate = True #order_obj.button_dummy()
							ac_rate		= True
		
		result.update({'x_qty_m2': False}) 		
		
		#if found_rate==False:
		#	rate=0.0
		if rate>0.0: #add only if rate is valid
			rate+=cost_xtra
		else:
			grp_rate =False #zero rate means no rate in group rate...so apply product rate /17/4/18
			
		if product_obj.x_is_main=='1':#x_is_calcrate:
			if product_obj.x_m2_factor and product_obj.x_m2_factor>0:
				qty_lm = round((length*qty*0.001*product_obj.x_m2_factor),4) 	#M2 
			else:	
				qty_lm = round(((length*qty*0.001)/3),4) 	#M2 
			#if rate>0:
			#	result.update({'price_unit': rate})	
			result.update({'x_qty_m2': True}) 
			if grp_rate==False and product_obj.list_price and product_obj.list_price>0.0:#do not overwrite if it has rate setup in product level
				if ac_rate and product_obj.x_price_account>0.0:
					result.update({'price_unit': product_obj.x_price_account+cost_xtra})	
				else:
					result.update({'price_unit': product_obj.list_price+cost_xtra})	
			else:
				result.update({'price_unit': rate})	
			
		else:
			
			qty_lm = qty	
			if partner.x_accs_m2convert:
				if product_obj.x_m2_factor and product_obj.x_m2_factor>0:
					qty_lm = round((qty*product_obj.x_m2_factor),4) 	
					if rate>0:
						result.update({'price_unit': rate})
					result.update({'x_qty_m2': True}) 
		
		#_logger.error("product_qty_changedproduct_qty_changed["+str(result)+"]")	
		#result.update({'x_rate_src': rate_src})	
		if 'price_unit' in result and result['price_unit']:
			result.update({'x_rate_readonly': result['price_unit']})
		result.update({'product_uom_qty': qty_lm})
		
		return {'value': result, 'domain': domain, 'warning': warning}
	
	def product_id_change_v2(self, cr, uid, ids, pricelist, product, qty=0,
			uom=False, qty_uos=0, uos=False, name='', partner_id=False,
			lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False,loc_id =False, context=None):
		context = context or {}
		lang = lang or context.get('lang', False)
		if not partner_id:
			raise osv.except_osv(_('No Customer Defined!'), _('Before choosing a product,\n select a customer in the sales form.'))
		warning = False
		product_uom_obj = self.pool.get('product.uom')
		partner_obj = self.pool.get('res.partner')
		product_obj = self.pool.get('product.product')
		context = {'lang': lang, 'partner_id': partner_id}
		partner = partner_obj.browse(cr, uid, partner_id)
		lang = partner.lang
		context_partner = {'lang': lang, 'partner_id': partner_id}
		 
		if not product:
			return {'value': {'th_weight': 0,
			'product_uos_qty': qty}, 'domain': {'product_uom': [],
			'product_uos': []}}
		if not date_order:
			date_order = time.strftime(DEFAULT_SERVER_DATE_FORMAT)

		result = {}
		warning_msgs = ''
		product_obj = product_obj.browse(cr, uid, product, context=context_partner)

		uom2 = False
		if uom:
			uom2 = product_uom_obj.browse(cr, uid, uom)
			if product_obj.uom_id.category_id.id != uom2.category_id.id:
				uom = False
		if uos:
			if product_obj.uos_id:
				uos2 = product_uom_obj.browse(cr, uid, uos)
				if product_obj.uos_id.category_id.id != uos2.category_id.id:
					uos = False
				else:
					uos = False

		fpos = False
		if not fiscal_position:
			fpos = partner.property_account_position or False
		else:
			fpos = self.pool.get('account.fiscal.position').browse(cr, uid, fiscal_position)
		if update_tax: #The quantity only have changed
			result['tax_id'] = self.pool.get('account.fiscal.position').map_tax(cr, uid, fpos, product_obj.taxes_id)

		if not flag:
			result['name'] = self.pool.get('product.product').name_get(cr, uid, [product_obj.id], context=context_partner)[0][1]
			if product_obj.description_sale:
				result['name'] += '\n'+product_obj.description_sale
		domain = {}
		if (not uom) and (not uos):
			result['product_uom'] = product_obj.uom_id.id
			if product_obj.uos_id:
				result['product_uos'] = product_obj.uos_id.id
				result['product_uos_qty'] = qty * product_obj.uos_coeff
				uos_category_id = product_obj.uos_id.category_id.id
			else:
				result['product_uos'] = False
				result['product_uos_qty'] = qty
				uos_category_id = False
			result['th_weight'] = qty * product_obj.weight
			domain = {'product_uom':
					[('category_id', '=', product_obj.uom_id.category_id.id)],
					'product_uos':
					[('category_id', '=', uos_category_id)]}
		elif uos and not uom: # only happens if uom is False
			result['product_uom'] = product_obj.uom_id and product_obj.uom_id.id
			result['product_uom_qty'] = qty_uos / product_obj.uos_coeff
			result['th_weight'] = result['product_uom_qty'] * product_obj.weight
		elif uom: # whether uos is set or not
			default_uom = product_obj.uom_id and product_obj.uom_id.id
			q = product_uom_obj._compute_qty(cr, uid, uom, qty, default_uom)
			if product_obj.uos_id:
				result['product_uos'] = product_obj.uos_id.id
				result['product_uos_qty'] = qty * product_obj.uos_coeff
			else:
				result['product_uos'] = False
				result['product_uos_qty'] = qty
			result['th_weight'] = q * product_obj.weight        # Round the quantity up

		if not uom2:
			uom2 = product_obj.uom_id
        # get unit price
		result.update({'x_order_length': product_obj.x_stock_length})
		
		if not pricelist:
			warn_msg = _('You have to select a pricelist or a customer in the sales form !\n'
			'Please set one before choosing a product.')
			warning_msgs += _("No Pricelist ! : ") + warn_msg +"\n\n"
		else:
			if product_obj.x_is_main=="1":
				result.update({'price_unit': 0.0})
			else:
				price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist],
						product, qty or 1.0, partner_id, {
						'uom': uom or result.get('product_uom'),
						'date': date_order,
						})[pricelist]
				if price is False:
					warn_msg = _("Cannot find a pricelist line matching this product and quantity.\n"
						"You have to change either the product, the quantity or the pricelist.")

					warning_msgs += _("No valid pricelist line found ! :") + warn_msg +"\n\n"
				else:
					result.update({'price_unit': price})
		if warning_msgs:
			warning = {
			'title': _('Configuration Error!'),
			'message' : warning_msgs
			}
		#_logger.error("product_id_change_v2product_id_change_v2["+str(result)+"]")	
		if 'price_unit' in result and result['price_unit']:
			result.update({'x_rate_readonly': result['price_unit']})	
		return {'value': result, 'domain': domain, 'warning': warning}
	
	def _total_lm_calc(self, cr, uid, ids, values, arg, context):
		x={}
		_lm=''
		for record in self.browse(cr, uid, ids):
			if record.product_id.x_prod_cat in ['customlength','stocklength']:
				_qty=record.x_order_qty
				_len=record.x_order_length
				_lm=_qty*_len*0.001
			else:
				_lm=''
			x[record.id] = _lm 
		return x
		
	def _rate_readonly(self, cr, uid, ids, values, arg, context):
		x={}
		for record in self.browse(cr, uid, ids):
			x[record.id]=record.price_unit 
		return x
		
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
		
	_columns = {
		'x_order_length':fields.float("Ordered Len",digits_compute= dp.get_precision('Int Number')),	
		'x_order_qty':fields.float("Ordered Qty",digits_compute= dp.get_precision('Int Number')),	
		'x_total_lm': fields.function(_total_lm_calc, method=True, string='L/M', type='float'),
		'x_rate_readonly': fields.function(_rate_readonly, method=True, string='Rate',type='float'),
		'x_rate_src':fields.char("Rate Source"),	
		'x_qty_m2':fields.boolean("m2 rate?"),
		'x_region_id': fields.many2one('dincelaccount.region', 'A/c Region'),
		'x_coststate_id':fields.many2one("res.country.state","Cost Centre"),
		'x_edit_rate': fields.function(_edit_rate, method=True, string='Edit Rate',type='boolean'),
	}	
	#_sql_constraints = [ 
	#	('product_length_uniq', 'unique (order_id,product_id,x_order_length)', 'Duplicate product found in order line item !!')
	#	]
	_defaults = {
		'x_order_qty': 1
	}	
	
	#def _get_default_currency(self, cr, uid, context=None):
	#	res = self.pool.get('res.company').search(cr, uid, [('currency_id','=','EUR')], context=context)
	#return res and res[0] or False
#---------------------------------------------------------------------------------------------	
#For revisoin of the sales order......14/10/2016
#Conditions.......	
#	1.Rate change due to COD to A/C or Discount Allowed
#	2.Panel Qty changed by customers
#	3.Delivery added from Pickup option or vice versa
#---------------------------------------------------------------------------------------------
class dincelaccount_sale_order_line_new(osv.Model):
	_name="sale.order.line.new"
	_columns = {
		'order_id': fields.many2one('sale.order', 'Sale Order'),
		'product_id': fields.many2one('product.product', 'Product'),
		'name': fields.char('Name',size=64),
		'order_length':fields.float("Ordered Len"),	
		'order_qty':fields.float("Ordered Qty"),	
		'product_uom': fields.many2one('product.uom', 'Unit of Measure'),
		'region_id': fields.many2one('dincelaccount.region', 'A/c Region'),
		'coststate_id':fields.many2one("res.country.state","Cost Centre"),
		'price_unit':fields.float("Unit Price"),	
		'tax_id': fields.many2one('account.tax', 'Tax'),
	}	
#not in use	
'''
class dincelaccount_sale_order_line_old(osv.Model):
	_name="sale.order.line.old"
	_columns = {
		'name': fields.char('Name',size=64),
	}
'''	
#not in use	
'''	
class dincelaccount_journal_dcstest(osv.Model):
	_name="dincelaccount.journal.dcstest"
	_columns = {
		'name': fields.char('Name',size=64),
	}	
'''	
#-------------------------------------------------------------
#--- used for sale order revise only...not use same table, cause of search criteria.., dropdown, etc...	
#-------------------------------------------------------------
class dincelaccount_sale_order_bak(osv.Model):
	_name="sale.order.bak"	
	_inherit = ['mail.thread']
	_description = "Sales Order Revise"
	
	def _amount_wrapper(self, cr, uid, ids, field_name, arg, context=None):
		res = {}
		_total=0.0
		#_logger.error("updatelink_order_dcs._amount_untaxed_amount_untaxed0000["+str(_total)+"]")	
		for record in self.browse(cr, uid, ids):
			res[record.id] = {
				'amount_untaxed': 0.0,
				'amount_tax': 0.0,
				'amount_total': 0.0,
			}
			for line in record.item_lines:
				price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
				_total=_total+(price*line.product_uom_qty)
				#_logger.error("updatelink_order_dcs._amount_untaxed_amount_untaxed["+str(_total)+"]")	
			#x[record.id] = _total 
			res[record.id]['amount_tax'] = _total*0.1
			res[record.id]['amount_untaxed'] = _total
			res[record.id]['amount_total'] = res[record.id]['amount_untaxed'] + res[record.id]['amount_tax']
		return res
	'''
	def _amount_tax(self, cr, uid, ids, values, arg, context):
		x={}
		_total=0
		for record in self.browse(cr, uid, ids):
			for line in record.item_lines:
				price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
				_total= _total+(price*line.product_uom_qty)
		x[record.id] = _total*0.1 
		return x
	
	def _amount_total(self, cr, uid, ids, values, arg, context):
		x={}
		_total=0
		for record in self.browse(cr, uid, ids):
			for line in record.item_lines:
				price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
				_total= _total+(price*line.product_uom_qty)
		x[record.id] = _total*1.1
		return x'''
		
	_columns = {
		'name': fields.char('Name',size=64),
		'date_order': fields.datetime('Date'),
		'origin_id':fields.many2one('sale.order', 'Origin OrderId'),
		'partner_id': fields.many2one('res.partner', 'Customer'),
		'user_id': fields.many2one('res.users', 'Salesperson'),
		'region_id': fields.many2one('dincelaccount.region', 'A/c Region'),
		'item_lines':fields.one2many('sale.order.bak.line', 'order_bak_id', 'Invoies'),
		'payment_term': fields.many2one('account.payment.term', 'Payment Term'),
		'project_id': fields.many2one('res.partner','Project / Site'),		
		'contact_id': fields.many2one('res.partner','Contact Person'),		
		'quote_id': fields.many2one('account.analytic.account','Quote'),		
		'warehouse_id': fields.many2one('stock.warehouse','Dispatch Location'),		
		'street': fields.char('Street'),	
		'postcode': fields.char('Postcode'),	
		'suburb': fields.char('Suburb'),	
		'state_id': fields.many2one('res.country.state','State'),		
		'country_id': fields.many2one('res.country','Country'),
		'deposit_exmpt': fields.boolean('Deposit Exempt'),
		'revise_sn': fields.integer('Revise SN', size=2),	
		'pudel':fields.selection([
			('pu','Pickup'),
			('del','Delivery'),
			], 'Pickup/Delivery'),
		'ac_status':fields.selection([
			('hold','Hold'),
			('open','Open'),
			('part','Partial'),
			('paid','Paid'),
			], 'A/c Status'),	
		'prod_status':fields.selection([
			('queue','Queue'),
			('part','Partial'),
			('complete','Complete'),
			], 'Production Status'),		
		'del_status':fields.selection([
			('none','None'),
			('part','Partial'),
			('delivered','Delivered'),
			], 'Delivery Status'),		
		'status':fields.selection([ #as in dcs open /close/ cancel
			('open','Open'),
			('close','Closed'),
			('cancel','Cancelled'),
			], 'Status'),	
		'revise_type':fields.selection([ #>>as revise type
			('shipment','Shipment'),
			('rate','Price changed'),
			('order','Qty changed'),
			('other','Other'),
			], 'Revise type'),	
		'dt_request':fields.date("Requested Date"),		
		'dt_process': fields.datetime("Order Entry Date"),
		'note': fields.text('Note'),
		'pricelist_id': fields.many2one('product.pricelist', 'Pricelist'), 
		'currency_id': fields.related('pricelist_id', 'currency_id', type="many2one", relation="res.currency", string="Currency", readonly=True),
		'amount_untaxed':fields.function(_amount_wrapper, digits_compute=dp.get_precision('Account'), string='Untaxed Amount',multi='sums',store=True),
		'amount_tax':fields.function(_amount_wrapper, digits_compute=dp.get_precision('Account'), string='Taxes',multi='sums',store=True),
		'amount_total':fields.function(_amount_wrapper, digits_compute=dp.get_precision('Account'), string='Total Amount',multi='sums',store=True),
	}	
	
class dincelaccount_sale_order_bak_line(osv.Model):
	_name="sale.order.bak.line"
	def _amount_line(self, cr, uid, ids, field_name, arg, context=None):
		tax_obj = self.pool.get('account.tax')
		cur_obj = self.pool.get('res.currency')
		res = {}
		if context is None:
			context = {}
		for line in self.browse(cr, uid, ids, context=context):
			price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
			_total= price*line.product_uom_qty
			#taxes = tax_obj.compute_all(cr, uid, line.tax_id, price, line.product_uom_qty, line.product_id, line.order_bak_id.partner_id)
			#_logger.error("dincelaccount_sale_order_bak_line["+str(price)+"]["+str(taxes)+"]")
			#cur = line.order_bak_id.pricelist_id.currency_id
			res[line.id] = _total#;cur_obj.round(cr, uid, cur, taxes['total'])
		return res

	_columns = {
		'order_bak_id': fields.many2one('sale.order.bak', 'Back Order'),
		'sequence': fields.integer('Sequence'),
		'product_id': fields.many2one('product.product', 'Product'),
		'name': fields.char('Name',size=64),
		'order_length':fields.float("Ordered Len"),	
		'order_qty':fields.float("Ordered Qty"),	
		'product_uom': fields.many2one('product.uom', 'Unit of Measure'),
		'product_uom_qty': fields.float('Quantity'),
		'region_id': fields.many2one('dincelaccount.region', 'A/c Region'),
		'price_unit':fields.float("Unit Price"),	
		'tax_id': fields.many2one('account.tax', 'Tax'),
		'price_subtotal': fields.function(_amount_line, string='Subtotal', digits_compute= dp.get_precision('Account')),
		'discount': fields.float('Discount (%)'),
	}	
	_defaults = {
		'discount': 0.0,
		'price_unit': 0.0,
	}

	
class accountmail_compose_message(osv.Model):
	_inherit = 'mail.compose.message'
	
	#@api.multi #res = super(dincelreport_res_partner, self).write(cr, uid, ids, vals, context=context)
	def send_mail(self, cr, uid, ids, context=None):
		#context = self._context
		#_logger.error("accountmail_compose_messageaccountmail_compose_message111["+str(context)+"]")
		if context.get('default_model') == 'sale.order' and context.get('mark_as_sent'):
			if context.get('default_inv_ids'):
				for _id in context.get('default_inv_ids'):
					#invoice = self.pool.get('account.invoice').browse(_id)
					#invoice=self.pool.get('account.invoice').browse(cr, uid, _id, context)
					#invoice = invoice.with_context(mail_post_autofollow=True)
					self.pool.get('account.invoice').write(cr, uid, _id, {'sent': True})
					#invoice.message_post(body=_("Invoice sent"))
			if context.get('default_res_id'):
				_id=context.get('default_res_id')
				#order =self.pool.get('sale.order').browse(cr, uid, _id, context)#= self.env['sale.order'].browse(_id)
				self.pool.get('sale.order').write(cr, uid, _id, {'x_sent': True,'state':'sent'}) #email_obj.cr, uid, template_id, {'attachment_ids': [(6, 0, _atths)]})  
		return super(accountmail_compose_message, self).send_mail(cr, uid, ids, context=context)
		
class dincelaccount_saleorder_approve(osv.Model):
	_name="dincelsale.order.approve"	
	_inherit = ['mail.thread']
	_description = "Order Approval"
	_order = "id desc"
	def _total_custom_lm(self, cr, uid, ids, field_name, arg, context=None):
		
		res = {}
		if context is None:
			context = {}
		_total=0.0	
		for record in self.browse(cr, uid, ids, context=context):
			for item in record.order_id.order_line:
				if item.product_id.x_prod_cat =='customlength':
					_length = item.x_order_length
					_qty	= item.x_order_qty 
					_total += _qty*_length*0.001
			res[record.id] = _total
		return res
		
	_columns = {
		'name': fields.char('Name',size=64),
		'date': fields.datetime('Date'),
		'order_id':fields.many2one('sale.order', 'Sale Order'),
		'invoice_id':fields.many2one('account.invoice', 'Invoice'),
		'partner_id': fields.related('order_id', 'partner_id',  string='Partner', type="many2one", relation="res.partner",store=False),
		'project_id': fields.related('order_id', 'x_project_id',  string='Project/Site', type="many2one", relation="res.partner",store=False),
		'request_uid': fields.many2one('res.users', 'Requested By'),
		'approve_uid': fields.many2one('res.users', 'Approved By'),
		'request_text': fields.char('Request Reason'),	
		'comments': fields.char('Comments'),	#, track_visibility='onchange'
		'total_custom': fields.function(_total_custom_lm, string='Total Custom LM'),
		'type':fields.selection([
			('cancel','Cancellation'),
			('discount','Discount'),
			('credit','Credit/Others'),
			('refund','Refund'),
			('mrp','MRP'),
			], 'Type'),
		'subtype':fields.selection([ #as in dcs open /reject/ approve
			('order','Order'),
			('invoice','Invoice'),
			], 'Sub Type'),	
		'state':fields.selection([ #as in dcs open /reject/ approve
			('open','Open'),
			('approve','Approved'),
			('reject','Rejected'),
			], 'Status'),	#, track_visibility='onchange'
		
	}	
	
	_defaults = {
		'date_request': fields.datetime.now,
		'state': 'open',
		'subtype': 'order',
		}
	def save_approval_btn(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		for record in self.browse(cr, uid, ids, context=context):		
			_id=record.id
			subj_part=""
			if record.order_id:
				_orderid=record.order_id.id 
				subj_part="[%s]" % (record.order_id.name)
			else:
				_orderid=None
			_type=record.type
			if record.invoice_id:
				_invid=record.invoice_id.id 
			else:
				_invid=False
			lids4=[]
			#_config_id = self.pool.get('dincelaccount.config.settings').search(cr,uid,[('id', '>', '0')], limit=1)
			#if _config_id:
			#	_conf= self.pool.get('dincelaccount.config.settings').browse(cr, uid, _config_id, context=context)
			#	if _conf and _conf.authorise_cc:
			#		lids4.append(_conf.authorise_cc.id)
			
			value = {
				'view_type': 'form',
				'view_mode': 'form',
				'res_model': 'saleorder.approve.request',
				#'res_id': _id,
				'type': 'ir.actions.act_window',
				'name' : _('Approval request'),
				'context':{
						'default_order_id': _orderid, 
						'default_invoice_id': _invid, 
						'default_user_id': uid, 
						'default_type': _type,
						'default_subtype': record.subtype,
						'default_approve_flag':True,	
						#'default_approve_pending':_pending,	
						'default_request_id':_id,
						'default_subject':'Re approval request ' + (subj_part),
						'default_partner_ids':lids4,
				},
				'target': 'new',
			}
			return value	
		