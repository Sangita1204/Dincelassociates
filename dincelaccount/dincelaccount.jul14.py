from openerp.osv import osv, fields
from datetime import date
#from openerp.addons.base_status.base_state import base_state
import time 
import datetime
import csv
import logging
#from dinceljournal import dincelaccount_journal
from openerp import tools
from dincel_journal import dincelaccount_journal
from openerp.tools.translate import _
from openerp.exceptions import except_orm, Warning, RedirectWarning
from time import gmtime, strftime
_logger = logging.getLogger(__name__)

class dincelaccount_act_invoice(osv.Model):
	_inherit = "account.invoice"
	
	def invoice_sales_validate(self, cr, uid, ids, context=None):
		
		new_id		= ids[0]
		#ret = _obj.sales_invoice2journals(cr, uid, ids, new_id, context=context)
		#if ret and ret > 0:
		_obj 		= self.pool.get('account.invoice')
		invoice 	= _obj.browse(cr, uid, new_id, context=context)
		
		if invoice.type=="in_invoice":
			self.validate_purchase_invoice_dcs(cr, uid, ids, context)
		elif invoice.type=="in_refund":
			self.validate_purchase_invoice_dcs(cr, uid, ids, context)
		elif invoice.type=="out_refund":
			_name = self.pool.get('ir.sequence').get(cr, uid, 'refund.invoice')	#custom sequence number
			self.write(cr, uid, new_id, {'state':'open',  'number':_name,'internal_number':_name})	
			_obj = self.pool.get('dincelaccount.journal')
			ret  = _obj.sales_invoice2journals(cr, uid, ids, new_id, context=context) #cause invoice.number is referenced in journal name (account_move) for report
		elif invoice.type=="out_invoice":
			_name = self.pool.get('ir.sequence').get(cr, uid, 'invoice.number')	#custom sequence number
			self.write(cr, uid, new_id, {'state':'open',  'number':_name,'internal_number':_name})	
			_obj = self.pool.get('dincelaccount.journal')
			ret  = _obj.sales_invoice2journals(cr, uid, ids, new_id, context=context) #cause invoice.number is referenced in journal name (account_move) for report
		else:
			_logger.error("invoice_sales_validate:invalid invoice type.ret["+str(new_id)+"]")
		
	def invoice_purchase_validate(self, cr, uid, ids, context=None):
		_obj 		= self.pool.get('dincelaccount.journal')
		new_id		= ids[0]
		ret = _obj.sales_invoice2journals(cr, uid, ids, new_id, context=context)
		if ret and ret > 0:
			self.write(cr, uid, new_id, {'state':'open'})	
			
	def invoice_make_refund(self, cr, uid, new_id, _date_invoice, _comment, _journal_id, context=None):
		#_obj 		= self.pool.get('dincelaccount.journal')
		#new_id		= ids[0]
		#ret = _obj.sales_invoice2journals(cr, uid, ids, new_id ,context=context)
		#if ret and ret > 0:
		#	self.write(cr, uid, new_id, {'state':'open'})	
		#new_id		= ids[0]
		
		invalid		= True
		_objperiod 	= self.pool.get('account.period') 
		_objprod 	= self.pool.get('product.product')
		_obj 		= self.pool.get('account.invoice')
		#_obj_new	= self.pool.get('account.invoice')
		_obj_line 		= self.pool.get('account.invoice.line') 
		
		invoice 		= _obj.browse(cr, uid, new_id, context=context)
		_reference		= invoice.reference
		_company_id 	= invoice.company_id.id
		_partner_id 	= invoice.partner_id.id
		
		_amount_untaxed = invoice.amount_untaxed
		_amount_tax 	= invoice.amount_tax
		_amount_total 	= invoice.amount_total
		_account_id 	= invoice.account_id.id
		 
		_name			= ""#"REF_"+str(invoice.name)
		
		#_date_invoice	= datetime.datetime.today()
		#_comment		= ""
		_period_id		= _objperiod.find(cr, uid, _date_invoice, context=context)[0]
		vals={
			'type':'out_refund',	
			'state':'draft',
			'journal_id':_journal_id,
			'account_id':_account_id,
			'name':_name,
			'comment':_comment,
			'reference':_reference,
			'company_id':_company_id,
			'date_invoice':_date_invoice,
			'period_id':_period_id,
			'partner_id':_partner_id,
			'amount_tax':_amount_tax,
			'amount_total':_amount_total,
			'x_inv_type':'refund',
			'amount_untaxed':_amount_untaxed
		}
		
		_id = _obj.create(cr, uid, vals, context=context)
		
		if _id:
			for line in invoice.invoice_line:
				_price_subtotal	= line.price_subtotal
				_price_unit		= line.price_unit
				_product_id 	= line.product_id.id
				_qty			= line.quantity
				_origin			= line.origin
				_discount		= line.discount
				
				_name			= line.product_id.name
		
				vals = {
					'name':_name,
					'account_id':_account_id,
					'company_id':_company_id,
					'invoice_id':_id,
					'partner_id':_partner_id,
					'product_id':_product_id,
					'quantity':_qty,
					'price_subtotal':_price_subtotal,
					'price_unit':_price_unit,
					'origin':_origin,
					'discount':_discount,
				}
				if line.product_id.taxes_id:
					vals['invoice_line_tax_id'] = [(6, 0, line.product_id.taxes_id.ids)]
					
				_obj_line.create(cr, uid, vals, context=context)	
				
			 #---for auto tax calculation
			obj_inv = _obj.browse(cr, uid, _id, context)
			obj_inv.button_compute(True)	
			
		return _id
		
	def invoice_sales_validate_final(self, cr, uid, ids, context=None):
		new_id		= ids[0]
		_obj 		= self.pool.get('account.invoice')
		invoice 	= _obj.browse(cr, uid, new_id, context=context)
		'''
		_objperiod 		= self.pool.get('account.period') 
		_objperiodcr	= _objperiod.find(cr, uid, invoice.date_invoice, context=context)[0]
		if _objperiodcr:
			period_id 		= _objperiodcr #[0] in above code
		else:
			period_id 		= None
		if period_id:		
			inv = dincelaccount_invoice(cr, uid, ids, context=context)
			inv.invoice_ref = invoice.id
			inv.period_id	= period_id
			ret = inv.record_sale_journal()
			if ret == 1:
				self.write(cr, uid, new_id, {'state':'open'})
			else:
				_logger.error("invoice_sales_validate:ERROR_INVOICE-account.invoice.id["+str(new_id)+"]")
		else:
			_logger.error("invoice_sales_validate:ERROR_INVOICE-account.no.period_id.id["+str(new_id)+"]")'''
		
	def invoice_sales_validate2(self, cr, uid, ids, context=None):
		
		new_id	= ids[0]
		
		invalid		= True
		_objperiod 	= self.pool.get('account.period') 
		_objprod 	= self.pool.get('product.product')
		_obj 		= self.pool.get('account.invoice')
		invoice 	= _obj.browse(cr, uid, new_id, context=context)
		
		#out_invoice
		
		if invoice.journal_id:
			journal_id  = invoice.journal_id.id
			journal_ref = invoice.journal_id.code
		else:
			journal_id	= None
			journal_ref = ""
		
		invoice_name 	= journal_ref + "_" + str(invoice.id)
		company_id		= invoice.company_id.id
		date_invoice	= invoice.date_invoice
		partner_id		= invoice.partner_id.id
		state_line		= "valid"
		
		_objperiodcr	= _objperiod.find(cr, uid, date_invoice, context=context)[0]
		if _objperiodcr:
			period_id 	= _objperiodcr #[0] in above code
		else:
			period_id 	= None
		
		state_move			= "posted"	#"draft" #draft, posted [NOTE, if posted then it will automatically reported in Tiral Balance, General Ledger, reports, etc]
		
		all_items 	= []
		tax_name  	= "GST"
		sql 		= "select sale_receiveable,sale_sale,sale_sale_tax,sale_cogs,sale_finished_goods from dincelaccount_config_settings"
		cr.execute(sql)
		res = cr.fetchone()
		if journal_id and res:
			
			trade_dr 	= (res[0])
			sale_acct 	= (res[1])
			sale_tax 	= (res[2])
			sale_cogs 	= (res[3])
			sale_goods 	= (res[4])
			
			#not trade_dr or not sale_acct or not sale_tax or not sale_cogs or not sale_goods:#
			if trade_dr ==None or sale_acct==None or sale_tax==None or sale_cogs==None or sale_goods==None:
				invalid	= True
			else:
				invalid	= False
				total_costprice=0
				total_saleprice=0
				sql = "select account_collected_id,account_paid_id from account_tax where id='%s'"%(sale_tax)
				cr.execute(sql)
				rest = cr.fetchone()
				if rest:
					sale_tax_id=rest[0]
					sale_taxrefund=rest[1]
					
					#_logger.error("invoice_sales_validate:sale_tax_id["+str(sale_tax_id)+"]")	
				else:
					sale_tax_id=None
					sale_taxrefund=None
					
				for _line in invoice.invoice_line:
					#if _line.account_id:
					#acct_id = _line.account_id.id
					price 		= _line.price_subtotal
					product_id 	= _line.product_id.id
					
					_prod 		= _objprod.browse(cr, uid, product_id, context=context)
					quantity	= _line.quantity
					costprice 	= _prod.standard_price*quantity
					type		= _prod.type
					
					total_costprice += costprice
					
					found 		= False	
					if type == "service":
						if _line.account_id:	#_prod.property_income_account:
							acct_id	= _line.account_id.id	#_prod.property_income_account.id
							found 	= True	
							item	= [acct_id, price, _line.account_id.name, _line.account_id.code, costprice, type]
							all_items.append(item)
					if found == False:
						total_saleprice += price
						
					for _tax in _line.invoice_line_tax_id:
						tax_name	= _tax.name

				if period_id == None:
					invalid	= True
				else:
					
					actmove = dincelaccount_journal(cr, uid, ids, context=context)#(cr,journal_id)
					actmove.journal_id		= journal_id
					actmove.partner_id		= partner_id
					actmove.ref_name 		= invoice_name
					actmove.company_id 		= company_id
					actmove.state_move 		= state_move
					actmove.date_invoice 	= date_invoice
					actmove.period_id 		= period_id
					
					move_id = actmove.insert_move()
					
					if move_id > 0:

						actmove.move_id 		= move_id
						actmove.move_line_name 	= invoice_name
						actmove.state_line		= state_line
						
						#FINISHED GOODS#
						actmove.credit 		= total_costprice
						actmove.debit 		= 0
						actmove.account_id  = sale_goods
						actmove.insert_move_line()
						
						#COGS#
						actmove.credit 		= 0
						actmove.debit 		= total_costprice
						actmove.account_id  = sale_cogs
						actmove.insert_move_line()
							
						#--------------------------------------------------------------------------------------------------------------------------------------------------
						#TAX#
						if invoice.amount_tax > 0 and sale_tax_id:
							actmove.credit 		= invoice.amount_tax
							actmove.debit 		= 0
							actmove.account_id  = sale_tax_id
							actmove.insert_move_line()
							
						#SERVICES ETC. DELIVERY,ETC	
						for item in all_items:
							actmove.credit 		= item[1]
							actmove.debit 		= 0
							actmove.account_id  = item[0]
							actmove.insert_move_line()
							
						#SALES#
						actmove.credit 		= total_saleprice #invoice.amount_untaxed
						actmove.debit 		= 0
						actmove.account_id  = sale_acct
						actmove.insert_move_line()
						
						actmove.credit 		= 0
						actmove.debit 		= invoice.amount_total
						actmove.account_id  = trade_dr
						actmove.insert_move_line()
					
						
		
		'''str2=""
		#all_items.append(item)
		for item in all_items:
			str2 += "[item]["+str(item[4])+"]["+str(item[5])+"]"
						
		_logger.error("invoice_sales_validate:["+str2+"]")
		'''
		if invalid:
			_logger.error("invoice_sales_validate:ERROR_INVOICE-account.invoice.id["+str(new_id)+"]")	#str2 += "[ERROR_INVOICE]"	
		else:
			self.write(cr, uid, new_id, {'state':'open'})
			#str2 += "[GOOD_INVOICE]"	
		
		return {}
		
	def invoice_sales_validate1(self, cr, uid, ids, context=None):
		
		new_id		= ids[0]
		
		invalid		= True
		_objperiod 	= self.pool.get('account.period') 
		_objprod 	= self.pool.get('product.product')
		_obj 		= self.pool.get('account.invoice')
		invoice 	= _obj.browse(cr, uid, new_id, context=context)
		
		#out_invoice
		if invoice.journal_id:
			journal_id = invoice.journal_id.id
		else:
			journal_id=None
		
		invoice_name 	= "SAJ-" + str(invoice.id)
		company_id		= invoice.company_id.id
		date_invoice	= invoice.date_invoice
		partner_id		= invoice.partner_id.id
		state_line		= "valid"
		
		_objperiodcr	= _objperiod.find(cr, uid, date_invoice, context=context)[0]
		if _objperiodcr:
			period_id 	= _objperiodcr
		else:
			period_id 	= None
		
		state_move			= "posted"	#"draft" #draft, posted [NOTE, if posted then it will automatically reported in Tiral Balance, General Ledger, reports, etc]
		
		all_items 	= []
		tax_name  	= "GST"
		sql 		= "select x_sale_acct_receive,x_sale_account,x_sale_account_tax,x_sale_cogs,x_sale_finished_goods from dincelaccount_config_settings"
		cr.execute(sql)
		res 		= cr.fetchone()
		if journal_id and res:
			trade_dr 	= (res[0])
			sale_acct 	= (res[1])
			sale_tax 	= (res[2])
			sale_cogs 	= (res[3])
			sale_goods 	= (res[4])
			
			#not trade_dr or not sale_acct or not sale_tax or not sale_cogs or not sale_goods:#
			if trade_dr ==None or sale_acct==None or sale_tax==None or sale_cogs==None or sale_goods==None:
				invalid	= True
			else:
				invalid	= False
				total_costprice=0
				
				sql = "select account_collected_id,account_paid_id from account_tax where id='%s'"%(sale_tax)
				cr.execute(sql)
				rest = cr.fetchone()
				if rest:
					sale_tax_id=rest[0]
					sale_taxrefund=rest[1]
					#_logger.error("invoice_sales_validate:sale_tax_id["+str(sale_tax_id)+"]")	
				else:
					sale_tax_id=None
					sale_taxrefund==None
					
				for _line in invoice.invoice_line:
					#if _line.account_id:
					#acct_id = _line.account_id.id
					price 		= _line.price_subtotal
					product_id 	= _line.product_id.id
					_prod 		= _objprod.browse(cr, uid, product_id, context=context)
					quantity	= _line.quantity
					costprice 	= _prod.standard_price*quantity
					type		= _prod.type
					if type == "service":
						if _prod.property_income_account:
							acct_id	= _prod.property_income_account.id
							total_costprice += costprice
							item	= [acct_id, price, _line.account_id.name, _line.account_id.code, costprice, type]
							all_items.append(item)
					for _tax in _line.invoice_line_tax_id:
						tax_name	= _tax.name

				if period_id == None:
					invalid	= True
				else:
					
					sql = "insert into account_move(ref,journal_id,name,company_id,state,date,period_id) " \
						  "	values('%s','%s','%s','%s','%s','%s','%s')" \
						  ""%(invoice_name,journal_id,invoice_name,company_id,state_move,date_invoice,period_id)
					cr.execute(sql)
					cr.commit()
					sql = "select id from account_move where ref='%s' and journal_id='%s'" %(invoice_name,journal_id)
					cr.execute(sql)
					rowsk 		= cr.fetchone()
					if rowsk == None or len(rowsk)==0:
						invalid	= True
					else:	
					
						move_id=rowsk[0]
						
						#--------------------------------------------------------------------------------------------------------------------------------------------------
						if total_costprice > 0: 
							#STOCK#
							quantity=1
							tax_name=invoice_name		 
							credit	=total_costprice
							debit	=0
							sql="insert into account_move_line(journal_id,move_id,account_id,credit,debit,company_id,partner_id,ref,period_id,date,name,quantity,state) "\
								"values('%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s')" \
								""%(journal_id,move_id,sale_goods,credit,debit,company_id,partner_id,invoice_name,period_id,date_invoice,tax_name,quantity,state_line)
							cr.execute(sql)
							cr.commit()
							
							#COGS#
							quantity=1
							tax_name=invoice_name		 
							credit	=0
							debit	=total_costprice
							sql="insert into account_move_line(journal_id,move_id,account_id,credit,debit,company_id,partner_id,ref,period_id,date,name,quantity,state) "\
								"values('%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s')" \
								""%(journal_id,move_id,sale_cogs,credit,debit,company_id,partner_id,invoice_name,period_id,date_invoice,tax_name,quantity,state_line)
							cr.execute(sql)
							cr.commit()
							
							
						#--------------------------------------------------------------------------------------------------------------------------------------------------
						#TAX#
						if invoice.amount_tax > 0 and sale_tax_id:
							quantity=1
							tax_name=invoice_name		 
							credit	=invoice.amount_tax
							debit	=0
							sql="insert into account_move_line(journal_id,move_id,account_id,credit,debit,company_id,partner_id,ref,period_id,date,name,quantity,state) "\
								"values('%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s')" \
								""%(journal_id,move_id,sale_tax_id,credit,debit,company_id,partner_id,invoice_name,period_id,date_invoice,tax_name,quantity,state_line)
							cr.execute(sql)
							cr.commit()
							#_logger.error("invoice_sales_validate:["+sql+"]")	
						
						#SALES#
						quantity=1
						tax_name=invoice_name		 
						credit	=invoice.amount_untaxed
						debit	=0
						sql="insert into account_move_line(journal_id,move_id,account_id,credit,debit,company_id,partner_id,ref,period_id,date,name,quantity,state) "\
							"values('%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s')" \
							""%(journal_id,move_id,sale_acct,credit,debit,company_id,partner_id,invoice_name,period_id,date_invoice,tax_name,quantity,state_line)
						cr.execute(sql)
						cr.commit()
						
						#DEBTORS#
						quantity=1
						tax_name=invoice_name		#"/"
						credit	=0
						debit	=invoice.amount_total
						sql	="insert into account_move_line(journal_id,move_id,account_id,credit,debit,company_id,partner_id,ref,period_id,date,name,quantity,state) "\
							"values('%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s')" \
							""%(journal_id,move_id,trade_dr,credit,debit,company_id,partner_id,invoice_name,period_id,date_invoice,tax_name,quantity,state_line)
						cr.execute(sql)
						cr.commit()
		
		
		str2=""
		#all_items.append(item)
		for item in all_items:
			str2 += "[item]["+str(item[4])+"]["+str(item[5])+"]"
						
		#_logger.error("invoice_sales_validate:["+str2+"]")
		
		if invalid:
			_logger.error("invoice_sales_validate:[ERROR_INVOICE]")	#str2 += "[ERROR_INVOICE]"	
		else:
			self.write(cr, uid, new_id, {'state':'open'})
			#str2 += "[GOOD_INVOICE]"	
		
		return {}
		
	def invoice_print_dcs(self, cr, uid, ids, context=None):	
		if context is None:
			context = {}
		#datas = {'ids': context.get('active_ids', [])}
		datas = {'ids': []}
		datas['form']  = self.read(cr, uid, ids, context=context)[0]
		#_logger.error("invoice_print_pdf_dcs:datas["+str(datas)+"]")
		return self.pool['report'].get_action(cr, uid, [], 'account.report_partner_invoice', data=datas, context=context)			
	
	def invoice_print_pdf_dcs(self, cr, uid, ids, context=None):	
		if context is None:
			context = {}
		datas = {'ids': context.get('active_ids', [])}
	 
		datas['form']  = self.read(cr, uid, ids, context=context)[0]
		
		return self.pool['report'].get_action(cr, uid, [], 'account.report_partner_invoice_pdf', data=datas, context=context)			
		#return {}	
		
	def invoice_sales_refund2(self, cr, uid, ids, context=None):	
		sql= "select id from account_journal where type='sale_refund'"
		#sql = "select id from account_move where ref='%s' and journal_id='%s'" %(invoice_name,journal_id)
		cr.execute(sql)
		rowsk 		= cr.fetchone()
		if rowsk == None or len(rowsk)==0:
			invalid	= True
		else:	
			journal_id=rowsk[0]
			
		return {}	
	
	def cr_limit_over(self, cr, uid, ids, values, arg, context):
			
		x={}
		_over=False
		for record in self.browse(cr, uid, ids):
			if record.partner_id and record.partner_id.credit_limit>0:
				sql ="select sum(amount_total) from sale_order where partner_id='%s' and x_status='open'" % (record.partner_id.id)
				cr.execute(sql)
				rows = cr.fetchone()
				if rows == None or len(rows)==0:
					_over=False
				else:
					 if rows[0]!=None:
						if record.partner_id.credit_limit<rows[0]:
							_over=True
		x[record.id] = _over 
		return x
		
	_columns = {
		'x_invoice_ref': fields.many2one('account.invoice', 'Origin Invoice', help="Origin of invoice for refund, etc."),
		'x_cr_limit_over': fields.function(cr_limit_over, method=True, string='Cr Limit', type='boolean'),
		'x_full_delivered':fields.boolean('Full Delivered'),
		'x_sale_order_id': fields.many2one('sale.order','Sale Order Reference'),
		'x_project_id': fields.many2one('res.partner','Project / Site'),
		'x_credit_limit': fields.related('partner_id', 'credit_limit', type='float', string='Credit Limit',store=False),
		'x_inv_type':fields.selection([
			('none', 'None'),
            ('deposit', 'Deposit'),
            ('balance', 'Balance'),
			('full', 'FULL'),
			('refund', 'Refund')
			], 'Invoice Type'),
	}
	
	def button_sales_orders(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		for record in self.browse(cr, uid, ids, context=context):	
			partner_id=record.partner_id.id 
			obj = self.pool.get('sale.order')
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
			
class dincelaccount_act_invoice_line(osv.Model):
	_inherit = "account.invoice.line"
	_columns={
		'x_qty_left': fields.float('Qty Left', digits=(16,2)),
		'x_region_id': fields.many2one('dincelaccount.region', 'A/c Region'),
	}
	
class dincelaccount_sale_order(osv.Model):
	_inherit="sale.order"
	
	def onchange_partner_id_v2(self, cr, uid, ids, part, project_id, context=None):
		if not part:
			return {'value': {'partner_invoice_id': False, 'partner_shipping_id': False,  'payment_term': False, 'fiscal_position': False}}

		part = self.pool.get('res.partner').browse(cr, uid, part, context=context)
		addr = self.pool.get('res.partner').address_get(cr, uid, [part.id], ['delivery', 'invoice', 'contact'])
		pricelist = part.property_product_pricelist and part.property_product_pricelist.id or False
		payment_term = part.property_payment_term and part.property_payment_term.id or False
		dedicated_salesman = part.user_id and part.user_id.id or uid
		val = {
			'partner_invoice_id': addr['invoice'],
			'partner_shipping_id': addr['delivery'],
			'payment_term': payment_term,
			'user_id': dedicated_salesman,
			'x_credit_limit': part.credit_limit,
			}
		delivery_onchange = self.onchange_delivery_id(cr, uid, ids, False, part.id, addr['delivery'], False,  context=context)
		val.update(delivery_onchange['value'])
		if pricelist:
			val['pricelist_id'] = pricelist
		sale_note = self.get_salenote(cr, uid, ids, part.id, context=context)
		if sale_note: val.update({'note': sale_note})  
		
		c_ids3  = []
		my_list = []
		#obj		= self.pool.get('res.partner').browse(cr,uid,part.id,context=context)
		for item in part.x_role_site_ids:
			my_list.append(item.id) 
			c_ids3 = c_ids3 + self.pool.get('res.partner').search(cr, uid, [('parent_id', '=', item.id)], context=context)
		
		
		c_ids1 = self.pool.get('res.partner').search(cr, uid, [('parent_id', '=', part.id)], context=context)
		if project_id:
			c_ids2 = self.pool.get('res.partner').search(cr, uid, [('parent_id', '=', project_id)], context=context)
			c_ids1 = c_ids1+ c_ids2
		else:
			c_ids1 = c_ids3
			
		if len(c_ids1) > 0:
			domain  = {'x_project_id': [('id','in', (my_list))],'x_contact_id': [('id','in', (c_ids1))]}#domain['x_contact_id']=[('id','in', (my_list))]
		else:
			domain  = {'x_project_id': [('id','in', (my_list))]}
			
		return {'value': val,'domain': domain}
		
	def onchange_projectsite(self, cr, uid, ids, project_id, context=None):
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
				
			val['x_street']=street	
			if _obj.state_id:
				val['x_state_id']=_obj.state_id.id
			if _obj.country_id:
				val['x_country_id']=_obj.country_id.id	
			return {'value': val}
			
	def change_payment_term(self, cr, uid, ids, partner_id=False, payment_term = False, dt_sale = False, context=None):
		#order_id	= None
		rate		= None
		partner_obj = self.pool.get('res.partner')
		product_obj = self.pool.get('product.product')
		term_obj 	= self.pool.get('account.payment.term')
		
		rate_obj 	= self.pool.get('dincelcrm.customer.rate')
		term_obj 	= term_obj.browse(cr, uid, payment_term)
		code 	 	= term_obj.x_payterm_code
	 
		if code:	
			rate_id = rate_obj.find(cr, uid, dt_sale, partner_id, context=context)
			if rate_id:
				rate_id	 = rate_id[0]
				rate_obj =  rate_obj.browse(cr, uid, rate_id)
				if rate_obj:
					if code == "30EOM":
						rate = rate_obj.rate_acct
					elif code == "COD":
						rate = rate_obj.rate_cod
				
		if rate:	
			for record in self.browse(cr, uid, ids, context=context):
				for line in record.order_line:
					if line.product_id.x_is_main =='1':
						line.price_unit = rate
					#_logger.error("change_payment_term:line.price_unit["+str(line.price_unit)+"]")
	def has_custom_profile(self, cr, uid, ids, values, arg, context):
		x={}
		has_custom='0'
		for record in self.browse(cr, uid, ids):
			#check if deposit invoice already created. if then do not display create button
			sql = "select p.id from product_product p,product_template t,account_invoice o,account_invoice_line l where o.id=l.invoice_id and p.id=l.product_id and p.product_tmpl_id=t.id and t.x_prod_cat='deposit' and o.x_sale_order_id='%s' "% (record.id)
			cr.execute(sql)
			#_logger.error("change_payment_term:line.sql_sql["+str(sql)+"]")
			rows1 = cr.fetchall()
			if len(rows1) > 0:
				has_custom = '0'
			else:	
				sql = "select p.id  from product_product p,product_template t,sale_order_line o where p.id=o.product_id and p.product_tmpl_id=t.id and t.x_prod_cat='customlength' and o.order_id='%s' " % (record.id)
				cr.execute(sql)
				rows = cr.fetchall()
				if len(rows) > 0:
					has_custom = '1'
				else:
					has_custom = '0'
			x[record.id] = has_custom 
		return x
		
	def cr_limit_over(self, cr, uid, ids, values, arg, context):
			
		x={}
		_over=False
		for record in self.browse(cr, uid, ids):
			if record.partner_id and record.partner_id.credit_limit>0:
				sql ="select sum(amount_total) from sale_order where partner_id='%s' and x_status='open'" % (record.partner_id.id)
				cr.execute(sql)
				rows = cr.fetchone()
				if rows == None or len(rows)==0:
					_over=False
				else:
					 if rows[0]!=None:
						if record.partner_id.credit_limit<rows[0]:
							_over=True
		x[record.id] = _over 
		return x
		
	def tot_invoiced(self, cr, uid, ids, values, arg, context):
		x={}
		tot_amt = 0
		#id = ids[0]
		obj_inv = self.pool.get('account.invoice')
		args = [("x_sale_order_id", "=", ids[0])]
		#result = obj_inv.search(cr, uid, args, context=context)
		i=0
		for sale_id in obj_inv.search(cr, uid, args, context=context):
			#i+=1
			#_logger.error("change_payment_term:line.sale_id_sale_id["+str(sale_id)+"]["+str(i)+"]")
			_inv 	= obj_inv.browse(cr, uid, sale_id, context)
			tot_amt	+= _inv.amount_total
			
		for record in self.browse(cr, uid, ids):
			x[record.id]= tot_amt
		return x
	
	def tot_balance(self, cr, uid, ids, values, arg, context):
		x={}
		#tot_amt = 0
		#id = ids[0]
		for record in self.browse(cr, uid, ids):
			x[record.id]= record.amount_total-record.x_tot_invoiced
		return x
	
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

				view_id 		= self.pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'dincelstock.delivery.form.view')], limit=1) 	
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
		
	_columns={
		'x_account_ids': fields.one2many('account.invoice', 'x_sale_order_id','Invoices'),
		'x_credit_limit': fields.related('partner_id', 'credit_limit', type='float', string='Credit Limit',store=False),
		'x_qty_tot_profile': fields.float('Total Profile Qty', digits=(16,2)),
		'x_origin_order': fields.many2one('dincelsale.ordersale','Origin Order'),
		'x_cr_limit_over': fields.function(cr_limit_over, method=True, string='Cr Limit', type='boolean'),
		'x_has_custom': fields.function(has_custom_profile, method=True, string='Has custom profile', type='char'),
		'x_tot_invoiced': fields.function(tot_invoiced, method=True, string='Total Invoiced',type='float'),
		'x_tot_balance': fields.function(tot_balance, method=True, string='Balance Amount',type='float'),
		'x_pickinglist_ids': fields.one2many('dincelstock.pickinglist', 'pick_order_id','Deliveries'),
		'x_project_id': fields.many2one('res.partner','Project / Site'),		
		'x_contact_id': fields.many2one('res.partner','Contact Person'),		
		'x_quote_id': fields.many2one('account.analytic.account','Quote'),		
		'x_warehouse_id': fields.many2one('stock.warehouse','Dispatch Location'),		
		'x_street': fields.char('Street'),	
		'x_postcode': fields.char('Postcode'),	
		'x_suburb': fields.char('Suburb'),	
		'x_state_id': fields.many2one('res.country.state','State'),		
		'x_country_id': fields.many2one('res.country','Country'),
		'x_pudel':fields.selection([
			('pu','Pickup'),
			('del','Delivery'),
			], 'Pickup/Delivery'),
		'x_ac_status':fields.selection([
			('hold','Hold'),
			('open','Open'),
			('part','Partial'),
			('paid','Paid'),
			], 'A/c Status'),	
		'x_prod_status':fields.selection([
			('queue','Queue'),
			('part','Partial'),
			('complete','Complete'),
			], 'Production Status'),		
		'x_del_status':fields.selection([
			('none','None'),
			('part','Partial'),
			('delivered','Delivered'),
			], 'Delivery Status'),		
		'x_status':fields.selection([ #as in dcs open /close/ cancel
			('open','Open'),
			('close','Closed'),
			('cancel','Cancelled'),
			], 'Status'),	
		'x_dt_request':fields.date("Requested Date"),		
	}
	_defaults = {
		'x_status': 'open',
		'x_ac_status': 'hold',
	}
	
	def unlink(self, cr, uid, ids, context=None, check=True):
		context = dict(context or {})
		if context is None:
			context = {}
		lids 	= self.pool.get('account.invoice').search(cr,uid,[('x_sale_order_id','=',ids[0])])
		if len(lids)>0:
			raise Warning(_('You cannot delete a sales order after an invoice has been generated.'))
			#raise osv.except_osv(_('Error!'), _('You cannot delete a sales order after an invoice has been generated.'))
		else:	 
			result = super(dincelaccount_sale_order, self).unlink(cr, uid, ids, context)
			return result
		
	def last_day_of_month(self, any_day):
		next_month = any_day.replace(day=28) + datetime.timedelta(days=4)  # this will never fail
		return next_month - datetime.timedelta(days=next_month.day)
	
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
				
	def create_balance_invoice(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		obj_inv 	= self.pool.get('account.invoice')	
		obj_invline	= self.pool.get('account.invoice.line')
		product_obj = self.pool.get('product.product')	
		tot_price = 0
		
		ar_items_done 	= {}
		ar_items_rem  	= {}
		
		tot_qty_rem 	= 0
		 
		#sname = None
		for record in self.browse(cr, uid, ids, context=context):	
			#gets all invoiced items qty
			sql = "select * from account_invoice_line where origin='%s' " % record.name
			cr.execute(sql)
			rows1 	= cr.dictfetchall()
			for row1 in rows1:
				qty = row1['quantity']
				product_id = row1['product_id']
				if ar_items_done.has_key(product_id) == False:
					ar_items_done[product_id] = qty
				else:
					ar_items_done[product_id] += qty
			#now calculate the net remaining qty		
			for line in record.order_line:
				qty = line.product_uom_qty
				product_id = line.product_id.id
				if ar_items_done.has_key(product_id):
					qty = qty - ar_items_done[product_id]
			
				tot_qty_rem += qty		
			
			#only if any remain qty is greater than zero
			if tot_qty_rem > 0 :
				
				vals = {
					'x_sale_order_id': record.id,
					'x_inv_type':'balance',
                    'origin': record.name,
                    'reference': record.name,
                    'partner_id': record.partner_id.id,
					#'internal_number': record.name, #cannot delete once this value is recorded
					'section_id': 1,
                    'type': 'out_invoice',
					'account_id':record.partner_id.property_account_receivable.id
					}
			
				vals['date_invoice']=datetime.datetime.now() 
				vals['date_due']=vals['date_invoice']
				#_logger.error("invoice_sales_validate.payment_termpayment_term["+str(record.payment_term)+"]")
				if record.payment_term: 
					
					code 	 = record.payment_term.x_payterm_code
					vals['payment_term']=record.payment_term.id
					if code:	
						if code == "30EOM":
							dt1=vals['date_invoice'] + datetime.timedelta(365/12)
							vals['date_due']= self.last_day_of_month(dt1)
							_logger.error("invoice_sales_validate.x_payterm_codex_payterm_code["+str(dt1)+"]["+str(vals['date_due'])+"]")
							#date_after_month = datetime.today()+ relativedelta(months=1) 
							#elif code == "COD":
							#	vals['date_due']=vals['date_invoice']
							
				proj_id = record.x_project_id and record.x_project_id.id  or False		
				if proj_id:
					vals['x_project_id']=proj_id
					
				#first create the invoice record
				inv_id = obj_inv.create(cr, uid, vals, context=context)
				
				#now loop throught all item lines and create invoice line if net qty remaining is greater than zero
				for line in record.order_line:
					qty = line.product_uom_qty
					product_id = line.product_id.id
					if ar_items_done.has_key(product_id):
						qty = qty - ar_items_done[product_id]		
					if qty > 0:
						
						vals = {
							'product_id': product_id,
							'quantity': qty,
							'invoice_id': inv_id,
							'origin': record.name,
							'discount':line.discount,
							'price_unit': line.price_unit,
							'price_subtotal': line.price_unit*qty,
						}
						vals['name']= line.product_id.name
						
						if line.x_region_id:
							vals['x_region_id']= line.x_region_id.id	
							 
						#_logger.error("change_payment_termvalsvals["+str(vals)+"]")
						
						if line.product_id.taxes_id:
							vals['invoice_line_tax_id'] = [(6, 0, line.product_id.taxes_id.ids)]
									
						obj_invline.create(cr, uid, vals, context=context)
				
				#check if deposit items exists	
				product_id =  product_obj.find_deposit_product(cr, uid, context=context)
				if product_id:
					#_logger.error("change_payment_term:line.product_id["+str(product_id)+"]")
					product_id	 = product_id[0]
					product_obj  = product_obj.browse(cr, uid, product_id, context)
					tot_amt = 0
					args = [("product_id", "=", product_id),("origin", "=", record.name)]
					#now find the item in the invoice line list
					for line_id in obj_invline.search(cr, uid, args, context=context):
						_invl 	 = obj_invline.browse(cr, uid, line_id, context)
						tot_amt	+= _invl.price_subtotal
						#for _tax in _invl.invoice_line_tax_id:
						#	tot_amt	+= _tax.amount * _invl.price_subtotal
					#if it has deposit invoice. then create invoice line for balancing with negative value	
					if tot_amt > 0:	
						vals = {
							'product_id': product_id,
							'quantity': '1',
							'invoice_id': inv_id,
							'origin': record.name,
							'price_unit': -tot_amt,
							'price_subtotal': -tot_amt,
						}
						
						vals['name']	= product_obj.name
						#if x_region_id:
						#	vals['x_region_id']	= x_region_id
						#_logger.error("change_payment_term:line.tax_id_tax_id["+str(product_obj.taxes_id)+"]")
						if product_obj.taxes_id:
							vals['invoice_line_tax_id'] = [(6, 0, product_obj.taxes_id.ids)]
									
						obj_invline.create(cr, uid, vals, context=context)
				else:
					#no deposit invoice
					self.write(cr, uid, [record.id], {'state':'progress'})	
					
				#for taxes reset
				obj_inv = self.pool.get('account.invoice')
				obj_inv = obj_inv.browse(cr, uid, inv_id, context)
				obj_inv.button_compute(True) #For taxes
				
				#--------------
				if record.x_ac_status==None or record.x_ac_status=="hold":
					self.write(cr, uid, [record.id], {'x_ac_status':'open'})	
				#--------------
				
				#str1 = "amttax["+str(obj_inv.amount_tax) + "]amtuntax["+str(obj_inv.amount_untax) + "] calculated["+str(obj_inv.amount_untax*0.1) + "]" 
				#_logger.error("change_payment_term:tax_id_tax_id_tax_id_tax_id["+str1+"]")
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
		obj_inv 	= self.pool.get('account.invoice')	
		obj_invline	= self.pool.get('account.invoice.line')
		product_obj = self.pool.get('product.product')	
		tot_price = 0
	 
		for record in self.browse(cr, uid, ids, context=context):	
			for line in record.order_line:
				if line.product_id.x_prod_cat =='customlength':
					qty = line.product_uom_qty
					price_unit=line.price_unit 
					 
					tot_price += qty*price_unit
		if tot_price > 0:
			tot_price = 0.33*tot_price #33 % of custom length
			#_logger.error("change_payment_term:line.tot_price["+str(tot_price)+"]")
			product_id =  product_obj.find_deposit_product(cr, uid, context=context)
			if product_id:
				#_logger.error("change_payment_term:line.product_id["+str(product_id)+"]")
				product_id	 = product_id[0]
				product_obj  =  product_obj.browse(cr, uid, product_id, context)
				vals = {
					'x_sale_order_id': record.id,
					'x_inv_type':'deposit',
                    'origin': record.name,
                    'reference': record.name,
                    'partner_id': record.partner_id.id,
					#'internal_number': record.name,
					'section_id': 1,
                    'type': 'out_invoice',
					'account_id':record.partner_id.property_account_receivable.id
					}
			
				vals['date_invoice']=datetime.datetime.now() 
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
				 
				#_logger.error("change_payment_term:line.tax_id_tax_id["+str(product_obj.taxes_id)+"]")
				
				if product_obj.taxes_id:
					vals['invoice_line_tax_id'] = [(6, 0, product_obj.taxes_id.ids)]
							
				obj_invline.create(cr, uid, vals, context=context)
				#for taxes
				#obj_inv = self.pool.get('account.invoice')
				obj_inv = obj_inv.browse(cr, uid, inv_id, context)
				obj_inv.button_compute(True) #For taxes
				
				#--------------
				val_sts={'state':'progress'}
				if  record.x_ac_status==None or record.x_ac_status=="hold":
					val_sts['x_ac_status']='open'
					#self.write(cr, uid, [record.id], {'x_ac_status':'open'})	
				self.write(cr, uid, [record.id], val_sts)		
				#--------------
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
				#return inv_id
		return False		
	
	def create_mo_order_dcs(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		#o_bom 	= self.pool.get('mrp.bom')	
		#o_prd 	= self.pool.get('mrp.production')	
		
		
class dincelaccount_sale_order_line(osv.Model):
	_inherit="sale.order.line"
		
	def product_qty_changed(self, cr, uid, ids, product, qty=0,length=0, partner_id=False, payment_term = False, dt_sale = False,loc_id =False, context=None):
		#result = super(dincelaccount_sale_order_line, self).product_qty_changed(cr, uid, ids, product, qty=qty, partner_id=partner_id, payment_term = payment_term, dt_sale = dt_sale, context=context)
		#result = super(dincelaccount_sale_order_line, self).product_qty_changed(cr, uid, ids, product, qty=0, partner_id=False, payment_term = False, dt_sale = False, context=None)
		result 		= {}	
		context 	= context or {}

		if not partner_id:
			raise osv.except_osv(_('No Customer Defined!'), _('Before choosing a product,\n select a customer in the sales form.'))
		
		warning 	= False
		
		domain 		= {}
		code 		= None
		
		order_id	= None
		#tot_qty  	= qty
		qty_lm 		= qty
		
		for record in self.browse(cr, uid, ids, context=context):
			order_id = record.order_id.id
			#tot_qty += record.product_uom_qty
			
		partner_obj = self.pool.get('res.partner')
		product_obj = self.pool.get('product.product')
		term_obj 	= self.pool.get('account.payment.term')
		
		rate_obj 	= self.pool.get('dincelcrm.customer.rate') 
		
		order_obj 	= self.pool.get('sale.order')
		order_obj 	= order_obj.browse(cr, uid, order_id)
		
		#loc_ob 	= self.pool.get('stock.warehouse')
		#if loc_id:
		#	loc_ob 	= loc_ob.browse(cr, uid, loc_id)
			
		partner 	= partner_obj.browse(cr, uid, partner_id)
		lang 		= partner.lang
		context 	= {'lang': lang, 'partner_id': partner_id}
		context_partner = {'lang': lang, 'partner_id': partner_id}
		
		warning_msgs = ''
		product_obj  = product_obj.browse(cr, uid, product, context=context_partner)
		
		#for line in order_obj.order_line:
		#	if line.product_id.x_is_calcrate:
		#		if line.product_id.id != product:
		#			tot_qty +=line.product_uom_qty
		#_logger.error("product_qty_changed:line.tot_qty.1["+str(tot_qty)+"]")
		#order_obj.x_qty_tot_profile = tot_qty
		#result['x_qty_tot_profile']= tot_qty
		
		#----------------------------------------------------------
		#converting [LM] into [M2]  LM->M2  LMtoM2 LM2M2
		#----------------------------------------------------------
		if product_obj.x_is_main=='1':#x_is_calcrate:
			if product_obj.x_stock_width and product_obj.x_stock_width>0:
				qty_lm = round(((length*qty*0.001)*(product_obj.x_stock_width/1000)),4) 	#M2 
			else:	
				qty_lm = round(((length*qty*0.001)/3),4) 	#M2 
			if payment_term:
				term_obj = term_obj.browse(cr, uid, payment_term)
				code 	 = term_obj.x_payterm_code
				found_rate = False
				if code:	
					rate_id = rate_obj.find(cr, uid, dt_sale, partner_id, context=context)
					if rate_id: #customer rate is present #-----------
						rate_id	 = rate_id[0]
					
						rate_obj =  rate_obj.browse(cr, uid, rate_id)
						
						if code == "30EOM":
							result.update({'price_unit': rate_obj.rate_acct})
							found_rate = True #order_obj.button_dummy()
						elif code == "COD":
							result.update({'price_unit': rate_obj.rate_cod})
							found_rate = True #
						
				if found_rate == False:
					#rate_id = None
					if loc_id:
						sql = "select rate1,rate2,rate3,id from dincelcrm_quote_rates where %s between from_val and to_val" % qty_lm
						cr.execute(sql)
						rows = cr.fetchone()
						if rows and len(rows) > 0:
							rate1= rows[0]
							rate3= rows[2]
							sql = "select rate1,rate2,rate3,id from dincelcrm_location_rates where location_rate_id='%s' and warehouse_id='%s'" % (str(rows[3]),str(loc_id))
							cr.execute(sql)
							row2 = cr.fetchone()
							if row2 and len(row2) > 0:
								rate1 = rate1+float(row2[0])
								rate3 = rate3+float(row2[2])	
								
							if code and code == "30EOM":
								result.update({'price_unit': rate1})
								#order_obj.button_dummy()
							else:#elif code == "COD":
								result.update({'price_unit': rate3})
		else:
			#if length>0.0001:
			#	qty_lm = (length*qty*0.001)
			#else:
			#	qty_lm = qty
			#_logger.error("product_qty_changed:line.product_obj.x_prod_cat["+str(product_obj.x_prod_cat)+"]["+str(product)+"]["+str(qty)+"]")
			#if product_obj.x_prod_cat=="freight":
			#	qty_lm = qty
				#result.update({'x_order_qty': qty})
			qty_lm = qty	
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
		return {'value': result, 'domain': domain, 'warning': warning}
		
	_columns = {
		'x_order_length':fields.float("Ordered Len"),	
		'x_order_qty':fields.float("Ordered Qty"),	
		'x_region_id': fields.many2one('dincelaccount.region', 'A/c Region'),
	}	
	_defaults = {
		'x_order_qty': 1
	}	
	
class dincelaccount_product_template(osv.Model):
	_inherit="product.template"
	
	def is_main_profile(self, cr, uid, ids, values, arg, context):
		x={}
		is_main='0'
		for record in self.browse(cr, uid, ids):
			if record.x_prod_cat:
				if record.x_prod_cat=='stocklength'	or record.x_prod_cat=='customlength':
					is_main = '1'
				else:	
					is_main = '0'
			x[record.id] = is_main 
		return x
		
	_columns={
		'x_is_calcrate': fields.boolean('Is Main Profile'), #not in use, due to -> is_main_profile()
		'x_prod_cat': fields.selection([
            ('none', 'None'),
            ('deposit', 'Deposit'),
            ('stocklength', 'Stock Length'),
            ('customlength', 'Custom Length'),
            ('accessories', 'Accessories'),
            ('freight', 'Freight'),
            ], 'Product Category'),
		'x_stock_length': fields.float("Stock Length"),	
		'x_stock_width': fields.float("Width"),	
		'x_stock_height': fields.float("Depth"),	
		'x_is_main': fields.function(is_main_profile, method=True, string='Is Main', type='char'),
		'x_bom_cat': fields.selection([
            ('none', 'None'),
            ('material', 'Material'),
            ('labour', 'Labour'),
            ('overheads', 'Overheads'),
            ], 'BOM Category'),
	}
	
	_defaults = {
		'x_bom_cat': 'none',
		'x_prod_cat': 'none',
	}
	

class dincelaccount_product_product(osv.Model):
	_inherit="product.product"	
	def find_deposit_product(self, cr, uid, context=None):
		if context is None: context = {}
		#result = []
		args = [("x_prod_cat", "=", "deposit")]
		result = self.search(cr, uid, args, context=context)
		return result
	
	
class dincelaccount_supplierinfo(osv.Model):
	_inherit="product.supplierinfo"
	_columns={
		'x_cost_price': fields.float("Supplier Cost"),	
	}
	
class dincelaccount_payment_term(osv.Model):
	_inherit="account.payment.term"
	_columns={
		'x_payterm_code': fields.char('Code',size=10),
	}
class dincelaccount_partner_bank(osv.Model):
	_inherit="res.partner.bank"
	_columns={
		'x_bank_userid': fields.char('Bank User Id',size=6),
		'x_bank_bsb': fields.char('Bank BSB',size=7),
	}
	
class dincelaccount_company(osv.Model):
	_inherit="res.company"
	_columns={
		'x_site_address': fields.char('Site Address'),
	}

class dincelaccount_partner_due(osv.osv):
    _name = "dincelaccount.partner.due"
    
    _auto = False
    
    _columns = {
        'partner_id': fields.many2one('res.partner', 'Partner', readonly=True),
        'sumtax': fields.float('Total Tax', readonly=True),
		'sumuntax': fields.float('Total Untaxed', readonly=True),
		'sumtot': fields.float('Total Due', readonly=True),
		'subtot': fields.float('Subtotal', readonly=True),
    }
    
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'dincelaccount_partner_due')
        cr.execute("""
            create or replace view dincelaccount_partner_due as (
                select min(a.id) as id,
                  a.partner_id,
				  sum(a.amount_tax) as sumtax,
				  sum(a.amount_untaxed) as sumuntax,
				  sum(a.amount_total) as sumtot,
				  sum(a.subtotal_wo_discount) as subtot 
				  from account_invoice a 
				  where a.type='out_invoice' and a.state='open'
				  group by a.partner_id         )
			""")	
	