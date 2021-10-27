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
	
class dincelstock_inventory_dcs(osv.Model):
	_name="dincelstock.inventory"
	_inherit = ['mail.thread']
	_description = 'Custom Stock Adjustment'
	_order = 'id desc'
	def _get_default_company(self, cr, uid, context=None):
		company_id = self.pool.get('res.users')._get_company(cr, uid, context=context)
		if not company_id:
			raise osv.except_osv(_('Error!'), _('There is no default company for the current user!'))
		return company_id
		
	_columns={
		'name': fields.char('Name'),
		'date': fields.date('Date'),
		'user_id':fields.many2one('res.users','Prepared By'),
		'location_id':fields.many2one('stock.location', 'Location'),
		'line_ids':fields.one2many('dincelstock.inventory.line','inventory_id', 'Items'),
		'company_id': fields.many2one('res.company', 'Company'),
		'state':fields.selection([
			('draft', 'Draft'),
			('progress', 'Progress'),
			('done', 'Done'),
			], 'State',track_visibility='onchange'),
		
	}
	_defaults = {
		'state': 'draft',
		'company_id': _get_default_company,
		'user_id': lambda obj, cr, uid, context: uid,
		#'name': lambda obj, cr, uid, context: '/',
	}
	''''
	def write(self, cr, uid, ids, vals, context=None):
		
		res = super(dincelstock_inventory_dcs, self).write(cr, uid, ids, vals, context=context)
		for record in self.browse(cr, uid, ids):
			inv=self.pool.get('dincelstock.inventory')
			for line in record.line_ids:
				#@theory_qty	=line.theory_qty
				
				theory_qty	=inv.stock_count(cr, uid, line.location_id.id, line.product_id.id, line.prod_length, context=context)
				real_qty	=line.real_qty
				adjust_qty1	=real_qty-theory_qty
				#adjust_qty	=line.adjust_qty
				_cost		=line.product_id.standard_price
				#if adjust_qty != adjust_qty1:
				sql="update dincelstock_inventory_line set theory_qty='%s',adjust_qty='%s',standard_cost='%s' where id='%s' " % (theory_qty, adjust_qty1,_cost, line.id)
				cr.execute(sql)
				#_logger.error("update.dincelstock_inventory_dcsdincelstock_inventory_dcs["+str(sql)+"]")	
		return res'''
		
	def _create_stock_move(self, cr, uid, inventory, todo_line, context=None):
		#_logger.error("_create_stock_move_create_stock_move[%s]" % (todo_line )) 
		stock_move_obj = self.pool.get('stock.move')
		product_obj = self.pool.get('product.product')
		product_id=todo_line.product_id.id#['product_id']
		prod = product_obj.browse(cr, uid, product_id, context=context)
		inventory_location_id=prod.property_stock_inventory.id
		vals = {
			'name': _('INV:') + (inventory.name or ''),
			'product_id': product_id,
			'product_uom': prod.uom_id.id,
			'date': inventory.date,
			'company_id': inventory.company_id.id,
			#'inventory_id': inventory.id,
			'state': 'assigned',
			'x_order_length': todo_line.prod_length,
			#'restrict_lot_id': todo_line.get('prod_lot_id'),
			#'restrict_partner_id': todo_line.get('partner_id'),
		}
		
		_lmqty=todo_line.adjust_qty*todo_line.prod_length*0.001
		
		if todo_line.adjust_qty < 0:
			#found less than expected
			vals['location_id'] 		= todo_line.location_id.id
			vals['location_dest_id'] 	= inventory_location_id			
			vals['product_uom_qty'] 	= -_lmqty
			vals['x_quantity']			= -todo_line.adjust_qty
			
		else:
			#found more than expected
			vals['location_id'] 		= inventory_location_id			
			vals['location_dest_id'] 	= todo_line.location_id.id
			vals['product_uom_qty'] 	= _lmqty
			vals['x_quantity']			= todo_line.adjust_qty
		#_logger.error("_create_stock_move_create_stovalsvalsvals1112[%s][%s][%s]" % (vals,todo_line.adjust_qty ,_lmqty)
		return stock_move_obj.create(cr, uid, vals, context=context)
		
	def _create_stock_journal(self, cr, uid, inventory, _jid, todo_line, context=None):
		_dtau= self.pool.get('dincelstock.transfer').get_au_datetime(cr, uid, inventory.date)
		_obj = self.pool.get('dincelstock.journal').browse(cr, uid, _jid, context=context)
		_objline = self.pool.get('dincelstock.journal.line')
		vals={'journal_id':_jid,
				'product_id':todo_line.product_id.id,
				'date':_dtau,#inventory.date,
				'date_gmt':inventory.date,
				'period_id':_obj.period_id.id,
				'prod_length':todo_line.prod_length,
				'location_id':todo_line.location_id.id,
				'reference':_('ADJ:') + (inventory.name or ''),
				}
		if todo_line.product_id.x_prod_type=="acs":
			vals['is_acs'] 	= True	
		else:
			vals['is_acs'] 	= False
		if todo_line.adjust_qty < 0:
			#found less than expected
			vals['qty_in'] 		= 0
			vals['qty_out'] 	= -todo_line.adjust_qty	
		else:
			#found more than expected
			vals['qty_in'] 	= todo_line.adjust_qty	
			vals['qty_out'] = 0
			
		return _objline.create(cr, uid, vals, context=context)
		
	def button_validate_inventory(self, cr, uid, ids, context=None):
		move_obj = self.pool.get('stock.move')
		for inv in self.browse(cr, uid, ids, context=context):
			_jid = self.pool.get('dincelstock.journal').stock_adjust_confirm(cr, uid, inv.id, context)
			for line in inv.line_ids:
				move_id= self._create_stock_move(cr, uid, inv, line, context)
				move_obj.action_done(cr, uid, [move_id], context=context)
				
				_id2= self._create_stock_journal(cr, uid, inv, _jid, line, context)
				
			# self.action_check(cr, uid, [inv.id], context=context)
			self.write(cr, uid, [inv.id], {'state': 'done'}, context=context)
		    # self.post_inventory(cr, uid, inv, context=context)
			
		return True
		 
	def stock_count(self, cr, uid, loc_id, product_id, prod_length, context=None):
		sql="""select sum(qty_in-qty_out) as net 
				from dincelstock_journal_line where 
				location_id='%s' and product_id='%s' and prod_length='%s'""" % (loc_id, product_id, prod_length)
		cr.execute(sql)
		res = cr.fetchone()
		if res and res[0] != None:
			return res[0]
		else:
			return 0		
	
