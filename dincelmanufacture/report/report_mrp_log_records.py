import time
from functools import partial
from openerp.osv import osv
from openerp.report import report_sxw
#from common_report_header import common_report_header
#from common_report_header1 import common_report_header1
import logging
_logger = logging.getLogger(__name__)

class dincelmrp_logs(report_sxw.rml_parse):

	#def set_context(self, objects, data, ids, report_type=None):
	#	new_ids = ids
	#	res = {}
	#	return super(purchase_invoice_dcs, self).set_context(objects, data, new_ids, report_type=report_type)

	def __init__(self, cr, uid, name, context=None):
		super(dincelmrp_logs, self).__init__(cr, uid, name, context=context)
		self.localcontext.update( {})
		#_logger.error("partner_invoice_dcspartner_invoice_dcser_logger"+str(context))
		self.context = context 
	 	

		
class report_mrp_log_records(osv.AbstractModel):
	_name = 'report.dincelmanufacture.report_mrp_log_records'
	_inherit = 'report.abstract_report'
	_template = 'dincelmanufacture.report_mrp_log_records'
	_wrapped_report_class = dincelmrp_logs	 