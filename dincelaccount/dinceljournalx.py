from openerp.osv import osv, fields
from datetime import date
#from openerp.addons.base_status.base_state import base_state
import time 
import datetime
import csv
import logging
from time import gmtime, strftime
_logger = logging.getLogger(__name__)

class dincelaccount_invoice:
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
	
	def __init__(self, cr, uid, ids, context=None):
		self.cr 	 =cr
		self.uid 	 =uid
		self.ids 	 =ids
		self.context =context
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
		sql = "select id,journal_id,name,company_id,currency_id,amount_untaxed,amount_tax,amount_total,subtotal_wo_discount,state,partner_id, type,account_id,date_invoice,period_id,x_full_delivered from account_invoice where id='%s'" %(self.invoice_ref)
		self.cr.execute(sql)
		row 		= self.cr.dictfetchone()
		if row == None or len(row)==0:
			return 0
		else:	
			self.invoice_id		= row['id']
			self.partner_id 	= row['partner_id']
			self.company_id 	= row['company_id']
			
			self.full_delivered = row['x_full_delivered']
			self.invoice_name	= row['name']
			self.currency_id	= row['currency_id']
			
			self.journal_id		= row['journal_id']
			self.account_state	= row['state']
			self.account_id		= row['account_id']
			
			self.amount_untaxed	= row['amount_untaxed']
			self.amount_tax 	= row['amount_tax']
			self.amount_total 	= row['amount_total']
			self.subtotal_wo_discount		= row['subtotal_wo_discount']
			
			self.date_invoice	= row['date_invoice']
			#self.period_id 		= row['period_id'] #passed from the top lavel [  dincelaccount.py->invoice_sales_validate_final()	]
			
			self.total_discount	 =  (self.amount_tax + self.subtotal_wo_discount) - self.amount_total
			
			sql 		= "select x_sale_acct_receive,x_sale_account,x_sale_account_tax,x_sale_cogs,x_sale_finished_goods,x_sale_cash_discount,x_sale_unrealised,x_sale_unrealised_discount from dincelaccount_config_settings"
			self.cr.execute(sql)
			res 		= self.cr.dictfetchone()	#self.cr.fetchone()
			if res:
				self.acct_trade_dr 		= (res['x_sale_acct_receive'])
				self.acct_sale_acct 	= (res['x_sale_account'])
				
				self.sale_tax 			= (res['x_sale_account_tax'])
				
				self.acct_sale_cogs 	= (res['x_sale_cogs'])
				self.acct_sale_goods 	= (res['x_sale_finished_goods'])
				self.acct_sale_discount = (res['x_sale_cash_discount'])
				self.acct_sale_unrealised  		= (res['x_sale_unrealised'])
				self.acct_unrealised_discount  	= (res['x_sale_unrealised_discount'])
				
				sql = "select account_collected_id,account_paid_id from account_tax where id='%s'"%(self.sale_tax)
				self.cr.execute(sql)
				rest = self.cr.fetchone()
				if rest:
					self.acct_sale_tax_id		=rest[0]
					self.acct_sale_taxrefund	=rest[1]
				else:
					self.acct_sale_tax_id		=None
					self.acct_sale_taxrefund	=None
					
			
		
			self.all_items 	= []
			self.total_saleprice = 0  #without delivery fee, etc -- without delivery fee and (less discounted)
			self.total_costprice = 0  #for cogs	
			#self.total_discount	= 0  #[C]
			sql 	= "select account_id,sequence,invoice_id,price_unit,price_subtotal,company_id,product_id,partner_id,quantity,name,subtotal_wo_discount-price_subtotal as disct  from account_invoice_line where invoice_id='%s'" % (self.invoice_ref)	
			self.cr.execute(sql)
			rows1 	= self.cr.dictfetchall()
			for row1 in rows1:
				price1 		= row1['price_subtotal']  #already reduced discount
				product_id1 = row1['product_id']
				quantity1	= row1['quantity']
				account_id1	= row1['account_id']
				disct		= row1['disct']
				
				#if disct and disct > 0:
				#	self.total_discount += disct
				
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
					
				costprice1 	= standard_price1*quantity1
				
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
			self.invoice_type	= "out_invoice"
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
		
		_logger.error("invoice_sales_validate:ERROR_INVOICE-account.self.full_delivered["+str(self.full_delivered)+"]")
		
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
			else:	
				self.new_id		=	rowsk[0]
				
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
		sql = "select account_id,sequence,invoice_id,price_unit,price_subtotal,company_id,product_id,partner_id,quantity,name from account_invoice_line where invoice_id='%s'" % (self.invoice_ref)	
		self.cr.execute(sql)
		rows = self.cr.dictfetchall()
		for row in rows:
			sql = "insert into account_invoice_line(invoice_id,account_id,sequence,price_unit,price_subtotal,company_id,product_id,partner_id,quantity,name) " \
				"	values('%s','%s','%s','%s','%s','%s','%s','%s','%s','%s')" \
				""%(self.new_id, row['account_id'], row['sequence'], row['price_unit'], row['price_subtotal'], row['company_id'], row['product_id'], row['partner_id'], row['quantity'], row['name'])
			
			self.cr.execute(sql)
			self.cr.commit()
	
	 	
	def insert_refund_journals(self):
		return 0
		'''
		#sql = "select journal_id,name,company_id,currency_id,amount_untaxed,amount_tax,amount_total,state,partner_id, type,account_id,date_invoice,period_id from account_invoice where id='%s'" %(self.new_id)
		#self.cr.execute(sql)
		#row 		= self.cr.dictfetchone()
		if self.new_id > 0:
			#return 0
			#else:
			#amount_tax		 = row['amount_tax']
			#amount_total 	 = row['amount_total']
			
			sql = "select code from account_journal where  id='%s'  " %(self.journal_id)
			self.cr.execute(sql)
			rowsk 		= self.cr.fetchone()
			if rowsk == None or len(rowsk)==0:
				journal_ref 	= ""
			else:	
				journal_ref		= rowsk[0]
			
			self.invoice_name 	= journal_ref + "_" + str(self.new_id)
			state_move			= "posted"	#  #draft, posted
			state_line			= "valid"
			
			actmove = dincelaccount_journal(self.cr, self.uid, self.ids, self.context)#(cr,journal_id)	
			actmove.journal_id		= self.journal_id
			actmove.partner_id		= self.partner_id
			actmove.ref_name 		= self.invoice_name
			actmove.company_id 		= self.company_id
			actmove.state_move 		= state_move
			actmove.date_invoice 	= self.date_invoice
			actmove.period_id 		= self.period_id
			
			move_id = actmove.insert_move()
				
			all_items 	= []
			tax_name  	= "GST"
			sql 		= "select x_sale_acct_receive,x_sale_account,x_sale_account_tax,x_sale_cogs,x_sale_finished_goods,x_sale_cash_discount,x_sale_unrealised,x_sale_unrealised_discount from dincelaccount_config_settings"
			self.cr.execute(sql)
			res 		= self.cr.dictfetchone()	#self.cr.fetchone()
			if res:
				trade_dr 	= (res['x_sale_acct_receive'])
				sale_acct 	= (res['x_sale_account'])
				sale_tax 	= (res['x_sale_account_tax'])
				sale_cogs 	= (res['x_sale_cogs'])
				sale_goods 	= (res['x_sale_finished_goods'])
				sale_discount = (res['x_sale_cash_discount'])
				sale_unrealised  = (res['x_sale_unrealised'])
				unrealised_discount  = (res['x_sale_unrealised_discount'])
				
				#not trade_dr or not sale_acct or not sale_tax or not sale_cogs or not sale_goods:#
				if trade_dr == None or sale_acct == None or sale_tax == None or sale_cogs == None or sale_goods == None or sale_unrealised == None or unrealised_discount == None:
					invalid	= True
				else:
					sql = "select account_collected_id,account_paid_id from account_tax where id='%s'" % (sale_tax)
					self.cr.execute(sql)
					rest = self.cr.fetchone()
					if rest:
						sale_tax_id		= rest[0]
						sale_taxrefund	= rest[1]
						
					else:
						sale_tax_id		= None
						sale_taxrefund	= None
						
					total_saleprice = 0
					total_costprice = 0
					total_discount	= 0
					sql 	= "select account_id,sequence,invoice_id,price_unit,price_subtotal,company_id,product_id,partner_id,quantity,name,subtotal_wo_discount-price_subtotal as disct  from account_invoice_line where invoice_id='%s'" % (self.invoice_ref)	
					self.cr.execute(sql)
					rows1 	= self.cr.dictfetchall()
					for row1 in rows1:
						price1 		= row1['price_subtotal']
						product_id1 = row1['product_id']
						quantity1	= row1['quantity']
						account_id1	= row1['account_id']
						disct		= row1['disct']
						
						if disct and disct > 0:
							total_discount += disct
						#sql 		= "select type from product_template where id= '%s'" % (product_id1)
						sql 		= "select t.type,t.id from product_template t,product_product p where p.product_tmpl_id=t.id and p.id= '%s'" % (product_id1)
						self.cr.execute(sql)
						rowsk1 		= self.cr.fetchone()
						if rowsk1 == None or len(rowsk1)==0:
							type1 	= ""
							tp_id	= 0
						else:	
							type1	= rowsk1[0]
							tp_id	= rowsk1[1]
						
						sql 		= "select value_float from ir_property where res_id = 'product.template,%s' and name='standard_price' " % (tp_id)
						self.cr.execute(sql)
						rowsk 		= self.cr.fetchone()
						if rowsk == None or len(rowsk)==0:
							standard_price1 = 0
						else:	
							standard_price1	= rowsk[0]
							
						costprice1 	= standard_price1*quantity1
						
						total_costprice += costprice1
						
						found 		= False	
						if type1 == "service":
							if account_id1:	#_prod.property_income_account:
								found 	= True	
								item	= [account_id1, price1, costprice1, type1]
								all_items.append(item)
						if found == False:
							total_saleprice += price1
	
					if move_id > 0:

						actmove.move_id 		= move_id
						actmove.move_line_name 	= self.invoice_name
						actmove.state_line		= state_line
						
						#FINISHED GOODS#
						actmove.credit 		= 0						#total_costprice
						actmove.debit 		= total_costprice		#0
						actmove.account_id  = sale_goods
						actmove.insert_move_line()
						
						#COGS#
						actmove.credit 		= total_costprice		#0
						actmove.debit 		= 0						#total_costprice
						actmove.account_id  = sale_cogs
						actmove.insert_move_line()
							
						#--------------------------------------------------------------------------------------------------------------------------------------------------
						#TAX#
						if self.amount_tax > 0 and sale_tax_id:
							actmove.credit 		= 0					#amount_tax
							actmove.debit 		= self.amount_tax	#0
							actmove.account_id  = sale_tax_id
							actmove.insert_move_line()
						
						#SERVICES ETC. DELIVERY,ETC
						for item in all_items:
							actmove.credit 		= 0			#item[1]
							actmove.debit 		= item[1]	#0
							actmove.account_id  = item[0]
							actmove.insert_move_line()		
							
						#SALES#
						actmove.credit 		= 0					#total_saleprice 
						actmove.debit 		= total_saleprice 	#0
						actmove.account_id  = sale_acct
						actmove.insert_move_line()
						
						actmove.credit 		= self.amount_total	#0
						actmove.debit 		= 0					#amount_total
						actmove.account_id  = trade_dr
						actmove.insert_move_line()
					
		'''

