from openerp.osv import osv, fields
from datetime import date
#from openerp.addons.base_status.base_state import base_state
import time 
import datetime
import logging
from dateutil import parser
from dateutil.relativedelta import relativedelta
from openerp.tools.translate import _
import urllib2
import simplejson
from time import gmtime, strftime
import base64
import subprocess
from subprocess import Popen, PIPE, STDOUT
import openerp.addons.decimal_precision as dp
from openerp import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

PROD_GROUP_SELECTION = [
	('none', 'None'),
	('P110', '110mm'),
	('P155', '155mm'),
	('P200', '200mm'),
	('P275', '275mm'),
	]

class dincelmrp_log_records(osv.Model):
	_name = "dincelmrp.log.records"
	_inherit = "mail.thread"
	_order = 'id desc'
	_description = 'MRP Line Log'
	def _get_log_details(self, cr, uid, ids, values, arg, context):
		x={}
		if context is None:
			context = {}
		return x
	
	def create(self, cr, uid, vals, context=None):
		if vals.get('name','') == '':
			vals['name'] = self.pool.get('ir.sequence').get(cr, uid, 'mrplog.number') or ''
		#else:
		#	vals['name'] = "lead"
		return super(dincelmrp_log_records, self).create(cr, uid, vals, context=context)
	
	def mrp_log_records(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		datas = {'ids': context.get('active_ids', [])}
		datas['form']  = self.read(cr, uid, ids, context=context)[0]
		
		#_logger.error("print_quotation_qweb111["+str(datas)+"]["+str(ids)+"]")
		
		return self.pool['report'].get_action(cr, uid, [], 'dincelmanufacture.report_mrp_log_records', data=datas, context=context)
		
	'''
	def _get_lines(self, cr, uid, ids, context=None):
		sql = "select id,name from mrp_routing where active='t'"
		cr.execute(sql)
		rows = cr.fetchall()
		sel = ''
		for row in rows:
			sel += "('"+row['id']+"','"+row['name']+"'),"

		return [sel]

	def _get_category(self, cr, uid, ids, context=None):
		sql = "select id,name from mrp_loss_category where active='t'"
		cr.execute(sql)
		rows = cr.fetchall()
		sel = ''
		for row in rows:
			sel += "('"+int(row['id'])+"','"+row['name']+"'),"

		return [sel]
	'''

	_columns = {
		'log_date': fields.date('Date'),
		'user_id':fields.many2one("res.users", 'Updated By'),
		'name':fields.char('Name'),
		'log_record_line': fields.one2many("dincelmrp.log.records.line", 'log_id', 'Log Records Lines')
	}
	_defaults = {
		'name': lambda obj, cr, uid, context: '',
		'user_id': lambda obj, cr, uid, context: uid
	}

	
class dincelmrp_log_records_line(osv.Model):
	_name = "dincelmrp.log.records.line"
	_columns = {
		'log_id': fields.many2one("dincelmrp.log.records", "Records"),
		'line_id':fields.many2one("mrp.routing", 'Line'),
		'category_id':fields.many2one("dincelmrp.log.records.category", 'Category'),
		'duration':fields.float("Duration"),
		'start_time': fields.datetime('Start Time'),
		'end_time': fields.datetime('End Time'),
		'duration_unit':fields.selection([
			('0.0167','Minutes'),
			('1','Hours'),
			('24','Days')
		], 'Duration Unit', type="float")#Duration unit all in hours (1 min = 0.0167 hour, 1 day = 24 hour)
	}
	_defaults = {
		'duration_unit': '0.0167',
	}
	def with_start_end(self, cr, uid, ids, _start=0, _end=0, _duration=0, _unit=0, context=None):
		result={}
		if _start == 0:
			result.update({'duration':None})
			result.update({'end_time':None})
			return {'value': result}
		elif _end == 0:
			result.update({'duration':None})
			return {'value': result}
		else:
			return self.calculate_duration(cr, uid, ids, _start, _end, 0, _unit, context)
	
	def with_duration(self, cr, uid, ids, _start=0, _end=0, _duration=0, _unit=0, context=None):
		result={}
		if _start == 0:
			result.update({'duration':None})
			result.update({'end_time':None})
			return {'value': result}
		elif _duration == 0:
			result.update({'end_time':None})
			return {'value': result}
		else:
			return self.calculate_duration(cr, uid, ids, _start, 0, _duration, _unit, context)
	
	def calculate_duration(self, cr, uid, ids, _start=0, _end=0, _duration=0, _unit=0, context=None):
		result={}
		_duration_tmp = 0
		
		if context is None:
			context = {}
			
		if(_start != 0):
			start_temp = datetime.datetime.strptime(str(_start), '%Y-%m-%d %H:%M:%S')
		else:
			start_temp = 0
			
		if(_end != 0):
			ends_temp = datetime.datetime.strptime(str(_end), '%Y-%m-%d %H:%M:%S')
		else:
			ends_temp = 0
		
		diff_temp = relativedelta(ends_temp,start_temp)
		
		total_minutes = 0
		
		if(diff_temp.months):
			total_minutes += int(diff_temp.months)*30*24*60
		if(diff_temp.days):
			total_minutes += int(diff_temp.days)*24*60
		if(diff_temp.hours):
			total_minutes += int(diff_temp.hours)*60
		if(diff_temp.minutes):
			total_minutes += int(diff_temp.minutes)
			
		if(_unit == '1'):
			total_minutes = total_minutes/60
		elif(_unit == '24'):
			total_minutes = total_minutes/(60*24)
		else:
			total_minutes = total_minutes
		
		total_minutes = round(total_minutes,2)
		
		if(_start != 0 and _end != 0):
			result.update({'duration':total_minutes})
			#result.update({'duration_unit':'0.0167'})
		elif(_start != 0 and _duration != 0):
			_duration_tmp = _duration * float(_unit) * 60
			end_time = start_temp + datetime.timedelta(minutes = _duration_tmp)
			new_end = datetime.datetime.strftime(end_time, '%Y-%m-%d %H:%M:%S')
			result.update({'end_time':new_end})
			result.update({'duration':_duration})
			#result.update({'duration_unit':_unit})
			
		'''
		if(_duration != 0):
			if(_start != 0):
				_duration = _duration * float(_unit) * 60
				end_time = start_temp + datetime.timedelta(minutes = _duration)
				new_end = datetime.datetime.strftime(end_time, '%Y-%m-%d %H:%M:%S')
				result.update({'duration':_duration})
				result.update({'end_time':new_end})
				result.update({'duration_unit':'0.0167'})
			else:
				result.update({'duration':_duration})
				result.update({'duration_unit':'0.0167'})
		else:
			result.update({'duration':total_minutes})
			result.update({'duration_unit':'0.0167'})
		'''	
		return {'value': result}
	
	 
		

class dincelmrp_log_records_category(osv.Model):
	_name = "dincelmrp.log.records.category"
	_columns = {
		'name':fields.char("Category Name")
	}