import time
from functools import partial
from openerp.osv import osv
from openerp.report import report_sxw
#from common_report_header import common_report_header
#from common_report_header1 import common_report_header1
import logging
_logger = logging.getLogger(__name__)

#mo production quantity report
class dincelmrp_mo_pqreport(report_sxw.rml_parse):

	def __init__(self, cr, uid, name, context=None):
		super(dincelmrp_mo_pqreport, self).__init__(cr, uid, name, context=context)
		self.localcontext.update( {
			'lines_110': self._get_lines_110,
			'lines_155': self._get_lines_155,
			'lines_200': self._get_lines_200,
			'lines_275': self._get_lines_275,
		})
		self.context = context 
	
 	def _get_lines(self, prod_id, prod):
		sql ="SELECT a.product_qty,a.state,a.product_id,a.name,a.x_order_length,a.x_sale_order_id,a.x_order_qty,  \
				a.x_pack_xtra,a.x_pack_20,a.x_pack_14,a.x_pack_10,a.x_pack_12, \
				b.name_template,c.x_dcs_itemcode \
				FROM  mrp_production a LEFT JOIN  product_product b ON a.product_id=b.id \
				LEFT JOIN product_template c ON b.product_tmpl_id = c.id \
				WHERE a.x_production_id='%s' AND c.x_dcs_group='%s' ORDER BY c.x_dcs_itemcode,a.x_order_length" 
		sql = sql % (str(prod_id), str(prod))
		#_logger.error("invoice_print_pdf_dcs:sqlsqlsql["+str(sql)+"]")
		self.cr.execute(sql)
		res = self.cr.dictfetchall()
		return res
		
	def _get_lines_110(self, context):
		res = []
		if context.get('form', False):# and context['form'].get('partner_id', False):
			prod_id= context['form']['id'] 
			res = self._get_lines(prod_id, 'P110')
		return res
		
	def _get_lines_275(self, context):
		res = []
		if context.get('form', False):
			prod_id= context['form']['id'] 
			res = self._get_lines(prod_id, 'P275')
		return res
		
	def _get_lines_155(self, context):
		res = []
		if context.get('form', False):
			prod_id= context['form']['id'] 
			res = self._get_lines(prod_id, 'P155')
		return res

	def _get_lines_200(self, context):
		res = []
		if context.get('form', False):
			prod_id= context['form']['id'] 
			res = self._get_lines(prod_id, 'P200')
		return res	
		
class report_mo_pqreport(osv.AbstractModel):
	_name = 'report.production.report_mo_pqreport'
	_inherit = 'report.abstract_report'
	_template = 'dincelmanufacture.report_mo_pqreport' #///NOTE "dincelmanufacture"
	_wrapped_report_class = dincelmrp_mo_pqreport
		
class report_mo_pqreport_pdf(osv.AbstractModel):
	_name = 'report.production.report_mo_pqreport_pdf'
	_inherit = 'report.abstract_report'
	_template = 'dincelmanufacture.report_mo_pqreport'
	_wrapped_report_class = dincelmrp_mo_pqreport   	

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
