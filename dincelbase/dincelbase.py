from openerp.osv import osv, fields
from datetime import date

import time 
import datetime
import logging
from openerp.tools.translate import _

from time import gmtime, strftime
_logger = logging.getLogger(__name__)

class dincelaccount_region(osv.Model):
	_name 		= 	'dincelaccount.region'
	_columns={
		'name': fields.char('Region Name'),
		'code': fields.char('Code'),
	}
	
class dincelbase_color(osv.Model):
	_name="dincelbase.color"
	_columns={
		'name': fields.char('Name'),
		'num_used': fields.integer('Used'),
		'color_hex': fields.char('Color'),
	}
 	_defaults = {
		'num_used':0,
	}
	
class dincelbase_postcode(osv.Model):
	_name="dincelbase.postcode"
	_columns={
		'name': fields.char('Postcode'),
		'suburb': fields.char('Suburb'),
		'state': fields.char('State'),
	}
	
	
class dincelbase_suburb(osv.Model):
	_name="dincelbase.suburb"
	_columns={
		'name': fields.char('Suburb'),
		'postcode': fields.char('Postcode'),
		'state': fields.char('State'),
	}
	_order = 'name asc'	

#for scheduled task to run for background to sycne with dcs
class dincelbase_scheduletask(osv.Model):
	_name="dincelbase.scheduletask"
	_columns={
		'name': fields.char('Name'),
		'url': fields.char('URL'),
		'action': fields.char('Action'),
		'ref_id': fields.char('Ref ID'),
		'state': fields.char('State'),
	}
class dincelbase_notification(osv.Model):
	_name="dincelbase.notification"
	_columns={
		'name': fields.char('Name'),
		'code': fields.char('Code'),
		'res_model': fields.char('Model'),
		'res_id': fields.char('Res ID'),
		'state': fields.char('State'),
	}	
'''
    def get_default_dcs_api_url(self, cr, uid, fields, context=None):
        #some code... 
        #you can get the field content from some table and return it
        #as a example
        user_name=self.pool.get('res.users').browse(cr, uid, uid, context=context).name
        return {'username': user_name}

    def set_default_dcs_api_url(self, cr, uid, ids, context=None):
        #some code... 
        #you can get the field content from some table and return it
        #as a example
        config = self.browse(cr, uid, ids[0], context)
        new_username=config.username
        self.pool.get('res.users').write(cr, uid, uid, {'name': new_username})	
	'''