import time
from functools import partial
from openerp.osv import osv
from openerp.report import report_sxw
import datetime
import dateutil.parser
import dateutil
from common_report_header1 import common_report_header1
import logging
from datetime import timedelta
import calendar
from calendar import monthrange

_logger = logging.getLogger(__name__)

class tax_statement_dcs(report_sxw.rml_parse, common_report_header1):

	def set_context(self, objects, data, ids, report_type=None):
		new_ids = ids
		res = {}
		return super(tax_statement_dcs, self).set_context(objects, data, new_ids, report_type=report_type)

	def __init__(self, cr, uid, name, context=None):
		super(tax_statement_dcs, self).__init__(cr, uid, name, context=context)
		self.localcontext.update( {
			'lines': self._get_lines,
		})
		
		self.context = context 
	      
	def _get_lines(self, context):
		
		ret_res = []
		
	 
		return ret_res
		
class report_tax_statement(osv.AbstractModel):
	_name = 'report.account.report_tax_statement'
	_inherit = 'report.abstract_report'
	_template = 'dincelaccount.report_tax_statement'
	_wrapped_report_class = tax_statement_dcs
 