from openerp.osv import fields, osv
import datetime
from openerp.tools.translate import _
import logging
_logger = logging.getLogger(__name__)
import subprocess
from subprocess import Popen, PIPE, STDOUT

class dincelmrp_accessories(osv.Model):
	_name="dincelmrp.accessories"
	#_description="Routing Schedule"
	_order = 'state desc, order_id desc,product' #order_item as in dcs , for summary
	def _get_deli_status(self, cr, uid, ids, values, arg, context):
		x={}
		for record in self.browse(cr, uid, ids):
			_id=record.order_id.id
			sch_id=False
			is_del=False
			update, dt, state = self.pool.get('sale.order').get_next_delivery_date(cr, uid, ids, _id, sch_id, is_del, context)
			x[record.id] = state
		return x
		
	def _is_order_changed(self, cr, uid, ids, values, arg, context):
		x={}
		_changed=False
		for record in self.browse(cr, uid, ids):
			_changed=False
			_prod="P%s"%(record.product)
			_tot1=0
			_tot2=0
			for row in record.accessories_line:
				_qty1= int(row.qty)
				_tot1+=_qty1
			for line in record.order_id.order_line:
				_dcsgrp=line.product_id.x_dcs_group
				_acs=line.product_id.x_prod_type
				if _dcsgrp and _dcsgrp==_prod and _acs and _acs=="acs":
					_qty2= int(line.x_order_qty)
					_tot2+=_qty2
					for row in record.accessories_line:
						
						
						if row.product_id.id==line.product_id.id:
							_qty1= int(row.qty)
							_qty2= int(line.x_order_qty)
							
							if _qty1!=_qty2:
								_changed=True
			if _tot2!=_tot1:
				_changed=True
								
			
			x[record.id] = _changed
		return x
	_columns={
		'name': fields.char('name'),
		'order_id': fields.many2one('sale.order','Order',ondelete='cascade'), #delete all this on delete sale.order
		'color_code': fields.related('order_id', 'x_colorcode', type='char', string='Color',store=False),
		'order_code': fields.related('order_id', 'origin', type='char', string='Order Code',store=False),
		'x_dt_actual': fields.related('order_id', 'x_dt_actual', type='date', string='Actual Date',store=False),#'x_dt_actual': fields.date("Actual Date"),
		'dt_actual': fields.date("Actual Date"),
		'deli_status': fields.function(_get_deli_status, method=True, string='Delivery Status', type='char'),
		'partner_id': fields.many2one('res.partner', 'Customer', domain=[('customer', '=', True),('x_is_project', '=', False)]),
		'project_id': fields.many2one('res.partner', 'Project', domain=[('x_is_project', '=', True)]),
		'note': fields.text('Notes'),
		'packs':fields.integer('Pack', size=2),
		'packs_10':fields.integer('Pack 10', size=2),
		'packs_12':fields.integer('Pack 12', size=2),
		'accessories_line': fields.one2many('dincelmrp.accessories.line', 'accessories_id', 'Accessories'),
		'product': fields.char('Product Group'), #110/155/200/275
		'packed_by':fields.char('Packed By'),
		'checked_by':fields.char('Checked By'),
		'packed_date':fields.date('Packed Date'),
		'is_order_changed': fields.function(_is_order_changed, method=True, string='Order changed', type='boolean'),
		'state': fields.selection([
			('draft', 'Draft'),
			('printed', 'Printed'),
			('packed', 'Packed'), #pending 
			('checked', 'Checked'), # 
			('cancel', 'Cancelled'), # 
			('close', 'Closed'), # 
			], 'Status',select=True),	
		}
	_defaults = {
		'state':'draft',
		'name': '/',
		}
	
	def write(self, cr, uid, ids, vals, context=None):

		res = super(dincelmrp_accessories, self).write(cr, uid, ids, vals, context=context)
		for record in self.browse(cr, uid, ids):
			sql=""
			checked_by	=record.checked_by
			if checked_by and checked_by!="":
				sql="update dincelmrp_accessories set state='checked' where id=%s " % (record.id)
			else:
				packed_by		=record.packed_by
				if packed_by and packed_by!="":
					sql="update dincelmrp_accessories set state='packed' where id=%s " % (record.id)
				else:
					if record.state !="printed" and record.state!="draft":
						sql="update dincelmrp_accessories set state='draft' where id=%s " % (record.id)
			if sql!="":	
				try:	
					cr.execute(sql)
					#if record.product=="110":
					#	sql="update dincelmrp_accessories set status_acs_110='%s' where id=%s " % (record.state, record.id)
					#record.status
				except Exception,e:
					pass
			#_logger.error("quoteupdate:update=dincelmrp_accessoriesdincelmrp_accessories-" + sql)	 	 
		return res
		
	def mark_as_printed(self, cr, uid, ids, context=None):
		for record in self.browse(cr, uid, ids):
			sql = "update dincelmrp_accessories set state = 'printed' where id='%s'" %(record.id)
			cr.execute(sql)
		return True
		
	def button_sync_qty(self, cr, uid, ids, context=None):
		for record in self.browse(cr, uid, ids):
			#_changed=False
			_prod="P%s"%(record.product)
			#_tot1=0
			#_tot2=0
			#for row in record.accessories_line:
			#	#_qty1= int(row.qty)
			#	#_tot1+=_qty1
			sql="delete from dincelmrp_accessories_line where accessories_id='%s'" % (record.id)
			cr.execute(sql)
			for line in record.order_id.order_line:
				_dcsgrp=line.product_id.x_dcs_group
				_acs=line.product_id.x_prod_type
				if _dcsgrp and _dcsgrp==_prod and _acs and _acs=="acs":
					vals1={
						'name':line.product_id.name,
						'accessories_id':record.id,
						'qty':int(line.x_order_qty),
						'product_id':line.product_id.id,
						} 
					#_logger.error("button_sync_qtybutton_sync_qty:button_sync_qty[" + str(vals1)+ "]")		
					self.pool.get('dincelmrp.accessories.line').create(cr, uid, vals1, context=context)
			#if _tot2!=_tot1:
			sql="update dincelmrp_accessories set state='draft',checked_by='' where id='%s'" % (record.id)
			cr.execute(sql)
		return True
	
	def button_preview(self, cr, uid, ids, context=None):
		
		url=self.pool.get('dincelaccount.config.settings').report_preview_url(cr, uid, ids,"acs2",ids[0],context=context)		
		return {
			'name'     : 'Go to website',
			'res_model': 'ir.actions.act_url',
			'type'     : 'ir.actions.act_url',
			'view_type': 'form',
			'view_mode': 'form',
			'target'   : 'new',
			'url'      : url}	
	def button_pdf_generate(self, cr, uid, ids, context=None): 
		url=self.pool.get('dincelaccount.config.settings').report_preview_url(cr, uid, ids,"acs2",ids[0],context=context)			
		if url:#rows and len(rows) > 0:
			
			fname = "accs_"+str(ids[0])+".pdf"
				
			#temp_path="/var/tmp/odoo/account/"+fname
			
			save_path="/var/tmp/odoo/mrp"
			
			process=subprocess.Popen(["wkhtmltopdf", 
						'--margin-top','1', 
						'--margin-left','1', 
						'--margin-right','1', 
						'--margin-bottom','1', url, save_path+"/"+fname],stdin=PIPE,stdout=PIPE)
			
			out, err = process.communicate()
			if process.returncode not in [0, 1]:
				raise osv.except_osv(_('Report (PDF)'),
									_('Wkhtmltopdf failed (error code: %s). '
									'Message: %s') % (str(process.returncode), err))
			return {
				'name': 'Load Sheet',
				'res_model': 'ir.actions.act_url',
				'type' : 'ir.actions.act_url',
				'url': '/web/binary/download_file?model=sale.order&field=datas&id=%s&path=%s&filename=%s' % (str(ids[0]),save_path,fname),
				'context': context} 
			
class dincelmrp_accessories_line(osv.Model):
	_name = "dincelmrp.accessories.line"
	#_description="Routing Schedule"
 
	_columns = {
		'name':fields.char("Name"),
		'accessories_id': fields.many2one('dincelmrp.accessories', 'Accessories',ondelete='cascade',), #delete all this on delete  .accessories
		'product_id': fields.many2one('product.product','Product'),
		'qty':fields.integer("Qty"),#,digits_compute= dp.get_precision('Int Number')),	
		'product_uom': fields.many2one('product.uom', 'Unit of Measure'),
	}
	   
	_defaults = {
		'name': '/',
		}
		
		