from openerp.osv import osv, fields
from datetime import date
#from openerp.addons.base_status.base_state import base_state
import time 
import datetime
import logging
from openerp.tools.translate import _

from time import gmtime, strftime
_logger = logging.getLogger(__name__)

class dincelaccount_move_line(osv.Model):
	_inherit = "account.move.line" 
	_columns = {
		'x_region_id': fields.many2one('dincelaccount.region', 'A/c Region'),
		'x_coststate_id':fields.many2one("res.country.state","Cost Centre"),
	}
class dincelaccount_move(osv.Model):
	_inherit = "account.move" 
	_columns = {
		'x_region_id': fields.many2one('dincelaccount.region', 'A/c Region'),
		'x_coststate_id':fields.many2one("res.country.state","Cost Centre"),
	}
	
class dincelaccount_journal_dcs(osv.Model):
	_name= "dincelaccount.journal.dcs"
	quantity		= 1
	move_name		= ""
	credit			= 0
	debit			= 0
	account_id		= None
	company_id		= None
	ref_name 		= ""
	state_move		= ""
	date_move 		= None
	period_id 		= 0
	move_line_name  = ""
	state_line		= ""
	move_id			= 0
	partner_id		= 0
	journal_id		= 0
	'''
	def __init__(self, cr, uid, ids, context=None):
		self.cr 	 = cr
		self.uid 	 = uid
		self.ids 	 = ids
		self.context = context
	'''	
	def insert_move(self, cr, uid, ids, context=None):
		_oacct		= self.pool.get('account.move')
		vals={
			'ref':self.ref_name,#origin+"_"+str(pick_id),	
			'state':self.state_move,
			'journal_id':self.journal_id,
			'name':self.move_name,
			'company_id':self.company_id,
			'date':self.date_move,
			'period_id':self.period_id,
			'partner_id':self.partner_id,
		}
		
		return _oacct.create(cr, uid, vals, context=context)
		#return _id
	def insert_move_line(self, cr, uid, ids, context=None):
		_oacctline 	= self.pool.get('account.move.line')
		vals={
			'move_id':self.move_id,	
			'state':self.state_line,
			'journal_id':self.journal_id,
			'name':self.move_line_name,
			'company_id':self.company_id,
			'date':self.date_move,
			'period_id':self.period_id,
			'partner_id':self.partner_id,
			'account_id':self.account_id,
			'credit':self.credit,
			'debit':self.debit,
			'quantity':self.quantity,
		}
		
		return _oacctline.create(cr, uid, vals, context=context)
	
	
	
	#Close - Manufacturing Order
	def mo_produced_qty_journal_dcs(self, cr, uid, ids, mo_id, qty, context=None):
		_mo 		= self.pool.get('mrp.production')
		_obj  		= _mo.browse(cr, uid, mo_id, context=context)
		
		_operiod 	= self.pool.get('account.period') 
		_oprod 		= self.pool.get('product.product')
		_oglcodes 	= self.pool.get('dincelaccount.config.settings')
		_id			= _oglcodes.search(cr, uid, [], limit=1) 	
		if _id:
			_oglcodes 	= _oglcodes.browse(cr, uid, _id, context=context)
		else:
			raise osv.except_osv(_('No account settings!'), _('No account settings found!'))
		
		_oacct			= self.pool.get('account.move')
		acct_wip 		= _oglcodes.stock_wip.id
		acct_wip_variance = _oglcodes.stock_wip_variance.id
		acct_stock_fgoods = _oglcodes.stock_finished_goods.id
		ar_items_qty 	= {}

		tot_qty		= _obj.product_qty
		for line in _obj.product_lines:
			_lineqty  = line.product_qty
			_qty_made = (_lineqty / tot_qty)*qty
			if ar_items_qty.has_key(line.product_id.id) == False:
				ar_items_qty[line.product_id.id] = _qty_made
			else:
				ar_items_qty[line.product_id.id] += _qty_made	
		
		cost_overhead=0
		cost_material=0
		
		#if _obj.x_order_length:
		#	order_len	= _obj.x_order_length
		#else:
		#	order_len =0
			
		for line in _obj.move_lines:
			#_price  	= line.price_unit
			_price  	= line.product_id.standard_price
			_qty_made 	= ar_items_qty[line.product_id.id]
			
			#if order_len>0:
			#	_qty_made = _qty_made*order_len*0.001	#converting mm to LM
				
			cost_price	= round((_price*_qty_made),4)
			if line.product_id.x_bom_cat in ['labour','overheads']:
				cost_overhead += cost_price
			else:
				cost_material += cost_price
		
		origin 		= _obj.name
		journal_ref = "MOJ" 
		move_name 	= journal_ref + "_" + str(origin)
		
		date_post		= datetime.datetime.today()  #todo alter date ??

		_objperiodcr	= _operiod.find(cr, uid, date_post, context=context)#[0]
		
		if _objperiodcr:
			period_id 			= _objperiodcr[0]# in above code

			_journal_id			= self.pool.get('account.journal').search(cr, uid, [('type', '=', 'general')], limit=1)[0] 	
			
			state_move			= "posted"	#"draft" [NOTE, if posted then it will automatically reported in Tiral Balance, General Ledger, reports, etc]
		
			self.ref_name 		= origin+"_"+str(mo_id)
			self.state_move 	= state_move
			self.journal_id 	= _journal_id
			self.move_name 		= move_name
			self.date_move		= date_post
			self.period_id		= period_id
			
			_id		=	self.insert_move(cr, uid, ids, context=context)
			if _id:
				#---------------------1---------------------
				cost_material	= round(cost_material,4)
				cost_overhead	= round(cost_overhead,4)
				amt_fgsh		= cost_material+cost_overhead
				cost_overhead	= amt_fgsh-cost_material
				state_line		= "valid"
				account_id		= acct_stock_fgoods
				debit			= amt_fgsh
				credit 			= 0
				
				self.move_id 		= _id
				self.state_line 	= state_line
				self.journal_id 	= _journal_id
				self.move_line_name = move_name
				self.date_move		= date_post
				self.period_id		= period_id
				#actmove.partner_id	= partner_id
				self.account_id		= account_id
				self.debit			= debit
				self.credit			= credit
				
				self.insert_move_line(cr, uid, ids, context=context)
				
				#----------	
				account_id	= acct_wip_variance
				debit		= 0
				credit 		= cost_overhead
				self.account_id	=account_id
				self.debit	=debit
				self.credit	=credit
				self.insert_move_line(cr, uid, ids, context=context)	
				
				account_id	= acct_wip
				debit		= 0
				credit 		= cost_material
				self.account_id	=account_id
				self.debit	=debit
				self.credit	=credit
				self.insert_move_line(cr, uid, ids, context=context)	
					
			return _id
			
		else:
			raise osv.except_osv(_('No account settings!'), _('No account settings found!'))		
	
	
	#Process C		Issue - Manufacturing Order				
	def mo_produce_start_journal_dcs(self, cr, uid, ids, mo_id, context=None):
		#def mo_produced_started_dcs(self, cr, uid, ids, mrp_id, qty, context=None):
		_mo 		= self.pool.get('mrp.production')
		_obj  		= _mo.browse(cr, uid, mo_id, context=context)
		
		_operiod 	= self.pool.get('account.period') 
		_oprod 		= self.pool.get('product.product')
		_oglcodes 	= self.pool.get('dincelaccount.config.settings')
		_id			= _oglcodes.search(cr, uid, [], limit=1) 	
		if _id:
			_oglcodes 	= _oglcodes.browse(cr, uid, _id, context=context)
		else:
			raise osv.except_osv(_('No account settings!'), _('No account settings found!'))
		
		_oacct				= self.pool.get('account.move')
		acct_wip 			= _oglcodes.stock_wip.id
		acct_raw_material 	= _oglcodes.stock_inventory.id
		
		#ar_items_qty 		= {}
		tot_qty		= _obj.product_qty
		 
		amt_wip_total=0
		cost_overhead=0 
		
		#if _obj.x_order_length:
		#	order_len	= _obj.x_order_length
		#else:
		#	order_len =0
			
		#for line in _obj.move_lines:
		for line in _obj.bom_id.bom_line_ids:
			#		product_qty
			_price  	= line.product_id.standard_price
			
			_qty_made 	= round((tot_qty*line.product_qty),4) #BOM qty x produce qty 
			#if order_len>0:
			#	_qty_made = _qty_made*order_len*0.001	#converting mm to LM
				
			cost_price	= round((_price*_qty_made),4)
			if line.product_id.x_bom_cat in ['labour','overheads']:
				cost_overhead += cost_price
			else:
				#m2 from LM
				#if product_obj.x_is_main=='1':
				#if line.product_id.x_stock_width and line.product_id.x_stock_width>0:
				#	qty_m2 = round(((order_len*_qty_made*0.001)*(line.product_id.x_stock_width/1000)),4) 	#M2 
				#else:	
				#	qty_m2 = round(((order_len*_qty_made*0.001)/3),4) 	#M2 
				#cost_price	= _price*qty_m2
				amt_wip_total += cost_price
				#else:
					
		origin 			= _obj.name
		journal_ref	 	= "MOJ" 
		move_name 		= journal_ref + "_" + str(origin)
		
		date_post		= datetime.datetime.today()  #todo alter date ??

		_objperiodcr	= _operiod.find(cr, uid, date_post, context=context)#[0]
		
		if _objperiodcr:
			period_id 			= _objperiodcr[0]# in above code

			_journal_id			= self.pool.get('account.journal').search(cr, uid, [('type', '=', 'general')], limit=1)[0] 	
			
			state_move			= "posted"	#"draft" [NOTE, if posted then it will automatically reported in Tiral Balance, General Ledger, reports, etc]
		
			self.ref_name 		= origin+"_"+str(mo_id)
			self.state_move 	= state_move
			self.journal_id 	= _journal_id
			self.move_name 		= move_name
			self.date_move		= date_post
			self.period_id		= period_id
			
			_id	=	self.insert_move(cr, uid, ids, context=context)
			if _id:
				#---------------------1---------------------
				state_line		= "valid"
				account_id		= acct_wip
				debit			= amt_wip_total
				credit 			= 0
				
				self.move_id 		= _id
				self.state_line 	= state_line
				self.journal_id 	= _journal_id
				self.move_line_name = move_name
				self.date_move		= date_post
				self.period_id		= period_id
				
				#actmove.partner_id	= partner_id
				self.account_id	= account_id
				self.debit		= debit
				self.credit		= credit
				
				self.insert_move_line(cr, uid, ids, context=context)
				
				#----------	
				account_id		= acct_raw_material
				debit			= 0
				credit 			= amt_wip_total
				self.account_id	= account_id
				self.debit		= debit
				self.credit		= credit
				self.insert_move_line(cr, uid, ids, context=context)	
					
			return _id
		else:
			raise osv.except_osv(_('No account settings!'), _('No account settings found!'))	
			
