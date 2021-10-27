from openerp.osv import osv
from openerp.report import report_sxw
import time

class supplier_payment_parser (report_sxw.rml_parse):
	def __init__(self, cr, uid, name, context): 
		super(supplier_payment_parser, self).__init__(cr, uid, name, context=context)
		self.localcontext.update({
								 'time': time,
								 'lines': self._get_lines,
								 })

	def _get_lines(self):
		return "ABC"

class report_supplier_payment(osv.AbstractModel):
	_name = 'report.account.report_supplier_payment'
	_inherit = 'report.abstract_report'
	_template = 'dincelaccount.report_supplier_payment'
	_wrapped_report_class = supplier_payment_parser 
	
class report_supplier_payment_pdf1(osv.AbstractModel):
	_name = 'report.account.report_supplier_payment_pdf1'
	_inherit = 'report.abstract_report'
	_template = 'dincelaccount.report_supplier_payment'
	_wrapped_report_class = supplier_payment_parser		

	
	