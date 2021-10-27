from openerp.osv import osv, fields
from datetime import date
#from openerp.addons.base_status.base_state import base_state
import time 
import datetime
import logging
from openerp.tools.translate import _

from time import gmtime, strftime
_logger = logging.getLogger(__name__)

class dincelproduct_product(osv.Model):
	_name = "dincelproduct.product"
	
	def qty_reserved_net(self, cr, uid, ids, product_id, product_len, origin=None, context=None):
		return self.qty_stock_reserved(cr, uid, ids, product_id, product_len,origin=origin, context=context)
		'''context = context or {}
		qty_reserve=0
			 
		_obj	= self.pool.get('stock.move.tmp')	
		args 	= [("product_id", "=", product_id),("order_length", "=", product_len),('state','=','reserve')]
		tmpids  = _obj.search(cr, uid, args, context=context)
		#_logger.error("qty_reserved_netqty_reserved_net["+str(tmpids)+"]args["+str(args)+"]")
		for o in _obj.browse(cr, uid, tmpids, context=context):
			qty_reserve+=o.product_qty
		
		#qty_net = record.qty_available-qty_reserve
		
		return qty_reserve
		'''
	def qty_stock_reserved(self, cr, uid, ids, product_id, product_len, origin=None, context=None):
		context = context or {}
		_qty	= 0 
		
		_po = self.pool.get('product.product').browse(cr, uid, product_id, context=context)	
		args 	= [("product_id", "=", product_id),('state','=','reserve')]
		#is_custom  	= False
		if _po.x_prod_cat in['stocklength','customlength']:	#=="customlength":
			args += [("order_length", "=", product_len)]
			#_len 	= product_len
			#if _po.x_prod_cat=='customlength':
			#	is_custom  	= True
		if not origin:
			args += [("origin", "=", origin)]
			
		_obj	= self.pool.get('stock.move.tmp')	
		
		tmpids  = _obj.search(cr, uid, args, context=context)
		for o in _obj.browse(cr, uid, tmpids, context=context):
			_qty+=o.product_qty
		 
		
		return _qty
		
	def qty_stock_onhand(self, cr, uid, ids, product_id, product_len =False, context=None):
		context = context or {}
		qty_in	= 0
		qty_out	= 0	 
		
		_obj	= self.pool.get('stock.move.tmp')	
		#domain = [('code', '=', code)]
		#if wh: 
		#domain += [('warehouse_id', '=', wh)]
		args 	= [("product_id", "=", product_id),('state','in',['produced', 'purchased'])]
		if product_len:
			args+=[("order_length", "=", product_len)]
			
		tmpids  = _obj.search(cr, uid, args, context=context)
		for o in _obj.browse(cr, uid, tmpids, context=context):
			qty_in+=o.product_qty
		
		args 	= [("product_id", "=", product_id),('state','in',['delivered', 'damaged'])]
		if product_len:
			args+=[("order_length", "=", product_len)]
		tmpids  = _obj.search(cr, uid, args, context=context)
		for o in _obj.browse(cr, uid, tmpids, context=context):
			qty_out+=o.product_qty
		
		
		return qty_in-qty_out
		
	def _qty_available_net(self, cr, uid, ids, values, arg, context):
		context = context or {}
		qty_reserve=0
		qty_net=0
		x={}
		for record in self.browse(cr, uid, ids):
			#if record.x_project_id:
			#product_id = record.product_id.id	
			 
			qty_reserve =  self.qty_reserved_net(cr, uid,ids,record.product_id.id, record.product_len)
			#_obj	= self.pool.get('stock.move.tmp')	
			#args 	= [("product_id", "=", product_id),("order_length", "=", ),('state','=','reserve')]
			#tmpids  = _obj.search(cr, uid, args, context=context)
			#_logger.error("_qty_available_nettmpidstmpids["+str(tmpids)+"]args["+str(args)+"]")
			#for o in _obj.browse(cr, uid, tmpids, context=context):
			#	qty_reserve+=o.product_qty
			
			#qty_net = 
			x[record.id]=record.qty_available-qty_reserve
		return x
	_columns = {
		'name': fields.char('Name'),
		'product_id': fields.many2one('product.product', 'Product'),
		'product_len': fields.float('Length'),
		'qty_available':  fields.float('Qty Available'),
		'is_custom': fields.boolean('Is Custom Length'),
		'qty_available_net': fields.function(_qty_available_net, method=True, string='Quantity On Hand',type='float' ),
	}	
	
	_defaults = {
		'is_custom': False,
	}
	def record_stok_move(self, cr, uid, origin,  product_id, product_uom_id, movetype, qty, product_len =False, context=None):
		#if not product_len:
		#product_len= 0
		
		_len=0
		_opt=""
		
		_po = self.pool.get('product.product').browse(cr, uid, product_id, context=context)	
		
		is_custom  	= False
		if _po.x_prod_cat in['stocklength','customlength']:	#=="customlength":
			_len 	= product_len
			if _po.x_prod_cat=='customlength':
				is_custom  	= True
		args = [("product_id", "=", product_id),("product_len", "=", _len)]			
		vals = {
			'product_qty': qty,
			'product_id': product_id,
			'product_uom': product_uom_id,
			'origin': origin, 
			'order_length': product_len,
			'state': movetype,
		}
		#_logger.error("stockproduct_uomproduct_uom_view_id["+str(vals)+"]")
		self.pool.get('stock.move.tmp').create(cr, uid, vals, context=context)
		if movetype in ['produced','add']:
			_opt="add"
		#elif movetype in ['produced','add']:	
		#if movetype='produced':
		#	self.pool.get('stock.move.tmp').create(cr, uid, vals, context=context)
		result = self.search(cr, uid, args, context=context)
		if result:
			item = self.browse(cr, uid, result[0], context=context)
			if _opt=="add":
				qty_available = item.qty_available+qty
			else:
				qty_available = item.qty_available-qty
			self.write(cr, uid, [item.id], {'qty_available': qty_available}, context=context)
		else:
			#po = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
			if _opt=="add":
				qty_available = qty
			else:	
				qty_available = -qty
			vals={
				'qty_available':qty_available,
				'product_id':product_id,
				'product_len':product_len,
				'is_custom':is_custom,
				'name':_po.name,
			}
			self.create(cr, uid, vals, context=context)
		#res = {}
	

 
	
