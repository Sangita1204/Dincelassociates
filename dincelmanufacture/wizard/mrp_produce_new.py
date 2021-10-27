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

class dincelmrp_produce_new(osv.osv_memory):
	_name = "dincelmrp.produce.new"
	_description = "Produce MRP"
	_columns = {
		'date': fields.date('Date'),
		'item_lines':fields.one2many('dincelmrp.produce.new.line', 'produce_id', 'MRP Lines'),
		'qty':fields.float("Qty test"),
		'is_full':fields.boolean("Is Full"),
		'routing_id': fields.many2one('mrp.routing','Routing'),		
		'dt_start':fields.datetime('Start'),
		'dt_stop':fields.datetime('End'),
	}
	
	def save_production(self, cr, uid, ids, context=None):	
		if context is None:
			context = {}
		order_ids=[]	
		record = self.browse(cr, uid, ids[0], context=context)
		if record.item_lines:
			#_obj_mrp	= self.pool.get('mrp.production')
			#_oprod 		= self.pool.get('dincelproduct.product')
			for line in record.item_lines:
				if line.mrp_id:
					_qty = line.qty_curr_produce
					if _qty and _qty > 0:
						
						dt_end = self._mrp_produced(cr, uid, ids, line.mrp_id.id, _qty, record.dt_start, record.dt_stop, line.routing_id, context)
						#_logger.error("save_productionsave_productionsave_production_objstock["+str(dt_end)+"]["+str(record.dt_start)+"]["+str(record.dt_stop)+"]")	
						#if record.dt_stop:
						#	dt_end=record.dt_stop
						#--------------------stock control--------------
						_jid = self.pool.get('dincelstock.journal').product_produced_confirm(cr, uid, line.mrp_id.id, dt_end, context)
						_id2 = self._create_stock_journal_mrp_produced(cr, uid, line.mrp_id, _jid, line,dt_end, context)
						if not line.order_id.id in order_ids:
							order_ids.append(line.order_id.id)
		for _id in order_ids:
			self.update_production_schedule(cr ,uid, ids,_id, context=context)
		return True
	
	def update_production_schedule(self, cr ,uid, ids,_orderid, context=None):
		sql="select * from dincelmrp_schedule where order_id='%s'" % (_orderid)
		cr.execute(sql)
		rows 	= cr.dictfetchall()
		for row in rows:
			id_id = row['id']
			production_id=row['production_id']
			#schedule_start=row['schedule_start']
			#planned=row['planned']
			product=row['product']
			if production_id:
				tot_order=0
				tot_produced=0
				lm_done=0.0
				sql="""select m.x_order_qty,m.x_produced_qty,m.id,m.name,m.x_order_length 
						from mrp_production m,product_product p, product_template t 
						where
						m.product_id = p.id and t.id=p.product_tmpl_id 
						and t.x_dcs_group='P%s' and m.x_production_id='%s'""" % (product, production_id)
				cr.execute(sql)
				rows1 	= cr.dictfetchall()
				for row1 in rows1:
					_order		=int(row1['x_order_qty'])
					_produced	=int(row1['x_produced_qty'])
					_len		=int(row1['x_order_length'])
					_lm			=_produced * _len
					_lm			=float(_len)*0.001*_produced
					lm_done +=_lm
					tot_order +=_order
					tot_produced +=_produced
					
				if tot_order <=	tot_produced:
					sql="update dincelmrp_schedule set len_complete=len_order,state='done' where id='%s'" % (id_id)
					cr.execute(sql)
					#count1+=1
				else:
					#other+=1
					if tot_produced > 0:
						sql="update dincelmrp_schedule set state='part',len_complete='%s'  where id='%s'" % (lm_done,id_id)
						cr.execute(sql)
						
						
	def _mrp_produced(self, cr, uid, ids, _id, _qty, _dtStart, _dtEnd, _routeid, context=None):
		production=self.pool.get('mrp.production')
		line	=production.browse(cr, uid, _id, context)
		actmove 	= self.pool.get('dincelaccount.journal.dcs')
		_oprod 		= self.pool.get('dincelproduct.product')
		
		est_mms = line.x_est_minute 
		if _dtStart:
			_start=_dtStart
		else:
			if line.date_start:
				_start=line.date_start
			else:
				_start=line.date_planned
		if _dtEnd:
			dt_end  =  _dtEnd
		else:
			dt_end  =  parser.parse(_start) +  datetime.timedelta(minutes = est_mms)
			
		if line.state == "draft": #Note--> for the first time...
			qty		= 0
			
			production.action_confirm(cr, uid, [line.id], context=context)		
			# / 60
			# timedelta(hours=est_hrs)#time.strftime('%Y-%m-%d %H:%M:%S')
			sql = "UPDATE mrp_production SET x_start_mo='True',date_start='%s',state='in_production',x_curr_produced_qty=0,x_produced_qty='%s' " % (str(_start),str(qty))
			if dt_end:
				sql +=",date_finished='%s',x_dt_produced='%s'  " % (dt_end,dt_end) #this date is required from inventory journal....****(must)
			sql +=" WHERE id='%s'  " % (str(line.id))	
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
				data 	= production.browse(cr, uid, line.id, context=context)
				
				#-------------------------------------------------
				#actmove.mo_produced_qty_journal_dcs(cr, uid, ids, line.id, line.product_qty, context=context) 	
				#Journal entry ----------------------	
				if line.product_id.x_prod_type  and line.product_id.x_prod_type =="acs":
					_qty_lm=curr_produced
				else:
					_qty_lm= curr_produced*0.001*line.x_order_length
				
				actmove.mo_produced_qty_journal_dcs(cr, uid, ids, line.id, _qty_lm, context=context) 	
				#Journal entry ----------------------		
				#_logger.error("error.mrpdone.update_order_dcsordercodevvvv_qty_lm"+str(_qty_lm)+"]["+str(curr_produced)+"]["+str(_qty)+"]")
							
				if line.x_sale_order_id:
					_mtype="mo-sales"
				else:
					_mtype="mo-stock" #>>for stock only no sales assigned....
					self.pool.get('dincelproduct.inventory').qty_increment(cr, uid, line.product_id.id, line.x_order_length, curr_produced, context = context)
					
				
				_oprod.record_stock_mrp_new(cr, uid, line.id, line.product_id.id, _qty_lm, curr_produced, _mtype, context=context)

				ctx = context.copy()
				ctx.update({'x_order_length': line.x_order_length})
				production_mode = 'consume_produce'
				wiz=False
				production.action_produce(cr, uid, line.id, _qty_lm, production_mode, wiz, context=ctx)
				
				sql="update stock_move set x_order_length='%s' where production_id='%s'" % (int(line.x_order_length), line.id)
				cr.execute(sql)
				
				#---------------------------------------------------------------------
				if line.state!="done" and qty==line.x_order_qty:
					#Note -->> mark as done....
					production.action_production_end(cr, uid, [line.id], context=context)
				#---------------------------------------------------------------------
				#cause by some resons action_production_end is putting date as today's date instead of correct date dt_end....
				sql ="UPDATE mrp_production SET"
				if line.state!="draft":
					sql +=" x_produced_qty=%s " % (str(qty))
				else:	#cause in first time above the producted qty is not set or set as zero
					if _dtStart:
						_start=_dtStart
					else:
						_start=time.strftime('%Y-%m-%d %H:%M:%S')
					sql +=" date_start='%s',x_produced_qty='%s'  " % (str(_start),str(qty))
				#if _dtEnd:
				#	sql +=",date_finished='%s' " % (_dtEnd)
				if dt_end:
					sql +=",date_finished='%s',x_dt_produced='%s'  " % (dt_end,dt_end)	
				if _routeid:
					sql +=",routing_id='%s' " % (_routeid.id)
						
				sql += " WHERE id='%s' "  % (str(line.id))
				cr.execute(sql)
				
				
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
			if _dtEnd:
				for move in line.move_created_ids2:
					#to fix backdate production issue....for stockvalution report...
					#only downside is having partial production...it will always takes the last date saved....
					#cauese move_created_ids2 includes all partial till date...
					sql="update stock_move set date='%s' where id='%s'" % (_dtEnd, move.id)
					cr.execute(sql)
					for quant in move.quant_ids:
						sql="update stock_quant set in_date='%s'  where id='%s'" % (_dtEnd, quant.id)
						cr.execute(sql)
				for move in line.move_lines2:
					sql="update stock_move set date='%s' where id='%s'" % (_dtEnd, move.id)
					cr.execute(sql)
					for quant in move.quant_ids:
						sql="update stock_quant set in_date='%s'  where id='%s'" % (_dtEnd, quant.id)
						cr.execute(sql)
			if line.x_sale_order_id: #for updating status...x_prod_status>>>>order_produced_check()
				self.pool.get('sale.order').order_produced_check(cr, uid, ids, line.x_sale_order_id.id, context=context)
		return dt_end
		
	def _create_stock_journal_mrp_produced(self, cr, uid, mrp, _jid, _line, dt, context=None):
		_qty		=int(_line.qty_curr_produce)
		if abs(_qty)>0:
			_length		=int(_line.order_length)
			_dtau		= self.pool.get('dincelstock.transfer').get_au_datetime(cr, uid, dt)
			_obj = self.pool.get('dincelstock.journal').browse(cr, uid, _jid, context=context)
			_objline = self.pool.get('dincelstock.journal.line')
			vals={'journal_id':_jid,
					'product_id':_line.product_id.id,
					'date':_dtau,#mrp.x_dt_produced, #mrp.date_finished
					'date_gmt':dt,#mrp.x_dt_produced,
					'period_id':_obj.period_id.id,
					'prod_length':_length,
					'location_id':mrp.location_dest_id.id,
					'reference':_('MRP:') + (mrp.name or ''),
					'name':_('MRP:') + (mrp.name or ''),
					}
			if _line.product_id.x_prod_type=="acs":
				vals['is_acs'] 	= True	
			else:
				vals['is_acs'] 	= False
			if mrp.x_sale_order_id:	
				vals['order_id'] 	= mrp.x_sale_order_id.id
				
			vals['qty_in'] 	= _qty	
			vals['qty_out'] = 0
			#_logger.error("order_delivery_confirmorder_delivery_confirm[%s][%s][%s]" % (_jid,vals,_qty ))		
			return _objline.create(cr, uid, vals, context=context)
			
	def on_change_is_full(self, cr, uid, ids, _isfull, _lines, context=None):
		#_lines_new = []
		context = context or {}
		
		#amt = 0.0
		#amt_fee = 0.0 
		
		if _lines:
			
			line_ids = self.resolve_2many_commands(cr, uid, 'item_lines', _lines, ['qty_curr_produce','qty_remain'], context)
			#_logger.error("error.mrpdone.update_order_dcsordercodevvvv"+str(_lines)+"]["+str(line_ids)+"]")
			for line in line_ids:
				if line:
					
					if _isfull:
						line['qty_curr_produce']= line['qty_remain']
					else:
						line['qty_curr_produce']= 0
					#_logger.error("updatelink_order_dcs.onchange_pay_lineslinelineleine2222["+str(line['qty_curr_produce'])+"]["+str(_isfull)+"]")		
			return {'value': {'item_lines': line_ids}}
		#return {'value': {'amount': amt,'amount_total': (amt+amt_fee),'amount_fee':amt_fee}}
					
		#_logger.error("error.mrpdone.update_order_dcsordercode555["+str(_lines)+"]["+str(_isfull)+"]")
		#for line in _lines:
		#	_logger.error("error.mrpdone.update_order_dcsordercode11111["+str(line)+"]["+str(_isfull)+"]")
		#	if line:
		#	
		#	#if line.mrp_id:
		#		#	_qty=line.qty_curr_produce
		#		if _isfull:
		#			line.qty_curr_produce=line.qty_remain
		#	#if _isfull:
		#	#	line['qty_curr_produce']=line['qty_remain']
		#	#else:
		#	#	line['qty_curr_produce']=0
		#	_lines_new.append(line)	
		#return {'value': {'item_lines': _lines_new}}
		
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
					'qty_curr_produce':0.0,
				}
				_lines.append(vals)
				
		return {'value': {'item_lines': _lines}}
	def on_change_routing(self, cr, uid, ids, _lineid, _lines, context=None):
		if _lineid:
			items=[]
			for line in _lines:
				# create    (0, 0,  { fields })
				# update    (1, ID, { fields })
				if line[0] in [0, 1]:
					line[2]['routing_id'] = _lineid
					items.append(line)
				# link      (4, ID)
				# link all  (6, 0, IDS)
				elif line[0] in [4, 6]:
					line_ids = line[0] == 4 and [line[1]] or line[2]
					for line_id in line_ids:
						items.append([1, line_id, {'routing_id': _lineid}])
				else:
					items.append(line)
			return {'value': {'item_lines': items}}
		
		
	def _get_init_qty(self, cr, uid, context=None):
		return 1
	
	_defaults = {
		'date': fields.date.context_today,
		'qty': _get_init_qty,
		}
		 
