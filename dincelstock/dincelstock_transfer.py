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
import pytz
from datetime import timedelta
import openerp.addons.decimal_precision as dp
_logger = logging.getLogger(__name__)

			
class dincelstock_transfer(osv.Model):
	_name 			= "dincelstock.transfer"
	_inherit = ['mail.thread']
	#account_id		= None
	#company_id		= None
	#move_id			= None
	#partner_id		= None
	#name			= None
	#date			= None
	#period_id		= None
	
	_order = 'id desc'
	_description = 'Stock Transfer'
	
	def _mrp_missing(self, cr, uid, ids, values, arg, context):
		x={}
		_missing=False
		for record in self.browse(cr, uid, ids):
			if record.order_id:
				_missing = self.pool.get("sale.order").mrp_missing_found(cr, uid, ids, record.order_id.id, context) 
			x[record.id]=  _missing 
		return x
	 
		
	def _get_default_company(self, cr, uid, context=None):
		company_id = self.pool.get('res.users')._get_company(cr, uid, context=context)
		if not company_id:
			raise osv.except_osv(_('Error!'), _('There is no default company for the current user!'))
		return company_id
		
	_columns = {
		'name': fields.char('Reference'),
		'origin': fields.char('Source Document', help="Reference of the document that generated this picking list."),
		'type': fields.selection([
			('order', 'Order'),
			('manual', 'Manual'),
			],'Type'),
		'state': fields.selection([
			('draft', 'Draft'),
			('cancel', 'Cancelled'),
			('printed', 'Printed'),
			('sent', 'Sent'),
			('done', 'Delivered'),
			], 'Status', track_visibility='onchange'),
		'date': fields.datetime('Date Pickup', required=True),
		'picking_id': fields.many2one('stock.picking', 'Picking'),#'stock.picking'
		'user_id': fields.many2one('res.users', 'Prepared By'),
		'date_received': fields.datetime('Date Received'),
		'all_location': fields.boolean('All Location'),
		'received_by': fields.many2one('res.users', 'Received By'),
		'picking_line': fields.one2many('dincelstock.transfer.line', 'transfer_id', 'Lines'),
		'move_line': fields.one2many('stock.move', 'x_transfer_id', 'Move Lines'),
		'note': fields.text('Note'),
		'mrp_missing': fields.function(_mrp_missing, method=True, string='MRP Missing/Mismatch',type='boolean'),
		'order_id': fields.many2one('sale.order', 'Origin Order',states={'printed': [('readonly', True)], 'done': [('readonly', True)]}),
		'order_code': fields.related('order_id', 'origin', type='char', string='DCS Code',store=False),
		'color_code': fields.related('order_id', 'x_colorcode', type='char', string='Color',store=False),
		'partner_id': fields.many2one('res.partner', 'Customer', domain=[('customer', '=', True),('x_is_project', '=', False)],states={'printed': [('readonly', True)], 'done': [('readonly', True)]}),
		'project_id': fields.many2one('res.partner', 'Project', domain=[('x_is_project', '=', True)],states={'printed': [('readonly', True)], 'done': [('readonly', True)]}),
		'company_id': fields.many2one('res.company', 'Company'),
		'source_location_id': fields.many2one('stock.location', 'Source Location'),
		'transit_location_id': fields.many2one('stock.location', 'Transit Location'),
		'destination_location_id': fields.many2one('stock.location', 'Destination Location'),
		'warehouse_id': fields.many2one('stock.warehouse','Source Warehouse'),	
		'destination_warehouse_id': fields.many2one('stock.warehouse','Destination Warehouse'),	
		'picking_type_id': fields.many2one('stock.picking.type', 'Picking Type', help="This will determine picking type of incoming shipment", required=True,
			states={'printed': [('readonly', True)], 'done': [('readonly', True)]}),
		'related_location_id': fields.related('picking_type_id', 'default_location_dest_id', type='many2one', relation='stock.location', string="Related location", store=True),
		'pudel':fields.selection([
			('pu','Pickup'),
			('del','Delivery'),
			], 'Pickup/Delivery'),
		'manifest_id': fields.many2one('dincelstock.ibt.manifest', 'IBT Manifest', ondelete='cascade'),	
	}	
	
	_defaults = {
		'date': fields.datetime.now,
		'company_id': _get_default_company,
		'state': 'draft',
		'type': 'manual',
		'user_id': lambda obj, cr, uid, context: uid,
		'name': lambda obj, cr, uid, context: '/',
		'all_location':False,
	}
	def create(self, cr, uid, vals, context=None):
		if vals.get('name','/')=='/':
			_name=self.pool.get('ir.sequence').get(cr, uid, 'stock.transfer') #stock.transfer
			vals['name'] =_name# self.pool.get('ir.sequence').get(cr, uid, 'quotation.number') or '/'
			t_ids = self.pool.get('stock.location').search(cr, uid, [('usage', '=', 'transit'),('active', '=', True)], context=context)
			#t_ids = self.pool.get('stock.location').search(cr, uid, [('loc_barcode', '=', 'TRANSIT2'),('active', '=', True)], context=context)
			if t_ids:
				vals['transit_location_id'] =t_ids[0]
			#else:
			#	vals['name'] = "lead"
		return super(dincelstock_transfer, self).create(cr, uid, vals, context=context)
		
	'''def write(self, cr, uid, ids, vals, context=None):
		context = context or {}
		if vals.get('type')=='order':
			for line in vals.get('picking_line'):#record.picking_line:
				if line.ship_qty>line.order_qty:
					raise osv.except_osv(_('Error!'), _('Invalid quantity found in shipment. %s %s ' % (line.ship_qty, line.order_qty)))	
		res=super(dincelstock_transfer, self).write(cr, uid, vals, context) #this will reflect current items in vals.
		#for record in self.browse(cr, uid, ids, context):
		#	if record.type=="order":
		#		for line in record.picking_line:
		#			if line.ship_qty>line.order_qty:
		#				raise osv.except_osv(_('Error!'), _('Invalid quantity found in shipment. %s %s ' % (line.ship_qty, line.order_qty)))
		#
		#res=super(dincelstock_transfer, self).write(cr, uid, vals, context)
		
		return res'''
		
			
	def onchange_location(self, cr, uid, ids, _all, context=None):
		if _all:
			domain  = {'destination_location_id': [('id','>', 0)],'source_location_id': [('id','>', 0)]}
		else:
			domain  = {'destination_location_id': [('usage', '=', 'internal')],'source_location_id': [('usage', '=', 'internal')]}
		return {'domain': domain}	
		
	def onchange_type(self, cr, uid, ids, _type, context=None):
		#if _type and _type=="order":
		return True	
	def onchange_origincode(self, cr, uid, ids, origincode, context=None):	
		result = self.pool.get('sale.order').search(cr, uid, [('origin', '=', str(origincode))], context=context)
		if result:
			order1	= self.pool.get('sale.order').browse(cr, uid, result[0], context=context)
			
			#_logger.error("onchange_origincodeonchange_origincode111["+str(result)+"]["+str(order1)+"]")
			
			if order1:
				partner_id=None	# so that load from >>order1.partner_id
				project_id=None # so that load from >>order1.project_id
				vals1=self.load_default_value(cr, uid, id,order1 ,partner_id, project_id)
				vals1['order_id']=order1.id
				return {'value': vals1}		
		#else:
		#	raise osv.except_osv(_('Error'), _('The similar client name already exists: \n'+str1 + '.'))
	def load_default_value(self,cr, uid, ids, order1,partner_id, project_id, context=None):
		new_lines=[] 
		for line in order1.order_line:
			if line.product_id.x_prod_cat not in['freight','deposit']:#='freight':	
				#order_length=line.x_order_length
				if line.product_id.x_prod_type and line.product_id.x_prod_type =="acs":
					acs=True 
				else:
					acs=False
				#if line.product_id.x_prod_cat not in['stocklength','customlength']:
				#	order_length = False
				location_id=False
				found=False
				for mrp in order1.x_mrp_lines_dcs:
					if found:
						break
					for reserve in mrp.reserve_line:
						if reserve.location_id:
							location_id=reserve.location_id.id
						if reserve.product_id.id == line.product_id.id:
							if acs==False:
								if reserve.order_length==line.x_order_length:
									found=True
									break
							else:
								found=True
								break
					if found==False:
						for pq in mrp.production_line:
							if pq.location_dest_id:
								location_id=pq.location_dest_id.id
							if pq.product_id.id == line.product_id.id:
								if pq.x_order_length==line.x_order_length:
									found=True
									break
				sql = """SELECT dl.order_qty, sum(dl.ship_qty) as total_ship from dincelstock_transfer dt 
						left join dincelstock_transfer_line dl on dt.id = dl.transfer_id 
						WHERE 
						dt.order_id = '%s' and dl.product_id = '%s' and dl.prod_length = '%s' 
						group by dl.order_qty""" %(order1.id, line.product_id.id, int(line.x_order_length))
				#_logger.error("onchange_origin_id11["+str(sql)+"]")
				cr.execute(sql)
				rows= cr.dictfetchall()
				rem_qty = 0
				ship = 0
				ord = 0
				if len(rows) > 0:
					for row in rows:
						if(row['total_ship'] != None):
							ship = int(row['total_ship'])
						if(row['order_qty'] != None):
							ord = int(row['order_qty'])
						rem_qty = ord - ship
				else:
					rem_qty = int(line.x_order_qty)
					
				vals = {
					'order_qty':line.x_order_qty,
					'product_id': line.product_id.id or False,
					'prod_length':line.x_order_length or 0.0,
					'name':line.product_id.name,
					'product_uom':line.product_id.uom_id.id,
					'qty_remain':rem_qty,
					'qty_remain_tmp':rem_qty,
					}
				if found and location_id:
					vals['location_id']=location_id
				new_lines.append(vals)
		vals1= {'picking_line': new_lines}	
		if not partner_id or not project_id: 	
			vals1['partner_id']  = order1.partner_id.id
			vals1['project_id']  = order1.x_project_id.id
		return vals1
	
	def onchange_origin_id(self, cr, uid, ids, origin_id,partner_id, project_id, _type, context=None):
		if origin_id:
			
			obj = self.pool.get('sale.order')
			order1 = obj.browse(cr, uid, origin_id, context=context)
			vals1=self.load_default_value(cr, uid, id,order1 ,partner_id, project_id)
			
			return {'value': vals1}		
			
	def onchange_partner_id(self, cr, uid, ids,partner_id, project_id, _type, is_contact ,  context=None):
		#if not partner_id:
		#	return {'value': { 'payment_term': False}}
		val = {}
		domain1={}
		order = self.pool.get('sale.order')
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
				return {'value': {'destination_location_id':_obj.lot_stock_id.id} , 'domain':domain1  }
		return True 
		
	
	def validate_stock_received(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		return self.mark_as_ibtreceived(cr, uid, ids, ids[0],context=context)	
		
	def validate_stock_receivedxx(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		move_obj = self.pool.get("stock.move")
		for pick in self.browse(cr, uid, ids, context=context):
			if pick.state=="progress":
				for item in pick.move_line:
					if item.state =="waiting":
						val1={
							"state": "done",
							}
						
						move_obj.write(cr, uid, [item.id], val1, context=context)		
			val1={
				"state": "done",
				}
			#_logger.error("onchange_product_unlinkunlink_state_val1val1["+str(val1)+"]")		
			self.pool.get('dincelstock.transfer').write(cr, uid, [pick.id], val1, context=context)			
		return True
		
	def button_print_docket(self, cr, uid, ids, context=None):
		if context is None:
			context = {}	
	 
	
		 
		for record in self.browse(cr, uid, ids):
			 
				
			fname="ibt_"+str(record.name)+".pdf"
			save_path="/var/tmp/odoo/docket/"
			temp_path=save_path+fname
			 
			url=self.pool.get('dincelaccount.config.settings').report_preview_url(cr, uid, ids,"docketibt",record.id,context=context)	
			
			
			 
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
			
			 
			return {
					'type' : 'ir.actions.act_url',
					'url': '/web/binary/download_file?model=dincelstock.transfer&field=datas&id=%s&path=%s&filename=%s' % (str(record.id),save_path,fname),
					'target': 'self',
				}
	def button_blank_loadsheet(self, cr, uid, ids, context=None):	
		if context is None:
			context = {}	
			
		fname="loadsheet_blank.pdf"
		save_path="/var/tmp/odoo/docket/"
		temp_path=save_path+fname
		record_id=0 
		url=self.pool.get('dincelaccount.config.settings').report_preview_url(cr, uid, ids,"loadsheetblank",record_id,context=context)	

		process=subprocess.Popen(["wkhtmltopdf",
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
		
		 
		return {
				'type' : 'ir.actions.act_url',
				'url': '/web/binary/download_file?model=dincelstock.transfer&field=datas&id=%s&path=%s&filename=%s' % (str(record_id),save_path,fname),
				'target': 'self',
			}
			
	def print_loadsheet_byorder(self, cr, uid, ids, order_id, context=None):	
		if context is None:
			context = {}	
		
		
				
	def button_print_loadsheet(self, cr, uid, ids, context=None):	
		if context is None:
			context = {}	
	 
	
		 
		for record in self.browse(cr, uid, ids):
			 
				
			fname="lsibt_"+str(record.name)+".pdf"
			save_path="/var/tmp/odoo/docket/"
			temp_path=save_path+fname
			 
			url=self.pool.get('dincelaccount.config.settings').report_preview_url(cr, uid, ids,"loadsheetibt",record.id,context=context)	
			#//url+="&loadsheetibt=1"
			
			#"--orientation",'landscape', 
			process=subprocess.Popen(["wkhtmltopdf",
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
			
			 
			return {
					'type' : 'ir.actions.act_url',
					'url': '/web/binary/download_file?model=dincelstock.transfer&field=datas&id=%s&path=%s&filename=%s' % (str(record.id),save_path,fname),
					'target': 'self',
				}
	
	def mark_as_ibtreceived(self, cr, uid, ids, _id,context=None):
		if context is None:
			context = {}
		todo_moves = []
		_date=None
		_type="ibtrx"
		stock_move = self.pool.get('stock.move')
		transfer = self.browse(cr, uid, _id, context=context)
		#for transfer in self.browse(cr, uid, ids, context=context):
		_date=transfer.date_received
		_jid = self.pool.get('dincelstock.journal').ibt_received_confirm(cr, uid, transfer.id, context)
		for _line in transfer.picking_line:
			if not _line.product_id:
				continue
			if _line.product_id.x_prod_cat not in['freight','deposit']:
				#if _line.product_id.type in ('product', 'consu'):
				if _line.ship_qty>0:
					_id2= self._create_stock_journal_ibtrx(cr, uid, transfer, _jid, _line, context)
					 
		
		 
		for line in transfer.picking_id.move_lines:
			todo_moves.append(line.id)	
		todo_moves = stock_move.action_confirm(cr, uid, todo_moves)
		stock_move.force_assign(cr, uid, todo_moves)
		done_moves = stock_move.action_done(cr, uid, todo_moves)
		stock_move.quants_assign_dcs(cr, uid, todo_moves) #assign the quants qty..
		#return todo_moves
		if _date:
			for _idtt in todo_moves:
				sql="update stock_move set date='%s' where id='%s'" % (_date, _idtt)
				cr.execute(sql)
				
		return self.write(cr, uid, _id, {'state':'done'})
		
	def mark_as_ibtsent(self, cr, uid, ids, _id,context=None):
		if context is None:
			context = {}
		transfer = self.browse(cr, uid, _id, context=context)
		stock_move = self.pool.get('stock.move')
		todo_moves = []
		todo_moves_t = []
		transit_src_id=False
		t_ids = self.pool.get('stock.location').search(cr, uid, [('usage', '=', 'transit'),('active', '=', True)], context=context)
		if t_ids:
			transit_src_id=t_ids[0]
		_name="IBT/%s" %(transfer.name)
		new_group = self.pool.get("procurement.group").create(cr, uid, {'name': _name, 'partner_id': transfer.company_id.partner_id.id}, context=context)
		picking_vals = {
			'picking_type_id': transfer.picking_type_id.id,
			'partner_id': transfer.company_id.partner_id.id,
			'date': transfer.date,
			'origin':_name,
		}
		_type="ibtsent"
		picking_id = self.pool.get('stock.picking').create(cr, uid, picking_vals, context=context)
		_jid = self.pool.get('dincelstock.journal').ibt_sent_confirm(cr, uid, transfer.id, context)
		for _line in transfer.picking_line:
			if not _line.product_id:
				continue
			if _line.product_id.x_prod_cat not in['freight','deposit']:
				#if _line.product_id.type in ('product', 'consu'):
				if _line.ship_qty>0:
					
					for vals in self._prepare_order_line_move(cr, uid, transfer, _line, picking_id, new_group, _type, context=context):
						
						move = stock_move.create(cr, uid, vals, context=context)	
						sql="update stock_move set date='%s' where id='%s'" % (transfer.date, move)
						cr.execute(sql)
						todo_moves.append(move)	
					_id2= self._create_stock_journal_ibtsent(cr, uid, transfer, _jid, _line, context)
					
		todo_moves = stock_move.action_confirm(cr, uid, todo_moves)
	
		 
		return self.write(cr, uid, _id, {'state':'sent','picking_id':picking_id})
		
	def button_mark_sent(self, cr, uid, ids, context=None):	
		if context is None:
			context = {}
		_id=ids[0]
		transfer = self.browse(cr, uid, ids[0], context=context)
		_totqty=0
		for _line in transfer.picking_line:
			if not _line.product_id:
				continue
			if _line.product_id.x_prod_cat not in['freight','deposit']:
				_totqty+=int(_line.ship_qty)
		if _totqty<1:
			raise osv.except_osv(_('Error'),_('Invalid return qty or zero qty found!!') )
			
		return self.mark_as_ibtsent(cr, uid, ids, _id,context=context)
		
	def _create_stock_journal_ibtsent(self, cr, uid, transfer, _jid, _line, context=None):
	
		_dtsent		= self.get_au_datetime(cr, uid, transfer.date)
		_qty		=_line.ship_qty
		_length		=_line.prod_length
		_obj = self.pool.get('dincelstock.journal').browse(cr, uid, _jid, context=context)
		_objline = self.pool.get('dincelstock.journal.line')
		vals={'journal_id':_jid,
				'product_id':_line.product_id.id,
				'date':_dtsent,#transfer.date,
				'date_gmt':transfer.date,
				'period_id':_obj.period_id.id,
				'prod_length':_length,
				'location_id':transfer.source_location_id.id,
				'reference':_('IBTSENT:') + (transfer.name or ''),
				}
		if _line.product_id.x_prod_type == "acs":
			vals['is_acs'] 	= True	
		else:
			vals['is_acs'] 	= False 
		if transfer.order_id:	
			vals['order_id'] 	= transfer.order_id.id		
		vals['qty_in'] 	= 0	
		vals['qty_out'] = _qty
		#double entry for transit....
		if transfer.transit_location_id:
			vals_t	=	vals.copy() 	
			vals_t['location_id'] 	= transfer.transit_location_id.id	
			vals_t['qty_in'] 		= _qty	
			vals_t['qty_out'] 		= 0
			_objline.create(cr, uid, vals_t, context=context)
		return _objline.create(cr, uid, vals, context=context)
	
	def get_au_date(self, cr, uid, dttime, context=None):
		try:
			if dttime:
				dttime1= str(dttime)[:19]
			else:
				dttime1=str(datetime.datetime.now())
				dttime1= str(dttime1)[:19]
			_from_date 	= datetime.datetime.strptime(str(dttime1),"%Y-%m-%d %H:%M:%S")
			time_zone	= 'Australia/Sydney'
			tz 			= pytz.timezone(time_zone)
			tzoffset 	= tz.utcoffset(_from_date)
			
			dt 	= str((_from_date + tzoffset).strftime("%Y-%m-%d"))
		except:
			dt=dttime
			pass	
		return dt
		
	def get_au_datetime(self, cr, uid, dttime, context=None):
		try:
			if dttime:
				dttime1= str(dttime)[:19]
			else:
				dttime1=str(datetime.datetime.now())
				dttime1= str(dttime1)[:19]
			_from_date 	= datetime.datetime.strptime(str(dttime1),"%Y-%m-%d %H:%M:%S")
			time_zone	= 'Australia/Sydney'
			tz 			= pytz.timezone(time_zone)
			tzoffset 	= tz.utcoffset(_from_date)
			
			dt 	= str((_from_date + tzoffset).strftime("%Y-%m-%d %H:%M:%S"))
		except:
			dt=dttime
			pass
		return dt
		
	def get_gmt_datetime(self, cr, uid, dttime, context=None):
		try:
			if dttime:
				dttime1= str(dttime)[:19]
			else:
				dttime1=str(datetime.datetime.now())
				dttime1= str(dttime1)[:19]
				
			_from_date 	= datetime.datetime.strptime(str(dttime1),"%Y-%m-%d %H:%M:%S")
			time_zone	= 'Australia/Sydney'
			tz 			= pytz.timezone(time_zone)
			
			aware_d = tz.localize(_from_date, is_dst=None)
			dt=aware_d.astimezone(pytz.utc)
		except:
			dt=dttime
			pass
		return dt
		
	def _create_stock_journal_ibtrx(self, cr, uid, transfer, _jid, _line, context=None):
		_dtrx		= self.get_au_datetime(cr, uid, transfer.date_received)
		_qty		=_line.ship_qty
		_length		=_line.prod_length
		_obj = self.pool.get('dincelstock.journal').browse(cr, uid, _jid, context=context)
		_objline = self.pool.get('dincelstock.journal.line')
		vals={'journal_id':_jid,
				'product_id':_line.product_id.id,
				'date':_dtrx,#transfer.date_received,
				'date_gmt':transfer.date_received,
				'period_id':_obj.period_id.id,
				'prod_length':_length,
				'location_id':transfer.destination_location_id.id,
				'reference':_('IBTRX:') + (transfer.name or ''),
				}
		if _line.product_id.x_prod_type=="acs":
			vals['is_acs'] 	= True	
		else:
			vals['is_acs'] 	= False 
		vals['qty_in'] 	= _qty	
		vals['qty_out'] = 0
		if transfer.order_id:	
			vals['order_id'] 	= transfer.order_id.id	
			
		#double entry for transit received....	
		if transfer.transit_location_id:
			vals_t	=	vals.copy() 	
			vals_t['location_id'] 	= transfer.transit_location_id.id	
			vals_t['qty_in'] 		= 0	
			vals_t['qty_out'] 		= _qty
			_objline.create(cr, uid, vals_t, context=context)	
		return _objline.create(cr, uid, vals, context=context)
		
	def button_mark_printed(self, cr, uid, ids, context=None):	
		if context is None:
			context = {}
		return self.write(cr, uid, ids[0], {'state':'printed'})	
		
	def button_mark_draft(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		return self.write(cr, uid, ids[0], {'state':'draft'})	
		
	def _prepare_order_line_move(self, cr, uid, transfer, _line, picking_id, group_id, _type, context=None):
		''' prepare the stock move data from the PO line. This function returns a list of dictionary ready to be used in stock.move's create()'''
		product_uom = self.pool.get('product.uom')
		
		res = []
		
		_origin="IBT/%s" % (transfer.name)
		
		_qty_lm		=0
		_qty		=_line.ship_qty
		_length		=_line.prod_length
		if _line.product_id.x_dcs_group and _line.product_id.x_dcs_group!="none":
			if _line.product_id.x_prod_type and _line.product_id.x_prod_type=="acs":#in ['customlength','stocklength']:
				_qty_lm=_qty
			else:
				_qty_lm=_qty*_length*0.001
		else:
			_qty_lm=_qty
		_name=	 _line.name or ''
		if not _name or _name=='':
			_name="%s" %(_line.product_id.name)
		
		if _line.location_id:
			_loc_id=_line.location_id.id 
		else:
			_loc_id=transfer.source_location_id.id
		location_dest_id=transfer.destination_location_id.id	
		'''	
		if _type=="ibtsent":
			if _line.location_id:
				_loc_id=_line.location_id.id 
			else:
				_loc_id=transfer.source_location_id.id
			if transfer.transit_location_id:
				location_dest_id=transfer.transit_location_id.id 
			else:
				location_dest_id=transfer.destination_location_id.id
		else:
			#if transfer.transit_location_id:
			_loc_id=transfer.transit_location_id.id 
			location_dest_id=transfer.destination_location_id.id	'''
			
		move_template = {
			'name':_name,# _line.name or '', #equivalent ... product name...
			'product_id': _line.product_id.id,
			'product_uom': _line.product_uom.id,
			'product_uos': _line.product_uom.id,
			'date': transfer.date,
			'date_expected':  transfer.date,#fields.date.date_to_datetime(self, cr, uid, order_line.date_planned, context),
			'location_id': _loc_id,
			'location_dest_id': location_dest_id,#transfer.destination_location_id.id,
			'picking_id': picking_id,
			'partner_id': False,
			'move_dest_id': False,
			'state': 'draft',
			#'purchase_line_id': order_line.id,
			'company_id': transfer.company_id.id,
			#'price_unit': price_unit,
			'picking_type_id': transfer.picking_type_id.id,
			'group_id': group_id,
			'procurement_id': False,
			'origin': _origin,
			'route_ids': transfer.warehouse_id and [(6, 0, [x.id for x in transfer.warehouse_id.route_ids])] or [],
			'warehouse_id':transfer.warehouse_id.id,
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
		
	 	

class dincelstock_move(osv.Model):
	_inherit 	= "stock.move"
	_columns = {
		'x_transfer_id': fields.many2one('dincelstock.transfer', 'Picking Reference'),
		#'x_quantity': fields.integer('Qty',help="Quantity for each, cause qty is sometimes recordes as L/M in case of stock/custome p1 products"),
		}
		
		
class dincelstock_transfer_line(osv.Model):
	_name 	= "dincelstock.transfer.line"
	#_order 	= "sequence"
	
	def _remain_qty(self, cr, uid, ids, product_id, vals, context=None):
		x={}
		_qty_rem=0
		for record in self.browse(cr, uid, ids):
			_qty_rem = record.qty_remain
			x[record.id] = _qty_rem 
		return x
		
	_columns = {
		'transfer_id': fields.many2one('dincelstock.transfer', 'Picking Ref', required=True, ondelete='cascade', select=True),
		'name': fields.text('Description', required=True),
		'sequence': fields.integer('Sequence'),
		'product_id': fields.many2one('product.product', 'Product', ondelete='restrict'),
		'order_qty': fields.float("Qty Ordered",digits_compute = dp.get_precision('Int Number')),	
		'ship_qty': fields.float("Qty Shipped"),	#,digits_compute = dp.get_precision('Int Number')
		'qty_remain':fields.float("Qty Remain"),
		'qty_remain_tmp':fields.float("Qty Remain"),
		'qty_remain_read':fields.function(_remain_qty, method=True, string="Balance Qty", store=False, type="float"),
		'packs': fields.char('Packs'),
		'prod_length':fields.integer('Length'),
		'product_uom': fields.many2one('product.uom', 'Unit of Measure'),
		'location_id': fields.many2one('stock.location', 'Source Location'),
	}
	
	def onchange_product_id(self, cr, uid, ids, product_id, context=None):
		res = {}
		if product_id:
			prod = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
			res['value'] = {
				'name': prod.name,
				'product_uom': prod.uom_id.id,
				'prod_length':int(prod.x_stock_length),
			}
		return res	
		
	def onchange_qty_remain(self, cr, uid, ids, order_qty, ship_qty, qty_remain, qty_remain_tmp, type, context=None):
		result={}
		if context is None:
			context = {}
		if(type != 'manual'):
			qty_remain_tmp=float(qty_remain_tmp)
			ship_qty=float(ship_qty)
			order_qty=float(order_qty)
			#_logger.error("onchange_qty_remainonchange_qty_remain1111["+str(qty_remain_tmp)+"]["+str(ship_qty)+"]["+str(order_qty)+"]")
			if(ship_qty > qty_remain_tmp):
				result.update({'ship_qty':0, 'qty_remain':qty_remain_tmp})
			else:
				if(qty_remain_tmp != 0.0):
					rem = qty_remain_tmp - ship_qty
				else:
					rem = order_qty - qty_remain_tmp
				result.update({'qty_remain':rem, 'ship_qty':ship_qty, 'qty_remain_read':rem})
				
		else:
			ship_qty=float(ship_qty)
			order_qty=ship_qty #cause in manual, order qty is not applicable. so making as equal as shipped qty
			#order_qty=float(order_qty)
			if(ship_qty > order_qty):
				result.update({'ship_qty':0, 'qty_remain':qty_remain, 'order_qty':order_qty})
			else:
				rem = order_qty - ship_qty
				result.update({'qty_remain':rem, 'ship_qty':ship_qty, 'qty_remain_read':rem, 'order_qty':order_qty})
		return {'value': result}

		