from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
import datetime
import logging
_logger = logging.getLogger(__name__)

class dincelwarehouse_delivery_docket(osv.osv_memory):
	_name = "dincelwarehouse.delivery.docket"
	#_description = "Sales Make MRP"
	_columns = {
		'date': fields.datetime('Date'),
		'date_actual': fields.datetime('Date Actual'),
		'order_id': fields.many2one('sale.order', 'Sale Order'),
		'partner_id': fields.many2one('res.partner', 'Partner'),
		'project_id': fields.many2one('res.partner', 'Project/Site'),
		'contact_id': fields.many2one('res.partner', 'Contact', domain=[('x_is_project', '=', False)]),
		'order_code':fields.char('DCS Code'),
		'pudel':fields.selection([
			('pu','Pickup'),
			('del','Delivery'),
			], 'Pickup/Delivery'),
		'trucks':fields.integer('Trucks', size=2),	
		'packs':fields.integer('Packs', size=2),	
		'comments':fields.char('Comments'),
		'scheduled_by': fields.many2one('res.users','Scheduled By'),
		'products':fields.char('Products'),
		'picking_lines':fields.one2many('dincelwarehouse.docket.line', 'picking_id', 'Picking Lines'),
		'reserve_lines':fields.one2many('dincelwarehouse.docket.reserve.line', 'picking_id', 'Reserve Lines'),
		'source_location_id': fields.many2one('stock.location', 'Source Location'),
		'destination_location_id': fields.many2one('stock.location', 'Destination Location'),
		'warehouse_id': fields.many2one('stock.warehouse','Dispatch Location'),	
		'delivery_to': fields.char('Deliver To'),	
		'qty':fields.float("Qty test"),
		'vehicle_type': fields.selection([
			('bdouble', 'B-Double'),
			('semi', 'Semi'),
			('rigid', '8 Metre Rigid'),
			('utility', 'Utility'),
			('other', 'Other'),
			], 'Vehicle Type'),	
		'recipient_full_name':fields.char('Recipient Full Name'),
		'vehicle_rego':fields.char('Vehicle REGO'),
		'trailer_rego':fields.char('Trailer REGO'),
		'trailer_rego_na':fields.boolean('Trailer REGO N/A'),	
		'recipient_license':fields.char('License No'),
		'schedule_id': fields.many2one('dincelwarehouse.sale.order.delivery', 'Deivery Schedule'),
	}

	def create_docket_dcs(self, cr, uid, ids, context=None):
		record = self.browse(cr, uid, ids[0], context=context)
		err_found	= False
		err_line 	= 0
		err_msg 	= ""
		qty_picked	= 0
		
		for line in record.picking_lines:
			err_line+=1
			
			if line.product_id.type != "service":
				
				if line.qty_picked and line.qty_picked > 0:
					if line.qty_onhand<=0:
						err_msg ='Invalid picking qty found or product not produced yet at line '+str(err_line)+'.'
						raise osv.except_osv(_('Error!'),_(err_msg))
					else:
						qty_picked+=line.qty_picked
						if line.qty_picked>line.qty_remain:
							err_msg ='Invalid picking qty found at line '+str(err_line)+'.'
							raise osv.except_osv(_('Error!'),_(err_msg))
					#if not line.qty_remain or line.qty_remain==0:
					#	err_msg ='Invalid remaining qty found at line '+str(err_line)+'.'
					#	raise osv.except_osv(_('Error!'),_(err_msg))
					#	return False
					#else:
					#	qty_remain = line.qty_remain
					#	if line.qty_onhand < line.qty_picked or qty_remain < line.qty_picked:
					#		err_msg ='Error in pickup qty at line '+str(err_line)+'.'	
					#		raise osv.except_osv(_('Error!'),_(err_msg))
					#		return False
				else:
					qty_picked+=line.qty_picked 
		err_line 	= 0
		for line in record.reserve_lines:
			err_line+=1
			if line.product_id.type != "service":
				if line.qty_picked and line.qty_picked > 0:
					qty_picked+=line.qty_picked
					if line.qty_picked>line.qty_remain:
						err_msg ='Invalid picking qty found at reserve line '+str(err_line)+'.'
						raise osv.except_osv(_('Error!'),_(err_msg))
					#if not line.qty_remain or line.qty_remain==0:
					#	err_msg ='Invalid remaining qty found at reserve line '+str(err_line)+'.'
					#	raise osv.except_osv(_('Error!'),_(err_msg))
					#	return False
					#else:
					#	qty_remain = line.qty_remain
					#	if line.qty_onhand < line.qty_picked or qty_remain < line.qty_picked:
					#		err_msg ='Error in pickup qty at reserve line '+str(err_line)+'.'	
					#		raise osv.except_osv(_('Error!'),_(err_msg))
					#		return False
				else:
					qty_picked+=line.qty_picked
					
		if qty_picked <= 0 and not err_found:
			err_msg ='Please select at least on picking item!'
			raise osv.except_osv(_('Error!'),_(err_msg))
			return False
		 
		if not err_found:

			line_sn		= 0
			
			_oprod 		= self.pool.get('dincelproduct.product')
			pick_obj 	= self.pool.get('dincelstock.pickinglist')
			line_obj 	= self.pool.get('dincelstock.pickinglist.line')
			
			_ids_done 	= pick_obj.search(cr, uid, [('origin','=',record.order_id.name)], context=context)
			_count 		= len(_ids_done) + 1
			_name 		= record.order_id.name +"-"+ str(_count)
			#_dt=str(record.date)
			_dt=self.pool.get('dincelstock.transfer').get_au_datetime(cr, uid, record.date)
			_dt=str(_dt)[:10]
			#_dt=_dt[:10]
			vals ={
				'name': _name,
				'pick_no': _count,
				'origin': record.order_id.name,
				'state': 'draft',
				'date_picking': _dt,
				'time_picking': record.date,
				'user_id': uid,
				'partner_id': record.order_id.partner_id.id,
				'pick_order_id': record.order_id.id,
				'pudel':record.pudel,
				'delivery_to':record.delivery_to,
				'vehicle_type':record.vehicle_type,
				'print_transport':True,
				'trailer_rego_na':record.trailer_rego_na,
			}
			if record.order_id.x_project_id:
				vals['project_id']=record.order_id.x_project_id.id
			if record.recipient_full_name:
				vals['recipient_full_name']=record.recipient_full_name
			if record.vehicle_rego:
				vals['vehicle_rego']=record.vehicle_rego
			if record.recipient_license:
				vals['recipient_license']=record.recipient_license	
			if not record.trailer_rego_na:
				vals['trailer_rego']=record.trailer_rego
			
			_dest_id=None
			if record.schedule_id:
				vals['schedule_id']=record.schedule_id.id
			if record.warehouse_id:
				vals['warehouse_id']=record.warehouse_id.id
			if record.source_location_id:
				vals['source_location_id']=record.source_location_id.id
			if record.destination_location_id:
				_dest_id=record.destination_location_id.id
				vals['destination_location_id']=_dest_id
			if record.contact_id:
				vals['contact_id']=record.contact_id.id 
			
			#-- create picking list	
			pick_id = pick_obj.create(cr, uid, vals, context=context)
			
			myDict = {}
			for line1 in record.picking_lines:
				#_key = str(line1.product_id.id)+"_"+str(int(line1.order_length))
				
				_key = str(line1.item_key)
				_qty1=line1.qty_picked 
				_remain1=line1.qty_remain-_qty1
				if line1.qty_picked and line1.qty_picked > 0:
					if line1.order_length and (line1.product_id.x_prod_cat in['stocklength','customlength']):
						qty_moved1=line1.order_length*line1.qty_picked *0.001
					else:
						qty_moved1=line1.qty_picked 
				else:
					qty_moved1=0
					
				vals = {
						'product_id': line1.product_id.id,
						'ship_qty': _qty1, #>>no matter what UOM, LM or Each, put the picking qty here for dispatch
						'pickinglist_id': pick_id,
						'origin': record.order_id.name,
						'order_length': line1.order_length,
						'price_unit': line1.price_unit,
						'disc_pc':line1.disc_pc,
						'qty_order':line1.qty_panel,
						'qty_remain':int(_remain1),
						'qty_moved':int(qty_moved1),
						'ytd_delivered':int(line1.qty_delivered),
						'qty_res':0,
						'product_uom':line1.product_uom.id,
						'region_id':0,
						'coststate_id':0,
						'packs':'',
					}
					
				vals['name']= line1.product_id.name
				if line1.region_id:
					vals['region_id']= line1.region_id.id	
				if line1.coststate_id:
					vals['coststate_id']= line1.coststate_id.id		
				if line1.packs:
					vals['packs']=line1.packs 
				if line1.location_id:
					vals['location_id']=line1.location_id.id 	
				myDict[_key]=vals
				#_logger.error("destination_location_item_qty_movedqty_movedqty_moved-sales-line1["+str(line1)+"]]")
				if qty_moved1 > 0:#>>here the act qty can be in LM or each depending upon >> for account purpose...
					_oprod.record_stock_shipped(cr, uid, record.order_id.id, line1.product_id.id, line1.product_uom.id, qty_moved1, _qty1, line1.order_length, _dest_id,'sales', context=context)
					#self.pool.get('dincelproduct.inventory').qty_decrement(cr, uid, line1.product_id.id, line1.order_length, _qty1, context = context)
					#>> only required stock decrement when reserve 
					
					#_logger.error("destination_location_item_qty_movedqty_movedqty_moved-sales["+str(qty_moved1)+"]]")
			#_logger.error("destination_location_item_myDictmyDictmyDict["+str(myDict)+"]]")	
			for line in record.reserve_lines:
				#_key = str(line.product_id.id)+"_"+str(int(line.order_length))
				_key = str(line.item_key)
				
				_qty=line.qty_picked 
				_qtyorder2=line.qty_panel
				_qtyres=_qty
				if line.qty_picked and line.qty_picked > 0:
					if line.order_length and (line.product_id.x_prod_cat in['stocklength','customlength']):
						qty_moved=line.order_length*line.qty_picked *0.001
					else:
						qty_moved=line.qty_picked 
				else:
					qty_moved=0
				
				if myDict.has_key(_key):
					vals= myDict[_key]
					qty_order=float(vals['qty_order'])+_qtyorder2 #total order qty
					qty_ship=float(vals['ship_qty'])+_qty #total ship on this docket....
					ytd_delivered=int(vals['ytd_delivered']) #get existing ytd qty
					ytd_delivered+=int(line.qty_delivered)	#add ytd qty of current line	
					ytd_delivered+=_qty					 #add current ship qty for ytd delivered total
					ytd_delivered+=int(vals['ship_qty']) #, + from production ship [eg refer.181-12-7] [8/11/17]
					qty_remain=qty_order-ytd_delivered
					
					vals['qty_order']	=	qty_order
					vals['ship_qty']	=	qty_ship	
					vals['ytd_delivered']	=ytd_delivered
					vals['qty_moved']	=	float(vals['qty_moved'])+qty_moved
					vals['qty_res']		=	float(vals['qty_res'])+_qtyres
					vals['qty_remain']	=	qty_remain
				else:
					_remain1=line.qty_remain-_qty
					vals = {
						'product_id': line.product_id.id,
						'ship_qty': _qty, #>>no matter what UOM, LM or Each, put the picking qty here for dispatch
						'pickinglist_id': pick_id,
						'origin': record.order_id.name,
						'order_length': line.order_length,
						'price_unit': line.price_unit,
						'disc_pc':line.disc_pc,
						'qty_order':line.qty_panel,
						'qty_remain':int(_remain1),
						'qty_moved':int(qty_moved),
						'product_uom':line.product_uom.id,
						'ytd_delivered':int(line.qty_delivered),
						'qty_res':_qtyres,
						'region_id':0,
						'coststate_id':0,
						'packs':'',
					}
					vals['name']		=   line.product_id.name
					vals['ship_qty']	=	_qty
					vals['qty_moved']	=	qty_moved
					vals['qty_remain']	=	_remain1 #todo check this value
					if line.region_id:
						vals['region_id']= line.region_id.id	
					if line.coststate_id:
						vals['coststate_id']= line.coststate_id.id		
					if line.packs:
						vals['packs']=line.packs 
					if line.location_id:
						vals['location_id']=line.location_id.id 
				#_logger.error("destination_location_item_qty_movedqty_movedqty_moved-reserve-line["+str(line)+"]]")
				myDict[_key]=vals
				if qty_moved > 0:#>>here the act qty can be in LM or each depending upon >> for account purpose...
					_oprod.record_stock_shipped(cr, uid, record.order_id.id, line.product_id.id, line.product_uom.id, qty_moved, _qty, line.order_length, _dest_id,'reserve-deliverd', context=context)
					#self.pool.get('dincelproduct.inventory').qty_decrement(cr, uid, line.product_id.id, line.order_length, _qty, context = context)
					#>> only required stock decrement when reserve 
					
					#_logger.error("destination_location_item_qty_movedqty_movedqty_moved-reserve["+str(qty_moved)+"]]")
			for _key in myDict:
				_item=myDict[_key]
				#_logger.error("destination_location_item_itemicklist_key["+str(_item)+"]["+str(_key)+"]")
				vals = {
					'product_id': int(_item['product_id']),
					'ship_qty': float(_item['ship_qty']), #>>no matter what UOM, LM or Each, put the picking qty here for dispatch
					'pickinglist_id': int(_item['pickinglist_id']),
					'origin': _item['origin'],
					'order_length': _item['order_length'],
					'price_unit': float(_item['price_unit']),
					'disc_pc':float(_item['disc_pc']),
					'qty_order':float(_item['qty_order']),
					'qty_remain':float(_item['qty_remain']),
					'qty_moved':float(_item['qty_moved']),
					'product_uom':int(_item['product_uom']),
					'name':_item['name'],
					'qty_res_picked':_item['qty_res'],
				}
					
				if _item['location_id']:
					vals['location_id']=int(_item['location_id'])
				if _item['region_id']:
					vals['region_id']= int(_item['region_id'])
				if _item['coststate_id']:
					vals['coststate_id']= int(_item['coststate_id'])	
					
				if _item['packs']:
					vals['packs']=_item['packs']
				#_logger.error("destination_loc_item_itemd_savepicklist["+str(vals)+"]["+str(_item)+"]")	
				
				line_obj.create(cr, uid, vals, context=context) #>> this is docket line items..so qty is not in LM, but as per picking items
				#>> qty_moved=float(_item['qty_moved']) :already done above.....reserve and pickup....>>>
				#if qty_moved and qty_moved>0:
				#	_oprod.record_stock_shipped(cr, uid, record.sale_order_id.id, line.product_id.id, line.product_uom.id, qty_moved, _qty, line.order_length, _dest_id, context=context)
			
			view_id	= self.pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'dincelstock.delivery.form.view')], limit=1) 	
			
			value = {
				'domain': str([('id', 'in', pick_id)]),
				'view_type': 'form',
				'view_mode': 'form',
				'res_model': 'dincelstock.pickinglist',
				'view_id': view_id,
				'type': 'ir.actions.act_window',
				'name' : _('Delivery'),
				'res_id': pick_id
			}
			
			return value	
			
		return {}
	def on_change_qty(self, cr, uid, ids, _qty, _lines, context=None):
		new_lines = []
		res_lines = []
		vals= {}
		domain={}
		active_id = context and context.get('active_id', False) or False
		if context and active_id:
			_objDeli = self.pool.get('dincelwarehouse.sale.order.delivery').browse(cr, uid, active_id, context=context)
			if _objDeli.hold_supply==True:
				if _objDeli.authorize_hold!=True:
					raise osv.except_osv(_('Error!'), _('Hold supply enabled for this customer, please contact account team or admin manager to continue !!'))
			if _objDeli.stop_supply==True:
				if _objDeli.authorize_blacklist!=True:
					raise osv.except_osv(_('Error!'), _('Stop supply enabled for this customer, please contact account team or admin manager to continue !!'))\

			if _objDeli.pending_invoice==True:
				if _objDeli.authorize_docket!=True:
					raise osv.except_osv(_('Error!'), _('Pending COD invoice/s found, please contact account team or admin manager to continue !!'))
					
			#_logger.error("on_change_qty.on_change_qty["+str(_objDeli.pending_invoice)+"]["+str(_objDeli.authorize_docket)+"]") 
			#_obj = self.pool.get('sale.order').browse(cr, uid, active_id, context=context)
			_obj=_objDeli.order_id
			
			source_location_id=None
			_prod = self.pool.get('dincelproduct.product')
			oprod = self.pool.get('product.product')
			
			if _obj.x_warehouse_id:
				vals['warehouse_id']=_obj.x_warehouse_id.id
				_ptype	=self.pool.get('stock.picking.type')
				_ids	=_ptype.search(cr, uid, [('code', '=', 'outgoing'),('warehouse_id', '=', _obj.x_warehouse_id.id)], limit=1) 	
				if _ids:
					_ptype 	= _ptype.browse(cr, uid, _ids[0], context=context)
					source_location_id=_ptype.default_location_src_id.id
					vals['source_location_id']		=source_location_id
					vals['destination_location_id']	=_ptype.default_location_dest_id.id	
					
			for line in _obj.order_line:
				if line.product_id.x_prod_cat not in['freight','deposit','service']  and line.product_id.type !="service":
					_found		= False
					_reserved	= False
					_mrpitem	= False
					#_split_item = False
					_location	= source_location_id
					_location2	= False
					_qtyonhand	= 0
					_qty_delivered	=0
					_qty_remain		=0
					
					_key = str(line.product_id.id)+"_"+str(int(line.x_order_length))
					 
					
					
					if line.product_id.x_prod_cat != "customlength":
						order_length = False
					else:
						order_length = line.x_order_length
						
					
					#_qty_delivered 	= _prod.qty_delivered_net_v2(cr, uid, ids, line.product_id.id, order_length, _obj.id)		 
					#_qtyonhand 		= _prod.qty_produced_net(cr, uid, ids, line.product_id.id, order_length, _obj.id)
					#_qtyonhand 		= _qtyonhand - _qty_delivered
					
					#_qty_remain=line.x_order_qty-_qty_delivered
					#_qty_remain=int(_qty_remain)
					#-------------------------------------------------------------------------------------------------------
					for ibt in _obj.x_ibt_ids:
						if ibt.state in ['sent','done']:
							for _item in ibt.picking_line:##this loop is required for location...
								if _item.product_id.id == line.product_id.id and _item.prod_length==line.x_order_length:
									#if _item.location_id:
									_location=ibt.destination_location_id.id 
									_found=True
									break
				 
					qty_reserve=0
					qty_mrp=0
					for mrp in _obj.x_mrp_lines_dcs: #all MRP items (MRP-1, MRP-2, etc)#this loop is required for location2...
						for _item in mrp.reserve_line:
							if _item.product_id.id == line.product_id.id and _item.order_length==line.x_order_length:
								_reserved=True
								qty_reserve=_item.reserve_qty
								if _item.location_id and _found==False:
									_location2=_item.location_id.id
									break#@_location2=_location
					 
					
					sql="""select sum(m.x_order_qty) from mrp_production m,sale_order o where 
							m.x_sale_order_id=o.id and m.x_sale_order_id='%s' and m.product_id='%s'  
							""" % (_obj.id, line.product_id.id)
					if line.x_order_length:
						sql+=" and m.x_order_length='%s'" % (int(line.x_order_length))
					cr.execute(sql)
					rows = cr.fetchone()
					if rows and len(rows) > 0 and rows[0]:	
						qty_mrp= int(rows[0])
						if qty_mrp>0:
							_mrpitem=True 
					
					vals1 = {
						#'qty_panel':qty_reserve,#line.x_order_qty,
						'qty':line.product_uom_qty,
						#'qty_onhand':_qtyonhand,
						#'qty_delivered':_qty_delivered,
						#'qty_remain':_qty_remain,
						'product_id': line.product_id.id or False,
						'dcs_itemcode':line.product_id.x_dcs_itemcode,
						'order_length':line.x_order_length or 0.0,
						'product_uom':line.product_uom.id or False,
						'price_unit': line.price_unit,
						'disc_pc':line.discount,
						'sale_order_id':_obj.id,
						'item_key':_key,
						}
					if line.x_region_id:
						vals1['region_id']= line.x_region_id.id	
					if line.x_coststate_id:
						vals1['coststate_id']= line.x_coststate_id.id		
						
					
					
					_qty_delivered 	= _prod.qty_delivered_net_v2(cr, uid, ids, line.product_id.id, order_length, _obj.id)		
					_qty_produced 	= _prod.qty_produced_net(cr, uid, ids, line.product_id.id, order_length, _obj.id)				
					if _mrpitem==True and _reserved==True:
						
						if qty_reserve>0: 
							qty_res_picked=0
							sql="""select sum(r.qty_res_picked) from dincelstock_pickinglist_line r, dincelstock_pickinglist p 
								where r.pickinglist_id=p.id and
								p.pick_order_id ='%s' and r.product_id='%s'""" % (_obj.id, line.product_id.id)
							if line.x_order_length:
								sql+=" and r.order_length='%s'" % (int(line.x_order_length))
							cr.execute(sql)
							rows = cr.fetchone()
							if rows and len(rows) > 0 and rows[0]:
								qty_res_picked= int(rows[0])
								_qty_delivered-=qty_res_picked
							
							valres=vals1.copy()
							valres['qty_onhand']= qty_reserve-qty_res_picked	 #Available
							valres['qty_delivered']= qty_res_picked	
							valres['qty_remain']= qty_reserve-qty_res_picked								
							valres['qty_panel']= qty_reserve
							if _location2:
								valres['location_id']=_location2	
							elif _location:
								valres['location_id']=_location	
							res_lines.append(valres)
							
						if qty_mrp>0:
							valmrp=vals1.copy()
							valmrp['qty_onhand']= _qty_produced	  #Produced
							valmrp['qty_delivered']= _qty_delivered	
							valmrp['qty_remain']= qty_mrp-_qty_delivered
							valmrp['qty_panel']= qty_mrp	
							if _location:
								valmrp['location_id']=_location	
							new_lines.append(valmrp)
							
					else:
						if _reserved:
							_qtyonhand  = _prod.qty_stock_reserved_new( cr, uid, ids,line.product_id.id,order_length, _obj.id) 
							_qtyonhand = _qtyonhand - _qty_delivered
						else:
							_qtyonhand=_qty_produced
						if _location2:
							_location=_location2
						if _location:
							vals1['location_id']=_location	
						if qty_reserve>0: 
							valres=vals1.copy()
							valres['qty_onhand']= _qtyonhand	 #Available
							valres['qty_delivered']= _qty_delivered	
							valres['qty_remain']= line.x_order_qty-_qty_delivered							
							valres['qty_panel']= line.x_order_qty	
							res_lines.append(valres)
						if qty_mrp>0:
							valmrp=vals1.copy()
							valmrp['qty_onhand']= _qtyonhand	  #Produced
							valmrp['qty_delivered']= _qty_delivered	
							valmrp['qty_remain']= line.x_order_qty-_qty_delivered
							valmrp['qty_panel']= line.x_order_qty	
							new_lines.append(valmrp)
					 
				vals['picking_lines']	= new_lines
				vals['reserve_lines']	= res_lines
				vals['order_id']		= _obj.id
				
				if _objDeli.pudel:
					vals['pudel']=_objDeli.pudel
					
				_addr = ""	
				if _obj.x_street:
					_addr = _obj.x_street
				if _obj.x_suburb:
					_addr += " " + _obj.x_suburb
				if _obj.x_state_id:
					_addr += " " + self.pool.get('res.country.state').browse(cr, uid, _obj.x_state_id.id, context=context).code
				if _obj.x_postcode:
					_addr += " " + _obj.x_postcode
				
				vals['delivery_to']	=	_addr
				vals['project_id']	=	_obj.x_project_id.id
				vals['partner_id']	=	_obj.partner_id.id
				vals['contact_id']	=	_obj.x_contact_id.id
				vals['order_code']	=	_obj.origin
				vals['schedule_id']	=	active_id
				dt=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
				vals['date']	=	dt#self.pool.get('dincelstock.transfer').get_au_datetime(cr, uid, dt)
				c_ids1 = self.pool.get('res.partner').search(cr, uid, [('parent_id', '=', _obj.partner_id.id)], context=context)
				 
				c_ids2 = self.pool.get('res.partner').search(cr, uid, [('parent_id', '=', _obj.x_project_id.id)], context=context)
				c_ids1 = c_ids1 + c_ids2
			 
				if len(c_ids1) > 0:
					domain  = {'contact_id': [('id','in', (c_ids1))]}
	
				
		return {'value':vals,'domain': domain }
		
	def on_change_qtyxx(self, cr, uid, ids, _qty, _lines, context=None):
		new_lines = []
		res_lines = []
		vals= {}
		domain={}
		active_id = context and context.get('active_id', False) or False
		if context and active_id:
			_objDeli = self.pool.get('dincelwarehouse.sale.order.delivery').browse(cr, uid, active_id, context=context)
			if _objDeli.hold_supply==True:
				raise osv.except_osv(_('Error!'), _('Hold supply enabled for this customer, please contact account team or admin manager to continue !!'))
			if _objDeli.stop_supply==True:
				if _objDeli.authorize_blacklist!=True:
					raise osv.except_osv(_('Error!'), _('Stop supply enabled for this customer, please contact account team or admin manager to continue !!'))\

			if _objDeli.pending_invoice==True:
				if _objDeli.authorize_docket!=True:
					raise osv.except_osv(_('Error!'), _('Pending COD invoice/s found, please contact account team or admin manager to continue !!'))
					
			#_logger.error("on_change_qty.on_change_qty["+str(_objDeli.pending_invoice)+"]["+str(_objDeli.authorize_docket)+"]") 
			#_obj = self.pool.get('sale.order').browse(cr, uid, active_id, context=context)
			_obj=_objDeli.order_id
			
				
			for line in _obj.order_line:
				if line.product_id.x_prod_cat not in['freight','deposit','service']:
					
					
					_prod = self.pool.get('dincelproduct.product')
					
					order_length=line.x_order_length
					
					_key = str(line.product_id.id)+"_"+str(int(line.x_order_length))
					
					#if line.product_id.x_prod_cat not in['stocklength','customlength']:
					if line.product_id.x_prod_cat != "customlength":
						order_length = False
						
					#qty_delivered =_prod.qty_delivered_net(cr, uid, ids, line.product_id.id, order_length, _obj.id)
					qty_delivered =_prod.qty_delivered_net_v2(cr, uid, ids, line.product_id.id, order_length, _obj.id)		 
					_qtyonhand = _prod.qty_produced_net(cr, uid, ids, line.product_id.id, order_length, _obj.id)
					_qtyonhand = _qtyonhand - qty_delivered#_prod.qty_delivered_net(cr, uid, ids, line.product_id.id, order_length, _obj.id)
					
					_qty_remain=line.x_order_qty-qty_delivered
					_qty_remain=int(_qty_remain)
					
					vals = {
						'qty_panel':line.x_order_qty,
						'qty':line.product_uom_qty,
						'qty_onhand':_qtyonhand,
						'qty_delivered':qty_delivered,
						'qty_remain':_qty_remain,
						'product_id': line.product_id.id or False,
						'dcs_itemcode':line.product_id.x_dcs_itemcode,
						'order_length':line.x_order_length or 0.0,
						'product_uom':line.product_uom.id or False,
						'price_unit': line.price_unit,
						'disc_pc':line.discount,
						'sale_order_id':_obj.id,
						'item_key':_key,
						}
					
					#...cause common delivered qty....
					#qty_delivered =_prod.qty_reserved_delivered_net(cr, uid, ids, line.product_id.id, order_length, _obj.id)
					#		 qty_stock_reserved_new(self, cr, uid, ids, product_id, order_length, order_id, context=None)
					_qtyonhand = _prod.qty_stock_reserved_new( cr, uid, ids,line.product_id.id,order_length, _obj.id)#.qty_stock_reserved(cr, uid, ids, line.product_id.id, order_length, _obj.id)
					_qtyonhand = _qtyonhand - qty_delivered#_prod.qty_delivered_net(cr, uid, ids, line.product_id.id, order_length, _obj.id)
					_qty_remain=line.x_order_qty-qty_delivered
					_qty_remain=int(_qty_remain)
					vals_res = {
						'qty_panel':line.x_order_qty,
						'qty':line.product_uom_qty,
						'qty_onhand':_qtyonhand,
						'qty_delivered':qty_delivered,
						'qty_remain':_qty_remain,
						'product_id': line.product_id.id or False,
						'dcs_itemcode':line.product_id.x_dcs_itemcode,
						'order_length':line.x_order_length or 0.0,
						'product_uom':line.product_uom.id or False,
						'price_unit': line.price_unit,
						'disc_pc':line.discount,
						'sale_order_id':_obj.id,
						'item_key':_key,
						}
						
					if line.x_region_id:
						vals['region_id']= line.x_region_id.id	
						vals_res['region_id']= line.x_region_id.id	
					
					if line.x_coststate_id:
						vals['coststate_id']= line.x_coststate_id.id	
						vals_res['coststate_id']= line.x_coststate_id.id	
						
					#if _qty_remain>0:	#so that the dockt prints all items includig remaing item as zero and zeros shipped
					#if this condition is placed then the docket will print only item shipped>0 but no historical shipped items (even though remaing qty==0)
					#todo....have it enabled...but while saving in dockets (add items of historical movements with zero remaining qty) for dcs compatibiluty
					#------------------------------------------
					new_lines.append(vals)
					if _qtyonhand>0:
						res_lines.append(vals_res)
				#vals= {}
				
				vals= {'picking_lines': new_lines, 'reserve_lines': res_lines,'order_id': _obj.id}
				
				if _objDeli.pudel:
					vals['pudel']=_objDeli.pudel
					
				_addr = ""	
				if _obj.x_street:
					_addr = _obj.x_street
				if _obj.x_suburb:
					_addr += " " + _obj.x_suburb
				if _obj.x_state_id:
					_addr += " " + self.pool.get('res.country.state').browse(cr, uid, _obj.x_state_id.id, context=context).code
				if _obj.x_postcode:
					_addr += " " + _obj.x_postcode
				vals['delivery_to']=_addr
				vals['project_id']=_obj.x_project_id.id
				vals['partner_id']=_obj.partner_id.id
				vals['contact_id']=_obj.x_contact_id.id
				vals['order_code']=_obj.origin
				vals['schedule_id']=active_id
				
				c_ids1 = self.pool.get('res.partner').search(cr, uid, [('parent_id', '=', _obj.partner_id.id)], context=context)
				 
				c_ids2 = self.pool.get('res.partner').search(cr, uid, [('parent_id', '=', _obj.x_project_id.id)], context=context)
				c_ids1 = c_ids1 + c_ids2
			 
				if len(c_ids1) > 0:
					domain  = {'contact_id': [('id','in', (c_ids1))]}
				 
				#_logger.error("destination_location_iddestination_location_id_savepicklistc_ids1c_ids1["+str(c_ids1)+"]["+str(domain)+"]")
				
				#return {'value': val,'domain': domain}
				
				if _obj.x_warehouse_id:
					vals['warehouse_id']=_obj.x_warehouse_id.id
					_ptype	=self.pool.get('stock.picking.type')
					_ids	=_ptype.search(cr, uid, [('code', '=', 'outgoing'),('warehouse_id', '=', _obj.x_warehouse_id.id)], limit=1) 	
					if _ids:
						_ptype 	= _ptype.browse(cr, uid, _ids[0], context=context)
						vals['source_location_id']		=_ptype.default_location_src_id.id
						vals['destination_location_id']	=_ptype.default_location_dest_id.id	
		return {'value':vals,'domain': domain }
		
 
	def _get_init_qty(self, cr, uid, context=None):
		return 1
	 
		
	def record_schedule(self, cr, uid, ids, context=None):
		record = self.browse(cr, uid, ids[0], context=context)
	 
		return {}
 
	_defaults = {
		'date': fields.datetime.now(),#fields.date.context_today,
		#'sale_order_id': _get_sale_order_id,
		'qty': _get_init_qty,
		}
 

