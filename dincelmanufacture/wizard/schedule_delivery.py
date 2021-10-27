from openerp.osv import fields, osv
from openerp.tools.translate import _
import datetime
import logging
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
_logger = logging.getLogger(__name__)
class dincelmrp_schedule_delivery(osv.osv_memory):
	_name = "dincelmrp.schedule.delivery"
	#_description = "Sales Make MRP"
	 
		
	_columns = {
		'date': fields.date('Date'),
		'from_order': fields.boolean('From Order?'),
		'qty':fields.float("Qty test"),
		'packs':fields.integer("Packs", size=2),
		'trucks':fields.integer("Trucks", size=2),
		'dockets':fields.integer('Deliveries', size=2),	
		'comments':fields.char("Comments"),
		'pudel': fields.selection([
			('pu', 'PU'),
			('del', 'DEL'),
			], 'PU/DEL'),
		'order_id': fields.many2one('sale.order', 'Sale Order'),
		'partner_id': fields.many2one('res.partner','Client'),
		'project_id': fields.many2one('res.partner','Project / Site'),
		'pending_invoice': fields.boolean('Pending COD Invoice'),
		'stop_supply': fields.boolean('Stop Supply'),
		'stop_supply_over': fields.boolean('Stop Supply Over'),
		'hold_supply': fields.boolean('Hold Supply / Legal'),
		'part': fields.selection([
			('full', 'FULL'),
			('part', 'PART'),
			], 'Part'),
	}
	_defaults = {
		'from_order': False,
	}
	
	def schedule_delivery(self, cr, uid, ids, context=None):
		record = self.browse(cr, uid, ids[0], context=context)
		if record.dockets == False or record.dockets<=0:
			str1="Please enter number of deliveries"
			raise osv.except_osv(_('Error'), _(''+str1))	
			return False
		obj = self.pool.get('dincelwarehouse.sale.order.delivery')
		date_post		= datetime.datetime.today() 
		vals={
				'order_id':record.order_id.id,
				'partner_id':record.order_id.partner_id.id,
				'pudel':record.pudel,
				'comments':record.comments,
				'date_entry': date_post,
				'date_actual':record.date,
				'trucks':record.trucks,
				'packs':record.packs,
				'dockets':record.dockets,
				'scheduled_by':uid,
				'name':record.order_id.origin,
				#'products':'',
			}
		if record.order_id.x_warehouse_id:
			vals["warehouse_id"]=record.order_id.x_warehouse_id.id
		if record.order_id.x_project_id:	
			vals["project_id"]=record.order_id.x_project_id.id
			if record.order_id.x_project_id.state_id:
				vals["state_id"]=record.order_id.x_project_id.state_id.id
			#self.pool.get('sale.order').write(cr, uid, record.order_id.id, {'x_dt_actual': record.date}, context=context)	
		
		_id1 = obj.create(cr, uid, vals, context=context)	
		
			
		try:	
			
			if record.order_id and record.order_id.id:
				self.pool.get("sale.order").set_next_delivery_date(cr, uid, ids, record.order_id.id, _id1, False,context=context)
				#acs=self.pool.get('dincelmrp.accessories') 
				#sql="update dincelmrp_accessories set dt_actual='%s' where order_id='%s'" % (record.date, record.order_id.id)
				#cr.execute(sql)
				#_ids=acs.search(cr, uid, [('order_id','=',str(record.order_id.id))],context)
				#if _ids:
				#	for o in acs.browse(cr, uid, _ids, context=context):
				#		acs.write(cr, uid, o.id, {'dt_actual': record.date}, context=context)	
				#	
		except ValueError:
			#_logger.error("schedule_deliveryschedule_deliveryerrr["+str(ValueError)+"]")	
			pass
			
		return True
				
		 
	def on_change_qty(self, cr, uid, ids,_qty, context=None):
		value={}
		if context and context.get('active_ids'):
			_ids=context.get('active_ids')
			
			partner_id=None
			project_id=None
			order_id=None
			stop_supply=False
			hold_supply=False
			trucks=0
			for record in self.browse(cr, uid, ids):
				if record.from_order == True:
					partner_id	= record.partner_id.id
					project_id	= record.project_id.id
					order_id	= record.order_id.id
					stop_supply = record.partner_id.x_stop_supply
					hold_supply = record.partner_id.x_hold_supply
				else:
					#partner_id = None
					#project_id = None
				
					#for o in self.pool.get('sale.order').browse(cr, uid, _ids, context=context):
					for o in self.pool.get('dincelmrp.production').browse(cr, uid, _ids, context=context):
						#_obj = self.pool.get('dincelmrp.production').browse(cr, uid, ids[0], context=context)
						partner_id	= o.partner_id.id
						project_id	= o.project_id.id
						order_id	=o.order_id.id
						trucks=o.trucks
						stop_supply=o.partner_id.x_stop_supply
						hold_supply=o.partner_id.x_hold_supply
						#_logger.error("on_change_qtyon_change_qty["+str(_ids)+"]")
						#_ids=context.get('active_ids')
						#obj = self.pool.get('sale.order').browse(cr, uid, vals, context=context)
						#_id=None
				context = context.copy()
				context['delivery']="1"
				proceed, o_ids=self.pool.get('sale.order').is_over_limit_ok( cr, uid, ids,order_id , context=context)
				if project_id:
					value={'partner_id':partner_id,
							'project_id':project_id,
							'dockets':trucks,
							'stop_supply':stop_supply,
							'hold_supply':hold_supply,}
					if proceed==0:
						value['stop_supply_over']=True 
					
		return {'value':value}
		
	def _get_init_qty(self, cr, uid, context=None):
		return 1	
	 
	_defaults = {
		'date': fields.date.context_today,
		'qty': _get_init_qty,
		}
	