import time
from lxml import etree
import urllib2
from openerp.osv import fields, osv
from openerp.osv.orm import setup_modifiers
from openerp.tools.translate import _
import subprocess
from subprocess import Popen, PIPE, STDOUT
import logging
_logger = logging.getLogger(__name__)
 
PROD_GROUP_SELECTION =[
	('110', '110mm'),
	('155', '155mm'),
	('200', '200mm'),
	('275', '275mm'),
	]
	
	
class dincelmrp_gantt_report(osv.osv_memory):
	_name = 'dincelmrp.gantt.report'
	#_inherit = "dcs.account.common.report"
	_columns = {
		'reportname': fields.selection(PROD_GROUP_SELECTION, 'Product'),
	}
	 
	 
	def preview_ganttreport(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		_ids=""
	 
		rptname=""
		for record in self.browse(cr, uid, ids):
			rptname=record.reportname
			
		url=self.pool.get('dincelaccount.config.settings').report_preview_url(cr, uid, ids,rptname,"",context=context)		
		if url:
			url+="&folder=gantt&p=%s" % (rptname)
			
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
				
	 
	 