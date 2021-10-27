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
			_ids = context.get('active_ids')
			#_logger.error("on_change_qtyon_change_qty["+str(_ids)+"]")
			for o in self.pool.get('sale.order').browse(cr, uid, _ids, context=context):
				lines = []
				for line in o.order_line:
					_cat	=line.product_id.x_prod_cat
					if (line.x_has_mrp == False) and (_cat== None or _cat in['stocklength','customlength','accessories']):
						lines.append(line.id)
				
				partner_id	= o.partner_id.id
				cr_limit 	= o.partner_id.credit_limit
				read_only	= False
				if cr_limit and cr_limit>0:
					if o.amount_total > cr_limit:
						read_only = True
					else:	
						sql ="select sum(amount_total) from sale_order where x_status='open' and x_prod_status in ('part','queue','complete') and partner_id='%s'" %(partner_id)
						cr.execute(sql)
						res = cr.fetchone()
						
						#_logger.error("on_change_qtyon_change_qty["+str(cr_limit)+"]["+str(sql)+"]")
						if res:
							amount_total=(res[0])
							if amount_total>cr_limit:
								read_only=True
			
				for line in self.pool.get('sale.order.line').browse(cr, uid, lines, context=context):
					qty_order=line.x_order_qty
					#qty_available=line.product_id.qty_available
					#qty_available=line.product_id.qty_available
					#_logger.error("on_change_line.product_id.x_prod_cat["+str(line.product_id.x_prod_cat)+"]")
					qty_available = line.product_id.qty_available
					sql ="select sum(x_order_qty) from mrp_production where product_id='"+str(line.product_id.id)+"' and x_sale_order_id ='"+str(o.id)+"'"
					sql2 ="select sum(product_qty) from stock_move_tmp where product_id='"+str(line.product_id.id)+"' and order_id ='"+str(o.id)+"'"
					if line.product_id.x_prod_cat in['stocklength','customlength']:#line.product_id.x_prod_cat=="customlength":
						_obj=	self.pool.get('dincelproduct.product')
						_id = 	_obj.search(cr, uid, [('product_id', '=', line.product_id.id), ('product_len', '=', line.x_order_length)], limit=1)
						#_logger.error("on_change_linon_change_qty_id[" +str(_id)+"]")
						if _id:
							_obj 	=  _obj.browse(cr, uid, _id[0])
							qty_available 	=_obj.qty_available_net
							sql =sql + " and x_order_length='"+str(round(line.x_order_length))+"'"
							sql2 =sql2 + " and order_length='"+str(round(line.x_order_length))+"'"
							#_logger.error("on_change_line.product_id.found...._id[" +str(_id)+"]")
						else:
							#_qty_pending=_obj.qty_reserved_net(cr, uid,ids,line.product_id.id, line.x_order_length)
							qty_available =0#qty_available - _qty_pending#_obj.qty_reserved_net(cr, uid,ids,line.product_id.id, line.x_order_length)
							#_logger.error("on_change_line.product_id.notfoundnotfound...._qty_pending[" +str(_qty_pending)+"]")
					#else:
					cr.execute(sql)
					res = cr.fetchone()
					if res and res[0]!= None:
						qty_already=(res[0])
					else:
						qty_already=0
					cr.execute(sql2)
					res = cr.fetchone()	
					if res and res[0]!= None:
						qty_already+=(res[0])
					#else:
					#	qty_already=0	
					if qty_already>0:	
						qty2produce=qty_order-qty_already
					else:
						qty2produce=qty_order
						
					if qty_available<0:
						qty_available=0
					qty_original=qty_available
					if qty2produce>qty_available:	
						qty_reserve=qty_available
						qty_produce=qty2produce-qty_reserve
						
					else:
						qty_produce=0
						qty_reserve=qty2produce
						#qty_available=qty_available-qty2produce
					#else:
					#	qty_produce=0
					#_logger.error("on_change_line.product_id.sqlsql[" +str(sql)+"]")
					
					if read_only:
						qty_produce =0#qty_available
					vals = {
						'product_qty':qty_order,
						'qty_original':qty_original,
						'qty2produce':qty2produce,
						'qty_available':qty_available,
						'qty_reserve':qty_reserve,
						'qty_produce':qty_produce,
						'product_id': line.product_id.id or False,
						'product_uom':line.product_uom.id,
						'order_id':line.order_id.id,
						'line_id':line.id,
						'region_id':line.x_region_id.id or False,
						'coststate_id':line.x_coststate_id.id or False,
						'order_length':line.x_order_length or 0.0,
						'read_only':read_only,
					}
					new_mrp_lines.append(vals)
        
		return {'value': {'mrp_lines': new_mrp_lines}}
		
 
	def _get_init_qty(self, cr, uid, context=None):
		return 1
	
	def make_mrp_dcs(self, cr, uid, ids, context=None):
		record = self.browse(cr, uid, ids[0], context=context)
		if record.mrp_lines:
			error_found		=False
			create_ids		=[]
			#mrp_vals		=[]
			#reserve_vals	=[]
			#stock_qtys		={}
			#reserve_qtys	={}
			line_sn			= 0
			
			#_obj_inventory	=	self.pool.get('dincelproduct.inventory')
			for line in record.mrp_lines:
				
				#automatic set-->name =self.pool.get('ir.sequence').get(cr, uid, 'mrp.production') or '/'
				line_sn+=1
				if line.product_qty<(line.qty_produce+line.qty_reserve):
					error_found=True
					raise osv.except_osv(_('Error!'),_('Sum of reserve and production qty greater than ordered qty, at line [' +str(line_sn)+']'))
					return False
				if line.product_qty<(line.qty_reserve):
					error_found=True
					raise osv.except_osv(_('Error!'),_('Reserve qty greater than ordered qty, at line [' +str(line_sn)+']'))
					return False
				
				if not error_found:
					
					if line.qty_produce>0:
						if line.order_length>0:
							qty_lm = line.order_length*line.qty_produce*0.001
						else:
							qty_lm=line.qty_produce
							
						vals = {
							'product_qty':qty_lm,
							'product_id': line.product_id.id or False,
							'product_uom':line.product_uom.id,
							'x_sale_order_id':line.order_id.id,
							'origin': line.order_id.name, 
							'date_planned':record.date,
							'x_order_qty':line.qty_produce,
							'x_reserve_qty':line.qty_reserve,
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
						if line.region_id and line.region_id.id:
							vals['x_region_id']= line.region_id.id	
						if line.coststate_id and line.coststate_id.id:
							vals['x_coststate_id']= line.coststate_id.id		
							
						#add for mrp produce
						self.pool.get('mrp.production').create(cr, uid, vals, context=context)
						#mrp_vals.append(vals)
						#mrp_id = self.pool.get('mrp.production').create(cr, uid, vals, context=context)
						#create_ids.append(mrp_id)		
					
					#add to stock.move for reserve
					if line.qty_reserve > 0:
						
						vals = {
							'product_qty':line.qty_reserve,
							'product_id': line.product_id.id or False,
							'product_uom':line.product_uom.id,
							'origin': line.order_id.name, 
							'order_id':line.order_id.id, 
							'order_length':line.order_length or 0.0,
							'state':'reserve',
						}
						self.pool.get('stock.move.tmp').create(cr, uid, vals, context = context)
						self.pool.get('dincelproduct.inventory').qty_decrement(cr, uid, line.product_id.id, line.order_length, line.qty_reserve, context = context)
						#reserve_vals.append(vals)
					self.pool.get('sale.order.line').write(cr, uid, [line.line_id.id], {'x_has_mrp': True}, context=context)
					vals = {'x_has_mrp': True}
					if not line.order_id.x_prod_status:
						vals['x_prod_status']='queue'
					self.pool.get('sale.order').write(cr, uid, [line.order_id.id], vals, context=context)	
					
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
		'product_qty':fields.float("Qty Ordered"),	
		'qty_available':fields.float("Qty Stock"),	
		'qty_produce':fields.float("Qty Produce"),	
		'qty2produce':fields.float("Qty 2 Produce"),	
		'qty_reserve':fields.float("Qty Reserve"),	
		'qty_original':fields.float("Qty Original"),	
		'order_id': fields.many2one('sale.order', 'Order Reference'),
		'line_id': fields.many2one('sale.order.line', 'Order Reference'),
		'product_uom': fields.many2one('product.uom', 'Unit of Measure'),
		'region_id': fields.many2one('dincelaccount.region', 'A/c Region'),
		'coststate_id':fields.many2one("res.country.state","Cost Centre"),
		'read_only':fields.boolean("Readonly"),	
	}	
	
	def on_change_qty2(self, cr, uid, ids, qty2produce,qty_original,product_qty, qty_available, qty_produce,qty_reserve, context=None):
		if qty2produce<qty_produce:
			raise osv.except_osv(_('Error!'),_('Invalid quantity found for production!'))
			return False
		if qty2produce<qty_reserve or  qty_available<qty_reserve :
			raise osv.except_osv(_('Error!'),_('Invalid quantity found for reserve !'))
			return False
		if (qty_reserve+qty_produce)>qty2produce:
			raise osv.except_osv(_('Error!'),_('Invalid quantity found for production!'))
			return False
		if qty_reserve>=0:
			#qty_available=qty2produce-qty_reserve
			#if qty_order>qty_available:	
			qty_produce=qty2produce-qty_reserve
			#	#qty_reserve=qty_available
			##	qty_produce=0
			#	#qty_reserve=qty_order
			#	qty_available=qty_available-qty_order
			#_logger.error("on_change_qty2on_change_qty2["+str(_qty)+"]")
			#return {'value': {'qty_available': qty_available,'qty_produce': qty_produce}}
			return {'value': {'qty_produce': qty_produce}}
		return True
		
	def on_change_qty(self, cr, uid, ids, qty_org,qty_order, qty_stock,qty_produce,qty_reserve, context=None):
		if qty_order<qty_produce:
			raise osv.except_osv(_('Error!'),_('Invalid quantity found!'))
			return False
		if qty_order<qty_reserve:
			raise osv.except_osv(_('Error!'),_('Invalid quantity found!'))
			return False
		return True