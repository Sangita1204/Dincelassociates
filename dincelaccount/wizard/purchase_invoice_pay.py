import time
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
import logging
_logger = logging.getLogger(__name__)

class dincelpurchase_pay_invoice(osv.osv_memory):
	_name = "dincelpurchase.pay.invoice"
	#_description = "Sales Make MRP"
	def _amount_total(self, cr, uid, ids, field_name, arg, context=None):
		res = {}
		#_total=0.0
		#_logger.error("updatelink_order_dcs._amount_untaxed_amount_untaxed0000["+str(_total)+"]")	
		for record in self.browse(cr, uid, ids):
			#if record.amount:
			#	_total=_total+record.amount
			#if record.amount_fee:
			#_total=record.amount+record.amount_fee	
			res[record.id] = record.amount+record.amount_fee	
		return res
		
	def onchange_fee_amt(self, cr, uid, ids, _amt, _fee, context=None):
		context = context or {}
		return {'value': {'amount_total': (_amt+_fee)}}	
		
	def onchange_pay_lines(self, cr, uid, ids, payline_ids, paymethod_id,  _amt, _fee, context=None):
		context = context or {}
		
		amt = 0.0
		amt_fee = 0.0 
		
		if payline_ids:
			
			line_ids = self.resolve_2many_commands(cr, uid, 'pay_lines', payline_ids, ['amount','reconcile'], context)
			
			for line in line_ids:
				if line:
					#_logger.error("updatelink_order_dcs.onchange_pay_lineslinelineleine["+str(line)+"]")	
					if line['amount']:
						amt += line['amount']
			try:
				if paymethod_id:
					obj		= self.pool.get('dincelaccount.paymethod').browse(cr,uid,paymethod_id,context=context)
					if obj.fee_purchase:
						amt_fee=amt*obj.fee_purchase*0.01
						#amt += amt_fee
			except ValueError:
				pass
		return {'value': {'amount': amt,'amount_total': (amt+amt_fee),'amount_fee':amt_fee}}
		
	_columns = {
		'date': fields.date('Payment Date'),
		'pay_lines':fields.one2many('dincelpurchase.pay.invoice.line', 'pay_invoice_id', 'Invoies'),
		'qty':fields.float("Qty test"),
		'journal_id':fields.many2one('account.journal', 'Journal'),
        'account_id':fields.many2one('account.account', 'Account'),
		'partner_id':fields.many2one('res.partner', 'Partner'),
        'amount': fields.float('Total'),
        'reference': fields.char('Ref #'),
		'comment': fields.char('Payment Description', size=18), #changed from 12 to 20 #as per Rita 20/3/2017 #changed back to 12 as per Felix (for aba file generation) [Dincel Const. Sys]
		'company_id': fields.many2one('res.company', 'Company'),
		'x_paymethod_id':fields.many2one('dincelaccount.paymethod', 'Pay Method'),
		'amount_fee': fields.float('Card Fee'),
		'amount_total': fields.function(_amount_total, digits_compute=dp.get_precision('Account'), string='Total'),
	}
	
	def button_reset_total(self, cr, uid, ids, context=None):
		return True
		
	def make_payment_dcs(self, cr, uid, ids, context=None):
		_vobj = self.pool.get('account.voucher')
		_vobjline = self.pool.get('dincelaccount.voucher.payline')
		_obj = self.pool.get('dincelpurchase.pay.invoice').browse(cr, uid, ids[0], context=context)
		tot_amt = 0.0
		if _obj.pay_lines: 
			for line in _obj.pay_lines:
				if line.amount > 0.0:
					tot_amt += line.amount
		
		_objperiod 	= self.pool.get('account.period') 
		period_id	= _objperiod.find(cr, uid, _obj.date, context=context)[0]
		vals = {
			'journal_id':_obj.journal_id.id,
			'amount':tot_amt,
			'x_amount_xtra':0,
			'x_amount_base':tot_amt,
			'account_id':_obj.account_id.id,
			'reference':_obj.reference,
			'type':'payment',
			'state':'draft',
			#'partner_id':_obj.partner_id.id,
			'period_id':period_id,
			'date':_obj.date,
			'comment':_obj.comment,
			}
		if 	_obj.partner_id:
			vals['partner_id']=_obj.partner_id.id 
		if 	_obj.x_paymethod_id:
			vals['x_paymethod_id']=_obj.x_paymethod_id.id 
		if 	_obj.amount_fee:
			vals['x_amount_xtra']=_obj.amount_fee
			
		#_logger.error("make_payment_dcsmake_payment_dcs["+str(vals)+"]")	
		voucher_id =_vobj.create(cr, uid, vals, context=context)
			
		if tot_amt > 0.0:
			for line in _obj.pay_lines:
				if line.amount > 0.0:
					vals = {
						'voucher_id':voucher_id,
						'amount':line.amount,
						'invoice_id':line.invoice_id.id,
						'partner_id':line.invoice_id.partner_id.id,
						'supplier_id':line.invoice_id.partner_id.id,
						'type':'pay_invoice',
						'ref_aba':line.invoice_id.number,
						}
					_vobjline.create(cr, uid, vals, context=context)
					
				if line.amount == line.amount_balance:
					self.pool.get('account.invoice').write(cr, uid, [line.invoice_id.id], {'state': 'paid'})
			_vobj.supplier_payment_validate_dcs(cr, uid, [voucher_id], context) #auto validate the payment...
		else:#refund invoice ....
			#eg GIO /etc
			for line in _obj.pay_lines:
				if line.amount:
					vals = {
						'voucher_id':voucher_id,
						'amount':line.amount,
						'invoice_id':line.invoice_id.id,
						'partner_id':line.invoice_id.partner_id.id,
						'supplier_id':line.invoice_id.partner_id.id,
						'type':'pay_invoice',
						'ref_aba':line.invoice_id.number,
						}
					_vobjline.create(cr, uid, vals, context=context)
					
				if line.amount == line.amount_balance:
					self.pool.get('account.invoice').write(cr, uid, [line.invoice_id.id], {'state': 'paid'})
			_vobj.supplier_payment_validate_dcs(cr, uid, [voucher_id], context) #auto validate the payment...		
		return True
		
	
	def onchange_journal_dcs(self, cr, uid, ids, journal_id, context=None):
		if context is None:
			context = {}
		vals={}	
		obj=self.pool.get('account.journal').browse(cr, uid, journal_id, context=context)
		if obj:
			account_id 	= obj.default_debit_account_id.id
			vals		= {'account_id':account_id,'x_paymethod_id':None} #to clear the list for none setup
			if obj.x_paymethod_id:
				vals['x_paymethod_id']=obj.x_paymethod_id.id
				
		return {'value':vals}	
		
	def onchange_account_id(self, cr, uid, ids, account_id, context=None):
		return True
		
	def on_change_qty(self, cr, uid, ids, product_qty, pay_lines, context=None):
		
		new_pay_lines = []
		_partner_id=None
		_prev_partner=None
		if context and context.get('active_ids'):
			
			_ids=context.get('active_ids')
			
			for o in self.pool.get('account.invoice').browse(cr, uid, _ids, context=context):
				
				if o.state=="open" and o.type=="in_invoice":	#in_invoice=supplier invoice only
					#if not _partner_id:
					_partner_id= o.partner_id.id or False
					if not _prev_partner:
						_prev_partner=_partner_id
					if _partner_id:#== o.partner_id.id: #take only one partner
						amount_bal=o.amount_total
						try:
							sql="select sum(amount) as tot from dincelaccount_voucher_payline where invoice_id=" + str(o.id) #type='pay_invoice' and [this condition removed...]
							cr.execute(sql)
							rows = cr.fetchall()
							if len(rows) > 0 and rows[0][0]:
								amount_bal = amount_bal-float(rows[0][0])
						except ValueError:
							pass
						vals = {
							'invoice_id':o.id,
							'supplier_invoice_number':o.supplier_invoice_number,
							'amount_balance':amount_bal,
							'date_due':o.date_due or False,
							'date':o.date_due or False,
							'amount_original':o.amount_total,
							'amount':0,
							'reconcile':False,
							'partner_id': o.partner_id.id or False,
							'invoice_number':o.internal_number,
						}
						new_pay_lines.append(vals)
						
		vals={'pay_lines': new_pay_lines}	
		if _prev_partner==_partner_id:
			#_partner_id=None
			vals['partner_id']=_partner_id
		else:	
			vals['partner_id']=None
			
		return {'value':vals}
		
 
	def _get_init_qty(self, cr, uid, context=None):
		return 1
	_defaults = {
		'date': fields.date.context_today, #for getting local date...see...quotation (dincelcrm)
		'qty': _get_init_qty,
		#'date': lambda *a: time.strftime('%Y-%m-%d'), not getting local date...but gmt
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'account.voucher',context=c),
		}
		
