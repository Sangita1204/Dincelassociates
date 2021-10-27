from openerp.osv import osv, fields
from datetime import date
#from openerp.addons.base_status.base_state import base_state
import time 
import datetime
import csv
import logging
#from dinceljournal import dincelaccount_journal
#from dinceljournal import dincelaccount_invoice
from dincel_journal import dincelaccount_journal
from openerp.tools.translate import _
from time import gmtime, strftime
_logger = logging.getLogger(__name__)

class dincelaccount_voucher(osv.Model):
	_inherit = "account.voucher"
	'''def write(self, cr, uid, ids, vals, context=None):
		linsn=0
		res  = super(dincelaccount_voucher, self).write(cr, uid, ids, vals, context=context)
		for record in self.browse(cr, uid, ids):
			 for line in record.line_ids:
				ac_code= line.invoice_id.code
				linsn +=1
				#_logger.error("dincelaccount_voucherdincelaccount_voucher:["+ac_code+"]["+ac_code[:1]+"]")	
				if ac_code[:1] in ['4','5','6'] :
					if not line.x_region_id:
						raise osv.except_osv(_('Error!'), _('Please select a region at line '+str(linsn)+'.'))
		return res'''	
	def compute_tax_purchase_dcs(self, cr, uid, ids, context=None):
		tax_pool = self.pool.get('account.tax')
		partner_pool = self.pool.get('res.partner')
		position_pool = self.pool.get('account.fiscal.position')
		voucher_line_pool = self.pool.get('account.voucher.line')
		voucher_pool = self.pool.get('account.voucher')
		if context is None: context = {}

		for voucher in voucher_pool.browse(cr, uid, ids, context=context):
			voucher_amount = 0.0
			total_tax=0.0
			for line in voucher.line_dr_ids:
				#voucher_amount += line.untax_amount# or line.amount
				if line.x_tax_id:
					_taxamt=line.x_tax_id.amount*line.untax_amount
				else:
					_taxamt=0.0
				#voucher_amount += _taxamt
				line.amount = line.untax_amount + _taxamt
				voucher_amount += line.amount
				total_tax += _taxamt
				voucher_line_pool.write(cr, uid, [line.id], {'amount':line.amount, 'untax_amount':line.untax_amount, 'x_tax_amount':_taxamt})

		  

			self.write(cr, uid, [voucher.id], {'amount':voucher_amount, 'tax_amount':total_tax})
			#_logger.error("onchange_amount_total_taxtotal_tax["+str(total)+"]["+str(total_tax)+"]")
		return True

		
class dincelaccount_voucher_line(osv.Model):
	_inherit = "account.voucher.line"
	_columns={
		'x_region_id': fields.many2one('dincelaccount.region', 'A/c Region'),
		'x_coststate_id':fields.many2one("res.country.state","Cost Centre"),
		'x_tax_id':fields.many2one("account.tax","Tax"),
		'x_tax_amount':fields.float('Tax Amount'),
	}
	
	#   //return {'type': 'ir.actions.act_window_close'}
	#
	#//voucher_obj.proforma_voucher(cr, uid, voucher_ids, context=context)
	

class dincelaccount_refund_purinvoice(osv.osv_memory):
	_name = 'dincelaccount.refund_purinvoice'

	_columns = {
		'reason_refund': fields.char('Cancel Reason'),
		'invoice_id':  fields.many2one('account.invoice', 'Account'),
		'journal_id':  fields.many2one('account.journal', 'Journal'),
		'date_invoice': fields.date('Refund date'),
		'cancel': fields.boolean('Cancel'),
	}
 
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
		obj_ids = _obj.search(cr, uid, [('type', '=', "purchase_refund")])
		if obj_ids:
			return obj_ids[0] if obj_ids[0] else False 
		else:
			return False	
	
	def cancelInvoice(self, cr, uid, ids, context=None):
		return self.refundInvoice(cr, uid, ids, context=context)
		
	def refundInvoice(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		
		#acct = dincelaccount_invoice(cr, uid, ids, context=context)#(cr,journal_id)
		#acct = self.pool.get('dincelaccount.invoice.dcs') 
		_objperiod 	= self.pool.get('account.period') 
		
		for obj in self.browse(cr, uid, ids, context=context):
			
			obj_inv = self.pool.get('account.invoice')	
			
			refund_id = obj_inv.invoice_make_purchase_refund(cr, uid, obj.invoice_id.id,obj.date_invoice, obj.reason_refund,obj.journal_id.id, context=context)
			if refund_id:
				sql="update account_invoice set state='cancel' where id='%s' " % (str(obj.invoice_id.id))
				cr.execute(sql) #so that it will ignore issues while calling .write() eg. duplicate supplier ref no...
				#_obj = self.pool.get('account.invoice')	
				#_obj.write(cr, uid, [obj.invoice_id.id], {'state': 'cancel'})
				view_id 		= self.pool.get('ir.ui.view').search(cr,uid,[('name', '=', 'dincelaccount.supplier.invoice.form')], limit=1) 	
				#_logger.error("invoice_make_purchase_refund:valuevalue -" + str(view_id)+"")
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
		#'invoice_id': _selectInvoice,
		'invoice_id': _selectInvoice,
		'journal_id': _selectJournal,
		'date_invoice' : fields.date.context_today,  
	} 
	