class dincelwarehouse_docket_reserve_line(osv.osv_memory):
	_name = "dincelwarehouse.docket.reserve.line"
	_columns = {
		'picking_id': fields.many2one('dincelwarehouse.delivery.docket', 'Docket Reference'),
		'product_id': fields.many2one('product.product', 'Product'), 
		'dcs_itemcode': fields.related('product_id', 'x_dcs_itemcode', type='char', string='Product Code',store=False),
		'location_id': fields.many2one('stock.location', 'Location'),
		'order_length':fields.float("Stock Length",digits_compute= dp.get_precision('Int Number')),	
		'qty':fields.float("Qty Ordered",digits_compute= dp.get_precision('Int Number')),	
		'qty_panel':fields.float("Qty Panel",digits_compute= dp.get_precision('Int Number')),	
		'qty_remain':fields.float("Qty Remain",digits_compute= dp.get_precision('Int Number')),	
		'pick_source':fields.selection([('reserve', 'Reserve'),('stock', 'Stock')], 'Source'),
		'qty_onhand':fields.float("Qty Available",digits_compute= dp.get_precision('Int Number')),	
		'qty_delivered':fields.float("Qty Delivered",digits_compute= dp.get_precision('Int Number')),	
		'qty_picked':fields.float("Qty  Picked",digits_compute= dp.get_precision('Int Number')),	
		'product_uom': fields.many2one('product.uom', 'Unit of Measure'),
		'price_unit':fields.float("Unit Price"),	
		'disc_pc':fields.float("Discount"),	
		'sale_order_id': fields.many2one('sale.order', 'Order Id'),
		'region_id': fields.many2one('dincelaccount.region', 'A/c Region'),
		'coststate_id':fields.many2one("res.country.state","Cost Centre"),
		'packs': fields.char('Packs'),
		'item_key': fields.char('Unique LineItem Key'), #note...used for mark save button manipulation....imp...
	}
	
	def get_stock_qty_source(self, cr, uid, ids,product_id,order_length, _source, order_id, context=None):
		product_obj = self.pool.get('product.product')
		_soo = self.pool.get('sale.order').browse(cr, uid, order_id, context=context)		
		_obj = self.pool.get('dincelproduct.product')
		prod = product_obj.browse(cr, uid, product_id, context=context)	
		if prod.x_prod_cat not in['stocklength','customlength']:
			order_length = False
		if _source == "reserve":#todo check later...
			_qty = _obj.qty_stock_reserved(cr, uid, ids, product_id, order_length,_soo.name)
		else:
			_qty = _obj.qty_produced_net(cr, uid, ids, product_id, order_length, order_id)
			_qty = _qty - _obj.qty_delivered_net(cr, uid, ids, product_id, order_length, order_id)
			'''sql ="SELECT SUM(product_qty) FROM stock_move_tmp WHERE move_type='mo-stock' AND product_id='"+str(product_id)+"'  "
			if order_length:
				sql += " AND order_length='"+str(order_length)+"'"
			cr.execute(sql)
			res = cr.fetchone()
			if res and res[0]!= None:
				_qty=(res[0])
				if order_length:
					_qty = int(_qty/((order_length)/1000))
			else:
				_qty=0'''
			#_qty = _obj.qty_stock_onhand(cr, uid, ids, product_id, order_length)
		return _qty
		
	def on_change_source(self, cr, uid, ids,product_id,order_length, _source,order_id, context=None):
		if context is None:
			context = {}
		#_qty  =0	
		#for data in self.browse(cr, uid, ids, context=context):#data = self.browse(cr, uid, ids[0], context=context)
		#product_id=data.product_id.id
		#order_length=data.order_length
		#_logger.error("on_change_sourceon_change_source["+str(product_id)+"]["+str(order_length)+"]")
		_qty = self.get_stock_qty_source(cr, uid, ids, product_id, order_length, _source, order_id, context=context)
		
		return {'value': {'qty_onhand': _qty}}
		
	
	def on_change_pickqty(self, cr, uid, ids, product_id, qty_onhand, qty_pick, context=None):
		product_obj = self.pool.get('product.product')
		prod = product_obj.browse(cr, uid, product_id, context=context)	
		'''TODO ENABLE THIS LOGIC after stock qty fixed....feb/6/2017
		if prod.type != "service":
			if qty_onhand < qty_pick:
				raise osv.except_osv(_('Error!'),_('Invalid quantity found!'))
				return False'''
		return True
		
	def on_change_qty(self, cr, uid, ids, qty_org,qty_order, qty_stock,qty_produce,qty_reserve, context=None):
		'''TODO ENABLE THIS LOGIC after stock qty fixed....feb/6/2017
		if qty_order < qty_produce:
			raise osv.except_osv(_('Error!'),_('Invalid quantity found!'))
			return False
		if qty_order < qty_reserve:
			raise osv.except_osv(_('Error!'),_('Invalid quantity found!'))
			return False
		return True'''
		return True
		
