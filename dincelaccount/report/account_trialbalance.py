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

class account_balance1(report_sxw.rml_parse, common_report_header1):
	_name = 'report.account.account.balance1'

	def __init__(self, cr, uid, name, context=None):
		super(account_balance1, self).__init__(cr, uid, name, context=context)
		self.sum_debit = 0.00
		self.sum_credit = 0.00
		self.date_lst = []
		self.date_lst_string = ''
		self.result_acc = []
		self.localcontext.update({
			'time': time,
			'lines': self.lines,
			'sum_debit': self._sum_debit,
			'sum_credit': self._sum_credit,
			'get_fiscalyear':self._get_fiscalyear,
			'get_filter': self._get_filter,
			'get_start_period': self.get_start_period,
			'get_end_period': self.get_end_period ,
			'get_account': self._get_account,
			'get_journal': self._get_journal,
			'get_start_date':self._get_start_date,
			'get_end_date':self._get_end_date,
			'get_target_move': self._get_target_move,
			'get_region': self._get_region,
			})
		self.context = context

	def set_context(self, objects, data, ids, report_type=None):
		new_ids = ids
		if (data['model'] == 'ir.ui.menu'):
			new_ids = 'chart_account_id' in data['form'] and [data['form']['chart_account_id']] or []
			objects = self.pool.get('account.account').browse(self.cr, self.uid, new_ids)
		return super(account_balance1, self).set_context(objects, data, new_ids, report_type=report_type)

	def _get_account(self, data):
		if data['model']=='account.account':
			return self.pool.get('account.account').browse(self.cr, self.uid, data['form']['id']).company_id.name
		return super(account_balance1 ,self)._get_account(data)

	def lines(self, form, ids=None, done=None):
		def _process_child(accounts, disp_acc, parent):
				account_rec = [acct for acct in accounts if acct['id']==parent][0]
				currency_obj = self.pool.get('res.currency')
				acc_id = self.pool.get('account.account').browse(self.cr, self.uid, account_rec['id'])
				currency = acc_id.currency_id and acc_id.currency_id or acc_id.company_id.currency_id
				res = {
					'id': account_rec['id'],
					'type': account_rec['type'],
					'code': account_rec['code'],
					'name': account_rec['name'],
					'level': account_rec['level'],
					'debit': account_rec['debit'],
					'credit': account_rec['credit'],
					'balance': account_rec['balance'],
					'parent_id': account_rec['parent_id'],
					'bal_type': '',
				}
				#_logger.error("check_report__process_child_process_child["+str(res)+"]")	 
				self.sum_debit += account_rec['debit']
				self.sum_credit += account_rec['credit']
				if disp_acc == 'movement':
					if not currency_obj.is_zero(self.cr, self.uid, currency, res['credit']) or not currency_obj.is_zero(self.cr, self.uid, currency, res['debit']) or not currency_obj.is_zero(self.cr, self.uid, currency, res['balance']):
						self.result_acc.append(res)
				elif disp_acc == 'not_zero':
					if not currency_obj.is_zero(self.cr, self.uid, currency, res['balance']):
						self.result_acc.append(res)
				else:
					self.result_acc.append(res)
				if account_rec['child_id']:
					for child in account_rec['child_id']:
						_process_child(accounts, disp_acc, child)
		obj_account = self.pool.get('account.account')
		if not ids:
			ids = self.ids
		if not ids:
			return []
		if not done:
			done={}

		ctx = self.context.copy()

		ctx['fiscalyear'] = form['fiscalyear_id']
		if form['filter'] == 'filter_period':
			ctx['period_from'] = form['period_from']
			ctx['period_to'] = form['period_to']
		elif form['filter'] == 'filter_date':
			ctx['date_from'] = form['date_from']
			ctx['date_to'] =  form['date_to']
		ctx['state'] = form['target_move']
		
		if form['region_id']:
			ctx['region_id'] = form['region_id']
		else:
			ctx['region_id'] = None
		if form['coststate_id']:
			ctx['coststate_id'] = form['coststate_id']	
		#_logger.error("check_report_lineslines1ctxctx["+str(ctx)+"]")	 	
		#else:
		#_logger.error("check_report_lineslines1["+str(form)+"]")	 	
		#_logger.error("check_report_idsidsids["+str(ids)+"]")	
		parents = ids
		child_ids = obj_account._get_children_and_consol_dcs(self.cr, self.uid, ids, ctx)
		if child_ids:
			ids = child_ids
		#_logger.error("check_report_accountsaccounts_idsids["+str(ids)+"]")		
		accounts = obj_account.read(self.cr, self.uid, ids, ['type','code','name','debit','credit','balance','parent_id','level','child_id'], ctx)
		#_logger.error("check_report_accountsaccounts["+str(accounts)+"]")	
		for parent in parents:
				if parent in done:
					continue
				done[parent] = 1
				_process_child(accounts,form['display_account'],parent)
		return self.result_acc

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
			#_logger.error("crt_sech_ids3ids3["+str(context)+"]["+str(ids3)+"]["+str(ids2)+"]["+str(ids)+"]")	
			ids3 = self._get_children_and_consol_dcs(cr, uid, ids3, context)
		return ids2 + ids3
		
class report_trialbalance1(osv.AbstractModel):
	_name = 'report.account.report_trialbalance1'
	_inherit = 'report.abstract_report'
	_template = 'dincelaccount.report_trialbalance1'
	_wrapped_report_class = account_balance1

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
