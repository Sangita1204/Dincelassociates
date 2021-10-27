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
		'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse'),
		'location_id': fields.many2one('stock.location', 'Location Stock (B)'),
		'ho_loc_id': fields.many2one('stock.location', 'Head Office (A)'),
		'full_mo':fields.boolean('MO All'),
		'full_stock':fields.boolean('Stock'),
		'is_headoffice':fields.boolean('Is Headoffice '),
		'root_stock':fields.boolean('Head Office'),
		'part': fields.selection([
			('full', 'FULL'),
			('part', 'PART'),
			], 'Part'),
	}
	def on_change_check_mo(self, cr, uid, ids, check,_lines, context=None):
		vals={}
		if check:
			vals = {'full_stock':False,'root_stock':False}	
		if _lines:
			line_ids = self.resolve_2many_commands(cr, uid, 'mrp_lines', _lines, ['full_mo'], context)
			for line in line_ids:
				if line:
					product_id=line['product_id']
					prod=self.pool.get('product.product').browse(cr,uid,product_id,context)
					if prod.x_prod_type=="acs":
						line['root_stock']= check
						line['qty_produce']=0
						line['qty_reserve']=line['qty2produce']
					else:	
						line['full_mo']= check
						if check:
							line['qty_produce']=line['qty2produce']
							line['qty_reserve']=0
						else:
							line['qty_produce']=0
							
			vals['mrp_lines']= line_ids			
		return {'value': vals}
	def on_change_check_stock(self, cr, uid, ids, check,_lines, context=None):
		vals={}
		if check:
			vals = {'full_mo':False,'root_stock':False}
		if _lines:
			line_ids = self.resolve_2many_commands(cr, uid, 'mrp_lines', _lines, ['full_stock'], context)
			for line in line_ids:
				if line:
					line['full_stock']= check
					product_id=line['product_id']
					prod=self.pool.get('product.product').browse(cr,uid,product_id,context)
					if prod.x_prod_type=="acs":
						line['qty_produce']=0
						line['qty_reserve']=line['qty2produce']
					else:
						if check:
							line['qty_reserve']=line['qty2produce']
						#else:
						#	line['qty_reserve']=0
			vals['mrp_lines']= line_ids
		return {'value': vals}
		
	def on_change_check_root(self, cr, uid, ids, check,_lines, context=None):
		vals={}
		if check:
			vals = {'full_stock':False,'full_mo':False}
		if _lines:
			line_ids = self.resolve_2many_commands(cr, uid, 'mrp_lines', _lines, ['root_stock'], context)
			for line in line_ids:
				if line:
					line['root_stock']= check
					product_id=line['product_id']
					prod=self.pool.get('product.product').browse(cr,uid,product_id,context)
					if prod.x_prod_type=="acs":
						line['qty_produce']=0
						line['qty_reserve']=line['qty2produce']
					else:
						if check:
							line['qty_reserve']=line['qty2produce']
						#else:
						#W	line['qty_reserve']=0
			vals['mrp_lines']= line_ids			
		return {'value': vals}
		
	def on_change_qty(self, cr, uid, ids, product_qty, mrp_lines, context=None):	
		vals1={}
		arr_domain={}
		new_mrp_lines = []
		location_id=None
		ho_loc_id=None
		is_headoffice=False
		oprod = self.pool.get('product.product')
		if context and context.get('active_ids'):
			_ids_ho 	= self.pool.get("stock.location").search(cr, uid, [('x_primary','=',True)], context=context)
			arr_domain  = {'ho_loc_id': [('id','in', (_ids_ho))]}
			if _ids_ho:
				vals1['ho_loc_id']=	_ids_ho[0]
				ho_loc_id = _ids_ho[0]
			#arr_domain={'ho_loc_id':_ids_ho}
			
			_ids=context.get('active_ids')
			_objres=self.pool.get("dincelmrp.production.reserve")
			for o in self.pool.get('sale.order').browse(cr, uid, _ids, context=context):
				 
				
				if o.x_warehouse_id:
					vals1['warehouse_id']=o.x_warehouse_id.id 
					if o.x_warehouse_id.x_master:
						vals1['is_headoffice']=True 
						is_headoffice=True
					if o.x_warehouse_id.lot_stock_id:
						location_id=o.x_warehouse_id.lot_stock_id.id 
						vals1['location_id']=location_id
				for line in o.order_line:
					_cat	=line.product_id.x_prod_cat
					_qty_ho=0
					_qty_ho_res=0
					if _cat !='freight' and line.product_id.type !="service":	
						qty_order=line.x_order_qty
						mo_already=0
						
						_product_id=line.product_id.id
						_len	=int(line.x_order_length)
						#if  line.product_id.x_prod_type and line.product_id.x_prod_type=="acs":
						#
						#else:
						
						qty_available 	= oprod.stock_value(cr, uid, _product_id, _len, location_id, context=context)
						qty_reserve		=oprod.stock_reserve_qty(cr, uid, _product_id, location_id, _len, False, context=context)
						qty_available	-=qty_reserve
						if ho_loc_id:
							_qty_ho 	= oprod.stock_value(cr, uid, _product_id, _len,  ho_loc_id, context)
							_qty_ho_res	= oprod.stock_reserve_qty(cr, uid, _product_id, ho_loc_id, _len, False, context=context)
							_qty_ho		-=_qty_ho_res
							
						'''if  line.product_id.x_prod_type=="acs":#P-3 and others...
							qty_available 	= oprod.stock_value(cr, uid, _product_id, _len, location_id, context=context)
							#qty_available = self.pool.get('stock.quant').qty_available(cr, uid, _product_id, location_id,context) 
							#qty_available = int(qty_available/(_len*0.001)) #P3 or other stock length cause they are produced in LM
							#qty_reserve		= _objres.qty_reserved_total( cr, uid, _product_id, location_id, None)
							qty_reserve		=oprod.stock_reserve_qty(cr, uid, _product_id, location_id, _len, False, context=context)
							if ho_loc_id:
								#_qty_ho = self.pool.get('stock.quant').qty_available(cr, uid, _product_id, ho_loc_id,context)
								_qty_ho 	= oprod.stock_value(cr, uid, _product_id, _len,  ho_loc_id, context)
								_qty_ho_res	= oprod.stock_reserve_qty(cr, uid, _product_id, ho_loc_id, _len, False, context=context)
								#_qty_ho_res	= _objres.qty_reserved_total(cr, uid, _product_id, ho_loc_id, None)
								#_logger.error("dincelmrp_produc_qty_ho_res_qty_ho_res["+str(_qty_ho)+"]["+str(_qty_ho_res)+"]")
								_qty_ho-=_qty_ho_res
						else:			
							#if (_len > 0 and location_id and _cat in ['customlength','stocklength']):
						
							#if  line.product_id.x_prod_type=="acs":#P-3 only == "customlength":
							#	qty_available = self.pool.get('stock.quant').qty_available(cr, uid, _product_id, location_id,context) 
							#	#qty_available = int(qty_available/(_len*0.001)) #P3 or other stock length cause they are produced in LM
							#	qty_reserve		= _objres.qty_reserved_total( cr, uid, _product_id, location_id, None)
							#	if ho_loc_id:
							#		qty_available = self.pool.get('stock.quant').qty_available(cr, uid, _product_id, location_id,context)
							#else:
							qty_available = self.pool.get('stock.quant').qty_available_custom(cr, uid, _product_id, _len,  location_id,context ) 
							qty_reserve		=	_objres.qty_reserved_total( cr, uid, _product_id, location_id, _len)
							qty_available-=qty_reserve
						'''
						#else:
						
						#	qty_available 	= self.pool.get('stock.quant').qty_available(cr, uid, _product_id, location_id,context) 
						#	qty_reserve		= _objres.qty_reserved_total( cr, uid, _product_id, location_id, None)
						#	qty_available-=qty_reserve
							
						 
						sql2res ="select sum(reserve_qty) from dincelmrp_production_reserve where product_id='"+str(_product_id)+"' and order_id ='"+str(o.id)+"'"
						sql 	="select sum(x_order_qty) from mrp_production where product_id='"+str(_product_id)+"' and x_sale_order_id ='"+str(o.id)+"'"
						if _cat in['stocklength','customlength']:#line.product_id.x_prod_cat=="customlength":
							if  line.product_id.x_prod_type != "acs":#NON P-3 only 
								sql  	=sql + " and x_order_length='"+str(_len)+"'"
								sql2res =sql2res + " and order_length='"+str(_len)+"'"
						#stock MO
						cr.execute(sql)
						res = cr.fetchone()
						if res and res[0]!= None: #Note -- >from scheduled  qty (no matter produced or not...)
							mo_already=int(res[0])
						else:
							mo_already=0
						#stock reserver 2	
						cr.execute(sql2res)
						res1 = cr.fetchone()	 # 
						if res1 and res1[0]!= None: #Note -- >from inventory stock reserve qty
							mo_already+=int(res1[0])
						
						if mo_already>0:	
							qty2produce=qty_order-mo_already
						else:
							qty2produce=qty_order
						
						if qty_available<0:
							qty_available=0
						
						if qty2produce<0:
							qty2produce=0	
							
						#qty_original=qty_available
						
						if qty2produce>qty_available:	
							qty_reserve=qty_available
							qty_produce=qty2produce-qty_reserve
						else:
							qty_produce=0
							qty_reserve=qty2produce
						
						vals = {
							'product_qty':qty_order,
							'qty_original':qty_available, #for calculation in runtime just in case...
							'qty2produce':qty2produce,
							'qty_available':qty_available,
							'product_id': _product_id,
							'product_uom':line.product_uom.id,
							'order_id':o.id,
							'line_id':line.id,
							'region_id':line.x_region_id.id or False,
							'coststate_id':line.x_coststate_id.id or False,
							'order_length':_len,
							'read_only':False,
							'full_mo':False,
							'is_headoffice':is_headoffice,
							'qty_root':_qty_ho,
						}
						'''
						if line.product_id.x_prod_type =='acs':
							vals['full_mo']=False
							#vals['qty_reserve']=qty2produce
						else:
							if line.product_id.x_prod_cat in ['customlength','stocklength']:#if line.product_id.x_prod_cat =='customlength':
								if line.product_id.x_prod_cat =='customlength':
									vals['full_mo']=True
									vals['qty_produce']=qty2produce
							else:
								vals['full_mo']=False
								vals['qty_reserve']=qty2produce
						'''	
						new_mrp_lines.append(vals)
		vals1['mrp_lines']=	new_mrp_lines
		
		return {'value':vals1,'domain':arr_domain}
 
		
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
				#if line.qty_available<(line.qty_reserve): todo enable later....
				#	error_found=True
				#	raise osv.except_osv(_('Error!'),_('Reserve qty greater than stock qty, at line [' +str(line_sn)+']'))
				#	return False
				
				if not error_found:
					
					if line.qty_produce>0:
						#if (line.product_id.x_prod_cat=='stocklength' or line.product_id.x_prod_cat=='customlength') and line.order_length>0:
						#	qty_lm = line.order_length*line.qty_produce*0.001
						#else:
						#	qty_lm=line.qty_produce
						if line.product_id.x_prod_type 	and line.product_id.x_prod_type =="acs":
							qty_lm=line.qty_produce
						else:
							qty_lm = line.order_length*line.qty_produce*0.001
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
						#_res=self._get_split_packs(cr, uid, _qty, line.product_id.x_pack10, line.product_id.x_pack12, line.product_id.x_pack14, line.product_id.x_pack20, context=context)
						_res=self._get_split_packs(cr, uid, _qty, line.product_id.id, context=context)
						vals['x_pack_10'] =_res['p10']
						vals['x_pack_12'] =_res['p12']
						vals['x_pack_14'] =_res['p14']
						vals['x_pack_20'] =_res['p20']
						vals['x_pack_xtra'] =_res['ext']
						 
						
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
						 
						vals = {
							'reserve_qty': line.qty_reserve,
							'product_id': line.product_id.id or False,
							'order_length': line.order_length or 0.0,
							'length_mm': int(line.order_length),
							'quantity': line.qty_reserve,
							'order_id': line.order_id.id, 
							#'location_id':record.order_id.x_warehouse_id.lot_stock_id.id,
							'warehouse_id':record.order_id.x_warehouse_id.id,
							'state':'reserved',
						}
						if record.full_mo or record.root_stock or line.root_stock:
							vals['location_id']	=	record.ho_loc_id.id
							#elif :
							#	vals['location_id']=record.ho_loc_id.id
						else:
							vals['location_id'] = record.order_id.x_warehouse_id.lot_stock_id.id
						#_res=self._get_split_packs(cr, uid, line.qty_reserve, line.product_id.x_pack10, line.product_id.x_pack12, line.product_id.x_pack14, line.product_id.x_pack20, context=context)
						_res=self._get_split_packs(cr, uid, line.qty_reserve, line.product_id.id, context=context)
						vals['pack_10'] =_res['p10']
						vals['pack_12'] =_res['p12']
						vals['pack_14'] =_res['p14']
						vals['pack_20'] =_res['p20']
						vals['pack_xtra'] =_res['ext']
						res_id=self.pool.get('dincelmrp.production.reserve').create(cr, uid, vals, context=context)
						reserve_ids.append(res_id)
						#reserve_vals.append(vals)
						if line.product_id.x_prod_type 	and line.product_id.x_prod_type =="acs":
							_qty=line.qty_reserve
						else:
							_qty = line.order_length*line.qty_reserve*0.001
						#if line.product_id.x_prod_cat in['stocklength','customlength']:
						#	_qty=line.qty_reserve*line.order_length*0.001
						#else:
						#	_qty=line.qty_reserve
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
				 
				_name="%s (%s)" % (record.order_id.name, scount)
				 
				vals = {
						'order_id':record.order_id.id,
						'name':_name, #record.order_id.name+"-"+str(scount),
						'date_produce':record.date,
						'partner_id':record.order_id.partner_id.id,
						'project_id':record.order_id.x_project_id.id,
						'user_id':record.order_id.user_id.id,
						'part_no':scount,
						'location_id':record.location_id.id,
						'root_loc_id':record.ho_loc_id.id,
						}
				if len(create_ids)>0:
					vals['production_line'] = [(6, 0, create_ids)]		
				if len(reserve_ids)>0:
					vals['reserve_line'] = [(6, 0, reserve_ids)]	
				if record.full_mo:
					_type="mo"
				elif record.root_stock:
					_type="root"
				elif record.full_stock:
					_type="local"
				else:
					_type="root"	
				vals['stock_type'] = _type	
				
				obj.create(cr,uid, vals, context=context)	
				
				return True
				
		return False
		
	def _get_split_packs(self, cr, uid, _qty, _prodid, context=None):	
		#dcs_group
		#if line.product_id.x_prod_cat in ('stocklength','customlength'):
		prod	= self.pool.get('product.product').browse(cr, uid, _prodid, context=context)
		mrp		= self.pool.get('mrp.production') 
		
		_prodgrp	=prod.x_dcs_group
		_prod_cat	=prod.x_prod_cat
		_ptype		=prod.x_prod_type
		#_prodgrp,prod_cat,ptype
		_p10=0
		_p12=0
		_p14=0
		_p20=0
		 
		_ext=0
		if _ptype and _ptype=="acs":#do nothing ...acs...
			_ext=0
		else:
			if _prod_cat in ['customlength','stocklength']: #no accessories and others...
				if _prodgrp == "P110": #20L
					_p20, _ext = mrp.calc_packs_110(cr, uid, _qty, context)
				elif _prodgrp == "P155": #14L
					_p14, _ext = mrp.calc_packs_155(cr, uid, _qty, context)
				elif _prodgrp == "P200": #12L 	10L
					_p10, _p12, _ext = mrp.calc_packs_200(cr, uid, _qty, context)
				elif _prodgrp == "P275": #12L
					_p12, _ext = mrp.calc_packs_275(cr, uid, _qty, context)
				else:
					_ext = _qty
			
		res={
			'p10':_p10,
			'p12':_p12,
			'p14':_p14,
			'p20':_p20,
			'ext':_ext,
		}	
		
		return res
		
	def _get_split_packsxx(self, cr, uid, _qty, _en10, _en12, _en14, _en20, context=None):
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
		#if _count > 0:
		if _rem<0:
			if _en20 and _p20>0:	
				_p20-=1
				_rem+=20
			else:
				if _en14 and _p14>0:	
					_p14-=1
					_rem+=14
				else:
					if _en12  and _p12>0:	
						_p12-=1
						_rem+=12
					else:
						if _en10  and _p10>0:	
							_p10-=1
							_rem+=10
			
			_ext=_rem	
		#else:
		#	_ext=_rem
		res={
			'p10':_p10,
			'p12':_p12,
			'p14':_p14,
			'p20':_p20,
			'ext':_ext,
		}	
		#@_logger.error("schedule_mrpschedule_mrp_valsvaresresresls["+str(res)+"]")
		return res	
				 
		
class dincelmrp_schedule_mrp_line(osv.osv_memory):
	_name = "dincelmrp.schedule.mrp.line"
	_columns = {
		'schedulemrp_id': fields.many2one('dincelmrp.schedule.mrp', 'MRP Reference'),
		'product_id': fields.many2one('product.product', 'Product'),
		'order_length':fields.float("Stock Length",digits_compute= dp.get_precision('Int Number')),	
		'product_qty':fields.float("Qty Ordered"),	
		'qty_available':fields.float("Qty Stock (B)",digits_compute= dp.get_precision('Int Number')),	
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
		'full_mo':fields.boolean('MO'),
		'full_stock':fields.boolean('Stock'),
		'root_stock':fields.boolean('Head Office'),
		'qty_root':fields.integer("Qty Head Office (A)"),	
		'is_headoffice':fields.boolean('Is Headoffice'),
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
	