class dincelaccount_journal:
	quantity		= 1
	move_name		= ""
	credit			= 0
	debit			= 0
	account_id		= None
	company_id		= None
	ref_name 		= ""
	state_move		= ""
	date_invoice 	= None
	period_id 		= 0
	move_line_name  = ""
	state_line		= ""
	move_id			= 0
	partner_id		= 0
	journal_id		= 0
	
	def __init__(self, cr, uid, ids, context=None):
		self.cr 	 = cr
		self.uid 	 = uid
		self.ids 	 = ids
		self.context = context
		
	def insert_move(self):

		sql = "insert into account_move(ref,journal_id,name,company_id,state,date,period_id,partner_id) " \
			"	values('%s','%s','%s','%s','%s','%s','%s','%s')" \
			"" % (self.ref_name, self.journal_id, self.move_name, self.company_id, self.state_move, self.date_invoice, self.period_id, self.partner_id)
		self.cr.execute(sql)
		self.cr.commit()
		sql 	= "select id from account_move where ref='%s' and journal_id='%s'" %(self.ref_name, self.journal_id)
		self.cr.execute(sql)
		rowsk 	= self.cr.fetchone()
		if rowsk == None or len(rowsk)==0:
			return 0
		else:	
			self.move_id		=	rowsk[0]
			return self.move_id
			
	def insert_move_line(self):
	
		sql="insert into account_move_line(journal_id,move_id,account_id,credit,debit,company_id,partner_id,ref,period_id,date,name,quantity,state) "\
			"values('%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s')" \
			""%(self.journal_id, self.move_id, self.account_id, self.credit, self.debit, self.company_id, self.partner_id, self.ref_name, self.period_id, self.date_invoice, self.move_line_name, self.quantity, self.state_line)
		
		self.cr.execute(sql)
		self.cr.commit()
	
	