class dincelstock_inventory_line(osv.Model):
	_name 	= "dincelstock.inventory.line"
	_order 	= "sequence"
	_columns = {
		'inventory_id': fields.many2one('dincelstock.inventory', 'Ref', required=True, ondelete='cascade', select=True),
		'name': fields.char('Description', required=True),
		'sequence': fields.integer('Sequence'),
		'location_id':fields.many2one('stock.location', 'Location'),
		'product_id': fields.many2one('product.product', 'Product'),
		'theory_qty': fields.integer("Theorical Qty"),	
		'real_qty': fields.integer("Real Qty"),	
		'standard_cost': fields.float("Standard Cost"),	
		'adjust_qty':fields.integer('Qty Diff'),
		'prod_length':fields.integer('Length'),
		'product_qty':fields.float('Qty Prod Qty Lm'),
		'diff_qty':fields.float('Qty Diff LM'),
		'product_uom': fields.many2one('product.uom', 'Unit of Measure'),
		'state':fields.selection([
			('draft', 'Draft'),
			('progress', 'Progress'),
			('done', 'Done'),
			], 'State'),
	}	
	_defaults = {
		'state': 'draft',
	}
	def onchange_createline_new1(self, cr, uid, ids, location_id, product_id, prod_length, real_qty, context=None):
		if context is None:
			context = {}
		val1={}
		try:
			if product_id:
				product = self.pool.get('product.product').browse(cr, uid, product_id, context)
				if product.x_prod_cat in ['stocklength']:
					val1.update ( {'prod_length': product.x_stock_length } ) 
				
				if prod_length and location_id:
					inv=self.pool.get('dincelstock.inventory')
					_qty=inv.stock_count(cr, uid, location_id, product_id, prod_length, context=context)
					
					#val1.update ( {'real_qty': _qty } ) 
					val1.update ( {'real_qty': _qty ,'theory_qty': _qty,'adjust_qty': 0} ) 
					#val1.update ( {'real_qty': _qty } ) 
					
				val1['name'] 	= product.name
		except Exception,e:
			
			pass
			 
		self.write( cr, uid, ids, val1, context ) 
		return {'value':val1}
	
	def onchange_createline_new2(self, cr, uid, ids, location_id, product_id, prod_length, real_qty, context=None):
		if context is None:
			context = {}
		val1={}
		try:
			if product_id:
				product = self.pool.get('product.product').browse(cr, uid, product_id, context)
				if product.x_prod_cat in ['stocklength']:
					val1.update ( {'prod_length': product.x_stock_length } ) 
				
				if prod_length and location_id:
					inv=self.pool.get('dincelstock.inventory')
					_qty=inv.stock_count(cr, uid, location_id, product_id, prod_length, context=context)
					
					val1.update ( {'adjust_qty': real_qty-_qty } ) 
					val1.update ( {'theory_qty': _qty } ) 
				
				val1['name'] 	= product.name
		except Exception,e:
			
			pass
			 
		self.write( cr, uid, ids, val1, context ) 
		return {'value':val1}
	
