
from openerp import tools
from openerp.osv import fields, osv
from openerp.tools.translate import _

class dincelaccount_bastax(osv.osv):
	_name = 'dincelaccount.bastax'
	_columns = {
		'number': fields.char('Number'),
	}
	
'''

CREATE OR REPLACE VIEW dincelaccount_tax AS (
			SELECT id,
				number,
				partner_id,
				type,
				date_invoice,
				state,
				tax_code_id,
				tax_amount,
				base_amount
				FROM
				(
				  select i.id::text || '-' || t.id::text AS id,
					i.number AS number,
					i.partner_id AS partner_id,
					i.type  AS type,
					i.date_invoice  AS date_invoice,
					i.state  AS state,
					t.tax_code_id  AS tax_code_id,
					t.amount  AS tax_amount,
					t.base_amount  AS base_amount
					from account_invoice i,account_invoice_tax t 
					where i.id=t.invoice_id and i.state='open'
				) AS foo
				)
				
union
					select v.id::text || '-' || v.number::text AS id,
					v.number  AS number,
					v.partner_id  AS partner_id,
					v.type  AS type,
					v.date  AS date_invoice,
					v.state  AS state,
					v.tax_id  AS tax_code_id,
					v.tax_amount  AS tax_amount,
					v.amount  AS base_amount
					from account_voucher v 
					where v.tax_amount is not null
				'''

class dincelaccount_tax(osv.osv):
	_name = 'dincelaccount.tax'
	_auto = False
	_order = 'date_invoice asc'

	#'company_id': fields.many2one('res.company', 'Company', required=True)
	_columns = {
		'number': fields.char('Number'),
		'company_id': fields.many2one('res.company', 'Company'),
		'partner_id': fields.many2one('res.partner', 'Partner'),
		'period_id': fields.many2one('account.period', 'Period'),
		'type': fields.char('Type'),
		'date_invoice': fields.datetime('Date'),
		'state': fields.char('State'),
		'tax_code_id': fields.many2one('account.tax.code', 'Tax Code'),
		'tax_name': fields.char('Tax Name'),
		'tax_code': fields.char('Tax Code'),
		'tax_amount': fields.float('Tax Amt'),
		'base_amount': fields.float('Base Amount'),
	}

	def init(self, cr):
		tools.drop_view_if_exists(cr, 'dincelaccount_tax')
		cr.execute("""
			CREATE OR REPLACE VIEW dincelaccount_tax AS (
			SELECT id,
				number,
				tax_amount,
				type,
				state,
				tax_code_id,
				tax_name,
				tax_code,
				base_amount,
				date_invoice,
				period_id,
				company_id,
				partner_name,
				partner_id
				FROM
				(
				  (	
				  select i.id::text || '-' || t.id::text AS id,
					i.number AS number,
					t.amount  AS tax_amount,
					i.type  AS type,
					i.state  AS state,
					t.tax_code_id  AS tax_code_id,
					c.name  AS tax_name,
					c.code  AS tax_code,
					t.base_amount  AS base_amount,
					i.date_invoice  AS date_invoice,
					i.period_id  AS period_id,
					i.company_id  AS company_id,
					p.name  AS partner_name,
					i.partner_id AS partner_id	
					from account_invoice i,account_invoice_tax t,account_tax_code c,res_partner p  
					where i.id=t.invoice_id and t.tax_code_id=c.id and i.partner_id=p.id and i.state='open'
					)
					union
					(
					select v.id::text || '-' || v.number::text AS id,
					v.number  AS number,
					v.tax_amount  AS tax_amount,
					v.type  AS type,
					v.state  AS state,
					c.id  AS tax_code_id,
					c.name  AS tax_name,
					c.code  AS tax_code,
					(v.amount-v.tax_amount)  AS base_amount,
					v.date  AS date_invoice,
					v.period_id  AS period_id,
					v.company_id  AS company_id,
					p.name  AS partner_name,
					v.partner_id  AS partner_id
					from account_voucher v,account_tax t,account_tax_code c,res_partner p 
					where v.tax_id=t.id and t.ref_tax_code_id=c.id and v.partner_id=p.id and v.tax_amount is not null
					)
				) AS foo1
				)
			""")

			
		