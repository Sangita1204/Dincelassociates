from openerp.osv import osv, fields

import logging
from openerp.tools.translate import _

from time import gmtime, strftime
_logger = logging.getLogger(__name__)

class dincelhr_employee(osv.Model):
	_inherit = "hr.employee"
	_columns = {
		'device_ids': fields.one2many('dincelhr.employee.device', 'employee_id', 'Devices'),
	}	
				
class dincelhr_employee_device(osv.Model):
	_name 	= "dincelhr.employee.device"
	_description ="Employee Devices"
	_columns = {
		'employee_id': fields.many2one('hr.employee', 'Employee Reference', required=True, ondelete='cascade', select=True),
		'name': fields.char('Device Name', required=True),
		'brand':fields.char("Brand"),	
		'model':fields.char("Model"),	
		'serialno':fields.char("Serial No"),	
		'keys1':fields.char("Keys 1"),	
		'keys2':fields.char("Keys 2"),	
		'simcard':fields.char("Sim Card"),		
		'given_date':fields.date("Given Date"),	
		'comments':fields.text("Comments"),	
		'parts':fields.char("Parts"),
	}	
 