class dincelstock_journal(osv.Model):
	_name 	= "dincelstock.journal"
	_columns = {
		'name': fields.char('Name'),
		'origin': fields.char('Origin'),
		'date': fields.datetime('Date'),
		'period_id':fields.many2one('account.period','Period'),
		'order_id':fields.many2one('sale.order','Order'),
		'user_id':fields.many2one('res.users','Prepared By'),
		'line_ids':fields.one2many('dincelstock.journal.line','journal_id', 'Items'),
		'state':fields.selection([
			('draft', 'Draft'),
			('progress', 'Progress'),
			('done', 'Done'),
			], 'State'),
		
	}
	_defaults = {
		'state': 'draft',
	}
	def stock_adjust_confirm(self, cr, uid, inv_id, context=None):
		inv_obj 		= self.pool.get('dincelstock.inventory').browse(cr, uid, inv_id, context=context)
		_operiod 		= self.pool.get('account.period') 
		_objperiodcr	= _operiod.find(cr, uid, inv_obj.date, context=context)#[0]
		
		if _objperiodcr:
			period_id 			= _objperiodcr[0]# in above code
			
			_name	= self.pool.get('ir.sequence').get(cr, uid, 'dincelstock.journal') #stock.transfer
			vals	= {'name': _name, 
						'origin': "ADJ/" + inv_obj.name, 
						'date': inv_obj.date, 
						'user_id': inv_obj.user_id.id, 
						'state': 'draft',
						'period_id':period_id,
						}
			#for line in inv_obj.line_ids:
			_id=self.create(cr, uid, vals, context)	
			return _id
		
	def ibt_sent_confirm(self, cr, uid, ibt_id, context=None):
		_obj 		= self.pool.get('dincelstock.transfer').browse(cr, uid, ibt_id, context=context)
		_operiod 		= self.pool.get('account.period') 
		_objperiodcr	= _operiod.find(cr, uid, _obj.date, context=context)#[0]
		
		if _objperiodcr:
			period_id 			= _objperiodcr[0]# in above code
			
			_name	= self.pool.get('ir.sequence').get(cr, uid, 'dincelstock.journal') #stock.transfer
			vals	= {'name': _name, 
						'origin': "IBTSENT/" + _obj.name, 
						'date': _obj.date, 
						'user_id': _obj.user_id.id, 
						'state': 'draft',
						'period_id':period_id,
						}
			if _obj.order_id:
				vals['order_id']=_obj.order_id.id 
			_id=self.create(cr, uid, vals, context)	
			return _id
		
		
	def ibt_received_confirm(self, cr, uid, ibt_id, context=None):
		_obj 		= self.pool.get('dincelstock.transfer').browse(cr, uid, ibt_id, context=context)
		_operiod 		= self.pool.get('account.period') 
		_objperiodcr	= _operiod.find(cr, uid, _obj.date_received, context=context)#[0]
		
		if _objperiodcr:
			period_id 			= _objperiodcr[0]# in above code
			
			_name	= self.pool.get('ir.sequence').get(cr, uid, 'dincelstock.journal') #stock.transfer
			vals	= {'name': _name, 
						'origin': "IBTRX/" + _obj.name, 
						'date': _obj.date_received, 
						'user_id': _obj.user_id.id, 
						'state': 'draft',
						'period_id':period_id,
						}
			if _obj.order_id:
				vals['order_id']=_obj.order_id.id 
			_id=self.create(cr, uid, vals, context)	
			return _id
			
	def product_produced_confirm(self,cr, uid,mrp_id,dt,context=None):
		_obj 		= self.pool.get('mrp.production').browse(cr, uid, mrp_id, context=context)
		_operiod 		= self.pool.get('account.period') 
		#cause in part production, due to some reason the dtProduced is holding the previous value stored in database
		if dt:#_obj.x_dt_produced:
			_dt=dt#_obj.x_dt_produced
		else:
			_dt= datetime.datetime.today() #All time gmt date time[3/4/18]
		#All time gmt date time [3/4/18]
		#_dt			= self.pool.get('dincelstock.transfer').get_au_datetime(cr, uid, _dt)
		#_objperiodcr	= _operiod.find(cr, uid, _obj.date_finished, context=context)#[0]
		_objperiodcr	= _operiod.find(cr, uid, _dt, context=context)#[0]
		
		if _objperiodcr:
			period_id 			= _objperiodcr[0]# in above code
			
			_name	= self.pool.get('ir.sequence').get(cr, uid, 'dincelstock.journal') #stock.transfer
			vals	= {'name': _name, 
						'origin': "MRP/" + _obj.name, 
						'date': _dt,#_obj.date_finished, 
						'user_id': _obj.user_id.id, 
						'state': 'draft',
						'period_id':period_id,
						}
			if _obj.x_sale_order_id:
				vals['order_id']=_obj.x_sale_order_id.id 
			_id=self.create(cr, uid, vals, context)	
			return _id
			
	def order_delivery_confirm(self,cr, uid,docket_id,context=None):
		_obj 		= self.pool.get('dincelstock.pickinglist').browse(cr, uid, docket_id, context=context)
		_operiod 	= self.pool.get('account.period') 
		
		_dt			=_obj.time_picking # self.pool.get('dincelstock.transfer').get_au_datetime(cr, uid, _obj.time_picking)
		
		_objperiodcr	= _operiod.find(cr, uid, _dt, context=context)#[0]
		
		if _objperiodcr:
			period_id 			= _objperiodcr[0]# in above code
			
			_name	= self.pool.get('ir.sequence').get(cr, uid, 'dincelstock.journal') #stock.transfer
			vals	= {'name': _name, 
						'origin': "DOCKET/" + _obj.name, 
						'date': _dt,#_obj.date_picking, 
						'user_id': _obj.user_id.id, 
						'state': 'draft',
						'period_id':period_id,
						}
			
			_id=self.create(cr, uid, vals, context)	
			return _id
		
	def order_return_confirm(self,cr,uid,return_id,context =None):
		_obj 		= self.pool.get('dincelsale.ordersale').browse(cr, uid, return_id, context=context)
		_operiod 		= self.pool.get('account.period') 
		_dt			= self.pool.get('dincelstock.transfer').get_au_datetime(cr, uid, _obj.date_order)
		_objperiodcr	= _operiod.find(cr, uid, _dt, context=context)#[0]
		
		if _objperiodcr:
			period_id 			= _objperiodcr[0]# in above code
			
			_name	= self.pool.get('ir.sequence').get(cr, uid, 'dincelstock.journal') #stock.transfer
			vals	= {'name': _name, 
						'origin': "RET/" + _obj.name, 
						'date': _dt,#_obj.date_order, 
						'user_id': uid, 
						'state': 'draft',
						'period_id':period_id,
						}
			
			_id=self.create(cr, uid, vals, context)	
			return _id
		else:
			raise osv.except_osv(_('No period found!'), _('Please check if date is correct.'))
