import time
from report import report_sxw
from osv import osv

class sale_quotation(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(sale_quotation, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time, 
            'show_discount':self._show_discount,
        })

    def _show_discount(self, uid, context=None):
        cr = self.cr
        try: 
            group_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'sale', 'group_discount_per_so_line')[1]
        except:
            return False
        return group_id in [x.id for x in self.pool.get('res.users').browse(cr, uid, uid, context=context).groups_id]
	def _display_accept_text(self, cr, uid, sname, txt, context=None):
		txt = txt.replace("#clientname#", sname)
		return txt + "1" + sname + "1"	
	def display_accept_text(self, cr, uid, sname, txt, context=None):
		txt = txt.replace("#clientname#", sname)
		return txt + "0" + sname + "0"		
 
report_sxw.report_sxw('report.sale.quotations.pdf','sale.order','addons/dincelcrm/report/sale_quotation.rml',parser=sale_quotation, header="external")

#---------------------------------------------------------------

class contract_quotation(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(contract_quotation, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time, 
        })

report_sxw.report_sxw('report.account.analytic.account.quote','account.analytic.account','addons/dincelcrm/report/contract_quotation.rml',parser=contract_quotation, header="external")

#---------------------------------------------------------------
class contract_quotation_rate1(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(contract_quotation_rate1, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time, 
        })

report_sxw.report_sxw('report.account.analytic.account.quote_rate1','account.analytic.account','addons/dincelcrm/report/contract_quotation_rate1.rml',parser=contract_quotation_rate1, header="external")

#---------------------------------------------------------------

class contract_quotation_rate2(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(contract_quotation_rate2, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time, 
        })

report_sxw.report_sxw('report.account.analytic.account.quote_rate2','account.analytic.account','addons/dincelcrm/report/contract_quotation_rate2.rml',parser=contract_quotation_rate2, header="external")

#---------------------------------------------------------------

class contract_quotation_rate3(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(contract_quotation_rate3, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time, 
        })

report_sxw.report_sxw('report.account.analytic.account.quote_rate3','account.analytic.account','addons/dincelcrm/report/contract_quotation_rate3.rml',parser=contract_quotation_rate3, header="external")

#---------------------------------------------------------------

class contract_quotation_275(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(contract_quotation_275, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time, 
        })

report_sxw.report_sxw('report.account.analytic.account.quote_275','account.analytic.account','addons/dincelcrm/report/contract_quotation_275.rml',parser=contract_quotation_275, header="external")

#---------------------------------------------------------------
class contract_quotation_v2(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(contract_quotation_v2, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time, 
        })

report_sxw.report_sxw('report.account.analytic.account.quote_v2','account.analytic.account','addons/dincelcrm/report/contract_quotation_v2.rml',parser=contract_quotation_v2, header="external")

#---------------------------------------------------------------