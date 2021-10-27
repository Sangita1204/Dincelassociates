import time
import datetime
from functools import partial
from openerp.osv import osv
from openerp.report import report_sxw
#from common_report_header import common_report_header
from common_report_header1 import common_report_header1
import logging
_logger = logging.getLogger(__name__)

class dcsaccount_reconcile_rpt(report_sxw.rml_parse, common_report_header1):

	def set_context(self, objects, data, ids, report_type=None):
		new_ids = ids
		res = {}
		return super(dcsaccount_reconcile_rpt, self).set_context(objects, data, new_ids, report_type=report_type)

	def __init__(self, cr, uid, name, context=None):
		super(dcsaccount_reconcile_rpt, self).__init__(cr, uid, name, context=context)
		self.localcontext.update( {
			'get_partner': self._get_partner,
			'lines': self._get_lines,
		})
		
		self.context = context 
	def _get_partner(self, data):
		if data.get('form', False) and data['form'].get('partner_id', False):
			return data['form']['partner_id'][1]
		return '-'
		
	def _get_lines(self, context):
		res1 = []
		if context.get('form', False) and context['form'].get('partner_id', False):
			partner_id= context['form']['partner_id'][0]
			current_date = datetime.date.today()
			
			#_logger.error("partner_aging_dcspartner_aging_dcs-"+str(partner_id))
			sql ='SELECT id,internal_number,state,date_invoice,amount_total,(\'%s\'-date_invoice)  as dtdiff, \
					case when (\'%s\'-date_invoice) < 30 then amount_total else 0 end as "day1", \
					case when ((\'%s\'-date_invoice) between 30 and 60) then amount_total else 0 end as "day2", \
					case when ((\'%s\'-date_invoice) between 61 and 90) then amount_total else 0 end as "day3", \
					case when ((\'%s\'-date_invoice) >90) then amount_total else 0 end as "day4" \
					FROM   account_invoice where date_invoice   is not null \
					and state=\'open\' and partner_id =%s order by date_invoice'
			'''		
			sql ='SELECT a.internal_number,a.state,a.date_invoice,(\'%s\'-a.date_invoice)  as dtdiff, \
					case when (\'%s\'-a.date_invoice) < 30 then (a.amount_total-b.amt_paid) else 0 end as "day1", \
					case when ((\'%s\'-a.date_invoice) between 30 and 60) then (a.amount_total-b.amt_paid) else 0 end as "day2", \
					case when ((\'%s\'-a.date_invoice) between 61 and 90) then (a.amount_total-b.amt_paid)else 0 end as "day3", \
					case when ((\'%s\'-a.date_invoice) >90) then (a.amount_total-b.amt_paid) else 0 end as "day4" \
					FROM   account_invoice a left join dincelaccount_voucher_payment b on a.id=b.invoice_id  where a.date_invoice   is not null \
					and a.state=\'open\' and a.partner_id =%s order by a.date_invoice''' 
			#self.cr.execute(sql,(str(current_date),str(current_date),str(current_date),str(current_date),str(current_date),partner_id,))
			sql = sql % (str(current_date),str(current_date),str(current_date),str(current_date),str(current_date),partner_id,)
			_logger.error("get_quote_total:sqlsql[" + str(sql)+ "]")
			self.cr.execute(sql)
			res = self.cr.dictfetchall()
			for row in res:	
				invoice_id = row['id']
				sql ='SELECT  \
					case when (\'%s\'-a.date_invoice) < 30 then b.amt_paid else 0 end as "day1", \
					case when ((\'%s\'-a.date_invoice) between 30 and 60) then b.amt_paid else 0 end as "day2", \
					case when ((\'%s\'-a.date_invoice) between 61 and 90) then b.amt_paid else 0 end as "day3", \
					case when ((\'%s\'-a.date_invoice) >90) then b.amt_paid else 0 end as "day4" \
					FROM   account_invoice a left join dincelaccount_voucher_payment b on a.id=b.invoice_id  where a.date_invoice   is not null \
					and a.state=\'open\' and a.partner_id =%s and a.id=%s' 
				#self.cr.execute(sql,(str(current_date),str(current_date),str(current_date),str(current_date),str(current_date),partner_id,))
				sql = sql % (str(current_date),str(current_date),str(current_date),str(current_date),partner_id,invoice_id,)
				#_logger.error("get_quote_total:sqlsql222[" + str(sql)+ "]")
				self.cr.execute(sql)
				row1 	= self.cr.dictfetchone()
				#_logger.error("get_quote_total:sqlsql222[" + str(sql)+ "]")
				if row1:
					#@row1= rows1[0]
					_logger.error("get_quote_total:row1row1row1[" + str(row1)+ "]")
					if row1['day1']:
						row['day1']=row['day1']-row1['day1']
					if row1['day2']:
						row['day2']=row['day2']-row1['day2']
					if row1['day3']:
						row['day3']=row['day3']-row1['day3']
					if row1['day4']:
						row['day4']=row['day4']-row1['day4']
				else:
					_logger.error("get_quote_total:sqlsqlrowrowrow[" + str(row)+ "]")
				res1.append(row)		
				#for row in res:	
				#amt += data['tot_amt']
			#return amt
		return res1
		
class report_account_reconcile(osv.AbstractModel):
	_name = 'report.account.report_account_reconcile'
	_inherit = 'report.abstract_report'
	_template = 'dincelaccount.report_account_reconcile'
	_wrapped_report_class = dcsaccount_reconcile_rpt

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