class dincelaccount_invoice_dcs(osv.Model):
	_name= "dincelaccount.invoice.dcs"
	invoice_type	= ""
	partner_id		= 0
	journal_id		= 0
	amount_tax		= 0
	amount_total	= 0
	amount_untaxed	= 0
	invoice_state	= 0
	
	date_invoice 	= None
	period_id 		= 0
	
	account_id		= None
	company_id		= None
	
	new_id			= 0
	invoice_ref		= 0
	invoice_ref_name= 0
	currency_id		= 0
	invoice_name	= ""
	comment			= ""
	full_delivered	= 0
	account_state	= ""
	invoice_id		= 0
	
	acct_trade_dr		= None
	acct_sale_acct		= None
	
	sale_tax			= None
	
	acct_sale_tax		= None
	acct_sale_cogs		= None
	acct_sale_goods		= None
	acct_sale_discount		= None
	acct_sale_unrealised		= None
	acct_unrealised_discount	= None
	acct_sale_taxrefund	= None
	
	journal_ref		= ""
	sale_tax_id		= None
	sale_taxrefund	= None
	
	total_saleprice = 0
	total_costprice = 0
	total_discount	= 0
	
	actmove			= None
	
	all_items 		= []
	move_id			= 0
	subtotal_wo_discount = 0
	'''
	def __init__(self, cr, uid, ids, context=None):
		self.cr 	 =cr
		self.uid 	 =uid
		self.ids 	 =ids
		self.context =context'''
	'''
	=============================
	Tot : 			   55,000 [D]
	Less discount :  	2,500 [C]
	-----------------------------
	Net	:			   52,500	
	GST :			    5,250 [B]
	-----------------------------
	TOT	:			   57,750 [A]	
	=============================
	account_invoice
		amount_tax 				[ 5, 250 ]  [B]
		amount_total 			[ 57,750 ]  [A]
		subtotal_wo_discount 	[ 55,000 ]  [D]
		amount_untaxed			[ 52,500 ]  
	account_invoice_line
		price_subtotal 			[ 47500.00, 5000.00] = [52,500 ]
		discount 				[ 5, 0 ]
		price_unit				[ 100.00, 50.00 ]
		quantity 				[ 500.000, 1000.000 ]
		subtotal_wo_discount 	[ 50000.00, 5000.00] = [55,000]
	'''
	def get_invoice_detail(self):
		#self.invoice_ref = invoice_ref
		obj_inv = self.pool.get('account.invoice')	
		_obj    = obj_inv.browse(cr, uid, self.invoice_ref, context)
		'''
		sql = "select id,journal_id,name,company_id,currency_id,amount_untaxed,amount_tax,amount_total,subtotal_wo_discount,state,partner_id, type,account_id,date_invoice,period_id,x_full_delivered from account_invoice where id='%s'" %(self.invoice_ref)
		self.cr.execute(sql)
		row 		= self.cr.dictfetchone()
		if row == None or len(row)==0:
			return 0
		else:'''
		if _obj:	
			self.invoice_id		= _obj.id#row['id']
			self.partner_id 	= _obj.partner_id and _obj.partner_id.id # row['partner_id']
			self.company_id 	= _obj.company_id and _obj.company_id.id # row['company_id']
			
			self.full_delivered = _obj.x_full_delivered # row['x_full_delivered']
			self.invoice_name	= _obj.name #row['name']
			self.currency_id	= _obj.currency_id and _obj.currency_id.id #row['currency_id']
			
			self.journal_id		= _obj.journal_id and _obj.journal_id.id #row['journal_id']
			self.account_state	= _obj.state #row['state']
			self.account_id		= _obj.account_id and _obj.account_id.id #row['account_id']
			
			self.amount_untaxed	= _obj.amount_untaxed #row['amount_untaxed']
			self.amount_tax 	= _obj.amount_tax #row['amount_tax']
			self.amount_total 	= _obj.amount_total #row['amount_total']
			self.subtotal_wo_discount		= _obj.subtotal_wo_discount #row['subtotal_wo_discount']
			
			self.date_invoice	= _obj.date_invoice #row['date_invoice']
			#self.period_id 		= row['period_id'] #passed from the top lavel [  dincelaccount.py->invoice_sales_validate_final()	]
			
			self.total_discount	 =  (self.amount_tax + self.subtotal_wo_discount) - self.amount_total
			
			_oglcodes 	= self.pool.get('dincelaccount.config.settings')
			_id			= _oglcodes.search(cr, uid, [], limit=1) 	
			if _id:
				_oglcodes 	= _oglcodes.browse(cr, uid, _id, context=context)
			else:
				raise osv.except_osv(_('No account settings!'), _('No account settings found!'))
			'''
			sql 		= "select x_sale_acct_receive,x_sale_account,x_sale_account_tax,x_sale_cogs,x_sale_finished_goods,x_sale_cash_discount,x_sale_unrealised,x_sale_unrealised_discount from dincelaccount_config_settings"
			self.cr.execute(sql)
			res 		= self.cr.dictfetchone()	#self.cr.fetchone()
			if res:'''
			self.acct_trade_dr 		= _oglcodes.sale_receiveable.id		#(res['x_sale_acct_receive'])
			self.acct_sale_acct 	= _oglcodes.sale_sale.id			#(res['x_sale_account'])
			
			self.sale_tax 			= _oglcodes.sale_sale_tax.id		#(res['x_sale_account_tax'])
			
			self.acct_sale_cogs 	= _oglcodes.sale_cogs.id			#(res['x_sale_cogs'])
			self.acct_sale_goods 	= _oglcodes.sale_finished_goods.id	#(res['x_sale_finished_goods'])
			self.acct_sale_discount = _oglcodes.sale_cash_discount.id	#(res['x_sale_cash_discount'])
			self.acct_sale_unrealised  		= _oglcodes.sale_unrealised.id	#(res['x_sale_unrealised'])
			self.acct_unrealised_discount  	= _oglcodes.sale_unrealised_discount.id	#(res['x_sale_unrealised_discount'])
			
			_objtax 	= self.pool.get('account.tax')
			_objtax 	= _objtax.browse(cr, uid, self.sale_tax, context=context)
			self.acct_sale_tax_id		=_objtax.account_collected_id.id	
			self.acct_sale_taxrefund	=_objtax.account_paid_id.id
			
			'''
			sql = "select account_collected_id,account_paid_id from account_tax where id='%s'"%(self.sale_tax)
			self.cr.execute(sql)
			rest = self.cr.fetchone()
			if rest:
				self.acct_sale_tax_id		=rest[0]
				self.acct_sale_taxrefund	=rest[1]
			else:
				self.acct_sale_tax_id		=None
				self.acct_sale_taxrefund	=None
					
			'''
		
			self.all_items 	= []
			self.total_saleprice = 0  #without delivery fee, etc -- without delivery fee and (less discounted)
			self.total_costprice = 0  #for cogs	
			#self.total_discount	= 0  #[C]
			'''
			sql 	= "select account_id,sequence,invoice_id,price_unit,price_subtotal,company_id,product_id,partner_id,quantity,name,subtotal_wo_discount-price_subtotal as disct  from account_invoice_line where invoice_id='%s'" % (self.invoice_ref)	
			self.cr.execute(sql)
			rows1 	= self.cr.dictfetchall()
			for row1 in rows1:'''
			for line in _obj.invoice_line:
				price1 		= line.price_subtotal	# row1['price_subtotal']  #already reduced discount
				product_id1 = line.product_id.id #row1['product_id']
				quantity1	= line.quantity	#row1['quantity']
				account_id1	= line.account_id.id #row1['account_id']
				disct		= line.disct	#row1['disct']
				
				#if disct and disct > 0:
				#	self.total_discount += disct
				type1	 = line.product_id.type
				standard_price1= line.standard_price
				'''
				sql 		= "select t.type,t.id from product_template t,product_product p where p.product_tmpl_id=t.id and p.id= '%s'" % (product_id1)
				self.cr.execute(sql)
				rowsk1 		= self.cr.fetchone()
				if rowsk1 == None or len(rowsk1)==0:
					type1 	= ""
					tp_id	= 0
				else:	
					type1	= rowsk1[0]		#product type [service, etc]
					tp_id	= rowsk1[1]		#template id
				
				sql 		= "select value_float from ir_property where res_id = 'product.template,%s' and name='standard_price' " % (tp_id)
				self.cr.execute(sql)
				rowsk 		= self.cr.fetchone()
				if rowsk == None or len(rowsk)==0:
					standard_price1 = 0
				else:	
					standard_price1	= rowsk[0]		#cost price 
				'''	
				costprice1 	= round((standard_price1*quantity1),4)
				
				self.total_costprice += costprice1
				
				found 		= False	
				if type1 == "service":
					if account_id1:	#EG. Delivery charge
						found 	= True	
						item	= [account_id1, price1, costprice1, type1]
						self.all_items.append(item)
				if found == False:
					self.total_saleprice += (price1 + disct)  #without delivery fee and (less discounted)
					
			return 1
	
	def get_journal_ref(self):
		sql = "select code from account_journal where  id='%s'  " %(self.journal_id)
		self.cr.execute(sql)
		rowsk 		= self.cr.fetchone()
		if rowsk == None or len(rowsk)==0:
			self.journal_ref 	= ""
		else:	
			self.journal_ref	= rowsk[0]
			
	def record_sale_journal(self):
		ret = self.get_invoice_detail()
		if ret == 1:
			
			self.get_journal_ref()	
			self.invoice_type		= "out_invoice"
			self.invoice_name 		= self.journal_ref + "_" + str(self.invoice_id)
			self.state_move			= "posted"	#  #draft, posted
			self.state_line			= "valid"
			move_id = self.insert_move()
			if move_id:
				self.add_journal_sale()
			return 1
		else:
			return 0
			
	def record_refund_journal(self):
		ret = self.get_invoice_detail()
		if ret == 1:
			self.invoice_type	= "out_refund"
			return 1
		else:
			return 0
	
	def record_delivery_journal(self):
		ret = self.get_invoice_detail()
		if ret == 1:
			self.invoice_type	= "out_invoice"
			return 1
		else:
			return 0
	
	def record_mrp_journal(self):
		ret = self.get_invoice_detail()
		if ret == 1:
			self.invoice_type	="out_invoice"
			return 1
		else:
			return 0
	
	def insert_move(self):
		actmove = dincelaccount_journal(self.cr, self.uid, self.ids, self.context)#(cr,journal_id)	
		actmove.journal_id		= self.journal_id
		actmove.partner_id		= self.partner_id
		actmove.ref_name 		= self.invoice_name
		actmove.company_id 		= self.company_id
		actmove.state_move 		= self.state_move
		actmove.date_invoice 	= self.date_invoice
		actmove.period_id 		= self.period_id
		
		self.move_id = actmove.insert_move()
		
		self.actmove = actmove
		
		return self.move_id
	
	def is_refund_invoice(self):
		if self.invoice_type	== "out_refund":
			return True
		else:
			return False
			
	#Process 1/3: Invoice Raised	
	def add_journal_sale(self):
		#SALES#
		
		#_logger.error("invoice_sales_validate:ERROR_INVOICE-account.self.full_delivered["+str(self.full_delivered)+"]")
		
		actmove = self.actmove
		if self.full_delivered:	
			self.add_journal_delivery()
		
		#TAX#
		if self.amount_tax > 0 and self.acct_sale_tax_id:
			if self.is_refund_invoice():
				cr_amt = 0
				dr_amt = self.amount_tax	
			else:
				cr_amt = self.amount_tax
				dr_amt = 0	
			
			actmove.credit 		= cr_amt	
			actmove.debit 		= dr_amt
			actmove.account_id  = self.acct_sale_tax_id
			actmove.insert_move_line()
			
		#SERVICES ETC. DELIVERY,ETC
		for item in self.all_items:
			if self.is_refund_invoice():
				cr_amt = 0
				dr_amt = item[1]
			else:
				cr_amt = item[1]
				dr_amt = 0	
			actmove.credit 		= cr_amt
			actmove.debit 		= dr_amt
			actmove.account_id  = item[0]
			actmove.insert_move_line()		
	
		
		#Unrealised sales cr
		if self.is_refund_invoice():
			cr_amt = 0
			dr_amt = self.total_saleprice 
		else:
			cr_amt = self.total_saleprice 
			dr_amt = 0	
		actmove.credit 		= cr_amt 	
		actmove.debit 		= dr_amt
		actmove.account_id  = self.acct_sale_unrealised
		actmove.insert_move_line()
		
		#discount allowed
		if self.total_discount > 0:
			if self.is_refund_invoice():
				cr_amt = self.total_discount
				dr_amt = 0
			else:
				cr_amt = 0 
				dr_amt = self.total_discount
			
			actmove.credit 		= cr_amt
			actmove.debit 		= dr_amt
			actmove.account_id  = self.acct_unrealised_discount
			actmove.insert_move_line()
		
		#Trade debtors dr
		if self.is_refund_invoice():
			cr_amt = self.amount_total 
			dr_amt = 0
		else:
			cr_amt = 0 
			dr_amt = self.amount_total 	
		actmove.credit 		= cr_amt
		actmove.debit 		= dr_amt
		actmove.account_id  = self.acct_trade_dr
		actmove.insert_move_line()	
			
	#Process 2/3: Product manufactured
	#def add_journal_mrp(self):
		
		
	#Process 3/3: Product delivered
	def add_journal_delivery(self):
		actmove = self.actmove
		#---added in reverse order, cause the display in openerp view. (reversed)
		#Journal 2/2
		#Unrealised sales cr
		if self.total_discount > 0:
			if self.is_refund_invoice():
				cr_amt = self.total_discount
				dr_amt = 0
			else:
				cr_amt = 0 
				dr_amt = self.total_discount	
			actmove.credit 		= cr_amt	
			actmove.debit 		= dr_amt
			actmove.account_id  = self.acct_sale_discount
			actmove.insert_move_line()
			
			if self.is_refund_invoice():
				cr_amt = 0
				dr_amt = self.total_discount 
			else:
				cr_amt = self.total_discount  
				dr_amt = 0	
			actmove.credit 		= cr_amt	
			actmove.debit 		= dr_amt
			actmove.account_id  = self.acct_unrealised_discount
			actmove.insert_move_line()
		
		#product sals credit
		if self.is_refund_invoice():
			cr_amt = 0
			dr_amt = self.total_saleprice 
		else:
			cr_amt = self.total_saleprice  
			dr_amt = 0	
		
		actmove.credit 		= cr_amt 	
		actmove.debit 		= dr_amt
		actmove.account_id  = self.acct_sale_acct
		actmove.insert_move_line()
		
		#Unrealised sales dr
		if self.is_refund_invoice():
			cr_amt = self.total_saleprice	
			dr_amt = 0
		else:
			cr_amt = 0  
			dr_amt = self.total_saleprice	
		
		actmove.credit 		= cr_amt 	
		actmove.debit 		= dr_amt
		actmove.account_id  = self.acct_sale_unrealised
		actmove.insert_move_line()
		
		#Journal 1/2
		#FINISHED GOODS#
		if self.is_refund_invoice():
			cr_amt = 0	
			dr_amt = self.total_costprice	
		else:
			cr_amt = self.total_costprice	  
			dr_amt = 0	
		
		actmove.credit 		= self.total_costprice		
		actmove.debit 		= 0
		actmove.account_id  = self.acct_sale_goods
		actmove.insert_move_line()
		
		#COGS#
		if self.is_refund_invoice():
			cr_amt = self.total_costprice		
			dr_amt = 0	
		else:
			cr_amt = 0	  
			dr_amt = self.total_costprice	
		actmove.credit 		= 0
		actmove.debit 		= self.total_costprice		
		actmove.account_id  = self.acct_sale_cogs
		actmove.insert_move_line()
		
		
	def insert_refund(self, journal_id, date_invoice, comment):
		ret = self.get_invoice_detail()
		if ret == 1:
			self.journal_id		=journal_id
			self.date_invoice	=date_invoice
			self.comment		=comment
			self.invoice_type	="out_refund"
			
			self.get_journal_ref()	
			vals={
				'reference_type':'none',
				'x_invoice_ref':self.invoice_ref,
				'journal_id':self.journal_id,
				'type': self.invoice_type,
				'date_invoice':self.date_invoice,
				'period_id':self.period_id,
				'name':self.invoice_name,
				'company_id':self.company_id,
				'currency_id': self.currency_id,
				'amount_untaxed':self.amount_untaxed,
				'amount_tax':self.amount_tax,
				'amount_total':self.amount_total,
				'state':self.account_state,
				'partner_id': self.partner_id,
				'account_id':self.account_id,
				'comment':self.comment,
			}
			
			_obj 	= self.pool.get('account.invoice')	
			self.new_id = _obj.create(cr, uid, vals, context=context)
			'''
			sql = "insert into account_invoice(reference_type,x_invoice_ref,journal_id, type,date_invoice,period_id,name,company_id,currency_id,amount_untaxed,amount_tax,amount_total,state,partner_id,account_id,comment) " \
				"	values('none','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s')" \
				""%(self.invoice_ref, self.journal_id, self.invoice_type, self.date_invoice, self.period_id, self.invoice_name, self.company_id, self.currency_id, self.amount_untaxed, self.amount_tax, self.amount_total, self.account_state, self.partner_id, self.account_id, self.comment)
			
			self.cr.execute(sql)
			self.cr.commit()

			sql = "select id from account_invoice where x_invoice_ref='%s' and journal_id='%s' and type='%s' " %(self.invoice_ref, self.journal_id, self.invoice_type)
			self.cr.execute(sql)
			rowsk 		= self.cr.fetchone()
			if rowsk == None or len(rowsk)==0:
				return 0
			else:	'''
			#self.new_id		=	rowsk[0]
			
			self.insert_refund_lines()
			
			#self.insert_refund_journals()
			self.invoice_name 		= self.journal_ref + "_" + str(self.invoice_id)
			self.state_move			= "posted"	#  #draft, posted
			self.state_line			= "valid"
			move_id = self.insert_move()
			if move_id:
				self.add_journal_sale()
			return 1
		else:
			return 0
		'''	
		self.invoice_type	= "out_refund"
		sql = "select journal_id,name,company_id,currency_id,amount_untaxed,amount_tax,amount_total,state,partner_id, type,account_id,date_invoice,period_id from account_invoice where id='%s'" %(self.invoice_ref)
		self.cr.execute(sql)
		row 		= self.cr.dictfetchone()
		if row == None or len(row)==0:
			return 0
		else:	
			sql = "insert into account_invoice(reference_type,x_invoice_ref,journal_id, type,date_invoice,period_id,name,company_id,currency_id,amount_untaxed,amount_tax,amount_total,state,partner_id,account_id,comment) " \
				"	values('none','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s')" \
				""%(self.invoice_ref, self.journal_id, self.invoice_type, self.date_invoice, self.period_id, row['name'], row['company_id'], row['currency_id'], row['amount_untaxed'], row['amount_tax'], row['amount_total'], row['state'], row['partner_id'], row['account_id'], self.comment)
			
			self.cr.execute(sql)
			self.cr.commit()
			
			self.partner_id 	= row['partner_id']
			self.company_id 	= row['company_id']
			self.amount_tax 	= row['amount_tax']
			self.amount_total 	= row['amount_total']

			sql = "select id from account_invoice where x_invoice_ref='%s' and journal_id='%s' and type='%s' " %(self.invoice_ref, self.journal_id, self.invoice_type)
			self.cr.execute(sql)
			rowsk 		= self.cr.fetchone()
			if rowsk == None or len(rowsk)==0:
				return 0
			else:	
				self.new_id		=	rowsk[0]
				
				self.insert_refund_lines()
				
				self.insert_refund_journals()
				
				return self.new_id
		'''
	def insert_refund_lines(self):
		obj_inv = self.pool.get('account.invoice')	
		_obj    = obj_inv.browse(cr, uid, self.invoice_ref, context)
		_invl 	= self.pool.get('account.invoice.line')	
		for line in _obj.invoice_line:
			vals={
				'invoice_id':self.new_id,
				'account_id':line.account_id.id,
				'sequence':line.sequence,
				'price_unit':line.price_unit,
				'price_subtotal':line.price_subtotal,
				'company_id':line.company_id.id,
				'product_id':line.product_id.id,
				'partner_id':line.partner_id.id,
				'quantity':line.quantity,
				'name':line.name,
			}
			_invl.create(cr, uid, vals, context=context)
			#_obj 	= self.pool.get('account.invoice.line')	
			#lids1	= _obj.search(cr,uid,[('invoice_id','=',self.invoice_ref)])
			#account_invoice_line
			'''sql = "select account_id,sequence,invoice_id,price_unit,price_subtotal,company_id,product_id,partner_id,quantity,name from account_invoice_line where invoice_id='%s'" % (self.invoice_ref)	
			self.cr.execute(sql)
			rows = self.cr.dictfetchall()
			for row in rows:'''
			'''sql = "insert into account_invoice_line(invoice_id,account_id,sequence,price_unit,price_subtotal,company_id,product_id,partner_id,quantity,name) " \
				"	values('%s','%s','%s','%s','%s','%s','%s','%s','%s','%s')" \
				""%(self.new_id, row['account_id'], row['sequence'], row['price_unit'], row['price_subtotal'], row['company_id'], row['product_id'], row['partner_id'], row['quantity'], row['name'])
			
			self.cr.execute(sql)
			self.cr.commit()
			'''
	 	
	def insert_refund_journals(self):
		return 0
		
