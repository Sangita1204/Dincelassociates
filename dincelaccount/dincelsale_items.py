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

	
	 