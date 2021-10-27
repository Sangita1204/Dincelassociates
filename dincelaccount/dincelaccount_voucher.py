from openerp.osv import osv, fields#, api
from datetime import date
from openerp import models, api
#from openerp.addons.base_status.base_state import base_state
import time 
import datetime
import csv
import logging
import urllib2
import simplejson
import urllib
import base64
import psycopg2
import os
import openerp.addons.decimal_precision as dp
import subprocess
from subprocess import Popen, PIPE, STDOUT

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
		amt_total=0.0#_obj.tax_amount	
		for line in _obj.line_dr_ids:
			amt_total+=line.amount
		if amt_total != 	_obj.amount:
			raise osv.except_osv(_('Error!'),_('Invalid amount in total found!'))
			return False
		_name = self.pool.get('ir.sequence').get(cr, uid, 'purchase.nonstock')	#custom sequence number	
		#_logger.error("validate_po_nostock_dcsvalidate_po_nostock_dcs["+str(ids)+"]["+str(_name)+"]")
		_obj1.write(cr, uid, _obj.id, {'state':'posted','number':_name,'name':_name}, context=context)	
		_obj_j = self.pool.get('dincelaccount.journal')
		ret  = _obj_j.purchase_nostock2journals(cr, uid, ids, _obj, context=context)
		#if ret:
		#	_obj1.write(cr, uid, _obj.id, {'state':'posted'}, context=context)
		return True
	
	def _edit_master(self, cr, uid, ids, values, arg, context):
		x={}
		_edit=False
		for record in self.browse(cr, uid, ids):
			cr.execute("select res_id from ir_model_data where name='deposit_ex_editor' and model='res.groups'") #+ str(record.id))
			#cr.execute(sql)
			rows = cr.fetchone()
			if rows == None or len(rows)==0:
				_edit=False
			else:
				if rows[0]:#!=None:
					sql ="select 1 from  res_groups_users_rel where gid='%s' and uid='%s'" % (str(rows[0]), str(uid))
					cr.execute(sql)
					rows1 = cr.fetchone()
					if rows1 and len(rows1)>0:
						_edit=True
				#if rows == None or len(rows)==0:
			x[record.id]=_edit 
		return x
	_columns = {
		'x_project_id': fields.many2one('res.partner','Project / Site'),
		'x_payline_ids': fields.one2many('dincelaccount.voucher.payline', 'voucher_id', 'Voucher Lines'),
		'x_refundline_ids': fields.one2many('dincelaccount.voucher.refundline', 'voucher_id', 'Refund Lines'),
		'x_amount_xtra': fields.float('Difference Amount'), #extra fee for credit cards, etc for payment.
		'x_amount_base': fields.float('Base Amount'), #less extra fee for credit cards, etc
		'x_paymethod_id':fields.many2one('dincelaccount.paymethod', 'Pay Method'),
		#'x_writeoff_amount': fields.function(_get_writeoff_amount_dcs, string='Difference Amount', type='float', readonly=True, help="Computed as the difference between the amount stated in the voucher and the sum of allocation on the voucher lines."),
		'x_aba_datas': fields.binary('ABA Data'),
		'x_aba_status':fields.char('Aba Status'),
		'x_journal_id':fields.many2one('account.journal', 'Pay Method Journal'),
        'x_account_id':fields.many2one('account.account', 'Pay Account'),
		'x_cr_note':fields.boolean('Credit Note Offset'),
		'x_aba_downloaded':fields.boolean('Aba Downloaded'),
		'x_paystate':fields.selection(
            [('draft','Draft'),
             ('cancel','Cancelled'),
			 ('reverse','Reversed'),
             ('paid','Paid')
            ], 'Status'),
		'x_edit_master': fields.function(_edit_master, method=True, string='Edit master',type='boolean'),	
	}
	_defaults={
		'x_aba_status':'0',
		'x_paystate':'draft',
		'x_cr_note':False,
		'x_aba_downloaded':False,
	}
	
	def button_preview_receipt(self, cr, uid, ids, context=None):
		assert len(ids) == 1, 'This option should only be used for a single id at a time.'
	
		url=self.pool.get('dincelaccount.config.settings').report_preview_url(cr, uid, ids,"receipt",ids[0],context=context)		
		if url:
			ctx = dict(context)
			return {
					  'name'     : 'Go to website',
					  'res_model': 'ir.actions.act_url',
					  'type'     : 'ir.actions.act_url',
					  'view_type': 'form',
					  'view_mode': 'form',
					  'target'   : 'current',
					  'url'      : url,
					  'context': ctx
				   }
				   
	@api.multi 
	def button_pdf_receipt(self):
		return self.receipt_pdf_byid(self.id)			   
	#def button_pdf_receipt(self, cr, uid, ids, context=None):
	
	@api.multi 
	def receipt_pdf_byid(self, _id):
		o =self.env['account.voucher'].browse(_id)
		
		context = self._context.copy() 
		
		url=self.env['dincelaccount.config.settings'].report_preview_url("receipt",_id)		
		if url:#rows and len(rows) > 0:
			url=url.replace("erp.dincel.com.au/", "localhost/")
			if o.number:
				fname="receipt_"+str(o.number)+".pdf"
			else:
				fname="receipt_"+str(o.id)+"_draft.pdf"
			#fname="receipt"+str(o.id)+".pdf"
			save_path="/var/tmp/odoo/receipt"
			
			process=subprocess.Popen(["wkhtmltopdf", 
						'--margin-top','1', 
						'--margin-left','1', 
						'--margin-right','1', 
						'--margin-bottom','1', url, save_path+"/"+fname],stdin=PIPE,stdout=PIPE)
			
			out, err = process.communicate()
			if process.returncode not in [0, 1]:
				raise osv.except_osv(_('Report (PDF)'),
									_('Wkhtmltopdf failed (error code: %s). '
									'Message: %s') % (str(process.returncode), err))
			
			return {
					'name': 'Receipt',
					'res_model': 'ir.actions.act_url',
					'type' : 'ir.actions.act_url',
					'url': '/web/binary/download_file?model=sale.order&field=datas&id=%s&path=%s&filename=%s' % (str(o.id),save_path,fname),
					'context': context}
					
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
	
	def onchange_line_ids_dcs(self, cr, uid, ids, payline_ids, refund_ids, amount, amt_xtra, voucher_currency, type, context=None):
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
		_idid=ids[0] #x_aba_downloaded
		_obj=_obj.browse(cr, uid, _idid, context=context)
		if _obj.journal_id:
			journal_id  = _obj.journal_id.id
			description = _obj.comment#''.join(e for e in string if e.isalnum())
			description = description[:12]
			d_description= 'PAYMENT DATA'#''.join(e for e in description if e.isalnum())
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
				#_logger.error("generate_aba_testgenerate_alineamountline.amount ["+str(line.amount)+"]")
				amount		=int(round(line.amount,2)*100)	#to CENTS
				partner_id	= line.supplier_id.id
				reference	= description#line.ref_aba
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
				_aba.payDate=_obj.date
				_str=_aba.generate_aba(cr, uid, ids,transactions, context)
				fname="pay_"+str(ids[0])+".aba"
				#temp_path="/var/tmp/"+fname
				save_path="/var/tmp/odoo/aba/"
				temp_path=save_path+fname
				#if os.path.exists(temp_path):
				#	os.unlink(temp_path)
				f=open(temp_path,'w')
				f.write(_str)
				f.close()
				#_logger.error("generate_aba_testgenerate_aba_test2 ["+str(_str)+"]")
				#return {'type' : 'ir.actions.act_url',
				#		'url': '/web/binary/some_html?f='+str(fname)+'&c=a',
				#		'target': 'self',}
				_idid=ids[0] #x_aba_downloaded
				
				sql="update account_voucher set x_aba_downloaded='t' where id='%s' " % (_idid)
				cr.execute(sql)
				
				return {
					'name': 'Aba File',
					'res_model': 'ir.actions.act_url',
					'type' : 'ir.actions.act_url',
					'url': '/web/binary/download_file?model=dincelaccount.aba&field=datas&id=%s&path=%s&filename=%s' % (str(_id1),save_path,fname),
					'context': context}		
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
	
	def button_reverse_payment_dcs(self, cr, uid, ids, context=None):
		_inv = self.pool.get('account.invoice')
		_obj = self.pool.get('account.voucher').browse(cr, uid, ids[0], context=context)
		if _obj.x_payline_ids: 
			#make journal first and then zerorize the amount paid
			#Step 1/2
			#-------------------------------------------------------
			_objourn = self.pool.get('dincelaccount.journal')
			ret = _objourn.payment2journals_reverse(cr, uid, ids, ids[0], context=context)
			
			#Step 2/2
			#-------------------------------------------------------
			for line in _obj.x_payline_ids:
				if line.amount != 0.0:
					_inv.write(cr, uid, [line.invoice_id.id], {'state':'open'}) #no matter put back to open state
				self.pool.get('dincelaccount.voucher.payline').write(cr, uid, [line.id], {'state':'cancel','amount':0.0})
			self.write(cr, uid, ids[0], {'state':'cancel',  'x_paystate':'reverse'})		
			
			
			#now call to update dcs
			#--------------------------------------------------------
			url=self.pool.get('dincelaccount.config.settings').get_dcs_api_url(cr, uid, ids, "receiptreverse", ids[0], context=context)		
			if url:#rows and len(rows) > 0:
				#--- check flag of payment before update ---#
				#self.pool.get('sale.order').update_payment_order(cr, uid, ids, ids[0], context=context)		
				#--- check flag of payment before update ---#
				
				try:
					f = urllib2.urlopen(url)
					response = f.read()
					str1= simplejson.loads(response)
					_logger.error("invoice_receipt_validate.url["+str(url)+"]response["+str(response)+"]")
				except urllib2.HTTPError, e:
					_logger.error("invoice_receipt_validate.url["+str(url)+"]response["+str(e.code)+"]")#checksLogger.error('HTTPError = ' + str(e.code))
				except urllib2.URLError, e:
					_logger.error("invoice_receipt_validate.url["+str(url)+"]response["+str(e.reason)+"]")#checksLogger.error('URLError = ' + str(e.reason))
				except httplib.HTTPException, e:
					_logger.error("invoice_receipt_validate.url["+str(url)+"]httplib.HTTPException")#checksLogger.error('HTTPException')
				except Exception:
					_logger.error("invoice_receipt_validate.url["+str(url)+"] Exception")#
			
		return True
	
	def _update_so_dcs(self,cr, uid,ids,so_id,context=None):
		url=self.pool.get('dincelaccount.config.settings').get_dcs_api_url(cr, uid, ids, "getorder",so_id, context=context)		
		if url:#rows and len(rows) > 0:
			
			try:
				f = urllib2.urlopen(url)
				response = f.read()
				str1= simplejson.loads(response)
				#_logger.error("invoice_receipt_validate.url["+str(url)+"]response["+str(response)+"]")
			except Exception, e:
				_logger.error("_update_so_dcs.url["+str(url)+"] Exception[" +str(e)+"]")#
				
	def button_validate_offset(self, cr, uid, ids, context=None):
		_inv = self.pool.get('account.invoice')
		_obj = self.pool.get('account.voucher').browse(cr, uid, ids[0], context=context)
		if _obj.x_payline_ids: 
			for line in _obj.x_payline_ids:
				#_logger.error("button_validate_dcsbutton_validate_dcs paymethod_idpaymethod_id["+str(line.amount)+"]["+str(line.paymethod_id.id)+"]")
				if line.amount > 0 and line.paymethod_id.id==False:
					raise osv.except_osv(_('Error!'),_('Please select a payment method.'))
					return False
				else:
					if line.amount < 0.0:
						if line.amount == line.amount_balance and line.invoice_id: #credit not close...
							if line.paymethod_id.code=="CNO":
								_inv.write(cr, uid, [line.invoice_id.id], {'state':'offset'})
							else:
								_inv.write(cr, uid, [line.invoice_id.id], {'state':'close'})
						#elif line.amount == line.amount_balance and line.invoice_id: #credit not close...
						#	_inv.write(cr, uid, [line.invoice_id.id], {'state':'close'})	
					else:
						if line.paymethod_id.code=="CN":#cause CN cannot be paid...only closed/open
							if line.amount == line.amount_balance and line.invoice_id:
								_inv.write(cr, uid, [line.invoice_id.id], {'state':'close'})
						elif line.paymethod_id.code=="CNO":#cause CN cannot be paid...only closed/open
							if line.amount == line.amount_balance and line.invoice_id:
								_inv.write(cr, uid, [line.invoice_id.id], {'state':'offset'})		
						else:
							if line.amount == line.amount_balance and line.invoice_id:
								_inv.write(cr, uid, [line.invoice_id.id], {'state':'paid'})
					 
		
			_name = self.pool.get('ir.sequence').get(cr, uid, 'purchase.pay.number')	#custom sequence number
			self.write(cr, uid, ids[0], {'state':'posted',  'number':_name})	
				
			#_objourn = self.pool.get('dincelaccount.journal')
			#ret = _objourn.payment2journals(cr, uid, ids, ids[0], context=context)
			
		
		return True
	
	
	def button_validate_dcs(self, cr, uid, ids, context=None):
		_inv = self.pool.get('account.invoice')
		_obj = self.pool.get('account.voucher').browse(cr, uid, ids[0], context=context)
		if _obj.x_payline_ids: 
			for line in _obj.x_payline_ids:
				#_logger.error("button_validate_dcsbutton_validate_dcs paymethod_idpaymethod_id["+str(line.amount)+"]["+str(line.paymethod_id.id)+"]")
				if line.amount > 0 and line.paymethod_id.id==False:
					raise osv.except_osv(_('Error!'),_('Please select a payment method.'))
					return False
				else:
					if line.amount < 0.0:
						if line.amount == line.amount_balance and line.invoice_id: #credit not close...
							if line.paymethod_id.code=="CNO":
								_inv.write(cr, uid, [line.invoice_id.id], {'state':'offset'})
							else:
								_inv.write(cr, uid, [line.invoice_id.id], {'state':'close'})
						#elif line.amount == line.amount_balance and line.invoice_id: #credit not close...
						#	_inv.write(cr, uid, [line.invoice_id.id], {'state':'close'})	
					else:
						if line.paymethod_id.code=="CN":#cause CN cannot be paid...only closed/open
							if line.amount == line.amount_balance and line.invoice_id:
								_inv.write(cr, uid, [line.invoice_id.id], {'state':'close'})
						elif line.paymethod_id.code=="CNO":#cause CN cannot be paid...only closed/open
							if line.amount == line.amount_balance and line.invoice_id:
								_inv.write(cr, uid, [line.invoice_id.id], {'state':'offset'})		
						else:
							if line.amount == line.amount_balance and line.invoice_id:
								_inv.write(cr, uid, [line.invoice_id.id], {'state':'paid'})
					if line.invoice_id.x_sale_order_id: #check for full/partial paid status
						so_id=line.invoice_id.x_sale_order_id.id
						self._update_so_dcs(cr, uid,ids,so_id,context)
						self.pool.get('sale.order').update_payment_order(cr, uid, ids, so_id, context=context)		
		
		_name = self.pool.get('ir.sequence').get(cr, uid, 'sales.pay.number')	#custom sequence number
		self.write(cr, uid, ids[0], {'state':'posted',  'number':_name})	
		#self.pool.get('sale.order').update_payment_order(cr, uid, ids, ids[0], context=context)		
		_objourn = self.pool.get('dincelaccount.journal')
		ret = _objourn.payment2journals(cr, uid, ids, ids[0], context=context)
		
		#now call to update dcs
		url=self.pool.get('dincelaccount.config.settings').get_dcs_api_url(cr, uid, ids, "receiptvalidate", ids[0], context=context)		
		if url:#rows and len(rows) > 0:
			#--- check flag of payment before update ---#
			#self.pool.get('sale.order').update_payment_order(cr, uid, ids, ids[0], context=context)		
			#--- check flag of payment before update ---#
			#http://220.233.149.98/dcsapi/index.php
			#url="http:///dcsapi/index.php?id="+str(ids[0])
			try:
				f = urllib2.urlopen(url)
				response = f.read()
				str1= simplejson.loads(response)
				#_logger.error("invoice_receipt_validate.url["+str(url)+"]response["+str(response)+"]")
			except urllib2.HTTPError, e:
				_logger.error("invoice_receipt_validate.url["+str(url)+"]response["+str(e.code)+"]")#checksLogger.error('HTTPError = ' + str(e.code))
			except urllib2.URLError, e:
				_logger.error("invoice_receipt_validate.url["+str(url)+"]response["+str(e.reason)+"]")#checksLogger.error('URLError = ' + str(e.reason))
			except httplib.HTTPException, e:
				_logger.error("invoice_receipt_validate.url["+str(url)+"]httplib.HTTPException")#checksLogger.error('HTTPException')
			except Exception:
				_logger.error("invoice_receipt_validate.url["+str(url)+"] Exception")#
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
		
	def supplier_payment_reverse(self, cr, uid, ids, context=None):
		ctx = dict(context)
		compose_form_id		= self.pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'dincelaccount.view_bill_payment_reverse')], limit=1) 

		o = self.browse(cr, uid, ids)[0]
		
		ctx.update({
				'default_voucher_id': ids[0],
				'default_amount': o.amount,
				})
				
		return {
				'name': _('Form'),
				'type': 'ir.actions.act_window',
				'view_type': 'form',
				'view_mode': 'form',
				'res_model': 'dincelaccount.bill.reverse',
				'views': [(compose_form_id, 'form')],
				'view_id': compose_form_id,
				'target': 'new',#current',#'target': 'new',
				'context': ctx,
			}
		
	def onchange_partner_supplier(self, cr, uid, ids, partner_id, journal_id, amount, currency_id, ttype, cr_note, context=None):
		if not journal_id:
			return {}
		if context is None:
			context = {}
		new_paylines = []	
		refund_lines = []	
		
		_inv = self.pool.get('account.invoice')
		#out_invoice= sales invoices
		#state=open
		_ids = _inv.search(cr, uid, [('partner_id', '=', partner_id),('state','in',['open','cancel']),('type','=','in_invoice')],order="id asc")
		#_logger.error("onchange_partner_id_new111["+str(_ids)+"]["+str(partner_id)+"]")
		for inv in _inv.browse(cr, uid, _ids, context=context):
			amount_bal=inv.amount_untaxed+inv.amount_tax
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
				'invoice_type':inv.x_inv_type,
				'inv_state':inv.state,
				'amount_original':inv.amount_untaxed+inv.amount_tax,
				'date':inv.date_invoice,
				'amount_balance':amount_bal,
				}
			if(amount>(inv.amount_untaxed+inv.amount_tax)):
				vals['amount']=inv.amount_untaxed+inv.amount_tax
			else:
				vals['amount']=amount
			if inv.internal_number:	
				vals['invoice_number']=inv.internal_number
			if inv.date_due:	
				vals['date_due']=inv.date_due	
			new_paylines.append(vals)
		
		#add debit notes for payments
		_ids = _inv.search(cr, uid, [('partner_id', '=', partner_id),('state','=','open'),('type','=','in_refund')])
		#_logger.error("onchange_partner_id_new222["+str(_ids)+"]["+str(partner_id)+"]")
		for inv in _inv.browse(cr, uid, _ids, context=context):
			amount_bal=inv.amount_untaxed+inv.amount_tax#inv.amount_total
			try:
				cr.execute("select sum(amount) as tot from dincelaccount_voucher_payline where state<>'cancel' and invoice_id=" + str(inv.id))
				rows = cr.fetchall()
				if len(rows) > 0 and rows[0][0]:
					amount_bal = amount_bal-float(rows[0][0])
			except ValueError:
				pass
			#else:	
			#	paid_bal=0.0
			vals = {
				'invoice_id':inv.id,
				'invoice_type':inv.x_inv_type,
				'inv_state':inv.state,
				'amount_original':inv.amount_untaxed+inv.amount_tax,#inv.amount_total,
				'date':inv.date_invoice,
				'amount_balance':amount_bal,
				'amount':0.0,
				}
			#if(amount>(inv.amount_untaxed+inv.amount_tax)):
			#	vals['amount']=inv.amount_untaxed+inv.amount_tax#inv.amount_total
			#else:
			#	vals['amount']=amount
			if inv.internal_number:	
				vals['invoice_number']=inv.internal_number
			if inv.date_due:	
				vals['date_due']=inv.date_due	
			new_paylines.append(vals)
		#if cr_note and cr_note==True:
		#	domain  = {'journal_id':[('type','=','general')]}
		#else:
		#	domain  = {'journal_id':[('type','in',['bank', 'cash'])]}
		domain={}
		return {'value': {'x_payline_ids': new_paylines},'domain':domain}
		
	def onchange_partner_id_new(self, cr, uid, ids, partner_id, journal_id, amount, currency_id, ttype, cr_note, context=None):
		if not journal_id:
			return {}
		if context is None:
			context = {}
		new_paylines = []	
		refund_lines = []	
		domain  = {}
		_inv = self.pool.get('account.invoice')
		#out_invoice= sales invoices
		#state=open
		try:
			_ids = _inv.search(cr, uid, [('partner_id', '=', partner_id),('state','in',['open','cancel']),('type','=','out_invoice')],order="id asc")
			
			for inv in _inv.browse(cr, uid, _ids, context=context):
				amount_bal=inv.amount_untaxed+inv.amount_tax
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
					'invoice_type':inv.x_inv_type,
					'inv_state':inv.state,
					'amount_original':inv.amount_untaxed+inv.amount_tax,
					'date':inv.date_invoice,
					'amount_balance':amount_bal,
					}
				if(amount>(inv.amount_untaxed+inv.amount_tax)):
					vals['amount']=inv.amount_untaxed+inv.amount_tax
				else:
					vals['amount']=amount
				if inv.internal_number:	
					vals['invoice_number']=inv.internal_number
				if inv.date_due:	
					vals['date_due']=inv.date_due	
				new_paylines.append(vals)
			
			#add credit notes for payments
			_ids = _inv.search(cr, uid, [('partner_id', '=', partner_id),('state','=','open'),('type','=','out_refund')])
			#_logger.error("onchange_partner_id_new111["+str(_ids)+"]["+str(partner_id)+"]")
			for inv in _inv.browse(cr, uid, _ids, context=context):
				amount_bal=inv.amount_untaxed+inv.amount_tax#inv.amount_total
				try:
					cr.execute("select sum(amount) as tot from dincelaccount_voucher_payline where state<>'cancel' and invoice_id=" + str(inv.id))
					rows = cr.fetchall()
					if len(rows) > 0 and rows[0][0]:
						amount_bal = amount_bal-float(rows[0][0])
				except ValueError:
					pass
				#else:	
				#	paid_bal=0.0
				vals = {
					'invoice_id':inv.id,
					'invoice_type':inv.x_inv_type,
					'inv_state':inv.state,
					'amount_original':inv.amount_untaxed+inv.amount_tax,#inv.amount_total,
					'date':inv.date_invoice,
					'amount_balance':amount_bal,
					'amount':0.0,
					}
				#if(amount>(inv.amount_untaxed+inv.amount_tax)):
				#	vals['amount']=inv.amount_untaxed+inv.amount_tax#inv.amount_total
				#else:
				#	vals['amount']=amount
				if inv.internal_number:	
					vals['invoice_number']=inv.internal_number
				if inv.date_due:	
					vals['date_due']=inv.date_due	
				new_paylines.append(vals)
			if cr_note and cr_note==True:
				domain  = {'journal_id':[('type','=','general')]}
			else:
				domain  = {}#'journal_id':[('type','in',['bank', 'cash'])]}
		except ValueError:
				pass	
		return {'value': {'x_payline_ids': new_paylines},'domain':domain}
	
	def button_print_payment(self, cr, uid, ids, context=None):
		transactions=[]
		if context is None:
			context = {}
		datas = {'ids': context.get('active_ids', [])}
	 
		datas['form']  = self.read(cr, uid, ids, context=context)[0]

		return self.pool['report'].get_action(cr, uid, [], 'account.report_supplier_payment', data=datas, context=context)		
		
	def button_print_payment_pdf(self, cr, uid, ids, context=None):
		transactions=[]
		if context is None:
			context = {}
		datas = {'ids': context.get('active_ids', [])}
	 
		datas['form']  = self.read(cr, uid, ids, context=context)[0]

		return self.pool['report'].get_action(cr, uid, [], 'account.report_supplier_payment_pdf1', data=datas, context=context)				
	
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
		
	'''def unlink(self, cr, uid, ids, context=None, check=True):
		context = dict(context or {})
		if context is None:
			context = {}
		 
		for record in self.browse(cr, uid, ids):
			prod_status= record.prod_status
			for line in record.x_payline_ids:
				
		result = super(dincelaccount_act_voucher, self).unlink(cr, uid, ids, context)
		return result'''
		
