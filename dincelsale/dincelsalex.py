from openerp.osv import osv, fields
from datetime import date
from datetime import datetime
import datetime
from datetime import timedelta
import time 
#from datetime import datetime, timedelta
from pytz import timezone
import pytz
#from datetime import date
#from openerp.addons.base_status.base_state import base_state
#import time 
#import datetime
#from datetime import date
#from datetime import datetime
#import datetime
#from datetime import timedelta
import logging
from openerp.tools.translate import _

from time import gmtime, strftime
_logger = logging.getLogger(__name__)

class dincelsale_ordersale(osv.Model):
	_name = "dincelsale.ordersale"

	def _get_default_company(self, cr, uid, context=None):
		company_id = self.pool.get('res.users')._get_company(cr, uid, context=context)
		if not company_id:
			raise osv.except_osv(_('Error!'), _('There is no default company for the current user!'))
		return company_id
	def get_salenote(self, cr, uid, ids, partner_id, context=None):
		context_lang = context.copy() 
		if partner_id:
			partner_lang = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context).lang
			context_lang.update({'lang': partner_lang})
		return self.pool.get('res.users').browse(cr, uid, uid, context=context_lang).company_id.sale_note

	def onchange_partner_id(self, cr, uid, ids, partner_id, project_id, is_contact, context=None):
		#if not partner_id:
		#	return {'value': { 'payment_term': False}}
		val = {}
		domain={}
		order = self.pool.get('sale.order')
		if partner_id:
			part = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context)
			payment_term = part.property_payment_term and part.property_payment_term.id or False
			dedicated_salesman = part.user_id and part.user_id.id or uid
			val['payment_term']=payment_term
			val['user_id']=dedicated_salesman
			c_ids1 = order.search(cr, uid, [('partner_id', '=', partner_id)], context=context)
			domain  = {'order_id': [('id','in', (c_ids1))]}
			
			if is_contact==True:
				domain  = {'order_id': [('id','in', (c_ids1))]}
				
		if project_id:
			c_ids1 = order.search(cr, uid, [('x_project_id', '=', project_id)], context=context)
			domain  = {'order_id': [('id','in', (c_ids1))]}
			
		#	return {'domain': domain}
		#sale_note = self.get_salenote(cr, uid, ids, part.id, context=context)
		#if sale_note: val.update({'note': sale_note})  
		return {'value': val,'domain': domain}
		
	_columns = {
		'name': fields.char('Order Reference'),
		'origin': fields.char('Source Document', help="Reference of the document that generated this sales order request."),
		'state': fields.selection([
			('draft', 'Draft'),
			('cancel', 'Cancelled'),
			('progress', 'Pending'),
			('done', 'Done'),
			], 'Status'),
		'date_order': fields.datetime('Date', required=True),
		'user_id': fields.many2one('res.users', 'Salesperson'),
		'origin_id': fields.many2one('sale.order', 'Origin Order'),
		'partner_id': fields.many2one('res.partner', 'Customer', domain=[('customer', '=', True),('x_is_project', '=', False)]),
		'project_id': fields.many2one('res.partner', 'Project', domain=[('x_is_project', '=', True)]),
		'order_line': fields.one2many('dincelsale.order.line', 'order_id', 'Order Lines'),
		'note': fields.text('Note'),
		'payment_term': fields.many2one('account.payment.term', 'Payment Term'),
		'company_id': fields.many2one('res.company', 'Company'),
	}	
	
	_defaults = {
		'date_order': fields.datetime.now,
		'company_id': _get_default_company,
		'state': 'draft',
		'user_id': lambda obj, cr, uid, context: uid,
		'name': lambda obj, cr, uid, context: '/',
		'note': lambda self, cr, uid, context: self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.sale_note,
	}
	_sql_constraints = [
		('name_uniq', 'unique(name, company_id)', 'Order Reference must be unique per Company!'),
		]
	
	def create(self, cr, uid, vals, context=None):
		if context is None:
			context = {}
		if vals.get('name', '/') == '/':
			vals['name'] = self.pool.get('ir.sequence').get(cr, uid, 'dincelsale.order') or '/'

		new_id = super(dincelsale_ordersale, self).create(cr, uid, vals, context=context)
		
		return new_id
	#(date_order,partner_id,payment_term,context)
	'''def create_test(self, cr, uid, ids, context=None):
		str1 = ""
		for record in self.browse(cr, uid, ids, context=context):
			for line in record.order_line:
				id1 = line.product_id.id
				str1 += "product_id [" + str(id1) + "]"
				if line.product_id.x_is_main == '1':
					qty 	= line.order_qty
					str1 += "x_is_main [" + str(qty) + "]"
				else:
					price	= line.product_id.list_price
					qty 	= line.order_qty
					str1 += "[" + str(qty) + "][" + str(price) + "]"
		_logger.error("invoice_sales_validate:["+str1+"]")	
	'''	
	def create_sales_order(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		order_obj 	= self.pool.get('sale.order')
		obj_line 	= self.pool.get('sale.order.line')
		rate_obj 	= self.pool.get('dincelcrm.customer.rate')
		term_obj 	= self.pool.get('account.payment.term')
	 
		price_unit		= None
		order_id 		= None 
		payment_term 	= None
		term_code 		= None		

		dt_sale 	= datetime.datetime.now() 	#None
		partner_id 	= None
		sname		= ""
		
		pricelist 	= False
		order_line 	= False
		for record in self.browse(cr, uid, ids, context=context):
			if record.payment_term:
				payment_term = record.payment_term.id
				term_code 	 = record.payment_term.x_payterm_code
			
			company_id 	= record.company_id.id
			user_id		= record.user_id.id
			dt_sale		= record.date_order
			
			sname		= record.name
			order_line	= record.order_line
			if record.partner_id:
				partner_id	= record.partner_id.id
				pricelist 	= record.partner_id.property_product_pricelist and record.partner_id.property_product_pricelist.id or False

		
		if term_code:	
			rate_id = rate_obj.find(cr, uid, dt_sale, partner_id, context=context)
			if rate_id:
				rate_id	 = rate_id[0]
				rate_obj =  rate_obj.browse(cr, uid, rate_id)
				if term_code == "30EOM":
					price_unit = rate_obj.rate_acct
				elif term_code == "COD":
					price_unit = rate_obj.rate_cod
	
		if order_line:	
			sale_id 	= self.pool.get('ir.sequence').get(cr, uid, 'sale.order')
			
			if not sale_id or sale_id=='':
				sale_id = "SO" + sname
			vals = {		
				'origin':sname,
				'date_order': dt_sale,
				'partner_id':partner_id,
				'payment_term':payment_term,
				'name':sale_id,
				'state': 'draft',
				'user_id':user_id,
				'order_policy':'manual',
				'picking_policy':'direct',
				'x_origin_order':ids[0], #current id
				}
			if pricelist:
				vals['pricelist_id'] = pricelist	
				
			order_id =   order_obj.create(cr, uid, vals, context=context)
			
			for line in order_line:
				if line.product_id.x_is_main == '1':
					qty = line.order_length*line.order_qty*0.001 	#LM 
					if price_unit:
						price 	= price_unit
					else:	
						price	= line.product_id.list_price
					#order_length= line.order_length	
				else:
					price	= line.product_id.list_price
					qty 	= line.order_qty
					#order_length= 0
				vals = {		
					'product_id': line.product_id.id,
					'product_uos_qty': qty,
					'product_uom_qty': qty,
					'price_unit': price,
					'name': line.product_id.name,
					'x_order_qty': line.order_qty,
					'x_order_length':line.order_length,#order_length,
					'state': 'draft',
					'company_id': company_id,
					'order_partner_id':partner_id,
					'order_id':order_id,
					'salesman_id':user_id,
				}

				line_id = obj_line.create(cr, uid, vals, context=context)
		if order_id:
			self.write(cr, uid, ids, {'state': 'done'})
			
			view_id 		= self.pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'dincelaccount.sale.order.form')], limit=1) 	

			value = {
				'domain': str([('id', 'in', order_id)]),
				'view_type': 'form',
				'view_mode': 'form',
				'res_model': 'sale.order',
				'view_id': view_id,
				'type': 'ir.actions.act_window',
				'name' : _('Sale Order'),
				'res_id': order_id
			}
			return value	
		if not partner_id or not order_line:
			raise osv.except_osv(_('No Customer Defined!'), _('No customer defined or no order line found!'))
		#return order_id

					