class dincelaccount_journal(osv.Model):
	_name = "dincelaccount.journal"
	
	account_id		= None
	company_id		= None
	move_id			= None
	partner_id		= None
	name			= None
	date			= None
	period_id		= None
	
	acct_trade_dr	= None
	acct_sale		= None
	
	sale_tax		= None
	
	acct_deposit	= None
	acct_sale_cogs	= None
	acct_sale_goods	= None
	acct_sale_discount		= None
	acct_sale_unrealised	= None
	acct_unrealised_discount	= None
	acct_freight	= None
	acct_freight_unrealised	= None
	
	sale_tax_id		= None
	sale_taxrefund	= None
	
	gen_overpayments= None
	gen_card_fees	= None
	
	invoice_type	= "out_invoice"
	
	x_region_id		= None
	x_coststate_id	= None
	amount_tax		= 0
	acct_trade_cr	= None
	def _get_config_data(self, cr, uid, ids, context=None):
		_config =self.pool.get('dincelaccount.config.settings')
		_id		= _config.search(cr, uid, [], limit=1) 	
		if _id:
			_config 				= _config.browse(cr, uid, _id, context=context)
			self.acct_trade_dr 		= _config.sale_receiveable and _config.sale_receiveable.id  or False
			self.acct_sale 			= _config.sale_sale and _config.sale_sale.id  or False			
			
			self.acct_trade_cr		= _config.buy_payable and _config.buy_payable.id  or False
			
			self.sale_tax 			= _config.sale_sale_tax and _config.sale_sale_tax.id  or False		
			
			self.acct_deposit 		= _config.sale_advance_payment and _config.sale_advance_payment.id  or False		
			
			self.acct_sale_cogs 			= _config.sale_cogs and _config.sale_cogs.id  or False						
			self.acct_sale_goods 			= _config.sale_finished_goods and _config.sale_finished_goods.id  or False
			self.acct_sale_discount 		= _config.sale_cash_discount and _config.sale_cash_discount.id  or False	
			self.acct_sale_unrealised  		= _config.sale_unrealised and _config.sale_unrealised.id  or False	
			self.acct_unrealised_discount  	= _config.sale_unrealised_discount and _config.sale_unrealised_discount.id  or False	
			self.acct_freight				= _config.sale_freight and _config.sale_freight.id  or False							
			self.acct_freight_unrealised	= _config.sale_freight_unrealised and _config.sale_freight_unrealised.id  or False	
			
			self.gen_overpayments	= _config.gen_overpayments and _config.gen_overpayments.id  or False	
			self.gen_card_fees	= _config.gen_card_fees and _config.gen_card_fees.id  or False	
			
			sql = "select account_collected_id,account_paid_id from account_tax where id='%s'" % (self.sale_tax)
			cr.execute(sql)
			rest = cr.fetchone()
			if rest:
				self.sale_tax_id	= rest[0]
				self.sale_taxrefund	= rest[1]
			else:
				self.sale_tax_id		= None
				self.sale_taxrefund	= None
	
	def purchase_nostock2journals(self, cr, uid, ids, _obj, context=None):
		self._get_config_data(cr, uid, ids, context)
		self.journal_id		= _obj.journal_id.id	
		 
		self.partner_id 	= _obj.partner_id and _obj.partner_id.id or False		
		self.date 			= _obj.date
		self.name			= _obj.name#reference
		self.company_id 	= _obj.company_id and _obj.company_id.id or False
		state				= "posted"	#  #draft, posted
			
		_objperiod 			= self.pool.get('account.period') 
		self.period_id		= _objperiod.find(cr, uid, self.date, context=context)[0]
		if self.period_id:
			obj_move = self.pool.get('account.move')
			obj_move_line = self.pool.get('account.move.line')
			
			vals={
				'journal_id':self.journal_id,
				'name':self.name,
				'company_id':self.company_id,
				'state':state,
				'date':self.date,
				'period_id':self.period_id,
				'partner_id':self.partner_id,
			}
			#_logger.error("purchase_nostock2journals.purchase_nostock2journals["+str(vals)+"]")
			self.move_id = obj_move.create(cr, uid, vals, context=context)
			if self.move_id:
				self.invoice_type	= "na"
				amt_total=0
				amt_total_tax=0.0
				for line in _obj.line_dr_ids:
					account_id	= line.account_id.id
					
					debit 		= line.untax_amount
					self.name	= line.name
					credit		= 0
					if line.x_region_id:
						self.x_region_id	= line.x_region_id.id
					if line.x_coststate_id:
						self.x_coststate_id	= line.x_coststate_id.id
						
					self.add_journal_moveline(cr, uid, ids,debit, credit,account_id, context)
					amt_total+=line.untax_amount
					
					if line.x_tax_id and line.x_tax_id.account_paid_id:
						amt_total_tax+=line.x_tax_amount
						self.name	= line.x_tax_id.name
						debit		= line.x_tax_amount
						credit		= 0
						account_id	= line.x_tax_id.account_paid_id.id
						self.add_journal_moveline(cr, uid, ids,debit, credit,account_id, context)
				'''if _obj.tax_id and _obj.tax_id.account_paid_id:
					self.name	= _obj.tax_id.name
					debit		=_obj.tax_amount
					credit		=0
					account_id	=_obj.tax_id.account_paid_id.id
					self.add_journal_moveline(cr, uid, ids,debit, credit,account_id, context)
				'''	
				self.name	= _obj.name#reference
				credit		=amt_total+amt_total_tax#amt_total+_obj.tax_amount
				debit		=0
				account_id	=_obj.account_id.id		#trade cr
				self.add_journal_moveline(cr, uid, ids, debit, credit,account_id, context)
				
				#payment done ------------------------
				#debit		=0
				#credit		=amt_total
				#account_id	=_obj.account_id.id		#trade cr
				#self.add_journal_moveline(cr, uid, ids, debit, credit,account_id, context)
				
				#debit		=0
				#credit		=amt_total+_obj.tax_amount
				#account_id	=_obj.x_account_id.id		#bank account
				#self.add_journal_moveline(cr, uid, ids, debit, credit,account_id, context)
				
				return self.move_id
				
		return False		
		
	def sales_delivery2journals(self, cr, uid, ids, new_id, context=None):
		self._get_config_data(cr, uid, ids, context)
		self.journal_id		= self.pool.get('account.journal').search(cr, uid, [('type', '=', 'sale')], limit=1)[0] 	
		#_logger.error("sales_delivery2journals.journal_id["+str(self.journal_id)+"]")
		
		if self.journal_id:
			_obj = self.pool.get('dincelstock.pickinglist')
			_obj = _obj.browse(cr, uid, new_id, context=context)
			self.partner_id 	= _obj.partner_id and _obj.partner_id.id or False		
			self.date 			= _obj.date_picking
			self.name			= _obj.name
			self.company_id 	= _obj.company_id and _obj.company_id.id or False
			state				= "posted"	#  #draft, posted
			
			_objperiod 			= self.pool.get('account.period') 
			self.period_id		= _objperiod.find(cr, uid, self.date, context=context)[0]
			if self.period_id:
				obj_move = self.pool.get('account.move')
				obj_move_line = self.pool.get('account.move.line')
				
				vals={
					'journal_id':self.journal_id,
					'name':self.name,
					'company_id':self.company_id,
					'state':state,
					'date':self.date,
					'period_id':self.period_id,
					'partner_id':self.partner_id,
				}
				#_logger.error("sales_delivery2journals.journal_idvalsvals["+str(vals)+"]")
				self.move_id = obj_move.create(cr, uid, vals, context=context)
				if self.move_id:
					cogs_amt 	= 0
					disc_amt	= 0
					deli_amt	= 0
					sale_amt	= 0
					amt_item	= 0
					
					for line in _obj.picking_line:
						
						amt_cost 		= line.product_id.standard_price	#cogs [cost price, standanrd cost]
						qty 			= line.ship_qty 
						qty_lm			= qty
						price_unit	 	= line.price_unit #sale price [=product sales]
						if line.region_id:
							self.x_region_id = line.region_id.id
						else:
							self.x_region_id = None
						if line.coststate_id:
							self.x_coststate_id=line.coststate_id.id
						else:
							self.x_coststate_id=None
							
						if line.product_id.x_prod_cat == "freight":
							amt_item	= round((price_unit*qty),4)
							deli_amt += amt_item							
						else:
							length = line.order_length
							if length>0 and line.product_id.x_is_main=='1':
								qty_lm=length*qty*0.001
								qty=round((qty_lm/3),4) #equavilent m2 value
							#if line.product_id.x_is_main=='1':
							#	qty 		= qty*line.order_length*0.001
							#if line.product_id.x_stock_width and line.product_id.x_stock_width>0:
							#	qty = round(((length*qty*0.001)*(line.product_id.x_stock_width/1000)),4) 	#M2 
							#else:	
							#	qty = round(((length*qty*0.001)/3),4) 	#M2 ---cause the rate in invoice is per M2 (Meter Square) not per LM (Linear metres)
							#else:
							#	#qty 			= line.ship_qty 
							amt_item	= round((price_unit*qty),4)
							sale_amt += amt_item
							
						amt_cost	= round((amt_cost*qty_lm),4) #cause standard cost ins in LM but the qty is in M2
						#amt_item	= price_unit*qty	
						
						cogs_amt += amt_cost
						
						disc_amt += round((amt_item*line.disc_pc*0.01),4)
					if cogs_amt > 0.00:
						debit		=cogs_amt
						credit		=0
						account_id	=self.acct_sale_cogs
						self.add_journal_moveline(cr, uid, ids,debit, credit,account_id, context)
						debit		=0
						credit		=cogs_amt
						account_id	=self.acct_sale_goods
						self.add_journal_moveline(cr, uid, ids, debit, credit,account_id, context)
					if disc_amt > 0.00:
						debit		=disc_amt
						credit		=0
						account_id	=self.acct_sale_discount
						self.add_journal_moveline(cr, uid, ids,debit, credit,account_id, context)
						debit		=0
						credit		=disc_amt
						account_id	=self.acct_unrealised_discount
						self.add_journal_moveline(cr, uid, ids, debit, credit,account_id, context)
					if deli_amt > 0.00:
						debit		=deli_amt
						credit		=0
						account_id	=self.acct_freight_unrealised
						self.add_journal_moveline(cr, uid, ids, debit, credit,account_id, context)
						debit		=0
						credit		=deli_amt
						account_id	=self.acct_freight
						self.add_journal_moveline(cr, uid, ids, debit, credit,account_id, context)
					if sale_amt > 0.00:
						debit		=sale_amt
						credit		=0
						account_id	=self.acct_sale_unrealised
						self.add_journal_moveline(cr, uid, ids, debit, credit,account_id, context)
						debit		=0
						credit		=sale_amt
						account_id	=self.acct_sale
						self.add_journal_moveline(cr, uid, ids,debit, credit,account_id, context)
					
					if self.x_region_id:
						obj_move.write(cr, uid, self.move_id, {'x_region_id':self.x_region_id})
					if self.x_coststate_id:
						obj_move.write(cr, uid, self.move_id, {'x_coststate_id':self.x_coststate_id})	
					return self.move_id
					
		return False			
	
	def sales_invoice2journals(self, cr, uid, ids,new_id, context=None):
		#self._get_config_data(cr, uid, ids, context)
		_obj =self.pool.get('account.journal')
		_id		= _obj.search(cr, uid, [('type', '=', 'sale')], limit=1)#[0] 
		self.journal = _obj.browse(cr, uid, _id, context=context)[0]
		#self.journal_id		= self.pool.get('account.journal').search(cr, uid, [('type', '=', 'sale')], limit=1)[0] 
		return self._invoice2journals(cr, uid, ids,new_id, context)
		
	def purchase_invoice2journalsxx(self, cr, uid, ids,new_id, context=None):
		#self._get_config_data(cr, uid, ids, context)
		#self.journal_id		= self.pool.get('account.journal').search(cr, uid, [('type', '=', 'purchase')], limit=1)[0] 
		_obj =self.pool.get('account.journal')
		_id		= _obj.search(cr, uid, [('type', '=', 'purchase')], limit=1)#[0] 
		self.journal = _obj.browse(cr, uid, _id, context=context)[0]
		return self._invoice2journals(cr, uid, ids,new_id, context)
	#def sales_invoice2journals(self, cr, uid, ids,new_id, context=None):
	def supplierpayment2journals(self, cr, uid, ids,_id, context=None):
		_objperiod 	= self.pool.get('account.period') 
		_obj     = self.pool.get('account.voucher').browse(cr, uid, _id, context=context)
		tot_paid = 0.0
		#tot_fee  = 0.0
		#tot_tot  = 0.0	
		if _obj.x_payline_ids: 
			for line in _obj.x_payline_ids:
				if line.amount > 0:# and line.invoice_id:
					tot_paid += line.amount
					#if line.amount_fee > 0: 
					#	tot_fee += line.amount_fee
						
			self._get_config_data(cr, uid, ids, context)
			#if _obj.x_amount_xtra > 0:
			#tot_tot += _obj.x_amount_xtra
			#if tot_paid > 0:
			#tot_tot += tot_paid
			#if tot_fee > 0:
			#tot_tot += tot_fee
			self.journal = 	_obj.journal_id
			if tot_paid > 0 and self.journal:	
				 
				#self.invoice_type 	= _obj.type
				self.journal_id  	= self.journal.id
				journal_ref 		= self.journal.code

				self.name 		= journal_ref + "_" + str(_obj.id)
				if _obj.reference:
					self.name 	+=  "_" + str(_obj.reference)
					
				self.company_id	= _obj.company_id.id
				
				#date_invoice	= _obj.date
				
				#self.partner_id	= _obj.partner_id.id
				#self.amount_tax	= _obj.amount_tax	
				
				state			= "posted"	#  #draft, posted
				
				self.date		= _obj.date
				
				self.period_id	= _objperiod.find(cr, uid, _obj.date, context=context)[0]
				state_move	= "posted"	#"draft" #draft, posted [NOTE, if posted then it will automatically reported in Tiral Balance, General Ledger, reports, etc]
				obj_move = self.pool.get('account.move')
			 
				
				vals={
					'journal_id':self.journal_id,
					'name':self.name,
					'ref':self.name,
					'company_id':self.company_id,
					'state':state,
					'date':self.date,
					'period_id':self.period_id,
					#'partner_id':self.partner_id,
				}
				#if self.x_region_id:
				#	vals['x_region_id']= self.x_region_id	
					
				self.move_id = obj_move.create(cr, uid, vals, context=context)
				if self.move_id:
					#bank a/c
					account_id 		  = _obj.journal_id.default_credit_account_id.id
					self.invoice_type = "na" #for add_journal_moveline() below
					
					debit		=0
					credit		=tot_paid
					self.add_journal_moveline(cr, uid, ids, debit, credit, account_id, context)
					 
					debit		=tot_paid
					credit		=0
					account_id	=self.acct_trade_cr
					self.add_journal_moveline(cr, uid, ids, debit, credit, account_id, context)
			
				return self.move_id
					
		return False	
		
	def payment2journals(self, cr, uid, ids,_id, context=None):
		_objperiod 	= self.pool.get('account.period') 
		_obj     = self.pool.get('account.voucher').browse(cr, uid, _id, context=context)
		tot_paid = 0.0
		tot_fee  = 0.0
		tot_tot  = 0.0	
		if _obj.x_payline_ids: 
			for line in _obj.x_payline_ids:
				if line.amount > 0 and line.invoice_id:
					tot_paid += line.amount
					if line.amount_fee > 0: 
						tot_fee += line.amount_fee
						
			self._get_config_data(cr, uid, ids, context)
			#if _obj.x_amount_xtra > 0:
			tot_tot += _obj.x_amount_xtra
			#if tot_paid > 0:
			tot_tot += tot_paid
			#if tot_fee > 0:
			tot_tot += tot_fee
			self.journal = 	_obj.journal_id
			if tot_tot > 0 and self.journal:	
				 
				#self.invoice_type 	= _obj.type
				self.journal_id  	= self.journal.id
				journal_ref 		= self.journal.code

				self.name 		= journal_ref + "_" + str(_obj.id)
				if _obj.reference:
					self.name 	+=  "_" + str(_obj.reference)
					
				self.company_id	= _obj.company_id.id
				
				#date_invoice	= _obj.date
				
				self.partner_id	= _obj.partner_id.id
				#self.amount_tax	= _obj.amount_tax	
				
				state			= "posted"	#  #draft, posted
				
				self.date		= _obj.date
				
				self.period_id	= _objperiod.find(cr, uid, _obj.date, context=context)[0]
				state_move	= "posted"	#"draft" #draft, posted [NOTE, if posted then it will automatically reported in Tiral Balance, General Ledger, reports, etc]
				obj_move = self.pool.get('account.move')
			 
				
				vals={
					'journal_id':self.journal_id,
					'name':self.name,
					'ref':self.name,
					'company_id':self.company_id,
					'state':state,
					'date':self.date,
					'period_id':self.period_id,
					'partner_id':self.partner_id,
				}
				#if self.x_region_id:
				#	vals['x_region_id']= self.x_region_id	
					
				self.move_id = obj_move.create(cr, uid, vals, context=context)
				if self.move_id:
					#bank a/c
					account_id 		  = _obj.journal_id.default_debit_account_id.id
					self.invoice_type = "na" #for add_journal_moveline() below
					
					debit		=tot_tot
					credit		=0
					self.add_journal_moveline(cr, uid, ids, debit, credit, account_id, context)
					if _obj.x_amount_xtra > 0 and self.gen_overpayments:#_obj.writeoff_acc_id:
						debit		=0
						credit		=_obj.x_amount_xtra
						account_id	=self.gen_overpayments#__obj.writeoff_acc_id.id
						self.add_journal_moveline(cr, uid, ids, debit, credit, account_id, context)
					if tot_paid > 0:
						debit		=0
						credit		=tot_paid
						account_id	=self.acct_trade_dr
						self.add_journal_moveline(cr, uid, ids, debit, credit, account_id, context)
					if tot_fee > 0:
						debit		=0
						credit		=tot_fee
						account_id	=self.gen_card_fees
						self.add_journal_moveline(cr, uid, ids, debit, credit, account_id, context)	
				return self.move_id
					
		return False	
		
	def _invoice2journals(self, cr, uid, ids,new_id, context=None):
		self._get_config_data(cr, uid, ids, context)
		
		_objperiod 	= self.pool.get('account.period') 
		_objprod 	= self.pool.get('product.product')
		_obj 		= self.pool.get('account.invoice')
		_obj 		= _obj.browse(cr, uid, new_id, context=context)
		
		if self.journal:#_obj.journal_id:
			self.invoice_type 	= _obj.type
			self.journal_id  	= self.journal.id
			journal_ref 		= self.journal.code

			self.name 		= journal_ref + " " + str(_obj.number)
			self.company_id	= _obj.company_id.id
			
			date_invoice	= _obj.date_invoice
			
			self.partner_id	= _obj.partner_id.id
			self.amount_tax	= _obj.amount_tax	
			
			state			= "posted"	#  #draft, posted
			
			self.date		= date_invoice
			
			self.period_id	= _objperiod.find(cr, uid, date_invoice, context=context)[0]
			state_move	= "posted"	#"draft" #draft, posted [NOTE, if posted then it will automatically reported in Tiral Balance, General Ledger, reports, etc]
			
			all_items 	= []
			tax_name  	= "GST"
			
			total_tax_amt = 0
			deposit_amt	  = 0
			sale_amt	  = 0
			
			sale_unreal_amt = 0
			unreal_disc_amt = 0
			unreal_deli_amt = 0
			total_costprice = 0
			tax_deposit_amt = 0
			for _line in _obj.invoice_line:
				
				price 		= _line.price_subtotal
				product_id 	= _line.product_id.id
				
				_prod 		= _objprod.browse(cr, uid, product_id, context=context)
				quantity	= _line.quantity
				
				prod_cat	= _prod.x_prod_cat
				
				if _line.x_region_id:
					self.x_region_id = _line.x_region_id.id
				else:
					self.x_region_id = None
				if _line.x_coststate_id:
					self.x_coststate_id = _line.x_coststate_id.id
				else:
					self.x_coststate_id = None
					
				found 		= False	
				if prod_cat == "deposit":
				
					costprice	= 0
					deposit_amt	+= price
				elif prod_cat == "freight":
					costprice 	= round((_prod.standard_price*quantity),4)
					
					unreal_deli_amt	+= price
					sale_amt	+= price
				else:
				
					costprice 	= round((_prod.standard_price*quantity),4)
					
					if _line.discount > 0:
						unreal_disc_amt += (_line.subtotal_wo_discount-_line.price_subtotal)
					sale_unreal_amt+= price
					sale_amt	+= price
					
				
				total_costprice += costprice
				
				for _tax in _line.invoice_line_tax_id:
				
					tax_amt = _tax.amount * price
				
					#if prod_cat != "deposit":
					#	sale_amt += tax_amt #trade debtors include tax amt as well
					
					if prod_cat == "deposit":#no tax calc for deposit type
						tax_deposit_amt += tax_amt
					else:
						total_tax_amt += tax_amt
						sale_amt += tax_amt #trade debtors include tax amt as well
					
				
			if self.journal_id:
				obj_move = self.pool.get('account.move')
				#			obj_move_line = self.pool.get('account.move.line')
				
				vals={
					'journal_id':self.journal_id,
					'name':self.name,
					'ref':_obj.name,
					'company_id':self.company_id,
					'state':state,
					'date':self.date,
					'period_id':self.period_id,
					'partner_id':self.partner_id,
				}
				if self.x_region_id:
					vals['x_region_id']= self.x_region_id	
				if self.x_coststate_id:
					vals['x_coststate_id']= self.x_coststate_id		
					
				self.move_id = obj_move.create(cr, uid, vals, context=context)
				if self.move_id:
					if sale_amt > 0.0001:
						#_logger.error("invoice_sales_validate:tax_deposit_amt.deposit_amt["+str(sale_amt)+"]["+str(deposit_amt)+"]["+str(tax_deposit_amt)+"]")
						if deposit_amt < 0.0001:	#for balance invoice
							sale_amt = sale_amt+deposit_amt+tax_deposit_amt
						debit		=sale_amt
						credit		=0
						account_id	=self.acct_trade_dr
						self.add_journal_moveline(cr, uid, ids,debit, credit,account_id, context)
					if unreal_disc_amt > 0.0001:
						debit		=unreal_disc_amt
						credit		=0
						account_id	=self.acct_unrealised_discount
						self.add_journal_moveline(cr, uid, ids,debit, credit,account_id, context)	
					if deposit_amt > 0.0001:
						debit		=deposit_amt+tax_deposit_amt
						credit		=0
						account_id	=self.acct_trade_dr
						self.add_journal_moveline(cr, uid, ids,debit, credit,account_id, context)
						
						debit		=0
						credit		=deposit_amt#+tax_deposit_amt
						account_id	=self.acct_deposit
						self.add_journal_moveline(cr, uid, ids,debit, credit,account_id, context)
						
						if tax_deposit_amt > 0.0001 and self.sale_tax_id:
							debit		=0
							credit		=tax_deposit_amt
							account_id	=self.sale_tax_id
							self.add_journal_moveline(cr, uid, ids,debit, credit,account_id, context)
					elif deposit_amt < 0.0001:
						#if negative deposit.....(just inc case)
						if abs(deposit_amt) > 0.0001:
							debit		=abs(deposit_amt)#+abs(tax_deposit_amt)
							credit		=0
							account_id	=self.acct_deposit
							self.add_journal_moveline(cr, uid, ids,debit, credit,account_id, context)
						
					if unreal_deli_amt > 0.0001:
						debit		=0
						credit		=unreal_deli_amt
						account_id	=self.acct_freight_unrealised
						self.add_journal_moveline(cr, uid, ids,debit, credit,account_id, context)
					
					if sale_unreal_amt > 0.0001:
						
						debit		=0
						credit		=sale_unreal_amt+unreal_disc_amt
						account_id	=self.acct_sale_unrealised
						self.add_journal_moveline(cr, uid, ids,debit, credit,account_id, context)
						
					if total_tax_amt > 0.0001 and self.sale_tax_id:
						debit		=0
						credit		=total_tax_amt+tax_deposit_amt
						account_id	=self.sale_tax_id
						self.add_journal_moveline(cr, uid, ids,debit, credit,account_id, context)
					else:#no tax for the default or other (only deposit tax available)
						if tax_deposit_amt < 0 and self.sale_tax_id:
							debit		=abs(tax_deposit_amt)
							credit		=0
							account_id	=self.sale_tax_id
							self.add_journal_moveline(cr, uid, ids,debit, credit,account_id, context)
					return self.move_id
					
		return False			
							
	def add_journal_moveline(self, cr, uid, ids, debit, credit, account_id, context=None):
		#_logger.error("add_journal_moveline_err_add_journal_moveline_account_id["+str(account_id)+"]")
		obj_move_line = self.pool.get('account.move.line')
		state_line	  = "valid"
		quantity	  = 1

		SIGN = {'na':1,'out_invoice': 1, 'in_invoice': -1, 'out_refund': -1, 'in_refund': 1}
		direction = SIGN[self.invoice_type]
		if direction!=1:#then reverse
			temp 	= debit
			debit 	= credit
			credit 	= temp
		#else:
		#_logger.error("add_journal_moveline_err_add_journal_moveline.obj_move_line["+str(self.invoice_type)+"]["+str(direction)+"]")
		vals1 = {
			'journal_id':self.journal_id,
			'move_id':self.move_id,
			'account_id':account_id,
			'debit': debit,
			'credit':credit,
			'ref':self.name,
			'name':self.name,
			'company_id':self.company_id,
			'state':state_line,
			'date':self.date,
			'quantity':quantity,
			'period_id':self.period_id,
			'partner_id':self.partner_id,
		}
		if self.x_region_id:
			vals1['x_region_id']= self.x_region_id	
		if self.x_coststate_id:
			vals1['x_coststate_id']= self.x_coststate_id			
			
			
		_id = obj_move_line.create(cr, uid, vals1, context=context)		
		if _id == None or _id == False:
			_logger.error("add_journal_moveline_err_add_journal_moveline.obj_move_line["+str(account_id)+"]")
		