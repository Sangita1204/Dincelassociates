import time
from openerp import tools
from openerp.osv import fields, osv
from openerp.tools.translate import _
import logging
_logger = logging.getLogger(__name__)

class dincelstock_ibt_batch(osv.osv_memory):
	_name = "dincelstock.ibt.batch"
	_columns = {
		'date': fields.datetime('Date Pickup', required=True),
		'note': fields.char('Note'),
		'source_location_id': fields.many2one('stock.location', 'Source Location'),
		'destination_location_id': fields.many2one('stock.location', 'Destination Location'),
		'source_warehouse_id': fields.many2one('stock.warehouse','Source Warehouse'),	
		'destination_warehouse_id': fields.many2one('stock.warehouse','Destination Warehouse'),	
		'partner_id': fields.many2one('res.partner','Delivery To'),	
		'contact_id': fields.many2one('res.partner','Contact'),	
		'item_line': fields.one2many('dincelstock.ibt.batch.line', 'batch_id', 'IBT Items'),
		'qty':fields.float("Qty test"),
	}	
	
	def _get_init_qty(self, cr, uid, context=None):
		return 1
	_defaults = {
		'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
		'subtype': 'order',
		'qty': _get_init_qty,
		}
		
	def on_change_qty(self, cr, uid, ids,qty, context=None):
		result={}
		_items=[]
		vals={}
		 
		if context and context.get('active_ids'):
			_ids=context.get('active_ids')
			value={}
			for o in self.pool.get('dincelstock.transfer').browse(cr, uid, _ids, context=context):
				if not o.manifest_id:
					#only if no previous manifest created...
					vals={'ibt_id':o.id,
						  'partner_id':o.partner_id.id,
						  'project_id':o.project_id.id,
						  'type':o.type,
						  'state':o.state,
						  'date':o.date,
						  'name':o.name,
						  }
					if o.source_location_id:
						vals['source_location_id']=o.source_location_id.id
					if o.destination_location_id:
						vals['destination_location_id']=o.destination_location_id.id
					_items.append(vals)
			result['item_line']=_items
			 
		return {'value':result}	
		
	def create_manifest(self, cr, uid, ids, context=None):	
		if context is None:
			context = {}	
		record = self.browse(cr, uid, ids[0], context=context)
		if len(record.item_line) > 0:
			_name=self.pool.get('ir.sequence').get(cr, uid, 'ibt.manifest')
			'''vals={'partner_id':record.partner_id.id,
				  'destination_warehouse_id':record.destination_warehouse_id.id,
				  'source_location_id':record.source_location_id.id,
				  'destination_location_id':record.destination_location_id.id,
				  'source_warehouse_id':record.source_warehouse_id.id,
				  'name':_name,
				  'date':record.date,
				  'note':record.note,
				  }'''
			vals={'partner_id':record.partner_id.id,
				  'name':_name,
				  'date':record.date,
				  'note':record.note,
				  }	  
			if record.contact_id:
				vals['contact_id']=record.contact_id.id 
				
			#@_logger.error("ex.error.mrpdone.mrpschedulemrpschedule["+str(vals)+"]["+str(_name)+"]")	  
			manifest_id=self.pool.get('dincelstock.ibt.manifest').create(cr, uid, vals, context=context)
			
			if manifest_id:			
				for line in record.item_line:
					 sql="update dincelstock_transfer set manifest_id='%s' where id='%s'" % (manifest_id, str(line.ibt_id.id))
					 cr.execute(sql)

			#view_id = self.pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'dincelaccount.invoice.form')], limit=1) 	
					
			value = {
				'domain': str([('id', 'in', manifest_id)]),
				'view_type': 'form',
				'view_mode': 'form',
				'res_model': 'dincelstock.ibt.manifest',
				#'view_id': view_id,
				'type': 'ir.actions.act_window',
				'name' : _('IBT Manifest'),
				'res_id': manifest_id
			}
			return value			 
		return True		
		
	def onchange_warehouse_frm(self, cr, uid, ids, warehouse_frm, context=None):
		if context is None:
			context = {}
		if warehouse_frm:
			domain1={}
			_obj = self.pool.get('stock.warehouse').browse(cr, uid, warehouse_frm, context=context)
			if _obj.lot_stock_id:
				_ids=self.pool.get('stock.location').search(cr, uid, [('x_ibt','=',True),('x_warehouse_id','=',_obj.id)],context=context)
				if _ids:
					domain1={'source_location_id':[('id','in', (_ids))]}
				return {'value': {'source_location_id':_obj.lot_stock_id.id} , 'domain':domain1 }
		return True 
		
	def onchange_warehouse_to(self, cr, uid, ids, warehouse_to, context=None):
		if context is None:
			context = {}
		if warehouse_to:
			domain1={}
			_obj = self.pool.get('stock.warehouse').browse(cr, uid, warehouse_to, context=context)
			if _obj.lot_stock_id:
				_ids=self.pool.get('stock.location').search(cr, uid, [('x_ibt','=',True),('x_warehouse_id','=',_obj.id)],context=context)
				if _ids:
					domain1={'destination_location_id':[('id','in', (_ids))]}
				return {'value': {'destination_location_id':_obj.lot_stock_id.id}, 'domain':domain1  }
		return True 
		
class dincelstock_ibt_batch_line(osv.osv_memory):
	_name="dincelstock.ibt.batch.line"
	_columns = {
		'batch_id': fields.many2one('dincelstock.ibt.batch', 'IBT Batch'),
		'sequence': fields.integer('Sequence'),
		'name': fields.char('IBT'),
		'date': fields.datetime('Date'),
		'type': fields.char('Type'),
		'state': fields.char('State'),
		'partner_id':fields.many2one('res.partner', 'Partner'),
		'project_id':fields.many2one('res.partner', 'Project'),
		'ibt_id':fields.many2one('dincelstock.transfer','Payment'),
		'reference':fields.char('Reference'),
		'source_location_id': fields.many2one('stock.location', 'Source Location'),
		'destination_location_id': fields.many2one('stock.location', 'Destination Location'),
	}	
		 