class dincelsale_ordersale_line(osv.Model):
	_name 	= "dincelsale.order.line"
	_order 	= "sequence"
	
	def product_id_change(self, cr, uid, ids, product,  partner_id=False, context=None):
		context = context or {}
		if not partner_id:
			raise osv.except_osv(_('No Customer Defined!'), _('Before choosing a product,\n select a customer in the sales form.'))
			#return {}
		warning = False
		domain = {}
		product_obj = self.pool.get('product.product')
		result = {}
		product_obj = product_obj.browse(cr, uid, product, context=context)
		if not product_obj.description_sale:
			sname=product_obj.name
		else:
			sname=product_obj.description_sale
		result.update({'name': sname})
		result.update({'order_length': product_obj.x_stock_length})
		return {'value': result, 'domain': domain}
		#product_obj = product_obj.browse(cr, uid, product, context=context)
		#result['name'] = product_obj.description_sale
		#result['order_length'] = product_obj.x_stock_length
        
		
		
	_columns = {
		'order_id': fields.many2one('dincelsale.ordersale', 'Order Reference', required=True, ondelete='cascade', select=True),
		'name': fields.text('Description', required=True),
		'sequence': fields.integer('Sequence'),
		'product_id': fields.many2one('product.product', 'Product', ondelete='restrict'),
		'order_length':fields.float("Stock Length"),	
		'order_qty':fields.float("Quantity"),	
	}	


