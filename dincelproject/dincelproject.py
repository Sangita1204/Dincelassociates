from openerp.osv import osv, fields
from datetime import date
#from openerp.addons.base_status.base_state import base_state
import time 
import datetime
import csv
import logging
#import config_dcs
#import urllib2
#import simplejson
from openerp import tools
from openerp.tools.translate import _
#from crm import crm
from time import gmtime, strftime
_logger = logging.getLogger(__name__)


class dincelproject_res_partner(osv.Model):
	_inherit = "res.partner"
	def button_view_partner_issues(self, cr, uid, ids, context=None):
		if context is None:
			context = {}	
		for record in self.browse(cr, uid, ids, context=context):	
			partner_id=record.id 
			#task_id = context.get('active_id', False)
			#task_pool = self.pool.get('project.issue')
			#delegate_data = self.read(cr, uid, ids, context=context)[0]
			#delegated_tasks = task_pool.do_delegate(cr, uid, [task_id], delegate_data, context=context)
			#models_data = self.pool.get('ir.model.data')

			#action_model, action_id = models_data.get_object_reference(cr, uid, 'project', 'action_view_task')
			#view_model, task_view_form_id = models_data.get_object_reference(cr, uid, 'project', 'view_task_form2')
			#view_model, task_view_tree_id = models_data.get_object_reference(cr, uid, 'project', 'view_task_tree2')
			#action = self.pool[action_model].read(cr, uid, [action_id], context=context)[0]
			#action['res_id'] = delegated_tasks[task_id]
			#action['view_id'] = False
			#action['views'] = [(task_view_form_id, 'form'), (task_view_tree_id, 'tree')]
			#action['help'] = False    
			value = {
				'type': 'ir.actions.act_window',
				'name': _('All Issues'),
				'view_type': 'form',
				'view_mode': 'tree,form',
				'res_model': 'project.issue',
				'domain':[('partner_id','=',partner_id)],
				'context':{'search_default_partner_id': partner_id},
				'view_id': False,
				
			}

			return value	
			
	def button_view_partner_task(self, cr, uid, ids, context=None):
		if context is None:
			context = {}	
		for record in self.browse(cr, uid, ids, context=context):	
			partner_id=record.id 
			#obj = self.pool.get('sale.order')
			#view_id = self.pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'accout.invoice_tree')], limit=1) 	
			task_id = context.get('active_id', False)
			task_pool = self.pool.get('project.task')
			delegate_data = self.read(cr, uid, ids, context=context)[0]
			#delegated_tasks = task_pool.do_delegate(cr, uid, [task_id], delegate_data, context=context)
			models_data = self.pool.get('ir.model.data')

			action_model, action_id = models_data.get_object_reference(cr, uid, 'project', 'action_view_task')
			view_model, task_view_form_id = models_data.get_object_reference(cr, uid, 'project', 'view_task_form2')
			view_model, task_view_tree_id = models_data.get_object_reference(cr, uid, 'project', 'view_task_tree2')
			action = self.pool[action_model].read(cr, uid, [action_id], context=context)[0]
			#action['res_id'] = delegated_tasks[task_id]
			#action['view_id'] = False
			#action['views'] = [(task_view_form_id, 'form'), (task_view_tree_id, 'tree')]
			#action['help'] = False    
			value = {
				'type': 'ir.actions.act_window',
				'name': _('All Tasks'),
				'view_type': 'form',
				'view_mode': 'tree,form',
				'res_model': 'project.task',
				'domain':[('partner_id','=',partner_id)],
				'context':{'search_default_partner_id': partner_id},
				'view_id': False,
				
			}

			return value	
			

class dincelproject_project(osv.Model):
	_inherit = "project.project"	
	def _curr_status(self, cr, uid, ids, values, arg, context=None):
		x={}
		for record in self.browse(cr, uid, ids):
			_str=""
			sql="select status from dincelproject_status where project_id='%s' order by date desc limit 1" % (record.id)
			cr.execute(sql)
			rows = cr.fetchall()
			for row in rows:
				if(row[0]):
					_str = str(row[0])
			x[record.id] = _str
		return x
	_columns = {
		'x_category_id': fields.many2one('dincelproject.category', 'Category'),
		'x_scope': fields.text('Project Scope'),
		'x_status': fields.text('Status'),
		'x_dates': fields.text('Key Dates'),
		'x_impact': fields.char('$ Impact',size=50),
		'x_tracking': fields.selection([
			('ontrack', 'On Track'),
			('delay', 'Delayed'),
            ('hold', 'On Hold'),
			], 'Tracking'),
		'x_curr_status':fields.function(_curr_status,method=True,type='char',string='Current Status'),
		'x_previous': fields.text('Previous Status'),
		'x_next_stage': fields.text('Next Stage Action'),
		'x_status_ids': fields.one2many('dincelproject.status', 'project_id', string="Status"),
		}		
		
class dincelproject_category(osv.Model):
	_name	= "dincelproject.status"
	_order 	= 'date desc'	
	_columns = {
		'date':fields.date("Date"),
		'status': fields.text('Status'),
		'project_id': fields.many2one('project.project', 'Project'),
		}	
		
class dincelproject_category(osv.Model):
	_name="dincelproject.category"
	_columns = {
		'name': fields.char('Name',size=64),
		}				