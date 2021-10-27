from openerp.osv import osv, fields
from datetime import date
#from openerp.addons.base_status.base_state import base_state
import time 
import datetime
import logging
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
#import dincelaccount
from openerp import api
from time import gmtime, strftime
_logger = logging.getLogger(__name__)

class dincelpurchase_orderpurchase(osv.Model):
	_inherit = "purchase.order"
	
	def _create_invoice_line(self, cr, uid, vals, context=None):

		obj_inv 	= self.pool.get('account.invoice.line')
		product_obj = self.pool.get('product.product')
		
		product_obj = product_obj.browse(cr, uid, vals['product_id'], context)
		
		vals['name']= product_obj.name
		
		inv_id = obj_inv.create(cr, uid, vals, context=context)
			
		return inv_id
		
	def _create_invoice(self, cr, uid, pur_id, dt_invoice, context=None):
		
		inv_id 	= 0
		
		_obj 	= self.pool.get('purchase.order')
		
		journal_id = False	
		
		_objr = self.pool.get('account.journal')
		obj_ids = _objr.search(cr, uid, [('type', '=', "purchase")])
		if obj_ids:
			journal_id= obj_ids[0] if obj_ids[0] else False 
		
		#_logger.error("purchase_confirm_test:journal_id[" + str(journal_id)+ "]journal_id]")	
			
		if context and pur_id and journal_id:
			
			obj_inv = self.pool.get('account.invoice')
			
			_obj 	= _obj.browse(cr, uid, pur_id, context)
			
			vals = {
					'journal_id': journal_id,
                    'origin': _obj.name,
                    'reference': _obj.name,
                    'partner_id': _obj.partner_id.id,
					'internal_number': _obj.name,
					'section_id': 1,
                    'type': 'in_invoice',
					'account_id':_obj.partner_id.property_account_payable.id
					}
			if dt_invoice:
				vals['date_invoice']=dt_invoice
			
			inv_id = obj_inv.create(cr, uid, vals, context=context)
			#_logger.error("purchase_confirm_test:inv_id[" + str(inv_id)+ "]inv_id]")
		return inv_id
	
	def action_picking_create_dcs(self, cr, uid, ids, context=None):
		for order in self.browse(cr, uid, ids):
			picking_vals = {
				'picking_type_id': order.picking_type_id.id,
				'partner_id': order.partner_id.id,
				'date': max([l.date_planned for l in order.order_line]),
				'origin': order.name,
				'x_buy_order_id': order.id,
			}
			picking_id = self.pool.get('stock.picking').create(cr, uid, picking_vals, context=context)
			self._create_stock_moves(cr, uid, order, order.order_line, picking_id, context=context)
		
	def purchase_confirm_dcs(self, cr, uid, ids, context=None):	
		#self.wkf_confirm_order(self, cr, uid, ids, context)
		self.action_picking_create_dcs( cr, uid, ids, context)
		todo = []
		for po in self.browse(cr, uid, ids, context=context):
			if not po.order_line:
				raise osv.except_osv(_('Error!'),_('You cannot confirm a purchase order without any purchase order line.'))
			for line in po.order_line:
				if line.state=='draft':
					todo.append(line.id)        
		self.pool.get('purchase.order.line').action_confirm(cr, uid, todo, context)
		##self.write(cr, uid, ids, {'shipped':1,'state':'approved'}, context=context)
		for id in ids:
			#self.write(cr, uid, [id], {'state' : 'confirmed', 'validator' : uid})
			self.write(cr, uid, [id], {'state' : 'approved', 'validator' : uid})
		return True
		
	def purchase_confirm_dcs_xx(self, cr, uid, ids, context=None):	
		if context is None:
			context = {}
		
		#id =  context.get('active_id', False)	
		
			#for line in record.order_line:
			#	name = line.name
			#	product_id = line.product_id.id or None
				
		dt_invoice = datetime.datetime.now()		
		inv_id 		= self._create_invoice(cr, uid, ids[0], dt_invoice, context=context)
		
		if inv_id:
			#_logger.error("purchase_confirm_test:inv_id[" + str(inv_id)+ "]inv_id]")
			
			for record in self.browse(cr, uid, ids, context=context):
				for line in record.order_line:
					qty = line.product_qty
					product_id = line.product_id.id
					#if ar_items_done.has_key(product_id):
					#	qty = qty - ar_items_done[product_id]		
					if qty > 0:
						vals = {
							'product_id': product_id,
							'quantity': qty,
							'invoice_id': inv_id,
							'origin': record.name,
							'price_unit': line.price_unit,
							'price_subtotal': line.price_unit*qty,
						}
						if line.x_region_id:
							vals['x_region_id']=line.x_region_id.id
						if line.x_coststate_id:
							vals['x_coststate_id']=line.x_coststate_id.id	
						if line.taxes_id:
							vals['invoice_line_tax_id'] = [(6, 0, line.taxes_id.ids)]
						
						line_id 		= self._create_invoice_line(cr, uid, vals, context=context)
				
			
			#for taxes
			obj_inv = self.pool.get('account.invoice')
			obj_inv = obj_inv.browse(cr, uid, inv_id, context)
			obj_inv.button_compute(True) #For taxes
			
			
			
			self.write(cr, uid, ids, {'state': 'approved'}, context=context)
			
			return self._view_invoice(cr, uid, inv_id, context=context) 
			#return value	
		return {}
	
	def _view_invoice(self, cr, uid, inv_id, context=None):
		view_id = self.pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'dincelaccount.invoice.form')], limit=1) 	
		#_logger.error("invoice_sales_validate.inv_id["+str(inv_id)+"]["+str(view_id)+"]")
		value = {
			'domain': str([('id', 'in', inv_id)]),
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'account.invoice',
			'view_id': view_id,
			'type': 'ir.actions.act_window',
			'name' : _('Invoice'),
			'res_id': inv_id
		}
		
		return value	
		
	def receive_product_dcs(self, cr, uid, ids, context=None):	
		#NOTE as existing purchase module works ....no need to custom built
		#APR20,2016 :Shukra
		if context is None:
			context = {}
		order_obj 	= self.pool.get('purchase.order')
		obj_line 	= self.pool.get('purchase.order.line')
		pick_obj 	= self.pool.get('stock.picking')
		transfer_obj 	= self.pool.get('stock.transfer.details')
		transfer_line_obj 	= self.pool.get('stock.transfer.details.items')
		
		pick_type_id =0
		_type = self.pool.get('stock.picking.type')
		obj_ids = _type.search(cr, uid, [('code', '=', "incoming")])
		if obj_ids:
			pick_type_id= obj_ids[0] if obj_ids[0] else False 
		#_logger.error("pick_type_idpick_type_idpick_type_idt["+str(obj_ids)+"]["+str(pick_type_id)+"]")	
		if not pick_type_id:
			return False
		ar_items_done 	= {}
		ar_items_rem  	= {}
		
		tot_qty_rem 	= 0
		found			= False
		for record in self.browse(cr, uid, ids, context=context):	
			sql = "select i.* from stock_transfer_details_items i,stock_transfer_details t,stock_picking s where i.transfer_id=t.id and t.picking_id=s.id and s.origin='%s' " % record.name
			cr.execute(sql)
			rows1 	= cr.dictfetchall()
			for row1 in rows1:
				transfer_qty = row1['quantity']
				product_id 	 = row1['product_id']
				
				skey	= str(product_id) #+ "_" + str(order_length)
				if ar_items_done.has_key(skey) == False:
					ar_items_done[skey] = transfer_qty
				else:
					ar_items_done[skey] += transfer_qty
			
		
			for line in record.order_line:
				qty = line.product_qty
				product_id = line.product_id.id
				#order_length = line.x_order_length
				skey	= str(product_id) #+ "_" + str(order_length)
				if ar_items_done.has_key(skey):
					qty = qty - ar_items_done[skey]
			
				tot_qty_rem += qty		
				
			#only if any remain qty is greater than zero
			if tot_qty_rem > 0 :
				sql = "select 1 from stock_picking   where origin='%s' " % record.name
				cr.execute(sql)
				count1 	= cr.rowcount
				
				sname = record.name + "-" + str(count1+1)#"/"  #todo generated auto number
				vals = {
					'picking_type_id': pick_type_id,
                    'origin': record.name,
                    'partner_id': record.partner_id.id,
					'name':sname,
					'move_type':'direct',
					'company_id':record.company_id.id,
					'invoice_state':'none'
					}
			
				vals['date_done']=datetime.datetime.now() 
				#first create the invoice record
				pick_id = pick_obj.create(cr, uid, vals, context=context)
				
				#now loop throught all item lines and create invoice line if net qty remaining is greater than zero
				for line in record.order_line:
					qty = line.product_qty#line.x_order_qty
					product_id = line.product_id.id
					#order_length= line.x_order_length
					#if order_length:
					#	skey	= str(product_id) + "_" + str(order_length)
					#else:	
					skey	= str(product_id)
					if ar_items_done.has_key(skey):
						qty = qty - ar_items_done[skey]		
					if qty > 0:
						
						vals = {
							'product_id': product_id,
							'ship_qty': qty,
							'pickinglist_id': pick_id,
							'origin': record.name,
							'price_unit': line.price_unit,
							#'disc_pc':line.discount,
						}
						#if order_length:
						#	vals['order_length']= line.x_order_length,
							
						vals['name']= line.product_id.name
							
						line_obj.create(cr, uid, vals, context=context)
						
				found = True

				view_id 		= self.pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'dincelstock.delivery.form.view')], limit=1) 	
				#_logger.error("invoice_sales_validate.view_id["+str(view_id)+"]")
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
				#return pick_id
		if found == False:
			raise osv.except_osv(_('No delivery remaining!'), _('No pending delivery found!'))
		return False
		#return {}

	def view_invoice_dcs(self, cr, uid, ids, context=None):
		name=""
		for record in self.browse(cr, uid, ids, context=context):
			name = record.name
		_objr = self.pool.get('account.invoice')
		
		obj_ids = _objr.search(cr, uid, [('type', '=', "in_invoice"),('internal_number','=',name)])
		
		if obj_ids:
			inv_id= obj_ids[0] if obj_ids[0] else False 
			return self._view_invoice(cr, uid, inv_id, context=context) 
		return {}
	
	
	def dcs_print_po(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		datas = {'ids': context.get('active_ids', [])}
	 
		datas['form']  = self.read(cr, uid, ids, context=context)[0]

		return self.pool['report'].get_action(cr, uid, [], 'purchase.report_purchase_invoice', data=datas, context=context)		
		
	def dcs_print_po_pdf(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		datas = {'ids': context.get('active_ids', [])}
		datas['form']  = self.read(cr, uid, ids, context=context)[0]
		return self.pool['report'].get_action(cr, uid, [], 'purchase.report_purchase_invoice_pdf', data=datas, context=context)			
	_columns = {
		'x_warehouse_address':fields.many2one('dincelcrm.warehouse.address',"Delivery Address"),
	}
class dincelpurchase_account_invoice_line(osv.Model):
	_inherit = "account.invoice.line"
	_columns={
		'price_unit': fields.float('Unit Price', required=True, digits_compute= dp.get_precision('Purchase Price')),
	} 
	
class incelpurchase_purchase_order_line(osv.Model):
	_inherit = "purchase.order.line"
	_columns={
		'x_region_id': fields.many2one('dincelaccount.region', 'A/c Region'),
		'x_coststate_id':fields.many2one("res.country.state","Cost Centre"),
		'price_unit': fields.float('Unit Price', required=True, digits_compute= dp.get_precision('Purchase Price')),
	}
	#@api.model
	'''def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
		res = super(incelpurchase_purchase_order_line, self).fields_view_get(
			view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
		_logger.error("invoice_sales_validateresresresc["+str(res)+"]")
		if self._context.get('partner_id'):
			doc = etree.XML(res['arch'])
			for node in doc.xpath("//field[@name='product_id']"):
				#if self._context['partner_id'] in ('in_invoice', 'in_refund'):
				#	node.set('domain', "[('purchase_ok', '=', True)]")
				#else:
				node.set('domain', "[('sale_ok', '=', True)]")
			_logger.error("invoice_sales_validatedocdocdoc["+str(doc)+"]")
			res['arch'] = etree.tostring(doc)
		return res'''
		
class dincelpurchase_stock_pick(osv.Model):
	_inherit="stock.picking"
	
	def pending_invoice(self, cr, uid, ids, values, arg, context):
		x={}
		ar_items_done={}
		#totqty=0
		for record in self.browse(cr, uid, ids):
			
			found	= "0"
			
			if record.invoice_state == "invoiced" and record.x_pending_inv_coming == True:
			
			#else:
				for line in record.move_lines: 
					skey 	 = str(line.product_id.id)
					_uom_qty = line.product_uom_qty
					#totqty	+=_uom_qty
					if ar_items_done.has_key(skey) == False:
						ar_items_done[skey]  = _uom_qty
					else:
						ar_items_done[skey] += _uom_qty
				
				
				sql= "select a.quantity,a.product_id from account_invoice i,account_invoice_line a where i.id=a.invoice_id and i.origin='" + str(record.name)+"'"		
				cr.execute(sql)
				rows = cr.fetchall()
				#_logger.error("dincelpurchase_move_lines_id:["+str(sql)+"]["+str(rows)+"]["+str(ar_items_done)+"]")	
				for row in rows: 
					skey 	 = str(row[1])
					if ar_items_done.has_key(skey):
						ar_items_done[skey] -= row[0]
				for sk in ar_items_done:  
					if ar_items_done[sk]>0: #if any item left
						found="1"
			x[record.id]=found
		return x
		
	_columns={
		'x_act_state': fields.selection([
            ('none', 'None'),
            ('received', 'Received'),
            ('reversed', 'Reversed'),
			], 'Account Status'),
		'x_pending_inv': fields.function(pending_invoice, method=True, string='has lead oppr',type='char'),
		'x_pending_inv_coming':fields.boolean("Is future invoice coming"),
		'x_buy_order_id': fields.many2one('purchase.order','Purchase Order Reference'),
		}
	_defaults = {
		'x_act_state': 'none',
		'x_pending_inv_coming':False,
	}	
	
	def _create_invoice_line(self, cr, uid, vals, context=None):

		obj_inv 	= self.pool.get('account.invoice.line')
		product_obj = self.pool.get('product.product')
		product_obj = product_obj.browse(cr, uid, vals['product_id'], context)
		vals['name']= product_obj.name
		
		inv_id = obj_inv.create(cr, uid, vals, context=context)
			
		return inv_id
		
	#def _create_invoice(self, cr, uid, pur_id, dt_invoice, context=None):
	#	
		
		
		
	def create_invoice_received_dcs(self, cr, uid, ids, context=None):
		inv_id 	= 0
		
		_obj 	= self.pool.get('purchase.order')
		
		journal_id = False	
		
		_objr = self.pool.get('account.journal')
		obj_ids = _objr.search(cr, uid, [('type', '=', "purchase")])
		if obj_ids:
			journal_id= obj_ids[0] if obj_ids[0] else False 
			
		if journal_id:
			dt_invoice = datetime.datetime.now()	
			obj_inv = self.pool.get('account.invoice')
			
			ar_items_done={}
					
			for record in self.browse(cr, uid, ids, context=context):
				
				sql= "select a.quantity,a.product_id from account_invoice i,account_invoice_line a where i.id=a.invoice_id and i.origin='" + str(record.name)+"'"		
				cr.execute(sql)
				rows = cr.fetchall()
				
				for row in rows: 
					skey 	 = str(row[1])
					if ar_items_done.has_key(skey) == False:
						ar_items_done[skey] = row[0]
					else:
						ar_items_done[skey] += row[0]
						
				vals = {
						'journal_id': journal_id,
						'origin': record.name,
						'reference': record.name,
						'partner_id': record.partner_id.id,
						'internal_number': record.name,
						'section_id': 1,
						'type': 'in_invoice',
						'account_id':record.partner_id.property_account_payable.id
						}
				if dt_invoice:
					vals['date_invoice']=dt_invoice
				
				inv_id = obj_inv.create(cr, uid, vals, context=context)
			#_logger.error("purchase_confirm_test:inv_id[" + str(inv_id)+ "]inv_id]")
		
		if inv_id:
			 
			order_id = None
			for record in self.browse(cr, uid, ids, context=context):
				for line in record.move_lines:
					qty = line.product_uom_qty
					product_id = line.product_id.id
					
					if ar_items_done.has_key(str(line.product_id.id)):
						qty = qty - ar_items_done[str(line.product_id.id)]		
					
					if qty > 0:
					
						vals = {
							'product_id': product_id,
							'quantity': qty,
							'invoice_id': inv_id,
							'origin': record.name,
							'price_unit': line.price_unit,
							'price_subtotal': line.price_unit*qty,
						}
						purchase_line 	= line.purchase_line_id
						order_id 		= purchase_line.order_id
						vals['invoice_line_tax_id'] = [(6, 0, [x.id for x in purchase_line.taxes_id])]
						 
						line_id = self._create_invoice_line(cr, uid, vals, context=context)
				
			
			#for taxes
			obj_inv = self.pool.get('account.invoice')
			obj_inv = obj_inv.browse(cr, uid, inv_id, context)
			obj_inv.button_compute(True) #For taxes
			
			if order_id:
				 
				order1 = _obj.browse(cr, uid, order_id.id, context)
				 
				order1.write({'invoice_ids': [(4, inv_id)]})
				#view_id = self.pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'dincelaccount.invoice.form')], limit=1) 	
				view_id = self.pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'account.invoice_supplier_form')], limit=1) 	
				
				#_logger.error("invoice_sales_validate.inv_id["+str(inv_id)+"]["+str(view_id)+"]")
				value = {
					'domain': str([('id', 'in', inv_id)]),
					'view_type': 'form',
					'view_mode': 'form',
					'res_model': 'account.invoice',
					'view_id': view_id,
					'type': 'ir.actions.act_window',
					'name' : _('Invoice'),
					'res_id': inv_id
				}
				return value
		#return inv_id
		
	def validate_stock_received_dcs(self, cr, uid, ids, context=None):
		_operiod 	= self.pool.get('account.period') 
		_oprod 		= self.pool.get('product.product')
		
		product_uom = self.pool.get('product.uom')
		
		#_oglcodes 	= self.pool.get('dincelaccount.config.settings').browse(cr, uid, 1, context=context)
		_oglcodes 	= self.pool.get('dincelaccount.config.settings')
		_id			= _oglcodes.search(cr, uid, [], limit=1) 	
		if _id:
			_oglcodes 	= _oglcodes.browse(cr, uid, _id, context=context)
		else:
			raise osv.except_osv(_('No account settings!'), _('No account settings found!'))
			
		_oacct		= self.pool.get('account.move')
		
		_opurline 		= self.pool.get('purchase.order.line')
		_opur 			= self.pool.get('purchase.order')
		
		acct_tax 		= False
		acct_stock 		= False
		acct_good2inv 	= False #Goods Reecived Not Yet Invoiced
		
		if _oglcodes:
			acct_stock 	= _oglcodes.stock_inventory.id or False
			_tax 		= _oglcodes.buy_payable_tax
			if _tax:
				_taxobj = self.pool.get('account.tax').browse(cr, uid, _tax.id, context=context)
				acct_tax	=_taxobj.account_collected_id.id or False
			acct_good2inv 	= _oglcodes.stock_received_notinvoiced.id or False
		#_journal_id		= self.pool.get('account.journal').search(cr, uid, [('type', '=', 'general')], limit=1)[0] 	
		_journal_id		= _oglcodes.stock_journal.id or False
		pick_id 	=None
		amt_stock 	=0
		origin 		=""
		picking_type_code=""
		for record in self.browse(cr, uid, ids, context=context):
			origin 	= record.origin
			pick_id = record.id
			picking_type_code=record.picking_type_code
			#date_invoice	= datetime.datetime.today()
			date_invoice	= record.min_date
			if record.x_buy_order_id:
				po_id		= record.x_buy_order_id.id
			else:
				po		= _opur.search(cr, uid, [('name', '=', origin)], limit=1)
				po_id	= po[0]
			pick_state = record.state
			
			if record.state not in ('done'):
				raise osv.except_osv(_('No delivery confirmed!'), _('No confirmed delivery found!'))
			else:
				if po_id:
					_opur = _opur.browse(cr, uid, po_id, context=context)
					
					for line in record.move_lines:
						qty			= line.product_qty 
						#line.product_qty  	-->>>> that's how stored in stock
						#line.product_uom_qty  -->>>> thats how get purchased
						#product_id 	= line.product_id
						price_unit	= line.product_id.standard_price
						
						#product = line.product_id
						default_uom_po_id = line.product_id.uom_po_id.id
						#ctx = context.copy()
						#ctx['tz'] = requisition.user_id.tz
						#date_order = requisition.ordering_date and fields.date.date_to_datetime(self, cr, uid, requisition.ordering_date, context=ctx) or fields.datetime.now()
						
						#get exact product qty from copute qtgy
						#from =To
						#qty = product_uom._compute_qty(cr, uid, line.product_uom.id, line.product_uom_qty, default_uom_po_id)
						#_logger.error("dincelpurchase_move_lines_id_compute_qty_compute_qty:["+str(line.product_uom.id)+"]["+str(default_uom_po_id)+"]["+str(qty)+"]")	
						#_logger.error("dincelpurchase_move_lines_id:["+str(line.id)+"]["+str(qty)+"]")	
						#_itemid 	= _opurline.search(cr, uid, [('product_id', '=', product_id.id),('order_id', '=', po[0])], limit=1)[0]
						#if _itemid:
						#	_item 	= _opurline.browse(cr, uid, _itemid, context=context)
						#	price_unit = _item.price_unit
						#else:
						#	price_unit = 0
						amt_stock = amt_stock + (qty*price_unit)
		
		#-----start of journal entry
		#_logger.error("dincelpurchase_move_lines_idpick_idpick_id:["+str(pick_id)+"]["+str(amt_stock)+"]")	
		if pick_id and amt_stock>0:
			journal_ref 	= "STK"
			invoice_name 	= journal_ref + "_" + str(_opur.id) + "_" + str(pick_id)
			company_id		= _opur.company_id.id
			#date_invoice	= datetime.datetime.today()
			partner_id		= _opur.partner_id.id
			
			
			_objperiodcr	= _operiod.find(cr, uid, date_invoice, context=context)#[0]
			if _objperiodcr:
				period_id 	= _objperiodcr[0] # in above code
			else:
				period_id 	= None
			
			#_journal_id		= self.pool.get('account.journal').search(cr, uid, [('type', '=', 'general')], limit=1)[0] 	
			
			state_move		= "posted"	#"draft" [NOTE, if posted then it will automatically reported in Tiral Balance, General Ledger, reports, etc]
			
			actmove = self.pool.get('dincelaccount.journal.dcs')
			
			actmove.ref_name 	= origin+"_"+str(pick_id)
			actmove.state_move 	= state_move
			actmove.journal_id 	= _journal_id
			actmove.move_name 	= invoice_name
			actmove.date_move	= date_invoice
			actmove.period_id	= period_id
			actmove.partner_id	= partner_id
			
			_id	=	actmove.insert_move(cr, uid, ids, context=context)
			if _id:
				#---------------------1---------------------
				state_line	= "valid"
				account_id	= acct_stock
				if picking_type_code and picking_type_code=="outgoing":
					debit		= 0
					credit 		= amt_stock
				else:
					debit		= amt_stock
					credit 		= 0
				actmove.move_id 	= _id
				actmove.state_line 	= state_line
				actmove.journal_id 	= _journal_id
				actmove.move_line_name = invoice_name
				actmove.date_move	= date_invoice
				actmove.period_id	= period_id
				actmove.partner_id	= partner_id
				actmove.account_id	= account_id
				actmove.credit		= credit
				actmove.debit		= debit
				actmove.insert_move_line(cr, uid, ids, context=context)
				
				#---------------------2---------------------
				account_id	= acct_good2inv
				if picking_type_code and picking_type_code=="outgoing":
					debit		= amt_stock
					credit 		= 0
				else:
					debit		= 0
					credit 		= amt_stock
				#actmove.move_id 	= _id
				#actmove.state_line 	= state_line
				#actmove.journal_id 	=_journal_id
				#actmove.move_line_name = invoice_name
				#actmove.date_move	=date_invoice
				#actmove.period_id	=period_id
				#actmove.partner_id	=partner_id
				actmove.account_id	=account_id
				actmove.credit	=credit
				actmove.debit	=debit
				actmove.insert_move_line(cr, uid, ids, context=context)

				vals={'x_act_state':'received'}
				self.write(cr, uid, pick_id, vals)	
			 
 	
