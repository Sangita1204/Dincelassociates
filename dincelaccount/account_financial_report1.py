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
from datetime import datetime
from dateutil.relativedelta import relativedelta
from operator import itemgetter

from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _

# ---------------------------------------------------------
# Account Financial Report
# ---------------------------------------------------------


class account_common_report1(osv.osv_memory):
	_name = "account.common.report1"
    _inherit = "account.common.report"
    _description = "Account Common Report 1"
	
	def check_report_test1(self, cr, uid, ids, context=None):
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
		return self.check_report_test1(cr, uid, ids, data, context=context)
 
class accounting_report(osv.osv_memory):
    _name = "accounting.report"
    _inherit = "account.common.report"
    _description = "Accounting Report"

    _columns = {from openerp.osv import fields, osv

	
	
class account_financial_report1(osv.osv):
    _name = "account.financial.report1"
	_inherits = "account.accounting.report"
    _description = "Account Report 1"
 
    def check_report_test1(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = super(account_financial_report1, self).check_report_test1(cr, uid, ids, context=context)
        data = {}
        data['form'] = self.read(cr, uid, ids, ['account_report_id', 'date_from_cmp',  'date_to_cmp',  'fiscalyear_id_cmp', 'journal_ids', 'period_from_cmp', 'period_to_cmp',  'filter_cmp',  'chart_account_id', 'target_move'], context=context)[0]
        for field in ['fiscalyear_id_cmp', 'chart_account_id', 'period_from_cmp', 'period_to_cmp', 'account_report_id']:
            if isinstance(data['form'][field], tuple):
                data['form'][field] = data['form'][field][0]
        comparison_context = self._build_comparison_context(cr, uid, ids, data, context=context)
        res['data']['form']['comparison_context'] = comparison_context
        return res