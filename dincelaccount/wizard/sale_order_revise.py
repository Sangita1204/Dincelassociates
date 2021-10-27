import time
from openerp.osv import fields, osv
from openerp.tools.translate import _
import logging
_logger = logging.getLogger(__name__)

class dincelsale_order_revise(osv.osv_memory):
	_name = "dincelsale.order.revise"
	_columns = {
		'date': fields.date('Date'),
		'new_lines':fields.one2many('sale.order.revise.line.new', 'revise_id', 'Invoies'),
		'old_lines':fields.one2many('sale.order.revise.line.old', 'revise_id', 'Invoies'),
		'qty':fields.float("Qty test"),
		'comments':fields.char("Comments"),
		'order_id':fields.many2one('sale.order', 'OrderId'),
		'partner_id':fields.many2one('res.partner', 'Partner'),
		'revise_type':fields.selection([ #>>as revise type
			('shipment','Shipment'),
			('rate','Price changed'),
			('order','Qty changed'),
			('other','Other'),
			], 'Revise type'),
	}
	
	def confirm_revise(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		for record in self.browse(cr, uid, ids, context=context):	#record = self.browse(cr, uid, ids[0], context=context)
			if record.order_id:
				o=record.order_id
				#err_found	= False
				#err_line 	= 0
				#err_msg 	= ""
				revise_sn	= o.x_revise_sn+1
				_new_name	= o.name+"-"+str(revise_sn)
				_new_note	= ""
				if o.note:
					_new_note	+= str(o.note)+ ", " 
				
				vals = {
					'origin_id':o.id,
					'date_order':o.date_order,
					'partner_id':o.partner_id.id,
					'name':_new_name,
					'user_id':o.user_id.id,
					'pudel':o.x_pudel,
					'revise_sn': revise_sn,
					'revise_type': record.revise_type,
					#'note': record.comments,
				}
				if record.comments:
					vals['note']=record.comments
					_new_note += record.comments
				if o.pricelist_id:
					vals['pricelist_id']= o.pricelist_id.id		
				if o.x_street:
					vals['street']=o.x_street
				if o.x_postcode:
					vals['postcode']=o.x_postcode
				if o.x_suburb:
					vals['suburb']=o.x_suburb		
				if o.x_dt_request:
					vals['dt_request']=o.x_dt_request
				if o.x_quote_id:
					vals['quote_id']=o.x_quote_id.id
				if o.payment_term:
					vals['payment_term']=o.payment_term.id
				#if o.origin:
				#	vals['origin']=o.origin
				if o.x_project_id:
					vals['project_id']=o.x_project_id.id
				if o.x_contact_id:
					vals['contact_id']=o.x_contact_id.id
				if o.x_warehouse_id:
					vals['warehouse_id']=o.x_warehouse_id.id
				if o.x_state_id:
					vals['state_id']=o.x_state_id.id
				if o.x_country_id:
					vals['country_id']=o.x_country_id.id
				#if o.company_id:
				#	vals['company_id']=o.company_id.id
				
				#vals['order_line']= _lines_new	
				#_obj=self.pool.get('sale.order')		
				#_logger.error("invoice_salesconfirm_reviseconfirm_revise[" + str(vals)+"]")
				
				_bkid = self.pool.get('sale.order.bak').create(cr, uid, vals, context=context)
				if _bkid:
					#_lines_new = []		
					for line in record.new_lines:
						vals1 = {
							'product_id':line.product_id.id,
							'order_bak_id':_bkid,
							'region_id':line.region_id.id,
							'order_length':line.order_length,
							'order_qty':line.order_qty,
							'product_uom_qty':line.product_uom_qty,
							'price_unit':line.price_unit,
							'sequence':line.sequence,
						}
						if line.product_uom:
							vals1['product_uom'] = line.product_uom.id
						if line.tax_id:
							vals1['tax_id']= line.tax_id.id
						
						#if line.tax_id:
						#	vals1['tax_id']= [(6, 0, line.tax_id.id)]
						#_lines_new.append(vals1)
						_idsub = self.pool.get('sale.order.bak.line').create(cr, uid, vals1, context=context)
					#---------------------------------------------------------------------------------------------------------------------------
					#change back the so, to 'state':'draft' for editing sale.lines.....
					self.pool.get('sale.order').write(cr, uid, o.id, 
								{
								'state': 'draft',#change back to draft, so that it can edit fields, etc.
								'x_type': 'revise',
								'x_revise_sn': revise_sn,
								'note': _new_note
								})  
					#---------------------------------------------------------------------------------------------------------------------------
				return True
			else:
				_logger.error("invoice_salesconfirm_record.order_idrecord.order_id[" + str(record.order_id)+"]")
		
	def on_change_qty(self, cr, uid, ids, product_qty, pay_lines, context=None):
		
		_lines_new = []
		_lines_old = []
		
		if context and context.get('active_ids'):
			
			_ids	= context.get('active_ids')
			
			for o in self.pool.get('sale.order').browse(cr, uid, _ids, context=context):
				vals = {
					'order_id':o.id,
					'partner_id':o.partner_id.id,
					}
				for line in o.order_line:
					vals1 = {
						'product_id':line.product_id.id,
						'region_id':line.x_region_id.id,
						'order_length':line.x_order_length,
						'order_qty':line.x_order_qty,
						'price_unit':line.price_unit,
						'product_uom_qty':line.product_uom_qty,
						'sequence':line.sequence,
					}
					if line.product_uom:
						vals1['product_uom']=line.product_uom.id
						
					if line.tax_id:
						assert len(line.tax_id) == 1, 'This option should only be used for a single id at a time.'
						vals1['tax_id']=line.tax_id[0]
						
					_lines_new.append(vals1)
					_lines_old.append(vals1)
				#if items:
				#	vals['new_lines']=o.company_id.id
				#_lines_new.append(vals)
				vals['new_lines']= _lines_new
				vals['old_lines']= _lines_old

		return {'value':vals}
		
	def _get_init_qty(self, cr, uid, context=None):
		return 1
	_defaults = {
		'qty': _get_init_qty,
		'date': lambda *a: time.strftime('%Y-%m-%d'),
		}
	
class dincelsale_order_revise_line_new(osv.osv_memory):
	_name="sale.order.revise.line.new"
	_columns = {
		'revise_id': fields.many2one('dincelsale.order.revise', 'Sale Order'),
		'sequence': fields.integer('Sequence'),
		'product_id': fields.many2one('product.product', 'Product'),
		'name': fields.char('Name',size=64),
		'order_length':fields.float("Ordered Len"),	
		'order_qty':fields.float("Ordered Qty"),	
		'product_uom_qty':fields.float("UOM Qty"),	
		'product_uom': fields.many2one('product.uom', 'Unit of Measure'),
		'region_id': fields.many2one('dincelaccount.region', 'A/c Region'),
		'price_unit':fields.float("Unit Price"),	
		'tax_id': fields.many2one('account.tax', 'Tax'),
		'discount': fields.float('Discount (%)'),
		#'region_id': fields.many2one('dincelaccount.region', 'Region'),
	}	
	
class dincelsale_order_revise_line_old(osv.osv_memory):
	_name="sale.order.revise.line.old"
	_columns = {
		'revise_id': fields.many2one('dincelsale.order.revise', 'Sale Order'),
		'sequence': fields.integer('Sequence'),
		'product_id': fields.many2one('product.product', 'Product'),
		'name': fields.char('Name',size=64),
		'order_length':fields.float("Ordered Len"),	
		'order_qty':fields.float("Ordered Qty"),	
		'product_uom': fields.many2one('product.uom', 'Unit of Measure'),
		'region_id': fields.many2one('dincelaccount.region', 'A/c Region'),
		'price_unit':fields.float("Unit Price"),	
		'tax_id': fields.many2one('account.tax', 'Tax'),
		'discount': fields.float('Discount (%)'),
		#'region_id': fields.many2one('dincelaccount.region', 'Region'),
	}		