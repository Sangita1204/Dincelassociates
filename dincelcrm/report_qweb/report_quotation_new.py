from openerp.osv import osv, fields
import time
from functools import partial
from openerp.osv import osv
from openerp.report import report_sxw
#from common_report_header import common_report_header
#from common_report_header1 import common_report_header1
import logging
import base64
from openerp import tools
import subprocess
from subprocess import Popen, PIPE, STDOUT
from openerp.tools import config

_logger = logging.getLogger(__name__)

class dincelcrm_quotation_dcs(report_sxw.rml_parse):

	def __init__(self, cr, uid, name, context=None):
		super(dincelcrm_quotation_dcs, self).__init__(cr, uid, name, context=context)
		
		manager_id = None
 		id = context.get('active_ids')[0]
		manager_id = self.pool.get('account.analytic.account').browse(cr, uid, id, context=context).x_manager
		
		#for id in context.get('active_ids'):
		#	manager_id = self.pool.get('account.analytic.account').browse(cr, uid, id, context=context).x_manager
			
		if manager_id:
			_attach = self.pool.get('ir.attachment').search(cr, uid, [('res_model', '=','res.users'),('res_id','=',manager_id.id)])
			_file_details = self.pool.get('ir.attachment').browse(cr, uid, _attach,context=context)
			location = config['data_dir'] + "/filestore/" + str(cr.dbname)
			if _file_details.store_fname: #added by shukra 27/7/2020 if no signature setup then skip sign
				folder=_file_details.store_fname# or 'daa'
				#_file_location = location+"/"+str(_file_details.store_fname)
				_file_location = location+"/"+str(folder) 
				#_logger.error("dincelcrm_quotation_dcs [%s] [%s]" % (_file_location, _file_details.store_fname))
				f=open(_file_location,'r')
				_data = f.read()
				image_src = base64.b64encode(_data)
							
				#_logger.error("__init__11111["+str(manager_id.id)+"]") 
				
				self.localcontext.update({
					'x_sign':image_src
				})
		
		self.context = context  
	 	

		
class report_quotation_new(osv.AbstractModel):
	_name = 'report.crm.report_quotation_new'
	_inherit = 'report.abstract_report'
	_template = 'dincelcrm.report_quotation_new'
	_wrapped_report_class = dincelcrm_quotation_dcs

class report_quotation_report1(osv.AbstractModel):
	_name = 'report.dincelcrm.report_quotation_report1'
	_inherit = 'report.abstract_report'
	_template = 'dincelcrm.report_quotation_report1'
	_wrapped_report_class = dincelcrm_quotation_dcs
	
class report_quotation_new_pdf(osv.AbstractModel):
	_name = 'report.crm.report_quotation_new_pdf'
	_inherit = 'report.abstract_report'
	_template = 'dincelcrm.report_quotation_new'
	_wrapped_report_class = dincelcrm_quotation_dcs
 	 
	 