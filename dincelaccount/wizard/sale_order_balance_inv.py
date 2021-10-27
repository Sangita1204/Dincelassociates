import time
from openerp.osv import fields, osv
from openerp.tools.translate import _
import logging
_logger = logging.getLogger(__name__)

class dincelsale_order_balance_inv(osv.osv_memory):
	_name = "dincelsale.order.balance"
	_columns = {
		'date': fields.date('Date'),
		'qty':fields.float("Qty test"),
		'comments':fields.char("Comments"),
		'order_id':fields.many2one('sale.order', 'OrderId'),
		'amount':fields.float('Amount Ex Gst'),
		'amount_total':fields.float('Amount Total'),
	}
		
	def on_change_amount(self, cr, uid, ids,_amounttot, context=None):
		amount= float(_amounttot)/1.1
		vals={'amount':amount}	

		return {'value':vals}
		
	def button_create_balance1(self, cr, uid, ids, context=None):
		if context is None:
			context = {}			
		for record in self.browse(cr, uid, ids, context=context):		
			if not record.amount or record.amount<=0.0:
				raise osv.except_osv(_('Error!'),_('Invalid amount found!!'))
			else:
				price_unit	= record.amount# float(record.amount_total)/1.1
				obj_inv 	= self.pool.get('account.invoice')	
				obj_invline	= self.pool.get('account.invoice.line')
				product_obj = self.pool.get('product.product')	
				args = [("x_prod_cat", "=", "balance1")]
				_ids = product_obj.search(cr, uid, args, context=context) 
				if not _ids:
					raise osv.except_osv(_('Error!'),_('Balance product not found!!'))
				else:
					product_id	 = _ids[0]
					_obj  =  product_obj.browse(cr, uid, product_id, context)
					vals = {
						'x_sale_order_id': record.order_id.id,
						'x_inv_type':'balance',
						'origin': record.order_id.name,
						'reference': record.order_id.name,
						'partner_id': record.order_id.partner_id.id,
						'user_id':record.order_id.user_id.id,
						#'internal_number': record.name,
						'section_id': 1,
						'type': 'out_invoice',
						'account_id':record.order_id.partner_id.property_account_receivable.id
						}
			
					vals['date_invoice']=record.date
					vals['date_due']=vals['date_invoice']
					
					 
					vals['x_project_id']=record.order_id.x_project_id.id
				 
					_payterm = 	self.pool.get('account.payment.term').search(cr, uid, [('x_payterm_code', '=', 'immediate')], limit=1)
					if _payterm:
						vals['payment_term']=_payterm[0]	
					
					inv_id = obj_inv.create(cr, uid, vals, context=context)
				
					vals = {
						'product_id': product_id,
						'quantity': '1',
						'invoice_id': inv_id,
						'origin': record.order_id.name,
						'price_unit': price_unit,
						'price_subtotal': price_unit,
					}
					vals['name'] = _obj.name
					 
					if _obj.taxes_id:
						vals['invoice_line_tax_id'] = [(6, 0, _obj.taxes_id.ids)]
				 
							
					obj_invline.create(cr, uid, vals, context=context)
					#for taxes
					
					obj_inv = obj_inv.browse(cr, uid, inv_id, context)
					obj_inv.button_compute(True) #For taxes
					
				 
					view_id = self.pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'dincelaccount.invoice.form')], limit=1) 	
					
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
					
		#return True
		
	def on_change_qty(self, cr, uid, ids, context=None):
		
		#if context and context.get('active_ids'):
			
		vals={}	

		return {'value':vals}
		
	def _get_init_qty(self, cr, uid, context=None):
		return 1
		
	_defaults = {
		'qty': _get_init_qty,
		'date': lambda *a: time.strftime('%Y-%m-%d'),
		}
	 