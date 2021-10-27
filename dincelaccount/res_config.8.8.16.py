from openerp.osv import fields, osv 

class dincelaccount_accountsettings(osv.Model):
	_name 		= 	'dincelaccount.config.settings'
	_columns={
		'name': fields.char('Name'),
		'sale_receiveable': fields.many2one('account.account','Accounts Recievbale'),
		'sale_receiveable_tax': fields.many2one('account.tax','Accounts Recievbale Tax'),
		'sale_payment': fields.many2one('account.account','Payment Recieved'),
		'sale_payment_tax': fields.many2one('account.tax','Payment Recieved Tax'),
		'sale_cash_onhand': fields.many2one('account.account','Cash On Hand'),
		'sale_cash_onhand_tax': fields.many2one('account.tax','Cash On Hand Tax'),
		'sale_overunder_payment': fields.many2one('account.account','Over/Under Payment'),
		'sale_overunder_payment_tax': fields.many2one('account.tax','Over/Under Payment Tax'),
		'sale_advance_payment': fields.many2one('account.account','Payment In Advance'),
		'sale_advance_payment_tax': fields.many2one('account.tax','Payment In Advance Tax'),
		'sale_exchange_loss': fields.many2one('account.account','Exchange Rate Loss'),
		'sale_exchange_loss_tax': fields.many2one('account.tax','Exchange Rate Loss Tax'),
		'sale_exchange_gain': fields.many2one('account.account','Exchange Rate Gain'),
		'sale_exchange_gain_tax': fields.many2one('account.tax','Exchange Rate Gain Tax'),
		'sale_cash_discount': fields.many2one('account.account','Cash Discount'),
		'sale_cash_discount_tax': fields.many2one('account.tax','Cash Discount Tax'),
		'sale_sale': fields.many2one('account.account','Sale Account'),
		'sale_sale_tax': fields.many2one('account.tax','Sale Account Tax'),
		'sale_return': fields.many2one('account.account','Sale Return'),
		'sale_return_tax': fields.many2one('account.tax','Sale Return Tax'),
		'sale_cogs': fields.many2one('account.account','Cost Of Sales'),
		'sale_cogs_tax': fields.many2one('account.tax','Cost Of Sales Tax'),
		'sale_finished_goods': fields.many2one('account.account','Finished Goods'),
		'sale_finished_goods_tax': fields.many2one('account.tax','Finished Goods Tax'),
		'sale_unrealised': fields.many2one('account.account','Unrealised Sales'),
		'sale_unrealised_discount': fields.many2one('account.account','Unrealised Discount Allowed'),
		'sale_freight': fields.many2one('account.account','Freight Income'),
		'sale_freight_unrealised': fields.many2one('account.account','Unrealised Freight Income'),
		'buy_payable': fields.many2one('account.account','Accounts Payable'),
		'buy_payable_tax': fields.many2one('account.tax','Accounts Payable Tax'),
		'buy_payment': fields.many2one('account.account','Payment Made'),
		'buy_payment_tax': fields.many2one('account.tax','Payment Made Tax'),
		'buy_cash_onhand': fields.many2one('account.account','Cash On Hand'),
		'buy_cash_onhand_tax': fields.many2one('account.tax','Cash On Hand Tax'),
		'buy_overunder_payment': fields.many2one('account.account','Over/Under Payment'),
		'buy_overunder_payment_tax': fields.many2one('account.tax','Over/Under Payment Tax'),
		'buy_advance_payment': fields.many2one('account.account','Payment In Advance'),
		'buy_advance_payment_tax': fields.many2one('account.tax','Payment In Advance Tax'),
		'buy_exchange_loss': fields.many2one('account.account','Exchange Rate Loss'),
		'buy_exchange_loss_tax': fields.many2one('account.tax','Exchange Rate Loss Tax'),
		'buy_exchange_gain': fields.many2one('account.account','Exchange Rate Gain'),
		'buy_exchange_gain_tax': fields.many2one('account.tax','Exchange Rate Gain Tax'),
		'buy_cash_discount': fields.many2one('account.account','Cash Discount'),
		'buy_cash_discount_tax': fields.many2one('account.tax','Cash Discount Tax'),
		'buy_expense': fields.many2one('account.account','Expense Account'),
		'buy_expense_tax': fields.many2one('account.tax','Expense Account Tax'),
		'buy_credit': fields.many2one('account.account','Purchase Credit Account'),
		'buy_credit_tax': fields.many2one('account.tax','Purchase Credit Tax'),
		'stock_inventory': fields.many2one('account.account','Inventory Account'),
		'stock_finished_goods': fields.many2one('account.account','Finished Goods'),
		'stock_cost_sale': fields.many2one('account.account','Cost of Goods Sold Account'),
		'stock_received_notinvoiced': fields.many2one('account.account','Stock Recieved Not Invoiced'),
		'stock_purchase_variance': fields.many2one('account.account','Purchase Variance Account'),
		'stock_price_variance': fields.many2one('account.account','Price Variance Account'),
		'stock_adjustment': fields.many2one('account.account','Negative Inventory Adjustment Account'),
		'stock_take_variance': fields.many2one('account.account','Stock Take Variance Account'),
		'stock_sale_return': fields.many2one('account.account','Sales Return Account'),
		'stock_sale_return_tax': fields.many2one('account.tax','Sales Return Tax'),
		'stock_exchange_rate_diff': fields.many2one('account.account','Exchange Rate Difference Account'),
		'stock_revaluation': fields.many2one('account.account','Stock Revaluation Account'),
		'stock_wip': fields.many2one('account.account','WIP Inventory Account'),
		'stock_wip_variance': fields.many2one('account.account','WIP Inventory Variance Account'),
		'stock_transit': fields.many2one('account.account','Stock in Transit Account'),
		'gen_card_fees': fields.many2one('account.account','Credit Card Fees'),
		'gen_overpayments': fields.many2one('account.account','Customer Over Payments'), #BL items
		'gen_closing': fields.many2one('account.account','Period End Closing Account'),
	}	