class dincelpurchase_act_invoice(osv.Model):
	_inherit = "account.invoice"	
	
	def qty_variance(self, cr, uid, ids, values, arg, context):
		x={}
		for record in self.browse(cr, uid, ids):
			origin 		= record.origin
			ar_items_qty 	= {}
			_ostpk 			= self.pool.get('stock.picking')
			idstk		= _ostpk.search(cr, uid, [('name', '=', origin)], limit=1)
			if idstk:
				_ostpk  = _ostpk.browse(cr, uid, idstk[0], context=context)
				for line in _ostpk.move_lines:
					qty			= line.product_uom_qty
					product_id 	= line.product_id
					
					if ar_items_qty.has_key(product_id.id) == False:
						ar_items_qty[product_id.id] = qty
					else:
						ar_items_qty[product_id.id] += qty	
			#_logger.error("dincelpurchase_move_linesar_items_qty11:["+str(ar_items_qty)+"]")	
			price_diff=0
			for line in record.invoice_line:
				qty			= line.quantity
				product_id 	= line.product_id	
				if product_id.x_prod_cat!="freight":
					price_unit2 = line.price_unit
					price_unit	= line.product_id.standard_price
					price_diff  = price_diff + ((price_unit2-price_unit)*qty)
					if ar_items_qty.has_key(product_id.id):
						ar_items_qty[product_id.id] -= qty	
			_qty = 0
			for _item in ar_items_qty:
				_qty 	+= ar_items_qty[_item]
				#_oprod  = _oprod.browse(cr, uid, _item, context=context)
				#price_unit	= _oprod.standard_price
				#qty_variance = qty_variance + (price_unit*qty)			
			#_logger.error("dincelpurchase_move_linesar_items_qty22:["+str(ar_items_qty)+"]")	
			if _qty != 0 or price_diff != 0:
				active_id = "1"
			else:
				active_id = "0"
			x[record.id]=active_id 
		return x
		
	_columns = {
		'x_qty_variance': fields.function(qty_variance, method=True, string='Qty variance',type='char'),
	}	
	
	def write(self, cr, uid, ids, vals, context=None):
		if context is None:
			context = {}
		if not ids:
			return True
		#type','=','in_invoice'	
		res =  super(dincelpurchase_act_invoice, self).write(cr, uid, ids, vals, context=context)
		for record in self.browse(cr, uid, ids):
			if not record.state or record.state=="draft":
				if record.type == "in_invoice":
					#obj_inv = self.pool.get('account.invoice')
					#obj_inv = obj_inv.browse(cr, uid, ids[0], context)
					#obj_inv.button_compute(True) #For taxes
					#self.pool.get('account.invoice').button_reset_taxes(cr, uid, ids)#todo tchedk this
					
					#note................................................
					#only when draft...after validated...ignore...
					#note................................................
					reference=record.supplier_invoice_number
					partner_id=record.partner_id.id
					reference=str(reference).strip()
					msg = str(reference) + ' has already been used!' 
					sql="select id from account_invoice where type='in_invoice' and partner_id='%s' and supplier_invoice_number='%s'" % (partner_id, reference)
					if record.id:
						sql+=" and id<>'%s' " % (str(record.id))
					cr.execute(sql)
					rows = cr.fetchall()
					#_logger.error("dincelpurchase_act_invoicedincelpurchase_act_invoice:["+str(sql)+"]["+str(rows)+"]")
					if rows and len(rows)>0:
						#_obj 	= self.pool.get('account.invoice')
						#invoice_ids = _obj.search(cr, uid, [('type','=','in_invoice'),('partner_id','=',str(partner_id))], context)
						raise osv.except_osv('Possible duplicate Invoice!',msg)
					# Get all the references for all Supplier Invoices
					#invoices = _obj.read(cr, uid, invoice_ids, fields=['supplier_invoice_number'],context=context)

					# Check for duplicates
					#for inv in invoices:
					#	if str(inv['supplier_invoice_number']) == str(reference):
					#		raise osv.except_osv('Possible duplicate Invoice!',msg)
			
		return res	
		
	def onchange_supplier_invoice(self, cr, uid, ids, reference,partner_id, type, context=None):
		reference=str(reference).strip()
		msg = str(reference) + ' has already been used!' 
		res = {}

		if not reference:
			return res
		if type=="in_invoice":
			res = {'supplier_invoice_number': str(reference), }
			# Get all Supplier Invoices
			invoice_ids = self.search(cr, uid, [('type','=','in_invoice'),('partner_id','=',partner_id)], context)

			# Get all the references for all Supplier Invoices
			invoices = self.read(cr, uid, invoice_ids, fields=['supplier_invoice_number'],context=context)

			# Check for duplicates
			for inv in invoices:
				if str(inv['supplier_invoice_number']) == str(reference):
					raise osv.except_osv('Possible duplicate Invoice!',msg)

		return res

	def onchange_origin_invoice(self, cr, uid, ids, origin, context=None):
		if origin:
			_opicks = self.pool.get('stock.picking')
			_opo 	= self.pool.get('purchase.order')
			_omo 	= self.pool.get('stock.move')
			_oinvl 	= self.pool.get('account.invoice.line')
			_pid	= _opo.search(cr, uid, [('name','=',origin.strip())], limit=1) 	
			#_logger.error("onchange_origin_invoice__pid:["+str(_pid)+"]["+str(origin)+"]")
			
			ar_items_done = {}
			if _pid:
				_op = _opo.browse(cr, uid, _pid, context=context)
				for line in _op.order_line:
					qty 		= line.product_qty
					product_id 	= line.product_id.id
					#line_id 	= line.id
					
					m_ids		= _omo.search(cr, uid, [('purchase_line_id','=',line.id)]) 	
					#_logger.error("onchange_origin_invoice_qty_product_id:["+str(qty)+"]["+str(line.id)+"]m_ids1["+str(m_ids1)+"]")
					#m_ids		= _omo.search(cr, uid, [('origin','=',origin.strip())]) 	
					#_logger.error("onchange_origin_invoice_qty_product_id:["+str(qty)+"]["+str(line.id)+"]["+str(m_ids)+"]")
					for m_id in m_ids:
						_item	 = _omo.browse(cr, uid, m_id, context=context)
						_origin  = _item.origin
						_uom_qty = _item.product_uom_qty
						_state 	 = _item.state
						skey 	 = str(_item.product_id.id)
						if ar_items_done.has_key(skey) == False:
							ar_items_done[skey] = _uom_qty
						else:
							ar_items_done[skey] += _uom_qty
							
						_logger.error("onchange_origin_invoice_qty_origin:["+str(m_id)+"]["+str(_item.origin)+"]["+str(_item.product_uom_qty)+"]")	
						
					l_ids		= _oinvl.search(cr, uid, [('purchase_line_id','=',line.id)]) 	
					for l_id in l_ids:
						_item	 = _oinvl.browse(cr, uid, l_id, context=context)
						_qty 	 = _item.quantity
						skey 	 = str(_item.product_id.id)
						if ar_items_done.has_key(skey):
							ar_items_done[skey] -= _qty
				
				for line in _op.order_line:
					qty 		= line.product_qty
					product_id 	= line.product_id.id
					skey 	 	= str(product_id)
					if ar_items_done.has_key(skey):
						if ar_items_done[skey] > 0:
							vals={'product_id':product_id}
	
	def _invoice_validate_nonstock(self, cr, uid, ids, inv_id, context=None):
		_operiod 	= self.pool.get('account.period') 
		obj_inv = self.pool.get('account.invoice').browse(cr, uid, inv_id, context)
		acc_tr_cr=obj_inv.account_id.id
		total_invoice=0.0
		total_exgst=0.0
		total_tax=0.00
		if obj_inv.type=="in_refund":
			journal_ref 	= "ECNJ" 
			_number = self.pool.get('ir.sequence').get(cr, uid, 'purchase.refund')	
			_journal_id		= self.pool.get('account.journal').search(cr, uid, [('type', '=', 'purchase_refund')], limit=1)[0] 	
		else:
			journal_ref 	= "EXJ" 
			_number = self.pool.get('ir.sequence').get(cr, uid, 'purchase.invoice')	
			_journal_id		= self.pool.get('account.journal').search(cr, uid, [('type', '=', 'purchase')], limit=1)[0] 	
		#_logger.error("date_nonstock_invoice_validate_nonstock ["+str(obj_inv.date_invoice)+"] ["+str(obj_inv.supplier_invoice_number)+"]")
		#return
		
		
		invoice_name 	= journal_ref + "/" + str(inv_id)  + "/" + str(_number) + ""
		
		
		date_invoice	= obj_inv.date_invoice
		if obj_inv.supplier_invoice_number:
			origin			= obj_inv.supplier_invoice_number
		else:
			origin=_number
		partner_id		= obj_inv.partner_id.id
		company_id 		= obj_inv.company_id.id
		_objperiodcr	= _operiod.find(cr, uid, date_invoice, context=context)#[0]
		if _objperiodcr:
			period_id 	= _objperiodcr[0]# in above code

			
			
			state_move		= "posted"	#"draft" [NOTE, if posted then it will automatically reported in Tiral Balance, General Ledger, reports, etc]
			
			actmove = self.pool.get('dincelaccount.journal.dcs')
			actmove.ref_name 	= str(origin)+" - "+str(inv_id)
			actmove.state_move 	= state_move
			actmove.journal_id 	= _journal_id
			actmove.move_name 	= invoice_name
			actmove.date_move	= date_invoice
			actmove.period_id	= period_id
			actmove.partner_id	= partner_id
			actmove.company_id	= company_id
			
			gst_ac_id=None
			state_line		= "valid"
			
			_id	=	actmove.insert_move(cr, uid, ids, context=context)
			if _id:
				actmove.move_id 	= _id
				actmove.state_line 	= state_line
				actmove.journal_id 	= _journal_id
				actmove.move_line_name = invoice_name
				actmove.date_move	= date_invoice
				actmove.period_id	= period_id
				actmove.partner_id	= partner_id
				
				for line in obj_inv.invoice_line:
					#qty			= line.quantity
					#product_id 	= line.product_id
					price_subtotal  = line.price_subtotal
					#if line.x_coststate_id:
					if line.x_coststate_id:
						actmove.x_coststate_id	= line.x_coststate_id.id
					else:
						actmove.x_coststate_id	=None
					#_logger.error("invoice_sales_validategst_ac_idgst_ac_idgst_ac_id["+str(actmove.x_coststate_id)+"]")	
					total_exgst+=price_subtotal
					line_ac_id	= line.account_id.id
					
					if line_ac_id:
						account_id	= line_ac_id
						if obj_inv.type=="in_refund" or price_subtotal<0:
							debit		= 0
							credit 		= abs(price_subtotal)
						else:
							debit		= price_subtotal
							credit 		= 0
					
						actmove.account_id	=account_id
						actmove.debit	=debit
						actmove.credit	=credit
						actmove.insert_move_line(cr, uid, ids, context=context)
				#-------------------------------------------------------------
				total_tax=0.0	
				gst_ac_id=None
				myDict={}
				sql ="select * from account_invoice_tax where invoice_id='%s'" % (inv_id)
				cr.execute(sql)
				rows1 	= cr.dictfetchall()
				for row1 in rows1:
					gst_ac_id	= "A-"+str(row1['account_id'])
					
					tax_amount	= float(row1['tax_amount'])
					if myDict.has_key(gst_ac_id):# in arr_gst:
						vals=myDict[gst_ac_id]
						gstamt=vals['amt']
						gstamt=float(gstamt)+tax_amount
						vals['amt']=gstamt
					else:
						vals={'amt':tax_amount}
						#gstamt=tax_amount
						myDict[gst_ac_id]=vals
					total_tax+=tax_amount	
				
				#-----------------------------------------------------------------------------------------------	
				#_logger.error("invoice_sales_validategst_ac_idgst_ac_idgst_ac_id222["+str(myDict)+"]["+str(total_tax)+"]")
				for gstacid in myDict:
					gst_ac_id=gstacid.split("-")[1]
					#_logger.error("invoice_sales_validategst_ac_idgst_ac_idgst_ac_id3333["+str(gstacid)+"]["+str(gst_ac_id)+"]")
					vals=myDict[str(gstacid)]
					gstamt=vals['amt']
					#_logger.error("invoice_sales_validategst_ac_idgst_ac_idgst_ac_id3444333["+str(vals)+"]["+str(gstamt)+"]["+str(gst_ac_id)+"]")
					#if gst_ac_id and total_tax:
					if gstamt!=0.0:
						account_id	= int(gst_ac_id) #strange when passed string,gave error....??? no explanation...but
						#eg..read forum>> https://github.com/odoo/odoo/issues/10701
						if obj_inv.type=="in_refund" or gstamt<0:
							debit		= 0
							credit 		= abs(float(gstamt))
												
						else:
							debit		= float(gstamt)
							credit 		= 0
							
						actmove.x_coststate_id	=None
						actmove.account_id	=account_id
						actmove.debit	=debit
						actmove.credit	=credit
						actmove.insert_move_line(cr, uid, ids, context=context)
				#-----------------------------------------------------------------------------------------------
				
				total_invoice=total_exgst+total_tax
				
				account_id		= acc_tr_cr
				if obj_inv.type=="in_refund" or total_invoice<0:
					debit			= abs(total_invoice)
					credit 			= 0
				
				else:
					debit			= 0
					credit 			= total_invoice
					
			
				actmove.account_id	= account_id
				actmove.debit		= debit
				actmove.credit		= credit
				
				actmove.insert_move_line(cr, uid, ids, context=context)
			
				#so that it will ignore issues while calling .write() eg. duplicate supplier ref no warning...
				sql="update account_invoice set number='%s',state='open' where id='%s' " % (str(_number), str(inv_id))
				cr.execute(sql)
				#vals={'state':'open','number':_number}
				
				#self.write(cr, uid, inv_id, vals)	#account.invoice (update)		
		return {}
				
				
	def invoice_validate_purchase(self, cr, uid, ids, inv_id, context=None):				
		_operiod 	= self.pool.get('account.period') 
		_oprod 		= self.pool.get('product.product')
		_oglcodes 	= self.pool.get('dincelaccount.config.settings')
		_id			= _oglcodes.search(cr, uid, [], limit=1) 	
		if _id:
			_oglcodes 	= _oglcodes.browse(cr, uid, _id, context=context)
			#_oglcodes 	= self.pool.get('dincelaccount.config.settings').browse(cr, uid, 1, context=context)
		else:
			raise osv.except_osv(_('No account settings!'), _('No account settings found!'))
		
		_oacct			= self.pool.get('account.move')
		
		_opurline 		= self.pool.get('purchase.order.line')
		_opur 			= self.pool.get('purchase.order')
		_ostpk 			= self.pool.get('stock.picking')
		product_uom = self.pool.get('product.uom')
		acct_disc_rx 	= False
		acct_stock 		= False
		acct_good2inv 	= False
		acct_trade_cr	= False
		acct_pur_var	= False
		acct_tax		= False
		acct_qty_var	= False
		if _oglcodes:
			acct_stock 	= _oglcodes.stock_inventory.id or False #raw materials
			_tax 		= _oglcodes.buy_payable_tax
			if _tax:
				_taxobj = self.pool.get('account.tax').browse(cr, uid, _tax.id, context=context)
				acct_tax	= _taxobj.account_collected_id.id or False
			acct_good2inv 	= _oglcodes.stock_received_notinvoiced.id or False
			acct_disc_rx 	= _oglcodes.buy_cash_discount.id or False
			acct_trade_cr	= _oglcodes.buy_payable.id or False
			acct_qty_var	= _oglcodes.stock_purchase_variance.id or False
			acct_pur_var	= _oglcodes.stock_price_variance.id or False
			#acct_freight	= _oglcodes.sale_freight and _oglcodes.sale_freight.id  or False	
			
		#inv_id 		=None
		amt_stock 	=0
		origin 		=""
		price_diff	=0
		price_inv	=0
		price_disc	=0
		price_tax	=0
		price_grnyi =0 #Goods Reecived Not Yet Invoiced
		price_freight=0
		po=None
		x_region_id=None
		#-------------
		obj_inv = self.pool.get('account.invoice')
		obj_inv = obj_inv.browse(cr, uid, inv_id, context)
		
	
		#---------------------------------------------------------------------------------------------------
		#obj_inv.button_compute(True) #For taxes 
		#disabled above only for purchase invoices....cause they manually overwrite the invoice gst (cents) due to margin of raounding issue.
		origin 		= obj_inv.origin
		idstk		= _ostpk.search(cr, uid, [('name', '=', origin)], limit=1)
		if not idstk:#not from stock picking
			#todo...add category of non.stock billing type....in form
			self._invoice_validate_nonstock(cr, uid, ids, inv_id, context=context)
		else:
			_ostpk  = _ostpk.browse(cr, uid, idstk[0], context=context)
		 	
			for record in self.browse(cr, uid, ids, context=context):
				origin 		= record.origin
				inv_id  	= record.id
				partner_id	= record.partner_id.id
				company_id	= record.company_id.id
				price_inv 	= record.amount_untaxed
				price_tax	= record.amount_tax
				date_invoice= record.date_invoice #date_invoice	= datetime.datetime.today()
				
				#self.button_compute(True) #For taxes'
				
				#Note, windows version odoo8 and linux odoo8 stores origin in accountinvoice differently (21/01/2016)
				#strange behaviour though.....todo...check later....
				#po			= _opur.search(cr, uid, [('name', '=', origin)], limit=1)
				#if not po:
				#	idstk		= _ostpk.search(cr, uid, [('name', '=', origin)], limit=1)
				#	if idstk:
				#		_ostpk  = _ostpk.browse(cr, uid, idstk[0], context=context)
				#		po		= _opur.search(cr, uid, [('name', '=', _ostpk.origin)], limit=1)
				#	#else:
					
				#pick_state = record.state
				#if record.state not in ('done'):
				#	raise osv.except_osv(_('No delivery confirmed!'), _('No confirmed delivery found!'))
				#else:
				ar_items_qty 	= {}
				#ar_items_price 	= {}
				
				#if po:
					#check purchase qty variance
					#_opur = _opur.browse(cr, uid, po[0], context=context)
					
				for line in _ostpk.move_lines:
					qty			= line.product_uom_qty
					product_id 	= line.product_id
					
					if ar_items_qty.has_key(product_id.id) == False:
						ar_items_qty[product_id.id] = qty
					else:
						ar_items_qty[product_id.id] += qty	
				
				 
				
				for line in record.invoice_line:
					qty			= line.quantity
					product_id 	= line.product_id
					price_unit2 = line.price_unit
					price_unit	= line.product_id.standard_price
					uom_id		= line.product_id.uom_id.id
					uos_id		= line.uos_id.id
					#qty_price = product_uom._compute_qty(cr, uid, uos_id, line.quantity, uom_id)
					qty_base 	= product_uom._compute_qty(cr, uid, uos_id, 1, uom_id)
					#_logger.error("dincelpurchase_quantityquantityquantity:["+str(line.quantity)+"]["+str(qty)+"]["+str(qty_base)+"]["+str(uom_id)+"]["+str(uos_id)+"]")
					price_unit	= price_unit*qty_base				
					if product_id.x_prod_cat=="freight":
						price_freight=price_freight+line.price_subtotal
					else:
						#_logger.error_logger.error("dincelpurchase_move_lines_id:["+str(line.id)+"]["+str(qty)+"]")	
						#_itemid 	= _opurline.search(cr, uid, [('product_id', '=', product_id.id),('order_id', '=', po[0])], limit=1)#[0]
						#if _itemid:
						#	_item 	= _opurline.browse(cr, uid, _itemid[0], context=context)
						#	price_unit = _item.price_unit
						#else:
						#	price_unit = 0
						price_diff  = price_diff + ((price_unit2-price_unit)*qty)	
						#price_inv	= price_inv+line.price_subtotal	
						price_disc	= price_disc + (line.subtotal_wo_discount-line.price_subtotal)
						price_grnyi = price_grnyi + (qty*price_unit)
						
						if ar_items_qty.has_key(product_id.id):
							ar_items_qty[product_id.id] -= qty
					#price_inv = price_inv + (qty*price_unit2)
				#else:
				#	raise osv.except_osv(_('No PO mapping found'), _('No PO mapping found ref code [dincelpurchase_act_invoice]!'))
			#-----start of journal entry
			#_logger.error("dincelpurchase_move_linesar_items_qty22:["+str(ar_items_qty)+"]")	
			qty_variance = 0
			for _item in ar_items_qty:
				qty 	= ar_items_qty[_item]
				_op  	= _oprod.browse(cr, uid, _item, context=context)
				price_unit	= _op.standard_price
				qty_variance = qty_variance + (price_unit*qty)
				#if qty >0: #shortfall in invoice
					
				#else if qty <0: #additinal item received
					
				#_logger.error("dincelpurchase_move_linesar_items_qty33:["+str(ar_items_qty[ii])+"]["+str(ii)+"]")	
			if inv_id and price_inv>0:
				journal_ref 	= "EXJ" 
				invoice_name 	= journal_ref + "_" + str(inv_id)
				
				#date_invoice	= datetime.datetime.today()
		
				_objperiodcr	= _operiod.find(cr, uid, date_invoice, context=context)#[0]
				if _objperiodcr:
					period_id 	= _objperiodcr[0]# in above code
				else:
					period_id 	= None
				
				_journal_id		= self.pool.get('account.journal').search(cr, uid, [('type', '=', 'purchase')], limit=1)[0] 	
				
				state_move		= "posted"	#"draft" [NOTE, if posted then it will automatically reported in Tiral Balance, General Ledger, reports, etc]
				
				actmove = self.pool.get('dincelaccount.journal.dcs')
				actmove.ref_name 	= origin+"_"+str(inv_id)
				actmove.state_move 	= state_move
				actmove.journal_id 	= _journal_id
				actmove.move_name 	= invoice_name
				actmove.date_move	= date_invoice
				actmove.period_id	= period_id
				actmove.partner_id	= partner_id
				
				_id	=	actmove.insert_move(cr, uid, ids, context=context)
				if _id:
					#---------------------1---------------------
					state_line		= "valid"
					account_id		= acct_good2inv
					debit			= price_grnyi
					credit 			= 0
					
					actmove.move_id 	= _id
					actmove.state_line 	= state_line
					actmove.journal_id 	= _journal_id
					actmove.move_line_name = invoice_name
					actmove.date_move	= date_invoice
					actmove.period_id	= period_id
					actmove.partner_id	= partner_id
					actmove.account_id	= account_id
					actmove.debit		= debit
					actmove.credit		= credit
					
					actmove.insert_move_line(cr, uid, ids, context=context)
					
					#---------------------2---------------------
					#_logger.error("dincelpurchase_validate_invoice_id_price_tax:["+str(price_tax)+"]acct_tax["+str(acct_tax)+"]")	
					if price_tax>0:
						account_id	= acct_tax
						debit		= price_tax
						credit 		= 0
						#actmove.move_id 	= _id
						#actmove.state_line 	= state_line
						#actmove.journal_id 	=_journal_id
						#actmove.move_line_name = invoice_name
						#actmove.date_move	=date_invoice
						#actmove.period_id	=period_id
						#actmove.partner_id	=partner_id
						actmove.account_id	=account_id
						actmove.debit	=debit
						actmove.credit	=credit
						actmove.insert_move_line(cr, uid, ids, context=context)
					if price_disc > 0:
						account_id	= acct_disc_rx
						debit		= 0
						credit 		= price_disc
						actmove.account_id	=account_id
						actmove.debit	=debit
						actmove.credit	=credit
						actmove.insert_move_line(cr, uid, ids, context=context)
					if price_diff != 0:
						account_id	= acct_pur_var
						if price_diff > 0:
							debit		= price_diff
							credit 		= 0
						else:
							debit		= 0
							credit 		= abs(price_diff)
						actmove.account_id	=account_id
						actmove.debit	=debit
						actmove.credit	=credit
						actmove.insert_move_line(cr, uid, ids, context=context)	
					if qty_variance > 0:
						account_id	= acct_qty_var
						debit		= 0
						credit 		= qty_variance
						actmove.account_id	=account_id
						actmove.debit	=debit
						actmove.credit	=credit
						actmove.insert_move_line(cr, uid, ids, context=context)
						
						account_id		= acct_good2inv
						debit			= qty_variance
						credit 			= 0
						actmove.account_id	=account_id
						actmove.debit	=debit
						actmove.credit	=credit
						actmove.insert_move_line(cr, uid, ids, context=context)
					if qty_variance < 0:	
						account_id	= acct_qty_var
						debit		= abs(qty_variance)
						credit 		= 0
						actmove.account_id	=account_id
						actmove.debit	=debit
						actmove.credit	=credit
						actmove.insert_move_line(cr, uid, ids, context=context)
						
						account_id	= acct_trade_cr
						debit		= 0
						credit 		= abs(qty_variance)
						actmove.account_id	=account_id
						actmove.debit	=debit
						actmove.credit	=credit
						actmove.insert_move_line(cr, uid, ids, context=context)
						
					#----------	
					account_id	= acct_trade_cr
					debit		= 0
					credit 		= price_tax+price_inv
					actmove.account_id	=account_id
					actmove.debit	=debit
					actmove.credit	=credit
					actmove.insert_move_line(cr, uid, ids, context=context)
					if price_freight>0:
						account_id	= acct_stock
						debit		= price_freight
						credit 		= 0
						actmove.account_id	=account_id
						actmove.debit	=debit
						actmove.credit	=credit
						actmove.insert_move_line(cr, uid, ids, context=context)
					
					_number = self.pool.get('ir.sequence').get(cr, uid, 'purchase.invoice')	
					vals={'state':'open','number':_number}
					
					self.write(cr, uid, inv_id, vals)	#account.invoice (update)		
		return {}
	def validate_purchase_invoice_dcs(self, cr, uid, ids, context=None):
		inv_id		= ids[0]
		#return self.invoice_validate_purchase_xx(cr, uid, ids, inv_id, context)
		_obj 	= self.pool.get('account.invoice').browse(cr, uid, inv_id, context=context)
		tot_base = 0.0
		#for record in self.pool.get('account.invoice').browse(cr, uid, ids, context=context):
		for line in _obj.tax_line:
			tot_base += float(line.base)
		if(round(float(_obj.amount_untaxed),2) != round(float(tot_base),2)):
			raise osv.except_osv(_('Error'), _('The tax amount is not correct. Click on "Edit" then "Update" to recalculate the tax amount.'))
				
		return self.invoice_validate(cr, uid, ids, inv_id, context)
'''		ALREADY DONE dincelaccount >> module
class dincelpurchase_act_invoice_line(osv.Model):
	_inherit = "account.invoice.line"			
	_columns={
		'x_region_id': fields.many2one('dincelaccount.region', 'A/c Region'),
	}'''
class dincelpurchase_res_partner(osv.Model):
	_inherit = "res.partner"	
	def button_view_supplier_invoices(self, cr, uid, ids, context=None):
		if context is None:
			context = {}	
		for record in self.browse(cr, uid, ids, context=context):	
			partner_id=record.id 
			
			value = {
				'type': 'ir.actions.act_window',
				'name': _('Supplier Invoices'),
				'view_type': 'form',
				'view_mode': 'tree,form',
				'res_model': 'account.invoice',
				'domain':[('partner_id','=',partner_id)],
				'context':{'search_default_partner_id': partner_id},
				'view_id': False,
				
			}

			return value	