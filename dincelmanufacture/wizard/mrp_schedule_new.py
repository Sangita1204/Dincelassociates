from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
import urllib2
import simplejson
from dateutil import parser
from datetime import date
import time 
import datetime
import logging
_logger = logging.getLogger(__name__)

class dincelmrp_schedule_new(osv.osv_memory):
	_name = "dincelmrp.schedule.new"
	_description = "Schedule MRP"
	_columns = {
		'date': fields.date('Date'),
		'item_lines':fields.one2many('dincelmrp.schedule.new.line', 'produce_id', 'MRP Lines'),
		'qty':fields.float("Qty test"),
	}
	
	def save_schedule(self, cr, uid, ids, context=None):	
		if context is None:
			context = {}
			
		record = self.browse(cr, uid, ids[0], context=context)
		if record.item_lines:
			#_obj_mrp	= self.pool.get('mrp.production')
			#_oprod 		= self.pool.get('dincelproduct.product')
			for line in record.item_lines:
				if line.mrp_id:
					#_qty=line.qty_curr_produce
					#if _qty and _qty>0:
					#	#_logger.error("save_productionsave_productionsave_production["+str(line.name)+"]["+str(_qty)+"]")
					#	#self._mrp_produced(cr, uid, ids, line.mrp_id.id, _qty,context)
						
		return True

	def _mrp_produced(self, cr, uid, ids, _id, _qty, context=None):
		production=self.pool.get('mrp.production')
		line=production.browse(cr, uid, _id, context)
		actmove 	= self.pool.get('dincelaccount.journal.dcs')
		_oprod 		= self.pool.get('dincelproduct.product')
		if line.state=="draft": #Note--> for the first time...
			qty		= 0
			est_mms = line.x_est_minute 
			if line.date_start:
				_start=line.date_start
			else:
				_start=line.date_planned
			
			dt_end  =  parser.parse(_start) +  datetime.timedelta(minutes = est_mms)
			production.action_confirm(cr, uid, [line.id], context=context)		
			# / 60
			# timedelta(hours=est_hrs)#time.strftime('%Y-%m-%d %H:%M:%S')
			sql = "UPDATE mrp_production SET x_start_mo='True',date_start='%s',date_finished='%s',state='in_production',x_curr_produced_qty=0,x_produced_qty='%s' WHERE id='%s' " % (str(_start),str(dt_end), str(qty), str(line.id))
			cr.execute(sql)
			actmove.mo_produce_start_journal_dcs(cr, uid, ids, line.id, context=context) #Note ->> WIP Journal
		if _qty > 0:
			#if line.x_curr_produced_qty > 0:
			qty=_qty
			curr_produced=qty
			if line.x_produced_qty:
				qty=qty+line.x_produced_qty
			if 	qty>line.x_order_qty:#---Note..some reasons more qty entered....then make the capping...
				qty=line.x_order_qty
				curr_produced=qty-line.x_produced_qty
			
			
			if curr_produced>0:	
				#sql ="UPDATE mrp_production SET x_curr_produced_qty=0,x_produced_qty=" +str(qty)+" WHERE id ='%s'" % (str(line.id))
				#cr.execute(sql)
				#_crit="x_curr_produced_qty=0,x_produced_qty=" +str(qty)+""
				
		#if line.x_full_mo==True:
		#	if line.state!="done":
				data 	= production.browse(cr, uid, line.id, context=context)
				if line.state=="draft":
					#_logger.error("dincelmrp_mrpdincelmrp_mrp2222["+str(line.id)+"]")	
					sql = "UPDATE mrp_production SET date_start='%s',x_curr_produced_qty=0,x_produced_qty='%s' WHERE id='%s' " % (str(time.strftime('%Y-%m-%d %H:%M:%S')),str(qty), str(line.id))
					cr.execute(sql)
				else:
					sql ="UPDATE mrp_production SET x_curr_produced_qty=0,x_produced_qty=%s WHERE id ='%s'" % (str(qty),str(line.id))
					cr.execute(sql)
				#-------------------------------------------------
				#actmove = self.pool.get('dincelaccount.journal.dcs')
				#return self.write(cr, uid, ids, {'state': 'in_production', 'date_start': time.strftime('%Y-%m-%d %H:%M:%S')})
				
				
				#-------------------------------------------------
				#production.action_in_production()
				#actmove = self.pool.get('dincelaccount.journal.dcs')
				#actmove.mo_produce_start_journal_dcs(cr, uid, ids, ids[0], context=context) 
				#return self.write(cr, uid, ids, {'state': 'in_production', 'date_start': time.strftime('%Y-%m-%d %H:%M:%S')})
				#actmove = self.pool.get('dincelaccount.journal.dcs')
				#------------------------------------------------
				#actmove.mo_produced_qty_journal_dcs(cr, uid, ids, line.id, line.product_qty, context=context) 	
				actmove.mo_produced_qty_journal_dcs(cr, uid, ids, line.id, line.product_qty, context=context) 	
				#Journal entry ----------------------	
				if line.product_id.x_prod_cat in['stocklength','customlength']:
					#_qty=(line.product_qty/(0.001*line.x_order_length))
					_qty_lm= curr_produced*0.001*line.x_order_length
				else:
					#_qty=line.product_qty
					_qty_lm=curr_produced
					
				if line.x_sale_order_id:
					_mtype="mo-sales"
				else:
					_mtype="mo-stock" #>>for stock only no sales assigned....
					#self.pool.get('dincelproduct.inventory').qty_increment(cr, uid, line.product_id.id, line.x_order_length, _qty, context = context)
					self.pool.get('dincelproduct.inventory').qty_increment(cr, uid, line.product_id.id, line.x_order_length, curr_produced, context = context)
					
				
				#_oprod.record_stock_mrp_new(cr, uid, line.id, line.product_id.id, line.product_qty, _qty, _mtype, context=context)
				_oprod.record_stock_mrp_new(cr, uid, line.id, line.product_id.id, _qty_lm, curr_produced, _mtype, context=context)
				
				#_oprod.record_stok_move(cr, uid, _objp.origin, product_id, _objp.product_uom.id, 'produced', data.product_qty, _objp.x_order_length, context=context)
				ctx = context.copy()
				ctx.update({'x_order_length': line.x_order_length})
				production_mode = 'consume_produce'
				wiz=False
				#_logger.error("action_create_mov_mov_ctxctxctx["+str(ctx)+"]")
				#raise osv.except_osv(_('Error'), _('TESTET'))
				#production.action_produce(cr, uid, line.id, data.product_qty, production_mode, wiz, context=ctx)
				production.action_produce(cr, uid, line.id, _qty_lm, production_mode, wiz, context=ctx)
				_mov_obj = self.pool.get('stock.move')
				_mids = _mov_obj.search(cr, uid, [('production_id', '=', line.product_id.id)], context=context)
				#for _mov in _mov_obj.browse(cr, uid, _mids, context=context):
				#	_logger.error("action_create_mov_mov_mo["+str(_mov)+"]")
				if _mids:	
					_mov_obj.write(cr, uid, _mids, {'x_order_length': line.x_order_length}, context=context)
				
				#---------------------------------------------------------------------
				if line.state!="done" and qty==line.x_order_qty:
					#Note -->> mark as done....
					production.action_production_end(cr, uid, [line.id], context=context)
				#---------------------------------------------------------------------
				
				
				#regardless the state ...call the update dcs on background	
				#---------------------------------------------------------------------
				url=self.pool.get('dincelaccount.config.settings').get_dcs_api_url(cr, uid, ids, "mrpdone", data.x_sale_order_id.id, context=context)	
				
				if url:#rows and len(rows) > 0:
					#url= str(rows[0]) + "?act=mrpdone&id="+str(data.x_sale_order_id.id)
					#url="http://deverp.dincel.com.au/dcsapi/index.php??act=mrpdone&id="+str(ids[0])
					#-------------------------------------------------------------------------------------------
					vals22={
						"url":url,
						"name":data.x_sale_order_id.name,
						"ref_id":data.x_sale_order_id.id,
						"action":"mrpdone",
						"state":"pending",
					}
					self.pool.get('dincelbase.scheduletask').create(cr, uid, vals22, context=context)
					#-------------------------------------------------------------------------------------------
					f 		 = urllib2.urlopen(url)
					response = f.read()
					str1	 = simplejson.loads(response)
					#@_logger.error("updatelink_order_dcs.updatelink_order_dcs["+str(str1)+"]["+str(response)+"]")
					item 	 = str1['item']
					status1	 = str(item['post_status'])
					dcs_refcode	= str(item['dcs_refcode'])
					if status1 != "success":
						#_logger.error("updatelink_order_dcs.updatelink_order_dcsordercode["+str(ordercode)+"]")	
						#sql ="UPDATE res_partner SET x_dcs_id='"+dcs_refcode+"' WHERE id='"+str(ids[0])+"'"
						#cr.execute(sql)
						#return True
						#else:
						if item['errormsg']:
							str1=item['errormsg']
						else:
							str1="Error while updating order at DCS."
						_logger.error("error.mrpdone.update_order_dcsordercode["+str(dcs_refcode)+"]["+str(str1)+"]")
			if line.x_sale_order_id: #for updating status...x_prod_status>>>>order_produced_check()
				self.pool.get('sale.order').order_produced_check(cr, uid, ids, line.x_sale_order_id.id, context=context)
				
	def on_change_qty(self, cr, uid, ids, _qty, _lines, context=None):
		_lines = []
		if context and context.get('active_ids'):
			_ids=context.get('active_ids')
			for mo in self.pool.get('mrp.production').browse(cr, uid, _ids, context=context):
				vals = {
					'name':mo.name,
					'qty_order':mo.x_order_qty,
					'mrp_id':mo.id,
					'product_id': mo.product_id.id or False,
					'product_uom':mo.product_uom.id,
					'order_id':mo.x_sale_order_id.id,
					'region_id':mo.x_region_id.id or False,
					'coststate_id':mo.x_coststate_id.id or False,
					'order_length':mo.x_order_length or 0.0,
					'qty_remain':mo.x_remain_qty,
					'qty_ytd_produced':mo.x_produced_qty,
					'project_id':mo.x_sale_order_id.x_project_id.id,
				}
				_lines.append(vals)
				
		return {'value': {'item_lines': _lines}}
		
	def _get_init_qty(self, cr, uid, context=None):
		return 1
	
	_defaults = {
		'date': fields.date.context_today,
		'qty': _get_init_qty,
		}
		 