class dincelstock_journal_line(osv.Model):
	_name 	= "dincelstock.journal.line"
	_order 	= "id desc"
	def _balance_qty(self, cr, uid, ids, values, arg, context):
		x1={}
		#_ret=''
		for record in self.browse(cr, uid, ids):#for record in self.browse(cr, uid, ids):
			x1[record.id] = record.qty_in-record.qty_out 
		return x1
	_columns = {
		'journal_id': fields.many2one('dincelstock.journal', 'Ref', required=True, ondelete='cascade', select=True),
		'name': fields.char('Name'),
		'reference': fields.char('Ref'),
		'date': fields.datetime('Date',help="AU Date"),
		'date_gmt': fields.datetime('Date GMT',help="GMT Date"),
		'order_id':fields.many2one('sale.order','Order'),
		'period_id':fields.many2one('account.period','Period'),
		'location_id':fields.many2one('stock.location', 'Location'),
		'product_id': fields.many2one('product.product', 'Product'),
		'is_acs': fields.boolean('Is Acs?'),
		'prod_length':fields.integer('Length'),
		'qty_in': fields.integer("In Qty"),	
		'qty_out': fields.integer("Out Qty"),	
		'qty_balance': fields.function(_balance_qty, method=True, string='Balance',type='integer'), #DO NOT USE
		'product_uom': fields.many2one('product.uom', 'Unit of Measure'),
		'state':fields.selection([
			('draft', 'Draft'),
			('progress', 'Progress'),
			('done', 'Done'),
			], 'State'),
		
	}
	def unlink(self, cr, uid, ids, context=None):
		context = context or {}
		if True:
			str1="Deletion of stock movement not allowed."
			raise osv.except_osv(_('Error'), _(''+str1))
		return super(dincelstock_journal_line, self).unlink(cr, uid, ids, context=context)
		
	_defaults = {
		'state': 'draft',
		'is_acs':True,
	}