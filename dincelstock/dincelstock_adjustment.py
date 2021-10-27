from openerp.osv import osv, fields
from datetime import date
#from openerp.addons.base_status.base_state import base_state
from openerp.tools.misc import find_in_path
import time 
import datetime
import logging
from openerp.tools.translate import _
import urllib2
import simplejson
import base64
import subprocess
from subprocess import Popen, PIPE, STDOUT
from time import gmtime, strftime
import openerp.addons.decimal_precision as dp
_logger = logging.getLogger(__name__)

class dincelstock_inventory(osv.Model):
	_inherit="stock.inventory"
	#_inherit = ['mail.thread']
	_order = "x_date desc, id desc"
	INVENTORY_STATE_SELECTION = [
		('draft', 'Draft'),
		('cancel', 'Cancelled'),
		('confirm', 'In Progress'),
		('done', 'Validated'),
	]
	_columns = {
		'x_date': fields.datetime('Date'),
		'state': fields.selection(INVENTORY_STATE_SELECTION, 'Status', readonly=True, select=True, copy=False, track_visibility='onchange'),
	}
	_defaults = {
		'x_date': fields.datetime.now,
	}
	def write(self, cr, uid, ids, vals, context=None):
		
		res = super(dincelstock_inventory, self).write(cr, uid, ids, vals, context=context)
		for record in self.browse(cr, uid, ids):
			if record.x_date:
				sql="update stock_inventory set date='%s' where id='%s'" % (record.x_date, record.id)
				cr.execute(sql)
			for line in record.line_ids:
				_qtyreal=line.product_qty
				_qtytheo=line.theoretical_qty
				_qtyvar=_qtyreal-_qtytheo
				_cost=line.product_id.standard_price
				sql="update stock_inventory_line set x_qty_adjust='%s',x_unit_cost='%s' where id='%s' " % (_qtyvar, _cost, line.id)
				cr.execute(sql)
				#_logger.error("update.dincelstock_inventorydincelstock_inventory["+str(sql)+"]")	
		return res
		
	def action_done_dcs(self, cr, uid, ids, context=None):
		""" Finish the inventory
		@return: True
		"""
		#f#or inv in self.browse(cr, uid, ids, context=context):
		#	for inventory_line in inv.line_ids:
		#		if inventory_line.product_qty < 0 and inventory_line.product_qty != inventory_line.theoretical_qty:
		#			raise osv.except_osv(_('Warning'), _('You cannot set a negative product quantity in an inventory line:\n\t%s - qty: %s' % (inventory_line.product_id.name, inventory_line.product_qty)))
		#		#_qty=	inventory_line.x_qty_adjust
		#		#_amt=	inventory_line.x_unit_cost
		#	#self.action_check(cr, uid, [inv.id], context=context)
		#	#self.write(cr, uid, [inv.id], {'state': 'done'}, context=context)
		#	#self.post_inventory(cr, uid, inv, context=context)
		inv_id=ids[0]
		self.pool.get('dincelaccount.journal.dcs').stock_inventory_journal(cr, uid, ids, inv_id, context)
		self.action_done(cr, uid, ids, context)
		for inv in self.browse(cr, uid, ids, context=context):
			for move in inv.move_ids:
				self.pool.get('stock.move').write(cr, uid, [move.id], {'date':inv.x_date,'date_expected':inv.x_date}, context) #force update the date...
		return True	
		
class dincelstock_inventory_line(osv.Model):	
	_inherit = "stock.inventory.line"
	def _net_amount(self, cr, uid, ids, values, arg, context):
		x1={}
		_ret=0.0
		for record in self.browse(cr, uid, ids):
			_amt=record.x_unit_cost
			_qty=record.x_qty_adjust
			if _amt and _qty:
				_ret=_amt*_qty
			x1[record.id] = _ret 
		return x1	
	_columns = {	
		'x_qty_adjust':fields.float("Qty Variance"),
		'x_unit_cost': fields.float('Standard Cost'),
		'x_prod_length':fields.integer('Length (mm)'),
		'x_th_qty':fields.integer('Theoritical Qty (each)'),
		'x_act_qty':fields.integer('Real Qty (each)'),
		'x_date': fields.datetime('Date'),
		'x_net_amount': fields.function(_net_amount, method=True, string='Net Amount', type='float'), 
	}
	_defaults = {
		'x_qty_adjust': 0,
		'x_date': fields.datetime.now,
	}
	def onchange_createline_new(self, cr, uid, ids, location_id=False, product_id=False, uom_id=False, package_id=False, prod_lot_id=False, partner_id=False, company_id=False, len=False, context=None):
		res =  self.onchange_createline(cr, uid, ids, location_id, product_id, uom_id, package_id, prod_lot_id, partner_id, company_id, context)
		if len and product_id and location_id:
			product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
			if product.x_prod_cat in ['customlength','stocklength']:
				if product.x_prod_cat == "customlength":
					qty_available = self.pool.get('stock.quant').qty_available_custom(cr, uid, product_id, len,  location_id,context ) 
				else:
					qty_available = self.pool.get('stock.quant').qty_available(cr, uid, product_id, location_id,context) 
					qty_available = int(qty_available/(_len*0.001))
				res['value']['x_th_qty'] 	= qty_available
				res['value']['x_act_qty'] 	= qty_available
		return res
	 	