class dincelmrp_schedule_line_new(osv.osv_memory):
	_name = "dincelmrp.schedule.new.line"
	_columns = {
		'name':fields.char("MO"),
		'schedule_id': fields.many2one('dincelmrp.schedule.new', 'Schedule Reference'),
		'product_id': fields.many2one('product.product', 'Product'),
		'order_length':fields.float("Stock Length",digits_compute= dp.get_precision('Int Number')),	
		'qty_order':fields.float("Qty Ordered",digits_compute= dp.get_precision('Int Number')),	
		'qty_ytd_produced':fields.float("Qty Produced YTD",digits_compute= dp.get_precision('Int Number')),	
		'qty_remain':fields.float("Qty Remain",digits_compute= dp.get_precision('Int Number')),	
		'order_id': fields.many2one('sale.order', 'Order Reference'),
		'mrp_id': fields.many2one('mrp.production', 'MRP'), 
		'product_uom': fields.many2one('product.uom', 'Unit of Measure'),
		'region_id': fields.many2one('dincelaccount.region', 'A/c Region'),
		'coststate_id':fields.many2one("res.country.state","Cost Centre"),
		'full_mo':fields.boolean('All Complete'),
		'mrp_id': fields.many2one('mrp.production', 'Production'),
		'project_id': fields.many2one('res.partner','Project / Site'),		
	}	
	
	
		