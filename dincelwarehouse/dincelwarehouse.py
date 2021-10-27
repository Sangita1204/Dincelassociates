from openerp.osv import osv, fields
from datetime import date
#from openerp.addons.base_status.base_state import base_state
import time 
import datetime
import logging
from openerp.tools.translate import _
from openerp import SUPERUSER_ID, api
from time import gmtime, strftime
_logger = logging.getLogger(__name__)

PROD_STATUS_SELECTION =[
	('queue','Queue'),
	('part','Partial'),
	('complete','Complete'),
	]

class dincelwarehouse_stock_warehouse(osv.Model):
	_inherit = "stock.warehouse"
	
	_columns = {
		'x_cost_xtra': fields.float('Surcharge Rate'),
		'x_master':fields.boolean('Master/Primary'),
		}

class dincelwarehouse_sale_order(osv.Model):
	_inherit = "sale.order"
	
	_columns = {
		'x_delivery_booking_ids':fields.one2many('dincelwarehouse.sale.order.delivery', 'order_id', 'Delivery Bookings', ondelete='cascade',),
		}
				
		
class dincelwarehouse_sale_order_delivery(osv.Model):
	_name = "dincelwarehouse.sale.order.delivery"
	_description = 'Delivery Schedule'
	_order = 'date_actual'
	_inherit = ['mail.thread']
	
	def button_prepare_docket(self, cr, uid, ids, context=None):
		#record = self.browse(cr, uid, ids[0], context=context)
		return True
 
	@api.multi 
	def print_loadsheet_docket(self):
		#return self.loadsheet_pdf_byid(self.id)
		obj =self.env['dincelwarehouse.sale.order.delivery'].browse(self.id)
		return self.env['sale.order'].loadsheet_pdf_byid(obj.order_id.id)	
		
	def _has_pending_docket(self, cr, uid, ids, values, arg, context):
		x={}
		_has_pending=True
		for record in self.browse(cr, uid, ids):
			_qty= record.dockets
			#if _qty>0:
			sql = "select 1 from dincelstock_pickinglist where schedule_id='%s'" % str(record.id)
			cr.execute(sql)
			rows 	= cr.dictfetchall()
			if len(rows)==0:
				_has_pending=True
			else:
				if len(rows)>=_qty:
					_has_pending=False
			x[record.id] = _has_pending 
		return x
			
	def _pending_invoice(self, cr, uid, ids, values, arg, context):
		x={}
		#_edit=False
		for record in self.browse(cr, uid, ids):
			x[record.id]=	self.pool.get("sale.order").get_cod_pending_invoice(cr,uid, ids,record.order_id.id,context) 
		return x
		
	def _admin_master(self, cr, uid, ids, values, arg, context):
		x={}
		_edit=False
		for record in self.browse(cr, uid, ids):
			_edit=self.pool.get("sale.order").get_admin_master(cr, uid, ids, record.order_id.id, context)
			x[record.id]=_edit 
		return x
		
	def _admin_super(self, cr, uid, ids, values, arg, context):
		x={}
		_edit=False
		for record in self.browse(cr, uid, ids):
			_edit=self.pool.get("sale.order").get_admin_super(cr, uid, ids, record.order_id.id, context)
			x[record.id]=_edit 
		return x	
	
	def _mrp_missing(self, cr, uid, ids, values, arg, context):
		x={}
		_missing=False
		for record in self.browse(cr, uid, ids):
			if record.order_id:
				_missing = self.pool.get("sale.order").mrp_missing_found(cr, uid, ids, record.order_id.id, context) 
			x[record.id]=  _missing 
		return x
		
	def _edit_master(self, cr, uid, ids, values, arg, context):
		x={}
		_edit=False
		for record in self.browse(cr, uid, ids):
			'''cr.execute("select res_id from ir_model_data where name='deposit_ex_editor' and model='res.groups'") #+ str(record.id))
			#cr.execute(sql)
			rows = cr.fetchone()
			if rows == None or len(rows)==0:
				_edit=False
			else:
				if rows[0]:#!=None:
					sql ="select 1 from  res_groups_users_rel where gid='%s' and uid='%s'" % (str(rows[0]), str(uid))
					cr.execute(sql)
					rows1 = cr.fetchone()
					if rows1 and len(rows1)>0:
						_edit=True'''
			_edit=self.pool.get("sale.order").get_edit_master(cr, uid, ids, record.order_id.id, context)
			x[record.id]=_edit 
		return x
		
	def _stop_supply_over(self, cr, uid, ids, values, arg, context):
		x={}
		_rem_dockets=0
		for record in self.browse(cr, uid, ids):
			_stop=False
			context = context.copy()
			context['delivery']="1"
			#always check open orders + all open invoices against the credit limit
			proceed, o_ids=self.pool.get('sale.order').is_over_limit_ok( cr, uid, ids, record.order_id.id, context=context)
			#proceed, o_ids=self.pool.get('sale.order').is_over_limit_bythisorder( cr, uid, ids, record.order_id.id, context=context)
			#is_over_limit_bythisorder
			if proceed==0 and record.authorize_blacklist==False:
				_stop=True
			x[record.id] = _stop
		return x	
		
	def _remaining_dockets(self, cr, uid, ids, values, arg, context):
		x={}
		_rem_dockets=0
		for record in self.browse(cr, uid, ids):
			_qty = record.dockets
			#if _qty>0:

			sql = "select count(*) as done_doc from dincelstock_pickinglist where schedule_id='%s' and state = 'done'" % str(record.id)
			cr.execute(sql)
			rows 	= cr.dictfetchall()
			
			for row in rows:
				_tot_done = row['done_doc']

			_rem_dockets = int(_qty) - int(_tot_done)
			
			x[record.id] = _rem_dockets

		return x	
		
	def _get_acs_status(self, cr, uid, ids, values, arg, context):
		x={}
		for record in self.browse(cr, uid, ids):
			status = ""
			sql = "select count(*) as rec_acs from dincelmrp_accessories where order_id='%s'" % str(record.order_id.id)
			cr.execute(sql)
			rows 	= cr.dictfetchall()
			status_list = []
			for row in rows:
				if(row['rec_acs'] > 0):
					sql_state = "select state from dincelmrp_accessories where order_id='%s' group by state" % str(record.order_id.id)
					cr.execute(sql_state)
					rows_s 	= cr.fetchall()
					for rows_state in rows_s:
						if(row['rec_acs'] == 1):
							status = rows_state[0].capitalize()
						else:
							status_list.append(rows_state[0])
						#_logger.error("_get_acs_status111["+str(row['rec_acs'])+"]["+str(status_list)+"]")
					if(('draft' in status_list or 'printed' in status_list) and ('checked' in status_list or 'packed' in status_list)):
						status = "Partial"
					elif(('draft' in status_list or 'printed' in status_list) and ('checked' not in status_list and 'packed' not in status_list)):
						status = "Draft"
					elif(('checked' in status_list or 'packed' in status_list) and ('draft' not in status_list and 'printed' not in status_list)):
						status = "Packed"
				else:
					status = "N/A"
			x[record.id] = status
		return x
		
	_columns = {
		'name': fields.char('Order Reference'),
		'date_entry': fields.date('Date Entry'),
		'date_actual': fields.date('Date Delivery/Pickup', states={'draft': [('readonly', False)], 'pending': [('readonly', False)]},track_visibility='onchange'),
		'order_id': fields.many2one('sale.order', 'Sale Order'),
		'mrp_res_id': fields.many2one('dincelmrp.production', 'MRP Res'), #todo refer this instead of so while creating dockects
		'partner_id': fields.many2one('res.partner','Client'),	
		'project_id': fields.many2one('res.partner','Project / Site'),	
		'project_suburb_id': fields.related('project_id', 'x_suburb_id',  string='Suburb', type="many2one", relation="dincelbase.suburb",store=True),	
		'state_id': fields.many2one('res.country.state','Project/Site State'),
		'warehouse_id': fields.many2one('stock.warehouse','Dispatch Location'),		
		'project_state':fields.related('project_id', 'state_id', string="P/S State", type="many2one", relation="res.country.state", store=False),	
		'stop_supply': fields.related('partner_id', 'x_stop_supply', type='boolean', string='Stop Supply',store=False),
		'hold_supply': fields.related('partner_id', 'x_hold_supply', type='boolean', string='Hold Supply / Legal',store=False),
		#'partner_id':fields.related('order_id', 'partner_id', string="Partner", type="many2one", relation="res.partner", store=True),
		#'project_id':fields.related('order_id', 'x_project_id', string="Project/Site", type="many2one", relation="res.partner", store=True),
		#'project_suburb_id': fields.related('order_id', 'x_project_suburb_id',  string='Suburb', type="many2one", relation="dincelbase.suburb",store=True),
		'mrp_missing': fields.function(_mrp_missing, method=True, string='MRP Mismatch',type='boolean'),		
		'contact_id':fields.related('order_id', 'x_contact_id', string="Contact", type="many2one", relation="res.partner", store=False),
		'order_code': fields.related('order_id', 'origin', type='char', string='DCS Code',store=False),
		'color_code': fields.related('order_id', 'x_colorcode', type='char', string='Color',store=False),
		'color_name': fields.related('order_id', 'x_colorname', type='char', string='Color Name',store=False),
		'balance_due': fields.related('order_id','x_over_due', string='Overdue?',type='char',store=False),
		'prod_status': fields.related('order_id', 'x_prod_status', type='selection', selection=PROD_STATUS_SELECTION, readonly=True, store=True, string='Production Status'),
		'deposit_paid': fields.related('order_id','x_dep_paid', string='Deposit Paid',type='char',store=True),
		'balance_paid': fields.related('order_id','x_bal_paid', string='Balance Paid',type='char',store=True),
		'location_id':fields.related('order_id', 'x_location_id', string="Stock Location", type="many2one", relation="stock.location", store=False),
		'pudel': fields.selection([
			('pu', 'Pickup'),
			('del', 'Delivery'),
			], 'PU/DEL', states={'draft': [('readonly', False)], 'pending': [('readonly', False)]}),
		'trucks':fields.integer('Trucks', size=2),	
		'packs':fields.integer('Packs', size=2),	
		'dockets':fields.integer('Deliveries', size=2, states={'draft': [('readonly', False)], 'pending': [('readonly', False)]}),	
		'dockets_remain':fields.integer('Remaining Dockets', size=2),	
		'rem_dockets':fields.function(_remaining_dockets, method=True, string='Remaining',type='integer', size=2, store=False),
		'comments':fields.char('Comments', states={'draft': [('readonly', False)], 'pending': [('readonly', False)]},track_visibility='onchange'),
		'internal_notes':fields.char('Internal Notes',track_visibility='onchange'),
		'scheduled_by': fields.many2one('res.users','Scheduled By'),
		'has_pending_docket': fields.function(_has_pending_docket, method=True, string='Pending Deliveries', type='boolean'),
		'products':fields.char('Products'),
		'authorize_docket':fields.boolean('Authorise COD Invoice',track_visibility='onchange'),
		'authorize_blacklist':fields.boolean('Authorise Stop Supply',track_visibility='onchange'),
		'authorize_hold':fields.boolean('Authorise Hold Supply',track_visibility='onchange'),
		'authorize_mrp_deli':fields.boolean('Authorise MRP',track_visibility='onchange',help="Authorise delivery on MRP missing/mismatch"),
		'authorize_comments':fields.char('Authorise Comments',track_visibility='onchange'),
		'fw_done':fields.boolean('F/W Done'),
		'fw_comments':fields.char('F/W Comments',track_visibility='onchange'),
		'docket_ids': fields.one2many('dincelstock.pickinglist', 'schedule_id','Dockets'),
		'pending_invoice': fields.function(_pending_invoice, method=True, string='Pending COD Invoice',type='boolean'),
		'x_edit_master': fields.function(_edit_master, method=True, string='Edit master',type='boolean'),
		'x_admin_master': fields.function(_admin_master, method=True, string='Admin master',type='boolean'),
		'x_admin_super': fields.function(_admin_super, method=True, string='Admin Super',type='boolean'),
		'stop_supply_over': fields.function(_stop_supply_over, method=True, string='Stop Supply Over',type='boolean'),
		'x_acs_status':fields.function(_get_acs_status, method=True, string='ACS Status',type='char'),
		'state': fields.selection([
			('draft', 'Draft'),
			('open', 'Open'),
			('confirm', 'Confirmed'),
			('partial', 'Partial'),
			('cancel','Cancelled'),
			('done', 'Done'),
			], 'Status', track_visibility='onchange'),
		}	
	_order = 'date_actual desc'
	_defaults = {
		'state': 'draft',
		'fw_done': False,
		'name':'Delivery',
		}		
		
	def unlink(self, cr, uid, ids, context=None, check=True):
		context = dict(context or {})
		if context is None:
			context = {}
		for record in self.browse(cr, uid, ids):
			if len(record.docket_ids)>0:
				#raise Warning(_('You cannot delete after docket/s has been generated.'))
			 	raise osv.except_osv(_('Forbbiden to delete'), _('You cannot delete delivery schedule after docket/s has been generated.'))	 
			if record.order_id:
				usr= self.pool.get('res.users').browse(cr, uid, uid)
				subject="Delivery schedule deleted"
				details="%s deleted delivery schedule which was booked for the date %s." % (usr.name, record.date_actual, )
				self.pool.get('sale.order').message_post(cr, uid, [record.order_id.id], body=details, subject=subject, context=context)
				self.pool.get("sale.order").set_next_delivery_date(cr, uid, ids, record.order_id.id, record.id, True,context=context)
		return super(dincelwarehouse_sale_order_delivery, self).unlink(cr, uid, ids, context)
		
	def write(self, cr, uid, ids, vals, context=None):

		res = super(dincelwarehouse_sale_order_delivery, self).write(cr, uid, ids, vals, context=context)
		for record in self.browse(cr, uid, ids):
			if record.date_actual:
				try:	
					'''#self.pool.get('sale.order').write(cr, uid, record.order_id.id, {'x_dt_actual': record.date_actual}, context=context)	
					sql="update sale_order set x_dt_actual='%s' where id='%s'" % (record.date_actual, record.order_id.id)
					cr.execute(sql)
					sql="update dincelmrp_accessories set dt_actual='%s' where order_id='%s'" % (record.date_actual, record.order_id.id)
					#_logger.error("dincelwarehouse_sale_order_deliverydincelwarehouse_sale_order_delivery["+str(sql)+"]")	
					cr.execute(sql)
					'''
					self.pool.get("sale.order").set_next_delivery_date(cr, uid, ids, record.order_id.id, record.id, False,context=context)
				except Exception,e:
					_logger.error("dincelwarehouse_sale_order_ExceptionExceptiony["+str(e)+"]")
					pass
			#if record.state!="partial" and record.rem_dockets and record.rem_dockets>0 and  record.rem_dockets>0 and record.rem_dockets:
			#	sql="update dincelwarehouse_sale_order_delivery set state='partial' where id='%s'" % (record.id)
			#	cr.execute(sql)
			#el
			 
				
			if record.rem_dockets == 0: #record.rem_dockets and 
				sql="update dincelwarehouse_sale_order_delivery set state='done',dockets_remain=0 "
				sql+=" where id='" + str(record.id)+"'"
				cr.execute(sql)
				
			else:
				if record.rem_dockets != record.dockets_remain:
					sql="update dincelwarehouse_sale_order_delivery set dockets_remain='%s' where id='%s'" % (record.rem_dockets,record.id)
					cr.execute(sql)
					
		return res	
		
	def btn_delivered_outstanding(self, cr, uid, ids, context=None):
		if context is None:
			context = {}	
		context = context.copy()
		context['delivery']="1"	
		for record in self.browse(cr, uid, ids): 
			proceed, o_ids =self.pool.get("sale.order").is_over_limit_ok(cr, uid, ids, record.order_id.id, context=context)
			value = {
				'type': 'ir.actions.act_window',
				'name': _('Outstanding Orders'),
				'view_type': 'form',
				'view_mode': 'tree,form',
				'res_model': 'sale.order',
				'domain':[('id','in',o_ids)],
				'context':{},
				#'view_id': view_id,
				
			}

			return value
		
	def button_create_docket_dcs(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		for record in self.browse(cr, uid, ids):
			if record.order_id.state in ['done','cancel']:
				raise osv.except_osv(_('Forbbiden delivery'), _('The order is already closed/cancelled.'))	 
			else:
				if record.mrp_missing==True and record.authorize_mrp_deli==False:
					raise osv.except_osv(_('Forbbiden delivery'), _('The order is has MRP missing/mismatch, please contact account to authorise and continue.'))	 
				else:	
					context = context.copy()
					context['delivery']="1"
					proceed, o_ids=self.pool.get('sale.order').is_over_limit_ok( cr, uid, ids, record.order_id.id, context=context)
					if proceed==0 and record.authorize_blacklist==False:
						#sql="update dincelwarehouse_sale_order_delivery set stop_supply='t' where id='%s'" % (record.id)
						#cr.execute(sql)
						raise osv.except_osv(_('Forbbiden delivery'), _('This delivery pushes the customer over their credit limit (stop supply), please contact account to authorise and continue.'))
					else:
						return {
							'type': 'ir.actions.act_window',
							'res_model': 'dincelwarehouse.delivery.docket',
							'view_type': 'form',
							'view_mode': 'form',
							#'res_id': 'id_of_the_wizard',
							'context':{'default_order_id': record.order_id.id},
							'target': 'new',
						}
	def dcs_partner_statement_pdf(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		#datas = {'ids': context.get('active_ids', [])}
		#datas['form']  = self.read(cr, uid, ids, context=context)[0]
		#return self.pool['report'].get_action(cr, uid, [], 'account.report_partner_statement_pdf', data=datas, context=context)	
		_ids=""
		#dt=""
		for record in self.browse(cr, uid, ids):
			#dt=record.date_order
			#dt = datetime.datetime.now()
			#dt = date.today()
			if record.partner_id:
				_ids=record.partner_id.id
		return self.pool.get('res.partner').download_statement_pdf(cr, uid, _ids, context=context)		