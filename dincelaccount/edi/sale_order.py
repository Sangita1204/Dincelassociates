from openerp.osv import osv
from openerp.tools.translate import _
from openerp.addons.edi import EDIMixin
'''
PURCHASE_ORDER_LINE_EDI_STRUCT = {
    'name': True,
    'date_planned': True,
    'product_id': True,
    'product_uom': True,
    'price_unit': True,
    'product_qty': True,

    # fields used for web preview only - discarded on import
    'price_subtotal': True,
}

PURCHASE_ORDER_EDI_STRUCT = {
    'company_id': True, # -> to be changed into partner
    'name': True,
    'partner_ref': True,
    'origin': True,
    'date_order': True,
    'partner_id': True,
    #custom: 'partner_address',
    'notes': True,
    'order_line': PURCHASE_ORDER_LINE_EDI_STRUCT,
    #custom: currency_id

    # fields used for web preview only - discarded on import
    'amount_total': True,
    'amount_untaxed': True,
    'amount_tax': True,
    'state':True,
}
'''
class dincelsale_order(osv.osv, EDIMixin):
	_inherit = 'sale.order'
	#def edi_export(self, cr, uid, records, edi_struct=None, context=None):
	#	 

class dincelsale_order_line(osv.osv, EDIMixin):
	_inherit='sale.order.line'

