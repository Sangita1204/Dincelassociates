import time
from functools import partial
from openerp.osv import osv
from openerp.report import report_sxw
#from common_report_header import common_report_header
#from common_report_header1 import common_report_header1
import logging
_logger = logging.getLogger(__name__)

class purchase_nonstock_dcs(report_sxw.rml_parse):

	def __init__(self, cr, uid, name, context=None):
		super(purchase_nonstock_dcs, self).__init__(cr, uid, name, context=context)
		self.localcontext.update( {})
		self.context = context 
	 	
class report_po_nonstock(osv.AbstractModel):
	_name = 'report.purchase.report_po_nonstock'
	_inherit = 'report.abstract_report'
	_template = 'dincelpurchase.report_po_nonstock'
	_wrapped_report_class = purchase_nonstock_dcs
 		
class report_po_nonstock_pdf(osv.AbstractModel):
	_name = 'report.purchase.report_po_nonstock_pdf'
	_inherit = 'report.abstract_report'
	_template = 'dincelpurchase.report_po_nonstock'
	_wrapped_report_class = purchase_nonstock_dcs   	
	
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
