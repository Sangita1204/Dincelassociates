import time
from functools import partial
from openerp.osv import osv
from openerp.report import report_sxw
#from common_report_header import common_report_header
#from common_report_header1 import common_report_header1
import logging
_logger = logging.getLogger(__name__)

#dcs dincelstock delivery report
class dincelstock_deliveryreport(report_sxw.rml_parse):

	def __init__(self, cr, uid, name, context=None):
		super(dincelstock_deliveryreport, self).__init__(cr, uid, name, context=context)
		self.localcontext.update( {})
		self.context = context 
	 	
class report_docket_report(osv.AbstractModel):
	_name = 'report.dincelstock.report_docket_report'
	_inherit = 'report.abstract_report'
	_template = 'dincelstock.report_docket_report' #///NOTE "dincelstock"
	_wrapped_report_class = dincelstock_deliveryreport
		
class report_docket_report_pdf(osv.AbstractModel):
	_name = 'report.dincelstock.report_docket_report_pdf'
	_inherit = 'report.abstract_report'
	_template = 'dincelstock.report_docket_report'
	_wrapped_report_class = dincelstock_deliveryreport   	

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
