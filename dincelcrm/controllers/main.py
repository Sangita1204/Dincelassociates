import pdb
from openerp.addons.web.http import Controller, route, request
from openerp.addons.report.controllers.main import ReportController
from openerp.osv import osv
from openerp import http
import simplejson

class PTReportController(ReportController):
	@route(['/report/download'], type='http', auth="user")
	def report_download(self, data, token):
		order_obj = http.request.env['account.analytic.account']
		requestcontent = simplejson.loads(data)
		url, type = requestcontent[0], requestcontent[1]
		# url = u'/report/pdf/sale.report_saleorder/37'
		# type = u'qweb-pdf'
		assert type == 'qweb-pdf'
		reportname = url.split('/report/pdf/')[1].split('?')[0]
		# reportname = u'sale.report_saleorder/37'
		reportname, docids = reportname.split('/')
		# reportname = u'sale.report_saleorder'
		# docids = 37
		assert docids
		object = order_obj.browse(int(docids))
		
		name = object.name
		# name = 2014-DE000020
		filename = '' + object.name
		# filename = PT_2014-DE000020
		
		response = ReportController().report_download(data, token)
		response.headers.set('Content-Disposition', 'attachment; filename=%s.pdf;' % filename)
		return response