class dincelsale_productsummary(osv.Model):	
	_name = "dincelsale.productsummary"
	
	def _get_completed_lm(self, cr, uid, ids, _prod, context=None):
		sql2="select sum(m.x_produced_qty*m.x_order_length*0.001) as tot from sale_order o,mrp_production m,product_product p,product_template t"
		sql2+=" where o.id=m.x_sale_order_id and m.product_id=p.id and p.product_tmpl_id=t.id and t.x_prod_cat='customlength'"
		sql2+=" and (o.x_dep_paid='NA' or o.x_dep_paid='paid')"
		sql2+=" and o.state not in ('cancel','done') and o.x_pending='f'"
		sql2+=" and t.x_dcs_group='%s'" % (_prod)
		cr.execute(sql2)
	
		rows 	= cr.fetchone()
		if rows and len(rows) > 0 and rows[0]:
			return rows[0]
		return 0
		
	def _get_remain_lm(self, cr, uid, ids, _prod, context=None):
		_ret='' 
		#sql="select id from sale_order where state not in ('cancel','done') and x_pending='f'"
		#sql+=" and (x_dep_paid='NA' or x_dep_paid='paid')"
		sql2="select sum(l.x_order_qty*l.x_order_length*0.001) as tot	from sale_order o,sale_order_line l,product_product p,product_template t"
		sql2+=" where o.id=l.order_id and l.product_id=p.id and p.product_tmpl_id=t.id and t.x_prod_cat='customlength'"
		sql2+=" and (o.x_dep_paid='NA' or o.x_dep_paid='paid')"
		sql2+=" and o.state not in ('cancel','done') and o.x_pending='f'"
		sql2+=" and t.x_dcs_group='%s'" % (_prod)
		cr.execute(sql2)
	
		rows 	= cr.fetchone()
		if rows and len(rows) > 0 and rows[0]:
			_ret = rows[0]
			_completed=self._get_completed_lm(cr, uid, ids, _prod, context=context)
			if _completed:
				_ret=float(_ret)-float(_completed)
		else:	
			_ret = '0'
		return _ret
	
	def _get_hold_lm(self, cr, uid, ids, _prod, context=None):
		_ret='' 
		#sql="select id from sale_order where state not in ('cancel','done') and x_pending='f'"
		#sql+=" and (x_dep_paid='NA' or x_dep_paid='paid')"
		sql2="select sum(l.x_order_qty*l.x_order_length*0.001) as tot	from sale_order o,sale_order_line l,product_product p,product_template t"
		sql2+=" where o.id=l.order_id and l.product_id=p.id and p.product_tmpl_id=t.id and t.x_prod_cat='customlength'"
		sql2+=" and (o.x_dep_paid='' or o.x_dep_paid is null)"
		sql2+=" and o.state not in ('cancel','done') and o.x_pending='f'"
		sql2+=" and t.x_dcs_group='%s'" % (_prod)
		cr.execute(sql2)
	
		rows 	= cr.fetchone()
		if rows and len(rows) > 0 and rows[0]:
			_ret = rows[0]
			#_completed=self._get_completed_lm(cr, uid, ids, _prod, context=context)
			#if _completed:
			#	_ret=float(_ret)-float(_completed)
		else:	
			_ret = '0'
		return _ret
		
	def _remain_lm(self, cr, uid, ids, values, arg, context):
		x={}
		_ret=''
		for record in self.browse(cr, uid, ids):
			if record.code=="P155" or record.code=="P110" or record.code=="P200" or record.code=="P275":
				_ret=self._get_remain_lm(cr, uid, ids, record.code, context=context)
				_ret=round(_ret,2)
				#_ret="{:,}".format(_ret)
				'''elif record.code=="P110":
					_ret=self._get_remain_lm(cr, uid, ids, record.code, context=context)
					_ret=round(_ret,2)
				elif record.code=="P200":
					_ret=self._get_remain_lm(cr, uid, ids, record.code, context=context)
					_ret=round(_ret,2)
				elif record.code=="P275":
					_ret=self._get_remain_lm(cr, uid, ids, record.code, context=context)
					_ret=round(_ret,2)'''
			else:
				_ret=''
			x[record.id]=_ret 	
		return x
	
	def _hold_hrs(self, cr, uid, ids, values, arg, context):
		x={}
		_ret=''
		for record in self.browse(cr, uid, ids):
			if not record.produce_speed or record.produce_speed==0:
				_speed=1.0
			else:
				_speed=record.produce_speed
			if record.code=="P155" or record.code=="P110" or record.code=="P200" or record.code=="P275":
				_ret=self._get_hold_lm(cr, uid, ids, record.code, context=context)
				_ret=float(_ret)/(_speed*60) 
				_ret=round(_ret,2)
				#_ret="{:,}".format(_ret)
				
			else:
				_ret=''
			x[record.id]=_ret 	
		return x
		
	def _remain_hrs(self, cr, uid, ids, values, arg, context):
		x={}
		_ret=''
		for record in self.browse(cr, uid, ids):
			if not record.produce_speed or record.produce_speed==0:
				_speed=1.0
			else:
				_speed=record.produce_speed
			if record.code=="P155" or record.code=="P110" or record.code=="P200" or record.code=="P275":
				_ret=self._get_remain_lm(cr, uid, ids, record.code, context=context)
				_ret=float(_ret)/(_speed*60) 
				_ret=round(_ret,2)
				#_ret="{:,}".format(_ret)
				'''elif record.code=="P110":
					_ret=self._get_remain_lm(cr, uid, ids, record.code, context=context)
					_ret=float(_ret)/(_speed*60) 
					_ret=round(_ret,2)
					_ret="{:,}".format(_ret)
				elif record.code=="P200":
					_ret=self._get_remain_lm(cr, uid, ids, record.code, context=context)
					_ret=float(_ret)/(_speed*60) 
					_ret=round(_ret,2)
					_ret="{:,}".format(_ret)
				elif record.code=="P275":
					_ret=self._get_remain_lm(cr, uid, ids, record.code, context=context)
					_ret=float(_ret)/(_speed*60) 
					_ret=round(_ret,2)
					_ret="{:,}".format(_ret)'''
			else:
				_ret=''
			x[record.id]=_ret 	
		return x
		
	def _hold_lm(self, cr, uid, ids, values, arg, context):
		x={}
		_ret=''
		for record in self.browse(cr, uid, ids):
			if record.code=="P155" or  record.code=="P110" or  record.code=="P200" or  record.code=="P275":
				_ret=self._get_hold_lm(cr, uid, ids, record.code, context=context)
				_ret=round(float(_ret),2)
				#_ret="{:,}".format(_ret)
				'''elif record.code=="P110":
					_ret=self._get_hold_lm(cr, uid, ids, record.code, context=context)
					_ret=round(float(_ret),2)
					_ret="{:,}".format(_ret)
				elif record.code=="P200":
					_ret=self._get_hold_lm(cr, uid, ids, record.code, context=context)
					_ret=round(float(_ret),2)
					_ret="{:,}".format(_ret)
				elif record.code=="P275":
					_ret=self._get_hold_lm(cr, uid, ids, record.code, context=context)
					_ret=round(float(_ret),2)
					_ret="{:,}".format(_ret)'''
			else:
				_ret=''
			x[record.id]=_ret 	
		return x	
		
	def _truck_count1(self, cr, uid, ids, values, arg, context):
		x={}
		_ret=''
		for record in self.browse(cr, uid, ids):
			if record.type=="delivery":
				dtfrom=datetime.datetime.now()
				dtfrom2=dtfrom+ timedelta(hours=10) #for gmt to au date (+10) hrs
				_from_date 	=  datetime.datetime.strptime(str(dtfrom2),"%Y-%m-%d %H:%M:%S.%f")
				#todo....get gmt to local time with timezone logic
				
				#_logger.error("_truck_count1_truck_count1:dtfrom2[" + str(_from_date)+ "][" + str(dtfrom)+ "]")
				#currtime=time.localtime()
				#_from_date 	=  datetime.datetime.strptime(str(dtfrom2),"%Y-%m-%d %H:%M:%S.%f")
				#time_zone	='Australia/Sydney'
				#tz 			= pytz.timezone(time_zone)
				#tzoffset 	= tz.utcoffset(_from_date)
				_dt_today 	= str((_from_date).strftime("%Y-%m-%d"))
				#_logger.error("_truck_count1_truck_count1:2day %s , wtime %s, currtime %s [%s]" % (_dt_today,_from_date,dtfrom,currtime))
				sql="select sum(dockets) from dincelwarehouse_sale_order_delivery where date_actual='%s'" % (_dt_today)
				cr.execute(sql)
				#_logger.error("_truck_count1_truck_count1_truck_count1:sqlsql[" + str(sql)+ "]")
				rows 	= cr.fetchone()
				if rows and len(rows) > 0 and rows[0]:
					_ret = rows[0]
				else:	
					_ret = '0'
			else:
				_ret=''
				#dtquote 	= str((_from_date + tzoffset).strftime("%Y-%m-%d"))
			x[record.id]=_ret 	
		return x
		
	def _truck_count2(self, cr, uid, ids, values, arg, context):
		x={}
		_ret=''
		for record in self.browse(cr, uid, ids):
			if record.type=="delivery":
				dtfrom=datetime.datetime.now()
				#todo....get gmt to local time with timezone logic
				dtfrom2=dtfrom+ timedelta(hours=10) #for gmt to au date (+10) hrs
				dtfrom2=dtfrom2+ timedelta(days=1) #
				_from_date 	=  datetime.datetime.strptime(str(dtfrom2),"%Y-%m-%d %H:%M:%S.%f")
				
				
				
				_dt 	= str((_from_date).strftime("%Y-%m-%d"))
				#_logger.error("_truck_count1_truck_count1:2maro %s , wtime %s, currtime %s []" % (_dt,_from_date,dtfrom))
				sql="select sum(dockets) from dincelwarehouse_sale_order_delivery where date_actual='%s'" % (_dt)
				cr.execute(sql)
				#_logger.error("_truck_count1_truck_count1_truck_count122222:sqlsql[" + str(sql)+ "]")
				rows 	= cr.fetchone()
				if rows and len(rows) > 0 and rows[0]:
					_ret = rows[0]
				else:	
					_ret = '0'
			else:
				_ret=''		
			x[record.id]=_ret 	
		return x	
		
	_columns = {	
		'name':fields.char("Name"),
		'code':fields.char("Code"),
		'produce_speed':fields.float("Production Speed"),
		'type':fields.selection([
			('product', 'Product'),
			('delivery', 'Delivery'),
			], 'Type'),
		'remain_lm':fields.float("Remain L/M"),
		'remain_hrs':fields.float("Remain Hrs"),
		'hold_lm':fields.float("Hold L/M"),	
		'hold_hrs':fields.float("Hold Hrs"),
		'x_remain_lm':fields.function(_remain_lm, method=True, string='Remain L/M',type='float'),
		'x_remain_hrs':fields.function(_remain_hrs, method=True, string='Remain Hrs',type='float'),
		'x_hold_lm':fields.function(_hold_lm, method=True, string='Hold L/M',type='float'),
		'x_hold_hrs':fields.function(_hold_hrs, method=True, string='Hold Hrs',type='float'),
		'truck1':fields.function(_truck_count1, method=True, string='Trucks Today',type='char'),
		'truck2':fields.function(_truck_count2, method=True, string='Tomorrow',type='char'),
	}
	 	