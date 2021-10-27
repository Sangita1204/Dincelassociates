import time
from openerp.osv import fields, osv
from openerp.tools.translate import _
import logging
_logger = logging.getLogger(__name__)

class dincelaccount_download_aba(osv.osv_memory):
	_name = "dincelaccount.download.aba"
	_columns = {
		'date': fields.date('Date'),
		'pay_lines':fields.one2many('dincelaccount.download.aba.line', 'download_id', 'Pay lines'),
		'qty':fields.float("Qty test"),
		'comments':fields.char("Comments"),
		'journal_id':fields.many2one('account.journal','Journal'),
		
	}
	
	def download_aba_file(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		_aba = self.pool.get('dincelaccount.aba')
		#_abaline = self.pool.get('dincelaccount.aba.line')
		_err=None
		_obj = self.pool.get('account.voucher')
		_obank = self.pool.get('res.partner.bank')
		d_bsb=''
		d_accountNumber=''
		d_bankName=''
		d_remitter=''
		d_userName=''
		d_directEntryUserId=''
		voucher_ids=[]
		for record in self.browse(cr, uid, ids, context=context):	#record = self.browse(cr, uid, ids[0], context=context)
			#_logger.error("invoice_salesconfirm_record.order_idrecord.order_id[" + str(record.id)+"]")
			
			#_objac = self.pool.get('account.invoice')
			_idid=ids[0] #x_aba_downloaded
			#_obj=_obj.browse(cr, uid, _idid, context=context)
			#if record.journal_id:
			journal_id  = record.journal_id.id
			#description = _obj.comment#''.join(e for e in string if e.isalnum())
			#description = description[:12]
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
			#_logger.error("journal_idjournal_id.order_id[%s][%s]"%(journal_id,_id))		
			transactions=[]	 
				 
			for line in record.pay_lines:
				#if line.amount > 0.0:
				#	tot_amt += line.amount
				#_logger.error("invoice_salesconfirm_record.order_idrecord.order_id[" + str(record.id)+"]")
				
		
			
				#for line in _obj.x_payline_ids:
				#invoice_id =line.invoice_id.id
				#partner_id = line.invoice_id.partner_id.id
				#partner_id = line.invoice_id.partner_id.id
				#_logger.error("x_payline_idsx_payline_ids["+str(invoice_id)+"]["+str(line.invoice_id.reference)+"]")
				#amount		=int(round(line.amount_paid,2)*100)	#to CENTS ....some reasons...rounding not calculating correctly...6.64<=6.65
				amount		= int(round((line.amount_paid*100),0))	#to CENTS
				partner_id	= line.partner_id.id
				reference	= line.trans_desc#line.ref_aba
				#_logger.error("x_payline_idsx_payline_idsline.amount_paidline.amount_paid["+str(amount)+"]["+str(line.amount_paid)+"]")
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
						
						voucher_ids.append(line.voucher_id.id)
						
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
			#_logger.error("generate_aba_generate_aba_[%s][%s][%s][%s][%s][%s][%s]" % (d_bsb, d_accountNumber, d_bankName, d_userName, d_remitter, d_directEntryUserId, d_description))
			if not _err and _id and _id1:
				_aba._init(cr, uid, ids,d_bsb, d_accountNumber, d_bankName, d_userName, d_remitter, d_directEntryUserId, d_description, context)
				_aba.payDate=record.date
				_str=_aba.generate_aba(cr, uid, ids,transactions, context)
				fname="WBC.aba"
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
				#_idid=ids[0] #x_aba_downloaded
				for _vid in voucher_ids:
					sql="update account_voucher set x_aba_downloaded='t' where id='%s' " % (_vid)
					cr.execute(sql)
				return {
					'name': 'Aba File',
					'res_model': 'ir.actions.act_url',
					'type' : 'ir.actions.act_url',
					'url': '/web/binary/download_file?model=dincelaccount.aba&field=datas&id=%s&path=%s&filename=%s' % (str(_id1),save_path,fname),
					'context': context}		
		return False		
		
		return True
	def on_change_qty(self, cr, uid, ids, product_qty, pay_lines, context=None):
		
	 
		pay_lines =[]
		journal_id=None
		if context and context.get('active_ids'):
			_date=None
			_ids	= context.get('active_ids')
			for o in self.pool.get('account.voucher').browse(cr, uid, _ids, context=context):
				
				if o.state=="posted":# and o.type=="purchase":	#in_invoice=supplier invoice only
					amount_bal=o.amount
					if journal_id==None:
						journal_id=o.journal_id.id 
					if journal_id==o.journal_id.id:
						if _date==None:
							_date=o.date
						else:
							if _date!=o.date:
								raise osv.except_osv(_('Warning'), _('The payment date for selected items mismatch, or more than one dates selected.'))
						val={'voucher_id':o.id,'amount_paid':o.amount,'pay_ref':o.reference,'downloaded':o.x_aba_downloaded,'trans_desc':o.comment,'date_paid':o.date}
						if o.partner_id:
							val['partner_id']=o.partner_id.id 
							
						pay_lines.append(val)

		return {'value': {'pay_lines': pay_lines,'journal_id': journal_id,'date':_date}}
		
	def _get_init_qty(self, cr, uid, context=None):
		return 1
	_defaults = {
		'qty': _get_init_qty,
		#'date': lambda *a: time.strftime('%Y-%m-%d'),
		}
	
class dincelaccount_download_aba_line(osv.osv_memory):
	_name="dincelaccount.download.aba.line"
	_columns = {
		'download_id': fields.many2one('dincelaccount.download.aba', 'Sale Order'),
		'sequence': fields.integer('Sequence'),
		'trans_desc': fields.char('Trans Descr'),
		'partner_id':fields.many2one('res.partner', 'Partner'),
		'pay_ref':fields.char('Pay Ref'),
		'date_paid':fields.date('Paid Date'),
		'amount_paid':fields.float('Paid Amount'),
		'downloaded':fields.boolean('Downloaded'),
		'voucher_id':fields.many2one('account.voucher','Payment'),
	}	
	 	