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

from openerp.osv import osv
from openerp.report import report_sxw
from common_report_header1 import common_report_header1
import logging
_logger = logging.getLogger(__name__)

class account_gledger2(report_sxw.rml_parse, common_report_header1):
	_name = 'report.account.account.gledger2'

	def __init__(self, cr, uid, name, context=None):
		super(account_gledger2, self).__init__(cr, uid, name, context=context)
		self.query = ""
		self.tot_currency = 0.0
		self.period_sql = ""
		self.sold_accounts = {}
		self.sum_debit = 0.00
		self.sum_credit = 0.00
		self.date_lst = []
		self.date_lst_string = ''
		self.result_acc = []
		self.sortby = 'sort_date'
		self.localcontext.update({
			'time': time,
			'lines': self.lines,
			'sum_debit': self._sum_debit,
			'sum_credit': self._sum_credit,
			'get_fiscalyear':self._get_fiscalyear,
			'get_filter': self._get_filter,
			'get_start_period': self.get_start_period,
			'get_end_period': self.get_end_period ,
			'get_children_accounts': self.get_children_accounts,
			'get_account': self._get_account,
			'get_journal': self._get_journal,
			'get_start_date':self._get_start_date,
			'get_end_date':self._get_end_date,
			'get_target_move': self._get_target_move,
			'get_sortby': self._get_sortby,
			'get_region': self._get_region,
			})
		self.context = context
	def get_children_accounts(self, account):
		res = []
		currency_obj = self.pool.get('res.currency')
		ids_acc = self.pool.get('account.account')._get_children_and_consol_dcs(self.cr, self.uid, account.id)
		
		currency = account.currency_id and account.currency_id or account.company_id.currency_id
		#_logger.error("get_children_accountsget_children_accounts-1" + str(account.currency_id))
		for child_account in self.pool.get('account.account').browse(self.cr, self.uid, ids_acc, context=self.context):
			sql = """
				SELECT count(id)
				FROM account_move_line AS l
				WHERE %s AND l.account_id = %%s
			""" % (self.query)
			self.cr.execute(sql, (child_account.id,))
			num_entry = self.cr.fetchone()[0] or 0
			sold_account = self._sum_balance_account_dcs(child_account)
			self.sold_accounts[child_account.id] = sold_account
			if self.display_account == 'movement':
				if child_account.type != 'view' and num_entry <> 0:
					res.append(child_account)
			elif self.display_account == 'not_zero':
				if child_account.type != 'view' and num_entry <> 0:
					if not currency_obj.is_zero(self.cr, self.uid, currency, sold_account):
						res.append(child_account)
			else:
				res.append(child_account)
		if not res:
			return [account]
		return res
		
	def set_context(self, objects, data, ids, report_type=None):
		new_ids = ids
		if (data['model'] == 'ir.ui.menu'):
			new_ids = 'chart_account_id' in data['form'] and [data['form']['chart_account_id']] or []
			objects = self.pool.get('account.account').browse(self.cr, self.uid, new_ids)
		return super(account_gledger2, self).set_context(objects, data, new_ids, report_type=report_type)

	def _get_account(self, data):
		if data['model']=='account.account':
			return self.pool.get('account.account').browse(self.cr, self.uid, data['form']['id']).company_id.name
		return super(account_gledger2 ,self)._get_account(data)

	def lines(self, form, ids=None, done=None):
		move_state = ['draft','posted']
		if self.target_move == 'posted':
			move_state = ['posted', '']
		# First compute all counterpart strings for every move_id where this account appear.
		# Currently, the counterpart info is used only in landscape mode
		sql = """
			SELECT m1.move_id,
				array_to_string(ARRAY(SELECT DISTINCT a.code
										  FROM account_move_line m2
										  LEFT JOIN account_account a ON (m2.account_id=a.id)
										  WHERE m2.move_id = m1.move_id
										  AND m2.account_id<>%%s), ', ') AS counterpart
				FROM (SELECT move_id
						FROM account_move_line l
						LEFT JOIN account_move am ON (am.id = l.move_id)
						WHERE am.state IN %s and %s AND l.account_id = %%s GROUP BY move_id) m1
		"""% (tuple(move_state), self.query)
		self.cr.execute(sql, (account.id, account.id))
		counterpart_res = self.cr.dictfetchall()
		counterpart_accounts = {}
		for i in counterpart_res:
			counterpart_accounts[i['move_id']] = i['counterpart']
		del counterpart_res

		# Then select all account_move_line of this account
		if self.sortby == 'sort_journal_partner':
			sql_sort='j.code, p.name, l.move_id'
		else:
			sql_sort='l.date, l.move_id'
		sql = """
			SELECT l.id AS lid, l.date AS ldate, j.code AS lcode, l.currency_id,l.amount_currency,l.ref AS lref, l.name AS lname, COALESCE(l.debit,0) AS debit, COALESCE(l.credit,0) AS credit, l.period_id AS lperiod_id, l.partner_id AS lpartner_id,
			m.name AS move_name, m.id AS mmove_id,per.code as period_code,
			c.symbol AS currency_code,
			i.id AS invoice_id, i.type AS invoice_type, i.number AS invoice_number,
			p.name AS partner_name
			FROM account_move_line l
			JOIN account_move m on (l.move_id=m.id)
			LEFT JOIN res_currency c on (l.currency_id=c.id)
			LEFT JOIN res_partner p on (l.partner_id=p.id)
			LEFT JOIN account_invoice i on (m.id =i.move_id)
			LEFT JOIN account_period per on (per.id=l.period_id)
			JOIN account_journal j on (l.journal_id=j.id)
			WHERE %s AND m.state IN %s AND l.account_id = %%s ORDER by %s
		""" %(self.query, tuple(move_state), sql_sort)
		self.cr.execute(sql, (account.id,))
		res_lines = self.cr.dictfetchall()
		res_init = []
		if res_lines and self.init_balance:
			#FIXME: replace the label of lname with a string translatable
			sql = """
				SELECT 0 AS lid, '' AS ldate, '' AS lcode, COALESCE(SUM(l.amount_currency),0.0) AS amount_currency, '' AS lref, 'Initial Balance' AS lname, COALESCE(SUM(l.debit),0.0) AS debit, COALESCE(SUM(l.credit),0.0) AS credit, '' AS lperiod_id, '' AS lpartner_id,
				'' AS move_name, '' AS mmove_id, '' AS period_code,
				'' AS currency_code,
				NULL AS currency_id,
				'' AS invoice_id, '' AS invoice_type, '' AS invoice_number,
				'' AS partner_name
				FROM account_move_line l
				LEFT JOIN account_move m on (l.move_id=m.id)
				LEFT JOIN res_currency c on (l.currency_id=c.id)
				LEFT JOIN res_partner p on (l.partner_id=p.id)
				LEFT JOIN account_invoice i on (m.id =i.move_id)
				JOIN account_journal j on (l.journal_id=j.id)
				WHERE %s AND m.state IN %s AND l.account_id = %%s
			""" %(self.init_query, tuple(move_state))
			self.cr.execute(sql, (account.id,))
			res_init = self.cr.dictfetchall()
		res = res_init + res_lines
		account_sum = 0.0
		for l in res:
			l['move'] = l['move_name'] != '/' and l['move_name'] or ('*'+str(l['mmove_id']))
			l['partner'] = l['partner_name'] or ''
			account_sum += l['debit'] - l['credit']
			l['progress'] = account_sum
			l['line_corresp'] = l['mmove_id'] == '' and ' ' or counterpart_accounts[l['mmove_id']].replace(', ',',')
			# Modification of amount Currency
			if l['credit'] > 0:
				if l['amount_currency'] != None:
					l['amount_currency'] = abs(l['amount_currency']) * -1
			if l['amount_currency'] != None:
				self.tot_currency = self.tot_currency + l['amount_currency']
		return res
		
	def _get_sortby(self, data):
		if self.sortby == 'sort_date':
			return self._translate('Date')
		elif self.sortby == 'sort_journal_partner':
			return self._translate('Journal & Partner')
		return self._translate('Date')	