'''
'x_sale_acct_receive': fields.many2one('account.account','Accounts Recievbale'),
'x_sale_acct_receive_tax': fields.many2one('account.tax','Accounts Recievbale Tax'),
'x_sale_acct_payment': fields.many2one('account.account','Payment Recieved'),
'x_sale_acct_payment_tax': fields.many2one('account.tax','Accounts Recievbale Tax'),
'x_sale_cash_onhand': fields.many2one('account.account','Cash On Hand'),
'x_sale_cash_onhand_tax': fields.many2one('account.tax','Cash On Hand Tax'),
'x_sale_overunder_payment': fields.many2one('account.account','Over/Under Payment'),
'x_sale_overunder_payment_tax': fields.many2one('account.tax','Over/Under Payment Tax'),
'x_sale_advance_payment': fields.many2one('account.account','Payment In Advance'),
'x_sale_advance_payment_tax': fields.many2one('account.tax','Payment In Advance Tax'),
'x_sale_exchange_loss': fields.many2one('account.account','Exchange Rate Loss'),
'x_sale_exchange_loss_tax': fields.many2one('account.tax','Exchange Rate Loss Tax'),
'x_sale_exchange_gain': fields.many2one('account.account','Exchange Rate Gain'),
'x_sale_exchange_gain_tax': fields.many2one('account.tax','Exchange Rate Gain Tax'),
'x_sale_cash_discount': fields.many2one('account.account','Cash Discount'),
'x_sale_cash_discount_tax': fields.many2one('account.tax','Cash Discount Tax'),
'x_sale_account': fields.many2one('account.account','Sale Account'),
'x_sale_account_tax': fields.many2one('account.tax','Sale Account Tax'),
'x_sale_return': fields.many2one('account.account','Sale Return'),
'x_sale_return_tax': fields.many2one('account.tax','Sale Return Tax'),
'x_sale_cogs': fields.many2one('account.account','Cost Of Sales'),
'x_sale_cogs_tax': fields.many2one('account.tax','Cost Of Sales Tax'),
'x_sale_finished_goods': fields.many2one('account.account','Finished Goods'),
'x_sale_finished_goods_tax': fields.many2one('account.tax','Finished Goods Tax'),
'x_sale_unrealised': fields.many2one('account.account','Unrealised Sales'),
'x_sale_unrealised_discount': fields.many2one('account.account','Unrealised Discount Allowed'),
'x_sale_freight': fields.many2one('account.account','Freight Income'),
'x_sale_freight_unrealised': fields.many2one('account.account','Unrealised Freight Income'),'''
#}
'''
class dincelaccount_region(osv.Model):
	_name 		= 	'dincelaccount.region'
	_columns={
		'name': fields.char('Region Name'),
		'code': fields.char('Code'),
	}'''
 