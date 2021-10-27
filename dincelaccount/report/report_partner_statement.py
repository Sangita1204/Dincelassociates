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

class partner_statement_dcs(report_sxw.rml_parse, common_report_header1):

	def set_context(self, objects, data, ids, report_type=None):
		new_ids = ids
		res = {}
		return super(partner_statement_dcs, self).set_context(objects, data, new_ids, report_type=report_type)

	def __init__(self, cr, uid, name, context=None):
		super(partner_statement_dcs, self).__init__(cr, uid, name, context=context)
		self.localcontext.update( {
			'get_partner': self._get_partner,
			'get_contact': self._get_contact,
			'lines': self._get_lines,
			'get_amount_qc': self._get_amount_qc,
		})
		
		self.context = context 
	def _get_contact(self, data):
		res = []
		if data.get('form', False) and data['form'].get('partner_id', False):
			partner_id= data['form']['partner_id'][0]
			sql ="select a.name,b.name as title,a.mobile from res_partner a left join dincelcrm_contact_type t on a.x_ctype_id=t.id left join res_partner_title b on a.title=b.id where a.parent_id=%s and t.code='AC'"
			self.cr.execute(sql,(partner_id,))
			row1 = self.cr.dictfetchone()
			if row1:
				row={}
				row['name']		= row1['name']
				row['title']	= row1['title']
				row['mobile']	= row1['mobile']
				res.append(row)
			#_logger.error("_get_contact:resres[" + str(res)+ "]")
		return res
		
	def _get_partner(self, data):
		if data.get('form', False) and data['form'].get('partner_id', False):
			return data['form']['partner_id'][1]
		return '-'
	
	def _get_days_diff(self,dtinv,today_dt):
		#dt_curr=str(dt_curr)
		#date_format = "%Y-%m-%d"
		#dt1=str(dt1)
		try:
			today_dt 	= dateutil.parser.parse(str(today_dt))
			dtfrom2 	= dateutil.parser.parse(str(dtinv))
			delta 		= today_dt - dtfrom2
			_diff		= delta.days
		except Exception,e:
			_logger.error("_get_contact:_get_days_diff_get_days_diff[" + str(today_dt)+ "][" + str(dtinv)+ "]")
			_diff=0
		return _diff
	
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
		
	def _get_due_terms(self,dt_due,today_dt):
		#dt_curr=str(dt_curr)
		#date_format = "%Y-%m-%d"
		#dt1=str(dt1)
		try:
			
			today_dt 	= dateutil.parser.parse(str(today_dt))
			dt_temp 	= str(today_dt.year) +"-"+str(today_dt.month)+"-1"
			dt_firstday = dateutil.parser.parse(str(dt_temp))
			#current = between dt_firstday & today_dt
			#30-60 days = -1 mohtns
			#60-
			dtfrom2 	= dateutil.parser.parse(str(dtinv))
			delta 		= today_dt - dtfrom2
			_diff		= delta.days
		except Exception,e:
			_logger.error("_get_contact:_get_days_diff_get_days_diff[" + str(today_dt)+ "][" + str(dtinv)+ "]")
			_diff=0
		return _diff
		
	def _get_amount_qc(self, context):
		res1 = []
		res=self._get_lines(context)
		
		current_date= context['form']['date']#[0]
		if not current_date:
			current_date = datetime.date.today()
			
		dt_firstday, dt2_from, dt2_till, dt3_from, dt3_till, dt4_from = self._get_date_ranges(current_date)	
		#current_date = dateutil.parser.parse(str(current_date))
		#_logger.error("_get_contact:_get_date_ranges[%s][%s][%s][%s][%s][%s]" % (dt_firstday, dt2_from, dt2_till, dt3_from, dt3_till, dt4_from))
		
		for row in res:	
			try:
				invoice_id 	= row['id']
				date_invoice= row['date_invoice']
				amount_total= row['amount_total']
				amt_paid	= row['amt_paid']
				date_due	= row['date_due']
				amt_net		= amount_total-amt_paid
				if date_due:
					date_due = dateutil.parser.parse(str(date_due))
				else:
					date_due =dateutil.parser.parse(str(date_invoice))
				#a = datetime.strptime(date_invoice, date_format)
				#b = datetime.strptime(current_date, date_format)
				#delta = b - a
				#_diff	= self._get_days_diff(date_invoice,current_date)
				''' example data as below
				[2017-02-01 00:00:00] > dt_firstday

				[2017-01-01 00:00:00] > dt2_from
				[2017-01-31 00:00:00] > dt2_till

				[2016-12-01 00:00:00] > dt3_from
				[2016-12-31 00:00:00] > dt3_till

				[2016-11-30 00:00:00] > dt4_from '''
				rowt	= {'id':invoice_id,'day1':0,'day2':0,'day3':0,'day4':0}
				if date_due<=dt4_from:
					rowt['day4']	= amt_net
				elif date_due>=dt2_from and  date_due<=dt2_till:
					rowt['day2']	= amt_net
				elif date_due>=dt3_from and  date_due<=dt3_till:
					rowt['day3']	= amt_net
				else:	
					rowt['day1']	= amt_net
				
				#str1="00"
				#if date_due<=current_date:
				#	row['date_due']= None
				#	str1="11"
				_logger.error("error:_get_amount_qc_get_amount_qc[%s][%s][%s][%s]" % (str(date_due), current_date,invoice_id, amt_net))		
				res1.append(rowt)
			except Exception,e:
				_logger.error("error:_get_amount_qc_get_amount_qc[%s]" % (str(e)))
				pass
		#
		#if context.get('form', False) and context['form'].get('partner_id', False):
		#	partner_id= context['form']['partner_id'][0]
		#	current_date= context['form']['date'][0]
		#	if not current_date:
		#		current_date = datetime.date.today()
		#	
		#	sql ='SELECT id,internal_number,state,date_invoice,amount_total,(\'%s\'-date_invoice)  as dtdiff, \
		#			case when (\'%s\'-date_invoice) < 30 then amount_total else 0 end as "day1", \
		#			case when ((\'%s\'-date_invoice) between 30 and 60) then amount_total else 0 end as "day2", \
		#			case when ((\'%s\'-date_invoice) between 61 and 90) then amount_total else 0 end as "day3", \
		#			case when ((\'%s\'-date_invoice) >90) then amount_total else 0 end as "day4" \
		#			FROM   account_invoice where date_invoice   is not null \
		#			and state not in(\'draft\',\'cancel\') and type in(\'out_invoice\',\'out_refund\') and partner_id =%s order by date_invoice asc' #state=\'open\' and 
		#	'''		
		#	sql ='SELECT a.internal_number,a.state,a.date_invoice,(\'%s\'-a.date_invoice)  as dtdiff, \
		#			case when (\'%s\'-a.date_invoice) < 30 then (a.amount_total-b.amt_paid) else 0 end as "day1", \
		#			case when ((\'%s\'-a.date_invoice) between 30 and 60) then (a.amount_total-b.amt_paid) else 0 end as "day2", \
		#			case when ((\'%s\'-a.date_invoice) between 61 and 90) then (a.amount_total-b.amt_paid)else 0 end as "day3", \
		#			case when ((\'%s\'-a.date_invoice) >90) then (a.amount_total-b.amt_paid) else 0 end as "day4" \
		#			FROM   account_invoice a left join dincelaccount_voucher_payment b on a.id=b.invoice_id  where a.date_invoice   is not null \
		#			and a.state=\'open\' and a.partner_id =%s order by a.date_invoice''' 
		#	#self.cr.execute(sql,(str(current_date),str(current_date),str(current_date),str(current_date),str(current_date),partner_id,))
		#	sql = sql % (str(current_date),str(current_date),str(current_date),str(current_date),str(current_date),partner_id,)
		#	#_logger.error("get_quote_total:sqlsql[" + str(sql)+ "]")
		#	self.cr.execute(sql)
		#	res = self.cr.dictfetchall()
		#	for row in res:	
		#		invoice_id = row['id']
		#		'''sql ='SELECT  \
		#			case when (\'%s\'-a.date_invoice) < 30 then b.amt_paid else 0 end as "day1", \
		#			case when ((\'%s\'-a.date_invoice) between 30 and 60) then b.amt_paid else 0 end as "day2", \
		#			case when ((\'%s\'-a.date_invoice) between 61 and 90) then b.amt_paid else 0 end as "day3", \
		#			case when ((\'%s\'-a.date_invoice) >90) then b.amt_paid else 0 end as "day4" \
		#			FROM   account_invoice a left join dincelaccount_voucher_payment b on a.id=b.invoice_id  where a.date_invoice   is not null \
		#			and a.state not in(\'draft\',\'cancel\') and a.type in(\'out_invoice\',\'out_refund\') and a.partner_id =%s and a.id=%s' #a.state=\'open\' and 
		#		#self.cr.execute(sql,(str(current_date),str(current_date),str(current_date),str(current_date),str(current_date),partner_id,))
		#		sql = sql % (str(current_date),str(current_date),str(current_date),str(current_date),partner_id,invoice_id,)
		#		'''
		#		'''sql ='SELECT  \
		#			case when (\'%s\'-b.date) < 30 then b.amt_paid else 0 end as "day1", \
		#			case when ((\'%s\'-b.date) between 30 and 60) then b.amt_paid else 0 end as "day2", \
		#			case when ((\'%s\'-b.date) between 61 and 90) then b.amt_paid else 0 end as "day3", \
		#			case when ((\'%s\'-b.date) >90) then b.amt_paid else 0 end as "day4" \
		#			FROM   account_invoice a left join dincelaccount_voucher_payline b on a.id=b.invoice_id  where a.date_invoice   is not null \
		#			and a.state not in(\'draft\',\'cancel\') and a.type in(\'out_invoice\',\'out_refund\') and a.partner_id =%s and a.id=%s' #a.state=\'open\' and 
		#		#self.cr.execute(sql,(str(current_date),str(current_date),str(current_date),str(current_date),str(current_date),partner_id,))
		#		sql = sql % (str(current_date),str(current_date),str(current_date),str(current_date),partner_id,invoice_id,)
		#		#_logger.error("get_quote_total:sqlsql222[" + str(sql)+ "]")
		#		self.cr.execute(sql)
		#		row1 	= self.cr.dictfetchone()
		#		#_logger.error("get_quote_total:sqlsql222[" + str(sql)+ "]")
		#		if row1:
		#			#@row1= rows1[0]
		#			#_logger.error("get_quote_total:row1row1row1[" + str(row1)+ "]")
		#			if row1['day1']:
		#				#row['day1_paid']=row1['day1']
		#				row['day1']=row['day1']-row1['day1']
		#			if row1['day2']:
		#				#row['day2_paid']=row1['day2']
		#				row['day2']=row['day2']-row1['day2']
		#			if row1['day3']:
		#				#row['day3_paid']=row1['day3']
		#				row['day3']=row['day3']-row1['day3']
		#			if row1['day4']:
		#				#row['day4_paid']=row1['day4']
		#				row['day4']=row['day4']-row1['day4']
		#		#else:
		#		#	_logger.error("get_quote_total:sqlsqlrowrowrow[" + str(row)+ "]")
		#		res1.append(row)	'''	
		#		#for row in res:	
		#		#amt += data['tot_amt']
		#	#return amt
		return res1
		
	def _get_lines(self, context):
		
		ret_res = []
		
		if context.get('form', False) and context['form'].get('partner_id', False):
			#partner_id= context['form']['partner_id'][0]
			partner_id	= context['form']['partner_id'][0]
			current_date= context['form']['date']#[0]
			
			if not current_date:
				current_date = datetime.date.today()
			
			current_date1 = dateutil.parser.parse(str(current_date))
			sql ="SELECT a.id,a.date_due,a.date_due as due_rpt,a.number,a.internal_number,a.state,a.date_invoice,a.amount_total,a.name \
					,o.origin,a.amount_tax,0 as amt_paid,0 as amt_balance,p.name as prjname,a.payment_term,upper(a.x_inv_type) as inv_type  \
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
				payment_term= row['payment_term']
				_term		= ""
				
				try:
					if payment_term:
						sql="select x_payterm_code from account_payment_term where id='%s'" % (payment_term)	
						self.cr.execute(sql)
						row1 = self.cr.fetchone()
						if row1 and row1[0]:
							_term = str(row1[0])
				except Exception,e:
					_term = ""
					
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
					amt_balance = amount_total-amt_paid
					#if amt_balance<0:
					
				except Exception,e:
					amt_paid = 0.0
					#_logger.error("error_payment_partner_statement_dcspartner_statement_dcs_sql"+str(e))
				try:
					if due_rpt:
						due_rpt = dateutil.parser.parse(str(due_rpt))
						if due_rpt <= current_date1:
							due_rpt = None
						else:
							due_rpt = str(due_rpt.year) +"-"+str(due_rpt.month)+"-" + str(due_rpt.day)
				except Exception,e:
					due_rpt = None
					
				row['amt_paid']		= amt_paid
				row['amt_balance']	= amt_balance
				row['due_rpt']		= due_rpt
				row['payment_term']	= _term.upper()
				if amt_balance and abs(amt_balance)>0.1: #for rounding margin is 10cents
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
		
class report_partner_statement(osv.AbstractModel):
	_name = 'report.account.report_partner_statement'
	_inherit = 'report.abstract_report'
	_template = 'dincelaccount.report_partner_statement'
	_wrapped_report_class = partner_statement_dcs

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
class report_partner_statement_pdf(osv.AbstractModel):
	_name = 'report.account.report_partner_statement_pdf'
	_inherit = 'report.abstract_report'
	_template = 'dincelaccount.report_partner_statement'
	_wrapped_report_class = partner_statement_dcs		