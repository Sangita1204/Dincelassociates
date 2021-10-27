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

			
class dincelstock_ibt_manifest(osv.Model):
	_name 			= "dincelstock.ibt.manifest"
	_inherit = ['mail.thread']

	
	_order = 'id desc'
	_description = 'IBT Manifest'
	
		
	_columns = {
		'name': fields.char('Reference'),
		'state': fields.selection([
			('draft', 'Draft'),
			('cancel', 'Cancelled'),
			('sent', 'Sent'),
			('done', 'Delivered'),
			], 'Status', track_visibility='onchange'),
		'date': fields.datetime('Date Pickup', required=True),
		'date_received': fields.datetime('Date Received'),
		'user_id': fields.many2one('res.users', 'Prepared By'),
		'note': fields.char('Note'),
		'source_location_id': fields.many2one('stock.location', 'Source Location'),
		'destination_location_id': fields.many2one('stock.location', 'Destination Location'),
		'source_warehouse_id': fields.many2one('stock.warehouse','Source Warehouse'),	
		'destination_warehouse_id': fields.many2one('stock.warehouse','Destination Warehouse'),	
		'partner_id': fields.many2one('res.partner','Delivery To'),	
		'contact_id': fields.many2one('res.partner','Contact'),	
		'ibt_ids': fields.one2many('dincelstock.transfer', 'manifest_id', 'IBT Items'),
		'print_transport': fields.boolean('Print Transport Document?'),
	}	
	
	_defaults = {
		'date': fields.datetime.now,
		'print_transport':True,
		'state': 'draft',
		'user_id': lambda obj, cr, uid, context: uid,
		'name': lambda obj, cr, uid, context: '/',
	}
	'''
	def create(self, cr, uid, vals, context=None):
		if vals.get('name','/')=='/':
			_name=self.pool.get('ir.sequence').get(cr, uid, 'ibt.manifest')
			vals['name'] =_name
		return super(dincelstock_ibt_manifest, self).create(cr, uid, vals, context=context)
		
	'''
			
	 
	def button_print_docket(self, cr, uid, ids, context=None):
		if context is None:
			context = {}  
		for record in self.browse(cr, uid, ids):
			 
				
			fname="manifestdockets_"+str(record.name)+".pdf"
			save_path="/var/tmp/odoo/docket/"
			temp_path=save_path+fname
			 
			url=self.pool.get('dincelaccount.config.settings').report_preview_url(cr, uid, ids,"manifestdockets",record.id,context=context)	
			 
			process=subprocess.Popen(["wkhtmltopdf",
										"--orientation",'landscape',
										'--margin-top','0', 
										'--margin-left','0', 
										'--margin-right','0', 
										'--margin-bottom','0', 
										url, temp_path], stdin=PIPE, stdout=PIPE)
			out, err = process.communicate()
			if process.returncode not in [0, 1]:
				raise osv.except_osv(_('Report (PDF)'),	_('Wkhtmltopdf failed (error code: %s). Message: %s') % (str(process.returncode), err))
			 
			return {
					'type' : 'ir.actions.act_url',
					'url': '/web/binary/download_file?model=dincelstock.ibt.manifest&field=datas&id=%s&path=%s&filename=%s' % (str(record.id),save_path,fname),
					'target': 'self',
				}	
				
	def button_print(self, cr, uid, ids, context=None):
		if context is None:
			context = {}	
	 
	
		 
		for record in self.browse(cr, uid, ids):
			 
				
			fname="manifestibt_"+str(record.name)+".pdf"
			save_path="/var/tmp/odoo/docket/"
			temp_path=save_path+fname
			 
			url=self.pool.get('dincelaccount.config.settings').report_preview_url(cr, uid, ids,"manifestibt",record.id,context=context)	
			 
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
			'''
			f=open(temp_path,'r')
			
			_data = f.read()
			_data = base64.b64encode(_data)
			f.close()'''
			
			 
			return {
					'type' : 'ir.actions.act_url',
					'url': '/web/binary/download_file?model=dincelstock.ibt.manifest&field=datas&id=%s&path=%s&filename=%s' % (str(record.id),save_path,fname),
					'target': 'self',
				}
				
	 
	def button_mark_sent(self, cr, uid, ids, context=None):	
		if context is None:
			context = {}
		for record in self.browse(cr, uid, ids):
			for line in record.ibt_ids:
				if line.state in ["draft","printed"]:
					#mark as sent 
					self.pool.get('dincelstock.transfer').mark_as_ibtsent(cr, uid, ids, line.id,context=context)
		return self.write(cr, uid, ids[0], {'state':'sent'})	
	
	   
	def button_mark_received(self, cr, uid, ids, context=None):	
		if context is None:
			context = {}
		for record in self.browse(cr, uid, ids):
			if not record.date_received:
				raise osv.except_osv(_('Error'),_('Blank or empty value found in Date Received!!') )
			for line in record.ibt_ids:
				if line.state =="sent":
					#mark as sent 
					#line['date_received']=record.date_received
					vals={'date_received':record.date_received, 'received_by':uid}
					self.pool.get('dincelstock.transfer').write(cr, uid, line.id,vals)	
					self.pool.get('dincelstock.transfer').mark_as_ibtreceived(cr, uid, ids, line.id,context=context)	
		return self.write(cr, uid, ids[0], {'state':'done'})	
		
	 
	 
	 	
   
		