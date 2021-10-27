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

				
class dincelstock_pickinglist(osv.Model):
	_name 			= "dincelstock.pickinglist"
	account_id		= None
	#company_id		= None
	move_id			= None
	#partner_id		= None
	#name			= None
	date			= None
	period_id		= None
	
	_order = 'date_picking desc, id desc'
	def change_picktime(self, cr, uid, ids, _time,  context=None):
		if _time:

			#dt	= self.pool.get('res.partner').browse(cr,uid,contact_id,context=context).phone
			dt=self.pool.get('dincelstock.transfer').get_au_datetime(cr, uid, _time)
			strt=str(dt)
			return {'value': {'date_picking':strt[:10]}}
		return {}	
		
	def onchange_contact(self, cr, uid, ids, contact_id,  context=None):
		if contact_id:
			mobile	= self.pool.get('res.partner').browse(cr,uid,contact_id,context=context).mobile
			phone	= self.pool.get('res.partner').browse(cr,uid,contact_id,context=context).phone
			#value   = {'phone':phone,'mobile':mobile}
			return {'value': {'phone':phone,'mobile':mobile}}
		return {}	
		
	def _get_default_company(self, cr, uid, context=None):
		company_id = self.pool.get('res.users')._get_company(cr, uid, context=context)
		if not company_id:
			raise osv.except_osv(_('Error!'), _('There is no default company for the current user!'))
		return company_id
		
	def _get_total_amount(self, cr, uid, ids, values, arg, context=None):
		if context is None:
			context = {}
		qty = 0
		x1={}
		for pick in self.browse(cr, uid, ids, context=context):
			totprice = 0.0
			for item in pick.picking_line:
				ship_qty = item.ship_qty
				qty_order = item.qty_order
				price_unit = item.price_unit
				order_length = item.order_length
				product_id = item.product_id.id
				
				prod_cat = item.product_id.x_prod_cat
				m2_factor = item.product_id.x_m2_factor
				
				if(prod_cat == 'stocklength' or prod_cat == 'customlength'):
					qty = round(ship_qty*order_length*0.001,2)
					if(m2_factor):
						qty = round(qty * m2_factor,2)
					else:
						qty = round(qty * 0.33333,2)
				else:
					qty = ship_qty
					
				price = round(float(qty*price_unit),2)
				totprice += price
			x1[pick.id] = round(totprice,2)
		return x1
		
		
	_columns = {
		'name': fields.char('Reference'),
		'origin': fields.char('Source Document', help="Reference of the document that generated this picking list."),
		'type': fields.selection([
			('order', 'Order'),
			('manual', 'Manual'),
			]),
		'state': fields.selection([
			('draft', 'Draft'),
			('cancel', 'Cancelled'),
			('sent', 'Sent'),
			('progress', 'Pending'), #('closed', 'Closed'),
			('done', 'Delivered'),
			], 'Status', track_visibility='onchange'),
		'date_picking': fields.date('Date', required=True),
		'time_picking': fields.datetime('Date Time'),
		'pick_order_id': fields.many2one('sale.order', 'Sale Order'),
		'project_id': fields.many2one('res.partner','Project / Site'),	
		'project_suburb_id': fields.related('project_id', 'x_suburb_id',  string='Suburb', type="many2one", relation="dincelbase.suburb",store=True),		
		'x_project_id': fields.related('pick_order_id', 'x_project_id', type='many2one', string='Project / Site',relation="res.partner",store=False),
		'order_code': fields.related('pick_order_id', 'origin', type='char', string='DCS Code',store=False),
		'color_code': fields.related('pick_order_id', 'x_colorcode', type='char', string='Color',store=False),
		'deposit_paid': fields.related('pick_order_id','x_dep_paid', string='Deposit Paid',type='char',store=True),
		'balance_paid': fields.related('pick_order_id','x_bal_paid', string='Balance Paid',type='char',store=True),
		'pick_total_amount':fields.function(_get_total_amount, string='Value $(ex.GST)',type='float',store=False),
		'user_id': fields.many2one('res.users', 'Prepared By'),
		'partner_id': fields.many2one('res.partner', 'Customer', domain=[('customer', '=', True),('x_is_project', '=', False)]),
		'contact_id': fields.many2one('res.partner', 'Contact', domain=[('x_is_project', '=', False)]),
		'phone': fields.related('contact_id', 'phone', type='char', string='Contact Phone',store=False),
		'mobile': fields.related('contact_id', 'mobile', type='char', string='Contact Mobile',store=False),
		'delivery_to': fields.char('Deliver To'),
		#'project_id': fields.many2one('res.partner', 'Project', domain=[('x_is_project', '=', True)]),
		'picking_line': fields.one2many('dincelstock.pickinglist.line', 'pickinglist_id', 'Order Lines'),
		#'move_line': fields.one2many('stock.move', 'x_pickinglist_id', 'Move Lines'),
		'note': fields.text('Note'),
		'company_id': fields.many2one('res.company', 'Company'),
		'source_location_id': fields.many2one('stock.location', 'Source Location'),
		'destination_location_id': fields.many2one('stock.location', 'Destination Location'),
		'warehouse_id': fields.many2one('stock.warehouse','Dispatch Location'),	
		'print_transport': fields.boolean('Print Transport Document?'),
		#'total_value': fields.function(_total_value, method=True, string='Value $(ex.GST)', type='float'),
		'pudel':fields.selection([
			('pu','Pickup'),
			('del','Delivery'),
			], 'Pickup/Delivery'),
		'vehicle_type': fields.selection([
			('bdouble', 'B-Double'),
			('semi', 'Semi'),
			('rigid', '8 Metre Rigid'),
			('utility', 'Utility'),
			('other', 'Other'),
			], 'Vehicle Type'),	
		'recipient_full_name':fields.char('Recipient Full Name'),
		'recipient_license':fields.char('License No'),
		'vehicle_rego':fields.char('Vehicle REGO'),
		'trailer_rego':fields.char('Trailer REGO'),
		'trailer_rego_na':fields.boolean('Trailer REGO N/A'),	
		'pick_no':fields.integer('SNo',size=2), #1=t, 1, 2, 3...99 is max ...	
		'dcs_refcode': fields.char('DCS Docket No.'),
		'pdf_attachs':fields.many2one('ir.attachment','Pdf Attachments'),
		'schedule_id': fields.many2one('dincelwarehouse.sale.order.delivery', 'Deivery Schedule'),
	}	
	#'x_market_wall_id': fields.related('x_project_id', 'x_market_wall_id',  string='Specified Wall', type="many2one", relation="dincelcrm.market.wall.type",store=False),
	_defaults = {
		'date_picking': fields.datetime.now,
		'company_id': _get_default_company,
		'state': 'draft',
		'type': 'order',
		'user_id': lambda obj, cr, uid, context: uid,
		'name': lambda obj, cr, uid, context: '/',
		'pick_no': 1,
		#'note': lambda self, cr, uid, context: self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.sale_note,
	}
	
	def validate_stock_received(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		return False
		
	
	def validate_stock_sent(self, cr, uid, ids, context=None):	
		if context is None:
			context = {}
		move_obj = self.pool.get("stock.move")
		 
		#id 	origin 	product_uos_qty 	create_date 	move_dest_id 	product_uom 	price_unit 	product_uom_qty 	company_id 	date 	product_qty 	product_uos 	location_id 	priority 	picking_type_id 	partner_id 	note 	state 	origin_returned_move_id 	product_packaging 	date_expected 	procurement_id 	name 	create_uid 	warehouse_id 	inventory_id 	partially_available 	propagate 	restrict_partner_id 	procure_method 	write_uid 	restrict_lot_id 	group_id 	product_id 	split_from 	picking_id 	location_dest_id 	write_date 	push_rule_id 	rule_id 	invoice_state 	consumed_for 	raw_material_production_id 	production_id 	purchase_line_id 	weight 	weight_net 	weight_uom_id 	x_order_length

		for pick in self.browse(cr, uid, ids, context=context):
			if pick.state=="draft":
				if not pick.destination_location_id or not pick.source_location_id:
					raise osv.except_osv(_('Error!'), _('Source/Destination location missing.'))
				src_loc_id=pick.source_location_id.id
				dest_loc_id=pick.destination_location_id.id
				_name=self.pool.get('ir.sequence').get(cr, uid, 'stock.transfer') #stock.transfer
				for item in pick.picking_line:
					_qty		=item.ship_qty
					uos_qty		=_qty
					uom_qty		=_qty
					company_id	=pick.company_id.id
					state		= "waiting" #done after confirmed received
					#todo or?? self.pool.get('res.company')._company_default_get(cr, uid, 'stock.quant', context=c)
					price_unit=item.product_id.standard_price
					vals={
						"origin":_name,
						"name":item.product_id.name,
						"product_uos_qty":uos_qty,
						"price_unit":price_unit,
						"product_uom_qty":uom_qty,
						"location_id":src_loc_id,
						"location_dest_id":dest_loc_id,
						"state":state,
						"product_id":item.product_id.id,
						"product_uom":item.product_id.uom_id.id,
						"x_pickinglist_id":pick.id,
					}
					move_obj.create(cr, uid, vals, context=context)
				#_obj.write(cr, uid, ids, vals, context=context)	
				val1={
					"name": _name ,
					"state": "progress",
					}
				#_logger.error("onchange_product_unlinkunlink_state_val1val1["+str(val1)+"]")		
				self.pool.get('dincelstock.pickinglist').write(cr, uid, [pick.id], val1, context=context)		
				
	#def write(self, cr, uid, ids, context=None):
	#	#move_obj = self.pool.get('stock.move')
	#	context = context or {}
	#	return super(dincelstock_pickinglist, self).write(cr, uid, ids, context=context)
	def unlink(self, cr, uid, ids, context=None):
		#move_obj = self.pool.get('stock.move')
		context = context or {}
		
		_state= self.pool.get('dincelstock.pickinglist').browse(cr, uid, ids[0], context=context).state
		if _state=="done":
			#_logger.error("onchange_product_unlinkunlink_state_state["+str(_state)+"]")	
			#raise osv.except_osv(_('Error!'), _('You cannot delete a delivered docket.'))
			str1="A delivered docket cannot be deleted."
			raise osv.except_osv(_('Error'), _(''+str1))
			return False
		else:		
			move_tmp = self.pool.get("stock.move.tmp")
			
			#_logger.error("onchange_product_unlinkunlink111["+str(ids)+"]")	
			#self.browse(cr, uid, ids[0], context=context):
			for pick in self.browse(cr, uid, ids, context=context):
				#if pick.state=="done":
				#	raise osv.except_osv(_('Error!'), _('You cannot delete a delivered docket.'))
				#else:
				for item in pick.picking_line:
					if item.product_id.x_prod_cat in['stocklength','customlength']:
						_qty=item.ship_qty*item.order_length*0.001
					else:
						_qty=item.ship_qty
						
					move_ids = move_tmp.search(cr, uid, [('order_id', '=', pick.pick_order_id.id),
											('product_id','=',item.product_id.id),
											('product_qty','=',_qty),
											('move_type','=','sales'),
											], context=context)
					move_tmp.unlink(cr, uid, move_ids, context=context)
				#_logger.error("onchange_product_unlinkunlink222["+str(move_ids)+"]["+str(pick.pick_order_id.id)+"]")	
				#move_ids = [move.id for move in pick.move_lines]
				#move_obj.action_cancel(cr, uid, move_ids, context=context)
				#move_obj.unlink(cr, uid, move_ids, context=context)
			return super(dincelstock_pickinglist, self).unlink(cr, uid, ids, context=context)
		
	def docket_print_dcs(self, cr, uid, ids, context=None):	
		'''datas = {'ids': []}
		datas['form']  = self.read(cr, uid, ids, context=context)[0]
		return self.pool['report'].get_action(cr, uid, [], 'dincelstock.report_docket_report', data=datas, context=context)	'''		
		if context is None:
			context = {}
		#datas = {'ids': []}
		#datas['form']  = self.read(cr, uid, ids, context=context)[0]
		#return self.pool['report'].get_action(cr, uid, [], 'production.report_mo_pqreport', data=datas, context=context)	
		url=self.pool.get('dincelaccount.config.settings').report_preview_url(cr, uid, ids,"docket",ids[0],context=context)		
		return {
				  'name'     : 'Go to website',
				  'res_model': 'ir.actions.act_url',
				  'type'     : 'ir.actions.act_url',
				  'view_type': 'form',
				  'view_mode': 'form',
				  'target'   : 'current',
				  'url'      : url,
				  'context': context
			   }
	def _get_wkhtmltopdf_bin(self, cr, uid, ids, context=None):
		wkhtmltopdf_bin = find_in_path('wkhtmltopdf')
		if wkhtmltopdf_bin is None:
			raise IOError
		return wkhtmltopdf_bin
	def docket_print_dcs_pdf(self, cr, uid, ids, context=None):	
		'''if context is None:
			context = {}
		datas = {'ids': []}
		datas['form']  = self.read(cr, uid, ids, context=context)[0]
		return self.pool['report'].get_action(cr, uid, [], 'dincelstock.report_docket_report_pdf', data=datas, context=context)	'''
		if context is None:
			context = {}
		#datas = {'ids': []}
		#datas['form']  = self.read(cr, uid, ids, context=context)[0]
		#return self.pool['report'].get_action(cr, uid, [], 'production.report_mo_pqreport_pdf', data=datas, context=context)	
		ir_id = False 
		fname = False
		ir_attachement_obj=self.pool.get('ir.attachment')
		
		for record in self.browse(cr, uid, ids):
			if not record.dcs_refcode or record.dcs_refcode=="":
				raise osv.except_osv(_('Error'), _('Docket number missing, please update DCS first to generate pdf.'))
				
			fname="docket_"+str(record.id)+".pdf"
			temp_path="/var/tmp/odoo/docket/"+fname
			if record.pdf_attachs:
				#ir_id=record.pdf_attachs.id
				try:
					ir_attachement_obj.unlink(cr, uid, [record.pdf_attachs.id])
				except ValueError:
					ir_id = False #......
			#else:
				'''
				command_args = []
				local_command_args=[]
				command_args.extend(['--orientation', 'landscape'])
				wkhtmltopdf = [self._get_wkhtmltopdf_bin(cr, uid, ids)] + command_args + local_command_args
				wkhtmltopdf += [url] + [temp_path]
				'''
				
			
			url=self.pool.get('dincelaccount.config.settings').report_preview_url(cr, uid, ids,"docket",record.id,context=context)	
			
			
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
			#_logger.error("returncodereturncodewkhtmltopdfwkhtmltopdf["+str(process)+"]["+str(out)+"]["+str(err)+"]")									
			f=open(temp_path,'r')
			
			_data = f.read()
			_data = base64.b64encode(_data)
			f.close()
			
			
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
		if ir_id and fname:
			return {
					'type' : 'ir.actions.act_url',
					'url': '/web/binary/saveas?model=ir.attachment&field=datas&filename_field=name&id=%s' % ( ir_id, ),
					'target': 'self',
				}
		
	def update_docket_dcs(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		
		sql ="SELECT dcs_api_url FROM dincelaccount_config_settings";
		cr.execute(sql)
		rows = cr.fetchone()
		if rows and len(rows) > 0:
			url= str(rows[0]) + "?act=docket&id="+str(ids[0])
			#url="http://erp.dincel.com.au/dcsapi/index.php?act=docket&id="+str(ids[0])
			#f = urllib2.urlopen(url)http://220.233.149.98/dcsapi/index.php?act=docket&id=2914
			try:
				f = urllib2.urlopen(url, timeout = 10) #10 seconds timeout
				response = f.read()
				str1= simplejson.loads(response)
				
				item = str1['item']
				status1=str(item['post_status'])
				dcs_refcode=str(item['dcs_refcode'])
				if status1=="success":
					sql ="UPDATE dincelstock_pickinglist SET dcs_refcode='"+dcs_refcode+"' WHERE id='"+str(ids[0])+"'"
					cr.execute(sql)
					return True
				else:
					if item['errormsg']:
						str1=item['errormsg']
					else:
						str1="Error while updating docket."
					raise osv.except_osv(_('Error'), _(''+str1))
			except Exception, e:
				pass
				raise osv.except_osv(_('Error'), _(''+str(e)))
			 
		return True		
		
	def mark_as_delivered(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		_obj 		= self.pool.get('dincelaccount.journal')
		new_id		= ids[0]
		ret 		= _obj.sales_delivery2journals(cr, uid, ids, new_id, context=context)
		if ret and ret > 0:
			#-----------------------------------------------------------------
			_objstock = self.pool.get('stock.picking')
			_objmove  = self.pool.get('stock.move')
			
			#_objpk = self.pool.get('dincelstock.pickinglist')
			_obj1 = self.pool.get('dincelstock.pickinglist')
			_objpk = _obj1.browse(cr, uid, new_id, context=context)
			line_obj 	= self.pool.get('dincelstock.pickinglist.line')
			_obj2sale 		= self.pool.get('sale.order').browse(cr, uid, _objpk.pick_order_id.id, context=context)
			
			'''
			tot_delivered 	=0
			tot_ordered 	=0
			for line in _obj2sale.order_line:
				
				prod_cat=line.product_id.prod_cat
				if prod_cat not in['freight','deposit']:
					qty_order=line.x_order_qty
					tot_ordered += qty_order
					qty_ship=0
					
					if prod_cat=="customlength":
						
					else:
						
				tmpids 	= line_obj.search(cr, uid, [('origin','=',_obj2sale.name),('product_id','=',line.product_id.id),('order_length','=',line.x_order_length or 0)], context=context)
				for o in line_obj.browse(cr, uid, tmpids, context=context):
					qty_ship+=o.ship_qty
				tot_delivered+=qty_ship
			if tot_delivered>0:
				if tot_delivered>=tot_ordered:
					#, 'state':'done' do not mark as done this time...cause invoice will still remained
					self.pool.get('sale.order').write(cr, uid, _obj2sale.id, {'x_del_status':'delivered'})	
				else:
					self.pool.get('sale.order').write(cr, uid, _obj2sale.id, {'x_del_status':'part'})	
			#-----------------------------------------------------------------	
			'''
			
			_ptype	=self.pool.get('stock.picking.type')
			_idtype	=_ptype.search(cr, uid, [('code', '=', 'outgoing'),('warehouse_id', '=', _objpk.warehouse_id.id)], limit=1) 	
			#if _ids:
			#	_ptype 	= _ptype.browse(cr, uid, _ids[0], context=context)
			vals={
				'origin': str(_objpk.origin),
				'partner_id': _obj2sale.partner_id.id,
				'company_id': _obj2sale.company_id.id,
				'name':_objpk.name,
				'state':'done',
				'move_type':'direct',
				}
			if _idtype:
				vals['picking_type_id']=_idtype[0]
			
			#_logger.error("picking_type_idpicking_type_i_objstock["+str(vals)+"]")		
			pckid = _objstock.create(cr,uid,vals,context)		
			
			if pckid:
				
				_jid = self.pool.get('dincelstock.journal').order_delivery_confirm(cr, uid, _objpk.id, context)
				for line in _objpk.picking_line:
					#product_id 	= line.product_id.id
					#order_length 	= line.x_order_length or 0
					#ship_qty 		= line.ship_qty
					if line.ship_qty>0:
						_id2= self._create_stock_journal_docketsent(cr, uid, _objpk, _jid, line, context)
						
						_origin = "%s" % ( _obj2sale.name)
						
						if _obj2sale.origin:
							_origin += "/%s" % (_obj2sale.origin)
						
						if _objpk.dcs_refcode:
							_origin += "/%s" % (_objpk.dcs_refcode)
						
						
						vals={
							'origin':_origin,#str(_objpk.name),#TODO may be product code??? 'origin': _obj2.origin,
							#'product_qty': line.ship_qty,
							'x_quantity': line.ship_qty, #stock qty movement...
							'partner_id': _obj2sale.partner_id.id,
							'picking_id': pckid,
							'x_order_length':line.order_length or 0,
							'product_id':line.product_id.id,
							'name':line.product_id.name,
							}
						if line.product_id.x_prod_type 	and line.product_id.x_prod_type =="acs":
							qty_move=line.ship_qty
						else:
						#if line.order_length and line.order_length>0 and line.product_id.x_prod_cat in['stocklength','customlength']:
							qty_move=line.order_length *0.001*line.ship_qty
						#else:
						#	qty_move=line.ship_qty
						'''
						--------------------------------------------
						NOTE ---------------------------------------
						--------------------------------------------
							product_uos_qty :is the quantity of product in the stock move in Unit of Sale.
							product_qty 	:is the qunatity of product in the stock move in product default UoM.
							product_uos_qty :is used to display on the invoice the same quantity than the quantity sold in the sale order in case of invoicing on delivery.
							product_qty 	:is used to compute the stock level of a product. The stock level is always computed in default product UoM.
						--------------------------------------------
						--------------------------------------------'''	
						if line.product_id.uom_id:
							vals['product_uom']=line.product_id.uom_id.id #unit of stock move
							vals['product_uos']=line.product_id.uom_id.id #unit of sold
							
						vals['product_uom_qty']=qty_move #assusing sold and move qty same...
						vals['product_uos_qty']=qty_move #assusing sold and move qty same...
						if _objpk.warehouse_id:
							vals['warehouse_id']=_objpk.warehouse_id.id
						
						if line.location_id:	
							vals['location_id']=line.location_id.id
						else:
							if _objpk.source_location_id:
								vals['location_id']=_objpk.source_location_id.id
						if _objpk.destination_location_id:
							vals['location_dest_id']=_objpk.destination_location_id.id
						#_logger.error("picking_type_idpicking_type_idpicking_type_id["+str(vals)+"]["+str(line)+"]")	
						_id=_objmove.create(cr, uid, vals, context)		
						_objmove.action_done(cr, uid, [_id], context)  #in order to make stock move qty update
						_objmove.quants_assign_dcs(cr, uid, [_id]) #assign the quants qty..
					
				#_objstock.do_transfer()
				#self.pool.get('dincelwarehouse.sale.order.delivery').write(cr, uid, _objpk.schedule_id.id, {'status':'done'})
			#-----------------------------------------------------------------	
			self.write(cr, uid, new_id, {'state':'done'})	
			
			#-----------------------------------------------------------------
			tot_delivered 	= 0
			tot_ordered 	= 0
			found_part		= False
			for line in _obj2sale.order_line:
				prod_cat	=line.product_id.x_prod_cat
				order_id	=_obj2sale.id 
				
				if prod_cat not in['freight','deposit']:
					product_id=line.product_id.id
					qty_order=line.x_order_qty
					tot_ordered += qty_order
					qty_delivered=0
					
					if prod_cat == "customlength":
						order_length=int(line.x_order_length)
						sql="select sum(d.ship_qty) from dincelstock_pickinglist s,dincelstock_pickinglist_line d, product_product p,product_template t WHERE s.id=d.pickinglist_id and p.product_tmpl_id=t.id and d.product_id=p.id and s.pick_order_id='%s' and d.order_length=%s and d.product_id='%s' " % (order_id, str(order_length),str(product_id))
					else:
						sql="select sum(d.ship_qty) from dincelstock_pickinglist s,dincelstock_pickinglist_line d, product_product p,product_template t WHERE s.id=d.pickinglist_id and p.product_tmpl_id=t.id and d.product_id=p.id and s.pick_order_id='%s' and d.product_id='%s' " % (order_id, str(product_id))
					
					try:
						cr.execute(sql)
						rows2= cr.fetchone()
						if rows2 and len(rows2)>0:
							qty_delivered=int(rows2[0])
					except Exception, e:
						qty_delivered = 0	
						
					tot_delivered += qty_delivered	
					
					if qty_delivered < qty_order:
						found_part	= True #just to make sure item delivery checked line by line rather than total sum...
				
			if tot_delivered>0:
				if tot_delivered>=tot_ordered and found_part == False:
					#, 'state':'done' do not mark as done this time...cause invoice will still remained
					#self.pool.get('sale.order').write(cr, uid, _obj2sale.id, {'x_del_status':'delivered'})	
					_status="delivered"
				else:
					#self.pool.get('sale.order').write(cr, uid, _obj2sale.id, {'x_del_status':'part'})	
					_status="part"
				
				sql="update sale_order set x_del_status='%s' where id='%s'"	 % (_status, _obj2sale.id)
				cr.execute(sql)
				#_logger.error("picking__status_status_status_id["+str(sql)+"]["+str(tot_delivered)+"]")
			#-----------------------------------------------------------------
			if _objpk.schedule_id:# and _objpk.schedule_id!=None:
				sql="select 1 from dincelwarehouse_sale_order_delivery where id='%s'" % (_objpk.schedule_id.id)
				cr.execute(sql)
				rows1 = cr.fetchall()
				if rows1 and len(rows1) >0:
					sql ="select 1 from dincelstock_pickinglist where schedule_id='"+str(_objpk.schedule_id.id)+"' and state='done'"
					cr.execute(sql)
					rows = cr.fetchall()
					_tot=_objpk.schedule_id.dockets
					_done=len(rows)
					_rem=_tot-_done
					if rows and len(rows) >= _objpk.schedule_id.dockets:
						self.pool.get('dincelwarehouse.sale.order.delivery').write(cr, uid, _objpk.schedule_id.id, {'state':'done','dockets_remain':_rem})
					else:
						self.pool.get('dincelwarehouse.sale.order.delivery').write(cr, uid, _objpk.schedule_id.id, {'state':'partial','dockets_remain':_rem})
					
	def _create_stock_journal_docketsent(self, cr, uid, transfer, _jid, _line, context=None):
		_qty		=int(_line.ship_qty)
		if abs(_qty)>0:
			_length		=int(_line.order_length)
			_obj = self.pool.get('dincelstock.journal').browse(cr, uid, _jid, context=context)
			_objline = self.pool.get('dincelstock.journal.line')
		 
			_dt		= self.pool.get('dincelstock.transfer').get_au_datetime(cr, uid, transfer.time_picking)
			vals={'journal_id':_jid,
					'product_id':_line.product_id.id,
					'date':_dt,#transfer.date_picking,
					'date_gmt':transfer.time_picking,
					'period_id':_obj.period_id.id,
					'prod_length':_length,
					#'location_id':transfer.source_location_id.id,
					'reference':_('DOCKET:') + (transfer.name or ''),
					}
			if _line.location_id:
				vals['location_id'] 	= _line.location_id.id
			else:
				vals['location_id'] 	= transfer.source_location_id.id
			if transfer.pick_order_id:
				vals['order_id'] 	= transfer.pick_order_id.id
			if _line.product_id.x_prod_type=="acs":
				vals['is_acs'] 	= True	
			else:
				vals['is_acs'] 	= False
			vals['qty_in'] 	= 0	
			vals['qty_out'] = _qty
			
			return _objline.create(cr, uid, vals, context=context)
		
	def mark_as_delivered_bakup(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
	
		self.journal_id		= self.pool.get('account.journal').search(cr, uid, [('type', '=', 'sale')], limit=1) 	
		#_logger.error("mark_as_delivered_mark_as_delivered.journal_id["+str(self.journal_id)+"]")
		'''sql 		= "select x_sale_acct_receive,x_sale_account,x_sale_account_tax,x_sale_cogs,x_sale_finished_goods,x_sale_cash_discount,x_sale_unrealised,x_sale_unrealised_discount,x_sale_freight,x_sale_freight_unrealised from dincelaccount_config_settings"
		cr.execute(sql)
		res 		= cr.dictfetchone()	#self.cr.fetchone()
		if res:
			acct_trade_dr 		= (res['x_sale_acct_receive'])
			acct_sale_acct 		= (res['x_sale_account'])
			
			sale_tax 			= (res['x_sale_account_tax'])
			
			acct_sale_cogs 		= (res['x_sale_cogs'])
			acct_sale_goods 	= (res['x_sale_finished_goods'])
			acct_sale_discount 	= (res['x_sale_cash_discount'])
			acct_sale_unrealised  		= (res['x_sale_unrealised'])
			acct_unrealised_discount  	= (res['x_sale_unrealised_discount'])
			acct_freight				=	res['x_sale_freight']
			acct_freight_unrealised		=	res['x_sale_freight_unrealised']'''
		_config =self.pool.get('dincelaccount.config.settings')
		_id		= _config.search(cr, uid, [], limit=1) 	
		if _id:
			_config 			= _config.browse(cr, uid, _id, context=context)
			acct_trade_dr 		= _config.sale_receiveable and _config.sale_receiveable.id  or False
			acct_sale 			= _config.sale_sale and _config.sale_sale.id  or False				
			
			sale_tax 			= _config.sale_sale_tax and _config.sale_sale_tax.id  or False		
			
			acct_sale_cogs 		= _config.sale_cogs and _config.sale_cogs.id  or False						
			acct_sale_goods 	= _config.sale_finished_goods and _config.sale_finished_goods.id  or False
			acct_sale_discount 	= _config.sale_cash_discount and _config.sale_cash_discount.id  or False	
			acct_sale_unrealised  		= _config.sale_unrealised and _config.sale_unrealised.id  or False	
			acct_unrealised_discount  	= _config.sale_unrealised_discount and _config.sale_unrealised_discount.id  or False	
			acct_freight				= _config.sale_freight and _config.sale_freight.id  or False							
			acct_freight_unrealised		= _config.sale_freight_unrealised and _config.sale_freight_unrealised.id  or False		
			sql = "select account_collected_id,account_paid_id from account_tax where id='%s'"%(sale_tax)
			cr.execute(sql)
			rest = cr.fetchone()
			if rest:
				acct_sale_tax_id		=rest[0]
				acct_sale_taxrefund		=rest[1]
			else:
				acct_sale_tax_id		=None
				acct_sale_taxrefund		=None
					
			for record in self.browse(cr, uid, ids, context=context):
				self.partner_id 	= record.partner_id
				self.date 			= record.date_picking
				self.name			= record.name
				self.company_id 	= record.company_id
				state				= "posted"	#  #draft, posted
				
				_objperiod 			= self.pool.get('account.period') 
				self.period_id		= _objperiod.find(cr, uid, date, context=context)[0]
				if self.period_id and self.journal_id:
					obj_move = self.pool.get('account.move')
					obj_move_line = self.pool.get('account.move.line')
					
					vals={
						'journal_id':self.journal_id,
						'name':self.name,
						'company_id':self.company_id,
						'state':state,
						'date':self.date,
						'period_id':self.period_id,
						'partner_id':self.partner_id,
					}
					
					self.move_id = obj_move.create(cr, uid, vals, context=context)
					if self.move_id:
						cogs_amt 	= 0
						disc_amt	= 0
						deli_amt	= 0
						sale_amt	= 0
						amt_item	= 0
						for line in picking_line:
							cogs_amt += line.product_id.standard_price
							#disc_amt += line.disc_pc
							if line.product_id.x_prod_cat=="freight":
								amt_item	= line.price_unit*line.ship_qty
							else:#elif line.product_id.x_prod_cat=="freight":	
								amt_item	= line.price_unit*line.ship_qty
							sale_amt += amt_item
							disc_amt += (amt_item*line.disc_pc*0.01) 
						if cogs_amt > 0.00:
							debit		=cogs_amt
							credit		=0
							account_id	=acct_sale_cogs
							self.add_journal_moveline(debit, credit,account_id, context)
							debit		=0
							credit		=cogs_amt
							account_id	=acct_sale_goods
							self.add_journal_moveline(debit, credit,account_id, context)
						if disc_amt > 0.00:
							debit		=disc_amt
							credit		=0
							account_id	=acct_sale_discount
							self.add_journal_moveline(debit, credit,account_id, context)
							debit		=0
							credit		=disc_amt
							account_id	=acct_unrealised_discount
							self.add_journal_moveline(debit, credit,account_id, context)
						if deli_amt > 0.00:
							debit		=deli_amt
							credit		=0
							account_id	=acct_freight_unrealised
							self.add_journal_moveline(debit, credit,account_id, context)
							debit		=0
							credit		=deli_amt
							account_id	=acct_freight
							self.add_journal_moveline(debit, credit,account_id, context)
						if sale_amt > 0.00:
							debit		=sale_amt
							credit		=0
							account_id	=acct_sale_unrealised
							self.add_journal_moveline(debit, credit,account_id, context)
							debit		=0
							credit		=sale_amt
							account_id	=acct_sale_acct
							self.add_journal_moveline(debit, credit,account_id, context)
					self.write(cr, uid, ids[0], {'state':'done'})	
			
	def add_journal_moveline(self, cr, uid, ids, debit, credit,account_id, context=None):
		obj_move_line = self.pool.get('account.move.line')
		state_line	= "valid"
		quantity	= 1
		vals={
			'journal_id':self.journal_id,
			'move_id':self.move_id,
			'account_id':account_id,
			'debit':debit,
			'credit':credit,
			'ref':self.name,
			'name':self.name,
			'company_id':self.company_id,
			'state':state_line,
			'date':self.date,
			'quantity':quantity,
			'period_id':self.period_id,
			'partner_id':self.partner_id,
		}
		obj_move_line.create(cr, uid, vals, context=context)
		

class dincelstock_pickinglist_line(osv.Model):
	_name 	= "dincelstock.pickinglist.line"
	_order 	= "sequence"
	_columns = {
		'pickinglist_id': fields.many2one('dincelstock.pickinglist', 'Picking Reference', required=True, ondelete='cascade', select=True),
		'name': fields.text('Description', required=True),
		'sequence': fields.integer('Sequence'),
		'product_id': fields.many2one('product.product', 'Product', ondelete='restrict'),
		'location_id': fields.many2one('stock.location', 'Location'),
		'ship_qty':fields.float("Qty Shipped",digits_compute= dp.get_precision('Int Number')),	
		'qty_res_picked':fields.integer("Picked out of reserved",help="If qty are produced part and reserved part then. put items which are reserved picked."),	
		'qty_order':fields.float("Qty Ordered",digits_compute= dp.get_precision('Int Number')),	
		'qty_remain':fields.float("Qty Remain",digits_compute= dp.get_precision('Int Number')),	
		'price_unit':fields.float("Unit Price"),	
		'disc_pc':fields.float("Discount Percent"),	
		'order_length':fields.float("Stock Length",digits_compute= dp.get_precision('Int Number')),	
		'origin': fields.char('Source Document'),
		'packs': fields.char('Packs'),
		'region_id': fields.many2one('dincelaccount.region', 'A/c Region'),
		'coststate_id':fields.many2one("res.country.state","Cost Centre"),
		'product_uom': fields.many2one('product.uom', 'Unit of Measure'),
	}	
	
	
		
	def onchange_product_id(self, cr, uid, ids, product_id, context=None):
		res = {}
		if product_id:
			prod = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
			res['value'] = {
				'name': prod.name,
			}
		#_logger.error("onchange_product_idonchange_product_id["+str(res)+"]["+str(product_id)+"]")	
		return res	
		
class dincelstock_location(osv.Model):
	_inherit="stock.location"
	_order 	= "x_sequence"
	_columns = {
		'x_warehouse_id': fields.many2one('stock.warehouse','Warehouse'),
		'x_sequence': fields.integer('Sequence'),		
		'x_holdyard': fields.boolean('Holding Yard', help="Holding yard after production. Temp stock location."),
		'x_primary': fields.boolean('Primary/Head Office', help="Head Office location."),
		'x_ibt': fields.boolean('IBT Location'),
	}
	_defaults = {
		'x_holdyard': False,
		'x_primary': False,
		'x_ibt': False,
	}


	
	
#class dincelstock_sale_order(osv.Model):		
#_inherit="sale.order"
#_columns = {
#	'x_pickinglist_ids': fields.one2many('dincelstock.pickinglist', 'pick_order_id', 'Deliveries'),#	'x_pickinglist_ids': fields.one2many('dincelstock.pickinglist', 'order_id','Deliveries'),	
#}

class dincelstock_stockreserve(osv.Model):	
	_name = "dincelstock.move.reserve"
	_columns = {	
		'date': fields.date('Date'),
		'order_id': fields.many2one('sale.order', 'Sale Order Id',ondelete='cascade',),
		'warehouse_id': fields.many2one('stock.warehouse', 'Source Warehouse'),
		'product_id': fields.many2one('product.product', 'Product'),
		#'production_id': fields.many2one('dincelmrp.production', 'Production Reference',ondelete='cascade',),
		'location_id': fields.many2one('stock.location', 'Source Location'),
		'order_length':fields.integer("Length (mm)"),
		'quantity': fields.integer('Qty (each)',help="Quantity for each, cause qty is sometimes recordes as L/M in case of stock/custome p1 products"),
		'state': fields.selection([
				('reserved', 'Reserve'), #for temporary stock count >> total reserve ===(reserve,packed)
				('packed', 'Packed'), #for temporary stock count
				('done', 'Move Done Delivered') 
				], 'Status'),
	}
	_defaults = {
		'quantity': 0,
	}



	
class dincelbase_stockmove(osv.Model):	
	_inherit = "stock.move"
	_columns = {	
		'x_order_length':fields.integer("Length (mm)"),
		'x_quantity': fields.integer('Qty (each)',help="Quantity for each, cause qty is sometimes recordes as L/M in case of stock/custome p1 products"),
	}
	_defaults = {
		'x_order_length': 0,
	}
	
	def quants_assign_dcs(self, cr, uid, ids, context=None):
	   
		for move in self.browse(cr, uid, ids, context=context):
			#found=False
			for quant in move.quant_ids:
				vals={}
				#_logger.error("quants_assign_dcsquants_assign_dcs["+str(move.x_order_length)+"]["+str(move.product_id.x_prod_cat)+"]")	
				if move.x_order_length and move.product_id.x_prod_cat in ['customlength','stocklength']:
					vals['x_order_length']=move.x_order_length
					_qty=quant.qty
					_len=move.x_order_length*0.001
					_qtyeach =int(_qty/_len) #backward calculation of 
					#found=True
					#if move.x_quantity:
					vals['x_quantity']=_qtyeach
				else:	
					vals['x_quantity']=quant.qty
					#found=True
				#if found:	
				self.pool.get('stock.quant').write(cr, uid, quant.id, vals)
		
class dincelbase_stockquant(osv.Model):	
	_inherit = "stock.quant"
	_columns = {	
		'x_order_length':fields.integer("Length (mm)"),
		'x_quantity': fields.integer('Qty (each)',help="Quantity for each, cause qty is sometimes recordes as L/M in case of stock/custome p1 products"),
	}
	_defaults = {
		'x_order_length': 0,
	}
	
	def qty_available(self, cr, uid, _product_id, _locid, context=None):	
		_qty=0
		_ids= self.search(cr, uid, [('product_id', '=', _product_id), ('location_id', '=', _locid)], context=context)
		for _item in self.browse(cr, uid, _ids, context=context):
			_qty+=int(_item.qty)
		return _qty	
		
	def qty_available_custom(self, cr, uid, _product_id, _len, _locid, context=None):	
		_qty=0
		sql="""select sum(qty_in-qty_out) as net from dincelstock_journal_line where 
					location_id='%s' and product_id='%s' and prod_length='%s' """	 % (_locid, _product_id, _len)
		cr.execute(sql)
		rows= cr.dictfetchall()
		for row in rows:
			qty_net=row['net']
			if qty_net and qty_net>0:
				_qty=qty_net
		#_ids= self.search(cr, uid, [('product_id', '=', _product_id), ('x_order_length', '=', _len), ('location_id', '=', _locid)], context=context)
		#for _item in self.browse(cr, uid, _ids, context=context):
		#	_qty+=int(_item.x_quantity)
		return _qty	