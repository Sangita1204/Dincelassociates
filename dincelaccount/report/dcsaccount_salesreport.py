import time
from lxml import etree
import urllib2
from openerp.osv import fields, osv
from openerp.osv.orm import setup_modifiers
from openerp.tools.translate import _
from account_trialbalance import account_balance1
from account_financial_report1 import report_account_common1
from report_bas_tax import bas_report_dcs
import subprocess
from subprocess import Popen, PIPE, STDOUT
import logging
_logger = logging.getLogger(__name__)
 
		
class dcsaccount_sales_report(osv.osv_memory):
	_name = 'dcsaccount.sales.report'
	#_inherit = "dcs.account.common.report"
	_columns = {
		'reportname':fields.selection([
			('salesrptuid','Sales by Salesperson'),
			('salesrptprod','Sales by Product'),
			('sales_detail','Sales Details by Salesperson'),
			('quotationreport','Quotation Report'),
			('saleorder','Orders Received Report'),
			], 'Report'),	
		'date1': fields.date('Date1'),
		'date2': fields.date('Date2'),
	}
	_defaults = {
		'date1': lambda *a: time.strftime('%Y-%m-%d'),
		'date2': lambda *a: time.strftime('%Y-%m-%d'),
	}
	def preview_salesreport(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		_ids=""
		dt1=""
		dt2=""
		rptname=""
		for record in self.browse(cr, uid, ids):
			dt1=record.date1
			dt2=record.date2
			rptname=record.reportname
			
		url=self.pool.get('dincelaccount.config.settings').report_preview_url(cr, uid, ids,rptname,"",context=context)		
		if url:
			url+="&dt1=%s&dt2=%s" % (dt1,dt2)
			#if supplier:
			#	url+="&t=s"
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
				
	def download_salesreport_csv(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		_ids=""
		dt1=""
		dt2=""
		rptname=""
		_id="0"
		for record in self.browse(cr, uid, ids):
			dt1=record.date1
			dt2=record.date2
			rptname=record.reportname
			
		url=self.pool.get('dincelaccount.config.settings').report_preview_url(cr, uid, ids,rptname,"",context=context)		
		if url:
			url+="&dt1=%s&dt2=%s&csv=1" % (dt1,dt2)
			fname=rptname
		 
			fname=fname.lower().replace(' ','')+".csv"
			 
			f = urllib2.urlopen(url)
			_csvtxt = f.read()
			
			temp_path="/var/tmp/odoo/account/"#+fname	
			save_as=temp_path+fname	
			with open(save_as, 'w') as the_file:
				the_file.write(_csvtxt)
			return {
					'name': 'CSV Report',
					'res_model': 'ir.actions.act_url',
					'type' : 'ir.actions.act_url',
					'url': '/web/binary/download_file?model=account.invoice&field=datas&id=%s&path=%s&filename=%s' % (str(_id),temp_path,fname),
					'context': context}	
				
	  
	 