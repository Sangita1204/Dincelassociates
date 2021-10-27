from datetime import date
#from openerp.addons.base_status.base_state import base_state
import time 
import datetime
from datetime import timedelta
import dateutil.parser
from openerp.osv import fields, osv
from openerp.tools.translate import _
import logging
import openerp.addons.decimal_precision as dp
import subprocess
from subprocess import Popen, PIPE, STDOUT
import urllib2
import simplejson
_logger = logging.getLogger(__name__)

class dincelaccount_invoice_multi(osv.Model):
	_name = "dincelaccount.invoice.multi"
	#_description="Print Schedule"
		
	def _get_init_qty(self, cr, uid, context=None):
		return 1
		
	_columns = {
		'name':fields.char("Name"),
		'invoice_lines': fields.one2many('dincelaccount.invoice.multi.line', 'invoice_multi_id', 'Invoice Lines'),
		'qty':fields.float("Qty test"),
	}
	_defaults = {
		'qty': _get_init_qty,
		
		}	

	 
		
	def on_change_qty(self, cr, uid, ids, _qty,invoice_lines, context=None):
		_items=[]
		if context is None:
			context = {}
		 
		
		_obj=self.pool.get('account.invoice') 
		
		if context and context.get('active_ids'):
			_ids=context.get('active_ids')
			for line in _obj.browse(cr, uid, _ids, context=context): 
				 
				_name=line.name
				vals={'invoice_id':line.id,
					  'partner_id':line.partner_id.id,
					  'project_id':line.x_project_id.id,
					  'sub_total':line.amount_total,
					  'name':_name,#line.order_id.origin or line.order_id.name,
					 }
					 
				_items.append(vals)	
	 
		vals1={}
		vals1['invoice_lines']=_items
	 
		
		return {'value':vals1}	
	
	 
		
	def print_pdf_invoice(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		 
		_str=""
	 
		record = self.browse(cr, uid, ids[0], context=context)
		for line in record.invoice_lines:
			_str+=str(line.invoice_id.id)+"-"
			 
			
		if _str and len(_str)>0:
			url=self.pool.get('dincelaccount.config.settings').report_preview_url(cr, uid, ids,"invoices","0",context=context)	
			if url:			
				url=url.replace("erp.dincel.com.au/", "localhost/")
				url+="&ids="+_str+"&uid=" +str(uid)
				fname_part=datetime.datetime.now().strftime("%Y%m%d")
				fname="invoices_"+str(fname_part)+".pdf"
				save_path="/var/tmp/odoo/account"
				
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
						'name': 'Pdf report',
						'res_model': 'ir.actions.act_url',
						'type' : 'ir.actions.act_url',
						'url': '/web/binary/download_file?model=dincelmrp.schedule&field=datas&id=1&path=%s&filename=%s' % (save_path,fname),
						'context': context}
		#return False				
		
	  
		
class dincelaccount_invoice_multi_line(osv.osv_memory):
	_name="dincelaccount.invoice.multi.line"
	#_order = 'id desc' order_item as in dcs , for summary
	_columns={
		'name': fields.char('Name'),
		'invoice_multi_id': fields.many2one('dincelaccount.invoice.multi','Print Reference'),
		'invoice_id':fields.many2one('account.invoice','Invoice'),
		'partner_id': fields.many2one('res.partner','Customer'),	
		'project_id': fields.many2one('res.partner','Project / Site'),	
		'sub_total': fields.float('Sub total', digits=(16,2)),
		}