'''
class dcs_account_account_move(osv.osv):
	_inherit = 'account.move.line'
	def search_dcs(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
		if context is None:
			context = {}
		if context.get('fiscalyear'):
			args.append(('period_id.fiscalyear_id', '=', context.get('fiscalyear', False)))
		if context and context.get('next_partner_only', False):
			if not context.get('partner_id', False):
				partner = self.list_partners_to_reconcile(cr, uid, context=context)
				if partner:
					partner = partner[0]
			else:
				partner = context.get('partner_id', False)
			if not partner:
				return []
			args.append(('partner_id', '=', partner[0]))
		return super(dcs_account_account_move, self).search(cr, uid, args, offset, limit, order, context, count)
		
class dcs_account_account(osv.osv):
	_inherit = 'account.account'
	def search_dcs(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
		if context is None:
			context = {}
		pos = 0

		while pos < len(args):

			if args[pos][0] == 'code' and args[pos][1] in ('like', 'ilike') and args[pos][2]:
				args[pos] = ('code', '=like', tools.ustr(args[pos][2].replace('%', ''))+'%')
			if args[pos][0] == 'journal_id':
				if not args[pos][2]:
					del args[pos]
					continue
				jour = self.pool.get('account.journal').browse(cr, uid, args[pos][2], context=context)
				if (not (jour.account_control_ids or jour.type_control_ids)) or not args[pos][2]:
					args[pos] = ('type','not in',('consolidation','view'))
					continue
				ids3 = map(lambda x: x.id, jour.type_control_ids)
				#_logger.error("check_report_search_idsid111sids3ids3["+str(ids3)+"]")	
				ids1 = super(dcs_account_account, self).search_dcs(cr, uid, [('user_type', 'in', ids3)])
				ids1 += map(lambda x: x.id, jour.account_control_ids)
				args[pos] = ('id', 'in', ids1)
			pos += 1
			
		if context and context.has_key('consolidate_children'): #add consolidated children of accounts
			ids = super(dcs_account_account, self).search_dcs(cr, uid, args, offset, limit,  order, context=context, count=count)
			for consolidate_child in self.browse(cr, uid, context['account_id'], context=context).child_consol_ids:
				ids.append(consolidate_child.id)
			#_logger.error("check_report_search_idsid111sids["+str(ids)+"]")	
			return ids
		#_logger.error("crt_sech_idsids["+str(context)+"]["+str(count)+"]["+str(args)+"]")	
		#return self.search_dcs(cr, uid, args, offset, limit, order, context=context, count=count)
		#_logger.error("crt_sech_idsimromro["+str(dcs_account_account.search().mro())+"]")	
		return super(dcs_account_account, self).search(cr, uid, args, offset, limit, order, context=context, count=count)
				
	def _get_children_and_consol_dcs(self, cr, uid, ids, context=None):
		#this function search for all the children and all consolidated children (recursively) of the given account ids
		ids2 = self.search_dcs(cr, uid, [('parent_id', 'child_of', ids)], context=context)
		ids3 = []
		for rec in self.browse(cr, uid, ids2, context=context):
			for child in rec.child_consol_ids:
				ids3.append(child.id)
		if ids3:
			_logger.error("crt_sech_ids3ids3["+str(context)+"]["+str(ids3)+"]["+str(ids2)+"]["+str(ids)+"]")	
			ids3 = self._get_children_and_consol_dcs(cr, uid, ids3, context)
		return ids2 + ids3
		'''
class report_gledger2(osv.AbstractModel):
	_name = 'report.account.report_gledger2'
	_inherit = 'report.abstract_report'
	_template = 'dincelaccount.report_gledger2'
	_wrapped_report_class = account_gledger2

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