class dincelaccount_voucher_refundline(osv.Model):
	_name = "dincelaccount.voucher.refundline"
	_columns = {
		'voucher_id':fields.many2one('account.voucher', 'Voucher',ondelete='cascade',),
		'account_id': fields.many2one('account.account','Account'),
		'amount': fields.float('Amount'),
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
        'date':fields.date('Invoice Date'),
		'reconcile': fields.boolean('Full Reconcile'),
		'invoice_id':fields.many2one('account.invoice', 'Invoice'),
		'amount_original': fields.related('invoice_id', 'amount_total', type='float', string='Invoice Value',store=False),
		'invoice_number': fields.related('invoice_id', 'internal_number', type='text', string='Number',store=False),
		'reference': fields.related('invoice_id', 'reference', type='text', string='Payment Reference',store=False),
		'partner_id':fields.related('voucher_id', 'partner_id', type='many2one', relation='res.partner', string='Partner Voucher'),
	}
	def onchange_reconcile(self, cr, uid, ids, reconcile, amount, amount_unreconciled,  context=None):
		amount=0.0
		#vals = {'amount': 0.0}
		if reconcile:
			amount=amount_unreconciled
		#amt_fee = self._get_card_fee(cr, uid, ids,paymethod_id, amount, context)	
		vals = { 'amount': amount}
		return {'value': vals}
		
	def onchange_amount(self, cr, uid, ids, amount, amount_unreconciled,  context=None):
		#vals = {'amount':0}
		vals = {}
		amt_fee=0.0
		if amount:
			amount=float(amount)
			if amount>0.0:
				vals['reconcile'] = (amount == amount_unreconciled)
			
				if amount_unreconciled < amount:
					amount = amount_unreconciled
					
				vals['amount'] = amount#vals = { 'amount': amount}
		
		
		return {'value': vals}	
