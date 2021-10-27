import time
from functools import partial
from openerp.osv import osv
from openerp.report import report_sxw
import datetime
import dateutil.parser
import dateutil
#from common_report_header1 import common_report_header1
import logging
from datetime import timedelta
import calendar
from calendar import monthrange

_logger = logging.getLogger(__name__)

class stock_delivery_report1(report_sxw.rml_parse):
	
	def set_context(self, objects, data, ids, report_type=None):
		new_ids = ids
		res = {}
		return super(stock_delivery_report1, self).set_context(objects, data, new_ids, report_type=report_type)

	def __init__(self, cr, uid, name, context=None):
		super(stock_delivery_report1, self).__init__(cr, uid, name, context=context)
		self.localcontext.update( {
			'lines': self._get_details,
			'get_start_date': self._get_start_date,
			'get_end_date': self._get_end_date,
		})
		self.context = context
		
	def _get_start_date(self, form):
		if(form['form']['date']):
			return form['form']['date']
		else:
			return 'START'
			
	def _get_end_date(self, form):
		if(form['form']['date_to']):
			return form['form']['date_to']
		else:
			return datetime.date.today()
		
	
	def _get_details(self,context=None):
		sql = "SELECT x_dcs_group FROM product_template WHERE x_dcs_group in ('P110','P155','P200','P275') GROUP BY x_dcs_group ORDER BY x_dcs_group"
		#_logger.error("_get_details_1111" + str(sql))	
		self.cr.execute(sql)
		ret_res = self.cr.dictfetchall()
		#_logger.error("_get_details_1111" + str(ret_res))
		rows=[]
		dcs_group=""
		
		for row in ret_res:
			dcs_group = row['x_dcs_group']
			sp = dcs_group.split("P",1)
			prod_like = sp[1] + "P"
			
			
			
			sql="""SELECT sum(sl.ship_qty) as prod_qty, sl.product_id as prod_id, sl.order_length as prod_length, st.name, st.x_dcs_group, st.x_dcs_itemcode
			FROM dincelstock_pickinglist so INNER JOIN dincelstock_pickinglist_line sl ON so.id = sl.pickinglist_id 
			INNER JOIN product_template st ON st.id = sl.product_id
			WHERE st.x_dcs_itemcode like '"""+str(prod_like)+"""%'"""
			
			if (context['form']['date'] and context['form']['date_to']):
				date_from = context['form']['date']
				date_to =  context['form']['date_to']
				sql += """ AND so.date_picking between '"""+str(date_from)+"""' AND '"""+str(date_to)+"""'"""
				
			sql += """ group by st.x_dcs_group, st.x_dcs_itemcode, st.name, sl.product_id, sl.order_length 
			ORDER BY st.x_dcs_itemcode, st.name, sl.order_length"""
			#_logger.error("_get_details_0000" + str(sql) + str(context))
			
			self.cr.execute(sql)
			ret_res = self.cr.dictfetchall()
			
			for row in ret_res:
				row1={'dcs_group':dcs_group,
					'qty':row['prod_qty'],
					'name':row['name'], 
					'item_code':row['x_dcs_itemcode'],
					'prod_length':row['prod_length'],
				}
				rows.append(row1)	
		return rows #=self._get_details(_taxid,date_from,date_to)
		
class report_stock_delivery(osv.AbstractModel):
	_name = 'report.dincelstock.report_stock_delivery' #return self.pool['report'].get_action(cr, uid, [], 'account.report_tax_dcs', data=datas, context=context)
	_inherit = 'report.abstract_report'
	_template = 'dincelstock.report_stock_delivery' #.xml filename....
	_wrapped_report_class = stock_delivery_report1

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:	