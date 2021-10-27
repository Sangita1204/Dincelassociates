import re	
import time
import dateutil.parser
import openerp
from openerp import SUPERUSER_ID, api
from openerp import tools
from openerp.osv import fields, osv, expression
from openerp.tools.translate import _

import logging
_logger = logging.getLogger(__name__)

class dincelaccount_aba(osv.Model):
	_name = "dincelaccount.aba"
	
	DESCRIPTIVE_TYPE = '0'
	DETAIL_TYPE = '1'
	BATCH_TYPE = '7'
	
	EXTERNALLY_INITIATED_DEBIT = '13'
	EXTERNALLY_INITIATED_CREDIT = '50'
	AUSTRALIAN_GOVERNMENT_SECURITY_INTEREST = '51'
	FAMILY_ALLOWANCE = '52'
	PAYROLL_PAYMENT = '53'
	PENSION_PAYMENT = '54'
	ALLOTMENT = '55'
	DIVIDEND = '56'
	DEBENTURE_OR_NOTE_INTEREST = '57'
	
	payDate = ''
	#string - aba file string
	abaString	= ''
	
	#integer - running total of credits in file
	creditTotal = 0
	#integer - running total of debit in file

	debitTotal = 0

	#integer
	numberRecords = 0

	#string
	bsb=''

	#string
	accountNumber=''

	#string
	bankName=''

	#The name of the user supplying the aba file. Some banks must match
	# * account holder or be specified as "SURNAME Firstname".
	userName=''

	#Appears of recipient's statement as origin of transaction.
	remitter=''

	#string
	directEntryUserId=''

	#string
	description=''

	#Validates that the BSB is 6 digits with a dash in the middle: 123-456
	bsbRegex = '^[\d]{3}-[\d]{3}'

	def _init(self, cr, uid, ids, bsb, accountNumber, bankName, userName, remitter, directEntryUserId, description, context=None):
		self.abaString=''
		self.bsb = bsb
		self.accountNumber =accountNumber
		self.bankName =bankName
		self.userName =userName
		self.remitter =remitter
		self.directEntryUserId =directEntryUserId
		self.description =description
		self.debitTotal=0
		self.creditTotal=0
		self.payDate=''
	def generate_aba(self, cr, uid, ids, transactions, context=None):
		#try:
		ret = self.validateDescriptiveRecord()
		if ret =="":
			self.addDescriptiveRecord()
			for _trans in transactions:
				ret1 = self.validateDetailRecord(_trans)
				if ret == "":
					self.addDetailRecord(_trans)
					if (_trans['transactionCode'] == self.EXTERNALLY_INITIATED_DEBIT):
						self.debitTotal += int(_trans['amount'])
					else:
						self.creditTotal += int(_trans['amount'])
				else:
					raise osv.except_osv(_('Error!'),_('' + str(ret)))
					return False
			#print "OK"
		else:
			raise osv.except_osv(_('Error!'),_('' + str(ret)))
			
		self.numberRecords = len(transactions)
		#_logger.error("onchange_amount_abaStringabaStringabaString111["+str(self.abaString)+"]")
		self.addBatchControlRecord()	
		
		#except ValueError:
		#	pass
		
		

		return self.abaString
		
	def addBatchControlRecord(self):
		
		line = self.BATCH_TYPE

		# BSB
		line += '999-999'

		# Reserved - must be twelve blank spaces
		line += ' ' * 12#str_repeat(' ', 12)

		# Batch Net Total
		line += (str(abs(self.creditTotal - self.debitTotal))).rjust(10, '0')#str_pad(abs(self.creditTotal - self.debitTotal), 10, '0', STR_PAD_LEFT)

		# Batch Credits Total
		line += (str(self.creditTotal)).rjust(10, '0')#str_pad(self.creditTotal, 10, '0', STR_PAD_LEFT)

		# Batch Debits Total
		line += (str(self.debitTotal)).rjust(10, '0')#str_pad(self.debitTotal, 10, '0', STR_PAD_LEFT)

		# Reserved - must be 24 blank spaces
		line += ' ' * 24#str_repeat(' ', 24)

		# Number of records
		line += (str(self.numberRecords)).rjust(6, '0')#str_pad(self.numberRecords, 6, '0', STR_PAD_LEFT)

		# Reserved - must be 40 blank spaces
		line += ' ' * 40#str_repeat(' ', 40)

		self.addLine(line, False)
		#_logger.error("onchange_amount_abaStringabaStringabaString222["+str(self.abaString)+"]")

	#/**
	# * Create the descriptive record line of the file.
	# */
	def addDescriptiveRecord(self):#
		## Record Type
		line = self.DESCRIPTIVE_TYPE

		 
		line += ' '* 17

		# Sequence Number
		line += '01'

		# Bank Name 3digit
		line += self.bankName

		# Reserved - must be seven blank spaces
		line += ' ' * 7#str_repeat(' ', 7)

		# User Name
		line += self.userName.ljust(26)#str_pad(self.userName, 26, ' ', STR_PAD_RIGHT)

		# User ID 6 digit uid by APCA
		line += self.directEntryUserId

		# File Description
		line += self.description.ljust(12)#str_pad(self.description, 12, ' ', STR_PAD_RIGHT)

		# Processing Date
		dt=dateutil.parser.parse(str(self.payDate))
		line += dt.strftime("%d%m%y")#date('dmy')

		# Processing Time
		line += ' ' * 4#str_repeat(' ', 4)

		# Reserved - 36 blank spaces
		line += ' ' * 36#str_repeat(' ', 36)

		self.addLine(line)
		
	def addLine(self,line, crlf = True):
		_str="\r\n" if crlf else ''
		self.abaString += line+_str#if crlf else ''#(crlf ? "\r\n" : "")
	
	#
	# * Add a detail record for each transaction.
	# */
	def addDetailRecord(self,transaction):
		# Record Type
		line = self.DETAIL_TYPE

		# BSB
		line += transaction['bsb']

		# Account Number
		line += transaction['accountNumber'].rjust(9)#str_pad(transaction->getAccountNumber(), 9, ' ', STR_PAD_LEFT)

		# Indicator todo N/W/X/Y
		line += ' '#transaction->getIndicator() ?: ' '

		# Transaction Code
		line += transaction['transactionCode']#transaction->getTransactionCode()

		# Transaction Amount
		line += (str(transaction['amount'])).rjust(10,'0')#str_pad(transaction->getAmount(), 10, '0', STR_PAD_LEFT)

		# Account Name
		line += transaction['accountName'].ljust(32)#str_pad(transaction->getAccountName(), 32, ' ', STR_PAD_RIGHT)

		# Lodgement Reference
		line += transaction['reference'].ljust(18)#str_pad(transaction->getReference(), 18, ' ', STR_PAD_RIGHT)

		# Trace BSB - already validated
		line += self.bsb

		# Trace Account Number - already validated
		line += self.accountNumber.rjust(9)#str_pad(this->accountNumber, 9, ' ', STR_PAD_LEFT)

		# Remitter Name - already validated
		#remitter = self.remitter#transaction->getRemitter() ?: this->remitter
		if transaction['remitter']!="":
			_remit=transaction['remitter']
		else:
			_remit=self.remitter
			
		line += _remit.ljust(16)#str_pad(remitter, 16, ' ', STR_PAD_RIGHT)

		# Withholding amount
		line += transaction['taxWithholding'].rjust(8,'0')#str_pad(transaction->getTaxWithholding(), 8, '0', STR_PAD_LEFT)

		self.addLine(line)#this->addLine(line)
 
	
	# Validate the parts of the descriptive record.
	def validateDescriptiveRecord(self):
		#num_format = re.compile(self.bsbRegex)
		#isbsb = re.match(num_format,self.bsb)
		
		if (not re.findall(self.bsbRegex, self.bsb)):
			return ('Descriptive record bsb ['+str(self.bsb)+'] is invalid. Required format is 000-000.')
		
		if (not re.findall('^[\d]{0,9}', self.accountNumber)):
			return ('Descriptive record account number ['+str(self.accountNumber)+'] is invalid. Must be up to 9 digits only.')
		
		if (not re.findall('^[A-Z]{3}',self.bankName)):
			return ('Descriptive record bank name ['+str(self.bankName)+'] is invalid. Must be capital letter abbreviation of length 3.')
		
		if (not re.findall('^[A-Za-z\s+]{0,26}',self.userName)):
			return ('Descriptive record user name ['+str(self.userName)+'] is invalid. Must be letters only and up to 26 characters long.')

		if (not re.findall('^[\d]{6}',self.directEntryUserId)):
			return ('Descriptive record direct entiry user ID ['+str(self.directEntryUserId)+'] is invalid. Must be 6 digits long.')
		
		if (not re.findall('^[A-Za-z\s]{0,12}',self.description)):
			return ('Descriptive record description ['+str(self.description)+'] is invalid. Must be letters only and up to 12 characters long.')
		
		return ""
		
	def validateDetailRecord(self,transaction):
		#num_format = re.compile(self.bsbRegex)
		isbsb = re.match(re.compile(self.bsbRegex),transaction['bsb'])
		if (not isbsb):
			return ('Detail record bsb is invalid: '+str(transaction['bsb'])+'. Required format is 000-000.')

		if (not re.findall('^[\d]{0,9}', transaction['accountNumber'])):
			return ('Detail record account number is invalid. Must be up to 9 digits only.')

		#if (transaction.indicator and (not re.findall('^W|X|Y| ', transaction.indicator))) 
		#	return ('Detail record transaction indicator is invalid. Must be one of W, X, Y or null.')

		if (not re.findall('^[A-Za-z0-9\s+]{0,18}', transaction['reference'])):
			return ('Detail record reference is invalid: "'+str(transaction['reference'])+'". Must be letters only and up to 18 characters long.')

		if (transaction['remitter'] and (not re.findall('^[A-Za-z\s+]{0,16}', transaction['remitter']))):
			return ('Detail record remitter is invalid. Must be letters only and up to 16 characters long.')

		if (not self.validateTransactionCode(transaction['transactionCode'])):
			return ('Detail record transaction code invalid. ')
		
	def validateTransactionCode(self,transactionCode):
		return transactionCode in [
			self.EXTERNALLY_INITIATED_DEBIT,
			self.EXTERNALLY_INITIATED_CREDIT,
			self.AUSTRALIAN_GOVERNMENT_SECURITY_INTEREST,
			self.FAMILY_ALLOWANCE,
			self.PAYROLL_PAYMENT,
			self.PENSION_PAYMENT,
			self.ALLOTMENT,
			self.DIVIDEND,
			self.DEBENTURE_OR_NOTE_INTEREST
		]

'''
class dincelaccount_aba_line(osv.Model):
	_name = "dincelaccount.aba.line"	
	accountName=""
	accountNumber=""
	bsb=""
	amount=""
	indicator=""
	transactionCode=""
	reference=""
	remitter=""
	taxWithholding=""'''
	