class dincelpurchase_pay_invoice_line(osv.osv_memory):
	_name = "dincelpurchase.pay.invoice.line"
	def _amount_subtotal(self, cr, uid, ids, field_name, arg, context=None):
		res = {}
		#_total=0.0
		#_logger.error("updatelink_order_dcs._amount_untaxed_amount_untaxed0000["+str(_total)+"]")	
		for record in self.browse(cr, uid, ids):
			#if record.amount:
			#	_total=_total+record.amount
			#if record.amount_fee:
			#_total=record.amount+record.amount_fee	
			res[record.id] = record.amount+record.amount_fee	
		return res
		
	_columns = {
		'pay_invoice_id': fields.many2one('dincelpurchase.pay.invoice', 'Pay Reference'),
		'invoice_id': fields.many2one('account.invoice', 'Invoice'),
		'reconcile': fields.boolean('Full Reconcile'),
		'supplier_invoice_number':fields.char("Supplier Invoice No."),
		'amount': fields.float('Amount'),
		'amount_fee': fields.float('Card Fee'),
		'amount_balance': fields.float('Amount Balance'),
		'amount_subtotal': fields.function(_amount_subtotal, digits_compute=dp.get_precision('Account'), string='Subtotal'),
		'date':fields.date('Invoice Date'),
		'date_due':fields.date('Due Date'),
		'name':fields.char('Memo'),
		'paymethod_id':fields.many2one('dincelaccount.paymethod', 'Pay Method'),
		'amount_original': fields.related('invoice_id', 'amount_total', type='float', string='Invoice Value',store=False),
		'invoice_number': fields.related('invoice_id', 'internal_number', type='text', string='Number',store=False),
		'partner_id':fields.related('invoice_id', 'partner_id', type='many2one', relation='res.partner', string='Partner'),
		#'paymethod_id':fields.many2one('dincelaccount.paymethod', 'Pay Method'),
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
	 