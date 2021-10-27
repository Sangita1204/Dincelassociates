from openerp.osv import osv, fields
from datetime import date
#from openerp.addons.base_status.base_state import base_state
import time 
import datetime
import logging
from openerp.tools.translate import _
from openerp import models, fields, api
from time import gmtime, strftime
_logger = logging.getLogger(__name__)

class dincelstock_base(models.TransientModel):#osv.Model):
	_inherit = "stock.transfer_details"
	#x_date_receipt = fields.date('Date')
	date_receipt = fields.Date('Date')
	#_columns = {
	#	'x_date_receipt':fields.date("Receipt Date"),		#'x_date_receipt':fields.date("Date"),
	#}
	
	@api.one
	def do_detailed_transfer_dcs(self):	
		#if context is None:
		#	context = {}
		#for lstits in [self.item_ids, self.packop_ids]:
		#	for prod in lstits:
		#		product_id	= prod.product_id.id
		#		product_qty	= prod.quantity
		#		product_len	= prod.product_id.x_stock_length
		#		self.pool.get('dincelproduct.inventory').qty_increment(self._cr, self._uid, product_id, product_len, product_qty)	
		#dt_day=datetime.datetime.today()
		#self.env['stock.pack.operation'].create(pack_datas)
		#for record in self.browse():	#record = self.browse(cr, uid, ids[0], context=context)
		dt_day=self.date_receipt
			
			
		processed_ids = []
		# Create new and update existing pack operations
		for lstits in [self.item_ids, self.packop_ids]:
			for prod in lstits:
				pack_datas = {
					'product_id': prod.product_id.id,
					'product_uom_id': prod.product_uom_id.id,
					'product_qty': prod.quantity,
					'package_id': prod.package_id.id,
					'lot_id': prod.lot_id.id,
					'location_id': prod.sourceloc_id.id,
					'location_dest_id': prod.destinationloc_id.id,
					'result_package_id': prod.result_package_id.id,
					'date': dt_day,#prod.date if prod.date else datetime.now(),
					'owner_id': prod.owner_id.id,
				}
				if prod.packop_id:
					prod.packop_id.write(pack_datas)
					processed_ids.append(prod.packop_id.id)
				else:
					pack_datas['picking_id'] = self.picking_id.id
					packop_id = self.env['stock.pack.operation'].create(pack_datas)
					processed_ids.append(packop_id.id)
				#------------------------------------------------------------------
				product_id	= prod.product_id.id
				product_qty	= prod.quantity
				product_len	= prod.product_id.x_stock_length
				self.pool.get('dincelproduct.inventory').qty_increment(self._cr, self._uid, product_id, product_len, product_qty)
				#------------------------------------------------------------------				
		# Delete the others
		packops = self.env['stock.pack.operation'].search(['&', ('picking_id', '=', self.picking_id.id), '!', ('id', 'in', processed_ids)])
		for packop in packops:
			packop.unlink()

		# Execute the transfer of the picking
		self.picking_id.do_transfer()
		#x_act_state#reseting ,x_act_state='none'  for eg reverse stock
		sql="update stock_picking set date_done='%s',date='%s' ,min_date='%s',x_act_state='none'  where id='%s'" % (dt_day,dt_day,dt_day, self.picking_id.id)
		self.env.cr.execute(sql)
		
		for move in self.picking_id.move_lines:
			sql="update stock_move set date='%s',date_expected='%s'  where id='%s'" % (dt_day, dt_day, move.id)
			self.env.cr.execute(sql)
			for quant in move.quant_ids:
				sql="update stock_quant set in_date='%s'  where id='%s'" % (dt_day, quant.id)
				self.env.cr.execute(sql)
				#_logger.error("quant_linesquant_lines.sqlsql["+str(sql)+"]")
		return True		
		#return self.do_detailed_transfer()
		#return self.pool['report'].get_action(cr, uid, [], 'dincelstock.report_docket_report', data=datas, context=context)			
	
	