class dincelwarehouse_docket_line(osv.osv_memory):
	_name = "dincelwarehouse.docket.line"
	_columns = {
		'picking_id': fields.many2one('dincelwarehouse.delivery.docket', 'Docket Reference'),
		'product_id': fields.many2one('product.product', 'Product'),
		'dcs_itemcode': fields.related('product_id', 'x_dcs_itemcode', type='char', string='Product Code',store=False),
		'location_id': fields.many2one('stock.location', 'Location'),
		'order_length':fields.float("Stock Length",digits_compute= dp.get_precision('Int Number')),	
		'qty':fields.float("Qty Ordered",digits_compute= dp.get_precision('Int Number')),	
		'qty_panel':fields.float("Qty Panel",digits_compute= dp.get_precision('Int Number')),	
		'qty_remain':fields.float("Qty Remain",digits_compute= dp.get_precision('Int Number')),	
		'pick_source':fields.selection([('reserve', 'Reserve'),('stock', 'Stock')], 'Source'),
		'qty_onhand':fields.float("Qty Available",digits_compute= dp.get_precision('Int Number')),	
		'qty_delivered':fields.float("Qty Delivered",digits_compute= dp.get_precision('Int Number')),	
		'qty_picked':fields.float("Qty  Picked",digits_compute= dp.get_precision('Int Number')),	
		'product_uom': fields.many2one('product.uom', 'Unit of Measure'),
		'price_unit':fields.float("Unit Price"),	
		'disc_pc':fields.float("Discount"),	
		'sale_order_id': fields.many2one('sale.order', 'Order Id'),
		'region_id': fields.many2one('dincelaccount.region', 'A/c Region'),
		'coststate_id':fields.many2one("res.country.state","Cost Centre"),
		'packs': fields.char('Packs'),
		'item_key': fields.char('Unique LineItem Key'), #note...used for mark save button manipulation....imp...
	}
	
	def get_stock_qty_source(self, cr, uid, ids,product_id,order_length, _source, order_id, context=None):
		product_obj = self.pool.get('product.product')
		_soo = self.pool.get('sale.order').browse(cr, uid, order_id, context=context)		
		_obj = self.pool.get('dincelproduct.product')
		prod = product_obj.browse(cr, uid, product_id, context=context)	
		if prod.x_prod_cat not in['stocklength','customlength']:
			order_length = False
		if _source == "reserve":#todo check later...
			_qty = _obj.qty_stock_reserved(cr, uid, ids, product_id, order_length,_soo.name)
		else:
			_qty = _obj.qty_produced_net(cr, uid, ids, product_id, order_length, order_id)
			_qty = _qty - _obj.qty_delivered_net(cr, uid, ids, product_id, order_length, order_id)
			'''sql ="SELECT SUM(product_qty) FROM stock_move_tmp WHERE move_type='mo-stock' AND product_id='"+str(product_id)+"'  "
			if order_length:
				sql += " AND order_length='"+str(order_length)+"'"
			cr.execute(sql)
			res = cr.fetchone()
			if res and res[0]!= None:
				_qty=(res[0])
				if order_length:
					_qty = int(_qty/((order_length)/1000))
			else:
				_qty=0'''
			#_qty = _obj.qty_stock_onhand(cr, uid, ids, product_id, order_length)
		return _qty
		
	def on_change_source(self, cr, uid, ids,product_id,order_length, _source,order_id, context=None):
		if context is None:
			context = {}
		#_qty  =0	
		#for data in self.browse(cr, uid, ids, context=context):#data = self.browse(cr, uid, ids[0], context=context)
		#product_id=data.product_id.id
		#order_length=data.order_length
		#_logger.error("on_change_sourceon_change_source["+str(product_id)+"]["+str(order_length)+"]")
		_qty = self.get_stock_qty_source(cr, uid, ids, product_id, order_length, _source, order_id, context=context)
		
		return {'value': {'qty_onhand': _qty}}
		
	
	def on_change_pickqty(self, cr, uid, ids, product_id, qty_onhand, qty_pick, context=None):
		product_obj = self.pool.get('product.product')
		prod = product_obj.browse(cr, uid, product_id, context=context)	
		'''TODO ENABLE THIS LOGIC after stock qty fixed....feb/6/2017
		if prod.type != "service":
			if qty_onhand < qty_pick:
				raise osv.except_osv(_('Error!'),_('Invalid quantity found!'))
				return False
			'''
		return True	
	def on_change_qty(self, cr, uid, ids, qty_org,qty_order, qty_stock,qty_produce,qty_reserve, context=None):
		'''TODO ENABLE THIS LOGIC after stock qty fixed....feb/6/2017
		if qty_order < qty_produce:
			raise osv.except_osv(_('Error!'),_('Invalid quantity found!'))
			return False
		if qty_order < qty_reserve:
			raise osv.except_osv(_('Error!'),_('Invalid quantity found!'))
			return False'''
		return True 