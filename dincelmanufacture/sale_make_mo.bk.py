from openerp.osv import fields, osv
from openerp.tools.translate import _
import logging
_logger = logging.getLogger(__name__)
class dincelsale_make_mrp(osv.osv_memory):
	_name = "dincelsale.make.mrp"
	_description = "Sales Make MRP"
	_columns = {
		'date': fields.date('Invoice Date'),
		'mrp_lines':fields.one2many('dincelsale.make.mrp.line', 'mrp_id', 'MRP Lines'),
		'qty':fields.float("Qty test"),
	}
		
	def on_change_qty(self, cr, uid, ids, product_qty, mrp_lines, context=None):
		
		new_mrp_lines = []
		if context and context.get('active_ids'):
			
			_ids=context.get('active_ids')
			#_logger.error("on_change_qtyon_change_qty["+str(_ids)+"]")
			for o in self.pool.get('sale.order').browse(cr, uid, _ids, context=context):
				lines = []
				for line in o.order_line:
					_cat	=line.product_id.x_prod_cat
					if (line.x_has_mrp == False) and (_cat== None or _cat in['stocklength','customlength','accessories']):
						lines.append(line.id)
				
				for line in self.pool.get('sale.order.line').browse(cr, uid, lines, context=context):
					qty_order=line.x_order_qty
					#qty_available=line.product_id.qty_available
					#qty_available=line.product_id.qty_available
					
					qty_available = line.product_id.qty_available
					if line.product_id.x_prod_cat=="customlength":
						_obj=	self.pool.get('dincelproduct.product')
						_id = 	_obj.search(cr, uid, [('product_id', '=', line.product_id.id), ('custom_len', '=', line.x_order_length)], limit=1)
						if _id:
							_obj 	=  _obj.browse(cr, uid, _id[0])
							qty_available 	=_obj.qty_available
					#else:
					if qty_available<0:
						qty_available=0
					qty_original=qty_available
					if qty_order>qty_available:	
						qty_produce=qty_order-qty_available
						qty_reserve=qty_available
					else:
						qty_produce=0
						qty_reserve=qty_order
						qty_available=qty_available-qty_order
					#else:
					#	qty_produce=0
					
					vals = {
						'product_qty':qty_order,
						'qty_original':qty_original,
						'qty_available':qty_available,
						'qty_reserve':qty_reserve,
						'qty_produce':qty_produce,
						'product_id': line.product_id.id or False,
						'product_uom':line.product_uom.id,
						'order_id':line.order_id.id,
						'line_id':line.id,
						'order_length':line.x_order_length or 0.0,
					}
					new_mrp_lines.append(vals)
        
		return {'value': {'mrp_lines': new_mrp_lines}}
		
 
	def _get_init_qty(self, cr, uid, context=None):
		return 1
	
	def make_mrp_dcs(self, cr, uid, ids, context=None):
		record = self.browse(cr, uid, ids[0], context=context)
		if record.mrp_lines:
			error_found=False
			create_ids=[]
			for line in record.mrp_lines:
				
				#automatic set-->name =self.pool.get('ir.sequence').get(cr, uid, 'mrp.production') or '/'
			
				if line.product_qty<(line.qty_produce+line.qty_reserve):
					error_found=True
					raise osv.except_osv(_('Error!'),_('Invalid quantity found!'))
					return False
				if not error_found:
					if line.qty_produce>0:
						vals = {
							'product_qty':line.qty_produce,
							'product_id': line.product_id.id or False,
							'product_uom':line.product_uom.id,
							'order_id':line.order_id.id,
							'origin': line.order_id.name, 
							'date_planned':record.date,
							'x_order_length':line.order_length or 0.0,
						}
						bom_obj = self.pool.get('mrp.bom')
						
						bom_id 	= bom_obj.search(cr, uid, [('product_tmpl_id', '=', line.product_id.product_tmpl_id.id)], limit=1) 	
						
						if bom_id:
							bom_point 	= bom_obj.browse(cr, uid, bom_id[0], context=context)
							routing_id 	= bom_point.routing_id.id or False
							vals['bom_id']=bom_id[0]
							if routing_id:
								vals['routing_id']=routing_id	
						mrp_id = self.pool.get('mrp.production').create(cr, uid, vals, context=context)
						create_ids.append(mrp_id)		
					
					#add to stock.move for reserve
					if line.qty_reserve>0:
						vals = {
							'product_qty':line.qty_reserve,
							'product_id': line.product_id.id or False,
							'product_uom':line.product_uom.id,
							'order_id':line.order_id.id,
							'origin': line.order_id.name, 
							'x_order_length':line.order_length or 0.0,
						}
					#self.pool.get('sale.order.line').write(cr, uid, [line.line_id.id], {'x_has_mrp': True}, context=context)
					#self.pool.get('sale.order').write(cr, uid, [line.order_id.id], {'x_has_mrp': True}, context=context)	
				#_logger.error("make_mrp_dcsmake_mrp_dcs["+str(vals)+"]")
		return {}
		
	def make_mrp_do(self, cr, uid, ids, context=None):
		order_obj = self.pool.get('sale.order')
		data = self.read(cr, uid, ids)[0]
		order_obj.action_create_mrp_mo(cr, uid, context.get(('active_ids'), []), False, date_invoice=data['date'])
		return False
	_defaults = {
		'date': fields.date.context_today,
		'qty': _get_init_qty,
		}
		
class dincelsale_make_mrp_line(osv.osv_memory):
	_name = "dincelsale.make.mrp.line"
	_columns = {
		'mrp_id': fields.many2one('dincelsale.make.mrp', 'MRP Reference'),
		'product_id': fields.many2one('product.product', 'Product'),
		'order_length':fields.float("Stock Length"),	
		'product_qty':fields.float("Quantity Ordered"),	
		'qty_available':fields.float("Quantity Stock"),	
		'qty_produce':fields.float("Quantity Produce"),	
		'qty_reserve':fields.float("Quantity Reserve"),	
		'qty_original':fields.float("Quantity Original"),	
		'order_id': fields.many2one('sale.order', 'Order Reference'),
		'line_id': fields.many2one('sale.order.line', 'Order Reference'),
		'product_uom': fields.many2one('product.uom', 'Unit of Measure'),
	}	
	
	def on_change_qty2(self, cr, uid, ids, qty_org,qty_order, qty_stock,qty_produce,qty_reserve, context=None):
		if qty_order<qty_produce:
			raise osv.except_osv(_('Error!'),_('Invalid quantity found!'))
			return False
		if qty_order<qty_reserve:
			raise osv.except_osv(_('Error!'),_('Invalid quantity found!'))
			return False
		if qty_reserve>qty_org:
			raise osv.except_osv(_('Error!'),_('Invalid quantity found!'))
			return False
		if qty_reserve>=0:
			qty_available=qty_org-qty_reserve
			#if qty_order>qty_available:	
			qty_produce=qty_order-qty_reserve
			#	#qty_reserve=qty_available
			##	qty_produce=0
			#	#qty_reserve=qty_order
			#	qty_available=qty_available-qty_order
			#_logger.error("on_change_qty2on_change_qty2["+str(_qty)+"]")
			return {'value': {'qty_available': qty_available,'qty_produce': qty_produce}}
		return True
		
	def on_change_qty(self, cr, uid, ids, qty_org,qty_order, qty_stock,qty_produce,qty_reserve, context=None):
		if qty_order<qty_produce:
			raise osv.except_osv(_('Error!'),_('Invalid quantity found!'))
			return False
		if qty_order<qty_reserve:
			raise osv.except_osv(_('Error!'),_('Invalid quantity found!'))
			return False
		return True