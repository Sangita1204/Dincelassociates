import time
import datetime
from functools import partial
from openerp.osv import osv
from openerp.report import report_sxw
#from common_report_header import common_report_header
from common_report_header1 import common_report_header1


import dateutil.parser
import dateutil
from datetime import timedelta
import calendar
from calendar import monthrange

import logging
_logger = logging.getLogger(__name__)

class partner_aging_dcs(report_sxw.rml_parse, common_report_header1):

	def set_context(self, objects, data, ids, report_type=None):
		new_ids = ids
		res = {}
		return super(partner_aging_dcs, self).set_context(objects, data, new_ids, report_type=report_type)

	def __init__(self, cr, uid, name, context=None):
		super(partner_aging_dcs, self).__init__(cr, uid, name, context=context)
		self.localcontext.update( {
			'get_partner': self._get_partner,
			'lines': self._get_lines,
		})
		
		self.context = context 
	def _get_partner(self, data):
		if data.get('form', False) and data['form'].get('partner_id', False):
			return data['form']['partner_id'][1]
		return '-'
	
	def get_month_last_date(self, date):
		#first_day = date.replace(day = 1)
		last_day = date.replace(day = calendar.monthrange(date.year, date.month)[1])
		return last_day
	
	def _get_date_ranges(self,today_dt):
	
		dt_firstday=today_dt
		
		dt2_from=today_dt
		dt2_till=today_dt
		
		dt3_from=today_dt
		dt3_till=today_dt
		
		dt4_from=today_dt
		
		try:
			today_dt 	= dateutil.parser.parse(str(today_dt))
			dt_temp 	= str(today_dt.year) +"-"+str(today_dt.month)+"-1"
			dt_firstday = dateutil.parser.parse(str(dt_temp))
			
			#30-60 days = -1 mohtns
			dt2_till	= dt_firstday+timedelta(days=-1)
			dt_temp 	= str(dt2_till.year) +"-"+str(dt2_till.month)+"-1"
			dt2_from	= dateutil.parser.parse(str(dt_temp))
			
			#60-90 days = -2 months
			dt3_till	= dt2_from+timedelta(days=-1)
			dt_temp 	= str(dt3_till.year) +"-"+str(dt3_till.month)+"-1"
			dt3_from	= dateutil.parser.parse(str(dt_temp))
			
			#+90 = 3 months +
			dt4_from	= dt3_from+timedelta(days=-1)
		except Exception,e:
			_logger.error("error:_get_date_ranges[" + str(e)+ "][" + str(today_dt)+ "]")
			
		return dt_firstday, dt2_from, dt2_till, dt3_from, dt3_till, dt4_from
	
	def _get_lines(self, context):
		
		ret_res = []
		
		if context.get('form', False) and context['form'].get('partner_id', False):
			#partner_id= context['form']['partner_id'][0]
			partner_id	= context['form']['partner_id'][0]
			current_date= context['form']['date']#[0]
			
			if not current_date:
				current_date = datetime.date.today()
			current_date1 = dateutil.parser.parse(str(current_date))
			
			dt_firstday, dt2_from, dt2_till, dt3_from, dt3_till, dt4_from = self._get_date_ranges(current_date)	
			#current_date = dateutil.parser.parse(str(current_date))
			#rowt	= {'id':invoice_id,'day1':0,'day2':0,'day3':0,'day4':0}
			sql ="SELECT a.id,a.date_due,a.date_due as due_rpt,a.number,a.internal_number,a.state,a.date_invoice,a.amount_total,a.name \
					,o.origin,a.amount_tax,0 as amt_paid,0 as amt_balance,p.name as prjname,0 as day1,0 as day2,0 as day3,0 as day4 \
					FROM account_invoice a left join sale_order o on a.x_sale_order_id=o.id  \
					left join res_partner p on a.x_project_id=p.id \
					where \
					a.state not in(\'draft\',\'cancel\') and a.type in(\'out_invoice\',\'out_refund\') \
					and a.partner_id =\'%s\' and a.date_invoice <='%s' \
					order by a.date_invoice asc" % (partner_id,current_date,)
			#_logger.error("partner_statement_dcspartner_statement_dcs_sql"+str(sql))
			self.cr.execute(sql)
			res = self.cr.dictfetchall()
			for row in res:	
				invoice_id 	= row['id']	
				amt_paid	= row['amt_paid']
				amount_total= row['amount_total']
				amt_balance	= row['amt_balance']
				due_rpt		= row['date_due']
				date_due	= row['date_due']
				date_invoice	= row['date_invoice']
				try:
					
					
					
					amount_total	= float(amount_total)
					amt_paid		= float(amt_paid)
					amt_balance		= float(amt_balance)
					
					sql="select sum(p.amount) as amt_paid from dincelaccount_voucher_payline p,account_invoice a,account_voucher v where a.id=p.invoice_id and p.voucher_id=v.id and p.invoice_id='%s'" % (invoice_id)
					
					sql += " and v.date <='%s' "  % (current_date)
					
					self.cr.execute(sql)
					res1 = self.cr.dictfetchall()
					
					for row1 in res1:	
						if row1['amt_paid']:
							amt_paid += float(row1['amt_paid'])
							#_logger.error("partner_statement_dcspartner_statement_dcs_sql222"+str(sql))
					amt_balance=amount_total-amt_paid
					
					
				except Exception,e:
					_logger.error("error_aging_partner_report_getlines["+str(e)+"]")
					amt_paid=0.0
				try:
					if date_due: 
						date_due = dateutil.parser.parse(str(date_due))	
					else:
						date_due = dateutil.parser.parse(str(date_invoice))	
					due_rpt = dateutil.parser.parse(str(due_rpt))
					if due_rpt <= current_date1:
						due_rpt = None	
				except Exception,e:
					due_rpt = None
					
				row['amt_paid']		= amt_paid
				row['amt_balance']	= amt_balance
				row['due_rpt']		= due_rpt
				
				if amt_balance and abs(amt_balance)>0.1: #for rounding margin is 10cents
					
					if date_due <= dt4_from:
						row['day4']	= amt_balance
					elif date_due >= dt2_from and  date_due <= dt2_till:
						row['day2']	= amt_balance
					elif date_due >= dt3_from and  date_due <= dt3_till:
						row['day3']	= amt_balance
					else:	
						row['day1']	= amt_balance
					ret_res.append(row)	
			'''sql ="select a.date_due,a.number,a.internal_number,a.amount_untaxed,a.amount_tax,a.state,a.date_invoice,a.name \
				  ,o.origin,a.amount_total,b.amt_paid,p.name as prjname \
				  from account_invoice a left join sale_order o on a.x_sale_order_id=o.id \
				  left join res_partner p on o.x_project_id=p.id \
				  left join dincelaccount_voucher_payment b on a.id=b.invoice_id \
				  where a.state='open' and a.partner_id=%s" #not in('draft','cancel','paid') #and a.type='out_invoice' 
			#_logger.error("partner_statement_dcspartner_statement_dcs-"+str(partner_id))
			self.cr.execute(sql,(partner_id,))
			res = self.cr.dictfetchall()
			'''
		return ret_res
		
	def _get_lines_xx(self, context):
		res_ret = []
		if context.get('form', False) and context['form'].get('partner_id', False):
			partner_id= context['form']['partner_id'][0]
			#current_date = datetime.date.today()
			current_date= context['form']['date']#[0]
			if not current_date:
				current_date = datetime.date.today()
			#_logger.error("partner_aging_dcspartner_aging_dcs-"+str(partner_id))
			sql ='SELECT id,internal_number,state,date_invoice,amount_total,(\'%s\'-date_invoice)  as dtdiff, \
					case when (\'%s\'-date_invoice) < 30 then amount_total else 0 end as "day1", \
					case when ((\'%s\'-date_invoice) between 30 and 60) then amount_total else 0 end as "day2", \
					case when ((\'%s\'-date_invoice) between 61 and 90) then amount_total else 0 end as "day3", \
					case when ((\'%s\'-date_invoice) >90) then amount_total else 0 end as "day4" \
					FROM   account_invoice where date_invoice   is not null \
					and state not in(\'draft\',\'cancel\') and type in(\'out_invoice\',\'out_refund\') and partner_id =%s order by date_invoice'
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
			#_logger.error("get_quote_total:sqlsql[" + str(sql)+ "]")
			#-->dincelaccount_voucher_payment is view defined in dincelaccount_voucher.py ...
			self.cr.execute(sql)
			res = self.cr.dictfetchall()
			for row in res:	
				invoice_id = row['id']
				#amt_paid=row['amt_paid']
				#amount_total=row['amount_total']
				#amt_balance=row['amt_balance']
				try:
					#amount_total=float(amount_total)
					#amt_paid=float(amt_paid)
					#amt_balance=float(amt_balance)
					sql ='SELECT  \
						case when (\'%s\'-v.date) < 30 then b.amount else 0 end as "day1", \
						case when ((\'%s\'-v.date) between 30 and 60) then b.amount else 0 end as "day2", \
						case when ((\'%s\'-v.date) between 61 and 90) then b.amount else 0 end as "day3", \
						case when ((\'%s\'-v.date) >90) then b.amount else 0 end as "day4" \
						FROM   account_invoice a left join dincelaccount_voucher_payline b on a.id=b.invoice_id  \
						left join account_voucher v on v.id=b.voucher_id \
						where   v.date <=\'%s\' and \
						a.state not in(\'draft\',\'cancel\')  and a.type in(\'out_invoice\',\'out_refund\') and a.partner_id =%s and a.id=%s' 
					#self.cr.execute(sql,(str(current_date),str(current_date),str(current_date),str(current_date),str(current_date),partner_id,))
					sql = sql % (str(current_date),str(current_date),str(current_date),str(current_date),str(current_date),partner_id,invoice_id,)
					_logger.error("get_quote_total:sqlsql222[" + str(sql)+ "]")
					self.cr.execute(sql)
					res1 = self.cr.dictfetchall()
					for row1 in res1:	
						if row1['day1']:
							row['day1']=row['day1']-row1['day1']
						if row1['day2']:
							row['day2']=row['day2']-row1['day2']
						if row1['day3']:
							row['day3']=row['day3']-row1['day3']
						if row1['day4']:
							row['day4']=row['day4']-row1['day4']
					#if amt_balance<0:
						
				except Exception,e:
					pass
				#row['amt_paid']	=amt_paid
				#row['amt_balance']	=amt_balance
				
				if abs(row['day1'])>0.1 or abs(row['day2'])>0 or abs(row['day3'])>0 or abs(row['day4'])>0: #for rounding margin is 10cents
					_bal=row['day1']+row['day2']+row['day3']+row['day4']
					if abs(_bal)>0.10:#for rounding margin is 10cents
						res_ret.append(row)
					
				#sql ='SELECT  \
				#	case when (\'%s\'-a.date_invoice) < 30 then b.amt_paid else 0 end as "day1", \
				#	case when ((\'%s\'-a.date_invoice) between 30 and 60) then b.amt_paid else 0 end as "day2", \
				#	case when ((\'%s\'-a.date_invoice) between 61 and 90) then b.amt_paid else 0 end as "day3", \
				#	case when ((\'%s\'-a.date_invoice) >90) then b.amt_paid else 0 end as "day4" \
				#	FROM   account_invoice a left join dincelaccount_voucher_payment b on a.id=b.invoice_id  where a.date_invoice   is not null \
				#	and a.state=\'open\' and a.type in(\'out_invoice\',\'out_refund\') and a.partner_id =%s and a.id=%s' 
				#self.cr.execute(sql,(str(current_date),str(current_date),str(current_date),str(current_date),str(current_date),partner_id,))
				#sql = sql % (str(current_date),str(current_date),str(current_date),str(current_date),partner_id,invoice_id,)
				#_logger.error("get_quote_total:sqlsql222[" + str(sql)+ "]")
				##self.cr.execute(sql)
				#row1 	= self.cr.dictfetchone()
				#_logger.error("get_quote_total:sqlsql222[" + str(sql)+ "]")
				#if row1:
				#	#@row1= rows1[0]
				#	#_logger.error("get_quote_total:row1row1row1[" + str(row1)+ "]")
				#	if row1['day1']:
				#		row['day1']=row['day1']-row1['day1']
				#	if row1['day2']:
				#			row['day2']=row['day2']-row1['day2']
				#	if row1['day3']:
				#		row['day3']=row['day3']-row1['day3']
				#	if row1['day4']:
				#		row['day4']=row['day4']-row1['day4']
				#else:
				#	_logger.error("get_quote_total:sqlsqlrowrowrow[" + str(row)+ "]")
				#res1.append(row)		
				#for row in res:	
				#amt += data['tot_amt']
			#return amt
		return res_ret
		
class report_partner_aging(osv.AbstractModel):
	_name = 'report.account.report_partner_aging'
	_inherit = 'report.abstract_report'
	_template = 'dincelaccount.report_partner_aging'
	_wrapped_report_class = partner_aging_dcs

class report_partner_aging_pdf(osv.AbstractModel):
	_name = 'report.account.report_partner_aging_pdf'
	_inherit = 'report.abstract_report'
	_template = 'dincelaccount.report_partner_aging'
	_wrapped_report_class = partner_aging_dcs
	
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
