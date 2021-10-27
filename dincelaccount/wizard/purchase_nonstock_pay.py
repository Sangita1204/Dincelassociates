import time
from openerp.osv import fields, osv
from openerp.tools.translate import _
import logging
_logger = logging.getLogger(__name__)

class dincelpurchase_nonstock_pay(osv.osv_memory):
	_name = "dincelpurchase.nonstock.pay"
	#_description = "Sales Make MRP"
	_columns = {
		'date': fields.date('Payment Date'),
		'pay_lines':fields.one2many('dincelpurchase.nonstock.pay.line', 'pay_nonstock_id', 'Purchases'),
		'qty':fields.float("Qty test"),
		'journal_id':fields.many2one('account.journal', 'Journal'),
        'account_id':fields.many2one('account.account', 'Account'),
        'amount': fields.float('Total'),
        'reference': fields.char('Ref #'),
		'comment': fields.char('Payment Description', size=12),
		'company_id': fields.many2one('res.company', 'Company'),
	}
	
	def make_payment_dcs(self, cr, uid, ids, context=None):
		_vobj = self.pool.get('account.voucher')
		#_vobjline = self.pool.get('dincelpurchase.nonstock.pay.line')
		_vobjline = self.pool.get('dincelaccount.voucher.payline')
		_obj = self.pool.get('dincelpurchase.nonstock.pay').browse(cr, uid, ids[0], context=context)
		tot_amt = 0.0
		if _obj.pay_lines: 
			for line in _obj.pay_lines:
				if line.amount > 0.0:
					tot_amt += line.amount
		if tot_amt > 0.0:
			_objperiod 	= self.pool.get('account.period') 
			period_id	= _objperiod.find(cr, uid, _obj.date, context=context)[0]
			
			vals = {
				'journal_id':_obj.journal_id.id,
				'amount':tot_amt,
				'x_amount_xtra':tot_amt,
				'x_amount_base':tot_amt,
				'account_id':_obj.account_id.id,
				'reference':_obj.reference,
				'type':'payment',
				'state':'draft',
				'period_id':period_id,
				'date':_obj.date,
				'comment':_obj.comment,
				}
				
			#_logger.error("make_payment_dcsmake_payment_dcs["+str(vals)+"]")	
			voucher_id =_vobj.create(cr, uid, vals, context=context)
			for line in _obj.pay_lines:
				if line.amount > 0.0:
					vals = {
						'voucher_id':voucher_id,
						'pay_voucher_id':line.voucher_id.id,
						'amount':line.amount,
						'type':'pay_voucher',
						'supplier_id':line.voucher_id.partner_id.id,
						'ref_aba':line.voucher_id.number,
						#'invoice_id':line.invoice_id.id,
						}
					_vobjline.create(cr, uid, vals, context=context)
				if line.amount == line.amount_balance:
					self.pool.get('account.voucher').write(cr, uid, [line.voucher_id.id], {'x_paystate': 'paid'})

		return True
		

	def onchange_journal_dcs(self, cr, uid, ids, journal_id, context=None):
		if context is None:
			context = {}
		vals={}	
		obj=self.pool.get('account.journal').browse(cr, uid, journal_id, context=context)
		if obj:
			account_id = obj.default_debit_account_id.id
			vals={'account_id':account_id}
		return {'value':vals}	
		
	def on_change_qty(self, cr, uid, ids, product_qty, pay_lines, context=None):
		
		new_pay_lines = []
		if context and context.get('active_ids'):
			
			_ids=context.get('active_ids')
			
			for o in self.pool.get('account.voucher').browse(cr, uid, _ids, context=context):
				
				if o.state=="posted" and o.type=="purchase":	#in_invoice=supplier invoice only
					amount_bal=o.amount
					try:
						sql="select sum(amount) as tot from dincelaccount_voucher_payline where type='pay_voucher' and pay_voucher_id=" + str(o.id)+""
						#_logger.error("on_change_qtyon_change_qty["+str(sql)+"]")
						cr.execute(sql)
						rows = cr.fetchall()
						if len(rows) > 0 and rows[0][0]:
							amount_bal = amount_bal-float(rows[0][0])
					except ValueError:
						pass
					vals = {
						'voucher_id':o.id,
						'amount_balance':amount_bal,
						'date_due':o.date_due or False,
						'date':o.date_due or False,
						#'amount_original':o.amount_total,
						'partner_id': o.partner_id.id or False,
						#'invoice_number':o.internal_number,
					}
					new_pay_lines.append(vals)
        
		return {'value': {'pay_lines': new_pay_lines}}
		
 
	def _get_init_qty(self, cr, uid, context=None):
		return 1
	_defaults = {
		#'date': fields.date.context_today,
		'qty': _get_init_qty,
		'date': lambda *a: time.strftime('%Y-%m-%d'),
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'account.voucher',context=c),
		}
		
class dincelpurchase_nonstock_pay_line(osv.osv_memory):
	_name = "dincelpurchase.nonstock.pay.line"
	_columns = {
		'pay_nonstock_id': fields.many2one('dincelpurchase.nonstock.pay', 'Pay Reference'),
		'voucher_id': fields.many2one('account.voucher', 'Receipt'),
		'reconcile': fields.boolean('Full Reconcile'),
		'amount': fields.float('Amount'),
		'amount_balance': fields.float('Amount Balance'),
		'date':fields.date('Invoice Date'),
		'date_due':fields.date('Due Date'),
		'name':fields.char('Memo'),
		'paymethod_id':fields.many2one('dincelaccount.paymethod', 'Pay Method'),
		'amount_original': fields.related('voucher_id', 'amount', type='float', string='Invoice Value',store=False),
		'invoice_number': fields.related('voucher_id', 'number', type='text', string='Number',store=False),
		'partner_id':fields.related('voucher_id', 'partner_id', type='many2one', relation='res.partner', string='Partner'),
	}
	
	def onchange_reconcile(self, cr, uid, ids, reconcile, amount, amount_unreconciled, context=None):
		amount=0.0
		#vals = {'amount': 0.0}
		if reconcile:
			amount=amount_unreconciled
		
		vals = { 'amount': amount}
		return {'value': vals}
		
	def onchange_amount(self, cr, uid, ids, amount, amount_unreconciled, context=None):
		vals = {}
		if amount:
			vals['reconcile'] = (amount == amount_unreconciled)
			vals['amount'] = amount#vals = { 'amount': amount}
			
		return {'value': vals}			 
	 