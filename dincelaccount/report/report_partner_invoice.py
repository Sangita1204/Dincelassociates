import time
from functools import partial
from openerp.osv import osv
from openerp.report import report_sxw
#from common_report_header import common_report_header
from common_report_header1 import common_report_header1
import logging
_logger = logging.getLogger(__name__)

class partner_invoice_dcs(report_sxw.rml_parse, common_report_header1):

	def set_context(self, objects, data, ids, report_type=None):
		new_ids = ids
		res = {}
		return super(partner_invoice_dcs, self).set_context(objects, data, new_ids, report_type=report_type)

	def __init__(self, cr, uid, name, context=None):
		super(partner_invoice_dcs, self).__init__(cr, uid, name, context=context)
		self.localcontext.update( {
			'get_partner': self._get_partner,
			'lines': self._get_lines,
			'get_street1': self._get_street1,
			'get_street2': self._get_street2,
			'get_date': self._get_date,
			'get_date_due': self._get_date_due,
			'get_subtotal': self._get_subtotal,
			'get_taxtotal': self._get_taxtotal,
			'get_total': self._get_total,
			'get_payterms': self._get_payterms,
			'get_invoice':self._get_invoice,
			'get_comment':self._get_comment,
			'get_site_address':self._get_site_address,
			'card_fees':self._get_card_fee,
			'get_total_paid':self._get_total_paid,
			'get_total_bal':self._get_total_bal,
		})
		#_logger.error("partner_invoice_dcspartner_invoice_dcser_logger"+str(context))
		self.context = context 
	def _get_card_fee(self, data):
		#res = []
		#if data.get('form', False) and data['form'].get('x_project_id', False):
		#	return data['form']['x_project_id'][1] 
		sql ="select a.code,a.fee_pc \
				 from dincelaccount_paymethod a  \
				where id>0 order by a.fee_pc"
		self.cr.execute(sql)
		res = self.cr.dictfetchall()
		return res
		
	def _get_site_address(self, data):
		if data.get('form', False) and data['form'].get('x_project_id', False):
			return data['form']['x_project_id'][1] 
		return '-'
		
	def _get_partner(self, data):
		if data.get('form', False) and data['form'].get('partner_id', False):
			return data['form']['partner_id'][1] 
		return '-'
	def _get_invoice(self, data):
		if data.get('form', False) and data['form'].get('internal_number', False):
			return data['form']['internal_number']
		return '-'
	def _get_comment(self, data):
		if data.get('form', False) and data['form'].get('comment', False):
			return data['form']['comment']
		return '-'
	def _get_payterms(self, data):
		payment_term=''
		if data.get('form', False) and data['form'].get('payment_term', False):
			payment_term= data['form']['payment_term'] [1]
		return payment_term	
	def _get_street1(self, data):
		street1=''
		if data.get('form', False) and data['form'].get('partner_id', False):
			partner_id= data['form']['partner_id'][0]
			sql ="select street, street2 from res_partner where id=%s" # data['form']['partner_id'][1] 
			self.cr.execute(sql,(partner_id,))
			res = self.cr.fetchone()
			if res[0]:
				street1= res[0]
			if res[1]:
				street1+= " "+res[1]	
		return street1
	def _get_street2(self, data):
		street1=''
		if data.get('form', False) and data['form'].get('partner_id', False):
			partner_id= data['form']['partner_id'][0]
			sql ="select a.zip,a.city,b.code  from res_partner a left join res_country_state b on a.state_id=b.id  where a.id=%s" 
			self.cr.execute(sql,(partner_id,))
			res = self.cr.fetchone()
			if res[1]:
				street1+= ""+res[1]	
			if res[2]:
				street1+= " "+res[2]	
			if res[0]:
				street1+=  " "+res[0]
		return street1
		
	def _get_date(self, data):
		if data.get('form', False) and data['form'].get('date_invoice', False):
			return data['form']['date_invoice'] 
		return '-'
	def _get_date_due(self, data):
		if data.get('form', False) and data['form'].get('date_due', False):
			return data['form']['date_due'] 
		return '-'	
	def _get_subtotal(self, data):
		if data.get('form', False) and data['form'].get('amount_untaxed', False):
			return data['form']['amount_untaxed'] 
		return 0.0
	def _get_taxtotal(self, data):
		if data.get('form', False) and data['form'].get('amount_tax', False):
			return data['form']['amount_tax'] 
		return 0.0
	
	#def _get_total_paid(self, data):	
		
	def _get_total_paid(self, data):
		if data.get('form', False) and data['form'].get('id', False):
			invoice_id= data['form'].get('id', False)
			sql ="select b.amt_paid \
				  from dincelaccount_voucher_payment b   \
				  where b.invoice_id=%s" 
			self.cr.execute(sql,(invoice_id,))
			rows = self.cr.fetchall()
			if len(rows) > 0 and rows[0][0]:
				return float(rows[0][0])
		return 0.0	
		
	def _get_total_bal(self, data):
		if data.get('form', False) and data['form'].get('amount_total', False):
			amount_bal= data['form']['amount_total'] 
			amt_paid = self._get_total_paid(data)
			return amount_bal-amt_paid
		return 0.0
		
	def _get_total(self, data):
		if data.get('form', False) and data['form'].get('amount_total', False):
			return data['form']['amount_total'] 
		return 0.0		
	def _get_lines(self, context):
		res = []
		if context.get('form', False) and context['form'].get('partner_id', False):
			partner_id= context['form']['partner_id'][0]
			invoice_id= context['form']['id'] 
			sql ="select a.price_unit,a.price_subtotal,a.discount,a.name,a.quantity,a.subtotal_wo_discount,b.name as uom \
				from account_invoice_line a  left join product_uom b on a.uos_id=b.id \
				where a.invoice_id=%s order by a.id" 
			#select a.id,b.id from account_invoice_line a left join product_uom b on a.uos_id=b.id where a.id=1
			self.cr.execute(sql,(invoice_id,))
			res = self.cr.dictfetchall()
		 
		return res
		
class report_partner_invoice(osv.AbstractModel):
	_name = 'report.account.report_partner_invoice'
	_inherit = 'report.abstract_report'
	_template = 'dincelaccount.report_partner_invoice'
	_wrapped_report_class = partner_invoice_dcs

class report_partner_invoice_pdf(osv.AbstractModel):
	_name = 'report.account.report_partner_invoice_pdf'
	_inherit = 'report.abstract_report'
	_template = 'dincelaccount.report_partner_invoice'
	_wrapped_report_class = partner_invoice_dcs		
  	
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
