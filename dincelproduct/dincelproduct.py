from openerp.osv import osv, fields
from datetime import date
#from openerp.addons.base_status.base_state import base_state
import time 
import datetime
import logging
from openerp.tools.translate import _

from time import gmtime, strftime
_logger = logging.getLogger(__name__)

class dincelproduct_inventory(osv.Model):
	_name = "dincelproduct.inventory"
	
	def create_if(self, cr, uid,  product_id, product_length, context=None):
		_obj=	self.pool.get('dincelproduct.product')
		_ids = 	_obj.search(cr, uid, [('product_id', '=', product_id), ('product_len', '=', product_length)], limit=1)
		if _ids:	
			_id=_ids[0]
		else:
			vals={
				'product_id':product_id,
				'product_len':product_length,
			}
			prod = self.pool.get('product.product').browse(cr, uid, product_id, context=context)	
			if prod:
				vals['name'] = prod.name
			 
			_id = _obj.create(cr, uid, vals, context=context)
			
		return _id	
	
	#>>straignt qty no to LM nor M2 or other....eg 20 panels of 3,000mm, etc HERE 20=qty_qty 	
	#>>by production, by purchase, un-reserve, etc
	def qty_increment(self, cr, uid,  product_id, product_length, qty_qty, context=None):
		_obj	= self.pool.get('dincelproduct.product')
		_id 	= self.create_if(cr, uid,  product_id, product_length)
		_item 	= _obj.browse(cr, uid, _id)
		_qty_qty = float(_item.qty_qty)+float(qty_qty)
		_obj.write(cr, uid, [_id], {'qty_qty': _qty_qty}, context=context)	
		return True

	#>>straignt qty no to LM nor M2 or other....eg 20 panels of 3,000mm, etc HERE 20=qty_qty 	
	#>>by loss, by reserve, shipment, etc [note reserve==ship, no need to deduct when reserve is shipped]
	def qty_decrement(self, cr, uid,  product_id, product_length, qty_qty, context=None):
		_obj	= self.pool.get('dincelproduct.product')
		_id 	= self.create_if(cr, uid,  product_id, product_length)
		_item 	= _obj.browse(cr, uid, _id)
		_qty_qty = float(_item.qty_qty)-float(qty_qty)
		_obj.write(cr, uid, [_id], {'qty_qty': _qty_qty}, context=context)	
		return True
		
	def qty_available(self, cr, uid,  product_id, product_length, context=None):
		_obj	= self.pool.get('dincelproduct.product')
		_id 	= self.create_if(cr, uid,  product_id, product_length)
		_item 	= _obj.browse(cr, uid, _id)
		return _item.qty_qty
	def qty_available_v2(self, cr, uid,  location_id, product_id, product_length, context=None):
		sql="select sum(x_quantity) from stock_move where location_dest_id='%s' and product_id='%s' and x_order_length='%s' and state='done'" % (location_id, product_id, product_length)
		cr.execute(sql)
		res = cr.fetchone()
		if res and res[0]!= None:
			qty_in=(res[0])
		else:
			qty_in=0
		sql="select sum(x_quantity) from stock_move where location_id='%s' and product_id='%s' and x_order_length='%s' and state='done'" % (location_id, product_id, product_length)
		cr.execute(sql)
		res = cr.fetchone()
		if res and res[0]!= None:
			qty_out=(res[0])
		else:
			qty_out=0
		if 	qty_in>=qty_out:
			return qty_in-qty_out
		else:
			return 0
