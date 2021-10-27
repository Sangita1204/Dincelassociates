import time
from functools import partial
from openerp.osv import osv
from openerp.report import report_sxw
#from common_report_header import common_report_header
#from common_report_header1 import common_report_header1
import logging
_logger = logging.getLogger(__name__)

class dincelcrm_quotation_dcs(report_sxw.rml_parse):

	#def set_context(self, objects, data, ids, report_type=None):
	#	new_ids = ids
	#	res = {}
	#	return super(purchase_invoice_dcs, self).set_context(objects, data, new_ids, report_type=report_type)

	def __init__(self, cr, uid, name, context=None):
		super(sale_quotation_dcs, self).__init__(cr, uid, name, context=context)
		self.localcontext.update( {})
		#_logger.error("partner_invoice_dcspartner_invoice_dcser_logger"+str(context))
		self.context = context 
	 	

		
class report_quotation_new(osv.AbstractModel):
	_name = 'report.dincelcrm.report_quotation_new'
	_inherit = 'report.abstract_report'
	_template = 'dincelcrm.report_quotation_new'
	_wrapped_report_class = dincelcrm_quotation_dcs

	
class report_quotation_v3_pdf(osv.AbstractModel):
	_name = 'report.dincelcrm.report_quotation_v3_pdf'
	_inherit = 'report.abstract_report'
	_template = 'dincelcrm.report_quotation_new'
	_wrapped_report_class = dincelcrm_quotation_dcs
 
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:	 