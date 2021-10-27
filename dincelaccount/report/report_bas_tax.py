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

class bas_report_dcs(report_sxw.rml_parse, common_report_header1):

	def set_context(self, objects, data, ids, report_type=None):
		new_ids = ids
		res = {}
		return super(bas_report_dcs, self).set_context(objects, data, new_ids, report_type=report_type)

	def __init__(self, cr, uid, name, context=None):
		super(bas_report_dcs, self).__init__(cr, uid, name, context=context)
		self.localcontext.update( {
			'lines': self._get_lines,
		})
		self.context = context 
	def _get_details(self,_taxcodeid,date_from,date_to,context=None):
		sql="""select '1' as level,i.id,
				i.number AS number,
				t.amount  AS tax_amount,
				i.type  AS type,
				i.state  AS state,
				t.tax_code_id  AS tax_code_id,
				c.name  AS tax_name,
				c.code  AS tax_code,
				t.base_amount  AS base_amount,
				i.date_invoice  AS date_invoice,
				i.period_id  AS period_id,
				i.company_id  AS company_id,
				p.name  AS partner_name,
				i.partner_id AS partner_id	
				from account_invoice i,account_invoice_tax t,account_tax_code c,res_partner p  
				where i.id=t.invoice_id and t.tax_code_id=c.id and i.partner_id=p.id and i.state!='draft'""" #no offset as per Felix....///2017/04/10
		
		sql +=" and i.date_invoice between '%s' and '%s' "  % (date_from, date_to)
		if _taxcodeid:
			sql +=" and c.id='%s'"  % (_taxcodeid)
		#_logger.error("sqltaxreport taxreport-0" + str(sql))	
		self.cr.execute(sql)
		ret_res = self.cr.dictfetchall()
		_rows=[]
		_sale=0.0
		_purchase=0.0
		_taxsale=0.0
		_taxpur=0.0
		_level='1'
		for row in ret_res:
			_sale1=0.0
			_taxsale1=0.0
			_purchase1=0.0
			_taxpur1=0.0
			
			if row['type'] in ["in_invoice","in_refund"]:
				_purchase1=row['base_amount']
				_taxpur1=row['tax_amount']
				_purchase+=(_purchase1+_taxpur1)
				_taxpur+=_taxpur1
			elif row['type'] in ["out_invoice","out_refund"]:
				_sale1=row['base_amount']
				_taxsale1=row['tax_amount']
				_sale+=(_sale1+_taxsale1)
				_taxsale+=_taxsale1
			row1={'level':_level, 
				'id':row['id'], 
				'number':row['number'], 
				'partner':row['partner_name'], 
				'date_invoice':row['date_invoice'], 
				'tax_name':'', 
				'tax_code':'', 
				'type':row['type'], 
				'state':row['state'], 
				'sale':_sale1, 
				'purchase':_purchase1, 
				'sale_tax':_taxsale1, 
				'purchase_tax':_taxpur1, 
				}
			_rows.append(row1)	
		return _sale,_purchase,_taxsale,_taxpur, _rows #=self._get_details(_taxid,date_from,date_to)
	def _get_lines(self, context=None):
		date_to=None
		ret_res = []
		rows=[]
		
		#ctx['fiscalyear'] = form['fiscalyear_id']
		#account.period
		period=self.pool.get('account.period')#.browse(cr, uid, _id, context)
		#if context.get('form', False) and context['form'].get('partner_id', False):
		#partner_id= context['form']['partner_id'][0]
		#partner_id	= context['form']['partner_id'][0]
		#current_date= context['form']['date']#[0]
		if context['form']['filter'] == 'filter_period':
			period_from = context['form']['period_from']
			period_to = context['form']['period_to']
			obj =period.browse(self.cr, self.uid, period_from, context)
			date_from=obj.date_start
			obj =period.browse(self.cr, self.uid, period_to, context)
			date_to=obj.date_stop
			
		elif context['form']['filter'] == 'filter_date':
			date_from = context['form']['date_from']
			date_to =  context['form']['date_to']
		sql="select * from account_tax where active='t' order by sequence"	
		self.cr.execute(sql)
		ret_res = self.cr.dictfetchall()
		
		for row in ret_res:	
			_level= '0'
			_taxcode=row['description']
			_taxname=row['name']
			_taxcodeid=row['tax_code_id']
			_number=''
			_id=''
			_sale,_purchase,_taxsale,_taxpur,_rows=self._get_details(_taxcodeid,date_from,date_to)
			row1={'level':_level, 
				'id':0, 
				'number':'', 
				'partner':'',
				'date_invoice':'',
				'tax_code':_taxcode, 
				'tax_name':_taxname, 
				'type':'', 
				'state':'', 
				'sale':_sale, 
				'purchase':_purchase, 
				'sale_tax':_taxsale, 
				'purchase_tax':_taxpur, 
				}
			rows.append(row1)	
			for row1 in _rows:
				rows.append(row1)
			#if date_to:	
			
		 
			#ret_res = self.cr.dictfetchall()
		return rows
		
class report_bas_dcs(osv.AbstractModel):
	_name = 'report.account.report_bas_dcs' #return self.pool['report'].get_action(cr, uid, [], 'account.report_tax_dcs', data=datas, context=context)
	_inherit = 'report.abstract_report'
	_template = 'dincelaccount.report_tax_dcs_new' #.xml filename....
	_wrapped_report_class = bas_report_dcs

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
class report_bas_dcs_pdf(osv.AbstractModel):
	_name = 'report.account.report_bas_dcs_pdf'
	_inherit = 'report.abstract_report'
	_template = 'dincelaccount.report_tax_dcs_new'
	_wrapped_report_class = bas_report_dcs		