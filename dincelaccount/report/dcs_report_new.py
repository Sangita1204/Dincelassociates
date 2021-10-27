# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import time
from lxml import etree

from openerp.osv import fields, osv
from openerp.osv.orm import setup_modifiers
from openerp.tools.translate import _
#from openerp.osv import fields, osv
#from openerp.tools.translate import _
class accounting_report_dcs(osv.osv_memory):
	_inherit = "account.common.report"
	_columns={
		'x_region_id': fields.many2one('dincelaccount.region', 'A/c Region'),
		}
class accounting_report_new(osv.osv_memory):
	_name = "account.common.report.new"
	_inherit = "account.common.report"
	_description = "Accounting Report New"
	
	def check_report_test1(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		res = super(accounting_report_new, self).check_report(cr, uid, ids, context=context)
		data = {}
		data['form'] = self.read(cr, uid, ids, ['account_report_id', 'date_from_cmp',  'date_to_cmp',  'fiscalyear_id_cmp', 'journal_ids', 'period_from_cmp', 'period_to_cmp',  'filter_cmp',  'chart_account_id', 'target_move'], context=context)[0]
		for field in ['fiscalyear_id_cmp', 'chart_account_id', 'period_from_cmp', 'period_to_cmp', 'account_report_id']:
			if isinstance(data['form'][field], tuple):
				data['form'][field] = data['form'][field][0]
		comparison_context = self._build_comparison_context(cr, uid, ids, data, context=context)
		res['data']['form']['comparison_context'] = comparison_context
		return res
		
	def check_report1(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		data = {}
		data['ids'] = context.get('active_ids', [])
		data['model'] = context.get('active_model', 'ir.ui.menu')
		data['form'] = self.read(cr, uid, ids, ['date_from',  'date_to',  'fiscalyear_id', 'journal_ids', 'period_from', 'period_to',  'filter',  'chart_account_id', 'target_move'], context=context)[0]
		for field in ['fiscalyear_id', 'chart_account_id', 'period_from', 'period_to']:
			if isinstance(data['form'][field], tuple):
				data['form'][field] = data['form'][field][0]
		used_context = self._build_contexts(cr, uid, ids, data, context=context)
		data['form']['periods'] = used_context.get('periods', False) and used_context['periods'] or []
		data['form']['used_context'] = dict(used_context, lang=context.get('lang', 'en_US'))
		return self._print_report1(cr, uid, ids, data, context=context)	

	def _print_report1(self, cr, uid, ids, data, context=None):
		data['form'].update(self.read(cr, uid, ids, ['date_from_cmp',  'debit_credit', 'date_to_cmp',  'fiscalyear_id_cmp', 'period_from_cmp', 'period_to_cmp',  'filter_cmp', 'account_report_id', 'enable_filter', 'label_filter','target_move'], context=context)[0])
		return self.pool['report'].get_action(cr, uid, [], 'account.report_financial1', data=data, context=context)

class accounting_report1(osv.osv_memory):
	_name = "accounting.report1"		
	_inherit = "accounting.report"
	_description = "Accounting Report New1"
	
	def _build_contexts1(self, cr, uid, ids, data, context=None):
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
		return result
	
	def _print_report1(self, cr, uid, ids, data, context=None):
		data['form'].update(self.read(cr, uid, ids, ['date_from_cmp',  'debit_credit', 'date_to_cmp',  'fiscalyear_id_cmp', 'period_from_cmp', 'period_to_cmp',  'filter_cmp', 'account_report_id', 'enable_filter', 'label_filter','target_move'], context=context)[0])
		return self.pool['report'].get_action(cr, uid, [], 'account.report_financial2', data=data, context=context)
		#raise (_('Error!'), _('Not implemented.'))

	def _check_report2(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		data = {}
		data['ids'] = context.get('active_ids', [])
		data['model'] = context.get('active_model', 'ir.ui.menu')
		data['form'] = self.read(cr, uid, ids, ['date_from',  'date_to',  'fiscalyear_id', 'journal_ids', 'period_from', 'period_to',  'filter',  'chart_account_id', 'target_move'], context=context)[0]
		for field in ['fiscalyear_id', 'chart_account_id', 'period_from', 'period_to']:
			if isinstance(data['form'][field], tuple):
				data['form'][field] = data['form'][field][0]
		used_context = self._build_contexts1(cr, uid, ids, data, context=context)
		data['form']['periods'] = used_context.get('periods', False) and used_context['periods'] or []
		data['form']['used_context'] = dict(used_context, lang=context.get('lang', 'en_US'))
		return self._print_report1(cr, uid, ids, data, context=context)
		
	def _build_comparison_context1(self, cr, uid, ids, data, context=None):
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
		return result
		
	def check_report1(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		res = self._check_report2(cr, uid, ids, context=context)
		data = {}
		data['form'] = self.read(cr, uid, ids, ['account_report_id', 'date_from_cmp',  'date_to_cmp',  'fiscalyear_id_cmp', 'journal_ids', 'period_from_cmp', 'period_to_cmp',  'filter_cmp',  'chart_account_id', 'target_move'], context=context)[0]
		for field in ['fiscalyear_id_cmp', 'chart_account_id', 'period_from_cmp', 'period_to_cmp', 'account_report_id']:
			if isinstance(data['form'][field], tuple):
				data['form'][field] = data['form'][field][0]
		comparison_context = self._build_comparison_context1(cr, uid, ids, data, context=context)
		res['data']['form']['comparison_context'] = comparison_context
		return res