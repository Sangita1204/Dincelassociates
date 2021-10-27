import time
from lxml import etree
import urllib2
from openerp.osv import fields, osv
from openerp.osv.orm import setup_modifiers
from openerp.tools.translate import _
from account_trialbalance import account_balance1
from account_financial_report1 import report_account_common1
from report_bas_tax import bas_report_dcs
import subprocess
from subprocess import Popen, PIPE, STDOUT
import logging
_logger = logging.getLogger(__name__)

class dcs_account_common_report(osv.osv_memory):
	_name = "dcs.account.common.report"
	_description = "DCS Account Common Report"
	_columns = {
		'chart_account_id': fields.many2one('account.account', 'Chart of Account', help='Select Charts of Accounts', required=True, domain = [('parent_id','=',False)]),
		'company_id': fields.related('chart_account_id', 'company_id', type='many2one', relation='res.company', string='Company', readonly=True),
		'fiscalyear_id': fields.many2one('account.fiscalyear', 'Fiscal Year', help='Keep empty for all open fiscal year'),
		'filter': fields.selection([('filter_no', 'No Filters'), ('filter_date', 'Date'), ('filter_period', 'Periods')], "Filter by", required=True),
		'period_from': fields.many2one('account.period', 'Start Period'),
		'period_to': fields.many2one('account.period', 'End Period'),
		'journal_ids': fields.many2many('account.journal', string='Journals', required=True),
		'date_from': fields.date("Start Date"),
		'date_to': fields.date("End Date"),
		'target_move': fields.selection([('posted', 'All Posted Entries'),('all', 'All Entries'),], 'Target Moves', required=True),
		'region_id': fields.many2one('dincelaccount.region', 'A/c Region'),
		'coststate_id':fields.many2one("res.country.state","Cost Centre"),
		'display_account': fields.selection([('all','All'), ('movement','With movements'),
                                            ('not_zero','With balance is not equal to 0'),
                                            ],'Display Accounts', required=True),
	}
	
	def onchange_filter(self, cr, uid, ids, filter='filter_no', fiscalyear_id=False, context=None):
		res = {'value': {}}
		if filter == 'filter_no':
			res['value'] = {'period_from': False, 'period_to': False, 'date_from': False ,'date_to': False}
		if filter == 'filter_date':
			res['value'] = {'period_from': False, 'period_to': False, 'date_from': time.strftime('%Y-01-01'), 'date_to': time.strftime('%Y-%m-%d')}
		if filter == 'filter_period' and fiscalyear_id:
			start_period = end_period = False
			cr.execute('''
					SELECT * FROM (SELECT p.id
						FROM account_period p
						LEFT JOIN account_fiscalyear f ON (p.fiscalyear_id = f.id)
						WHERE f.id = %s
						AND p.special = false
						ORDER BY p.date_start ASC, p.special ASC
						LIMIT 1) AS period_start
					UNION ALL
					SELECT * FROM (SELECT p.id
						FROM account_period p
						LEFT JOIN account_fiscalyear f ON (p.fiscalyear_id = f.id)
						WHERE f.id = %s
						AND p.date_start < NOW()
						AND p.special = false
						ORDER BY p.date_stop DESC
						LIMIT 1) AS period_stop''', (fiscalyear_id, fiscalyear_id))
			periods =  [i[0] for i in cr.fetchall()]
			if periods and len(periods) > 1:
				start_period = periods[0]
				end_period = periods[1]
			res['value'] = {'period_from': start_period, 'period_to': end_period, 'date_from': False, 'date_to': False}
		return res


	def _get_account(self, cr, uid, context=None):
		user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
		accounts = self.pool.get('account.account').search(cr, uid, [('parent_id', '=', False), ('company_id', '=', user.company_id.id)], limit=1)
		return accounts and accounts[0] or False
	def _get_fiscalyear(self, cr, uid, context=None):
		if context is None:
			context = {}
		now = time.strftime('%Y-%m-%d')
		company_id = False
		ids = context.get('active_ids', [])
		if ids and context.get('active_model') == 'account.account':
			company_id = self.pool.get('account.account').browse(cr, uid, ids[0], context=context).company_id.id
		else:  # use current company id
			company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
		domain = [('company_id', '=', company_id), ('date_start', '<', now), ('date_stop', '>', now)]
		fiscalyears = self.pool.get('account.fiscalyear').search(cr, uid, domain, limit=1)
		return fiscalyears and fiscalyears[0] or False

	def _get_all_journal(self, cr, uid, context=None):
		return self.pool.get('account.journal').search(cr, uid ,[])
	_defaults = {
		'fiscalyear_id': _get_fiscalyear,
		'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'account.common.report',context=c),
		'journal_ids': _get_all_journal,
		'filter': 'filter_no',
		'chart_account_id': _get_account,
		'target_move': 'posted',
		'display_account': 'movement',
	}
	
	def _build_contexts_dcs(self, cr, uid, ids, data, context=None):
		if context is None:
			context = {}
		#slog = '.'.join(data)	
		#_logger.error("check_report1-3-"+slog)	 		
		result = {}
		result['fiscalyear']  = 'fiscalyear_id' in data['form'] and data['form']['fiscalyear_id'] or False
		result['journal_ids'] = 'journal_ids' in data['form'] and data['form']['journal_ids'] or False
		result['chart_account_id'] = 'chart_account_id' in data['form'] and data['form']['chart_account_id'] or False
		result['state'] = 'target_move' in data['form'] and data['form']['target_move'] or ''
		if data['form']['filter'] == 'filter_date':
			result['date_from'] = data['form']['date_from']
			result['date_to'] = data['form']['date_to']
		elif data['form']['filter'] == 'filter_period':
			if not data['form']['period_from'] or not data['form']['period_to']:
				raise osv.except_osv(_('Error!'),_('Select a starting and an ending period.'))
			result['period_from'] 	= data['form']['period_from']
			result['period_to'] 	= data['form']['period_to']
		
		#slog = '.'.join(result)	+ str(result['fiscalyear'])+ "]"
		#_logger.error("check_report1-3-a-"+slog)	 	
		return result
	
	def print_report_dcs_tb(self, cr, uid, ids, context=None):
		return self.print_report_dcs(cr, uid, ids, context=context)	
	
	def csv_report_dcs_tb(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		_ids=[]	
		_id=0
		for record in self.browse(cr, uid, ids, context=context):	#record = self.browse(cr, uid, ids[0], context=context)
			_id= record.chart_account_id.id or False
			_ids=[_id]
		data = {}
		data = self._pre_print_report_dcs(cr, uid, ids, data, context=context) 
		
		tb1 = account_balance1(cr, uid, "name1", context=context)#tb1=account_balance1 #self.pool.get('report.account.account.balance1')
		tb1.ids=_ids
		#_logger.error("print_report_dcs-tb1tb1tb_ids_ids_ids[" + str(_ids)+"]")
		_lines=tb1.lines(data['form'])
		_csv="Code,Name,,dr,cr,balance,\n"
		fname="trial_balance.csv"
		_len=len(_lines)
		for line in _lines:
			if line['type']=="view":
				_str="::"
			else:
				_str=""
			_lvl=int(line['level'])	
			_str2=""
			while _lvl>0:
				_lvl-=1
				_str2+=" "
			_csv+="\" %s\",\" %s\",\"%s\",\"%s\",\"%s\",\"%s\",\n" % (line['code'],_str2+line['name'],_str,line['debit'],line['credit'],line['balance'])
		
		temp_path="/var/tmp/odoo/account/"#+fname	
		save_as=temp_path+fname	
		
		with open(save_as, 'w') as the_file:
			the_file.write(_csv)
		return {
				'name': 'Balance Sheet',
				'res_model': 'ir.actions.act_url',
				'type' : 'ir.actions.act_url',
				'url': '/web/binary/download_file?model=sale.order&field=datas&id=%s&path=%s&filename=%s' % (str(_id),temp_path,fname),
				'context': context}
					
	def print_report_dcs(self, cr, uid, ids, context=None):
		'''if context is None:
			context = {}
		#_logger.error("print_report_dcs-print_report_dcs_tbprint_report_dcs_tb")	 	
		data = {}
		data['ids'] = context.get('active_ids', [])
		data['model'] = context.get('active_model', 'ir.ui.menu')
		data['form'] = self.read(cr, uid, ids, ['date_from',  'date_to',  'fiscalyear_id', 'journal_ids', 'period_from', 'period_to',  'filter',  'chart_account_id', 'target_move','region_id','coststate_id'], context=context)[0]
		for field in ['fiscalyear_id', 'chart_account_id', 'period_from', 'period_to']:
			if isinstance(data['form'][field], tuple):
				data['form'][field] = data['form'][field][0]
		used_context = self._build_contexts_dcs(cr, uid, ids, data, context=context)
		data['form']['periods'] = used_context.get('periods', False) and used_context['periods'] or []
		data['form']['used_context'] = dict(used_context, lang=context.get('lang', 'en_US'))'''
		data = {}
		return self._print_report_dcs(cr, uid, ids, data, context=context)	
		
	def _pre_print_report_dcs(self, cr, uid, ids, data, context=None):
		if context is None:
			context = {}
		if context is None:
			context = {}
		#_logger.error("print_report_dcs-print_report_dcs_tbprint_report_dcs_tb")	 	
		data = {}
		data['ids'] = context.get('active_ids', [])
		data['model'] = context.get('active_model', 'ir.ui.menu')
		data['form'] = self.read(cr, uid, ids, ['date_from',  'date_to',  'fiscalyear_id', 'journal_ids', 'period_from', 'period_to',  'filter',  'chart_account_id', 'target_move','region_id','coststate_id'], context=context)[0]
		for field in ['fiscalyear_id', 'chart_account_id', 'period_from', 'period_to']:
			if isinstance(data['form'][field], tuple):
				data['form'][field] = data['form'][field][0]
		used_context = self._build_contexts_dcs(cr, uid, ids, data, context=context)
		data['form']['periods'] = used_context.get('periods', False) and used_context['periods'] or []
		data['form']['used_context'] = dict(used_context, lang=context.get('lang', 'en_US'))	
		data['form'].update(self.read(cr, uid, ids, ['display_account'], context=context)[0])
		return data
	def _print_report_dcs(self, cr, uid, ids, data, context=None):
		#_logger.error("check_report1-2")	 	
		data = self._pre_print_report_dcs(cr, uid, ids, data, context=context)
		return self.pool['report'].get_action(cr, uid, [], 'account.report_trialbalance1', data=data, context=context)
		
class dcs_accounting_report(osv.osv_memory):
	_name = "dcs.accounting.report"
	_inherit = "dcs.account.common.report"
	#_description = "Accounting Report New1"
	_columns = {
		'enable_filter': fields.boolean('Enable Comparison'),
		'account_report_id': fields.many2one('account.financial.report', 'Account Reports', required=True),
		'label_filter': fields.char('Column Label', help="This label will be displayed on report to show the balance computed for the given comparison filter."),
		'fiscalyear_id_cmp': fields.many2one('account.fiscalyear', 'Fiscal Year', help='Keep empty for all open fiscal year'),
		'filter_cmp': fields.selection([('filter_no', 'No Filters'), ('filter_date', 'Date'), ('filter_period', 'Periods')], "Filter by", required=True),
		'period_from_cmp': fields.many2one('account.period', 'Start Period'),
		'period_to_cmp': fields.many2one('account.period', 'End Period'),
		'date_from_cmp': fields.date("Start Date"),
		'date_to_cmp': fields.date("End Date"),
		'debit_credit': fields.boolean('Display Debit/Credit Columns', help="This option allows you to get more details about the way your balances are computed. Because it is space consuming, we do not allow to use it while doing a comparison."),
	}

	def _get_account_report_dcs(self, cr, uid, context=None):
		# TODO deprecate this it doesnt work in web
		menu_obj = self.pool.get('ir.ui.menu')
		report_obj = self.pool.get('account.financial.report')
		report_ids = []
		if context.get('active_id'):
			menu = menu_obj.browse(cr, uid, context.get('active_id')).name
			report_ids = report_obj.search(cr, uid, [('name','ilike',menu)])
		return report_ids and report_ids[0] or False

	_defaults = {
		'filter_cmp': 'filter_no',
		'target_move': 'posted',
		'account_report_id': _get_account_report_dcs,
	}
	
	def _print_report_dcs(self, cr, uid, ids, data, context=None):
		#data['form'].update(self.read(cr, uid, ids, ['date_from_cmp',  'debit_credit', 'date_to_cmp',  'fiscalyear_id_cmp', 'period_from_cmp', 'period_to_cmp',  'filter_cmp', 'account_report_id', 'enable_filter', 'label_filter','target_move','region_id','coststate_id'], context=context)[0])
		return self.pool['report'].get_action(cr, uid, [], 'account.report_financial2', data=data, context=context)
	
	def _build_contexts_dcs(self, cr, uid, ids, data, context=None):
		if context is None:
			context = {}
		result = {}
		result['fiscalyear'] = 'fiscalyear_id' in data['form'] and data['form']['fiscalyear_id'] or False
		result['journal_ids'] = 'journal_ids' in data['form'] and data['form']['journal_ids'] or False
		result['chart_account_id'] = 'chart_account_id' in data['form'] and data['form']['chart_account_id'] or False
		result['state'] = 'target_move' in data['form'] and data['form']['target_move'] or ''
		if data['form']['filter'] == 'filter_date':
			result['date_from'] = data['form']['date_from']
			result['date_to'] = data['form']['date_to']
		elif data['form']['filter'] == 'filter_period':
			if not data['form']['period_from'] or not data['form']['period_to']:
				raise osv.except_osv(_('Error!'),_('Select a starting and an ending period.'))
			result['period_from'] = data['form']['period_from']
			result['period_to'] = data['form']['period_to']
		if data['form']['coststate_id']:
			result['coststate_id'] = data['form']['coststate_id']
		if data['form']['region_id']:
			result['region_id'] = data['form']['region_id']
		else:
			result['region_id'] = None
		return result
	
	def _check_report_dcs(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		data = {}
		data['ids'] = context.get('active_ids', [])
		data['model'] = context.get('active_model', 'ir.ui.menu')
		data['form'] = self.read(cr, uid, ids, ['date_from',  'date_to',  'fiscalyear_id', 'journal_ids', 'period_from', 'period_to',  'filter',  'chart_account_id', 'target_move','region_id','coststate_id'], context=context)[0]
		for field in ['fiscalyear_id', 'chart_account_id', 'period_from', 'period_to']:
			if isinstance(data['form'][field], tuple):
				data['form'][field] = data['form'][field][0]
		used_context = self._build_contexts_dcs(cr, uid, ids, data, context=context)
		data['form']['periods'] = used_context.get('periods', False) and used_context['periods'] or []
		data['form']['used_context'] = dict(used_context, lang=context.get('lang', 'en_US'))
		data['form'].update(self.read(cr, uid, ids, ['date_from_cmp',  'debit_credit', 'date_to_cmp',  'fiscalyear_id_cmp', 'period_from_cmp', 'period_to_cmp',  'filter_cmp', 'account_report_id', 'enable_filter', 'label_filter','target_move','region_id','coststate_id'], context=context)[0])
		#return self._print_report_dcs(cr, uid, ids, data, context=context)
		return data
	def _build_comparison_context_dcs(self, cr, uid, ids, data, context=None):
		if context is None:
			context = {}
		result = {}
		result['fiscalyear'] = 'fiscalyear_id_cmp' in data['form'] and data['form']['fiscalyear_id_cmp'] or False
		result['journal_ids'] = 'journal_ids' in data['form'] and data['form']['journal_ids'] or False
		result['chart_account_id'] = 'chart_account_id' in data['form'] and data['form']['chart_account_id'] or False
		result['state'] = 'target_move' in data['form'] and data['form']['target_move'] or ''
		if data['form']['filter_cmp'] == 'filter_date':
			result['date_from'] = data['form']['date_from_cmp']
			result['date_to'] = data['form']['date_to_cmp']
		elif data['form']['filter_cmp'] == 'filter_period':
			if not data['form']['period_from_cmp'] or not data['form']['period_to_cmp']:
				raise osv.except_osv(_('Error!'),_('Select a starting and an ending period'))
			result['period_from'] = data['form']['period_from_cmp']
			result['period_to'] = data['form']['period_to_cmp']
		if data['form']['coststate_id']:
			result['coststate_id'] = data['form']['coststate_id']
		if data['form']['region_id']:
			result['region_id'] = data['form']['region_id']
		else:
			result['region_id'] = None
		#_logger.error("change_payment_term:line._build_comparison_context_build_comparison_context["+str(data['form'])+"]")	
		return result
		
	def csv_report_dcs_bs(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		_ids=[]	
		_id=0
		fname="csv"
		for record in self.browse(cr, uid, ids, context=context):	
			_id= record.chart_account_id.id or False
			fname=record.account_report_id.name
			_ids=[_id]
		#data = {}
		data = self._check_report_dcs(cr, uid, ids, context=context)
		
		bs1 = report_account_common1(cr, uid, "name1", context=context)
		bs1.ids=_ids
		
		_lines=bs1.get_lines(data)
		_csv=" , ,dr,cr,balance,\n"
		fname=fname.lower().replace(' ','')+".csv"
		#fname="balance_sheet.csv"
		#_len=len(_lines)
		for line in _lines:
			if line.get('debit'):
				_dr=line.get('debit')
			else:
				_dr=""
			if line.get('credit'):
				_cr=line.get('credit')
			else:
				_cr=""
			_grpstr=""	
			if line['level'] != 0:
				if not line.get('level') > 3:
					_grpstr="::"
			_csv+="\" %s\",\" %s\",\"%s\",\"%s\",\"%s\",\n" % (line['name'],_grpstr,_dr,_cr,line.get('balance'))
		temp_path="/var/tmp/odoo/account/"#+fname	
		save_as=temp_path+fname	
		with open(save_as, 'w') as the_file:
			the_file.write(_csv)
		return {
				'name': 'Trial Balance',
				'res_model': 'ir.actions.act_url',
				'type' : 'ir.actions.act_url',
				'url': '/web/binary/download_file?model=sale.order&field=datas&id=%s&path=%s&filename=%s' % (str(_id),temp_path,fname),
				'context': context}
				
	def print_report_dcs_bs(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		#res = self._check_report_dcs(cr, uid, ids, context=context)
		data = self._check_report_dcs(cr, uid, ids, context=context)
		res = self._print_report_dcs(cr, uid, ids, data, context=context)
		
		#data = {}
		#data['form'] = self.read(cr, uid, ids, ['account_report_id', 'date_from_cmp',  'date_to_cmp',  'fiscalyear_id_cmp', 'journal_ids', 'period_from_cmp', #'period_to_cmp',  'filter_cmp',  'chart_account_id', 'target_move','region_id','coststate_id'], context=context)[0]
		#for field in ['fiscalyear_id_cmp', 'chart_account_id', 'period_from_cmp', 'period_to_cmp', 'account_report_id']:
		#	if isinstance(data['form'][field], tuple):
		#		data['form'][field] = data['form'][field][0]
		#comparison_context = self._build_comparison_context_dcs(cr, uid, ids, data, context=context)
		#@res['data']['form']['comparison_context'] = comparison_context
		return res
		
#_inherit = "dcs.account.common.report"		
class dcs_account_report_general_ledger(osv.osv_memory):
	
	_name = "dcs.account.report.general.ledger"
	#_description = "General Ledger Report"
	_inherit = "dcs.account.common.report"
	_columns = {
		'landscape': fields.boolean("Landscape Mode"),
		'initial_balance': fields.boolean('Include Initial Balances',
									help='If you selected to filter by date or period, this field allow you to add a row to display the amount of debit/credit/balance that precedes the filter you\'ve set.'),
		'amount_currency': fields.boolean("With Currency", help="It adds the currency column on report if the currency differs from the company currency."),
		'sortby': fields.selection([('sort_date', 'Date'), ('sort_journal_partner', 'Journal & Partner')], 'Sort by', required=True),
		'journal_ids': fields.many2many('account.journal', 'dcs_account_report_general_ledger_journal_rel', 'account_id', 'journal_id', 'Journals', required=True),
	}
	_defaults = {
		'landscape': True,
		'amount_currency': True,
		'sortby': 'sort_date',
		'initial_balance': False,
	}
	
	def _build_contexts_dcs(self, cr, uid, ids, data, context=None):
		if context is None:
			context = {}
		result = {}
		result['fiscalyear'] = 'fiscalyear_id' in data['form'] and data['form']['fiscalyear_id'] or False
		result['journal_ids'] = 'journal_ids' in data['form'] and data['form']['journal_ids'] or False
		result['chart_account_id'] = 'chart_account_id' in data['form'] and data['form']['chart_account_id'] or False
		result['state'] = 'target_move' in data['form'] and data['form']['target_move'] or ''
		if data['form']['filter'] == 'filter_date':
			result['date_from'] = data['form']['date_from']
			result['date_to'] = data['form']['date_to']
		elif data['form']['filter'] == 'filter_period':
			if not data['form']['period_from'] or not data['form']['period_to']:
				raise osv.except_osv(_('Error!'),_('Select a starting and an ending period.'))
			result['period_from'] = data['form']['period_from']
			result['period_to'] = data['form']['period_to']
		if data['form']['region_id']:
			result['region_id'] = data['form']['region_id']
		else:
			result['region_id'] = None
		
		if data['form']['coststate_id']:
			result['coststate_id'] = data['form']['coststate_id']
		
		return result
		
	def pre_print_report_dcs(self, cr, uid, ids, data, context=None):
		if context is None:
			context = {}
		data['form'].update(self.read(cr, uid, ids, ['display_account'], context=context)[0])
		return data
		
	def onchange_fiscalyear_dcs(self, cr, uid, ids, fiscalyear=False, context=None):
		res = {}
		if not fiscalyear:
			res['value'] = {'initial_balance': False}
		return res
	
	def print_report_dcs_ledger(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		#_logger.error("print_report_dcs-0")	 	
		data = {}
		data['ids'] = context.get('active_ids', [])
		data['model'] = context.get('active_model', 'ir.ui.menu')
		data['form'] = self.read(cr, uid, ids, ['date_from',  'date_to',  'fiscalyear_id', 'journal_ids', 'period_from', 'period_to',  'filter',  'chart_account_id', 'target_move','region_id','coststate_id'], context=context)[0]
		for field in ['fiscalyear_id', 'chart_account_id', 'period_from', 'period_to']:
			if isinstance(data['form'][field], tuple):
				data['form'][field] = data['form'][field][0]
		used_context = self._build_contexts_dcs(cr, uid, ids, data, context=context)
		data['form']['periods'] = used_context.get('periods', False) and used_context['periods'] or []
		data['form']['used_context'] = dict(used_context, lang=context.get('lang', 'en_US'))
		return self._print_report_dcs_ledger(cr, uid, ids, data, context=context)
		
	#def print_report_dcs_ledger(self, cr, uid, ids, context=None):
	#	return self._print_report_dcs_ledger(cr, uid, ids, context=context)	
	
	
	def _print_report_dcs_ledger(self, cr, uid, ids, data, context=None):
		if context is None:
			context = {}
		data = self.pre_print_report_dcs(cr, uid, ids, data, context=context)
		data['form'].update(self.read(cr, uid, ids, ['landscape',  'initial_balance', 'amount_currency', 'sortby'])[0])
		if not data['form']['fiscalyear_id']:# GTK client problem onchange does not consider in save record
			data['form'].update({'initial_balance': False})

		if data['form']['landscape'] is False:
			data['form'].pop('landscape')
		else:
			context['landscape'] = data['form']['landscape']
		#_logger.error("_print_report_dcs_ledger-0" + str(context))
		#return self.pool['report'].get_action(cr, uid, [], 'account.report_general_ledger_dcs', data=data, context=context)
		#return self.pool['report'].get_action(cr, uid, [], 'account.report_trialbalance1', data=data, context=context)
		return self.pool['report'].get_action(cr, uid, [], 'account.report_gledger2', data=data, context=context)

class dcsaccount_tax_report(osv.osv_memory):
	_name = 'dcsaccount.tax.report'
	#_description = 'Account Vat Declaration'
	_inherit = "dcs.account.common.report"
	_columns = {
		'based_on': fields.selection([('invoices', 'Invoices'),
									  ('payments', 'Payments'),],
									  'Based on', required=True),
		'chart_tax_id': fields.many2one('account.tax.code', 'Chart of Tax', help='Select Charts of Taxes', required=True, domain = [('parent_id','=', False)]),
		'display_detail': fields.boolean('Display Detail'),
	}

	def _get_tax(self, cr, uid, context=None):
		user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
		taxes = self.pool.get('account.tax.code').search(cr, uid, [('parent_id', '=', False), ('company_id', '=', user.company_id.id)], limit=1)
		return taxes and taxes[0] or False

	_defaults = {
		'based_on': 'invoices',
		'chart_tax_id': _get_tax,
		'date_from': time.strftime('%Y-01-01'), 
		'date_to': time.strftime('%Y-%m-%d')
	}
	
	def dcs_csv_tax_report(self, cr, uid, ids, context=None):
		
		if context is None:
			context = {}

		datas = {'ids': context.get('active_ids', [])}
		datas['model'] = 'account.tax.code'
		datas['form']  = self.read(cr, uid, ids, context=context)[0]

		for field in datas['form'].keys():
			if isinstance(datas['form'][field], tuple):
				datas['form'][field] = datas['form'][field][0]

		taxcode_obj = self.pool.get('account.tax.code')
		taxcode_id  = datas['form']['chart_tax_id']
		taxcode     = taxcode_obj.browse(cr, uid, [taxcode_id], context=context)[0]
		datas['form']['company_id'] = taxcode.company_id.id
		
		#----------------------------------------------------------------
		_ids=[]	
		_id=0
		fname="bascsv"
	 
		 
		
		tax1 = bas_report_dcs(cr, uid, "name1", context=context)
		tax1.ids=_ids
		
		_lines=tax1._get_lines(datas)
		_csv="Tax Name,	Reference,	Date,	Partner,	Sale Value,	Purchase Value,	Tax Collected,	Tax Paid\n"
		fname=fname.lower().replace(' ','')+".csv"
		 
		for line in _lines:
			_csv+="\" %s\",\" %s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\n" % (line['tax_code'],line['number'],line['date_invoice'],line['partner'],line['sale'],line['purchase'],line['sale_tax'],line['purchase_tax'])
		temp_path="/var/tmp/odoo/account/"#+fname	
		save_as=temp_path+fname	
		with open(save_as, 'w') as the_file:
			the_file.write(_csv)
		return {
				'name': 'Tax Report',
				'res_model': 'ir.actions.act_url',
				'type' : 'ir.actions.act_url',
				'url': '/web/binary/download_file?model=sale.order&field=datas&id=%s&path=%s&filename=%s' % (str(_id),temp_path,fname),
				'context': context}
	
		
	def dcs_create_tax_report_new(self, cr, uid, ids, context=None):
		if context is None:
			context = {}

		datas = {'ids': context.get('active_ids', [])}
		datas['model'] = 'account.tax.code'
		datas['form']  = self.read(cr, uid, ids, context=context)[0]

		for field in datas['form'].keys():
			if isinstance(datas['form'][field], tuple):
				datas['form'][field] = datas['form'][field][0]

		taxcode_obj = self.pool.get('account.tax.code')
		taxcode_id  = datas['form']['chart_tax_id']
		taxcode     = taxcode_obj.browse(cr, uid, [taxcode_id], context=context)[0]
		datas['form']['company_id'] = taxcode.company_id.id
		return self.pool['report'].get_action(cr, uid, [], 'account.report_bas_dcs', data=datas, context=context)
		#return self.pool['report'].get_action(cr, uid, [], 'account.report_tax_statement', data=datas, context=context)
		
	def dcs_create_tax_report(self, cr, uid, ids, context=None):
		if context is None:
			context = {}

		datas = {'ids': context.get('active_ids', [])}
		datas['model'] = 'account.tax.code'
		datas['form']  = self.read(cr, uid, ids, context=context)[0]

		for field in datas['form'].keys():
			if isinstance(datas['form'][field], tuple):
				datas['form'][field] = datas['form'][field][0]

		taxcode_obj = self.pool.get('account.tax.code')
		taxcode_id  = datas['form']['chart_tax_id']
		taxcode     = taxcode_obj.browse(cr, uid, [taxcode_id], context=context)[0]
		datas['form']['company_id'] = taxcode.company_id.id
		#result['date_from'] = data['form']['date_from']
		#result['date_to'] = data['form']['date_to']
		#_logger.error("dcs_create_tax_reportdcs_create_tax_report-0" + str(datas))	
		return self.pool['report'].get_action(cr, uid, [], 'account.report_tax_dcs', data=datas, context=context)
		#return self.pool['report'].get_action(cr, uid, [], 'account.report_trialbalance1', data=datas, context=context)

class dcsaccount_partner_statement(osv.osv_memory):
	_name = 'dcsaccount.partner.statement'
	#_description = 'Account Vat Declaration'
	_inherit = "dcs.account.common.report"
	_columns = {
		'partner_id': fields.many2one('res.partner', 'Partner', domain = [('customer','=', True),('x_is_project','=', False),('parent_id','=', False)]),
		'date': fields.date('Date'),
		'partner_line': fields.one2many('dincelaccount.partner.tmp', 'statement_id', 'Partners'),
		'partner_ids' : fields.many2many('res.partner', 'rel_statement_partner', 'statement_id', 'partner_id', string = "Customers"),
	}
	_defaults = {
		'date': lambda *a: time.strftime('%Y-%m-%d'),
	}
	
	def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
		if context is None: context = {}
		res = super(dcsaccount_partner_statement, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=False)
		'''cmp_select = []
		# display in the widget selection only the companies that haven't been configured yet
		#unconfigured_cmp = self.get_unconfigured_cmp(cr, uid, context=context)
		for field in res['fields']:
			if field == 'partner_id':
				cr.execute("SELECT partner_id FROM dincelaccount_partner_due")
				all_ids = [r[0] for r in cr.fetchall()]
				#unconfigured_cmp = list(set(company_ids)-set(configured_cmp))
				res['fields'][field]['domain'] = [('id', 'in', all_ids)]
				#res['fields'][field]['selection'] = [('', '')]
				#if unconfigured_cmp:
				#	cmp_select = [(line.id, line.name) for line in self.pool.get('res.company').browse(cr, uid, unconfigured_cmp)]
				#	res['fields'][field]['selection'] = cmp_select'''
		return res

	def dcs_create_report(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		#datas = {'ids': context.get('active_ids', [])}
	 
		#datas['form']  = self.read(cr, uid, ids, context=context)[0]
		_ids=""
		#if data.get('form', False) and data['form'].get('partner_id', False):
		#	#_ids=data['form'].get('partner_id', False)
		#	_ids= data['form']['partner_id'][0]
		#	#_ids=
		#else:'
		dt=""
		for record in self.browse(cr, uid, ids):
			dt=record.date
			if record.partner_id:
				_ids=record.partner_id.id
				
			else:	
				for _id in record.partner_ids:#obj_inv = self.pool.get('account.invoice')
					_ids+=str(_id.id)+"-"
					#args = [("x_sale_order_id", "=", record.id)]
		#use of odoo/web report instead of qweb
		#//return self.pool['report'].get_action(cr, uid, [], 'account.report_partner_statement', data=datas, context=context)		
		url=self.pool.get('dincelaccount.config.settings').report_preview_url(cr, uid, ids,"statement","",context=context)		
		if url:
			url=url.replace("erp.dincel.com.au/", "localhost/")
			url+="&ids=%s&dt=%s" % (_ids,dt)
			return {
				  'name'     : 'Go to website',
				  'res_model': 'ir.actions.act_url',
				  'type'     : 'ir.actions.act_url',
				  'view_type': 'form',
				  'view_mode': 'form',
				  'target'   : 'current',
				  'url'      : url,
				  'context': context
			   }
			   
	
	def dcs_partner_statement_pdf(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		#datas = {'ids': context.get('active_ids', [])}
	 
		#datas['form']  = self.read(cr, uid, ids, context=context)[0]

		#return self.pool['report'].get_action(cr, uid, [], 'account.report_partner_statement_pdf', data=datas, context=context)	
		_ids=""
		dt=""
		for record in self.browse(cr, uid, ids):
			dt=record.date
			if record.partner_id:
				_ids=record.partner_id.id
				
			else:	
				for _id in record.partner_ids:#obj_inv = self.pool.get('account.invoice')
					_ids+=str(_id.id)+"-"
		
		url=self.pool.get('dincelaccount.config.settings').report_preview_url(cr, uid, ids,"statement","",context=context)		
		if url:
			url=url.replace("erp.dincel.com.au/", "localhost/")
			url+="&ids=%s&dt=%s" % (_ids,dt)	
			fname="statement"+str(dt).replace("/","")+".pdf"
			save_path="/var/tmp/odoo/account"
			
			process=subprocess.Popen(["wkhtmltopdf", 
						"--orientation",'landscape',
						'--margin-top','1', 
						'--margin-left','1', 
						'--margin-right','1', 
						'--margin-bottom','1', url, save_path+"/"+fname],stdin=PIPE,stdout=PIPE)
			
			out, err = process.communicate()
			if process.returncode not in [0, 1]:
				raise osv.except_osv(_('Report (PDF)'),
									_('Wkhtmltopdf failed (error code: %s). '
									'Message: %s') % (str(process.returncode), err))
			
			return {
					'name': 'Report Pdf',
					'res_model': 'ir.actions.act_url',
					'type' : 'ir.actions.act_url',
					'url': '/web/binary/download_file?model=account.invoice&field=datas&id=%s&path=%s&filename=%s' % (str(ids[0]),save_path,fname),
					'context': context}
class dcsaccount_partner_tmp(osv.osv_memory):
	_name="dincelaccount.partner.tmp"
	#_order = 'id desc' order_item as in dcs , for summary
	_columns={
		'name': fields.char('name'),
		'sequence':fields.integer('Sequence'),
		'statement_id': fields.many2one('dcsaccount.partner.statement', 'Statement Reference',ondelete='cascade',),
		'partner_id': fields.many2one('res.partner','Customer'),
		}
		
		
class dcsaccount_partner_aging(osv.osv_memory):
	_name = 'dcsaccount.partner.aging'
	_inherit = "dcs.account.common.report"
	_columns = {
		'partner_id': fields.many2one('res.partner', 'Partner', domain = [('customer','=', True),('x_is_project','=', False),('parent_id','=', False)]),
		'date': fields.date('Date'),
		'supplier': fields.boolean('Supplier?'),
	}
	_defaults = {
		'date': lambda *a: time.strftime('%Y-%m-%d'),
	}
	def dcs_summary_report_aging(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		_ids=""
		dt=""
		supplier=False
		for record in self.browse(cr, uid, ids):
			dt=record.date
			if record.supplier:
				supplier=True
				
		url=self.pool.get('dincelaccount.config.settings').report_preview_url(cr, uid, ids,"ageingall","",context=context)		
		if url:
			url+="&dt=%s" % (dt)
			if supplier:
				url+="&t=s"
			return {
				  'name'     : 'Go to website',
				  'res_model': 'ir.actions.act_url',
				  'type'     : 'ir.actions.act_url',
				  'view_type': 'form',
				  'view_mode': 'form',
				  'target'   : 'current',
				  'url'      : url,
				  'context': context
			   }	
				
	def dcs_summary_report_aging_csv(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		_ids=""
		_id=0
		dt=""
		supplier=False
		for record in self.browse(cr, uid, ids):
			_id=record.id
			dt=record.date
			if record.supplier:
				supplier=True
				
		url=self.pool.get('dincelaccount.config.settings').report_preview_url(cr, uid, ids,"ageingall","",context=context)		
		if url:
			url+="&dt=%s&csv=1" % (dt)
			if supplier:
				url+="&t=s"
				fname="payablesummary"
			else:
				fname="receivablesummary"
		 
			fname=fname.lower().replace(' ','')+".csv"
			 
			f = urllib2.urlopen(url)
			_csvtxt = f.read()
			
			temp_path="/var/tmp/odoo/account/"#+fname	
			save_as=temp_path+fname	
			with open(save_as, 'w') as the_file:
				the_file.write(_csvtxt)
			return {
					'name': 'CSV Report',
					'res_model': 'ir.actions.act_url',
					'type' : 'ir.actions.act_url',
					'url': '/web/binary/download_file?model=account.invoice&field=datas&id=%s&path=%s&filename=%s' % (str(_id),temp_path,fname),
					'context': context}	
				
	def dcs_create_report_aging(self, cr, uid, ids, context=None):
		'''if context is None:
			context = {}
		datas = {'ids': context.get('active_ids', [])}
	 
		datas['form']  = self.read(cr, uid, ids, context=context)[0]

		return self.pool['report'].get_action(cr, uid, [], 'account.report_partner_aging', data=datas, context=context)		'''
		if context is None:
			context = {}
		 
		_ids=""
		dt=""
		for record in self.browse(cr, uid, ids):
			dt=record.date
			if record.partner_id:
				_ids=record.partner_id.id
	 
		url=self.pool.get('dincelaccount.config.settings').report_preview_url(cr, uid, ids,"ageing","",context=context)		
		if url:
			url+="&ids=%s&dt=%s" % (_ids,dt)
			return {
				  'name'     : 'Go to website',
				  'res_model': 'ir.actions.act_url',
				  'type'     : 'ir.actions.act_url',
				  'view_type': 'form',
				  'view_mode': 'form',
				  'target'   : 'current',
				  'url'      : url,
				  'context': context
			   }		
		
	def dcs_aging_report_aging_pdf(self, cr, uid, ids, context=None):
		'''if context is None:
			context = {}
		datas = {'ids': context.get('active_ids', [])}
	 
		datas['form']  = self.read(cr, uid, ids, context=context)[0]

		return self.pool['report'].get_action(cr, uid, [], 'account.report_partner_aging_pdf', data=datas, context=context)		'''
		if context is None:
			context = {}
		 
		_ids=""
		dt=""
		for record in self.browse(cr, uid, ids):
			dt=record.date
			if record.partner_id:
				_ids=record.partner_id.id
	 
		url=self.pool.get('dincelaccount.config.settings').report_preview_url(cr, uid, ids,"ageing","",context=context)		
		if url: 
			url+="&ids=%s&dt=%s" % (_ids,dt)	
			fname="ageing"+str(dt).replace("/","")+".pdf"
			save_path="/var/tmp/odoo/account"
			
			process=subprocess.Popen(["wkhtmltopdf", 
						"--orientation",'landscape',
						'--margin-top','1', 
						'--margin-left','1', 
						'--margin-right','1', 
						'--margin-bottom','1', url, save_path+"/"+fname],stdin=PIPE,stdout=PIPE)
			
			out, err = process.communicate()
			if process.returncode not in [0, 1]:
				raise osv.except_osv(_('Report (PDF)'),
									_('Wkhtmltopdf failed (error code: %s). '
									'Message: %s') % (str(process.returncode), err))
			
			return {
					'name': 'Report Pdf',
					'res_model': 'ir.actions.act_url',
					'type' : 'ir.actions.act_url',
					'url': '/web/binary/download_file?model=account.invoice&field=datas&id=%s&path=%s&filename=%s' % (str(ids[0]),save_path,fname),
					'context': context}
					
		
class dcsaccount_reconcile_rpt(osv.osv_memory):
	_name = 'dcsaccount.reconcile.rpt'
	_inherit = "dcs.account.common.report"
	_columns = {
		'account_id': fields.many2one('account.account', 'Account'),
	}

	def dcs_create_report(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		datas = {'ids': context.get('active_ids', [])}
	 
		datas['form']  = self.read(cr, uid, ids, context=context)[0]

		return self.pool['report'].get_action(cr, uid, [], 'account.report_account_reconcile', data=datas, context=context)			

		