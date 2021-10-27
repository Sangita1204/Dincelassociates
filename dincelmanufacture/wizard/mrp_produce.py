from openerp.osv import fields, osv
from openerp.tools.translate import _
import logging
_logger = logging.getLogger(__name__)
class dincelmrp_produce(osv.osv_memory):
	_name = "dincelmrp.produce"
	_description = "Produce MRP"
	_columns = {
		'date': fields.date('Date'),
		'item_lines':fields.one2many('dincelmrp.produce.line', 'produce_id', 'MRP Lines'),
		'qty':fields.float("Qty test"),
		'production_id': fields.many2one('dincelmrp.production', 'Production'),
	}
	
	def _save_production(self, cr, uid, ids, _id, context=None):	
		self.pool.get('mrp.production').action_confirm(cr, uid, _id, context=context)
		
	def save_production(self, cr, uid, ids, context=None):	
		if context is None:
			context = {}
		record = self.browse(cr, uid, ids[0], context=context)
		if record.item_lines:
			#_obj_mrp	= self.pool.get('mrp.production')
			#_oprod 		= self.pool.get('dincelproduct.product')
			for line in record.item_lines:
				if line.qty_produce>0:
					#_logger.error("save_productionsave_productionsave_production["+str(line.qty_produce)+"]")
					
					if line.mrp_id.state=="draft":
						ctx = context.copy()
						_ids=[]
						_ids.append(line.mrp_id.id)
						_logger.error("save_productionsave_productionsave_production["+str(_ids)+"]")
						self._save_production(cr, uid, _ids, _ids[0], context=ctx)
					#_obj = _obj_mrp.browse(cr, uid, line.mrp_id.id, context=context)
	def on_change_qty(self, cr, uid, ids, _qty, _lines, context=None):
		#_logger.error("on_change_qtyon_change_qtyproduceproduce["+str(context)+"]")
		_lines = []
		if context and context.get('active_ids'):
			_ids=context.get('active_ids')
			#_logger.error("on_change_qtyon_change_qtyproduceproduce["+str(_ids)+"]")
			for p in self.pool.get('dincelmrp.production').browse(cr, uid, _ids, context=context):
				#_logger.error("p.production_linep.production_linep.production_line["+str(p.production_line)+"]") 
				for line in p.production_line:
					_qty1=line.x_order_qty
					_qty2=_qty1
					vals = {
						'qty_order':_qty2,
						'mrp_id':line.id,
						'product_id': line.product_id.id or False,
						'product_uom':line.product_uom.id,
						'order_id':line.x_sale_order_id.id,
						'region_id':line.x_region_id.id or False,
						'order_length':line.x_order_length or 0.0,
						'qty_remain':_qty2,
					}
					_lines.append(vals)
					#_logger.error("production_lineproduction_lineproduction_lineproduction_line["+str(vals)+"]___["+str(_lines)+"]")	  
				
		return {'value': {'item_lines': _lines}}
		
	def _get_init_qty(self, cr, uid, context=None):
		return 1
	
	_defaults = {
		'date': fields.date.context_today,
		'qty': _get_init_qty,
		}
		 
class dincelmrp_produce_line(osv.osv_memory):
	_name = "dincelmrp.produce.line"
	_columns = {
		'produce_id': fields.many2one('dincelmrp.produce', 'Produce Reference'),
		'product_id': fields.many2one('product.product', 'Product'),
		'order_length':fields.float("Stock Length"),	
		'qty_order':fields.float("Qty Ordered"),	
		'qty_actual':fields.float("Qty Acutal"),	
		'qty_produce':fields.float("Qty Produce"),	
		'qty_remain':fields.float("Qty Remain"),	
		'order_id': fields.many2one('sale.order', 'Order Reference'),
		'mrp_id': fields.many2one('mrp.production', 'MRP'), 
		'product_uom': fields.many2one('product.uom', 'Unit of Measure'),
		'region_id': fields.many2one('dincelaccount.region', 'A/c Region'),
		'full_mo':fields.boolean('All Complete'),
	}	
	
	def onchange_full_mo(self, cr, uid, ids, full_mo, qty, context=None):
		#qty=0
		#vals = {'amount': 0.0}
		vals = { 'qty_produce': 0}
		if full_mo:
			vals['qty_produce']=qty
		
		return {'value': vals}