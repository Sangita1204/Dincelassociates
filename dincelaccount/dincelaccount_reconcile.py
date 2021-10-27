import time
import datetime
from lxml import etree

from openerp.osv import fields, osv
from openerp.osv.orm import setup_modifiers
from openerp.tools.translate import _
import logging
_logger = logging.getLogger(__name__)

class dincelaccount_move_reconcile(osv.Model):
	_inherit = 'account.move.reconcile'
	_order = 'id desc'
	_columns = {
		'x_account_id': fields.many2one('account.account', 'Bank Account'),
		'x_last_reconcile':fields.date("Last Reconcile Date"),
		'x_bank_balance':fields.float("Bank Balance"),
		'x_user_id': fields.many2one('res.users','User'),
		'x_dates': fields.selection([('Select', 'Select'),], 'Document Type'),
		'x_move_line_ids': fields.one2many('account.move.line', 'reconcile_id', string="Account moves"),
		#'move_line_id':fields.many2one('account.move.line', 'Move Line'),
	}
	
	def onchange_account(self, cr, uid, ids, account_id, context=None):
		if account_id:
			dates=[]
			cr.execute("select to_char(x_last_reconcile, 'MM/dd/YYYY'),x_bank_balance from account_move_reconcile where x_account_id=" + str(account_id) + " order by write_date desc")
			rows 	= cr.fetchall()
			for row in rows:
				dates.append(str(row[0]))
			#_logger.error("onchange_accountonchange_account:dates -" + str(dates)+"")	
			#return {'value':{'x_dates':selection_add=[dates]}}
 	
