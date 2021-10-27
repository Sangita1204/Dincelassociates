import time
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
import logging
_logger = logging.getLogger(__name__)

class dincelaccount_bill_reverse(osv.osv_memory):
	_name = "dincelaccount.bill.reverse"
	
	_columns = {
		'date': fields.date('Date'),
        'comment': fields.char('Comments'),
		'voucher_id':fields.many2one('account.voucher', 'Payment Voucher'),
		'amount': fields.float('Total Amount'),
		'qty':fields.float("Qty test"),
	}
	
	
	def make_payment_reverse(self, cr, uid, ids, context=None):
		_objperiod 	= self.pool.get('account.period') 
		_vobj = self.pool.get('account.voucher') 
		_vobjline = self.pool.get('dincelaccount.voucher.payline')
		_objrev = self.browse(cr, uid, ids[0], context=context)
		
		_obj	= _objrev.voucher_id
		
		period_id	= _objperiod.find(cr, uid, _objrev.date, context=context)[0]
		
		vals = {
				'journal_id':_obj.journal_id.id,
				'amount':0,
				'x_amount_xtra':0,
				'x_amount_base':0,
				'account_id':_obj.account_id.id,
				'reference':_obj.reference,
				'type':'payment',
				'state':'draft',
				#'partner_id':_obj.partner_id.id,
				'period_id':period_id,
				'date':_objrev.date,
				'comment':_objrev.comment,
				}
		if 	_obj.partner_id:
			vals['partner_id']=_obj.partner_id.id 
		if 	_obj.x_paymethod_id:
			vals['x_paymethod_id']=_obj.x_paymethod_id.id 
		#if 	_obj.amount_fee:
		#	vals['x_amount_xtra']=_obj.amount_fee
			
		voucher_id =_vobj.create(cr, uid, vals, context=context)
		
		_amt_tot=0.0
		if voucher_id:
			for line in _obj.x_payline_ids:
				if line.amount:
					_amt_rev = float(line.amount)*-1.0
					_amt_tot+=_amt_rev
				
			
			 
					vals = {
						'voucher_id':voucher_id,
						'amount':_amt_rev,
						'invoice_id':line.invoice_id.id,
						'partner_id':line.invoice_id.partner_id.id,
						'supplier_id':line.invoice_id.partner_id.id,
						'type':'pay_invoice',
						'ref_aba':line.invoice_id.number,
						}
					_vobjline.create(cr, uid, vals, context=context)
					if line.invoice_id.state=="paid":
						self.pool.get('account.invoice').write(cr, uid, [line.invoice_id.id], {'state': 'open'})
				 
		vals={'amount':_amt_tot}  #,'state':'posted'
		_vobj.write(cr, uid, [voucher_id], vals)	#new voucher 
		_vobj.write(cr, uid, [_obj.id], {'state':'cancel'})	 #cancel the existing voucher
		_vobj.supplier_payment_validate_dcs(cr, uid, [voucher_id], context) #auto validate the payment...
		
	def on_change_qty(self, cr, uid, ids, product_qty, pay_lines, context=None):
		vals={}	 
		if context and context.get('active_ids'):
			
			_ids=context.get('active_ids')
			
			for o in self.pool.get('account.voucher').browse(cr, uid, _ids, context=context):
				vals['voucher_id']=o.id
				vals['amount']=o.amount 
				 
			
		return {'value':vals}
		
 
	def _get_init_qty(self, cr, uid, context=None):
		return 1
	_defaults = {
		'date': fields.date.context_today, #for getting local date...see...quotation (dincelcrm)
		'qty': _get_init_qty,
		}
 		 
	 