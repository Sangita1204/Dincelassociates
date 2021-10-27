import os

from openerp import http
from openerp.http import request, route
from openerp.addons.web.controllers.main import serialize_exception,content_disposition
import base64
from sys import argv
from openerp.addons.report.controllers.main import ReportController
#f#rom openerp.http import request, route
from werkzeug import exceptions, url_decode
import simplejson

import logging
_logger = logging.getLogger(__name__)

#script, filename = argv

#txt = open(filename)

#print "Here's your file %r:" % filename
#print txt.read()

class MyController(http.Controller):
	
	@http.route('/web/binary/some_html', type="http")
	def some_html(self,f,c):
		#filecontent="hello"#base64.b64decode("hello")
		#filename="11.aba"
		filename='/var/tmp/'+str(f)
		if os.path.exists(filename):
			txt = open(filename)
			cc=txt.read()
			os.remove(filename)
			return request.make_response(cc,[('Content-Type', 'application/octet-stream'),('Content-Disposition', content_disposition(f))])
		#return "<h1>This is a test</h1>"
	#@serialize_exception	
	@http.route('/web/binary/download_document', type='http', auth="public")
	def download_document(self,model,field,id,filename=None, **kw):
		#""" Download link for files stored as binary fields.
		#:param str model: name of the model to fetch the binary from
		#:#param str field: binary field
		#:param str id: id of the record from which to fetch the binary
		#:param str filename: field holding the file's name, if any
		#:returns: :class:`werkzeug.wrappers.Response`
		#1"1""
		#return "hello"
		 
		Model = request.registry[model]
		cr, uid, context = request.cr, request.uid, request.context
		fields = [field]
		res = Model.read(cr, uid, [int(id)], fields, context)[0]
		
		filecontent = base64.b64decode(res.get(field) or '')
		#return filecontent
		'''
		if not filecontent:
			return request.not_found()
		else:
			if not filename:
				filename = '%s_%s' % (model.replace('.', '_'), id)
			print filename
			return	
			return request.make_response(filecontent,
						[('Content-Type', 'application/octet-stream'),
						('Content-Disposition', content_disposition(filename))])
		'''					 
		print "12"
	@http.route('/web/binary/download_file', type='http', auth="public")
	def download_file(self,model,field,id,path,filename):
		#""" Download link for files stored as binary fields.
		#:param str model: name of the model to fetch the binary from
		#:#param str field: binary field
		#:param str id: id of the record from which to fetch the binary
		#:param str filename: field holding the file's name, if any
		#:returns: :class:`werkzeug.wrappers.Response`
		#1"1""
		#return "hello"
		 
		Model = request.registry[model]
		cr, uid, context = request.cr, request.uid, request.context
		#fields = [field]
		#res = Model.read(cr, uid, [int(id)], fields, context)[0]
		#fname="loadsheet"+str(o.id)+".pdf"
		#save_path="/var/tmp/odoo/sale/"+fname
		 
		
		if path and filename:
			#filecontent = base64.b64decode(path + "/" + filename)
			temp_path=path + "/" + filename
			f=open(temp_path,'r')
		
			filecontent = f.read()
			#filecontent = base64.b64encode(_data)
			return request.make_response(filecontent,
							[('Content-Type', 'application/octet-stream'),
							('Content-Disposition', content_disposition(filename))])
		#return request.not_found()
		#return filecontent
		'''
		if not filecontent:
			return request.not_found()
		else:
			if not filename:
				filename = '%s_%s' % (model.replace('.', '_'), id)
			print filename
			return	
			return request.make_response(filecontent,
						[('Content-Type', 'application/octet-stream'),
						('Content-Disposition', content_disposition(filename))])
		'''					 
		#print "12"				




class Main(ReportController):

	def get_custom_filename(self, model, res_id):
		"""Default behavior will be to get the name of the generated attachment.
		If no attachment is found, for watever reason, this method will generate 
		the filename based on the res_model.
		
		Feel free to override it if needed.
		"""
		args = [('res_model', '=', model), ('res_id', '=', res_id)]
		attachment = request.env['ir.attachment'].search(args)

		record = request.env[model].browse(res_id)

		for rec in attachment: #added
			if attachment.exists():
		 		return rec.name #added
		 		#return attachment.name

		if record.exists():
				return record.name#'{}-{}'.format(record._table, record.name)



	@route()
	def report_download(self, data, token):
		"""Attempt to generate proper filenames for qweb-pdf."""
		res = super(Main, self).report_download(data, token)
		
		data1 = simplejson.loads(data)
		url, report_type = data1
		model=None
		active_id=None
		filename=None
		report_name=None
		if report_type != 'qweb-pdf':
			return res
		part1, part2 = url.split('/report/pdf/')	
		
		if '/' in part2:
			report_name, active_id = part2.split('/')
			
		else:
			# Particular report:
			report_name,part2 = part2.split('?')#url_decode([1]).items()  # decoding the args represented in JSON
			data=url_decode(part2).items()
			
			
			data=dict(data)
			context1=data['context']
			
			context1 = simplejson.loads(context1)
			
			
			if context1.get('active_id'):
				active_id=context1.get('active_id')
			if context1.get('active_model'):
				model=context1.get('active_model')	
		
		
		#_logger.error("report_download:report_type -" + str(report_type)+"-url[" + str(url)+"]")	
		args = [('report_name', '=', report_name)]
		act_report = request.env['ir.actions.report.xml'].search(args)
		#_logger.error("report_download:act_report [" + str(act_report)+"]args[" + str(args)+"]")	
		if not act_report.exists():
			return res

		filename = self.get_custom_filename(act_report.model, int(active_id))
		if not(filename):
			return res

		if not filename.endswith('.pdf'):
			filename = '{}.pdf'.format(filename)

		content_disposition = 'attachment; filename={}'.format(filename)
		res.headers.set('Content-Disposition', content_disposition)
		#_logger.error("report_download:report_name -" + str(report_name)+"-active_id[" + str(active_id)+"]")

		return res
		