from openerp.osv import fields, osv
from openerp.tools.translate import _
import logging
_logger = logging.getLogger(__name__)
#from dincel_journal import dincelaccount_invoice

class dincelaccount_refund_invoice(osv.osv_memory):
	_name = 'dincelaccount.refund_invoice'

	_columns = {
		'reason_refund': fields.char('Refund Reason'),
		'account_id':  fields.many2one('account.invoice', 'Account'),
		'journal_id':  fields.many2one('account.journal', 'Journal'),
		'date_invoice': fields.date('Refund date'),
		'invoice_id': fields.char('Invoice Ref', size=50),
		'cancel': fields.boolean('Cancel'),
		'ok2cancel': fields.boolean('Ok2Cancel'),
		'qty':fields.integer("Qty test"),
	}
	def _get_init_qty(self, cr, uid, context=None):
		return 1
		
	def _selectAccount(self, cr, uid, context=None):
		if context is None:
			context = {}
		_obj = self.pool.get('account.invoice')
		return context and context.get('active_id', False) or False
	
		#if not active_id:
		#	return False
		#return active_id	

	
	def _selectInvoice(self, cr, uid, context=None):
		if context is None:
			context = {}
		_obj = self.pool.get('account.invoice')
		return context and context.get('active_id', False) or False
		
		#if not active_id:
		#	return False
		 
		
		#return active_id
		
	def _selectJournal(self, cr, uid, context=None):
		if context is None:
			context = {}
		_obj = self.pool.get('account.journal')
		obj_ids = _obj.search(cr, uid, [('type', '=', "sale_refund")])
		if obj_ids:
			return obj_ids[0] if obj_ids[0] else False 
		else:
			return False	
	
	def cancelInvoice(self, cr, uid, ids, context=None):
		for obj in self.browse(cr, uid, ids, context=context):
			if obj.account_id.x_sale_order_id:
				sale=obj.account_id.x_sale_order_id
				#sale=obj.x_sale_order_id
				if sale.x_prod_status in ["part","complete"]:
					if obj.account_id.x_authorise_cancel==False:
						raise osv.except_osv(
							_('Cannot cancel this invoice!'),
							_('Because the order has been partially/fully produced. Please contact manager or account admin to continue.'))
		return self.refundInvoice(cr, uid, ids, context=context)
		
	def refundInvoice(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		
		#acct = dincelaccount_invoice(cr, uid, ids, context=context)#(cr,journal_id)
		#acct = self.pool.get('dincelaccount.invoice.dcs') 
		_objperiod 	= self.pool.get('account.period') 
		
		for obj in self.browse(cr, uid, ids, context=context):
			#acct.invoice_ref 	= obj.account_id.id
			#acct.journal_id 	= obj.journal_id.id
			#acct.date_invoice 	= obj.date_invoice
			#acct.comment		= obj.reason_refund
			
			#_objperiodcr		= _objperiod.find(cr, uid, obj.date_invoice, context=context)[0]
			#if _objperiodcr:
			#	period_id 		= _objperiodcr #[0] in above code
			#else:
			#	period_id 		= None
			
			#acct.period_id = period_id
			obj_inv = self.pool.get('account.invoice')	
			#obj_inv    = obj_inv.browse(cr, uid, self.invoice_ref, context)
			refund_id = obj_inv.invoice_make_refund(cr, uid, obj.account_id.id,obj.date_invoice, obj.reason_refund,obj.journal_id.id, context=context)
			if refund_id:
				try:
					url=self.pool.get('dincelaccount.config.settings').get_dcs_api_url(cr, uid, ids, "invoice", obj.account_id.id, context=context)	
					if url:
						val={
							"url":url,
							"name":obj.account_id.name,
							"ref_id":obj.account_id.id,
							"action":"invoice",
							"state":"pending",
						}
						self.pool.get('dincelbase.scheduletask').create(cr, uid, val, context=context)
					
				except Exception,e:
					_logger.error("invoice_make_refund.invoice_err["+str(e)+"]")	
					
				_obj = self.pool.get('account.invoice')	
				_obj.write(cr, uid, [obj.account_id.id], {'state': 'cancel'})
				view_id 		= self.pool.get('ir.ui.view').search(cr,uid,[('name', '=', 'dincelaccount.invoice.form')], limit=1) 	
				
				#//view_id=277
				value = {
                    'domain': str([('id', 'in', refund_id)]),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'account.invoice',
                    'view_id': view_id,
                    'type': 'ir.actions.act_window',
                    'name' : _('Invoice'),
                    'res_id': refund_id
                }
				#_logger.error("refundInvoicerefundInvoice:valuevalue -" + str(value)+"")
				return value
		'''	
		if acct.invoice_ref:
			refund_id = acct.insert_refund(acct.journal_id,acct.date_invoice,acct.comment)
			if refund_id:
				_obj = self.pool.get('account.invoice')
				_obj.write(cr, uid, [acct.invoice_ref], {'state': 'cancel'})
		'''
	_defaults={
		'invoice_id': _selectInvoice,
		'account_id': _selectAccount,
		'journal_id': _selectJournal,
		'date_invoice' : fields.date.context_today, 
		'qty': _get_init_qty,		
	} 
	
	def on_change_qty(self, cr, uid, ids, _qty,_invid, context=None):
	
		if context is None:
			context = {}
			
		#obj_inv = self.pool.get('account.invoice')	
		obj    = self.pool.get('account.invoice').browse(cr, uid, _invid, context)
		vals={'ok2cancel':True} 
		if obj.x_sale_order_id:
				sale=obj.x_sale_order_id
				if sale.x_prod_status in ["part","complete"]:
					#@_ret=False
					if obj.x_authorise_cancel==False:
						vals['ok2cancel']=False
		return {'value':vals}	
