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
		
	def _selectPartner(self, cr, uid, context=None):
		if context is None:
			context = {}
		_obj = self.pool.get('res.partner')
		return context and context.get('active_id', False) or False
		
	def _selectSaleOrderLine(self, cr, uid, context=None):
		if context is None:
			context = {}
		#_obj = self.pool.get('sale.order')
		#if context:
			#id =  context.get('active_id', False)# or False
			
			#_logger.error("invoice_sales_validate._selectSaleOrderLine["+str(id)+"]")
			
			#_obj = _obj.browse(cr, uid, id, context)
			
			#st1 = str(id) + "]["+ str(_obj.name)
			
			#_logger.error("invoice_sales_validate.111["+str(st1)+"]")
			
			#for line in _obj.order_line:
				#st1 = str(line.price_unit) + str(line.name) +"-" + str(line.product_id.id)
				#product.product.id 
				#---------------------------
				#_logger.error("invoice_sales_validate._selectSaleOrderLine["+str(st1)+"]")
			'''for order in _obj.browse(cr, uid, context.get('active_id', False) or False, context=context):
				if order.order_line:
					return order.order_line
			'''		
			#return _obj.order_line# and context.get('active_id', False) or False
		#else:
		return False
		#''return False
	
	def create_invoices(self, cr, uid, ids, context=None):
        #""" create invoices for the active sales orders """
		if context is None:
			context = {}
		_obj = self.pool.get('sale.order')
		if context:
			id =  context.get('active_id', False)# or False
			_obj = _obj.browse(cr, uid, id, context)
			
			st1 = str(id) + "]["+ str(_obj.name)
			#sql = "select * from account_invoice where origin='%s' " % _obj.name
			sql = "select * from account_invoice_line where origin='%s' " % _obj.name
			cr.execute(sql)
			rows1 	= cr.dictfetchall()
			
			ar_items_done = {}
			ar_items_rem  = {}
			ar_price = {}
			tot_qty = 0
			
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
				#else:
				#	qty_less=0
				ar_price[product_id]= line.price_unit
				ar_items_rem[product_id] = qty	
				tot_qty += qty
				
			if tot_qty > 0 :
				dt_invoice = None
				for record in self.browse(cr, uid, ids, context=context):
					dt_invoice = record.date_invoice
				inv_id 		= self._create_invoice(cr, uid, id, dt_invoice, context=context)
				
			
				for key, value in ar_items_rem.iteritems():
					if value > 0.0:
						#st1 = str(key) + "," + str(value)
						vals = {
							'product_id': key,
							'quantity': value,
							'invoice_id': inv_id,
							'origin': _obj.name,
							'price_unit': ar_price[key],
							'price_subtotal': ar_price[key]*value,
						}
						line_id 		= self._create_invoice_line(cr, uid, vals, context=context)
					#else:
					#	st1 = str(key) + "_zero_qty_" + str(value)
					#_logger.error("invoice_sales_validate.create_invoices_ar_items_rem["+str(st1)+"]")
				
				view_id 		= self.pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'dincelaccount.dincelaccount_invoice_form')], limit=1) 	
				
				#view_id=277
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
				_logger.error("invoice_sales_validate.create_invoices_zero_qty["+str(tot_qty)+"]")
		return {}		
	
	def _create_invoice(self, cr, uid, sale_id, dt_invoice, context=None):
		inv_id 	= 0
		_obj 	= self.pool.get('sale.order')
		
		if context:
			#sale_id = context.get('active_id', False) 
			
			obj_inv = self.pool.get('account.invoice')
			
			_obj 	= _obj.browse(cr, uid, sale_id, context)
			
			vals = {
					
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
				
			#str1 = str(sale_id) + ","+str(_obj.partner_id.property_account_receivable.id) + ","+str(_obj.partner_id.id)
			
			#_logger.error("invoice_112233["+str(str1)+"]")
			
			inv_id = obj_inv.create(cr, uid, vals, context=context)
			
		return inv_id
		
	def _create_invoice_line(self, cr, uid, vals, context=None):

		obj_inv = self.pool.get('account.invoice.line')
		product_obj = self.pool.get('product.product')
		product_obj = product_obj.browse(cr, uid, vals['product_id'], context)
		vals['name']=product_obj.name
		
		inv_id = obj_inv.create(cr, uid, vals, context=context)
			
		return inv_id
		
	def create_invoices1(self, cr, uid, ids, context=None):
        #""" create invoices for the active sales orders """
		sale_obj 	= self.pool.get('sale.order')
		act_window 	= self.pool.get('ir.actions.act_window')
		wizard 		= self.browse(cr, uid, ids[0], context)
		sale_ids 	= context.get('active_ids', [])
		
		
		_obj = self.pool.get('account.invoice')
		obj_ids = _obj.search(cr, uid, [('origin', '=', "sale_refund")])
		if obj_ids:
			return obj_ids[0] if obj_ids[0] else False 
		else:
			return False
			
		#if wizard.advance_payment_method == 'all':
		# create the final invoices of the active sales orders
		res = sale_obj.manual_invoice(cr, uid, sale_ids, context)
		if context.get('open_invoices', False):
			return res
		return {'type': 'ir.actions.act_window_close'}

		'''
        inv_ids = []
        for sale_id, inv_values in self._prepare_advance_invoice_vals(cr, uid, ids, context=context):
            inv_ids.append(self._create_invoices(cr, uid, inv_values, sale_id, context=context))

        if context.get('open_invoices', False):
            return self.open_invoices( cr, uid, ids, inv_ids, context=context)
        return {'type': 'ir.actions.act_window_close'}
		'''
	def open_invoices(self, cr, uid, ids, invoice_ids, context=None):
		#""" open a view on one of the given invoice_ids """
		ir_model_data = self.pool.get('ir.model.data')
		form_res = ir_model_data.get_object_reference(cr, uid, 'account', 'invoice_form')
		form_id = form_res and form_res[1] or False
		tree_res = ir_model_data.get_object_reference(cr, uid, 'account', 'invoice_tree')
		tree_id = tree_res and tree_res[1] or False

		return {
			'name': _('Advance Invoice'),
			'view_type': 'form',
			'view_mode': 'form,tree',
			'res_model': 'account.invoice',
			'res_id': invoice_ids[0],
			'view_id': False,
			'views': [(form_id, 'form'), (tree_id, 'tree')],
			'context': "{'type': 'out_invoice'}",
			'type': 'ir.actions.act_window',
		}	
		
	_defaults={
		'date_invoice' : fields.date.context_today,  
		'sale_order_id': _selectSaleOrder,
		'partner_id': _selectPartner,
		'order_line': _selectSaleOrderLine,
	} 
		