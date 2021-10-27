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

from openerp.osv import fields, osv


class account_report_general_ledger1(osv.osv_memory):
    _inherit = "account.report.general.ledger"
    _name = "account.report.general.ledger1"
    _description = "General Ledger Report 1"
 

    def onchange_fiscalyear(self, cr, uid, ids, fiscalyear=False, context=None):
        res = {}
        if not fiscalyear:
            res['value'] = {'initial_balance': False}
        return res

    def _print_report1(self, cr, uid, ids, data, context=None):
        if context is None:
            context = {}
        data = self.pre_print_report1(cr, uid, ids, data, context=context)
        data['form'].update(self.read(cr, uid, ids, ['landscape',  'initial_balance', 'amount_currency', 'sortby'])[0])
        if not data['form']['fiscalyear_id']:# GTK client problem onchange does not consider in save record
            data['form'].update({'initial_balance': False})

        if data['form']['landscape'] is False:
            data['form'].pop('landscape')
        else:
            context['landscape'] = data['form']['landscape']

        return self.pool['report'].get_action(cr, uid, [], 'account.report_generalledger1', data=data, context=context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