class dincelaccount_reconcile(osv.osv_memory):
	_name = 'dincelaccount.reconcile'
	
	_columns = {
		'account_id': fields.many2one('account.account', 'Bank Account'),
		'last_reconcile':fields.date("Last Reconcile Date"),
		'dt_reconcile':fields.date("Reconcile Date"),
		'dt_from':fields.date("From Date"),
		'dt_till':fields.date("Till Date"),
		'bank_balance':fields.float("Bank Balance"),
		'last_balance':fields.float("Last Balance"),
		'curr_balance':fields.float("Current Balance"),
		'net_balance':fields.float("Net Balance"),
		'net_balance2':fields.float("Net Balance"),
		'reconcile_balance':fields.float("Reconcile Balance"),
		'reconcile_lines':fields.one2many('dincelaccount.reconcile.line', 'reconcile_id', 'Reconciles'),
		'user_id': fields.many2one('res.users','User'),
		'process_flag':fields.boolean("Process Flag"),
	}
	
	_defaults={
		'dt_reconcile': fields.date.context_today, #time
		'user_id': lambda obj, cr, uid, context: uid,
		}
	def on_change_processflag(self, cr, uid, ids, _flag,_lines, context=None):
		vals={}
		context = context or {}
		
	 
		if _lines:
			
			line_ids = self.resolve_2many_commands(cr, uid, 'reconcile_lines', _lines, ['reconcile'], context)
			 
			for line in line_ids:
				if line:
				 
					line['reconcile']= _flag
					 
			return {'value': {'reconcile_lines': line_ids}}
			
		return {'value':vals}
		
	def onchange_line_ids(self, cr, uid, ids, reconcile_lines, last_balance,bank_balance, context=None):
		context = context or {}
		if not reconcile_lines:
			return {}

		line_ids = self.resolve_2many_commands(cr, uid, 'reconcile_lines', reconcile_lines, ['debit','credit','reconcile'], context)
		amt_dr = 0.0
		amt_cr = 0.0 
		for line in line_ids:
			#_logger.error("convert2opportunity:vals -" + str(line)+"")	
			if line['reconcile']:
				if line['debit']:
					amt_dr += line['debit']
				if line['credit']:
					amt_cr += line['credit'] 
		return {'value': {'curr_balance': (amt_dr-amt_cr)}}
		
	def onchange_amount(self, cr, uid, ids, curr,net,last,bank, context=None):
		#new=last+curr
		net_val = bank+curr
		return {'value': {'net_balance': (net_val), 'net_balance2': (net_val)}}
	
	def onchange_account(self, cr, uid, ids, account_id,dt_from,dt_till, context=None):
		if account_id:
			_line=self.pool.get('account.move.line')
			items=[]
			
			dt1=datetime.date.today()
			bal1=0.0
			#cr.execute("select to_char(x_last_reconcile, 'MM/dd/YYYY i:mm:ss am') from account_move_reconcile where x_account_id=" + str(account_id) + " order by x_last_reconcile desc")
			cr.execute("select to_char(x_last_reconcile, 'MM/dd/YYYY'),x_bank_balance from account_move_reconcile where x_account_id=" + str(account_id) + " order by write_date desc")
			rows 	= cr.fetchone()
			if rows:
				#dt1 	=  datetime.datetime.strptime(rows[0],"%m/%d/%Y %I:%M:%S %p")
				dt1 	=  datetime.datetime.strptime(rows[0],"%m/%d/%Y")
				bal1	=  rows[1]
				 
			value={
					'last_reconcile':dt1,
					'last_balance':bal1,
					'bank_balance':bal1,
					'process_flag':False,
				}	
			if dt_from and dt_till:
				_ids	= _line.search(cr,uid,[('account_id', '=', account_id),('state', '=', 'valid'),('reconcile_id', '=', False),('date', '>=', dt_from),('date', '<=', dt_till)]) 	
			else:
				_ids	= _line.search(cr,uid,[('account_id', '=', account_id),('state', '=', 'valid'),('reconcile_id', '=', False)]) 	
			for rec in _line.browse(cr, uid, _ids, context=context):
				if rec.move_id.state == "posted":
					vals={
						'move_line_id':rec.id,
						'debit':rec.debit,
						'credit':rec.credit,
						'reconcile':False,
						'dt_move':rec.date,
					}
					if rec.partner_id:
						vals['partner_id']=rec.partner_id.id
					items.append(vals)
			value['reconcile_lines']  =items
			return {'value': value}
		return {}	
	
	def save_reconcile(self, cr, uid, ids, context=None):	
		_obj = self.pool.get('account.move.reconcile')
		_objline = self.pool.get('account.move.line')

		record = self.browse(cr, uid, ids[0], context=context)
		
		#_logger.error("convert2opportunity:net_balancenet_balance[" + str(record.net_balance)+"][" + str(record.last_balance)+"]")	
		'''if record.net_balance:
			if record.bank_balance == record.last_balance:
				raise osv.except_osv(_('Error!'),_('The reconcile bank balance has not been changed.'))
				return False
			elif record.net_balance != 0.0:
				raise osv.except_osv(_('Error!'),_('The reconcile net balance is not zero.'))
				return False
			else:'''
		search_ids = _obj.search(cr, uid, [])
		last_id = search_ids and max(search_ids)
		if last_id:
			last_id=last_id+1
		else:
			last_id=1

		if record.bank_balance:		
			vals ={
				'type':'manual',
				'name':'A'+str(last_id),
				'x_account_id':record.account_id.id,
				'x_last_reconcile':record.dt_reconcile,
				'x_bank_balance':record.net_balance2,
				'x_user_id':record.user_id.id,
			}
			 
			_newid= _obj.create(cr, uid, vals, context=context)
			for rec in record.reconcile_lines:
				if rec.reconcile:
					_objline.write(cr, uid, [rec.move_line_id.id], {'reconcile_id':_newid}, context=context)
		#else:
		#	_logger.error("convert2opportunity:valserrrr[" + str(ids[0])+"]")	
		
class dincelaccount_reconcile_line(osv.osv_memory):
	_name = 'dincelaccount.reconcile.line'
	
	_columns = {
		'reconcile_id':fields.many2one('dincelaccount.reconcile', 'Reconcile'),
		'move_line_id':fields.many2one('account.move.line', 'Move Line'),
		'partner_id': fields.many2one('res.partner','Partner'),
		'debit':fields.float("Debit"),
		'credit':fields.float("Credit"),
		'reconcile':fields.boolean("Reconcile"),
		'balance':fields.float("Balance"),
		'dt_move':fields.date("Date"),
	}
	
	def onchange_reconcile(self, cr, uid, ids, reconcile,debit,credit, context=None):
		value={}
		if reconcile:
			balance = debit-credit
		else:
			balance=0
		value['balance']  =balance
		return {'value': value}