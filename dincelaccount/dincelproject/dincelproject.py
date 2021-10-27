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