'''	
class dincelproduct_stockmove(osv.Model):	
	_inherit = "stock.move"
	_columns = {	
		'x_order_length':fields.float("Ordered Length"),
	}
	_defaults = {
		'x_order_length': 0,
	}
'''
class dincelproduct_stockmove_tmp(osv.Model):	
	_name = "stock.move.tmp"
	_columns = {
		'date':fields.datetime("Date"),
		'origin': fields.char("Source"),
		'partner_id': fields.many2one('res.partner', 'Partner'),
		'location_id': fields.many2one('stock.location', 'Source Location'),
		'location_dest_id': fields.many2one('stock.location', 'Dest Location'),
		'product_id': fields.many2one('product.product', 'Product'),
		'product_uom': fields.many2one('product.uom', 'Unit of Measure'),
		'product_qty': fields.float('Quantity'),
		'order_length':fields.float("Ordered Length"),
		'picking_type_id': fields.many2one('stock.picking.type', 'Picking Type'),
		'state': fields.selection([('reserve', 'Reserve'),
								('produced', 'Produced'),
								('purchased', 'Purchased'),
								('damaged', 'Damaged'),
								('delivered', 'Delivered'),
								('cancel', 'Cancelled'),
								('done', 'Move Done Delivered') 
								], 'Status'),
	}
	_defaults = {
		'date': datetime.datetime.now()#lambda *a: time.strftime('%Y-%m-%d %H:%M:%S.%f'),#fields.date.context_today,
	}
	_order = 'date desc'	