class dincelproduct_product(osv.Model):
	_name = "dincelproduct.product"
	
	#def qty_reserved_net(self, cr, uid, ids, product_id, product_len, origin=None, context=None):
	#	return self.qty_stock_reserved(cr, uid, ids, product_id, product_len,origin=origin, context=context)
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
	
		
	def qty_produced_net(self, cr, uid, ids, product_id, order_length, order_id, context=None):
		sql ="SELECT SUM(x_produced_qty) FROM mrp_production WHERE product_id='"+str(product_id)+"' AND x_sale_order_id='"+str(order_id)+"'"
		if order_length:
			sql += " AND x_order_length="+str(int(order_length))+" " #>>>due to numeric/float fignure no quote added ''>>>
		cr.execute(sql)
		res = cr.fetchone()
		if res and res[0]!= None:
			_qty=(res[0])
		else:
			_qty=0
		return 	_qty
	def qty_delivered_net_v2(self, cr, uid, ids, product_id, order_length, order_id, context=None):
		sql ="SELECT SUM(p.ship_qty) FROM dincelstock_pickinglist_line p,dincelstock_pickinglist s WHERE p.pickinglist_id=s.id and s.pick_order_id ='"+str(order_id)+"' and p.product_id='"+str(product_id)+"' "
		if order_length:
			sql += " AND p.order_length="+str(int(order_length))+" " #>>>due to numeric/float fignure no quote added ''>>>
		
		cr.execute(sql)
		res = cr.fetchone()
		if res and res[0]!= None:
			_qty=(res[0])
		else:
			_qty=0
		return 	_qty
		
	def qty_delivered_net(self, cr, uid, ids, product_id, order_length, order_id, context=None):
		sql ="SELECT SUM(product_qty) FROM stock_move_tmp WHERE move_type in('damage','lost','sales') AND product_id='"+str(product_id)+"'  AND order_id='"+str(order_id)+"' "
		if order_length:
			sql += " AND order_length="+str(int(order_length))+" " #>>>due to numeric/float fignure no quote added ''>>>
		
		cr.execute(sql)
		res = cr.fetchone()
		if res and res[0]!= None:
			_qty=(res[0])
			#_logger.error("qty_delivered_netqty_delivered_netsql1ty111["+str(_qty)+"]")
			if order_length:
				_qty = int(_qty/((order_length)/1000))
				#_logger.error("qty_delivered_netqty_delivered_netsql2222["+str(_qty)+"]")
		else:
			_qty=0
		return 	_qty
		
	def qty_reserved_delivered_net(self, cr, uid, ids, product_id, order_length, order_id, context=None):
		sql ="SELECT SUM(product_qty) FROM stock_move_tmp WHERE move_type in('reserve-deliverd') AND product_id='"+str(product_id)+"'  AND order_id='"+str(order_id)+"' "
		if order_length:
			sql += " AND order_length="+str(int(order_length))+" " #>>>due to numeric/float fignure no quote added ''>>>
		
		cr.execute(sql)
		res = cr.fetchone()
		if res and res[0]!= None:
			_qty=(res[0])
			if order_length:
				_qty = int(_qty/((order_length)/1000))
		else:
			_qty=0
		return 	_qty
	
	#for available but less reserved....
	def qty_stock_reserved_new_all(self, cr, uid, ids, product_id, order_length, context=None):
		sql ="SELECT SUM(product_qty) FROM stock_move_tmp WHERE move_type in('reserve') AND product_id='"+str(product_id)+"'  "
		if order_length:
			sql += " AND order_length='"+str(int(order_length))+"' " #>>>due to numeric/float fignure no quote added ''>>>
		cr.execute(sql)
		res = cr.fetchone()
		if res and res[0]!= None:
			_qty=(res[0])
			if order_length:
				_qty = int(_qty/((order_length)/1000))
		else:
			_qty=0
		return 	_qty	
		
	def qty_stock_reserved_new(self, cr, uid, ids, product_id, order_length, order_id, context=None):
		sql ="SELECT SUM(product_qty) FROM stock_move_tmp WHERE move_type in('reserve') AND product_id='"+str(product_id)+"'  AND order_id='"+str(order_id)+"' "
		if order_length:
			sql += " AND order_length='"+str(int(order_length))+"' " #>>>due to numeric/float fignure no quote added ''>>>
		cr.execute(sql)
		res = cr.fetchone()
		if res and res[0]!= None:
			_qty=(res[0])
			if order_length:
				_qty = int(_qty/((order_length)/1000))
		else:
			_qty=0
		return 	_qty	
		
	def qty_stock_reservedxx(self, cr, uid, ids, product_id, product_len, origin=None, context=None):
		context = context or {}
		_qty	= 0 
		if product_id:
			_po = self.pool.get('product.product').browse(cr, uid, product_id, context=context)	
			args 	= [("product_id", "=", product_id),('state','=','reserve')]

			if _po.x_prod_cat in['stocklength','customlength']:	#=="customlength":
				args += [("order_length", "=", product_len)]

			if not origin:
				args += [("origin", "=", origin)]
				
			_obj	= self.pool.get('stock.move.tmp')	
			
			tmpids  = _obj.search(cr, uid, args, context=context)
			if tmpids:
				for o in _obj.browse(cr, uid, tmpids, context=context):
					if o.order_length:
						_qty+=(o.product_qty/(0.001*o.order_length))
					else:
						_qty+=o.product_qty
		return _qty
		
	def qty_stock_onhand(self, cr, uid, ids, product_id, product_len =False, context=None):
		context = context or {}
		qty_in	= 0
		qty_out	= 0	 
		
		_obj	= self.pool.get('stock.move.tmp')	
		args 	= [("product_id", "=", product_id),('state','in',['produced', 'purchased'])]
		if product_len:
			args+=[("order_length", "=", product_len)]
			
		tmpids  = _obj.search(cr, uid, args, context=context)
		for o in _obj.browse(cr, uid, tmpids, context=context):
			if o.order_length:
				qty_in+=(o.product_qty/(0.001*o.order_length))
			else:
				qty_in+=o.product_qty
		
		args 	= [("product_id", "=", product_id),('state','in',['delivered', 'damaged'])]
		if product_len:
			args+=[("order_length", "=", product_len)]
		tmpids  = _obj.search(cr, uid, args, context=context)
		for o in _obj.browse(cr, uid, tmpids, context=context):
			if o.order_length:
				qty_out+=(o.product_qty/(0.001*o.order_length))
			else:
				qty_out+=o.product_qty
		
		
		return qty_in-qty_out
		
	def _qty_panel_net(self, cr, uid, ids, values, arg, context):
		context = context or {}
		x={}
		for record in self.browse(cr, uid, ids):
			if record.product_len>0:
				x[record.id]=record.qty_available/(record.product_len*0.001)
			else:
				x[record.id]=0
		return x		
	
	def _qty_available_net(self, cr, uid, ids, values, arg, context):
		context = context or {}
		qty_reserve=0
		qty_net=0
		x={}
		for record in self.browse(cr, uid, ids):
			 
			qty_reserve =  0#self.qty_stock_reserved_new_all(cr, uid,ids,record.product_id.id, record.product_len)
			
			if record.product_len:
				qty_avail=(record.qty_available/(record.product_len*0.001))
			else:
				qty_avail=record.qty_available
			x[record.id]=qty_avail-qty_reserve
		return x
	_columns = {
		'name': fields.char('Name'),
		'product_id': fields.many2one('product.product', 'Product'),
		'product_len': fields.float('Length'),
		'qty_available':  fields.float('Qty LM'),
		'qty_qty':  fields.float('Qty Qty'), #qty net in the stock,
		'is_custom': fields.boolean('Is Custom Length'),
		'qty_panel': fields.function(_qty_panel_net, method=True, string='Qty',type='float' ),
		'qty_available_net': fields.function(_qty_available_net, method=True, string='Quantity On Hand',type='float' ),
		'product_uom': fields.many2one('product.uom', 'Unit of Measure'),
	}	
	_sql_constraints  = [
		('product_uniq', 'unique(product_id, product_len)', 'The Product Length is not Unique!'),
		]
	_defaults = {
		'is_custom': False,
	}
	
	#def record_stok_move_new(self, cr, uid, order_id,  product_id,  movetype, qty, product_len =False, context=None):
	def record_stock_mrp_new(self, cr, uid, production_id, product_id, product_qty,qty_origin, movetype, context=None): 
		#DO NOTE RE CALC QTY MOVE ---already calculated in function call
		
		_mrp = self.pool.get('mrp.production').browse(cr, uid, production_id, context=context)	
		 		
		vals = {
			'product_qty': product_qty,
			'qty_origin':qty_origin,
			'product_id': product_id,
			'product_uom': _mrp.product_uom.id,#product_uom_id,
			'origin': _mrp.origin, 
			'order_length': _mrp.x_order_length,
			'location_dest_id':_mrp.location_dest_id.id,
			'move_type': movetype,
		}
		if _mrp.x_sale_order_id:
			vals['order_id'] = _mrp.x_sale_order_id.id
			
		#warehouse_dest_id--> TODO ..or derive from location_dest_id???
		if movetype == 'mo-stock' or movetype == 'mo-sales':
			vals['state']= "produced"		#,_state="produced"
			
		self.pool.get('stock.move.tmp').create(cr, uid, vals, context=context)
	
	def record_stock_order_reserve_new(self, cr, uid, order_id, product_id, product_qty,qty_origin,_uom,_length, movetype, context=None): 
		#DO NOTE RE CALC QTY MOVE ---already calculated in function call
		#_state=""
		
		_so = self.pool.get('sale.order').browse(cr, uid, order_id, context=context)	
		 		
		vals = {
			'product_qty': product_qty,
			'qty_origin':qty_origin,
			'product_id': product_id,
			'product_uom': _uom,#product_uom_id,
			'origin': _so.name, 
			'order_length': _length,
			'move_type': movetype, #reserve
		}
		#'location_dest_id':_mrp.location_dest_id.id,
		#if _mrp.x_sale_order_id:
		vals['order_id'] = order_id
		
		vals['state']= "reserve"		#,_state="produced"
			
		self.pool.get('stock.move.tmp').create(cr, uid, vals, context=context)
		
	#def record_stock_delivered(self, cr, uid, order_id, product_id, product_qty, movetype, context=None): 
	def record_stock_shipped(self, cr, uid, order_id, product_id, uom_id, product_qty,qty_origin, order_length, _dest_id, _type, context=None):
	#DO NOTE RE CALC QTY MOVE ---already calculated in function call
		_order = self.pool.get('sale.order').browse(cr, uid, order_id, context=context)	
		 		
		vals = {
			'product_qty': product_qty,
			'qty_origin':qty_origin,
			'product_id': product_id,
			'product_uom': uom_id,#product_uom_id,
			'origin': _order.name, 
			'order_length': order_length,
			'order_id':order_id,
			'move_type': _type#'sales', #>>sales delivery type
		}
		
		if _dest_id:
			vals['location_dest_id']=_dest_id
		#warehouse_dest_id--> TODO ..or derive from location_dest_id???
		#if movetype == 'mo-stock':
		vals['state']= "delivered"		#,_state="produced"
			
		self.pool.get('stock.move.tmp').create(cr, uid, vals, context=context)

		
	def record_stok_move_xx(self, cr, uid, origin,  product_id, product_uom_id, movetype, qty, product_len =False, context=None):
		#if not product_len:
		#product_len= 0
		#DO NOTE RE CALC QTY MOVE ---alrady calculated in function call
		_len=0
		_opt=""
		
		_po = self.pool.get('product.product').browse(cr, uid, product_id, context=context)	
		
		is_custom  	= False
		if _po.x_prod_cat in['stocklength','customlength']:	#=="customlength":
			_len 	= product_len
			#qty 	= qty*product_len*0.001#NONONONO0000
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
'''>> moved to dincelstock....
class dincelproduct_stockmove(osv.Model):	
	_inherit = "stock.move"
	_columns = {	
		'x_order_length':fields.integer("Ordered Length"),
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
		'warehouse_id': fields.many2one('stock.warehouse', 'Source Warehouse'),
		'warehouse_dest_id': fields.many2one('stock.warehouse', 'Dest Warehouse'),
		'location_id': fields.many2one('stock.location', 'Source Location'),
		'location_dest_id': fields.many2one('stock.location', 'Dest Location'),
		'product_id': fields.many2one('product.product', 'Product'),
		'product_uom': fields.many2one('product.uom', 'Unit of Measure'),
		'product_qty': fields.float('Quantity'),
		'qty_origin': fields.float('Origin Qty'), #>> this is origin qty, non-LM in case of P-1,[product_qty = qty_origin >> in case of accs]
		#'qty_in': fields.float('Qty In'),	 -->>N/A this is calculated in runtime by using "move_type" value logic
		#'qty_out': fields.float('Qty Out'), -->>N/A this is calculated in runtime by using "move_type" value logic
		'order_length':fields.float("Ordered Length"),
		'order_id': fields.many2one('sale.order', 'Sale Order Id'),
		'picking_type_id': fields.many2one('stock.picking.type', 'Picking Type'),
		'move_type':fields.selection([
					('mo-sales','MO Sales'), #manufactured for sales
					('mo-stock','MO Stock'), #manufactured for stock item (no sales item assigned)
					('purchase','PO Stock'),
					('internal','Internal Stock'),
					('damage','Damage Stock'),
					('lost','Lost Stock'),
					('sales','Sales Delivered Stock'), #deliverd to customer
					('reserve', 'Sales Reserve'),		#reserver for specific sales item
					('reserve-deliverd', 'Reserve Delivered'),		#reserve and delivered for specific sales item
					],'Move Type'),
		'state': fields.selection([
								('reserve', 'Reserve'),
								('produced', 'Produced'),
								('purchased', 'Purchased'),
								('damaged', 'Damaged'),
								('delivered', 'Delivered'),
								('cancel', 'Cancelled'),
								('done', 'Move Done Delivered') 
								], 'Status'), #todo not in USE**********
	}
	_defaults = {
		'qty_in':0,
		'qty_out':0,
		'date': datetime.datetime.now()#lambda *a: time.strftime('%Y-%m-%d %H:%M:%S.%f'),#fields.date.context_today,
	}
	_order = 'date desc'	
	