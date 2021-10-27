import time
from report import report_sxw
from osv import osv

class dincelcrm_report_newcontact(report_sxw.rml_parse):

	def __init__(self, cr, uid, name, context=None):
		super(dincelcrm_report_newcontact, self).__init__(cr, uid, name, context=context)
		self.localcontext.update( {
			'lines': self._get_lines_contact,
		})
		self.context = context 
	
 	 
	def _get_username(self,_id,context){
		if _id:
			sql ="select login from res_users where id='%s'" % (str(_id))
			self.cr.execute(sql)
			rs = self.cr.fetchone()
			if rs and len(rs) > 0:
				return rs[0]
		return ''		
			
	def _get_lines_contact(self, context):
		res = []
		if context.get('form', False):
			
			sql ="SELECT a.name ,a.id,a.create_date,a.write_date,a.create_uid,a.write_uid,a.street,a.mobile,a.phone,a.email,a.x_is_project,a.customer,a.approved_by \
					FROM  res_partner a \
					WHERE a.customer='t' and a.create_date > '2017-02-01' and a.approved_by is null order by a.name" 
			 
			self.cr.execute(sql)
			res1 = self.cr.dictfetchall()
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
				
				vals = {"name": _name, 
						"id": _id, 
						"create_date": create_date, 
						"write_date": write_date, 
						"street": street, 
						"phone": phone, 
						"email": email, 
						"mobile": mobile, 
						"is_project": is_project
						}
				res.append(vals)
			 		
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