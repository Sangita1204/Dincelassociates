from openerp.osv import osv, fields
from datetime import date
from datetime import datetime
import datetime
from datetime import timedelta
import time 
#from datetime import datetime, timedelta
from pytz import timezone
import pytz
#from datetime import date
#from openerp.addons.base_status.base_state import base_state
#import time 
#import datetime
#from datetime import date
#from datetime import datetime
#import datetime
#from datetime import timedelta
import openerp.addons.decimal_precision as dp
#FOR PDF -------------------------
import base64
import subprocess
from subprocess import Popen, PIPE, STDOUT
#FOR PDF -------------------------

import logging
from openerp.tools.translate import _

from time import gmtime, strftime
_logger = logging.getLogger(__name__)

class dincelsale_ordersale(osv.Model):
	_name = "dincelsale.ordersale"
	_inherit = ['mail.thread']
	_description="Return of sale order"
	_order 	= "date_order desc"
	def _get_default_company(self, cr, uid, context=None):
		company_id = self.pool.get('res.users')._get_company(cr, uid, context=context)
		if not company_id:
			raise osv.except_osv(_('Error!'), _('There is no default company for the current user!'))
		return company_id
	def get_salenote(self, cr, uid, ids, partner_id, context=None):
		context_lang = context.copy() 
		if partner_id:
			partner_lang = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context).lang
			context_lang.update({'lang': partner_lang})
		return self.pool.get('res.users').browse(cr, uid, uid, context=context_lang).company_id.sale_note
		
	def onchange_origin_id(self, cr, uid, ids, origin_id,partner_id, project_id, context=None):
		if origin_id:
			new_lines=[]
			obj = self.pool.get('sale.order')
			order1 = obj.browse(cr, uid, origin_id, context=context)
			for line in order1.order_line:
				if line.product_id.x_prod_cat not in['freight','deposit']:#='freight':	
					order_length=line.x_order_length
					
					#if line.product_id.x_prod_cat not in['stocklength','customlength']:
					#	order_length = False
					
					vals = {
						'order_qty':line.x_order_qty,
						'product_id': line.product_id.id or False,
						'order_length':line.x_order_length or 0.0,
						'name':line.product_id.name,
						'product_uom_id':line.product_id.uom_id.id,
						'order_line_id':line.id,
						'price_unit':line.price_unit,
						'qty_price':0.0,
						}
					if line.tax_id:
						vals['taxes_id'] = [(6, 0, line.tax_id.ids)]	
					new_lines.append(vals)
			vals1= {'order_line': new_lines}	
			if order1.origin:
				vals1['order_code']=order1.origin
				
			if not partner_id or not project_id: 	
				vals1['partner_id']  = order1.partner_id.id
				vals1['project_id']  = order1.x_project_id.id
			
			return {'value': vals1}		
	def onchange_partner_id(self, cr, uid, ids,partner_id, project_id, is_contact , context=None):
		#if not partner_id:
		#	return {'value': { 'payment_term': False}}
		val = {}
		domain1={}
		order = self.pool.get('sale.order')
		if project_id:
			val['site_address']=self.pool.get('res.partner').browse(cr, uid, project_id, context=context).name
			
		if partner_id:
			part = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context)
			payment_term = part.property_payment_term and part.property_payment_term.id or False
			dedicated_salesman = part.user_id and part.user_id.id or uid
			val['payment_term']=payment_term
			val['user_id']=dedicated_salesman
			c_ids1 = order.search(cr, uid, [('partner_id', '=', partner_id)], context=context)
			domain1  = {'origin_id': [('id','in', (c_ids1))]}
			
			if is_contact == True:
				proj_list = []
			
				for item in part.x_role_site_ids:
					proj_list.append(item.id) 
					
				domain1['project_id']  = [('id','in', (proj_list))]
		else:		
			if project_id:
				c_ids1 = order.search(cr, uid, [('x_project_id', '=', project_id)], context=context)
				domain1  = {'origin_id': [('id','in', (c_ids1))]}
		
		return {'domain': domain1, 'value': val}	#return {'value': val,'domain': domain1}
		
	_columns = {
		'name': fields.char('Order Reference'),
		'origin': fields.char('Source Document', help="Reference of the document that generated this sales order request."),
		'state': fields.selection([
			('draft', 'Draft'),
			('cancel', 'Cancelled'),
			('progress', 'Pending'),
			('printed', 'Printed'),
			('done', 'Done'),
			], 'Status'),
		'date_order': fields.datetime('Date', required=True,states={'printed': [('readonly', True)], 'done': [('readonly', True)]}),
		'user_id': fields.many2one('res.users', 'Salesperson'),
		'origin_id': fields.many2one('sale.order', 'Origin Order',states={'printed': [('readonly', True)], 'done': [('readonly', True)]}),
		'order_code': fields.related('origin_id', 'origin', type='char', string='DCS Code',store=False),
		'color_code': fields.related('origin_id', 'x_colorcode', type='char', string='Color',store=False),
		'partner_id': fields.many2one('res.partner', 'Customer', domain=[('customer', '=', True),('x_is_project', '=', False)],states={'printed': [('readonly', True)], 'done': [('readonly', True)]}),
		'project_id': fields.many2one('res.partner', 'Project', domain=[('x_is_project', '=', True)],states={'printed': [('readonly', True)], 'done': [('readonly', True)]}),
		'order_line': fields.one2many('dincelsale.order.line', 'order_id', 'Order Lines'),
		'note': fields.text('Note'),
		'site_address': fields.char('Site Address'),
		'payment_term': fields.many2one('account.payment.term', 'Payment Term'),
		'company_id': fields.many2one('res.company', 'Company'),
		'picking_id': fields.many2one('stock.picking', 'Picking'),
		'picking_type_id': fields.many2one('stock.picking.type', 'Deliver To', help="This will determine picking type of incoming shipment", required=True,
			states={'printed': [('readonly', True)], 'done': [('readonly', True)]}),
		'related_location_id': fields.related('picking_type_id', 'default_location_dest_id', type='many2one', relation='stock.location', string="Related location", store=True),
		'location_id':fields.many2one('stock.location', 'Destination', required=True,states={'printed': [('readonly', True)], 'done': [('readonly', True)]}),
	}	
	
	_defaults = {
		'date_order': fields.datetime.now,
		'company_id': _get_default_company,
		'state': 'draft',
		'user_id': lambda obj, cr, uid, context: uid,
		'name': lambda obj, cr, uid, context: '/',
		'note': lambda self, cr, uid, context: self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.sale_note,
	}
	_sql_constraints = [
		('name_uniq', 'unique(name, company_id)', 'Order Reference must be unique per Company!'),
		]
	
	def create(self, cr, uid, vals, context=None):
		if context is None:
			context = {}
		if vals.get('name', '/') == '/':
			vals['name'] = self.pool.get('ir.sequence').get(cr, uid, 'dincelsale.order') or '/'

		new_id = super(dincelsale_ordersale, self).create(cr, uid, vals, context=context)
		
		return new_id
	#(date_order,partner_id,payment_term,context)
	'''def create_test(self, cr, uid, ids, context=None):
		str1 = ""
		for record in self.browse(cr, uid, ids, context=context):
			for line in record.order_line:
				id1 = line.product_id.id
				str1 += "product_id [" + str(id1) + "]"
				if line.product_id.x_is_main == '1':
					qty 	= line.order_qty
					str1 += "x_is_main [" + str(qty) + "]"
				else:
					price	= line.product_id.list_price
					qty 	= line.order_qty
					str1 += "[" + str(qty) + "][" + str(price) + "]"
		_logger.error("invoice_sales_validate:["+str1+"]")	
	'''	
	def _prepare_order_line_move(self, cr, uid, order, _line, picking_id, group_id, context=None):
		''' prepare the stock move data from the PO line. This function returns a list of dictionary ready to be used in stock.move's create()'''
		product_uom = self.pool.get('product.uom')
		#price_unit = order_line.price_unit
		#if order_line.product_uom.id != order_line.product_id.uom_id.id:
		#    price_unit *= order_line.product_uom.factor / order_line.product_id.uom_id.factor
		#if order.currency_id.id != order.company_id.currency_id.id:
		#    #we don't round the price_unit, as we may want to store the standard price with more digits than allowed by the currency
		#    price_unit = self.pool.get('res.currency').compute(cr, uid, order.currency_id.id, order.company_id.currency_id.id, price_unit, round=False, context=context)
		res = []
		
		_origin="RET/%s" % (order.origin_id.name)
		if order.origin_id.origin:
			_origin+="/%s"% (order.origin_id.origin)
		
		_qty_lm		=0
		_qty		=_line.qty_return
		_length		=_line.order_length
		
		if _line.product_id.x_prod_type and _line.product_id.x_prod_type=="acs":#in ['customlength','stocklength']:
			_qty_lm=_qty #all accessories....
			
		else:
			_qty_lm=_qty*_length*0.001
		#if _line.product_id.x_prod_cat in ['customlength','stocklength']:
		#	_qty_lm=_qty*_length*0.001
		#else:
		#	_qty_lm=_qty
			
		move_template = {
			'name': _line.name or '', #equivalent ... product name...
			'product_id': _line.product_id.id,
			'product_uom': _line.product_uom_id.id,
			'product_uos': _line.product_uom_id.id,
			'date': order.date_order,
			'date_expected':  order.date_order,#fields.date.date_to_datetime(self, cr, uid, order_line.date_planned, context),
			'location_id': order.partner_id.property_stock_customer.id,
			'location_dest_id': order.location_id.id,
			'picking_id': picking_id,
			'partner_id': order.partner_id.id,
			'move_dest_id': False,
			'state': 'draft',
			#'purchase_line_id': order_line.id,
			'company_id': order.company_id.id,
			#'price_unit': price_unit,
			'picking_type_id': order.picking_type_id.id,
			'group_id': group_id,
			'procurement_id': False,
			'origin': _origin,
			'route_ids': order.picking_type_id.warehouse_id and [(6, 0, [x.id for x in order.picking_type_id.warehouse_id.route_ids])] or [],
			'warehouse_id':order.picking_type_id.warehouse_id.id,
			#'invoice_state': order.invoice_method == 'picking' and '2binvoiced' or 'none',
			'product_uom_qty': _qty_lm,#min(procurement_qty, diff_quantity),
			'product_uos_qty': _qty_lm,#min(procurement_qty, diff_quantity),
			'x_quantity':_qty,
			'x_order_length':_length,
			#'move_dest_id': procurement.move_dest_id.id,  #move destination is same as procurement destination
			#'group_id': procurement.group_id.id or group_id,  #move group is same as group of procurements if it exists, otherwise take another group
			#'procurement_id': procurement.id,
			#'invoice_state': procurement.rule_id.invoice_state or (procurement.location_id and procurement.location_id.usage == 'customer' and procurement.invoice_state=='2binvoiced' and '2binvoiced') or (order.invoice_method == 'picking' and '2binvoiced') or 'none', #dropship case takes from sale
			#'propagate': procurement.rule_id.propagate,
			}

		
		res.append(move_template)
		
		return res
		
	def button_print_pdf(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
	
		#ir_id = False 
		#fname = False
		#ir_attachement_obj=self.pool.get('ir.attachment')
		
		for record in self.browse(cr, uid, ids):
			#if not record.dcs_refcode or record.dcs_refcode=="":
			#	raise osv.except_osv(_('Error'), _('Docket number missing, please update DCS first to generate pdf.'))
				
			fname="returns_"+str(record.id)+".pdf"
			save_path="/var/tmp/odoo/docket/"
			temp_path=save_path+fname
			'''if record.pdf_attachs:
				#ir_id=record.pdf_attachs.id
				try:
					ir_attachement_obj.unlink(cr, uid, [record.pdf_attachs.id])
				except ValueError:
					ir_id = False #......
		 
				
			'''
			url=self.pool.get('dincelaccount.config.settings').report_preview_url(cr, uid, ids,"docketr",record.id,context=context)	
			
			
			#process = subprocess.Popen(wkhtmltopdf, stdout=subprocess.PIPE, stderr=subprocess.PIPE)	
			process=subprocess.Popen(["wkhtmltopdf",
										"--orientation",'landscape',
										'--margin-top','0', 
										'--margin-left','0', 
										'--margin-right','0', 
										'--margin-bottom','0', 
										url, temp_path], stdin=PIPE, stdout=PIPE)
			out, err = process.communicate()
			if process.returncode not in [0, 1]:
				raise osv.except_osv(_('Report (PDF)'),
									_('Wkhtmltopdf failed (error code: %s). '
									'Message: %s') % (str(process.returncode), err))
			
			f=open(temp_path,'r')
			
			_data = f.read()
			_data = base64.b64encode(_data)
			f.close()
			
			'''
			document_vals = {
				'name': fname,   #                     -> filename.csv
				'datas': _data,    #                                              -> path to my file (under Windows)
				'datas_fname': fname, #           -> filename.csv 
				'res_model': self._name, #                                  -> My object_model
				'res_id': record.id,  #                                   -> the id linked to the attachment.
				'type': 'binary' 
				}
			
			ir_id = ir_attachement_obj.create(cr, uid, document_vals, context) 
			
			try:
				_obj = self.pool.get('dincelstock.pickinglist')  
				_obj.write(cr, uid, record.id, {'pdf_attachs': ir_id})  
				
			except ValueError:
				ir_id = False #.......
		if ir_id and fname:'''
			return {
					'type' : 'ir.actions.act_url',
					'url': '/web/binary/download_file?model=dincelsale.ordersale&field=datas&id=%s&path=%s&filename=%s' % (str(record.id),save_path,fname),
					'target': 'self',
				}
		
	def button_mark_printed(self, cr, uid, ids, context=None):
		#if context is None:
		#	context = {}
		return self.write(cr, uid, ids[0], {'state':'printed'})	
		#return False
	def button_create_crn(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		obj_inv 	= self.pool.get('account.invoice')	
		obj_invline	= self.pool.get('account.invoice.line')
		product_obj = self.pool.get('product.product')	
		
		to_return=0
		for record in self.browse(cr, uid, ids, context=context):		
			for line in record.order_line:
				to_return += line.qty_return
		if to_return<=0:
			str1="Invalid quantity return found."
			raise osv.except_osv(_('Error'), _(''+str1))
		tot_price 	= 0	
		_obj = self.pool.get('account.journal')
		obj_ids = _obj.search(cr, uid, [('type', '=', "sale_refund")])
		if obj_ids:
			journal_id=obj_ids[0]
			
			for record in self.browse(cr, uid, ids, context=context):		
				vals = {
						'x_sale_order_id': record.origin_id.id,
						'x_inv_type':'refundreturn',
						'origin': record.name,
						'reference': record.name,
						'partner_id': record.partner_id.id,
						'user_id':record.origin_id.user_id.id,
						'journal_id':journal_id,
						#'internal_number': record.name, #cannot delete once this value is recorded
						'section_id': 1,
						'type': 'out_refund',
						'account_id':record.partner_id.property_account_receivable.id
						}
				
				vals['date_invoice']=record.date_order	#datetime.datetime.now() 
				vals['date_due']=vals['date_invoice']
							
				vals['x_project_id']=record.project_id.id 
				 
					
				#first create the invoice record
				inv_id = obj_inv.create(cr, uid, vals, context=context)
				
				for line in record.order_line:
					qty = line.qty_return
					product_id = line.product_id.id
					 	
					if qty > 0:
						_length = line.order_length 
						'''prodcat=line.product_id.x_prod_cat
						if prodcat in ['customlength','stocklength']:
							_factor=line.product_id.x_m2_factor
							
							if _factor and _factor>0:
								qty_m2 = round((_length*qty*0.001*_factor),4) 	#M2 
							else:	
								qty_m2 = round(((_length*qty*0.001)/3),4) 
							#qty=qty_m2
						else:
							qty_m2=qty
						'''	
						qty_m2=line.qty_price*(-1.0)
						vals = {
							'product_id': product_id,
							'quantity': qty_m2,
							'invoice_id': inv_id,
							'origin': record.name,
							'discount':0,
							'price_unit': line.price_unit,
							'price_subtotal': line.price_unit*qty_m2,
							'x_order_length':_length,
							'x_order_qty':qty,
						}
						vals['name']= line.product_id.name
						
						#if line.x_region_id:
						#	vals['x_region_id']= line.x_region_id.id	
						#if line.x_coststate_id:
						#	vals['x_coststate_id']= line.x_coststate_id.id	
							
						
						#>>> todo...somethiems taxes not being recorded in invoice...14/7/2016 >> 1/3/2017....no isue
						#instead of product settings ...pick from line items....eg nz do not have tax
						#if line.product_id.taxes_id:
						#	vals['invoice_line_tax_id'] = [(6, 0, line.product_id.taxes_id.ids)]
						if line.taxes_id:
							vals['invoice_line_tax_id'] = [(6, 0, line.taxes_id.ids)]
						obj_invline.create(cr, uid, vals, context=context)
				
				
				obj_inv = self.pool.get('account.invoice')
				obj_inv = obj_inv.browse(cr, uid, inv_id, context)
				obj_inv.button_compute(True) #For taxes
				
				#--------------
				#if record.x_ac_status==None or record.x_ac_status=="hold":
				#	self.write(cr, uid, [record.id], {'x_ac_status':'open'})	
				#--------------
				
				#str1 = "amttax["+str(obj_inv.amount_tax) + "]amtuntax["+str(obj_inv.amount_untax) + "] calculated["+str(obj_inv.amount_untax*0.1) + "]" 
				
				view_id 		= self.pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'dincelaccount.invoice.form')], limit=1) 	
				#_logger.error("invoice_sales_validate.view_id["+str(view_id)+"]")
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
	
	def _create_stock_journal(self, cr, uid, _retobj, _jid, _line, context=None):
		_qty		=_line.qty_return
		_length		=_line.order_length
		_obj = self.pool.get('dincelstock.journal').browse(cr, uid, _jid, context=context)
		_objline = self.pool.get('dincelstock.journal.line')
		vals={'journal_id':_jid,
				'product_id':_line.product_id.id,
				'date':_retobj.date_order,
				'period_id':_obj.period_id.id,
				'prod_length':_length,
				'location_id':_retobj.location_id.id,
				'reference':_('RET:') + (_retobj.name or ''),
				}
		if _line.product_id.x_prod_type and _line.product_id.x_prod_type=="acs":
			vals['is_acs'] 	= True	
		else:
			vals['is_acs'] 	= False
			
		vals['qty_in'] 	= _qty	
		vals['qty_out'] = 0
			
		return _objline.create(cr, uid, vals, context=context)
		
	def button_validate_return(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		_id=ids[0]
		order = self.browse(cr, uid, ids[0], context=context)
		_totqty=0
		for _line in order.order_line:
			if not _line.product_id:
				continue
			if _line.product_id.x_prod_cat not in['freight','deposit'] and _line.product_id.type !="service":
				_totqty+=int(_line.qty_return)
		if _totqty<1:
			raise osv.except_osv(_('Error'),_('Invalid return qty or zero qty found!!') )
		stock_move = self.pool.get('stock.move')
		todo_moves = []
		new_group = self.pool.get("procurement.group").create(cr, uid, {'name': order.origin_id.name, 'partner_id': order.partner_id.id}, context=context)
		picking_vals = {
			'picking_type_id': order.picking_type_id.id,
			'partner_id': order.partner_id.id,
			'date': order.date_order,#max([l.date_planned for l in order.order_line]),
			'origin': order.origin_id.name
		}
		picking_id = self.pool.get('stock.picking').create(cr, uid, picking_vals, context=context)
		
		_jid = self.pool.get('dincelstock.journal').order_return_confirm(cr, uid, order.id, context)
		for _line in order.order_line:
			if not _line.product_id:
				continue
			if _line.product_id.x_prod_cat not in['freight','deposit'] and _line.product_id.type !="service":
				#if _line.product_id.type in ('product', 'consu'):
				if _line.qty_return>0:
					for vals in self._prepare_order_line_move(cr, uid, order, _line, picking_id, new_group, context=context):
						move = stock_move.create(cr, uid, vals, context=context)
						#_logger.error("stock_movestock_move:moveid["+str(move)+"]["+str(vals)+"]")	
						todo_moves.append(move)
					_id2= self._create_stock_journal(cr, uid, order, _jid, _line, context)
					
		todo_moves = stock_move.action_confirm(cr, uid, todo_moves)
		stock_move.force_assign(cr, uid, todo_moves)
		done_moves = stock_move.action_done(cr, uid, todo_moves)
		stock_move.quants_assign_dcs(cr, uid, todo_moves) #assign the quants qty..
		#  def action_done(self, cr, uid, ids, context=None):
		self.pool.get('dincelsale.ordersale').write(cr, uid, _id, {'state': 'done','picking_id':picking_id})
		 
		 

					
class dincelsale_ordersale_line(osv.Model):
	_name 	= "dincelsale.order.line"
	_order 	= "sequence"
	
	def product_id_change(self, cr, uid, ids, product,  partner_id=False, context=None):
		context = context or {}
		'''if not partner_id:
			raise osv.except_osv(_('No Customer Defined!'), _('Before choosing a product,\n select a customer in the sales form.'))
			#return {}
		warning = False
		domain = {}
		product_obj = self.pool.get('product.product')
		result = {}
		product_obj = product_obj.browse(cr, uid, product, context=context)
		if not product_obj.description_sale:
			sname=product_obj.name
		else:
			sname=product_obj.description_sale
		result.update({'name': sname})
		result.update({'order_length': product_obj.x_stock_length})
		return {'value': result, 'domain': domain}
		#product_obj = product_obj.browse(cr, uid, product, context=context)
		#result['name'] = product_obj.description_sale
		#result['order_length'] = product_obj.x_stock_length
        '''
		return {}
		
	def product_qty_changed(self, cr, uid, ids, product, qty=0,length=0, context=None):
		
		result 		= {}	
		context 	= context or {}
		product_obj = self.pool.get('product.product')
		_obj  = product_obj.browse(cr, uid, product, context)
		if _obj.x_is_main=='1':#x_is_calcrate:
			if _obj.x_m2_factor and _obj.x_m2_factor>0:
				qty_m2 = round((length*qty*0.001*_obj.x_m2_factor),4) 	#M2 
			else:	
				qty_m2 = round(((length*qty*0.001)/3),4) 	#M2 
			 
			
		else:
			
			qty_m2 = qty	
		
					
		#if _obj.x_prod_cat in ['customlength','stocklength']:
		#	qty_m2 = round(((length*qty*0.001)/3),4) 	#M2 
		#else:
			
		#	qty_m2 = qty	
			 
		result.update({'qty_price': qty_m2})
		
		return {'value': result}
		
	def _sub_total(self, cr, uid, ids, values, arg, context):
		x={}
		_ret=0.0
		for record in self.browse(cr, uid, ids):
			
			_qty=float(record.qty_price)
			_amt=float(record.price_unit)
			_ret=_qty*_amt
		
			x[record.id] = _ret 
		return x	
		
	_columns = {
		'order_id': fields.many2one('dincelsale.ordersale', 'Order Reference', required=True, ondelete='cascade', select=True),
		'name': fields.text('Description', required=True),
		'sequence': fields.integer('Sequence'),
		'product_id': fields.many2one('product.product', 'Product', ondelete='restrict'),
		'order_length':fields.float("Length",digits_compute= dp.get_precision('Int Number')),	
		'order_qty':fields.float("Qty Ordered",digits_compute= dp.get_precision('Int Number')),	
		'qty_return':fields.float("Qty Return",digits_compute= dp.get_precision('Int Number')),
		'product_uom_id': fields.many2one('product.uom', 'Unit', required=True),	
		'order_line_id': fields.many2one('sale.order.line', 'Order Line'),
		'taxes_id': fields.many2many('account.tax','dincelsale_order_line_tax', 'order_line_id', 'tax_id', string='Taxes'),
		'price_unit': fields.float("Rate"),#fields.related('order_line_id', 'price_unit', type='float', string='Unit Price', store=False),#'price_unit':
		'qty_price':fields.float("M2/each"),
		'sub_total': fields.function(_sub_total, method=True, string='Subtotal', type='float'),
	}	#'x_role_site_ids' : fields.many2many('res.partner', 'rel_partner_roles', '_partner_roles_id', 'object_partner_id', string = "Sites"),

class dincelsale_saleorder(osv.Model):
	_inherit = "sale.order"
	
	_columns = {
		'x_return_ids':fields.one2many('dincelsale.ordersale', 'origin_id', 'Returns', ondelete='cascade',),
		}
		
		
		
class dincelsale_productsummary(osv.Model):	
	_name = "dincelsale.productsummary"
	
	def _get_completed_lm(self, cr, uid, ids, _prod, context=None):
		sql2="select sum(m.x_produced_qty*m.x_order_length*0.001) as tot from sale_order o,mrp_production m,product_product p,product_template t"
		sql2+=" where o.id=m.x_sale_order_id and m.product_id=p.id and p.product_tmpl_id=t.id and t.x_prod_cat='customlength'"
		sql2+=" and (o.x_dep_paid='NA' or o.x_dep_paid='paid')"
		sql2+=" and o.state not in ('cancel','done') and o.x_pending='f'"
		sql2+=" and t.x_dcs_group='%s'" % (_prod)
		cr.execute(sql2)
	
		rows 	= cr.fetchone()
		if rows and len(rows) > 0 and rows[0]:
			return rows[0]
		return 0
		
	def _get_remain_lm(self, cr, uid, ids, _prod, context=None):
		_ret='' 
		#sql="select id from sale_order where state not in ('cancel','done') and x_pending='f'"
		#sql+=" and (x_dep_paid='NA' or x_dep_paid='paid')"
		sql2="select sum(l.x_order_qty*l.x_order_length*0.001) as tot	from sale_order o,sale_order_line l,product_product p,product_template t"
		sql2+=" where o.id=l.order_id and l.product_id=p.id and p.product_tmpl_id=t.id and t.x_prod_cat='customlength'"
		sql2+=" and (o.x_dep_paid='NA' or o.x_dep_paid='paid')"
		sql2+=" and o.state not in ('cancel','done') and o.x_pending='f'"
		sql2+=" and t.x_dcs_group='%s'" % (_prod)
		cr.execute(sql2)
	
		rows 	= cr.fetchone()
		if rows and len(rows) > 0 and rows[0]:
			_ret = rows[0]
			_completed=self._get_completed_lm(cr, uid, ids, _prod, context=context)
			if _completed:
				_ret=float(_ret)-float(_completed)
		else:	
			_ret = '0'
		return _ret
	
	def _get_hold_lm(self, cr, uid, ids, _prod, context=None):
		_ret='' 
		#sql="select id from sale_order where state not in ('cancel','done') and x_pending='f'"
		#sql+=" and (x_dep_paid='NA' or x_dep_paid='paid')"
		sql2="select sum(l.x_order_qty*l.x_order_length*0.001) as tot	from sale_order o,sale_order_line l,product_product p,product_template t"
		sql2+=" where o.id=l.order_id and l.product_id=p.id and p.product_tmpl_id=t.id and t.x_prod_cat='customlength'"
		sql2+=" and (o.x_dep_paid='' or o.x_dep_paid is null)"
		sql2+=" and o.state not in ('cancel','done') and o.x_pending='f'"
		sql2+=" and t.x_dcs_group='%s'" % (_prod)
		cr.execute(sql2)
	
		rows 	= cr.fetchone()
		if rows and len(rows) > 0 and rows[0]:
			_ret = rows[0]
			#_completed=self._get_completed_lm(cr, uid, ids, _prod, context=context)
			#if _completed:
			#	_ret=float(_ret)-float(_completed)
		else:	
			_ret = '0'
		return _ret
		
	def _remain_lm(self, cr, uid, ids, values, arg, context):
		x={}
		_ret=''
		for record in self.browse(cr, uid, ids):
			if record.code=="P155" or record.code=="P110" or record.code=="P200" or record.code=="P275":
				_ret=self._get_remain_lm(cr, uid, ids, record.code, context=context)
				_ret=round(_ret,2)
				#_ret="{:,}".format(_ret)
				'''elif record.code=="P110":
					_ret=self._get_remain_lm(cr, uid, ids, record.code, context=context)
					_ret=round(_ret,2)
				elif record.code=="P200":
					_ret=self._get_remain_lm(cr, uid, ids, record.code, context=context)
					_ret=round(_ret,2)
				elif record.code=="P275":
					_ret=self._get_remain_lm(cr, uid, ids, record.code, context=context)
					_ret=round(_ret,2)'''
			else:
				_ret=''
			x[record.id]=_ret 	
		return x
	
	def _hold_hrs(self, cr, uid, ids, values, arg, context):
		x={}
		_ret=''
		for record in self.browse(cr, uid, ids):
			if not record.produce_speed or record.produce_speed==0:
				_speed=1.0
			else:
				_speed=record.produce_speed
			if record.code=="P155" or record.code=="P110" or record.code=="P200" or record.code=="P275":
				_ret=self._get_hold_lm(cr, uid, ids, record.code, context=context)
				_ret=float(_ret)/(_speed*60) 
				_ret=round(_ret,2)
				#_ret="{:,}".format(_ret)
				
			else:
				_ret=''
			x[record.id]=_ret 	
		return x
		
	def _remain_hrs(self, cr, uid, ids, values, arg, context):
		x={}
		_ret=''
		for record in self.browse(cr, uid, ids):
			if not record.produce_speed or record.produce_speed==0:
				_speed=1.0
			else:
				_speed=record.produce_speed
			if record.code=="P155" or record.code=="P110" or record.code=="P200" or record.code=="P275":
				_ret=self._get_remain_lm(cr, uid, ids, record.code, context=context)
				_ret=float(_ret)/(_speed*60) 
				_ret=round(_ret,2)
				#_ret="{:,}".format(_ret)
				'''elif record.code=="P110":
					_ret=self._get_remain_lm(cr, uid, ids, record.code, context=context)
					_ret=float(_ret)/(_speed*60) 
					_ret=round(_ret,2)
					_ret="{:,}".format(_ret)
				elif record.code=="P200":
					_ret=self._get_remain_lm(cr, uid, ids, record.code, context=context)
					_ret=float(_ret)/(_speed*60) 
					_ret=round(_ret,2)
					_ret="{:,}".format(_ret)
				elif record.code=="P275":
					_ret=self._get_remain_lm(cr, uid, ids, record.code, context=context)
					_ret=float(_ret)/(_speed*60) 
					_ret=round(_ret,2)
					_ret="{:,}".format(_ret)'''
			else:
				_ret=''
			x[record.id]=_ret 	
		return x
		
	def _hold_lm(self, cr, uid, ids, values, arg, context):
		x={}
		_ret=''
		for record in self.browse(cr, uid, ids):
			if record.code=="P155" or  record.code=="P110" or  record.code=="P200" or  record.code=="P275":
				_ret=self._get_hold_lm(cr, uid, ids, record.code, context=context)
				_ret=round(float(_ret),2)
				#_ret="{:,}".format(_ret)
				'''elif record.code=="P110":
					_ret=self._get_hold_lm(cr, uid, ids, record.code, context=context)
					_ret=round(float(_ret),2)
					_ret="{:,}".format(_ret)
				elif record.code=="P200":
					_ret=self._get_hold_lm(cr, uid, ids, record.code, context=context)
					_ret=round(float(_ret),2)
					_ret="{:,}".format(_ret)
				elif record.code=="P275":
					_ret=self._get_hold_lm(cr, uid, ids, record.code, context=context)
					_ret=round(float(_ret),2)
					_ret="{:,}".format(_ret)'''
			else:
				_ret=''
			x[record.id]=_ret 	
		return x	
		
	def _truck_count1(self, cr, uid, ids, values, arg, context):
		x={}
		_ret=''
		for record in self.browse(cr, uid, ids):
			if record.type=="delivery":
				dtfrom=datetime.datetime.now()
				dtfrom2=dtfrom+ timedelta(hours=10) #for gmt to au date (+10) hrs
				_from_date 	=  datetime.datetime.strptime(str(dtfrom2),"%Y-%m-%d %H:%M:%S.%f")
				#todo....get gmt to local time with timezone logic
				
				#_logger.error("_truck_count1_truck_count1:dtfrom2[" + str(_from_date)+ "][" + str(dtfrom)+ "]")
				#currtime=time.localtime()
				#_from_date 	=  datetime.datetime.strptime(str(dtfrom2),"%Y-%m-%d %H:%M:%S.%f")
				#time_zone	='Australia/Sydney'
				#tz 			= pytz.timezone(time_zone)
				#tzoffset 	= tz.utcoffset(_from_date)
				_dt_today 	= str((_from_date).strftime("%Y-%m-%d"))
				#_logger.error("_truck_count1_truck_count1:2day %s , wtime %s, currtime %s [%s]" % (_dt_today,_from_date,dtfrom,currtime))
				sql="select sum(dockets) from dincelwarehouse_sale_order_delivery where date_actual='%s'" % (_dt_today)
				cr.execute(sql)
				#_logger.error("_truck_count1_truck_count1_truck_count1:sqlsql[" + str(sql)+ "]")
				rows 	= cr.fetchone()
				if rows and len(rows) > 0 and rows[0]:
					_ret = rows[0]
				else:	
					_ret = '0'
			else:
				_ret=''
				#dtquote 	= str((_from_date + tzoffset).strftime("%Y-%m-%d"))
			x[record.id]=_ret 	
		return x
		
	def _truck_count2(self, cr, uid, ids, values, arg, context):
		x={}
		_ret=''
		for record in self.browse(cr, uid, ids):
			if record.type=="delivery":
				dtfrom=datetime.datetime.now()
				#todo....get gmt to local time with timezone logic
				dtfrom2=dtfrom+ timedelta(hours=10) #for gmt to au date (+10) hrs
				dtfrom2=dtfrom2+ timedelta(days=1) #
				_from_date 	=  datetime.datetime.strptime(str(dtfrom2),"%Y-%m-%d %H:%M:%S.%f")
				
				
				
				_dt 	= str((_from_date).strftime("%Y-%m-%d"))
				#_logger.error("_truck_count1_truck_count1:2maro %s , wtime %s, currtime %s []" % (_dt,_from_date,dtfrom))
				sql="select sum(dockets) from dincelwarehouse_sale_order_delivery where date_actual='%s'" % (_dt)
				cr.execute(sql)
				#_logger.error("_truck_count1_truck_count1_truck_count122222:sqlsql[" + str(sql)+ "]")
				rows 	= cr.fetchone()
				if rows and len(rows) > 0 and rows[0]:
					_ret = rows[0]
				else:	
					_ret = '0'
			else:
				_ret=''		
			x[record.id]=_ret 	
		return x	
		
	_columns = {	
		'name':fields.char("Name"),
		'code':fields.char("Code"),
		'produce_speed':fields.float("Production Speed"),
		'type':fields.selection([
			('product', 'Product'),
			('delivery', 'Delivery'),
			], 'Type'),
		'remain_lm':fields.float("Remain L/M"),
		'remain_hrs':fields.float("Remain Hrs"),
		'lead_days':fields.integer("Lead Days"),	
		'last_update':fields.datetime("Last Update"),	
		'next_schedule':fields.date("Next Schedule Start"),	
		'user_id':fields.many2one("res.users", 'Updated By'),
		'hold_lm':fields.float("Hold L/M"),	
		'hold_hrs':fields.float("Hold Hrs"),
		'x_remain_lm':fields.function(_remain_lm, method=True, string='Remain L/M',type='float'),
		'x_remain_hrs':fields.function(_remain_hrs, method=True, string='Remain Hrs',type='float'),
		'x_hold_lm':fields.function(_hold_lm, method=True, string='Hold L/M',type='float'),
		'x_hold_hrs':fields.function(_hold_hrs, method=True, string='Hold Hrs',type='float'),
		'truck1':fields.function(_truck_count1, method=True, string='Trucks Today',type='char'),
		'truck2':fields.function(_truck_count2, method=True, string='Tomorrow',type='char'),
	}
	
	def write(self, cr, uid, ids, vals, context=None):
		res = super(dincelsale_productsummary, self).write(cr, uid, ids, vals, context=context)
		for record in self.browse(cr, uid, ids):
			dt 	= datetime.datetime.now()
			sql="update dincelsale_productsummary set user_id='%s',last_update='%s'" %(uid, dt)
			sql+=" where id='%s'" %(record.id)
			cr.execute(sql)	
		return res	
	 	