#make sure to reflect if changes is made in x_inv_type in account.invoice
INV_TYPE_SELECTION =[
	('none', 'None'),
	('deposit', 'Deposit'),
	('balance', 'Balance'),
	('balance1', 'Balance1'),
	('full', 'FULL'),
	('refund', 'Refund'),
	('refundreturn', 'Refund Return'),
	]
	
class dincelaccount_voucher_payline(osv.Model):
	_name = "dincelaccount.voucher.payline"
	
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
		'account_id': fields.many2one('account.account','Account'),
		'amount': fields.float('Amount'),
		'amount_fee': fields.float('Card Fee'),
		'amount_balance': fields.float('Amount Balance'),
		'amount_subtotal': fields.function(_amount_subtotal, digits_compute=dp.get_precision('Account'), string='Subtotal'),
		'inv_state':fields.selection([
			('draft','Draft'),
			('proforma','Pro-forma'),
			('proforma2','Pro-forma'),
			('open','Open'),
			('paid','Paid'),
			('close','Closed'),
			('cancel','Cancelled'),
		], string='Status'),
		'state': fields.selection([
				('done','Done'),
				('cancel','Cancel'),
				],'State'),
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
		'voucher_id':fields.many2one('account.voucher', 'Voucher',ondelete='cascade',),
		'invoice_id':fields.many2one('account.invoice', 'Invoice'),
		'pay_voucher_id':fields.many2one('account.voucher', 'Voucher Paid'),
		'supplier_id':fields.many2one('res.partner', 'Supplier'),
		'supplier_inv_no':fields.related('invoice_id','supplier_invoice_number',type='char',string='Ref No',store=False),
		'amount_original': fields.related('invoice_id', 'amount_total', type='float', string='Invoice Value',store=False),
		'invoice_number': fields.related('invoice_id', 'internal_number', type='text', string='Number',store=False),
		'invoice_type': fields.related('invoice_id', 'x_inv_type', type='selection', selection=INV_TYPE_SELECTION, readonly=True, store=True, string='Type'),
		'reference': fields.related('invoice_id', 'reference', type='text', string='Payment Reference',store=False),
		'partner_id':fields.related('voucher_id', 'partner_id', type='many2one', relation='res.partner', string='Partner Voucher'),
		'date_paid': fields.related('voucher_id', 'date', type='date', string='Paid Date',store=False),
		'partner_invoice':fields.related('invoice_id', 'partner_id', type='many2one', relation='res.partner', string='Partner Invoice'),
	}
	_defaults = {
		'state':'done',
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
		vals = {'amount_fee': amt_fee,'amount_subtotal': amt_fee+amount}
		return {'value': vals}	
		
	def onchange_reconcile(self, cr, uid, ids, reconcile, amount, amount_unreconciled, paymethod_id, context=None):
		amount=0.0
		#vals = {'amount': 0.0}
		if reconcile:
			amount=amount_unreconciled
		amt_fee = self._get_card_fee(cr, uid, ids,paymethod_id, amount, context)	
		vals = { 'amount': amount,'amount_fee': amt_fee,'amount_subtotal': amt_fee+amount}
		return {'value': vals}
		
	def onchange_amount(self, cr, uid, ids, amount, amount_unreconciled, paymethod_id, context=None):
		vals = {'amount':0}
		amt_fee=0.0
		if amount:
			amount=float(amount)
			if amount>0.0:
				vals['reconcile'] = (amount == amount_unreconciled)
				if amount_unreconciled < amount:
					amount = amount_unreconciled
			vals['amount'] = amount#vals = { 'amount': amount}
			amt_fee = self._get_card_fee(cr, uid, ids,paymethod_id, amount, context)	
		vals['amount_fee'] = amt_fee	
		vals['amount_subtotal'] = amt_fee+vals['amount']
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

#class dincelaccount_journal(osv.Model):
#	_inherit = "account.journal"
#	_columns = {		
#		'x_paymethod_id':fields.many2one('dincelaccount.paymethod', 'Default Pay Method'),
#		'x_default':fields.boolean("Default in Sale/Purchase"),
#	#}
	
class dincelaccount_paymethod(osv.Model):
	_name = "dincelaccount.paymethod"
	_columns = {
		'name':fields.char('Name'),
        'active':fields.boolean('Active'),
		'fee_pc':fields.float('Surchage Fee %'),
		'fee_sale':fields.float('Card Fee (AR) %'),
		'fee_purchase':fields.float('Card Fee (AP) %'),
		'code': fields.char('Code'),
		'cn_offset':fields.boolean("CN Offset"),
		'purchase':fields.boolean('Purchase'),
		'sale':fields.boolean('Sale'),
		'account_dr_id':fields.many2one('account.account', 'Default Debit Account'),
		'account_cr_id':fields.many2one('account.account', 'Default Credit Account'),
	}	
	_defaults = {
		'cn_offset':False,
		'purchase':False,
		'sale':True,
	}	