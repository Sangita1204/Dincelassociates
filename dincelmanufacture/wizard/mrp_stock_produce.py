from openerp.osv import fields, osv
from openerp.tools.translate import _
import logging
_logger = logging.getLogger(__name__)
class dincelmrp_stock_produce(osv.osv_memory):
	_name = "dincelmrp.stock.produce"
	_description = "Produce Stock MRP"
	_columns = {
		'date': fields.datetime('Date'),
		'qty':fields.float("Qty test"),
		'product_id': fields.many2one('product.product', 'Product'),
		'mrp_id': fields.many2one('mrp.production', 'MRP'),
		'produced_other':fields.float("Qty Produced"),
		'remaining_other': fields.float('Remaining Qty'),
		'ordered_qty': fields.integer('Ordered Qty (each)'),
		'produced_qty_ytd': fields.integer('Produced YTD (each)'),
		'produced_qty': fields.integer('Produced (each)'),
		'stock_length': fields.integer('Length (mm)'),
		'qty_lm':fields.float("Qty LM"),
		'is_other':fields.boolean("Is other item?"),
		'routing_id': fields.many2one('mrp.routing','Routing'),		
	}
	
	def button_stock_produce_item(self, cr, uid, ids, context=None):
		if context is None:
			context = {}	
		record = self.browse(cr, uid, ids[0], context=context)
		err_msg="Invalid produced quantity found!!"
		#_complete=False
		if record.produced_other>0:
			if record.produced_other > record.remaining_other:
				raise osv.except_osv(_('Error!'),_(err_msg))
				return False
			#elif record.produced_other == record.remaining_other:	
			#	_complete=True
		production_mode = 'consume_produce'		
		production_id = record.mrp_id.id
		wiz=False
		self.pool.get('mrp.production').action_produce(cr, uid, production_id,record.produced_other, production_mode, wiz, context=context)
		if record.date:
			sql ="UPDATE mrp_production SET "
			#sql +=",x_dt_produced='%s' " % (record.date)
			sql +="date_start='%s' " % (record.date)
			#if _complete==True:
			#sql +=",x_dt_produced='%s' " % (record.date)
			sql +=",date_finished='%s' " % (record.date)
			sql += " WHERE id ='%s'" % (record.mrp_id.id)
			cr.execute(sql)
			prod = self.pool.get('mrp.production').browse(cr, uid, production_id, context=context)
			for move in prod.move_created_ids2:
				#to fix backdate production issue....for stockvalution report...
				#only downside is having partial production...it will always takes the last date saved....
				#cauese move_created_ids2 includes all partial till date...
				sql="update stock_move set date='%s' where id='%s'" % (record.date, move.id)
				cr.execute(sql)
				for quant in move.quant_ids:#for ERP and report compatibility
					sql="update stock_quant set in_date='%s'  where id='%s'" % (record.date, quant.id)
					cr.execute(sql)
			for move in prod.move_lines2:
				sql="update stock_move set date='%s' where id='%s'" % (record.date, move.id)
				cr.execute(sql)
				for quant in move.quant_ids:#for ERP and report compatibility
					sql="update stock_quant set in_date='%s'  where id='%s'" % (record.date, quant.id)
					cr.execute(sql)
		return True 
		
	def button_stock_produce_dcs(self, cr, uid, ids, context=None):
		if context is None:
			context = {}	 
		production=self.pool.get('mrp.production')
		_mov_obj = self.pool.get('stock.move')
		_objstock = self.pool.get('stock.picking')
		record = self.browse(cr, uid, ids[0], context=context)
		err_msg="Invalid produced quantity found!!"
		if record.produced_qty>0:
			if record.produced_qty > (record.ordered_qty-record.produced_qty_ytd):
				
				raise osv.except_osv(_('Error!'),_(err_msg))
				return False
				
			if record.product_id.x_prod_type and record.product_id.x_prod_type=="acs":
				qty_produced=record.produced_qty
			else:	
				qty_produced=record.produced_qty*0.001*record.stock_length 
			
			#-------------------------------------------------------------------------------------------------------------

			_ptype	=self.pool.get('stock.picking.type')
			
			_idpick	=_objstock.search(cr, uid, [('origin', '=', str(record.mrp_id.name))], limit=1) 	
			if _idpick:
				pckid=_idpick[0]
			else:
				_idtype	=_ptype.search(cr, uid, [('code', '=', 'internal')], limit=1) 	
				#if _ids:
				#	_ptype 	= _ptype.browse(cr, uid, _ids[0], context=context)
				vals={
					'origin': str(record.mrp_id.name),
					#'partner_id': _obj2sale.partner_id.id,
					#'company_id': _obj2sale.company_id.id,
					'name':record.mrp_id.name,
					'state':'done',
					'move_type':'direct',
					}
				if _idtype:
					vals['picking_type_id']=_idtype[0]
				
				#_logger.error("picking_type_idpicking_type_i_objstock["+str(vals)+"]")		
				pckid = _objstock.create(cr,uid,vals,context)	
			production_id = record.mrp_id.id
			finished=False
			sql ="UPDATE mrp_production SET x_produced_qty=x_produced_qty+%s " % (record.produced_qty)
			if record.date:
				sql +=",x_dt_produced='%s' " % (record.date)
			if record.routing_id:
				sql +=",routing_id='%s' " % (record.routing_id.id)	
			if record.produced_qty == (record.ordered_qty-record.produced_qty_ytd):
				sql +=",date_finished='%s' " % (record.date)
				finished=True
			sql += " WHERE id ='%s'" % (production_id)
			cr.execute(sql)
			#_logger.error("picking_type_idpicking_sqlsqlsql["+str(sql)+"]")	
			#------------------------------------------------------------------------------------------------------------- 	
			#stock journal and line items...	
			_jid = self.pool.get('dincelstock.journal').product_produced_confirm(cr, uid, production_id,record.date, context)
			_id2= self._create_stock_journal_produced(cr, uid, record.mrp_id, _jid, record, context)
			#-------------------------------------------------------------------------------------------------------------
			#-------------------------------------------------------------------------------------------------------------	
			ctx = context.copy()
			ctx.update({'x_order_length': record.stock_length})
			production_mode = 'consume_produce'
			wiz=False
			
			
					
			#production.action_produce(cr, uid, line.id, data.product_qty, production_mode, wiz, context=ctx)
			production.action_produce(cr, uid, record.mrp_id.id, qty_produced, production_mode, wiz, context=ctx)
			 
			_mids = _mov_obj.search(cr, uid, [('production_id', '=', production_id)], context=context)
			#for _mov in _mov_obj.browse(cr, uid, _mids, context=context):
			#	_logger.error("action_create_mov_mov_mo["+str(_mov)+"]")
			if _mids:	#all stock moves (stock.move)
				_mov_obj.write(cr, uid, _mids, {'x_order_length': record.stock_length,'date':record.date}, context=context)
			prod = self.pool.get('mrp.production').browse(cr, uid, production_id, context=context)	
			for move in prod.move_created_ids2:
				#to fix backdate production issue....for stockvalution report...
				#only downside is having partial production...it will always takes the last date saved....
				#cauese move_created_ids2 includes all partial till date...
				sql="update stock_move set date='%s' where id='%s'" % (record.date, move.id)
				cr.execute(sql)
				for quant in move.quant_ids:
					sql="update stock_quant set in_date='%s'  where id='%s'" % (record.date, quant.id)
					cr.execute(sql)
			for move in prod.move_lines2:
				sql="update stock_move set date='%s' where id='%s'" % (record.date, move.id)
				cr.execute(sql)
				for quant in move.quant_ids:
					sql="update stock_quant set in_date='%s'  where id='%s'" % (record.date, quant.id)
					cr.execute(sql)
			#---------------------------------------------------------------------
			if finished==True:#if record.produced_qty == (record.ordered_qty-record.produced_qty_ytd):
				#Note -->> mark as done....
				production.action_production_end(cr, uid, [record.mrp_id.id], context=context)
				#cause above function updates the date to current datetime,,,need to overwrite the date
				sql="UPDATE mrp_production SET "
				sql +=" date_finished='%s' " % (record.date)
				sql +=" WHERE id ='%s'" % (record.mrp_id.id)
				cr.execute(sql)
				
				
			#---------------------------------------------------------------------
				
		else:		
			raise osv.except_osv(_('Error!'),_(err_msg))
			return False
		return True
		
	def _create_stock_journal_produced(self, cr, uid, mrp, _jid, _line, context=None):
		_qty		=int(_line.produced_qty)
		if abs(_qty)>0:
			_length		=int(_line.stock_length)
			_obj = self.pool.get('dincelstock.journal').browse(cr, uid, _jid, context=context)
			_dtau		= self.pool.get('dincelstock.transfer').get_au_datetime(cr, uid, _obj.date)
			
			_objline = self.pool.get('dincelstock.journal.line')
			vals={'journal_id':_jid,
					'product_id':_line.product_id.id,
					'date':_dtau,#_obj.date,#mrp.date_planned,
					'date_gmt':_obj.date,
					'period_id':_obj.period_id.id,
					'prod_length':_length,
					'location_id':mrp.location_dest_id.id,
					'name':_('MRP:') + (mrp.name or ''),
					'reference':_('MRP:') + (mrp.name or ''),
					}
			if _line.product_id.x_prod_type=="acs":
				vals['is_acs'] 	= True	
			else:
				vals['is_acs'] 	= False
			vals['qty_in'] 	= _qty	
			vals['qty_out'] = 0
			#_logger.error("order_delivery_confirmorder_delivery_confirm[%s][%s][%s]" % (_jid,vals,_qty ))		
			return _objline.create(cr, uid, vals, context=context)
			
	def on_change_qty(self, cr, uid, ids, _qty, mrp_id, context=None):
		result={}
		#if context and context.get('active_ids'):
		#	#_ids=context.get('active_ids')
		#	for mo in self.pool.get('mrp.production').browse(cr, uid, [mrp_id], context=context):
		#	
		#		result={'product_id':mo.product_id.id, 'mrp_id': mrp_id,'stock_length':mo.x_order_length}
		#
		if context is None:
			context = {}
		prod = self.pool.get('mrp.production').browse(cr, uid, mrp_id, context=context)
		done = 0.0
		for move in prod.move_created_ids2:
			if move.product_id == prod.product_id:
				if not move.scrapped:
					done += move.product_uom_qty # As uom of produced products and production order should correspond
		_remain=prod.product_qty - done		
		result={'product_id':prod.product_id.id, 'mrp_id': mrp_id,'stock_length':prod.x_order_length,'remaining_other':_remain,'produced_other':_remain}
		#_logger.error("order_delivery_confirmorder_resultresult[%s] " % (result ))		
		return {'value':result}
		
	def _get_init_qty(self, cr, uid, context=None):
		return 1
	
	_defaults = {
		'date': fields.date.context_today,
		'qty': _get_init_qty,
		'is_other': False,
		}
		 