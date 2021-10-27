from openerp.osv import osv, fields#, api
from datetime import date
from openerp import models, api
#from openerp.addons.base_status.base_state import base_state
import time 
import datetime
import csv
import logging

import urllib
import base64
import psycopg2
import os

from openerp import tools
from dincel_journal import dincelaccount_journal
from openerp.tools.translate import _
from time import gmtime, strftime
_logger = logging.getLogger(__name__)

class dincelaccount_act_voucher(osv.Model):
	_inherit = "account.voucher"
	
	def _get_writeoff_amount_dcs(self, cr, uid, ids, name, args, context=None):
		if not ids: return {}
		currency_obj = self.pool.get('res.currency')
		res = {}
		amt = 0.0
		for voucher in self.browse(cr, uid, ids, context=context):
			#sign = voucher.type == 'payment' and -1 or 1
			for l in voucher.x_payline_ids:
				amt += l.amount
			 
			currency = voucher.currency_id or voucher.company_id.currency_id
			res[voucher.id] =  currency_obj.round(cr, uid, currency, voucher.amount -  (amt))
		return res
	
	def onchange_pay_journal_dcs(self, cr, uid, ids, journal_id, context=None):
		if context is None:
			context = {}
		vals={}	
		obj=self.pool.get('account.journal').browse(cr, uid, journal_id, context=context)
		if obj:
			account_id = obj.default_debit_account_id.id
			vals={'x_account_id':account_id}
		return {'value':vals}	

	def validate_po_nostock_dcs(self, cr, uid, ids, context=None):
		#new_id		= ids[0]
		_obj1 		= self.pool.get('account.voucher')
		_obj 	= _obj1.browse(cr, uid, ids[0], context=context)
		#if not _obj.x_journal_id or not _obj.x_account_id:
		#	raise osv.except_osv(_('Error!'),_('Please select a payment method!'))
		#	return False
		amt_total=_obj.tax_amount	
		for line in _obj.line_dr_ids:
			amt_total+=line.amount
		if amt_total!= 	_obj.amount:
			raise osv.except_osv(_('Error!'),_('Invalid amount in total found!'))
			return False
		_name = self.pool.get('ir.sequence').get(cr, uid, 'purchase.nonstock')	#custom sequence number	
		#_logger.error("validate_po_nostock_dcsvalidate_po_nostock_dcs["+str(ids)+"]["+str(_name)+"]")
		_obj.write(cr, uid, _obj.id, {'state':'posted','number':_name,'name':_name}, context=context)	
		_obj_j = self.pool.get('dincelaccount.journal')
		ret  = _obj_j.purchase_nostock2journals(cr, uid, ids, _obj, context=context)
		#if ret:
		#	_obj1.write(cr, uid, _obj.id, {'state':'posted'}, context=context)
		return True
	
	_columns = {
		'x_project_id': fields.many2one('res.partner','Project / Site'),
		'x_payline_ids': fields.one2many('dincelaccount.voucher.payline', 'voucher_id', 'Voucher Lines'),
		'x_amount_xtra': fields.float('Difference Amount'),
		'x_amount_base': fields.float('Base Amount'), #less extra fee for credit cards, etc
		#'x_writeoff_amount': fields.function(_get_writeoff_amount_dcs, string='Difference Amount', type='float', readonly=True, help="Computed as the difference between the amount stated in the voucher and the sum of allocation on the voucher lines."),
		'x_aba_datas': fields.binary('ABA Data'),
		'x_aba_status':fields.char('Aba Status'),
		'x_journal_id':fields.many2one('account.journal', 'Pay Method'),
        'x_account_id':fields.many2one('account.account', 'Pay Account'),
		'x_paystate':fields.selection(
            [('draft','Draft'),
             ('cancel','Cancelled'),
             ('paid','Paid')
            ], 'Status'),
	}
	_defaults={
		'x_aba_status':'0',
		'x_paystate':'draft',
	}
	
	def onchange_journal_dcs(self, cr, uid, ids, journal_id,  date, amount, type, company_id, context=None):
		if context is None:
			context = {}
		vals={}	
		obj=self.pool.get('account.journal').browse(cr, uid, journal_id, context=context)
		if obj:
			account_id = obj.default_debit_account_id.id
			vals={'account_id':account_id}
		return {'value':vals}	
		
	def recompute_voucher_lines_dcs(self, cr, uid, ids, partner_id, journal_id, price, currency_id, ttype, date, context=None):

		def _remove_noise_in_o2m():
			if line.reconcile_partial_id:
				if currency_id == line.currency_id.id:
					if line.amount_residual_currency <= 0:
						return True
				else:
					if line.amount_residual <= 0:
						return True
			return False

		if context is None:
			context = {}
		context_multi_currency = context.copy()

		currency_pool = self.pool.get('res.currency')
		move_line_pool = self.pool.get('account.move.line')
		partner_pool = self.pool.get('res.partner')
		journal_pool = self.pool.get('account.journal')
		line_pool = self.pool.get('account.voucher.line')

		#set default values
		default = {
			'value': {'line_dr_ids': [], 'line_cr_ids': [], 'pre_line': False},
		}

		# drop existing lines
		line_ids = ids and line_pool.search(cr, uid, [('voucher_id', '=', ids[0])])
		for line in line_pool.browse(cr, uid, line_ids, context=context):
			if line.type == 'cr':
				default['value']['line_cr_ids'].append((2, line.id))
			else:
				default['value']['line_dr_ids'].append((2, line.id))

		if not partner_id or not journal_id:
			return default

		journal = journal_pool.browse(cr, uid, journal_id, context=context)
		partner = partner_pool.browse(cr, uid, partner_id, context=context)
		currency_id = currency_id or journal.company_id.currency_id.id

		total_credit = 0.0
		total_debit = 0.0
		account_type = None
		if context.get('account_id'):
			account_type = self.pool['account.account'].browse(cr, uid, context['account_id'], context=context).type
		if ttype == 'payment':
			if not account_type:
				account_type = 'payable'
			total_debit = price or 0.0
		else:
			total_credit = price or 0.0
			if not account_type:
				account_type = 'receivable'

		if not context.get('move_line_ids', False):
			ids = move_line_pool.search(cr, uid, [('state','=','valid'), ('account_id.type', '=', account_type), ('reconcile_id', '=', False), ('partner_id', '=', partner_id)], context=context)
		else:
			ids = context['move_line_ids']
		invoice_id = context.get('invoice_id', False)
		company_currency = journal.company_id.currency_id.id
		move_lines_found = []

		#order the lines by most old first
		ids.reverse()
		account_move_lines = move_line_pool.browse(cr, uid, ids, context=context)

		#compute the total debit/credit and look for a matching open amount or invoice
		for line in account_move_lines:
			if _remove_noise_in_o2m():
				continue

			if invoice_id:
				if line.invoice.id == invoice_id:
					#if the invoice linked to the voucher line is equal to the invoice_id in context
					#then we assign the amount on that line, whatever the other voucher lines
					move_lines_found.append(line.id)
			elif currency_id == company_currency:
				#otherwise treatments is the same but with other field names
				if line.amount_residual == price:
					#if the amount residual is equal the amount voucher, we assign it to that voucher
					#line, whatever the other voucher lines
					move_lines_found.append(line.id)
					break
				#otherwise we will split the voucher amount on each line (by most old first)
				total_credit += line.credit or 0.0
				total_debit += line.debit or 0.0
			elif currency_id == line.currency_id.id:
				if line.amount_residual_currency == price:
					move_lines_found.append(line.id)
					break
				total_credit += line.credit and line.amount_currency or 0.0
				total_debit += line.debit and line.amount_currency or 0.0

		remaining_amount = price
		#voucher line creation
		for line in account_move_lines:

			if _remove_noise_in_o2m():
				continue

			if line.currency_id and currency_id == line.currency_id.id:
				amount_original = abs(line.amount_currency)
				amount_unreconciled = abs(line.amount_residual_currency)
			else:
				#always use the amount booked in the company currency as the basis of the conversion into the voucher currency
				amount_original = currency_pool.compute(cr, uid, company_currency, currency_id, line.credit or line.debit or 0.0, context=context_multi_currency)
				amount_unreconciled = currency_pool.compute(cr, uid, company_currency, currency_id, abs(line.amount_residual), context=context_multi_currency)
			line_currency_id = line.currency_id and line.currency_id.id or company_currency
			rs = {
				'name':line.move_id.name,
				'type': line.credit and 'dr' or 'cr',
				'move_line_id':line.id,
				'account_id':line.account_id.id,
				'amount_original': amount_original,
				'amount': (line.id in move_lines_found) and min(abs(remaining_amount), amount_unreconciled) or 0.0,
				'date_original':line.date,
				'date_due':line.date_maturity,
				'amount_unreconciled': amount_unreconciled,
				'currency_id': line_currency_id,
			}
			remaining_amount -= rs['amount']
			#in case a corresponding move_line hasn't been found, we now try to assign the voucher amount
			#on existing invoices: we split voucher amount by most old first, but only for lines in the same currency
			if not move_lines_found:
				if currency_id == line_currency_id:
					if line.credit:
						amount = min(amount_unreconciled, abs(total_debit))
						rs['amount'] = amount
						total_debit -= amount
					else:
						amount = min(amount_unreconciled, abs(total_credit))
						rs['amount'] = amount
						total_credit -= amount

			if rs['amount_unreconciled'] == rs['amount']:
				rs['reconcile'] = True

			if rs['type'] == 'cr':
				default['value']['line_cr_ids'].append(rs)
			else:
				default['value']['line_dr_ids'].append(rs)

			if len(default['value']['line_cr_ids']) > 0:
				default['value']['pre_line'] = 1
			elif len(default['value']['line_dr_ids']) > 0:
				default['value']['pre_line'] = 1
			default['value']['writeoff_amount'] = self._compute_writeoff_amount(cr, uid, default['value']['line_dr_ids'], default['value']['line_cr_ids'], price, ttype)
		return default
	
	def onchange_amount_dcs(self, cr, uid, ids, amount, rate, partner_id, journal_id, currency_id, ttype, date, payment_rate_currency_id, company_id, context=None):
		if context is None:
			context = {}
		ctx = context.copy()
		ctx.update({'date': date})
		#read the voucher rate with the right date in the context
		currency_id = currency_id or self.pool.get('res.company').browse(cr, uid, company_id, context=ctx).currency_id.id
		voucher_rate = self.pool.get('res.currency').read(cr, uid, [currency_id], ['rate'], context=ctx)[0]['rate']
		ctx.update({
			'voucher_special_currency': payment_rate_currency_id,
			'voucher_special_currency_rate': rate * voucher_rate})
		
		_payline = self.pool.get('dincelaccount.voucher.payline')
		if not ctx.get('x_payline_ids', False):
			_ids = _payline.search(cr, uid, [('partner_id', '=', partner_id)], context=context)
			#_logger.error("onchange_amount_dcs111["+str(_ids)+"]["+str(partner_id)+"]")
		else:
			_ids = ctx['x_payline_ids']
			#_logger.error("onchange_amount_dcs1231432["+str(_ids)+"]["+str(partner_id)+"]")
		#ids.reverse()
		_lines = _payline.browse(cr, uid, _ids, context=context)
		
		res = self.recompute_voucher_lines_dcs(cr, uid, ids, partner_id, journal_id, amount, currency_id, ttype, date, context=ctx)
		#res['value']['x_writeoff_amount'] = self._compute_writeoff_amount_dcs(cr, uid, _lines, amount, ttype)
		vals = self.onchange_rate(cr, uid, ids, rate, amount, currency_id, payment_rate_currency_id, company_id, context=ctx)
		for key in vals.keys():
			res[key].update(vals[key])
		return res
		
	def _compute_writeoff_amount_dcs(self, cr, uid, payline_ids, amount, type):
		amt = 0.0
		for l in payline_ids:
			amt += (l['amount'] +l['amount_fee'])
		
		return amount - (amt)
	
	def onchange_line_ids_dcs(self, cr, uid, ids, payline_ids, amount,amt_xtra, voucher_currency, type, context=None):
		context = context or {}
		if not payline_ids:
			return {}

		line_ids = self.resolve_2many_commands(cr, uid, 'x_payline_ids', payline_ids, ['amount','amount_fee','paymethod_id'], context)
		amt = 0.0
		 
		for line in line_ids:
			if line['amount']:
				amt += line['amount']
				if line.get("paymethod_id") and line['paymethod_id']:
					try:
						obj		= self.pool.get('dincelaccount.paymethod').browse(cr,uid,int(line['paymethod_id']),context=context)
						if obj.fee_pc:
							amt += line['amount']*obj.fee_pc*0.001
					except ValueError:
						pass
		return {'value': {'amount': (amt+amt_xtra),'x_amount_base':amt}}
	
	#@api.multi 
	def get_aba_file(self, cr, uid, ids, context=None):
		if context is None: context = {}
		link = "http://deverp.dincel.com.au/odoo/aba.php?id="+str(ids[0])
		
		f = urllib.urlopen(link)
		_data = f.read()
		if _data.find("Error") == -1:
			#_data = base64.b64encode(_data)
			cr.execute("update account_voucher set x_aba_status='2' where id=%s", (ids[0],)) 
			return {'type' : 'ir.actions.act_url',
				'url': '/web/binary/some_html?f=pay_'+str(ids[0])+'.aba&c='+_data,
				'target': 'self',}
		else:
			raise osv.except_osv(_('Error!'),_('' + str(_data)))
			return False
	 
	def generate_aba_download(self, cr, uid, ids, context=None):
		transactions=[]
		_aba = self.pool.get('dincelaccount.aba')
		#_abaline = self.pool.get('dincelaccount.aba.line')
		_err=None
		_obj = self.pool.get('account.voucher')
		_obank = self.pool.get('res.partner.bank')
		#_objac = self.pool.get('account.invoice')
		
		_obj=_obj.browse(cr, uid, ids[0], context=context)
		if _obj.journal_id:
			journal_id  = _obj.journal_id.id
			description = _obj.comment#''.join(e for e in string if e.isalnum())
			d_description= ''.join(e for e in description if e.isalnum())
			_id = _obank.search(cr, uid, [('journal_id', '=', journal_id)])
			if _id:
				_id=_id[0]
			else:
				_id=None
				_err = True
				raise osv.except_osv(_('Error!'),_('Partner bank not setup.'))
				return False
			if _id:
				_bank=_obank.browse(cr, uid, _id, context=context)
				d_bsb=_bank.x_bank_bsb
				d_accountNumber=_bank.acc_number
				d_bankName=_bank.bank_bic
				d_remitter=_bank.owner_name
				d_userName=_bank.owner_name
				d_directEntryUserId=_bank.x_bank_userid
				
			
			'''bsb="123-564"
			accountNumber="112233449"
			bankName="CBA"
			userName="DINCEL const"
			remitter="DINCEL"
			directEntryUserId="123456"
			description="DINCEL BDFD"
			'''
			
			for line in _obj.x_payline_ids:
				#invoice_id =line.invoice_id.id
				#partner_id = line.invoice_id.partner_id.id
				#partner_id = line.invoice_id.partner_id.id
				#_logger.error("x_payline_idsx_payline_ids["+str(invoice_id)+"]["+str(line.invoice_id.reference)+"]")
				amount		=int(round(line.amount,2)*100)	#to CENTS
				partner_id	= line.supplier_id.id
				reference	= line.ref_aba
				#_ac=_objac.browse(cr, uid, invoice_id, context=context)
				#if line.invoice_id.reference:
				#	reference=line.invoice_id.reference
				#else:
				#	reference=None
				#if not reference:# or reference=="":
				#	reference=line.invoice_id.number
					
				_id1 = _obank.search(cr, uid, [('partner_id', '=', partner_id)])
				if _id1:
					_id1=_id1[0]
					_bank=_obank.browse(cr, uid, _id1, context=context)
				else:
					_id1=None
					_err = True
					raise osv.except_osv(_('Error!'),_('Partner bank not setup.'))
					return False
				if _id1:
					
					if not _bank.x_bank_bsb:
						_id1=None
						_err = True
						raise osv.except_osv(_('Error!'),_('Partner bank BSB not setup.'))
						return False
					else:
					
						bsb=_bank.x_bank_bsb
						accountNumber=_bank.acc_number
						bankName=_bank.bank_bic
						remitter=''
						userName=_bank.owner_name
						#directEntryUserId=_bank.x_bank_userid
						indicator=""
						taxWithholding=""
						transactionCode=_aba.EXTERNALLY_INITIATED_CREDIT
						
						'''accountName="CBA"
						bsb="111-444"
						amount="12500"
						indicator=""
						
						reference="RefText11"
						remitter="Shukra Rai"
						taxWithholding=""'''
						vals = {
								'accountName':userName,
								'accountNumber':accountNumber,
								'bsb':bsb,
								'amount':amount,
								'indicator':indicator,
								'transactionCode':transactionCode,
								'reference':reference,
								'remitter':remitter,
								'taxWithholding':taxWithholding,
								}
							
						transactions.append(vals)		
			#_logger.error("generate_aba_testgenerate_aba_test1["+str(transactions)+"]")
			if not _err:
				_aba._init(cr, uid, ids,d_bsb, d_accountNumber, d_bankName, d_userName, d_remitter, d_directEntryUserId, d_description, context)
				_str=_aba.generate_aba(cr, uid, ids,transactions, context)
				fname="pay_"+str(ids[0])+".aba"
				temp_path="/var/tmp/"+fname
				#if os.path.exists(temp_path):
				#	os.unlink(temp_path)
				f=open(temp_path,'w')
				f.write(_str)
				f.close();
				#_logger.error("generate_aba_testgenerate_aba_test2 ["+str(_str)+"]")
				return {'type' : 'ir.actions.act_url',
						'url': '/web/binary/some_html?f='+str(fname)+'&c=a',
						'target': 'self',}
		return False				
		
	def button_generate_aba(self, cr, uid, ids, context=None):
		'''if context is None: context = {}
		link = "http://deverp.dincel.com.au/odoo/aba.php?id="+str(ids[0])
		
		f = urllib.urlopen(link)
		_data = f.read()
		
		if _data.find("Error") == -1:
			_data = base64.b64encode(_data)
			cr.execute("update account_voucher set x_aba_datas=%s,x_aba_status='1' where id=%s", (psycopg2.Binary(_data),ids[0],)) 
		else:
			raise osv.except_osv(_('Error!'),_('' + str(_data)))
			return False
		'''	
		return True
		
	def button_validate_dcs(self, cr, uid, ids, context=None):
		_inv = self.pool.get('account.invoice')
		_obj = self.pool.get('account.voucher').browse(cr, uid, ids[0], context=context)
		if _obj.x_payline_ids: 
			for line in _obj.x_payline_ids:
				if line.amount == line.amount_balance and line.invoice_id:
					_inv.write(cr, uid, [line.invoice_id.id], {'state':'paid'})
		
		_name = self.pool.get('ir.sequence').get(cr, uid, 'sales.pay.number')	#custom sequence number
		self.write(cr, uid, ids[0], {'state':'posted',  'number':_name})	
		
		_objourn = self.pool.get('dincelaccount.journal')
		ret = _objourn.payment2journals(cr, uid, ids, ids[0], context=context)
		#if ret and ret > 0:
		#	self.write(cr, uid, [ids[0]], {'state': 'posted'})
		return True
	
	def supplier_payment_validate_dcs(self, cr, uid, ids, context=None):
		#_inv = self.pool.get('account.invoice')
		#_obj = self.pool.get('account.voucher').browse(cr, uid, ids[0], context=context)
		#if _obj.x_payline_ids: 
		#	for line in _obj.x_payline_ids:
		#		if line.amount == line.amount_balance and line.invoice_id:
		#			_inv.write(cr, uid, [line.invoice_id.id], {'state':'paid'})
		_name = self.pool.get('ir.sequence').get(cr, uid, 'purchase.pay.number')	#custom sequence number
		self.write(cr, uid, ids[0], {'state':'posted',  'number':_name})	
		
		_objourn = self.pool.get('dincelaccount.journal')
		ret = _objourn.supplierpayment2journals(cr, uid, ids, ids[0], context=context)
		#if ret and ret > 0:
		#	self.write(cr, uid, [ids[0]], {'state': 'posted'})
		return True
		
	def onchange_partner_id_new(self, cr, uid, ids, partner_id, journal_id, amount, currency_id, ttype, date, context=None):
		if not journal_id:
			return {}
		if context is None:
			context = {}
		new_paylines = []	
		
		_inv = self.pool.get('account.invoice')
		#out_invoice= sales invoices
		#state=open
		_ids = _inv.search(cr, uid, [('partner_id', '=', partner_id),('state','=','open'),('type','=','out_invoice')])
		#_logger.error("onchange_partner_id_new111["+str(_ids)+"]["+str(partner_id)+"]")
		for inv in _inv.browse(cr, uid, _ids, context=context):
			amount_bal=inv.amount_total
			try:
				cr.execute("select sum(amount) as tot from dincelaccount_voucher_payline where invoice_id=" + str(inv.id))
				rows = cr.fetchall()
				if len(rows) > 0 and rows[0][0]:
					amount_bal = amount_bal-float(rows[0][0])
			except ValueError:
				pass
			#else:	
			#	paid_bal=0.0
			vals = {
				'invoice_id':inv.id,
				'amount_original':inv.amount_total,
				'date':inv.date_invoice,
				'amount_balance':amount_bal,
				}
			if(amount>inv.amount_total):
				vals['amount']=inv.amount_total
			else:
				vals['amount']=amount
			if inv.internal_number:	
				vals['invoice_number']=inv.internal_number
			if inv.date_due:	
				vals['date_due']=inv.date_due	
			new_paylines.append(vals)
		
		return {'value': {'x_payline_ids': new_paylines}}
	
	def button_print_payment(self, cr, uid, ids, context=None):
		transactions=[]
		if context is None:
			context = {}
		datas = {'ids': context.get('active_ids', [])}
	 
		datas['form']  = self.read(cr, uid, ids, context=context)[0]

		return self.pool['report'].get_action(cr, uid, [], 'account.report_supplier_payment', data=datas, context=context)			

	def onchange_amount_xtra(self, cr, uid, ids,x_amount_base, x_amount_xtra,x_payline_ids, context=None):
		amount_total=x_amount_base+x_amount_xtra
		return {'value': {'amount': amount_total}}
	def write(self, cr, uid, ids, vals, context=None):
		amt=0.0
		new_id=None
		res = super(dincelaccount_act_voucher, self).write(cr, uid, ids, vals, context=context)
		for record in self.browse(cr, uid, ids):
			new_id=record.id
			amt += record.x_amount_xtra
			for line in record.x_payline_ids:
				amt += line.amount
				if line.amount_fee:
					amt += line.amount_fee
		if new_id and record.x_payline_ids and amt>0: #TODO whay is this value here
			#this is for recording the card fee etc, for customer payments....TODO check if purchase receipts issue
			sql ="update account_voucher set amount=%s where id=%s" %(amt, new_id)
			#_logger.error("onchange_amount_xtraonchange_amount_xtrawrite["+str(new_id)+"]")
			cr.execute(sql)
		
		return True
		
