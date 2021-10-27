import time
from openerp.report import report_sxw
from common_report_header1 import common_report_header1
from openerp.tools.translate import _
from openerp.osv import osv
import logging
_logger = logging.getLogger(__name__)

class account_balance_report1(osv.osv_memory):
	_name = 'account.balance.report1'
	_inherit = "account.balance.report"
	_description = 'Trial Balance Report1'
	
	def _pre_print_report1(self, cr, uid, ids, data, context=None):
		if context is None:
			context = {}
		data['form'].update(self.read(cr, uid, ids, ['display_account'], context=context)[0])
		return data
		
	def _print_report1(self, cr, uid, ids, data, context=None):
		#_logger.error("check_report1-2")	 	
		data = self._pre_print_report1(cr, uid, ids, data, context=context)
		return self.pool['report'].get_action(cr, uid, [], 'account.report_trialbalance1', data=data, context=context)
	
	def _build_contexts1(self, cr, uid, ids, data, context=None):
		if context is None:
			context = {}
		#slog = '.'.join(data)	
		#_logger.error("check_report1-3-"+slog)	 		
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
		
		#slog = '.'.join(result)	+ str(result['fiscalyear'])+ "]"
		#_logger.error("check_report1-3-a-"+slog)	 	
		return result
	
	def check_report1(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		
		data = {}
		data['ids'] = context.get('active_ids', [])
		data['model'] = context.get('active_model', 'ir.ui.menu')
		data['form'] = self.read(cr, uid, ids, ['date_from',  'date_to',  'fiscalyear_id', 'journal_ids', 'period_from', 'period_to',  'filter',  'chart_account_id', 'target_move','region_id','coststate_id'], context=context)[0]
		for field in ['fiscalyear_id', 'chart_account_id', 'period_from', 'period_to']:
			if isinstance(data['form'][field], tuple):
				data['form'][field] = data['form'][field][0]
		used_context = self._build_contexts1(cr, uid, ids, data, context=context)
		data['form']['periods'] = used_context.get('periods', False) and used_context['periods'] or []
		data['form']['used_context'] = dict(used_context, lang=context.get('lang', 'en_US'))
		return self._print_report1(cr, uid, ids, data, context=context)	
	

