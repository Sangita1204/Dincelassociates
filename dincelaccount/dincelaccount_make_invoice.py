from openerp.osv import fields, osv
from openerp.tools.translate import _
import logging
_logger = logging.getLogger(__name__)
#from dinceljournal import dincelaccount_invoice

class dincelaccount_make_invoice(osv.osv_memory):
	_name = 'dincelaccount.make_invoice'
	_columns = {
		'date_invoice': fields.date('Invoice date'),
		'sale_order_id':fields.many2one('sale.order', 'Account'),
		'partner_id': fields.many2one('res.partner', 'Customer'), 
		'order_line': fields.one2many('sale.order.line', 'order_id', 'Order Lines'),
		#'order_line_id':fields.one2many('sale.order.line', 'Order Lines'),
	}
	
	def _selectSaleOrder(self, cr, uid, context=None):
		if context is None:
			context = {}
		_obj = self.pool.get('sale.order')
		return context and context.get('active_id', False) or False
		
	 
	
	def create_invoices(self, cr, uid, ids, context=None):
        #""" create invoices for the active sales orders """
		if context is None:
			context = {}
		_obj = self.pool.get('sale.order')
		if context:
			id =  context.get('active_id', False)# or False
			_obj = _obj.browse(cr, uid, id, context)
			
			sql = "select * from account_invoice_line where origin='%s' " % _obj.name
			cr.execute(sql)
			rows1 	= cr.dictfetchall()
			
			ar_items_done 	= {}
			ar_items_rem  	= {}
			
			tot_qty_rem 	= 0
			
			for row1 in rows1:
				qty = row1['quantity']
				product_id = row1['product_id']
				if ar_items_done.has_key(product_id) == False:
					ar_items_done[product_id] = qty
				else:
					ar_items_done[product_id] += qty
					
			for line in _obj.order_line:
				qty = line.product_uom_qty
				product_id = line.product_id.id
				if ar_items_done.has_key(product_id):
					qty = qty - ar_items_done[product_id]
			
				tot_qty_rem += qty
				
			if tot_qty_rem > 0 :
				dt_invoice = None
				for record in self.browse(cr, uid, ids, context=context):
					dt_invoice = record.date_invoice
				inv_id 		= self._create_invoice(cr, uid, id, dt_invoice, context=context)
				
				for line in _obj.order_line:
					qty = line.product_uom_qty
					product_id = line.product_id.id
					if ar_items_done.has_key(product_id):
						qty = qty - ar_items_done[product_id]		
					if qty > 0:
						vals = {
							'product_id': product_id,
							'quantity': qty,
							'invoice_id': inv_id,
							'origin': _obj.name,
							'price_unit': line.price_unit,
							'price_subtotal': line.price_unit*qty,
						}
						if line.tax_id:
							vals['invoice_line_tax_id'] = [(6, 0, line.tax_id.ids)]
						line_id 		= self._create_invoice_line(cr, uid, vals, context=context)
				
				
				#for taxes
				obj_inv = self.pool.get('account.invoice')
				obj_inv 	= obj_inv.browse(cr, uid, inv_id, context)
				obj_inv.button_compute(True) #For taxes
				
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
			else:
				return {}#_logger.error("invoice_sales_validate.create_invoices_zero_qty["+str(tot_qty_rem)+"]")
		return {}		
	
	def _create_invoice(self, cr, uid, sale_id, dt_invoice, context=None):
		inv_id 	= 0
		_obj 	= self.pool.get('sale.order')
		
		if context:
			
			obj_inv = self.pool.get('account.invoice')
			
			_obj 	= _obj.browse(cr, uid, sale_id, context)
			
			vals = {
					'x_sale_order_id': sale_id,
                    'origin': _obj.name,
                    'reference': _obj.name,
                    'partner_id': _obj.partner_id.id,
					'internal_number': _obj.name,
					'section_id': 1,
                    'type': 'out_invoice',
					'account_id':_obj.partner_id.property_account_receivable.id
					}
			if dt_invoice:
				vals['date_invoice']=dt_invoice
			
			inv_id = obj_inv.create(cr, uid, vals, context=context)
			
		return inv_id
		
	def _create_invoice_line(self, cr, uid, vals, context=None):

		obj_inv 	= self.pool.get('account.invoice.line')
		product_obj = self.pool.get('product.product')
		product_obj = product_obj.browse(cr, uid, vals['product_id'], context)
		vals['name']= product_obj.name
		
		inv_id = obj_inv.create(cr, uid, vals, context=context)
			
		return inv_id
		
	 
		
	_defaults={
		'date_invoice' : fields.date.context_today,  
		'sale_order_id': _selectSaleOrder,
		#'partner_id': _selectPartner,
		#'order_line': _selectSaleOrderLine,
	} 
		