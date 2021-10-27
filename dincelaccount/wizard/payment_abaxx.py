import time
from openerp.osv import fields, osv
from openerp.tools.translate import _
import logging
_logger = logging.getLogger(__name__)

class dincelpayment_abafile(osv.osv_memory):
	_name = "dincelpayment.abafile"
	
	_columns = {
		'date': fields.date('Payment Date'),
		'pay_lines':fields.one2many('dincelpayment.abaline', 'pay_abafile_id', 'Invoies'),
		'qty':fields.float("Qty test"),
        'amount': fields.float('Total'),
        'reference': fields.char('Ref #'),
		'company_id': fields.many2one('res.company', 'Company'),
	}
		
	def on_change_qty(self, cr, uid, ids, product_qty, pay_lines, context=None):
		
		new_pay_lines = []
		if context and context.get('active_ids'):
			
			_ids=context.get('active_ids')
			
			for o in self.pool.get('account.voucher').browse(cr, uid, _ids, context=context):
				
				for line in voucher.x_payline_ids:
					amt =line.amount
					invoice_id= line.invoice_id.id
					amount_original= line.invoice_id.amount_total
					invoice_number= line.invoice_id.invoice_number
					partner_id= line.invoice_id.partner_id.id
					vals = {
						'invoice_id':invoice_id,
						'amount':amt,
						'amount_original':amount_original,
						'partner_id': partner_id,
						'invoice_number':invoice_number,
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
		
class dincelpayment_abaline(osv.osv_memory):
	_name = "dincelpayment.abaline"
	_columns = {
		'pay_abafile_id': fields.many2one('dincelpayment.abafile', 'Pay Reference'),
		'invoice_id': fields.many2one('account.invoice', 'Invoice'),
		'amount': fields.float('Amount'),
		'name':fields.char('Memo'),
		'amount_original': fields.related('invoice_id', 'amount_total', type='float', string='Invoice Value',store=False),
		'partner_id':fields.related('invoice_id', 'partner_id', type='many2one', relation='res.partner', string='Partner'),
	}
	
 	 
	 