class dincelmrp_produce_line_new(osv.osv_memory):
	_name = "dincelmrp.produce.new.line"
	_columns = {
		'name':fields.char("MO"),
		'produce_id': fields.many2one('dincelmrp.produce.new', 'Produce Reference'),
		'product_id': fields.many2one('product.product', 'Product'),
		'order_length':fields.float("Stock Length",digits_compute= dp.get_precision('Int Number')),	
		'qty_order':fields.float("Qty Ordered",digits_compute= dp.get_precision('Int Number')),	
		'qty_ytd_produced':fields.float("Qty Produced YTD",digits_compute= dp.get_precision('Int Number')),	
		'qty_curr_produce':fields.float("Qty Produce",digits_compute= dp.get_precision('Int Number')),	
		'qty_remain':fields.float("Qty Remain",digits_compute= dp.get_precision('Int Number')),	
		'order_id': fields.many2one('sale.order', 'Order Reference'),
		'mrp_id': fields.many2one('mrp.production', 'MRP'), 
		'product_uom': fields.many2one('product.uom', 'Unit of Measure'),
		'region_id': fields.many2one('dincelaccount.region', 'A/c Region'),
		'coststate_id':fields.many2one("res.country.state","Cost Centre"),
		'full_mo':fields.boolean('All Complete'),
		'mrp_id': fields.many2one('mrp.production', 'Production'),
		'project_id': fields.many2one('res.partner','Project / Site'),		
		'routing_id': fields.many2one('mrp.routing','Routing'),		
		'dt_start':fields.datetime('Start'),
		'dt_stop':fields.datetime('End'),
	}	
	
	
		