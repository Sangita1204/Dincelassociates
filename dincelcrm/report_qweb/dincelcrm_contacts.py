import time
from functools import partial
#from openerp.osv import osv
from openerp.osv import fields, osv
from openerp.report import report_sxw
#from common_report_header import common_report_header
#from common_report_header1 import common_report_header1
import logging
_logger = logging.getLogger(__name__)


class dincelcrm_report_newcontact(report_sxw.rml_parse):

	def __init__(self, cr, uid, name, context=None):
		super(dincelcrm_report_newcontact, self).__init__(cr, uid, name, context=context)
		self.localcontext.update( {
			'lines': self._get_lines_contact,
		})
		self.context = context 
	
 	 
	def _get_username(self,_id,context):
		if _id:
			sql ="select login from res_users where id='%s'" % (str(_id))
			self.cr.execute(sql)
			rs = self.cr.fetchone()
			if rs and len(rs) > 0:
				return rs[0]
		return ''		
	def _to_string(self, _str):
		if _str:
			return str(_str)
		else:
			return ""
	def _get_lines_contact(self, context):
		res = []
		if context.get('form', False):
			
			sql ="SELECT a.name ,a.id,a.create_date,a.write_date,a.create_uid,a.write_uid,a.street,a.mobile,a.phone,a.email,a.x_is_project,a.customer,a.x_approved_by \
					FROM  res_partner a \
					WHERE a.customer='t' and a.create_date > '2017-02-01' and a.x_approved_by is null order by a.name" 
			#_logger.error("_get_lines_contact:sqlsql[" + str(sql)+ "]") 
			self.cr.execute(sql)
			res1 = self.cr.dictfetchall()
			#_logger.error("_get_lines_contact:res1res1[" + str(res1)+ "]") 
			for row in res1:
				_name		=row['name']
				_id			=row['id']
				create_date	=row['create_date']
				write_date	=row['write_date']
				create_uid	=row['create_uid']
				write_uid	=row['write_uid']
				street		=row['street']
				phone		=row['phone']
				is_project	=row['x_is_project']
				email		=row['email']
				mobile		=row['mobile']
				
				create_usr=self._get_username(create_uid, context) 
				write_usr=self._get_username(create_uid, context) 
			
				vals = {"name": str(_name), 
						"id": str(_id), 
						"create_date": self._to_string(create_date), 
						"write_date": self._to_string(write_date), 
						"street": self._to_string(street), 
						"phone": self._to_string(phone), 
						"email": self._to_string(email), 
						"mobile": self._to_string(mobile), 
						"is_project": self._to_string(is_project),
						"create_usr": self._to_string(create_usr), 
						"write_usr": self._to_string(write_usr),
						}
				res.append(vals)
		#_logger.error("_get_lines_contact:resresres[" + str(len(res))+ "]")	 		
		return res
		
 
		
class report_newcontact(osv.AbstractModel):
	_name = 'report.dincelcrm.report_newcontact'
	_inherit = 'report.abstract_report'
	_template = 'dincelcrm.report_newcontact' #///NOTE "dincelcrm"
	_wrapped_report_class = dincelcrm_report_newcontact
	 
 	
class dcsreport_stock_report(osv.osv_memory):
	_name = 'dcsreport.contact.report'
	_columns = {
		'date': fields.date('Date'),
	}
	_defaults = {
		'date': lambda *a: time.strftime('%Y-%m-%d'),
	}
	

	def print_report(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		datas = {'ids': context.get('active_ids', [])}
	 
		datas['form']  = self.read(cr, uid, ids, context=context)[0]
		#_logger.error("print_reportprint_reportprint_report["+str(datas['form'])+"]")	
		return self.pool['report'].get_action(cr, uid, [], 'dincelcrm.report_newcontact', data=datas, context=context)			