from openerp.osv import osv, fields
from datetime import date
#from openerp.addons.base_status.base_state import base_state
import time 
import datetime
import logging
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp import api
from time import gmtime, strftime
_logger = logging.getLogger(__name__)

class dincelpurchase_nonstock(osv.Model):
	_inherit = "account.voucher"
	def dcs_print_po(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		datas = {'ids': context.get('active_ids', [])}
	 
		datas['form']  = self.read(cr, uid, ids, context=context)[0]

		return self.pool['report'].get_action(cr, uid, [], 'purchase.report_po_nonstock', data=datas, context=context)	
		
	def dcs_print_po_pdf(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		datas = {'ids': context.get('active_ids', [])}
	 
		datas['form']  = self.read(cr, uid, ids, context=context)[0]

		return self.pool['report'].get_action(cr, uid, [], 'purchase.report_po_nonstock_pdf', data=datas, context=context)		
		
class dincelpurchase_voucher_line(osv.Model):
	_inherit = "account.voucher.line"
	def on_change_amt(self, cr, uid, ids, amount, context=None):
		return {'value': {'amount': amount}}
		
	def onchange_tax(self, cr, uid, ids, taxid, amt, context = None):	
		_tax=0
		if taxid:
			obj	= self.pool.get('account.tax').browse(cr,uid,taxid,context=context)
			_tax=obj.amount*amt
		return {'value': {'x_tax_amount': _tax,'amount': _tax+amt}}	
'''		
class dincelpurchase_nonstock(osv.Model):
	_name = "dincelpurchase.nonstock"
	_columns = {
		'name': fields.char('Memo'),
		'reference': fields.char('Ref #'),
		'date': fields.date('Date'),
		'account_id':fields.many2one('account.account','Account', required=True),
		'partner_id':fields.many2one('res.partner','Supplier'),
		'journal_id':fields.many2one('account.journal','Journal'),
		'amount':fields.float('Amount', digits_compute=dp.get_precision('Account')),
		'nonstock_lines':fields.one2many('dincelpurchase.nonstock.line', 'purchase_id', 'Nonstock Purchase Lines'),
		'state':fields.selection(
			[('draft','Draft'),
			 ('cancel','Cancelled'),
			 ('proforma','Pro-forma'),
			 ('posted','Posted')
			], 'Status', readonly=True, track_visibility='onchange'),
	}
	_defaults = {
		'date': fields.date.context_today,
	}	
	
class dincelpurchase_nonstock_line(osv.Model):
	_name = "dincelpurchase.nonstock.line"
	_columns = {
		'name': fields.char('Name'),
		'account_id':fields.many2one('account.account','Account', required=True),
		'untax_amount':fields.float('Untax Amount'),
		'amount':fields.float('Amount', digits_compute=dp.get_precision('Account')),
		'purchase_id': fields.many2one('dincelpurchase.nonstock', 'Purchase Order'),
		'x_region_id': fields.many2one('dincelaccount.region', 'A/c Region'),
		}'''
		