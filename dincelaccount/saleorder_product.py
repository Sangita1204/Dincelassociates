from openerp.osv import osv, fields
from datetime import date
from dateutil.relativedelta import relativedelta
import base64
#import urllib
import time 
import datetime
from datetime import timedelta
import dateutil.parser
import csv
import logging
import urllib2
import simplejson
from openerp import SUPERUSER_ID, api
#from dinceljournal import dincelaccount_journal
import subprocess
from openerp import tools
from dincel_journal import dincelaccount_journal
from openerp.tools.translate import _
from openerp.exceptions import except_orm, Warning, RedirectWarning
from time import gmtime, strftime
from subprocess import Popen, PIPE, STDOUT
import openerp.addons.decimal_precision as dp

_logger = logging.getLogger(__name__)


'''	
class dincelaccount_saleorderxxx_product(osv.Model):
	_inherit="dincelsaleorder.x.product"
	#_order = 'id desc' order_item as in dcs , for summary
	_columns={
		'name': fields.char('name'),
		'order_id': fields.many2one('sale.order','Order'),
		'product': fields.char('Product Group'),
		'date_start': fields.datetime('Start Date'),
		'date_stop': fields.datetime('Complete Date'),
		'is_start': fields.boolean('Is Start'),
		'len_order': fields.float('Ordered Length', digits=(16,2)),
		'len_complete': fields.related('Completed Length', digits=(16,2)),
		'project_id': fields.many2one('res.partner','Project / Site'),	
		'partner_id': fields.many2one('res.partner','Customer'),	
		'state': fields.selection([
			('draft', 'Draft'),
			('done', 'Complete'),
			('part', 'Partial'),
			], 'Status',select=True),	
		}'''
	