class dincelaccount_voucher_payline(osv.Model):
	_name = "dincelaccount.voucher.payline"
	_columns = {
		'account_id': fields.many2one('account.account','Account'),
		'amount': fields.float('Amount'),
		'amount_fee': fields.float('Card Fee'),
		'amount_balance': fields.float('Amount Balance'),
		'type': fields.selection([
				('sale','Sale'),
				('purchase','Purchase'),
				('payment','Payment'),
				('pay_voucher','Pay Voucher'),
				('pay_invoice','Pay Invoice'),
				('receipt','Receipt'),
				],'Default Type'),
        'name':fields.char('Memo'),
		'ref_aba':fields.char('Aba Reference'),
        'date':fields.date('Invoice Date'),
		'date_due':fields.date('Due Date'),
		'reconcile': fields.boolean('Full Reconcile'),
		'paymethod_id':fields.many2one('dincelaccount.paymethod', 'Pay Method'),
		'voucher_id':fields.many2one('account.voucher', 'Voucher'),
		'invoice_id':fields.many2one('account.invoice', 'Invoice'),
		'pay_voucher_id':fields.many2one('account.voucher', 'Voucher Paid'),
		'supplier_id':fields.many2one('res.partner', 'Supplier'),
		'amount_original': fields.related('invoice_id', 'amount_total', type='float', string='Invoice Value',store=False),
		'invoice_number': fields.related('invoice_id', 'internal_number', type='text', string='Number',store=False),
		'reference': fields.related('invoice_id', 'reference', type='text', string='Payment Reference',store=False),
		'partner_id':fields.related('voucher_id', 'partner_id', type='many2one', relation='res.partner', string='Partner Voucher'),
		'partner_invoice':fields.related('invoice_id', 'partner_id', type='many2one', relation='res.partner', string='Partner Invoice'),
	}
	
	def _get_card_fee(self, cr, uid, ids, paymethod_id,amount, context=None):
		amt_fee=0.0
		if paymethod_id:
			obj		= self.pool.get('dincelaccount.paymethod').browse(cr,uid,paymethod_id,context=context)
			if obj.fee_pc:
				amt_fee = amount*obj.fee_pc*0.001
		return amt_fee
		
	def onchange_paymethod(self, cr, uid, ids, paymethod_id,amount, context=None):
		#vals = {}
		amt_fee = self._get_card_fee(cr, uid, ids,paymethod_id, amount, context)
		vals = {'amount_fee': amt_fee}
		return {'value': vals}	
		
	def onchange_reconcile(self, cr, uid, ids, reconcile, amount, amount_unreconciled, paymethod_id, context=None):
		amount=0.0
		#vals = {'amount': 0.0}
		if reconcile:
			amount=amount_unreconciled
		amt_fee = self._get_card_fee(cr, uid, ids,paymethod_id, amount, context)	
		vals = { 'amount': amount,'amount_fee': amt_fee}
		return {'value': vals}
		
	def onchange_amount(self, cr, uid, ids, amount, amount_unreconciled, paymethod_id, context=None):
		vals = {}
		amt_fee=0.0
		if amount:
			vals['reconcile'] = (amount == amount_unreconciled)
			if amount_unreconciled < amount:
				amount = amount_unreconciled
			vals['amount'] = amount#vals = { 'amount': amount}
			amt_fee = self._get_card_fee(cr, uid, ids,paymethod_id, amount, context)	
		vals['amount_fee'] = amt_fee	
		return {'value': vals}	
		
		
class dincelaccount_voucher_payment(osv.osv):
    _name = "dincelaccount.voucher.payment"
    #_description = "Sales Receipt Statistics"
    _auto = False
    #_rec_name = 'date'
    _columns = {
        'invoice_id': fields.many2one('account.invoice', 'Invoice', readonly=True),
        'amt_paid': fields.float('Total Without Tax', readonly=True),
    }
    #_order = 'date desc'
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'dincelaccount_voucher_payment')
        cr.execute("""
            create or replace view dincelaccount_voucher_payment as (
                select min(a.id) as id,
                    p.invoice_id as invoice_id,
					sum(p.amount) as amt_paid 
					from dincelaccount_voucher_payline p,account_invoice a 
					where a.id=p.invoice_id group by p.invoice_id
            )
        """)

		
class dincelaccount_paymethod(osv.Model):
	_name = "dincelaccount.paymethod"
	_columns = {
		'name':fields.char('Name'),
        'active':fields.boolean('Active'),
		'fee_pc':fields.float('Surchage Fee %'),
		'code': fields.char('Code')
	}		