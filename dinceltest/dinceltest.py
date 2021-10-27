from openerp.tools.translate import _
from openerp.osv import osv, fields
from datetime import date
from datetime import datetime
import datetime
from datetime import timedelta

#from dateutil import parser from datetime import date
#from openerp.addons.base_status.base_state import base_state
import time 
#import datetime
import csv
from openerp import netsvc, api
from openerp.osv import fields, osv, orm
import logging
import pytz
_logger = logging.getLogger(__name__)

class dinceltest_test(osv.Model):
	_name = "dinceltest.test"
	
  
	def testbutton(self, cr, uid, ids, context=None):
		 
		_from_date 	=  datetime.datetime.strptime(str(datetime.datetime.now()),"%Y-%m-%d %H:%M:%S.%f")
		time_zone	= 'Australia/Sydney'
		tz 			= pytz.timezone(time_zone)
		tzoffset 	= tz.utcoffset(_from_date)
		
		dtquote 	= str((_from_date + tzoffset).strftime("%Y-%m-%d %H:%M:%S.%f"))
		  
		_logger.error("testbutton_testbutton_stage_id -" + str(dtquote)+"[" + str(datetime.datetime.now())+"]")
		 
		
		 
		value 	= { }
		return value
	  
	 
	  