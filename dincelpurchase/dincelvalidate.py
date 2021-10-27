from openerp.osv import fields, osv
from openerp.tools.translate import _
from datetime import date

import time 
import datetime
import logging
from openerp.tools.translate import _


from time import gmtime, strftime
_logger = logging.getLogger(__name__)


class dincelpurchase_validate_invoice(osv.osv_memory):
	_name 		= "dincelpurchase.validate.invoice"
	#validate qty variance invoices
	def validate_invoice_qtyvariance(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
			
		for record in self.browse(cr, uid, ids, context=context):
			invoice_id 	= record.invoice_id
			date_invoice = record.date_invoice
			bal_coming = record.bal_coming
			
			_operiod 	= self.pool.get('account.period') 
			_oprod 		= self.pool.get('product.product')
			_oglcodes 	= self.pool.get('dincelaccount.config.settings')
			_id			= _oglcodes.search(cr, uid, [], limit=1) 	
			if _id:
				_oglcodes 	= _oglcodes.browse(cr, uid, _id, context=context)
				#_oglcodes 	= self.pool.get('dincelaccount.config.settings').browse(cr, uid, 1, context=context)
			else:
				raise osv.except_osv(_('No account settings!'), _('No account settings found!'))
			
			_oacct			= self.pool.get('account.move')
			
			_opurline 		= self.pool.get('purchase.order.line')
			_opur 			= self.pool.get('purchase.order')
			_ostpk 			= self.pool.get('stock.picking')
			acct_disc_rx 	= False
			acct_stock 		= False
			acct_good2inv 	= False
			acct_trade_cr	= False
			acct_pur_var	= False
			acct_tax		= False
			acct_qty_var	= False
			if _oglcodes:
				acct_stock 	= _oglcodes.stock_inventory.id or False #raw materials
				_tax 		= _oglcodes.buy_payable_tax
				if _tax:
					_taxobj = self.pool.get('account.tax').browse(cr, uid, _tax.id, context=context)
					acct_tax	= _taxobj.account_collected_id.id or False
				acct_good2inv 	= _oglcodes.stock_received_notinvoiced.id or False
				acct_disc_rx 	= _oglcodes.buy_cash_discount.id or False
				acct_trade_cr	= _oglcodes.buy_payable.id or False
				acct_qty_var	= _oglcodes.stock_purchase_variance.id or False
				acct_pur_var	= _oglcodes.stock_price_variance.id or False
				#acct_freight	= _oglcodes.sale_freight and _oglcodes.sale_freight.id  or False	
				
			inv_id 		=None
			amt_stock 	=0
			origin 		=""
			price_diff	=0
			price_inv	=0
			price_disc	=0
			price_tax	=0
			price_grnyi =0 #Goods Reecived Not Yet Invoiced
			price_freight=0
			po=None
			
			origin 		= invoice_id.origin
			inv_id  	= invoice_id.id
			partner_id	= invoice_id.partner_id.id
			company_id	= invoice_id.company_id.id
			price_inv 	= invoice_id.amount_untaxed
			price_tax	= invoice_id.amount_tax
			
			ar_items_qty 	= {}
			#ar_items_price 	= {}
			idstk		= _ostpk.search(cr, uid, [('name', '=', origin)], limit=1)
			if idstk:
				_ostpk  = _ostpk.browse(cr, uid, idstk[0], context=context)
		
				for line in _ostpk.move_lines:
					qty			= line.product_uom_qty
					product_id 	= line.product_id
					
					if ar_items_qty.has_key(product_id.id) == False:
						ar_items_qty[product_id.id] = qty
					else:
						ar_items_qty[product_id.id] += qty	
		
				for line in invoice_id.invoice_line:
					qty			= line.quantity
					product_id 	= line.product_id
					price_unit2 = line.price_unit
					price_unit	= line.product_id.standard_price
					if product_id.x_prod_cat=="freight":
						price_freight=price_freight+line.price_subtotal
					else:
						#_logger.error_logger.error("dincelpurchase_move_lines_id:["+str(line.id)+"]["+str(qty)+"]")	
						#_itemid 	= _opurline.search(cr, uid, [('product_id', '=', product_id.id),('order_id', '=', po[0])], limit=1)#[0]
						#if _itemid:
						#	_item 	= _opurline.browse(cr, uid, _itemid[0], context=context)
						#	price_unit = _item.price_unit
						#else:
						#	price_unit = 0
						price_diff  = price_diff + ((price_unit2-price_unit)*qty)	
						#price_inv	= price_inv+line.price_subtotal	
						price_disc	= price_disc + (line.subtotal_wo_discount-line.price_subtotal)
						price_grnyi = price_grnyi + (qty*price_unit)
						
						if ar_items_qty.has_key(product_id.id):
							ar_items_qty[product_id.id] -= qty
					#price_inv = price_inv + (qty*price_unit2)
			else:
				raise osv.except_osv(_('No PO mapping found'), _('No PO mapping found ref code [dincelpurchase_act_invoice]!'))
				
			
			qty_variance = 0
			if bal_coming == True:
				#no qty variance
				qty_variance = 0
				#vals={'state':'open'}
				#	self.write(cr, uid, inv_id, vals)	
				_ostpk.write({'x_pending_inv_coming':True})
			else:
				#with qty variance
				for _item in ar_items_qty:
					qty 	= ar_items_qty[_item]
					_op  	= _oprod.browse(cr, uid, _item, context=context)
					price_unit		= _op.standard_price
					qty_variance 	= qty_variance + (price_unit*qty)
					#if qty >0: #shortfall in invoice
						
					#else if qty <0: #additinal item received
					
				#_logger.error("dincelpurchase_move_linesar_items_qty33:["+str(ar_items_qty[ii])+"]["+str(ii)+"]")	
			if inv_id and price_inv>0:
				journal_ref 	= "EXJ" 
				invoice_name 	= journal_ref + "_" + str(inv_id)
				
				date_invoice	= datetime.datetime.today()
		
				_objperiodcr	= _operiod.find(cr, uid, date_invoice, context=context)#[0]
				if _objperiodcr:
					period_id 	= _objperiodcr[0]# in above code
				else:
					period_id 	= None
				
				_journal_id		= self.pool.get('account.journal').search(cr, uid, [('type', '=', 'purchase')], limit=1)[0] 	
				
				state_move		= "posted"	#"draft" [NOTE, if posted then it will automatically reported in Tiral Balance, General Ledger, reports, etc]
				
				actmove = self.pool.get('dincelaccount.journal.dcs')
				actmove.ref_name 	= origin+"_"+str(inv_id)
				actmove.state_move 	= state_move
				actmove.journal_id 	= _journal_id
				actmove.move_name 	= invoice_name
				actmove.date_move	= date_invoice
				actmove.period_id	= period_id
				actmove.partner_id	= partner_id
				
				_id	=	actmove.insert_move(cr, uid, ids, context=context)
				if _id:
					#---------------------1---------------------
					state_line		= "valid"
					account_id		= acct_good2inv
					debit			= price_grnyi
					credit 			= 0
					
					actmove.move_id 	= _id
					actmove.state_line 	= state_line
					actmove.journal_id 	= _journal_id
					actmove.move_line_name = invoice_name
					actmove.date_move	= date_invoice
					actmove.period_id	= period_id
					actmove.partner_id	= partner_id
					actmove.account_id	= account_id
					actmove.debit		= debit
					actmove.credit		= credit
					
					actmove.insert_move_line(cr, uid, ids, context=context)
					
					#---------------------2---------------------
					#_logger.error("dincelpurchase_validate_invoice_id_price_tax:["+str(price_tax)+"]acct_tax["+str(acct_tax)+"]")	
					if price_tax>0:
						account_id	= acct_tax
						debit		= price_tax
						credit 		= 0
						#actmove.move_id 	= _id
						#actmove.state_line 	= state_line
						#actmove.journal_id 	=_journal_id
						#actmove.move_line_name = invoice_name
						#actmove.date_move	=date_invoice
						#actmove.period_id	=period_id
						#actmove.partner_id	=partner_id
						actmove.account_id	=account_id
						actmove.debit	=debit
						actmove.credit	=credit
						actmove.insert_move_line(cr, uid, ids, context=context)
					if price_disc > 0:
						account_id	= acct_disc_rx
						debit		= 0
						credit 		= price_disc
						actmove.account_id	=account_id
						actmove.debit	=debit
						actmove.credit	=credit
						actmove.insert_move_line(cr, uid, ids, context=context)
					if price_diff != 0:
						account_id	= acct_pur_var
						if price_diff > 0:
							debit		= price_diff
							credit 		= 0
						else:
							debit		= 0
							credit 		= abs(price_diff)
						actmove.account_id	=account_id
						actmove.debit	=debit
						actmove.credit	=credit
						actmove.insert_move_line(cr, uid, ids, context=context)	
					if qty_variance > 0:
						account_id	= acct_qty_var
						debit		= 0
						credit 		= qty_variance
						actmove.account_id	=account_id
						actmove.debit	=debit
						actmove.credit	=credit
						actmove.insert_move_line(cr, uid, ids, context=context)
						
						account_id		= acct_good2inv
						debit			= qty_variance
						credit 			= 0
						actmove.account_id	=account_id
						actmove.debit	=debit
						actmove.credit	=credit
						actmove.insert_move_line(cr, uid, ids, context=context)
					if qty_variance < 0:	
						account_id	= acct_qty_var
						debit		= abs(qty_variance)
						credit 		= 0
						actmove.account_id	=account_id
						actmove.debit	=debit
						actmove.credit	=credit
						actmove.insert_move_line(cr, uid, ids, context=context)
						
						account_id	= acct_trade_cr
						debit		= 0
						credit 		= abs(qty_variance)
						actmove.account_id	=account_id
						actmove.debit	=debit
						actmove.credit	=credit
						actmove.insert_move_line(cr, uid, ids, context=context)
						
					#----------	
					account_id	= acct_trade_cr
					debit		= 0
					credit 		= price_tax+price_inv
					actmove.account_id	=account_id
					actmove.debit	=debit
					actmove.credit	=credit
					actmove.insert_move_line(cr, uid, ids, context=context)
					if price_freight>0:
						account_id	= acct_stock
						debit		= price_freight
						credit 		= 0
						actmove.account_id	=account_id
						actmove.debit	=debit
						actmove.credit	=credit
						actmove.insert_move_line(cr, uid, ids, context=context)
					
					vals={'state':'open'}
					_obj = self.pool.get('account.invoice')
					_obj.write(cr, uid, inv_id, vals)	
					#self.write(cr, uid, inv_id, vals)		
					#if journal_id:	
				
			
			
			
	def _selectInvoice(self, cr, uid, context=None):
		if context is None:
			context = {}
		_obj = self.pool.get('account.invoice')
		active_id = context and context.get('active_id', False) or False
		if not active_id:
			return False
			
		return active_id
		#l#ead = _obj.read(cr, uid, active_id, ['partner_id'], context=context)
		#return lead['partner_id'][0] if lead['partner_id'] else False
		
	
	_columns={
        'date_invoice': fields.date("Date"),
        'bal_coming': fields.boolean('Future Balance Qty Coming?', help='Check this to if balance quantity is being delivered in future.'),
		#'picking_id': fields.many2one('stock.picking','Picking List'),
		'invoice_id': fields.many2one('account.invoice','Invoice'),
    }	
	
	_defaults = {
     
        'invoice_id': _selectInvoice,
		
    }