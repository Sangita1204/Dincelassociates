from openerp.tools.translate import _
from openerp.osv import osv, fields
from datetime import date
from datetime import datetime
import datetime
from datetime import timedelta
import config_dcs
import openerp.addons.decimal_precision as dp
from dateutil import parser# from datetime import date
#from openerp.addons.base_status.base_state import base_state
import subprocess
from subprocess import Popen, PIPE, STDOUT
import time 
#import datetime
import csv
from openerp import netsvc, api
from openerp.osv import fields, osv, orm
import logging
import pytz
_logger = logging.getLogger(__name__)
#from openerp import models, fields, api, _
class dincelcrm_quote_schedule(osv.Model):
	_name="dincelcrm.quote.schedule"
	_inherit = ['mail.thread']
	_description = 'Component List Schedule' #quote schedule
	
	def _over_due_clist(self, cr, uid, ids, values, arg, context):
		x={}
		
		for record in self.browse(cr, uid, ids):
			_ret=False
			if record.component_required and record.component_sent==False:
				cur_date = datetime.datetime.now().date()
				new_date = cur_date + datetime.timedelta(days=5)
				if parser.parse(str(new_date)) > parser.parse(record.component_required):
					_ret=True
			x[record.id]=_ret 
		return x
		
	_columns={
		'name': fields.char('Name',size=64, required=True),
		'sequence':fields.integer('sequence'),
		'user_id': fields.many2one('res.users', 'Salesperson'),
		'partner_id': fields.many2one("res.partner","Customer"),
		'project_id': fields.many2one("res.partner","Project/Site"),
		'quote_id': fields.many2one("account.analytic.account","Quote"),
		'wall_id': fields.many2one('dincelcrm.quote.wall.type','Wall/Level'),
		'product': fields.selection([
			('P110', '110mm'),
			('P155', '155mm'),
			('P200', '200mm'),
			('P275', '275mm'),
			], 'Product'),
		'entry_dt': fields.date("Entry Date"),
		'entry_by': fields.many2one('res.users', 'Estimate Team',track_visibility='onchange'),
		'component_sent': fields.date("Component List Sent"),
		'component_required': fields.date("Component Required"),
		'component_received': fields.date("Component List Returned"),
		'order_sent': fields.date("Order Sent"),
		'order_received': fields.date("Order Returned"),
		'delivery_date': fields.date("Delivery",track_visibility='onchange'),
		'size_m2': fields.float("Size m2"),
		'comments': fields.char("Comments"),
		'over_due_clist': fields.function(_over_due_clist, method=True, string='OverdueCList',type='boolean'),
		'pour_ids': fields.one2many('dincelcrm.quote.pour', 'schedule_id', string="Pours"),
		'state': fields.selection([
			('draft', 'Draft'),
			('progress', 'Progress'),
			('done', 'Done'),
			], 'State',track_visibility='onchange'),
	}
	_defaults={
        'entry_dt': fields.date.context_today, 
		'entry_by': lambda s, cr, uid, c: uid,
		'sequence': 10,
		'state': 'draft',
		#'user_id': lambda obj, cr, uid, context: uid,
        'name': lambda obj, cr, uid, context: '/',
    }
	
	def create(self, cr, uid, vals, context=None):
		if context is None:
			context = {}
		if vals.get('name', '/') == '/':
			vals['name'] 		=	self.pool.get('ir.sequence').get(cr, uid, 'quote.schedule') or '/'
		if vals.get('delivery_date'):	
			vals['component_required']  =  parser.parse(vals.get('delivery_date')) -  datetime.timedelta(days = 21)
		new_id = super(dincelcrm_quote_schedule, self).create(cr, uid, vals, context=context)
		
		return new_id
		
	def write(self, cr, uid, ids, vals, context=None):
		
		res = super(dincelcrm_quote_schedule, self).write(cr, uid, ids, vals, context=context)
		for record in self.browse(cr, uid, ids):
			if record.delivery_date:
				_dt  =  parser.parse(record.delivery_date) -  datetime.timedelta(days = 21)
				sql="update dincelcrm_quote_schedule set component_required='%s' where id='%s'" % (_dt, record.id)
				cr.execute(sql)
			
		return res	
		
class dincelcrm_quote_pour(osv.Model):
	_name="dincelcrm.quote.pour"
	_description = 'Level Pouring'
	_columns={
		'schedule_id': fields.many2one('dincelcrm.quote.schedule', 'Schedule', ondelete='cascade',), #delete all this on delete  
		'name': fields.char('Pour Level /Wall /Name',size=64),
		'pour_date':fields.date("Pour Date"),
		'pour_sn':fields.integer("SN"),
		'size_m2':fields.float("Size m2"),
		'state': fields.selection([
			('draft', 'Draft'),
			('progress', 'Progress'),
			('done', 'Done'),
			], 'State'),
		
	}

	