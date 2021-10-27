from openerp.osv import fields, osv
from openerp.tools.translate import _
import logging
import openerp.addons.decimal_precision as dp
_logger = logging.getLogger(__name__)
class dincelmrp_schedule_mrp(osv.osv_memory):
	_name = "dincelmrp.schedule.mrp"
	#_description = "Sales Make MRP"
	_columns = {
		'date': fields.date('Date'),
		'mrp_lines':fields.one2many('dincelmrp.schedule.mrp.line', 'schedulemrp_id', 'MRP Lines'),
		'qty':fields.float("Qty test"),
		'part_no':fields.integer('Part No',size=1),
		'part_tot':fields.integer('Total Parts',size=1),
		'order_id': fields.many2one('sale.order', 'Sale Order'),
		'part': fields.selection([
			('full', 'FULL'),
			('part', 'PART'),
			], 'Part'),
	}
	
	def on_change_qty(self, cr, uid, ids, product_qty, mrp_lines, context=None):
		
		new_mrp_lines = []
		if context and context.get('active_ids'):
			#_logger.error("on_change_qtyon_change_qty["+str(_ids)+"]")
			_ids=context.get('active_ids')
			
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
					
					qty_already=0
					#_logger.error("on_change_line.product_id.x_prod_cat["+str(line.product_id.x_prod_cat)+"]")
					##qty_available = line.product_id.qty_available
					qty_available =  self.pool.get('dincelproduct.inventory').qty_available(cr, uid, line.product_id.id, line.x_order_length,  context = context)
					sql ="select sum(x_order_qty) from mrp_production where product_id='"+str(line.product_id.id)+"' and x_sale_order_id ='"+str(o.id)+"'"
					
					#sql2 ="select sum(product_qty) from stock_move_tmp where product_id='"+str(line.product_id.id)+"' and order_id ='"+str(o.id)+"'"
					sql2reserve ="select sum(qty_origin) from stock_move_tmp where state='reserve' and product_id='"+str(line.product_id.id)+"' and order_id ='"+str(o.id)+"'"
					if line.product_id.x_prod_cat in['stocklength','customlength']:#line.product_id.x_prod_cat=="customlength":
						_obj=	self.pool.get('dincelproduct.product')
						_id = 	_obj.search(cr, uid, [('product_id', '=', line.product_id.id), ('product_len', '=', line.x_order_length)], limit=1)
						#_logger.error("on_change_linon_change_qty_id[" +str(_id)+"]")
						if _id:
							_obj 	=  _obj.browse(cr, uid, _id[0])
							##qty_available 	=_obj.qty_available_net
							sql  =sql + " and x_order_length='"+str(round(line.x_order_length))+"'"
							sql2reserve =sql2reserve + " and order_length='"+str(round(line.x_order_length))+"'"
							#_logger.error("on_change_line.product_id.found...._id[" +str(_id)+"]")
						##else:
							
							##qty_available =0#qty_available - _qty_pending#_obj.qty_reserved_net(cr, uid,ids,line.product_id.id, line.x_order_length)
							#_logger.error("on_change_line.product_id.notfoundnotfound...._qty_pending[" +str(_qty_pending)+"]")
					
					cr.execute(sql)
					res = cr.fetchone()
					if res and res[0]!= None: #Note -- >from scheduled  qty (no matter produced or not...)
						qty_already=(res[0])
					else:
						qty_already=0
					cr.execute(sql2reserve)
					res1 = cr.fetchone()	 # 
					if res1 and res1[0]!= None: #Note -- >from inventory stock reserve qty
						qty_already+=(res1[0])
					
					#_logger.error("on_change_line.qty_orderqty_orderqty_order[" +str(qty_order)+"][" +str(qty_already)+"]")	
					
					if qty_already>0:	
						qty2produce=qty_order-qty_already
					else:
						qty2produce=qty_order
					
					if qty_available<0:
						qty_available=0
					
					if qty2produce<0:
						qty2produce=0	
						
					qty_original=qty_available
					
					if qty2produce>qty_available:	
						qty_reserve=qty_available
						qty_produce=qty2produce-qty_reserve
					else:
						qty_produce=0
						qty_reserve=qty2produce
					
					#_logger.error("on_change_line.product_id.sqlsql[" +str(sql)+"]")
					
					if read_only:
						qty_produce =0
					
					vals = {
						'product_qty':qty_order,
						'qty_original':qty_original,
						'qty2produce':qty2produce,
						'qty_available':qty_available,
						#'qty_reserve':qty_reserve,
						#'qty_produce':qty_produce,
						'product_id': line.product_id.id or False,
						'product_uom':line.product_uom.id,
						'order_id':line.order_id.id,
						'line_id':line.id,
						'region_id':line.x_region_id.id or False,
						'coststate_id':line.x_coststate_id.id or False,
						'order_length':line.x_order_length or 0.0,
						'read_only':read_only,
						#'full_mo':True,
					}
					if line.product_id.x_prod_cat =='customlength':
						vals['full_mo']=True
						vals['qty_reserve']=qty_reserve
						vals['qty_produce']=qty_produce
					else:
						vals['full_mo']=False
						vals['qty_produce']=0
						vals['qty_reserve']=qty2produce
					if line.product_id.x_prod_cat !='freight':	
						new_mrp_lines.append(vals)
				
				
		return {'value': {'mrp_lines': new_mrp_lines}}
		
	def _get_init_qty(self, cr, uid, context=None):
		return 1	
	 
	_defaults = {
		'date': fields.date.context_today,
		'qty': _get_init_qty,
		}
	
	def schedule_mrp(self, cr, uid, ids, context=None):
		record = self.browse(cr, uid, ids[0], context=context)
		if record.mrp_lines:
			error_found		=False
			create_ids		=[]
			reserve_ids		=[]
			#mrp_vals		=[]
			#reserve_vals	=[]
			#stock_qtys		={}
			#reserve_qtys	={}
			line_sn			= 0
			_oprod 		= self.pool.get('dincelproduct.product')
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
						if (line.product_id.x_prod_cat=='stocklength' or line.product_id.x_prod_cat=='customlength') and line.order_length>0:
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
							'x_pack_10':0,
							'x_pack_12':0,
							'x_pack_14':0,
							'x_pack_20':0,
							'x_pack_xtra':0,
							'x_order_length':line.order_length or 0.0,
						}
						if line.order_id.origin:
							_name= line.order_id.origin + " " + line.product_id.x_dcs_itemcode# + " "
							if line.product_id.x_prod_cat in ('stocklength','customlength'):
								_name=_name + " " + str(long(line.order_length))
							#vals['name'] =_name	
							#_logger.error("on_change_line._name_name_name[" +str(_name)+"]")
						_qty=line.qty_produce
						#Y=x*10+x*12+x*14+x*20
						#x=Y/(10+12+14+20)
						_res=self._get_split_packs(cr, uid, _qty, line.product_id.x_pack10, line.product_id.x_pack12, line.product_id.x_pack14, line.product_id.x_pack20, context=context)
						vals['x_pack_10'] =_res['p10']
						vals['x_pack_12'] =_res['p12']
						vals['x_pack_14'] =_res['p14']
						vals['x_pack_20'] =_res['p20']
						vals['x_pack_xtra'] =_res['ext']
						'''
						_div=0
						_p10=0
						_p12=0
						_p14=0
						_p20=0
						if line.product_id.x_pack10:	
							_div+=10
							_p10=10
						if line.product_id.x_pack12:	
							_div+=12
							_p12=12
						if line.product_id.x_pack14:	
							_div+=14
							_p14=14
						if line.product_id.x_pack20:	
							_div+=20
							_p20=20
						
						if _div > 0:
							_x	= 	int(_qty / _div)
							
							_qtynew = _x*_p10 + _x*_p12 + _x*_p14 + _x*_p20
							
							if _qtynew <= _qty:
								_ext = _qty - _qtynew
								_qty2= _qty
								if _p10 > 0:
									if _x==0 and _p10>_qty2:
										vals['x_pack_10'] =1
										_ext=_qty2-_p10
										_qty2=_qty2-_p10 #for other calc below lines
									else:
										vals['x_pack_10'] = _x	
								if _p12 > 0:
									if _x==0 and _p10>_qty2:
										vals['x_pack_12'] =1
										_ext=_qty2-_p12
										_qty2=_qty2-_p12  #for other calc below lines
									else:
										vals['x_pack_12'] = _x
								if _p14 > 0:
									if _x==0 and _p10>_qty2:
										vals['x_pack_14'] =1
										_ext=_qty2-_p14
										_qty2=_qty2-_p14  #for other calc below lines
									else:
										vals['x_pack_14'] = _x
								if _p20 > 0:
									if _x==0 and _p20>_qty2:
										vals['x_pack_20']=1
										_ext=_qty2-_p20
										_qty2=_qty2-_p20  #for other calc below lines
									else:
										vals['x_pack_20'] = _x
								if _ext > 0:
									vals['x_pack_xtra'] = _ext'''
						
						bom_obj = self.pool.get('mrp.bom')
						
						bom_id 	= bom_obj.search(cr, uid, [('product_tmpl_id', '=', line.product_id.product_tmpl_id.id)], limit=1) 	
						
						if bom_id:
							bom_point 	= bom_obj.browse(cr, uid, bom_id[0], context=context)
							routing_id 	= bom_point.routing_id.id or False
							vals['bom_id'] = bom_id[0]
							if routing_id:
								vals['routing_id'] = routing_id	
								
						if line.region_id and line.region_id.id:
							vals['x_region_id']= line.region_id.id	
							
						if line.coststate_id and line.coststate_id.id:
							vals['x_coststate_id']= line.coststate_id.id	
							
						#add for mrp produce
						#_logger.error("schedule_mrpschedule_mrp_valsvals["+str(vals)+"]")
						mrp_id = self.pool.get('mrp.production').create(cr, uid, vals, context=context)
						#mrp_vals.append(vals)
						#mrp_id = self.pool.get('mrp.production').create(cr, uid, vals, context=context)
						create_ids.append(mrp_id)		
					
					#add to stock.move for reserve
					
					if line.qty_reserve>0:
						
						'''vals = {
							'product_qty':line.qty_reserve,
							'product_id': line.product_id.id or False,
							'product_uom':line.product_uom.id,
							'origin': line.order_id.name, 
							'order_id':line.order_id.id, 
							'order_length':line.order_length or 0.0,
							'state':'reserve',
						}
						self.pool.get('stock.move.tmp').create(cr, uid, vals, context=context)
						'''
						vals = {
							'reserve_qty': line.qty_reserve,
							'product_id': line.product_id.id or False,
							'order_length': line.order_length or 0.0,
							'order_id': line.order_id.id, 
						}
						_res=self._get_split_packs(cr, uid, line.qty_reserve, line.product_id.x_pack10, line.product_id.x_pack12, line.product_id.x_pack14, line.product_id.x_pack20, context=context)
						vals['pack_10'] =_res['p10']
						vals['pack_12'] =_res['p12']
						vals['pack_14'] =_res['p14']
						vals['pack_20'] =_res['p20']
						vals['pack_xtra'] =_res['ext']
						res_id=self.pool.get('dincelmrp.production.reserve').create(cr, uid, vals, context=context)
						reserve_ids.append(res_id)
						#reserve_vals.append(vals)
						if line.product_id.x_prod_cat in['stocklength','customlength']:
							_qty=line.qty_reserve*line.order_length*0.001
						else:
							_qty=line.qty_reserve
						_oprod.record_stock_order_reserve_new(cr, uid, line.order_id.id, line.product_id.id, _qty, line.qty_reserve, line.product_uom.id, line.order_length, 'reserve', context=context)
						
					self.pool.get('sale.order.line').write(cr, uid, [line.line_id.id], {'x_has_mrp': True}, context=context)
					
					vals1 = {'x_has_mrp': True}
					if not line.order_id.x_prod_status:
						vals1['x_prod_status']='queue'
					self.pool.get('sale.order').write(cr, uid, [line.order_id.id], vals1, context=context)	
			#now add the mrp records
			#
			if create_ids or reserve_ids:		
				
				sql ="select 1 from dincelmrp_production where order_id = '%s'" %(str(record.order_id.id))
				cr.execute(sql)
				rows = cr.fetchall()
				scount=len(rows)+1
				obj = self.pool.get('dincelmrp.production')
				vals = {
						'order_id':record.order_id.id,
						'name':record.order_id.name+"-"+str(scount),
						'date_produce':record.date,
						'partner_id':record.order_id.partner_id.id,
						'project_id':record.order_id.x_project_id.id,
						'user_id':record.order_id.user_id.id,
						'part_no':scount,
						}
				if len(create_ids)>0:
					vals['production_line'] = [(6, 0, create_ids)]		
				if len(reserve_ids)>0:
					vals['reserve_line'] = [(6, 0, reserve_ids)]	
					
				obj.create(cr,uid, vals, context=context)	
				
				return True
				
		return False
		
	def _get_split_packs(self, cr, uid, _qty, _en10, _en12, _en14, _en20, context=None):
		_p10=0
		_p12=0
		_p14=0
		_p20=0
		_count=0
		_rem=_qty
		_ext=0
		while _rem>0:
			if _en10:	
				_p10+=1
				_rem-=10
				_count+=1
			if _en12:	
				_p12+=1
				_rem-=12
				_count+=1
			if _en14:	
				_p14+=1
				_rem-=14
				_count+=1
			if _en20:	
				_p20+=1
				_rem-=20
				_count+=1
			if _count==0: #non found
				_ext=_rem
				_rem=0
		if _count > 0:
			if _rem<0:
				if _en20:	
					_p20-=1
					_rem+=10
				elif _en14:	
					_p14-=1
					_rem+=14
				elif _en12:	
					_p12-=1
					_rem+=12
				elif _en10:	
					_p10-=1
					_rem+=10
				
			_ext=_rem	
		else:
			_ext=_rem
		res={
			'p10':_p10,
			'p12':_p12,
			'p14':_p14,
			'p20':_p20,
			'ext':_ext,
		}	
		return res	
				 
		
