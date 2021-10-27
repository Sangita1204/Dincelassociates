from openerp.osv import osv, fields
from datetime import date
#from openerp.addons.base_status.base_state import base_state
import time 
import datetime
import logging
from dateutil import parser
from openerp.tools.translate import _
import urllib2
import simplejson
from time import gmtime, strftime
import base64
import subprocess
from subprocess import Popen, PIPE, STDOUT
import openerp.addons.decimal_precision as dp
from openerp import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

PROD_GROUP_SELECTION =[
	('none', 'None'),
	('P110', '110mm'),
	('P155', '155mm'),
	('P200', '200mm'),
	('P275', '275mm'),
	]
	
PUDEL_SELECTION =[
	('pu', 'Pickup'),
	('del', 'Delivery'),
	]
	
PROD_STATUS=[
			('queue','Queue'),
			('part','Part'),
			('complete','Complete'),
			]
			
class dincelmrp_mrp(osv.Model):
	_name = "dincelmrp.production"
	_order = 'id desc'
	
	def _pack_tot(self, cr, uid, ids, values, arg, context):
		x={}
		#_tot=0
		for record in self.browse(cr, uid, ids):
			x[record.id] = record.pack_110+record.pack_155+record.pack_200+record.pack_275
		return x
		
	def _has_res_110(self, cr, uid, ids, values, arg, context):
		x={}
		_has_panel=False
		for record in self.browse(cr, uid, ids):
			_has_panel=False
			for line in record.reserve_line:
				if line.product_id.x_dcs_group=="P110":
					_has_panel = True
			x[record.id] = _has_panel
		return x
	
	def _has_res_155(self, cr, uid, ids, values, arg, context):
		x={}
		_has_panel=False
		for record in self.browse(cr, uid, ids):
			_has_panel=False
			for line in record.reserve_line:
				if line.product_id.x_dcs_group=="P155":
					_has_panel = True
			x[record.id] = _has_panel
		return x
	
	def _has_res_200(self, cr, uid, ids, values, arg, context):
		x={}
		_has_panel=False
		for record in self.browse(cr, uid, ids):
			_has_panel=False
			for line in record.reserve_line:
				if line.product_id.x_dcs_group=="P200":
					_has_panel = True
			x[record.id] = _has_panel
		return x
	
	def _has_res_275(self, cr, uid, ids, values, arg, context):
		x={}
		_has_panel=False
		for record in self.browse(cr, uid, ids):
			_has_panel=False
			for line in record.reserve_line:
				if line.product_id.x_dcs_group=="P275":
					_has_panel = True
			x[record.id] = _has_panel
		return x	
		
	def _has_110(self, cr, uid, ids, values, arg, context):
		x={}
		_has_panel=False
		for record in self.browse(cr, uid, ids):
			_has_panel=False
			for line in record.production_line:
				if line.product_id.x_dcs_group=="P110":
					_has_panel = True
			x[record.id] = _has_panel
		return x
	
	def _has_155(self, cr, uid, ids, values, arg, context):
		x={}
		_has_panel=False
		for record in self.browse(cr, uid, ids):
			_has_panel=False
			for line in record.production_line:
				if line.product_id.x_dcs_group=="P155":
					_has_panel = True
			x[record.id] = _has_panel
		return x
	
	def _has_200(self, cr, uid, ids, values, arg, context):
		x={}
		_has_panel=False
		for record in self.browse(cr, uid, ids):
			_has_panel=False
			for line in record.production_line:
				if line.product_id.x_dcs_group=="P200":
					_has_panel = True
			x[record.id] = _has_panel
		return x
	
	def _has_275(self, cr, uid, ids, values, arg, context):
		x={}
		_has_panel=False
		for record in self.browse(cr, uid, ids):
			_has_panel=False
			for line in record.production_line:
				if line.product_id.x_dcs_group=="P275":
					_has_panel = True
			x[record.id] = _has_panel
		return x
		
	def _get_trucks(self, cr, uid, ids, _orderid, _type, context):	
		_no=0
		if _orderid and _type:
			sql = "select status,dockets from dincelwarehouse_sale_order_delivery where order_id='%s'" % str(_orderid)
			if _type=="done":
				sql += " and state='done'"
			else:	
				sql += " and state!='done'"
			cr.execute(sql)
			rows 	= cr.dictfetchall()
			_no=0
			for row in rows:
				status	=row['status']
				dockets	=row['dockets']
				if dockets=="" or dockets=="0":
					_no+=1#raise
				else:
					_no+=int(dockets)
		if _no==0:
			_no=''
		return _no
		
	def _trk_booked(self, cr, uid, ids, values, arg, context):
		x={}
		_no=''
		for record in self.browse(cr, uid, ids):
			#_qty= record.dockets
			#if _qty>0:
			_no=self._get_trucks( cr, uid, ids, record.order_id.id,"open",context)
			x[record.id] = _no 
		return x
	def _trk_delivered(self, cr, uid, ids, values, arg, context):
		x={}
		_no=''
		for record in self.browse(cr, uid, ids):
			#_qty= record.dockets
			#if _qty>0:
			_no=self._get_trucks( cr, uid, ids, record.order_id.id,"done",context)
			x[record.id] = _no 
		return x
	
	def _pending_invoice(self, cr, uid, ids, values, arg, context):
		x={}
		#_edit=False
		for record in self.browse(cr, uid, ids):
			x[record.id]=	self.pool.get("sale.order").get_cod_pending_invoice(cr,uid, ids,record.order_id.id,context) 
		return x
		
	_columns={
		'name': fields.char('Order Reference'),
		'order_id': fields.many2one('sale.order', 'Sale Order'),
		'order_code': fields.related('order_id', 'origin', type='char', string='DCS Code',store=False),
		'color_code': fields.related('order_id', 'x_colorcode', type='char', string='Color',store=False),
		'color_name': fields.related('order_id', 'x_colorname', type='char', string='Color Name',store=False),
		'deposit_paid': fields.related('order_id','x_dep_paid', string='Deposit Paid',type='char',store=False),
		'balance_paid': fields.related('order_id','x_bal_paid', string='Balance Paid',type='char',store=False),
		'balance_due': fields.related('order_id','x_over_due', string='Overdue?',type='char',store=False),
		'prod_status': fields.related('order_id', 'x_prod_status', type='selection', selection=PROD_STATUS, readonly=True, store=False, string='Status'),
		'pudel': fields.related('order_id', 'x_pudel', type='selection', selection=PUDEL_SELECTION, readonly=True, store=True, string='PU/DEL'),
		'production_line': fields.one2many('mrp.production', 'x_production_id', 'Production Lines'),
		'reserve_line': fields.one2many('dincelmrp.production.reserve', 'production_id', 'Reserve Lines'),
		#'stock_reserve_ids': fields.one2many('dincelstock.move.reserve', 'production_id', 'Stock Reserves'), NANA
		'state': fields.selection([
			('draft', 'Draft'),
			('cancel', 'Cancelled'),
			('progress', 'Pending'),
			('confirmed', 'Confirmed'),
			], 'Status'),
		'date_produce': fields.datetime('Date'),
		'user_id': fields.many2one('res.users', 'User'),
		'partner_id': fields.many2one('res.partner', 'Customer', domain=[('customer', '=', True),('x_is_project', '=', False)]),
		'project_id': fields.many2one('res.partner', 'Project', domain=[('x_is_project', '=', True)]),
		'project_suburb_id': fields.related('project_id', 'x_suburb_id',  string='Suburb', type="many2one", relation="dincelbase.suburb",store=True),
		'note': fields.text('Notes'),
		'note_110': fields.text('Notes 110mm'),
		'note_155': fields.text('Notes 155mm'),
		'note_200': fields.text('Notes 200mm'),
		'note_275': fields.text('Notes 275mm'),
		'note_reserve': fields.text('Notes Reserve'),
		'pack_110':fields.integer('Pack 110', size=2),
		'pack_155':fields.integer('Pack 155', size=2),
		'pack_200':fields.integer('Pack 200', size=2),
		'pack_275':fields.integer('Pack 275', size=2),
		'pack_tot': fields.function(_pack_tot, method=True, string='Packs', type='integer'),
		'has_110': fields.function(_has_110, method=True, string='Has 100', type='boolean'),
		'has_155': fields.function(_has_155, method=True, string='Has 155', type='boolean'),
		'has_200': fields.function(_has_200, method=True, string='Has 200', type='boolean'),
		'has_275': fields.function(_has_275, method=True, string='Has 275', type='boolean'),
		'has_res_110': fields.function(_has_res_110, method=True, string='Has Res 100', type='boolean'),
		'has_res_155': fields.function(_has_res_155, method=True, string='Has Res 155', type='boolean'),
		'has_res_200': fields.function(_has_res_200, method=True, string='Has Res 200', type='boolean'),
		'has_res_275': fields.function(_has_res_275, method=True, string='Has Res 275', type='boolean'),
		'part_no':fields.integer('Part', size=2), #0=full>default , 1,2,3...9 is max ...
		'fullpart': fields.selection([
			('full', 'FULL'),
			('part', 'PART'),
			], 'Production'),
		'trucks':fields.integer('Trucks', size=2),	
		'trk_booked': fields.function(_trk_booked, method=True, string='Booked Trucks', type='char'),
		'trk_delivered': fields.function(_trk_delivered, method=True, string='Delivered Trucks', type='char'),
		'product_id': fields.many2one('product.product', 'Delivery'),
		'packs':fields.integer('Packs', size=2),	
		'dcs_refcode':fields.char('DCS Reference'),
		'pdf_attachs':fields.many2one('ir.attachment','Pdf Attachments'),
		'acspdf_attachs':fields.many2one('ir.attachment','Acs Pdf Attachments'),
		'status_110':fields.char('Status 110mm'),
		'status_155':fields.char('Status 155mm'),
		'status_200':fields.char('Status 200mm'),
		'status_275':fields.char('Status 275mm'),
		'packby_110':fields.char('Packed By 110'),
		'packby_155':fields.char('Packed By 155'),
		'packby_200':fields.char('Packed By 200'),
		'packby_275':fields.char('Packed By 275'),
		'checkby_110':fields.char('Checked By 110'),
		'checkby_155':fields.char('Checked By 155'),
		'checkby_200':fields.char('Checked By 200'),
		'checkby_275':fields.char('Checked By 275'),
		'packdt_110':fields.date('Packed Date 110'),
		'packdt_155':fields.date('Packed Date 155'),
		'packdt_200':fields.date('Packed Date 200'),
		'packdt_275':fields.date('Packed Date 275'),
		'pending_invoice': fields.function(_pending_invoice, method=True, string='Pending COD Invoice',type='boolean'),
		#'mrp_route_id':fields.many2one('mrp.routing','MRP Route'),
		'mrp_route_ids' : fields.many2many('mrp.routing', 'rel_mrp_routing', 'route_id', 'production_id', string = "MRP Routes"),
		#'company_id': fields.many2one('res.company', 'Company'),
		'location_id': fields.many2one('stock.location', 'Location Stock'),
		'root_loc_id': fields.many2one('stock.location', 'Head Office Location'),
		'stock_type':fields.selection([
			('mo', 'MO'), #P-1 manufacture other MRP...
			('root', 'Head Office'),
			('local', 'Local Stock'), #root_loc_id=location_id
			], 'Stock Type'),
	}
	_defaults = {
		'state': 'draft',
		'fullpart': 'full',
		'status_110': '',
		'status_155': '',
		'status_200': '',
		'status_275': '',
		'part_no':0,
	}
	
	def unlink(self, cr, uid, ids, context=None, check=True):
		context = dict(context or {})
		if context is None:
			context = {}
		#_del=True	
		prod_status=''
		for record in self.browse(cr, uid, ids):
			prod_status= record.prod_status
		if prod_status and prod_status in ['part','complete','printed']:
			#_del=False
			raise osv.except_osv(_('Error!'), _('You cannot delete MRP after it has been printed, or produced partially or in full.'))
			#raise Warning(_('You cannot delete MRP after it has been produced partially or in full.'))
		else:#if _del:	 
			result = super(dincelmrp_mrp, self).unlink(cr, uid, ids, context)
			return result
			
	@api.multi 
	def print_pdf_load_sheet_dcs(self):
		#return self.loadsheet_pdf_byid(self.id)
		mo =self.env['dincelmrp.production'].browse(self.id)
		return self.env['sale.order'].loadsheet_pdf_byid(mo.order_id.id)		
		
	def button_schedule_delivery(self, cr, uid, ids, context=None):
		#obj = self.pool.get('sale.order').browse(cr, uid, ids[0], context=context)
		_obj = self.pool.get('dincelmrp.production').browse(cr, uid, ids[0], context=context)
		if _obj.order_id.state in ['done','cancel']:
			raise osv.except_osv(_('Forbbiden delivery'), _('The order is already closed/cancelled.'))	
		else:
			return {
				'type': 'ir.actions.act_window',
				'res_model': 'dincelmrp.schedule.delivery',
				'view_type': 'form',
				'view_mode': 'form',
				#'res_id': 'id_of_the_wizard',
				'context':{
					'default_order_id': _obj.order_id.id, 
					'default_pudel': _obj.order_id.x_pudel, 
					'default_partner_id': _obj.partner_id.id, 
					'default_project_id': _obj.project_id.id,
					'default_pending_invoice': _obj.pending_invoice,
				},
				'target': 'new',
			}
	 
		
	def onchange_product_line(self, cr, uid, ids, production_line, context=None):
		context = context or {}
	
		line_ids = self.resolve_2many_commands(cr, uid, 'production_line', production_line, ['product_id','x_pack_10','x_pack_12','x_pack_14','x_pack_20'], context)
		p110=0
		p155=0
		p200=0
		p275=0
		#_logger.error("onchange_order_line_dcs.line_ids["+str(line_ids)+"]["+str(x_region_id)+"]["+str(order_line)+"]")	  
		for line in line_ids:
			if line['product_id']:
				#_logger.error("onchange_order_line_dcs.line_idx_pack_20x_pack_20x_pack_20["+str(line['x_pack_20'])+"]")	  
				_obj = self.pool.get('product.product').browse(cr, uid, line['product_id'][0], context=context)
				#_logger.error("onchange_order_line_dcs.line_ids["+str(_obj.x_dcs_group)+"]")	  
				if _obj.x_dcs_group=="P110":
					p110=p110+int(line['x_pack_20'])
				elif _obj.x_dcs_group=="P155":
					p155=p155+int(line['x_pack_14'])	
				elif _obj.x_dcs_group=="P200":
					p200=p200+int(line['x_pack_10'])+int(line['x_pack_12'])		
				elif _obj.x_dcs_group=="P275":
					p275=p275+int(line['x_pack_12'])		
		return {'value': {'pack_110': p110,'pack_155': p155,'pack_200': p200,'pack_275': p275}}
		
	def write(self, cr, uid, ids, vals, context=None):
		res = super(dincelmrp_mrp, self).write(cr, uid, ids, vals, context=context)
		for record in self.browse(cr, uid, ids):
			sql = "SELECT sum(coalesce(x_pack_10,0)+coalesce(x_pack_12,0)+coalesce(x_pack_14,0)+coalesce(x_pack_20,0)) FROM mrp_production WHERE x_production_id='"+str(record.id)+"'"
			cr.execute(sql)
			rows = cr.fetchall()
			if len(rows) > 0:
				tot = rows[0][0]
				#_logger.error("dincelmrp_mrpdincelmrp_mrp["+str(sql)+"]")	
				if tot and int(tot)>0:
					sql = "UPDATE dincelmrp_production SET packs='%s' WHERE id='%s' " % (str(tot), str(record.id))
					cr.execute(sql)
			#_logger.error("dincelmrp_mrpdincelmrp_mrp11["+str(record.production_line)+"]")		
			
			production  = self.pool.get('mrp.production')
			actmove 	= self.pool.get('dincelaccount.journal.dcs')
			_oprod 		= self.pool.get('dincelproduct.product')
			for line in record.production_line:
				
				#_logger.error("dincelmrp_mrpdiproduction_lineproduction_x_est_minutex_est_minutene["+str(line.date_start)+"]["+str(dt_end)+"]["+str(est_mms)+"]")	
				if line.x_start_mo and line.state=="draft": #Note--> for the first time...
					qty		= 0
					est_mms = line.x_est_minute 
					dt_end  =  parser.parse(line.date_start) +  datetime.timedelta(minutes = est_mms)
					production.action_confirm(cr, uid, [line.id], context=context)		
					# / 60
					# timedelta(hours=est_hrs)#time.strftime('%Y-%m-%d %H:%M:%S')
					sql = "UPDATE mrp_production SET date_finished='%s',state='in_production',x_curr_produced_qty=0,x_produced_qty='%s' WHERE id='%s' " % (str(dt_end),str(qty), str(line.id))
					cr.execute(sql)
					actmove.mo_produce_start_journal_dcs(cr, uid, ids, line.id, context=context) #Note ->> WIP Journal
				if line.x_curr_produced_qty > 0:
					#if line.x_curr_produced_qty > 0:
					qty=line.x_curr_produced_qty
					curr_produced=qty
					if line.x_produced_qty:
						qty=qty+line.x_produced_qty
					if 	qty>line.x_order_qty:#---Note..some reasons more qty entered....then make the capping...
						qty=line.x_order_qty
						curr_produced=qty-line.x_produced_qty
					
					
					if curr_produced>0:	
						#sql ="UPDATE mrp_production SET x_curr_produced_qty=0,x_produced_qty=" +str(qty)+" WHERE id ='%s'" % (str(line.id))
						#cr.execute(sql)
						#_crit="x_curr_produced_qty=0,x_produced_qty=" +str(qty)+""
						
				#if line.x_full_mo==True:
				#	if line.state!="done":
						data 	= production.browse(cr, uid, line.id, context=context)
						if line.state=="draft":
							#_logger.error("dincelmrp_mrpdincelmrp_mrp2222["+str(line.id)+"]")	
							sql = "UPDATE mrp_production SET date_start='%s',x_curr_produced_qty=0,x_produced_qty='%s' WHERE id='%s' " % (str(time.strftime('%Y-%m-%d %H:%M:%S')),str(qty), str(line.id))
							cr.execute(sql)
						else:
							sql ="UPDATE mrp_production SET x_curr_produced_qty=0,x_produced_qty=%s WHERE id ='%s'" % (str(qty),str(line.id))
							cr.execute(sql)
						#-------------------------------------------------
						#actmove = self.pool.get('dincelaccount.journal.dcs')
						#return self.write(cr, uid, ids, {'state': 'in_production', 'date_start': time.strftime('%Y-%m-%d %H:%M:%S')})
						
						
						#-------------------------------------------------
						#production.action_in_production()
						#actmove = self.pool.get('dincelaccount.journal.dcs')
						#actmove.mo_produce_start_journal_dcs(cr, uid, ids, ids[0], context=context) 
						#return self.write(cr, uid, ids, {'state': 'in_production', 'date_start': time.strftime('%Y-%m-%d %H:%M:%S')})
						#actmove = self.pool.get('dincelaccount.journal.dcs')
						#------------------------------------------------
						#actmove.mo_produced_qty_journal_dcs(cr, uid, ids, line.id, line.product_qty, context=context) 	
						actmove.mo_produced_qty_journal_dcs(cr, uid, ids, line.id, line.product_qty, context=context) 	
						#Journal entry ----------------------	
						if line.product_id.x_prod_cat in['stocklength','customlength']:
							#_qty=(line.product_qty/(0.001*line.x_order_length))
							_qty_lm= curr_produced*0.001*line.x_order_length
						else:
							#_qty=line.product_qty
							_qty_lm=curr_produced
							
						if line.x_sale_order_id:
							_mtype="mo-sales"
						else:
							_mtype="mo-stock" #>>for stock only no sales assigned....
							#self.pool.get('dincelproduct.inventory').qty_increment(cr, uid, line.product_id.id, line.x_order_length, _qty, context = context)
							self.pool.get('dincelproduct.inventory').qty_increment(cr, uid, line.product_id.id, line.x_order_length, curr_produced, context = context)
							
						
						#_oprod.record_stock_mrp_new(cr, uid, line.id, line.product_id.id, line.product_qty, _qty, _mtype, context=context)
						_oprod.record_stock_mrp_new(cr, uid, line.id, line.product_id.id, _qty_lm, curr_produced, _mtype, context=context)
						
						#_oprod.record_stok_move(cr, uid, _objp.origin, product_id, _objp.product_uom.id, 'produced', data.product_qty, _objp.x_order_length, context=context)
						ctx = context.copy()
						ctx.update({'x_order_length': line.x_order_length})
						production_mode = 'consume_produce'
						wiz=False
						#_logger.error("action_create_mov_mov_ctxctxctx["+str(ctx)+"]")
						#raise osv.except_osv(_('Error'), _('TESTET'))
						#production.action_produce(cr, uid, line.id, data.product_qty, production_mode, wiz, context=ctx)
						production.action_produce(cr, uid, line.id, _qty_lm, production_mode, wiz, context=ctx)
						_mov_obj = self.pool.get('stock.move')
						_mids = _mov_obj.search(cr, uid, [('production_id', '=', line.product_id.id)], context=context)
						#for _mov in _mov_obj.browse(cr, uid, _mids, context=context):
						#	_logger.error("action_create_mov_mov_mo["+str(_mov)+"]")
						if _mids:	
							_mov_obj.write(cr, uid, _mids, {'x_order_length': line.x_order_length}, context=context)
						
						#------------------
						if line.state!="done" and qty==line.x_order_qty:
							#Note -->> mark as done....
							production.action_production_end(cr, uid, [line.id], context=context)
							#sql ="SELECT dcs_api_url FROM dincelaccount_config_settings";
							#cr.execute(sql)
							#rows = cr.fetchone()
							url=self.pool.get('dincelaccount.config.settings').get_dcs_api_url(cr, uid, ids, "mrpdone", data.x_sale_order_id.id, context=context)	
							if url:#rows and len(rows) > 0:
								#url= str(rows[0]) + "?act=mrpdone&id="+str(data.x_sale_order_id.id)
								#url="http://deverp.dincel.com.au/dcsapi/index.php??act=mrpdone&id="+str(ids[0])
								f 		 = urllib2.urlopen(url)
								response = f.read()
								str1	 = simplejson.loads(response)
								#@_logger.error("updatelink_order_dcs.updatelink_order_dcs["+str(str1)+"]["+str(response)+"]")
								item 	 = str1['item']
								status1	 = str(item['post_status'])
								dcs_refcode	= str(item['dcs_refcode'])
								if status1 != "success":
									#_logger.error("updatelink_order_dcs.updatelink_order_dcsordercode["+str(ordercode)+"]")	
									#sql ="UPDATE res_partner SET x_dcs_id='"+dcs_refcode+"' WHERE id='"+str(ids[0])+"'"
									#cr.execute(sql)
									#return True
									#else:
									if item['errormsg']:
										str1=item['errormsg']
									else:
										str1="Error while updating order at DCS."
									_logger.error("error.mrpdone.update_order_dcsordercode["+str(dcs_refcode)+"]["+str(str1)+"]")
								#raise osv.except_osv(_('Error'), _(''+str1 + ''))
						#if if line.state=="confirmed":
		return res		
		
	def onchange_order_id(self, cr, uid, ids, order_id, context=None):
		#if not part:
		#	return {'value': {'partner_invoice_id': False, 'partner_shipping_id': False,  'payment_term': False, 'fiscal_position': False}}

		so = self.pool.get('sale.order').browse(cr, uid, order_id, context=context)
		
		partner_id = so.partner_id and so.partner_id.id or False
		name = so.name or False
		
		val = {
			'partner_id': partner_id,
			'name': name,
			}
		 
		return {'value': val}
		
	def generate_mo_lines(self, cr, uid, ids, context=None):
		_obj 		= self.pool.get('sale.order')
		#for record in self.browse(cr, uid, ids):
	
	
	def production_start(self, cr, uid, ids, context=None):	
		if context is None:
			context = {}
		return {
			'type': 'ir.actions.act_window',
			'res_model': 'dincelmrp.produce',
			'view_type': 'form',
			'view_mode': 'form',
			#'res_id': ids[0],#'id_of_the_wizard',
			'context':{'default_production_id':ids[0]},
			'target': 'new',
		}	
		
	def acsreport_print_dcs(self, cr, uid, ids, context=None):	
		if context is None:
			context = {}
		#datas = {'ids': []}
		#datas['form']  = self.read(cr, uid, ids, context=context)[0]
		#return self.pool['report'].get_action(cr, uid, [], 'production.report_mo_pqreport', data=datas, context=context)	
		url=self.pool.get('dincelaccount.config.settings').report_preview_url(cr, uid, ids,"acs",ids[0],context=context)		
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
			   
	def acsreport_print_pdf_dcs(self, cr, uid, ids, context=None):	
		if context is None:
			context = {}
	
		ir_id = False 
		fname = False
		ir_attachement_obj=self.pool.get('ir.attachment')
		for record in self.browse(cr, uid, ids):
			fname="acs_"+str(record.id)+".pdf"
			if record.acspdf_attachs:
				
				try:
					ir_attachement_obj.unlink(cr, uid, [record.acspdf_attachs.id])
				except ValueError:
					ir_id = False #....
			#else:
				
			temp_path="/var/tmp/odoo/mrp/"+fname
			url=self.pool.get('dincelaccount.config.settings').report_preview_url(cr, uid, ids,"acs",record.id,context=context)	
			process=subprocess.Popen(["wkhtmltopdf", 
						'--margin-top','0', 
						'--margin-left','0', 
						'--margin-right','0', 
						'--margin-bottom','0', 
						url, temp_path],stdin=PIPE,stdout=PIPE)
			
			out, err = process.communicate()
			if process.returncode not in [0, 1]:
				raise osv.except_osv(_('Report (PDF)'),
									_('Wkhtmltopdf failed (error code: %s). '
									'Message: %s') % (str(process.returncode), err))
										
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
				_obj = self.pool.get('dincelmrp.production')  
				_obj.write(cr, uid, record.id, {'acspdf_attachs': ir_id})  
				
			except ValueError:
				ir_id = False #.......
		if ir_id and fname:
			return {
					'type' : 'ir.actions.act_url',
					'url': '/web/binary/saveas?model=ir.attachment&field=datas&filename_field=name&id=%s' % ( ir_id, ),
					'target': 'self',
				}
				
	def pqreport_print_dcs(self, cr, uid, ids, context=None):	
		if context is None:
			context = {}
		#datas = {'ids': []}
		#datas['form']  = self.read(cr, uid, ids, context=context)[0]
		#return self.pool['report'].get_action(cr, uid, [], 'production.report_mo_pqreport', data=datas, context=context)	
		url=self.pool.get('dincelaccount.config.settings').report_preview_url(cr, uid, ids,"pq",ids[0],context=context)		
		url+="&uid="+str(uid)
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
			   
	def pqreport_print_pdf_dcs(self, cr, uid, ids, context=None):	
		if context is None:
			context = {}
		#datas = {'ids': []}
		#datas['form']  = self.read(cr, uid, ids, context=context)[0]
		#return self.pool['report'].get_action(cr, uid, [], 'production.report_mo_pqreport_pdf', data=datas, context=context)	
		ir_id = False 
		fname = False
		ir_attachement_obj=self.pool.get('ir.attachment')
		for record in self.browse(cr, uid, ids):
			fname="pq_"+str(record.id)+".pdf"
			if record.pdf_attachs:
				#ir_id=record.pdf_attachs.id
				try:
					ir_attachement_obj.unlink(cr, uid, [record.pdf_attachs.id])
				except ValueError:
					ir_id = False #....
			#else:
				
			temp_path="/var/tmp/odoo/mrp/"+fname
			url=self.pool.get('dincelaccount.config.settings').report_preview_url(cr, uid, ids,"pq",record.id,context=context)	
			url+="&uid="+str(uid)
			process=subprocess.Popen(["wkhtmltopdf", 
						'--margin-top','0', 
						'--margin-left','0', 
						'--margin-right','0', 
						'--margin-bottom','0', 
						url, temp_path],stdin=PIPE,stdout=PIPE)
			
			out, err = process.communicate()
			if process.returncode not in [0, 1]:
				raise osv.except_osv(_('Report (PDF)'),
									_('Wkhtmltopdf failed (error code: %s). '
									'Message: %s') % (str(process.returncode), err))
										
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
				_obj = self.pool.get('dincelmrp.production')  
				_obj.write(cr, uid, record.id, {'pdf_attachs': ir_id})  
				
			except ValueError:
				ir_id = False #.......
		if ir_id and fname:
			return {
					'type' : 'ir.actions.act_url',
					'url': '/web/binary/saveas?model=ir.attachment&field=datas&filename_field=name&id=%s' % ( ir_id, ),
					'target': 'self',
				}
			
	def updatelink_production_dcs(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		
		#order_id = ids[0]
		#request = urllib.urlopen("http://deverp.dincel.com.au/dcsapi/")
		sql ="SELECT dcs_api_url FROM dincelaccount_config_settings";
		cr.execute(sql)
		rows = cr.fetchone()
		if rows and len(rows) > 0:
			url= str(rows[0]) + "?act=production&id="+str(ids[0])
			#url="http://deverp.dincel.com.au/dcsapi/index.php?id="+str(ids[0])
			f = urllib2.urlopen(url)
			response = f.read()
			str1= simplejson.loads(response)
			#@_logger.error("updatelink_order_dcs.updatelink_order_dcs["+str(str1)+"]["+str(response)+"]")
			item 		= str1['item']
			status1 	= str(item['post_status'])
			dcs_refcode = str(item['dcs_refcode'])
			if status1 == "success":
				#_logger.error("updatelink_order_dcs.updatelink_order_dcsordercode["+str(ordercode)+"]")	
				sql ="UPDATE dincelmrp_production SET dcs_refcode='"+dcs_refcode+"' WHERE id='"+str(ids[0])+"'"
				cr.execute(sql)
				return True
			else:
				if item['errormsg']:
					str1=item['errormsg']
				else:
					str1="Error while updating production quantity."
				raise osv.except_osv(_('Error'), _(''+str1))


		
class dincelmrp_production_reserve(osv.Model):
	_name = "dincelmrp.production.reserve"
	_columns={
 		'product_id': fields.many2one('product.product', 'Product'),
		'location_id': fields.many2one('stock.location', 'Source Location'),
		'warehouse_id': fields.many2one('stock.warehouse', 'Source Warehouse'),
		'order_length':fields.float("Length",digits_compute= dp.get_precision('Int Number')),
		'reserve_qty':fields.float("Reserve Qty",digits_compute= dp.get_precision('Int Number')),
		'production_id': fields.many2one('dincelmrp.production', 'Production Reference',ondelete='cascade',),
		'order_id': fields.many2one('sale.order', 'Sale Order'),
		'packs':fields.integer('Packs',size=2), 
		'pack_10':fields.integer('Pack 10',size=2), 
		'pack_12':fields.integer('Pack 12',size=2), 
		'pack_14':fields.integer('Pack 14',size=2), 
		'pack_20':fields.integer('Pack 20',size=2), 
		'pack_xtra':fields.integer('Extra',size=2), 
		'pack10a': fields.related('product_id', 'x_pack10', type='boolean', string='Pack 10 Active',store=False),
		'pack12a': fields.related('product_id', 'x_pack12', type='boolean', string='Pack 12 Active',store=False),
		'pack14a': fields.related('product_id', 'x_pack14', type='boolean', string='Pack 14 Active',store=False),
		'pack20a': fields.related('product_id', 'x_pack20', type='boolean', string='Pack 20 Active',store=False),
		'prod_group': fields.related('product_id', 'x_dcs_group', type='selection', selection=PROD_GROUP_SELECTION, readonly=True, store=True, string='Group'),
		'packed_by': fields.char('Packed By'),
		'packed_dt':fields.date('Packed Date'), 
		'checked_by': fields.char('Checked By'),
		'checked_dt':fields.date('Checked Date'), 
		'length_mm':fields.integer("Length (mm)"),
		'quantity': fields.integer('Qty (each)',help="Quantity for each, cause qty is sometimes recordes as L/M in case of stock/custome p1 products"),
		'state': fields.selection([
				('reserved', 'Reserve'), #for temporary stock count >> total reserve ===(reserve,packed)
				('packed', 'Packed'), #for temporary stock count
				('done', 'Move Done Delivered') 
				], 'Status'),
	}
	
	def _qty_available(self, cr, uid, _product_id, _locid,_len, _state, context=None):	
		_qty=0
		if _len:
			#_crit=[('product_id', '=', _product_id), ('location_id', '=', _locid), ('order_length', '=', _len), ('state', '=', _state)]
			_ids= self.search(cr, uid, [('product_id', '=', _product_id), ('location_id', '=', _locid), ('length_mm', '=', _len), ('state', '=', _state)], context)
		else:
			#_crit=[('product_id', '=', _product_id), ('location_id', '=', _locid), ('state', '=', _state)]
			_ids= self.search(cr, uid, [('product_id', '=', _product_id), ('location_id', '=', _locid), ('state', '=', _state)], context)
		for _item in self.browse(cr, uid, _ids, context):
			_qty+=int(_item.quantity)
		return _qty	
	
	#qty+1ty	
	def qty_reserved_total(self, cr, uid, _product_id, _locid,_len, context=None):	
		#_res= self._qty_available( cr, uid, _product_id, _locid, _len, 'reserved')		
		#_pak= self._qty_available( cr, uid, _product_id, _locid, _len, 'packed')		
		#return _res+_pak
		prod=self.pool.get("product.product")
		if _len and _len != None:
			_custom=True 
		else:
			_custom=False
		return prod.stock_reserve_qty(cr, uid, _product_id, _locid, _len, _custom, context=context)
		
	def qty_reserved(self, cr, uid, _product_id, _locid,_len, context=None):	
		prod=self.pool.get("product.product")
		if _len:
			_custom=True 
		else:
			_custom=False
		#return self._qty_available(cr, uid, _product_id, _locid, _len, 'reserved', context)	
		return prod.stock_reserve_qty(cr, uid, _product_id, _locid, _len, _custom, context=context)
		
	def qty_packed(self, cr, uid, _product_id, _locid,_len, context=None):	
		return self._qty_available(cr, uid, _product_id, _locid, _len, 'packed', context)	
		
	def qty_available_custom(self, cr, uid, _product_id, _len, _locid, context=None):	
		_qty=0
		_ids= self.search(cr, uid, [('product_id', '=', _product_id), ('x_order_length', '=', _len), ('location_id', '=', _locid)], context=context)
		for _item in self.browse(cr, uid, _ids, context):
			_qty+=int(_item.x_quantity)
		return _qty	
		
	def onchange_pack_qty(self, cr, uid, ids, qty, q10 = 0, q12 = 0, q14 = 0, q20 = 0, context = None):
		xtra=0
		en10=False
		en12=False
		en14=False
		en20=False
		qtynew=0
		for record in self.browse(cr, uid, ids):
			en10 = record.pack10a
			en12 = record.pack12a
			en14 = record.pack14a
			en20 = record.pack20a
		if en10:	
			qtynew += (q10*10)
		if en12:	
			qtynew += (q12*12)
		if en14:	
			qtynew += (q14*14)#+(q20*20)
		if en20:	
			qtynew += (q20*20)		
		
		if qtynew > qty:
			xtra=qty-qtynew#raise osv.except_osv(_('Error'), _('Invalid quantity found!'))
			#['+str(qtynew)+"]qty["+str(qty)+"]10["+str(q10)+"]12["+str(q12)+"]14["+str(q14)+"]20["+str(q20)+""))
		else:
			xtra=qty-qtynew
		return {'value': {'pack_xtra': xtra }} 
	
	
class dincelmrp_production(osv.Model):
	_inherit = "mrp.production"
	
	def get_total_lm(self, cr, uid, ids, values, arg, context):
		x={}
		for record in self.browse(cr, uid, ids):
			total_lm = record.x_order_length*record.x_order_qty*0.001
			x[record.id]=total_lm 
		return x
	
	
	def _remain_hrs_calc(self, cr, uid, ids, values, arg, context):
		x={}
		_mins=0
		for record in self.browse(cr, uid, ids):
			_lm = record.x_remain_qty * record.x_order_length * 0.001
			_speed = record.product_id.x_produce_speed
			if _speed and _speed > 0 and _lm:
				_mins = _lm / _speed
			x[record.id]=round((_mins/60),2) 
		return x
		
	def get_est_hrs(self, cr, uid, ids, values, arg, context):
		x={}
		_hh_mm=0
		for record in self.browse(cr, uid, ids):
			_mins = record.x_est_minute
			#if _mins:
				#_hh=int(_mins / 60)
				#_mm=int(_mins-(_hh*60))
				#_hh_mm=str(_hh) + ":" +str(_mm)
			x[record.id]=round((_mins/60),2) 
		return x
		
	def get_est_minute(self, cr, uid, ids, values, arg, context):
		x={}
		_mins=0
		for record in self.browse(cr, uid, ids):
			_lm = record.x_tot_lm
			_speed=record.product_id.x_produce_speed
			if _speed and _speed > 0 and _lm:
				_mins=_lm / _speed
			x[record.id]=_mins 
		return x
		
	def get_pack_xtra(self, cr, uid, ids, values, arg, context):
		x={}
		_qty=0
		qtynew=0
		for record in self.browse(cr, uid, ids):
			_qty = record.x_order_qty
			if _qty and _qty>0:
				#_logger.error("updatelink_order_dcs.product_idproduct_id["+str(record.product_id)+"]")	
			
				if record.product_id:
					if record.product_id.x_pack10 and record.x_pack_10:	
						qtynew+=(record.x_pack_10*10)
					if record.product_id.x_pack12 and record.x_pack_12:	
						qtynew+=(record.x_pack_12*12)
					if record.product_id.x_pack14 and record.x_pack_14:	
						qtynew+=(record.x_pack_14*14)+(q20*20)
					if record.product_id.x_pack20 and record.x_pack_20:	
						qtynew+=(record.x_pack_20*20)
			else:
				_qty=0
				
			x[record.id]=_qty- qtynew
		return x	
		
	'''def write(self, cr, uid, ids, vals, context=None):
		res = super(dincelmrp_production, self).write(cr, uid, ids, vals, context=context)
		 
		for record in self.browse(cr, uid, ids):
			if record.x_tree_edit:
				_logger.error("dincelmrp_productiondincelmrp_tree_edittree_edit1111111["+str(record.id)+"]["+str(record.x_curr_produced_qty)+"]")
			else:
				_logger.error("dincelmrp_productiondincelmrp_tree_edittree_edit00000000["+str(record.id)+"]["+str(record.x_curr_produced_qty)+"]")
		return res'''
	'''NONO.....issue on this if added....
	def write(self, cr, uid, ids, vals, context=None):
		res = super(dincelmrp_production, self).write(cr, uid, ids, vals, context=context)
		_qty=0
		qtynew=0
		_pack=False
		for record in self.browse(cr, uid, ids):
			_qty = record.x_order_qty
			if _qty and _qty>0:
				if record.product_id:
					if record.product_id.x_pack10 and record.x_pack_10:	
						qtynew+=(record.x_pack_10*10)
						_pack=True
					if record.product_id.x_pack12 and record.x_pack_12:	
						qtynew+=(record.x_pack_12*12)
						_pack=True
					if record.product_id.x_pack14 and record.x_pack_14:	
						qtynew+=(record.x_pack_14*14)+(q20*20)
						_pack=True
					if record.product_id.x_pack20 and record.x_pack_20:	
						qtynew+=(record.x_pack_20*20)
						_pack=True
			else:
				_qty=0
			
			if _pack==True:
				sql = "UPDATE mrp_production SET x_pack_xtra='%s' WHERE id='%s' " % (str(int(_qty-qtynew)), str(record.id))
				#_logger.error("dincelmrp_productiondincelmrp_production["+str(sql)+"]")
				cr.execute(sql)
		return res		'''
	def button_confirm_dcs(self, cr, uid, ids, context=None):	
		if context is None:
			context = {}
			
		record = self.browse(cr, uid, ids[0], context=context)
		production=self.pool.get('mrp.production')
		#line=production.browse(cr, uid, _id, context)
		actmove 	= self.pool.get('dincelaccount.journal.dcs')
		_oprod 		= self.pool.get('dincelproduct.product')
		if record.state=="draft": #Note--> for the first time...
			
			self.action_confirm(cr, uid, [record.id], context=context)		
			# / 60
			# timedelta(hours=est_hrs)#time.strftime('%Y-%m-%d %H:%M:%S')
			sql = "UPDATE mrp_production SET x_start_mo='True',x_curr_produced_qty=0,x_produced_qty='0' WHERE id='%s' " % (str(record.id))
			cr.execute(sql)
			actmove.mo_produce_start_journal_dcs(cr, uid, ids, record.id, context=context) #Note ->> WIP Journal
			
	def product_qty_change(self, cr, uid, ids, mo_type, order_length, order_qty, context=None):
		result = {}
		if mo_type=="manual":
			qty_lm=order_length*0.001*order_qty
			result['value'] = {'product_qty': qty_lm}
		return result
			
	def product_id_change_new(self, cr, uid, ids, mo_type, product_id, product_qty=0, context=None):
		result = self.product_id_change(cr, uid, ids, product_id, product_qty, context=context)
		#if mo_type=="manual":
		product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
		if product.x_stock_length:
			result['value']['x_order_length'] = product.x_stock_length
		return result	
		
	def onchange_pack_qty(self, cr, uid, ids, qty, q10 = 0, q12 = 0, q14 = 0, q20 = 0, context = None):
		xtra=0
		en10=False
		en12=False
		en14=False
		en20=False
		qtynew=0
		for record in self.browse(cr, uid, ids):
			en10 = record.x_pack10a
			en12 = record.x_pack12a
			en14 = record.x_pack14a
			en20 = record.x_pack20a
		if en10:	
			qtynew += (q10*10)
		if en12:	
			qtynew += (q12*12)
		if en14:	
			qtynew += (q14*14)#+(q20*20)
		if en20:	
			qtynew += (q20*20)		
		
		if qtynew > qty:
			xtra=qty-qtynew#raise osv.except_osv(_('Error'), _('Invalid quantity found!'))
			#['+str(qtynew)+"]qty["+str(qty)+"]10["+str(q10)+"]12["+str(q12)+"]14["+str(q14)+"]20["+str(q20)+""))
		else:
			xtra=qty-qtynew
		return {'value': {'x_pack_xtra': xtra }} 
	
	def _get_remain_qty(self, cr, uid, ids, values, arg, context):
		x={}
		for record in self.browse(cr, uid, ids):
			_qty = record.x_order_qty-record.x_produced_qty
			x[record.id]=_qty 
		return x
		
	_columns = {
		'x_order_length':fields.float("Length (mm)",digits_compute= dp.get_precision('Int Number')),
		'x_order_qty':fields.float("Qty (each)",digits_compute= dp.get_precision('Int Number')),
		'x_produced_qty':fields.float("Produced YTD",digits_compute= dp.get_precision('Int Number')),
		'x_remain_qty':fields.function(_get_remain_qty, method=True, string='Remain Qty',type='float',digits_compute= dp.get_precision('Int Number')),
		'x_curr_produced_qty':fields.float("Completed Qty",digits_compute= dp.get_precision('Int Number')),
		'x_dt_produced':fields.datetime("Produced Date"),#for capturing the production date...for bi reports...cause stop date is erp auto...if partial production this is handy..todo...need to create production log table as well.... in future
		'x_full_mo':fields.boolean('All Complete'),
		'x_start_mo':fields.boolean('Started'),
		'x_tree_edit':fields.boolean('Tree Edit'),
		'x_scheduled':fields.boolean('Scheduled'), #help if scheduled by Michael.Admin then enabled this flag(by schedle task.cronjob)
		'x_reserve_qty':fields.float("Reserve Qty",digits_compute= dp.get_precision('Int Number')),
		'x_production_id': fields.many2one('dincelmrp.production', 'Production Reference',ondelete='cascade',),
		'x_schedule_id': fields.many2one('dincelmrp.schedule', 'Schedule Reference'),
		'x_region_id': fields.many2one('dincelaccount.region', 'A/c Region'),
		'x_coststate_id':fields.many2one("res.country.state","Cost Centre"),
		'x_sale_order_id': fields.many2one('sale.order','Sale Order Reference'),
		'x_partner_id':fields.related('x_sale_order_id', 'partner_id', string="Partner", type="many2one", relation="res.partner", store=False),
		'x_project_id':fields.related('x_sale_order_id', 'x_project_id', string="Project", type="many2one", relation="res.partner", store=False),
		'x_order_code': fields.related('x_sale_order_id', 'origin', type='char', string='DCS Code',store=False),
		'x_color_code': fields.related('x_sale_order_id', 'x_colorcode', type='char', string='Color',store=False),
		'x_pack_10':fields.integer('Pack 10',size=2), 
		'x_pack_12':fields.integer('Pack 12',size=2), 
		'x_pack_14':fields.integer('Pack 14',size=2), 
		'x_pack_20':fields.integer('Pack 20',size=2), 
		'x_pack_xtra':fields.integer('Extra',size=2), 
		#'x_xtra_pk':fields.function(get_pack_xtra, method=True, string='Pack Extra',type='float'),#'Pack Extra',size=2), 
		'x_pack10a': fields.related('product_id', 'x_pack10', type='boolean', string='Pack 10 Active',store=False),
		'x_pack12a': fields.related('product_id', 'x_pack12', type='boolean', string='Pack 12 Active',store=False),
		'x_pack14a': fields.related('product_id', 'x_pack14', type='boolean', string='Pack 14 Active',store=False),
		'x_pack20a': fields.related('product_id', 'x_pack20', type='boolean', string='Pack 20 Active',store=False),
		'x_tot_lm':fields.function(get_total_lm, method=True, string='L/M',type='float'),
		'x_est_minute':fields.function(get_est_minute, method=True, string='Est Minutes',type='float'),
		'x_est_hrs':fields.function(get_est_hrs, method=True, string='Est Hrs',type='float'),#char'),
		'x_remain_hrs':fields.function(_remain_hrs_calc, method=True, string='Remain Hrs',type='float'),#char'),
		'x_prod_group': fields.related('product_id', 'x_dcs_group', type='selection', selection=PROD_GROUP_SELECTION, readonly=True, store=True, string='Group'),
		'x_mo_type':fields.selection([
			('manual', 'Manual'),
			('order', 'Order'),
			], 'MO Type'),
	}
	_defaults = {
		'x_order_length': 0,
		'x_scheduled':False,
		'x_order_qty': 0,
		'x_reserve_qty': 0,
		'x_pack_10': 0,
		'x_pack_12': 0,
		'x_pack_14': 0,
		'x_pack_20': 0,
		'x_produced_qty': 0,
		'x_curr_produced_qty': 0,
		'x_mo_type': 'order',
	}
	
	_order = 'id desc'
	
	def unlink(self, cr, uid, ids, context=None, check=True):
		context = dict(context or {})
		if context is None:
			context = {}
		#_del=True	
		prod_status=''
		for record in self.browse(cr, uid, ids):
			#order_id= record.x_sale_order_id.id
			sql="select 1 from  dincelmrp_schedule  where  order_id='%s' and state in ('part','complete','printed')" %(record.x_sale_order_id.id)
			cr.execute(sql)
			rows = cr.fetchall()
			if(len(rows) > 0):
				prod_status="part"
		if prod_status and prod_status in ['part','complete','printed']:
			#_del=False
			raise osv.except_osv(_('Error!'), _('You cannot delete MRP after it has been printed, or produced partially or in full.'))
			#raise Warning(_('You cannot delete MRP after it has been produced partially or in full.'))
		else:#if _del:	 
			result = super(dincelmrp_production, self).unlink(cr, uid, ids, context)
			return result
			
	def calc_packs_275(self, cr, uid,  qty, context):
		 pack12	= int(qty / 12)
		 ext	= qty-(pack12*12)
		 return pack12, ext
		 
	def calc_packs_155(self, cr, uid,  qty, context):
		 pack14	= int(qty / 14)
		 ext	=qty-(pack14*14)
		 return pack14, ext
		 
	def calc_packs_110(self, cr, uid,  qty, context):
		 pack20	= int(qty / 20)
		 ext	= qty-(pack20*20)
		 return pack20, ext
	def calc_packs_200(self, cr, uid,  qty, context):
		qty10	=int(float(qty)/2.2)
		qty12	=qty-qty10
		packs12	=int(qty12 / 12)
		packs10	=int(qty10 / 10)
		ext		=qty-(packs12*12+packs10*10)
		if ext > 11:
			if packs10 < packs12:
				packs10 +=1
			else:
				packs12 +=1
		elif ext > 9:
			packs10 +=1
			
		ext		=qty-(packs12*12+packs10*10)	
			 
		return packs10, packs12, ext
		 
		 
	def onchange_full_mo(self, cr, uid, ids, full_mo, qty, context=None):
		#qty=0
		#vals = {'amount': 0.0}
		vals = { 'x_curr_produced_qty': 0}
		if full_mo:
			vals['x_curr_produced_qty']=qty
		
		return {'value': vals}
		
	def action_confirm_wip_journal(self, cr, uid, ids, context=None):
		actmove = self.pool.get('dincelaccount.journal.dcs')
		actmove.mo_produce_start_journal_dcs(cr, uid, ids, ids[0], context=context) 
		return True
		#return res
		
	def button_produce_item(self, cr, uid, ids, context=None):
		if context is None:
			context = {}	 
		#_logger.error("invoice_sales_validate.view_id["+str(view_id)+"]")
		mrp=self.pool.get('mrp.production').browse(cr, uid, ids[0], context=context)
		value = {
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'dincelmrp.stock.produce',
			'type': 'ir.actions.act_window',
			'context':{'default_mrp_id':ids[0],
						'default_product_id': mrp.product_id.id,
						'default_ordered_qty': mrp.x_order_qty,
						'default_stock_length': mrp.x_order_length,
						'default_produced_qty_ytd':mrp.x_produced_qty,
						'default_produced_qty':mrp.x_order_qty-mrp.x_produced_qty,
						'default_qty_lm': mrp.product_qty,
						'default_is_other': True, #other than Acs/Panel production e.g. Blended matrrials
						},
			'target': 'new',
		}
		return value
		
	def button_produce_dcs(self, cr, uid, ids, context=None):
		if context is None:
			context = {}	 
		#_logger.error("invoice_sales_validate.view_id["+str(view_id)+"]")
		mrp=self.pool.get('mrp.production').browse(cr, uid, ids[0], context=context)
		value = {
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'dincelmrp.stock.produce',
			'type': 'ir.actions.act_window',
			'context':{'default_mrp_id':ids[0],
						'default_product_id': mrp.product_id.id,
						'default_ordered_qty': mrp.x_order_qty,
						'default_stock_length': mrp.x_order_length,
						'default_produced_qty_ytd':mrp.x_produced_qty,
						'default_produced_qty':mrp.x_order_qty-mrp.x_produced_qty,
						'default_qty_lm': mrp.product_qty,
						},
			'target': 'new',
		}
		return value
		
	def button_produce_start_dcs(self, cr, uid, ids, context=None):
		_obj = self.pool.get('mrp.production').browse(cr, uid, ids[0], context=context)
		#_obj.action_confirm()
		#_obj.action_assign()
		#_obj.force_production()
		#actmove = self.pool.get('dincelaccount.journal.dcs')
		#actmove.mo_produce_start_journal_dcs(cr, uid, ids, ids[0], context=context) 
		return _obj.action_in_production()

class dincelmrp_order_line(osv.Model):
	_inherit = "sale.order.line"
	_columns = {
		'x_has_mrp': fields.boolean('has mrp'),
		
	}
	_defaults = {
		'x_has_mrp': False,
	}
	
	def _prepare_mrp_order_line(self, cr, uid, line, dt=False, context=None):

		res = {}
		if not dt:
			dt = datetime.datetime.now()
		name =self.pool.get('ir.sequence').get(cr, uid, 'mrp.production') or '/'#self.pool.get('ir.sequence').get('mrp.production') or '/'	
		res = {
			'name': name,
			'date_planned':dt,
			'origin': line.order_id.name,
			'product_qty': line.x_order_qty or 0.0,
			'product_id': line.product_id.id or False,
			'product_uom':line.product_uom.id,
			'x_order_length':line.x_order_length or 0.0,
		}
		
		bom_obj = self.pool.get('mrp.bom')
		#product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
		#bom_id = bom_obj._bom_find(cr, uid, product_id=line.product_id.id, properties=[], context=context)
		bom_id 	= bom_obj.search(cr, uid, [('product_tmpl_id', '=', line.product_id.product_tmpl_id.id)], limit=1) 	
		#routing_id = False
		#_logger.error("_prepare_mrp_order_line_prepare_mrp_order_line["+str(line.product_id.product_tmpl_id.id)+"]["+str(bom_id)+"]")
		if bom_id:
			bom_point 	= bom_obj.browse(cr, uid, bom_id[0], context=context)
			routing_id 	= bom_point.routing_id.id or False
			res['bom_id']=bom_id[0]
			if routing_id:
				res['routing_id']=routing_id	
		return res
		
	def mrp_line_create(self, cr, uid, ids, dt =False, context=None):
		if context is None:
			context = {}

		create_ids = []
		# sales = set()
		for line in self.browse(cr, uid, ids, context=context):
			vals = self._prepare_mrp_order_line(cr, uid, line, dt, context)
			if vals:
				inv_id = self.pool.get('mrp.production').create(cr, uid, vals, context=context)
				self.write(cr, uid, [line.id], {'x_has_mrp': True}, context=context)
				#sales.add(line.order_id.id)
				create_ids.append(inv_id)
		# Trigger workflow events
		#for sale_id in sales:
		#    workflow.trg_write(uid, 'sale.order', sale_id, cr)
		return create_ids

class dincelmrp_saleorder(osv.Model):
	_inherit = "sale.order"	
	
	def _remain2mo(self, cr, uid, ids, values, arg, context):
		x={}
		_remain=False
		for record in self.browse(cr, uid, ids):
			for line in record.order_line:
				qty_order=line.x_order_qty
				qty_already=0
				qty2produce=qty_order
				if line.product_id and line.product_id.x_prod_cat in['stocklength','customlength','accessories']:
					sql ="select sum(x_order_qty) from mrp_production where product_id='"+str(line.product_id.id)+"' and x_sale_order_id ='"+str(record.id)+"'"
					sql2reserve ="select sum(qty_origin) from stock_move_tmp where state='reserve' and product_id='"+str(line.product_id.id)+"' and order_id ='"+str(record.id)+"'"
					if line.product_id.x_prod_cat in['stocklength','customlength']:#line.product_id.x_prod_cat=="customlength":
						_obj=	self.pool.get('dincelproduct.product')
						_id = 	_obj.search(cr, uid, [('product_id', '=', line.product_id.id), ('product_len', '=', line.x_order_length)], limit=1)
						if _id:
							_obj 	=  _obj.browse(cr, uid, _id[0])
							sql  =sql + " and x_order_length='"+str(round(line.x_order_length))+"'"
							sql2reserve =sql2reserve + " and order_length='"+str(round(line.x_order_length))+"'"
							#_logger.error("_prepare_mrp_order_line_prepare_sql2reservesql2reservesql2reserve["+str(sql2reserve)+"]")
					cr.execute(sql)
					res = cr.fetchone()
					if res and res[0]!= None: #Note -- >from scheduled  qty (no matter produced or not...)
						qty_already=(res[0])
					else:
						qty_already=0
					cr.execute(sql2reserve)
					res1 = cr.fetchone()	 # 
					if res1 and res1[0]!= None: #Note -- >from inventory stock reserve qty
						qty_already+=(res1[0])

					if qty_already>0:	
						qty2produce=qty_order-qty_already
					
					if qty2produce>0:
						_remain = True
						#_logger.error("_prepare_mrp_order_lineqty2produceqty2produceqty2produce["+str(qty2produce)+"]["+str(line.product_id.id)+"]")
				 
			x[record.id] = _remain 
		return x
		
	_columns = {
		'x_has_mrp': fields.boolean('has mrp'),
		'x_acs_lines_dcs':fields.one2many('dincelmrp.accessories', 'order_id', 'Acs Lines',ondelete='cascade',),
		'x_mrp_lines_dcs':fields.one2many('dincelmrp.production', 'order_id', 'MRP Lines',ondelete='cascade',),
		'x_mrp_schedule_ids':fields.one2many('dincelmrp.schedule', 'order_id', 'Production Schedules',ondelete='cascade',),
		'x_remain2mo': fields.function(_remain2mo, method=True, string='Has Remain2MO?', type='boolean'),
	}
	_defaults = {
		'x_has_mrp': False,
	}
	
	def button_schedule_delivery(self, cr, uid, ids, context=None):
		obj = self.pool.get('sale.order').browse(cr, uid, ids[0], context=context)
		if obj.state in ['done','cancel']:
			raise osv.except_osv(_('Forbbiden delivery'), _('The order is already closed/cancelled.'))	
		else:
			return {
				'type': 'ir.actions.act_window',
				'res_model': 'dincelmrp.schedule.delivery',
				'view_type': 'form',
				'view_mode': 'form',
				#'res_id': 'id_of_the_wizard',
				'context':{'default_order_id': ids[0], 'default_pudel': obj.x_pudel},
				'target': 'new',
			}
			
	def is_over_limit_bythisorder(self, cr, uid, ids, _id, context=None):
		#in delivery schedule.....
		data = self.browse(cr, uid, _id, context=context)
		o_ids=[]
		pay_term = data.payment_term.x_payterm_code
		proceed = 0
		if(pay_term == 'COD'):
			proceed = 1
		else:
			
			#partner_id 			= data.partner_id.id
			credit_limit 		= data.x_credit_limit
			openinvoice_value	= data.partner_id.x_openinvoice_value 
			openorder_value		= data.x_tot_balance
			
			res = float(credit_limit) - (float(openinvoice_value) + float(openorder_value))
			
				
			if(res > 0.1):
				proceed = 1
			else:
				proceed = 0
			#else:
			#proceed = 1
		return proceed, o_ids#,o_names	
		
	def is_over_limit_ok(self, cr, uid, ids, _id, context=None):
		data = self.browse(cr, uid, _id, context=context)
		#data = self.browse(cr, uid, ids[0], context=context)
		o_ids=[]
		#o_names=[]
		pay_term = data.payment_term.x_payterm_code

		proceed = 0
		if(pay_term == 'COD'):
			proceed = 1
		else:
			balance 		= 0.0
			invoiced_this	= 0.0
			balance_other	= 0.0 
			partner_id 		= data.partner_id.id
			credit_limit 	= data.x_credit_limit
			#openorder_value	= data.x_openorder_value 
			openinvoice_value=data.partner_id.x_openinvoice_value 
			openorder_value, o_ids=self.pool.get("res.partner").get_open_order_info(cr, uid, ids, partner_id, context=context)
			res = float(credit_limit) - (float(openinvoice_value) + float(openorder_value))
			
			'''
			delivery="0"
			if 'delivery' in context:	
				delivery=str(context['delivery'])
				
			#inv_date 		= fields.date.context_today(self, cr, uid, context=context)
			
			_ids	= "'%s'" % (data.id)
			o_ids.append(data.id)
			'-'-' As inv_date is not relavant here so, commented out below...
			sql = """SELECT a.id as inv_id, a.amount_total,a.x_sale_order_id FROM account_invoice a left join sale_order o on a.x_sale_order_id = o.id left join res_partner p on a.x_project_id = p.id 
						where a.state not in('draft','cancel') and a.partner_id ='%s' and a.date_invoice <='%s'""" %(partner_id,inv_date)'-'-'
			sql="""select id,amount_total,x_del_status from sale_order 
					where partner_id ='%s' and state not in ('cancel','done')  """ % (partner_id)
			cr.execute(sql)
			rows = cr.dictfetchall()
			for row in rows:
				amt = float(row['amount_total'])
				sale_order_id=row['id']		
				sql="select a.id as inv_id,a.amount_total,a.x_sale_order_id from account_invoice a where a.state not in('draft','cancel') and a.x_sale_order_id='%s' " % (sale_order_id)
				cr.execute(sql)
				rows1 = cr.dictfetchall()
				for row1 in rows1:
					amt2 = float(row1['amount_total'])
					#sale_order_id=row['x_sale_order_id']
		
					amt_paid = 0
					sql_line = """select sum(p.amount) as amt_paid from dincelaccount_voucher_payline p,account_invoice a,account_voucher v where a.id = p.invoice_id and p.voucher_id=v.id and p.invoice_id='%s'""" %(row1['inv_id'])
					cr.execute(sql_line)
					rows_line = cr.dictfetchall()
					for row_line in rows_line:
						if(row_line['amt_paid']):
							amt_paid = float(row_line['amt_paid'])
							
					if sale_order_id and sale_order_id == data.id:
						bal=0
						invoiced_this=invoiced_this+(amt2 - amt_paid)
					else:	
						
						bal = amt2 - amt_paid #eg check >>S3448/  S5888[6610]
						if(bal and abs(bal)>0.1):
							balance = balance + bal
							if sale_order_id:
								if str(sale_order_id) not in _ids:
									_ids += ",'%s'" % (sale_order_id)
									o_ids.append(sale_order_id)
			'-'-'						
			sql = """SELECT a.id as inv_id, a.amount_total,a.x_sale_order_id 
					FROM account_invoice a left join sale_order o on a.x_sale_order_id = o.id left join res_partner p on a.x_project_id = p.id 
						where a.state not in('draft','cancel') and a.partner_id ='%s' """ %(partner_id)			
			cr.execute(sql)
			rows = cr.dictfetchall()
			for row in rows:
				amt = row['amount_total']
				sale_order_id=row['x_sale_order_id']
	
				amt_paid = 0
				sql_line = """select sum(p.amount) as amt_paid from dincelaccount_voucher_payline p,account_invoice a,account_voucher v where a.id = p.invoice_id and p.voucher_id=v.id and p.invoice_id='%s'""" %(row['inv_id'])
				cr.execute(sql_line)
				rows_line = cr.dictfetchall()
				for row_line in rows_line:
					if(row_line['amt_paid']):
						amt_paid = float(row_line['amt_paid'])
						
				if sale_order_id and sale_order_id == data.id:
					bal=0
					invoiced_this=invoiced_this+(amt - amt_paid)
				else:	
					
					bal = amt - amt_paid
					if(bal and abs(bal)>0.1):
						balance = balance + bal
						if sale_order_id:
							if str(sale_order_id) not in _ids:
								_ids += ",'%s'" % (sale_order_id)
								o_ids.append(sale_order_id)
								'-'-'
			#if(credit_limit):
			#select * from sale_order where   partner_id='55457' and id not in (select distinct x_sale_order_id from account_invoice where partner_id='55457' and x_sale_order_id is not null)
			#_logger.error("_is_ready_for_mrp000["+str(credit_limit)+"]["+str(balance)+"]["+str(pay_term)+"]")
			
			sql="""select id,amount_total,x_del_status from sale_order 
					where partner_id ='%s' and state not in ('cancel','done') and 
					id not in(select distinct x_sale_order_id from account_invoice where partner_id='%s' and x_sale_order_id is not null)   """ %(partner_id,partner_id)
			cr.execute(sql)
			rows = cr.fetchall()
			for row in rows:
				if row[0] and row[1]:
					if str(row[0]) not in _ids:
						if delivery=="1":
							if row[2] and str(row[2]) in ["part","delivered"]:
								balance_other += float(row[1])
								#_ids += ",'%s'" % (row[0])
								o_ids.append(row[0])
						else:
							balance_other += float(row[1])
							#_ids += ",'%s'" % (row[0])
							o_ids.append(row[0])
			#to calculate the current value + outstanding balance
			balance_this=data.amount_total - invoiced_this #(if any invoiced this...)
			#_logger.error("_is_ready_for_sqlsqlsql["+str(sql)+"]_ids["+str(_ids)+"]["+str(o_ids)+"]["+str(balance_this)+"]["+str(balance_other)+"]")
			res = float(credit_limit) - float(balance) - float(balance_this) - float(balance_other)
			'''
			if(res > 0.1):
				proceed = 1
			else:
				proceed = 0
			#else:
			#proceed = 1
		return proceed, o_ids#,o_names	
		
	def _is_ready_for_mrp(self, cr, uid, ids, context=None):
		'''
		
		partner_id = data.partner_id.id
		credit_limit = data.x_credit_limit
		pay_term = data.payment_term.x_payterm_code
		inv_date = fields.date.context_today(self, cr, uid, context=context)
		balance = 0.0
		proceed = 0
		
		invoiced_this=0.0
		sql = """SELECT a.id as inv_id, a.amount_total,a.x_sale_order_id FROM account_invoice a left join sale_order o on a.x_sale_order_id = o.id left join res_partner p on a.x_project_id = p.id 
					where a.state not in('draft','cancel') and a.partner_id ='%s' and a.date_invoice <='%s'""" %(partner_id,inv_date)
		cr.execute(sql)
		rows = cr.dictfetchall()
		for row in rows:
			amt = row['amount_total']
			sale_order_id=row['x_sale_order_id']
			amt_paid = 0
			sql_line = """select sum(p.amount) as amt_paid from dincelaccount_voucher_payline p,account_invoice a,account_voucher v where a.id = p.invoice_id and p.voucher_id=v.id and p.invoice_id='%s'""" %(row['inv_id'])
			cr.execute(sql_line)
			rows_line = cr.dictfetchall()
			for row_line in rows_line:
				if(row_line['amt_paid']):
					amt_paid = float(row_line['amt_paid'])
			if sale_order_id==data.id:
				bal=0
				invoiced_this=invoiced_this+(amt - amt_paid)
			else:			
				bal = amt - amt_paid
			if(bal and abs(bal)>0.1):
				balance = balance + bal
		#if(credit_limit):
		#_logger.error("_is_ready_for_mrp000["+str(credit_limit)+"]["+str(balance)+"]["+str(pay_term)+"]")
		if(pay_term != 'COD'):
			#to calculate the current value + outstanding balance
			balance_this=data.amount_total - invoiced_this #(if any invoiced this...)
			res = float(credit_limit) - float(balance) - float(balance_this)
			if(res > 0.1):
				proceed = 1
			else:
				proceed = 0
		else:
			proceed = 1
		'''
		#_logger.error("_is_ready_for_mrp11 proceed["+str(proceed)+"]["+str(credit_limit)+"]["+str(balance)+"]["+str(balance_this)+"]")
		proceed, o_ids =self.is_over_limit_ok(cr, uid, ids, ids[0], context=context)
		if(proceed==0):
			#return True
			#else:
			data = self.browse(cr, uid, ids[0], context=context)
			if data.x_authorise_mrp==False:
				return False, o_ids	
			#else:
		return True, o_ids 
		
	def button_schedule_mo(self, cr, uid, ids, context=None):
		res, o_ids=self._is_ready_for_mrp(cr, uid, ids, context)
		if res:
			so=self.pool.get('sale.order')
			chk=so.check_discount_allowed(cr, uid, ids, ids[0]) 
			if chk==-1 or chk==1:
				if chk==-1:
					type="credit"
				else:
					type="discount"
				return so.open_popup_approve_request(cr, uid, ids[0],type, None, context)
			
			return {
				'type': 'ir.actions.act_window',
				'res_model': 'dincelmrp.schedule.mrp',
				'view_type': 'form',
				'view_mode': 'form',
				#'res_id': 'id_of_the_wizard',
				'context':{'default_order_id':ids[0]},
				'target': 'new',
			}
		else:	
			type="mrp"
			context = context.copy()
			context['o_ids']=o_ids
			#context['o_names']=o_names
			return self.pool.get('sale.order').open_popup_approve_request(cr, uid, ids[0],type,None, context)
			#raise osv.except_osv(_('CREDIT LIMIT EXCEEDED'), _('The customer has outstanding balance to pay which is over their credit limit. So, MO could not be scheduled at the moment.'))	
		 
		
	def get_mrp_mo_lines(self, cr, uid, ids, context=None):
		obj_sale_order_line = self.pool.get('sale.order.line')
		partner_currency = {}

		obj_mrp = self.pool.get('mrp.production')

		for o in self.browse(cr, uid, ids, context=context):
			lines = []
			for line in o.order_line:
				_cat	=line.product_id.x_prod_cat
				if (line.x_has_mrp == False) and (_cat == None or _cat in['stocklength','customlength','accessories']):
					lines.append(line.id)
				
					
			created_lines = obj_sale_order_line.mrp_line_create(cr, uid, lines,date_invoice)		
			self.write(cr, uid, [o.id], {'x_has_mrp': True}, context=context)
		return res
		
	def action_create_mrp_mo(self, cr, uid, ids, grouped=False, states=None, date_invoice = False, context=None):
		#if states is None:
		#	states = ['confirmed', 'done', 'exception']
		res = False
		
		obj_sale_order_line = self.pool.get('sale.order.line')
		partner_currency = {}

		obj_mrp = self.pool.get('mrp.production')

		for o in self.browse(cr, uid, ids, context=context):
			#currency_id = o.pricelist_id.currency_id.id

			lines = []
			for line in o.order_line:
				#lines.append(line.id)
				_cat	= line.product_id.x_prod_cat
				#_logger.error("action_create_mrp_moaction_create_mrp_mo["+str(line.product_id.route_ids)+"]["+str(line.product_id.x_prod_cat)+"]")
				#if rec.state not in ['draft', 'cancel']:
				if (line.x_has_mrp == False) and (_cat == None or _cat in['stocklength','customlength','accessories']):
					#=="stocklength" or _cat=="customlength" or _cat=="accessories"):
					lines.append(line.id)
				#	#continue
				#elif (line.state in states):
				#else:
				#	lines.append(line.id)
					
			created_lines = obj_sale_order_line.mrp_line_create(cr, uid, lines, date_invoice)		
			self.write(cr, uid, [o.id], {'x_has_mrp': True}, context=context)
		return res
		
class dincelmrp_production_produce(osv.osv_memory):
	_inherit="mrp.product.produce"
	
	def do_produce_dcs(self, cr, uid, ids, context=None):
		production_id = context.get('active_id', False)
		assert production_id, "Production Id should be specified in context as a Active ID."
		data 	= self.browse(cr, uid, ids[0], context=context)
		
		_oprod 	= self.pool.get('dincelproduct.product')
		_obj	= self.pool.get('mrp.production')
		 
		if data.product_id:
			_objp		= _obj.browse(cr, uid, production_id, context=context)
			product_id 	= data.product_id.id
			
			#Journal entry ----------------------
			
			actmove = self.pool.get('dincelaccount.journal.dcs')
			actmove.mo_produced_qty_journal_dcs(cr, uid, ids, production_id, data.product_qty, context=context) 	
			#Journal entry ----------------------	
			if data.product_id.x_prod_cat in['stocklength','customlength']:
				_qty=(data.product_qty/(0.001*_objp.x_order_length))
			else:
				_qty=data.product_qty
				
			if _objp.x_sale_order_id:
				_mtype="mo-sales"
			else:
				_mtype="mo-stock" #>>for stock only no sales assigned....
				self.pool.get('dincelproduct.inventory').qty_increment(cr, uid, product_id, _objp.x_order_length, _qty, context = context)
				
			
			_oprod.record_stock_mrp_new(cr, uid, production_id, product_id, data.product_qty, _qty, _mtype, context=context)
			
			#_oprod.record_stok_move(cr, uid, _objp.origin, product_id, _objp.product_uom.id, 'produced', data.product_qty, _objp.x_order_length, context=context)
			ctx = context.copy()
			ctx.update({'x_order_length': _objp.x_order_length})
			
			#_logger.error("action_create_mov_mov_ctxctxctx["+str(ctx)+"]")
			raise osv.except_osv(_('Error'), _('TESTET'))
			_obj.action_produce(cr, uid, production_id, data.product_qty, data.mode, data, context=ctx)
			_mov_obj = self.pool.get('stock.move')
			_mids = _mov_obj.search(cr, uid, [('production_id', '=', production_id)], context=context)
			#for _mov in _mov_obj.browse(cr, uid, _mids, context=context):
			#	_logger.error("action_create_mov_mov_mo["+str(_mov)+"]")
			if _mids:	
				_mov_obj.write(cr, uid, _mids, {'x_order_length': _objp.x_order_length}, context=context)
			if _objp.x_sale_order_id:
				#UPdate completed length back to DCS
				sql ="SELECT dcs_api_url FROM dincelaccount_config_settings";
				cr.execute(sql)
				rows = cr.fetchone()
				if rows and len(rows) > 0:
					url= str(rows[0]) + "?act=mrpdone&id="+str(_objp.x_sale_order_id.id)
					#url="http://deverp.dincel.com.au/dcsapi/index.php??act=mrpdone&id="+str(ids[0])
					f 		 = urllib2.urlopen(url)
					response = f.read()
					str1	 = simplejson.loads(response)
					#@_logger.error("updatelink_order_dcs.updatelink_order_dcs["+str(str1)+"]["+str(response)+"]")
					item 	 = str1['item']
					status1	 = str(item['post_status'])
					dcs_refcode	= str(item['dcs_refcode'])
					if status1 != "success":
						#_logger.error("updatelink_order_dcs.updatelink_order_dcsordercode["+str(ordercode)+"]")	
						#sql ="UPDATE res_partner SET x_dcs_id='"+dcs_refcode+"' WHERE id='"+str(ids[0])+"'"
						#cr.execute(sql)
						#return True
						#else:
						if item['errormsg']:
							str1=item['errormsg']
						else:
							str1="Error while updating order at DCS."
						raise osv.except_osv(_('Error'), _(''+str1 + ''))
						#raise osv.except_osv(_('Error'), _(''+str1 + ' : '+str(status1)+'-'+str(production_id)))
			#if _objp.x_sale_order_id and _objp.state == "done":
			#	#actmove.mo_produced_completed_dcs(cr, uid, ids, production_id, context=context) 	
			#	self.pool.get('sale.order').write(cr, uid, [_objp.x_sale_order_id.id], {'x_prod_status': 'complete'}, context=context)//could not update due to concurrent update issue.
			#this above line makes _obj.move_lines as blank/cleares it all. so called as the end of the function.
			#cause mo_produced_qty_journal_dcs are dependent of "_obj.move_lines"
		return {}
		
	_columns = {
		'x_produce_qty':fields.float("Produce Qty"),
		'x_order_length':fields.float("Ordered Len"),
		'x_order_qty':fields.float("Ordered Qty"),
		'x_product_uom': fields.many2one('product.uom', 'Unit of Measure'),
	}
	
class dincelmrp_bom(osv.Model):
	_inherit = "mrp.bom"
	
	def button_update_cost(self, cr, uid, ids, context=None):
		
		for record in self.browse(cr, uid, ids):
			#product_id=record.product_id.id
			_tot=0
			for line in record.bom_line_ids:
				cost=line.product_id.standard_price
				qty=line.product_qty
				_tot += round((cost*qty),4)
				
			self.pool.get('product.product').write(cr, uid, [record.product_id.id], {'standard_price':_tot}, context=context)
	#'x_cost_price': fields.related('product_id', 'standard_price', type='float', string='Cost Price',store=False),
	#}
	_columns = {
		'x_cost_price': fields.related('product_id', 'standard_price', type='float', string='Standard Cost',store=False),
	}
	
class dincelmrp_bom_line(osv.Model):
	_inherit = "mrp.bom.line"
	_columns = {
		'x_cost_price': fields.related('product_id', 'standard_price', type='float', string='Standard Cost',store=False),
	}
		
	def onchange_product_id_dcs(self, cr, uid, ids, product_id, product_qty=0, context=None):
	
		res = {}
		if product_id:
			prod = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
			res['value'] = {
				'product_uom': prod.uom_id.id,
				'x_cost_price': prod.standard_price,
				'product_uos_qty': 0,
				'product_uos': False
			}
			if prod.uos_id.id:
				res['value']['product_uos_qty'] = product_qty * prod.uos_coeff
				res['value']['product_uos'] = prod.uos_id.id
		return res	
		