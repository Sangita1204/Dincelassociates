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
	def __init__(self, cr, uid, ids, context=None):
		
		self.cr 	 =cr
		self.uid 	 =uid
		self.ids 	 =ids
		self.context =context
		
		
	def insert_refund(self):
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
			sql 		= "select x_sale_acct_receive,x_sale_account,x_sale_account_tax,x_sale_cogs,x_sale_finished_goods,x_sale_cash_discount from dincelaccount_config_settings"
			self.cr.execute(sql)
			res 		= self.cr.fetchone()
			if res:
				trade_dr 	= (res[0])
				sale_acct 	= (res[1])
				sale_tax 	= (res[2])
				sale_cogs 	= (res[3])
				sale_goods 	= (res[4])
				sale_discount = (res[5])
				
				#not trade_dr or not sale_acct or not sale_tax or not sale_cogs or not sale_goods:#
				if trade_dr == None or sale_acct == None or sale_tax == None or sale_cogs == None or sale_goods == None:
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
					sql 	= "select account_id,sequence,invoice_id,price_unit,price_subtotal,company_id,product_id,partner_id,quantity,name,subtotal_wo_discount-price_subtotal as disct from account_invoice_line where invoice_id='%s'" % (self.invoice_ref)	
					self.cr.execute(sql)
					rows1 	= self.cr.dictfetchall()
					for row1 in rows1:
						price1 		= row1['price_subtotal']
						product_id1 = row1['product_id']
						quantity1	= row1['quantity']
						account_id1	= row1['account_id']
						disct		= row1['disct']
						
						if disct and disct>0:
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
	
	