class dincelmrp_schedule_mrp_line(osv.osv_memory):
	_name = "dincelmrp.schedule.mrp.line"
	_columns = {
		'schedulemrp_id': fields.many2one('dincelmrp.schedule.mrp', 'MRP Reference'),
		'product_id': fields.many2one('product.product', 'Product'),
		'order_length':fields.float("Stock Length",digits_compute= dp.get_precision('Int Number')),	
		'product_qty':fields.float("Qty Ordered"),	
		'qty_available':fields.float("Qty Stock",digits_compute= dp.get_precision('Int Number')),	
		'qty_produce':fields.float("Qty Produce",digits_compute= dp.get_precision('Int Number')),	
		'qty2produce':fields.float("Qty 2 Produce",digits_compute= dp.get_precision('Int Number')),	
		'qty_reserve':fields.float("Qty Reserve",digits_compute= dp.get_precision('Int Number')),	
		'qty_original':fields.float("Qty Original"),	
		'order_id': fields.many2one('sale.order', 'Order Reference'),
		'line_id': fields.many2one('sale.order.line', 'Order Reference'),
		'product_uom': fields.many2one('product.uom', 'Unit of Measure'),
		'region_id': fields.many2one('dincelaccount.region', 'A/c Region'),
		'coststate_id':fields.many2one("res.country.state","Cost Centre"),
		'read_only':fields.boolean("Readonly"),	
		'full_mo':fields.boolean('All MO'),
	}	
	
	def onchange_full_mo(self, cr, uid, ids, full_mo, qty2produce, qty_reserve, context=None):
		qty=0
		#vals = {'amount': 0.0}
		vals = { 'qty_produce': qty}
		if full_mo:
			vals['qty_produce']=qty2produce
			vals['qty_reserve']=0
		#amt_fee = self._get_card_fee(cr, uid, ids,paymethod_id, amount, context)	
		#_logger.error("on_change_line.onchange_full_moonchange_full_mo[" +str(vals)+"]")
		return {'value': vals}
	