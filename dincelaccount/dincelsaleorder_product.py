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

	
class dincelaccount_saleorder_product(osv.Model):
	_name="dincelsaleorder.product"
	#_order = 'id desc' order_item as in dcs , for summary
	_columns={
		'name': fields.char('name'),
		'order_id': fields.many2one('sale.order','Order'),
		'color_code': fields.related('order_id', 'x_colorcode', type='char', string='Color',store=False),
		'product': fields.char('Product Group'),
		'date_start': fields.datetime('Start Date'),
		'date_stop': fields.datetime('Complete Date'),
		'is_start': fields.boolean('Is Start'),
		'len_order': fields.float('Ordered Length', digits=(16,2)),
		'len_complete': fields.float('Completed Length', digits=(16,2)),
		'process_status': fields.char('Process Status'),
		'project_id': fields.many2one('res.partner','Project / Site'),	
		'partner_id': fields.many2one('res.partner','Customer'),	
		'route_id': fields.many2one('mrp.routing','Routing/Line'),	
		'progress':fields.float('Progress'),
		'state': fields.selection([
			('draft', 'Draft'),
			('done', 'Complete'),
			('part', 'Partial'),
			], 'Status',select=True),	
		}
	

class dincelaccount_product_product(osv.Model):
	_inherit="product.product"	
	def find_deposit_product(self, cr, uid, context=None):
		if context is None: context = {}
		#result = []
		args = [("x_prod_cat", "=", "deposit")]
		result = self.search(cr, uid, args, context=context)
		return result
	def stock_value(self, cr, uid, _id, _len, _locid, context=None):
		sql="""select p.name_template,t.x_prod_type,p.product_tmpl_id,t.uom_id ,t.x_dcs_itemcode  
					from product_product p,product_template t 
					where p.product_tmpl_id=t.id and 
					p.id='%s'""" % (_id)
		cr.execute(sql)
		rows 	= cr.dictfetchall()
		for row in rows:
			dcs_itemcode = row['x_dcs_itemcode']
			if dcs_itemcode:
				dcs_itemcode=str(dcs_itemcode)
				_code=dcs_itemcode[-3:]
			else:
				_code=""
			#_logger.error("stock_valuep1stock_valuestock_valuesqlsql["+str(sql)+"]["+str(dcs_itemcode)+"]")
			
			if _code=="P-1":
				return self.stock_value_p1(cr, uid, _id, _locid, _len, context)
			else:
				return self.stock_value_acs(cr, uid, _id, _locid, context)
		return 0
	def stock_value_p1(self, cr, uid, _id, _locid, _len, context=None):	
		sql="""select sum(l.qty_in-l.qty_out) as bal 
				FROM 
				dincelstock_journal_line l,dincelstock_journal j,stock_location s,product_product p WHERE
				l.location_id=s.id AND l.product_id=p.id AND 
				l.journal_id=j.id AND 
				l.is_acs != 't' AND l.product_id='%s' AND l.location_id='%s'  AND l.prod_length='%s' """ %(_id, _locid, _len)
		#_logger.error("stock_value_p1stock_value_p1sqlsql["+str(sql)+"]")
		cr.execute(sql)
		rows 	= cr.dictfetchall()
		_total	= 0
		for row in rows:
			if row['bal']:
				_total += float(row['bal'])
		#_logger.error("stock_value_p1stock_value_p1_total["+str(_total)+"]["+str(_id)+"]_locid["+str(_locid)+"]_len["+str(_len)+"]")	
		return _total
		
	def stock_value_acs(self, cr, uid, _id, _locid, context=None):
		_obj=self.pool.get('stock.quant')
		domain1=[('location_id', '=', _locid),('product_id', '=', _id)]
		_newqty=0
		_qids=_obj.search(cr, uid, domain1, context=context)
		for item in _obj.browse(cr, uid, _qids, context=context):
			_newqty+=item.qty
		return _newqty
		
	def stock_value_acsxx(self, cr, uid, _id, _locid, context=None):
		sql = """SELECT 
				sum( d.qty - c.qty) AS bal
				FROM   (SELECT y.location_id,
					   y.product_id,
					   coalesce(a.qty, 0) qty
				FROM   (SELECT l.id location_id,
							   p.id product_id,
							   p.product_tmpl_id,
							   t.id temp_id,
							   t.type as p_type
						FROM   stock_location l,
							   product_product p,
							   product_template t WHERE p.product_tmpl_id = t.id  AND l.usage in ('internal','inventory')) y
					   LEFT JOIN (SELECT location_id,
										 product_id,
										 Sum(product_qty) qty
								  FROM   stock_move WHERE  state = 'done' AND location_id != '5'
								  GROUP  BY location_id,
											product_id) a
							  ON y.location_id = a.location_id
								 AND y.product_id = a.product_id AND y.p_type = 'product') c
						INNER JOIN (SELECT y.location_id,
								  y.product_id,
								  coalesce(b.qty, 0) qty
						   FROM   (SELECT l.id location_id,
										  p.id product_id,
										  p.product_tmpl_id,
										  t.id temp_id,
										  t.type as p_type
								   FROM   stock_location l,
										  product_product p,
										  product_template t WHERE p.product_tmpl_id = t.id AND l.usage in ('internal','inventory')) y
								  LEFT JOIN (SELECT location_dest_id,
													product_id,
													Sum(product_qty) qty
											 FROM   stock_move WHERE   state = 'done' AND location_dest_id != '5'
											 GROUP  BY location_dest_id,
													   product_id) b
										 ON y.location_id = b.location_dest_id
											AND y.product_id = b.product_id AND y.p_type = 'product') d
					   ON c.product_id = d.product_id
						  AND c.location_id = d.location_id
						  AND ( d.qty > 0
								 OR c.qty > 0 ) and c.location_id='%s' and c.product_id='%s' """ % (_locid, _id)
		cr.execute(sql)
		rows 	= cr.dictfetchall()
		_total=0
		for row in rows:
			if row['bal']:
				_total += float(row['bal'])
				
		return _total
	
	def stock_reserve_qty(self,cr, uid, _id, _locid, _len, _custom, context=None):
		sql="""select r.reserve_qty, r.product_id, r.order_length,p.order_id,o.origin,t.name_template,p.date_produce    
			from 
			dincelmrp_production_reserve r,dincelmrp_production p,sale_order o,product_product t 
			where r.production_id=p.id and p.order_id=o.id and r.product_id=t.id and o.x_del_status <>'delivered' and o.state not in ('done','cancel')
			and r.product_id='%s' and r.location_id='%s'""" % (_id, _locid)
		if _custom:
			sql+=" and r.order_length='%s'" % (_len)
		cr.execute(sql)
		rows 	= cr.dictfetchall()
		_total	= 0
		for row in rows:
			shipped=0
			order_id=row['order_id']
			reserve_qty=row['reserve_qty']
			sql="""select d.ship_qty,p.dcs_refcode,p.date_picking from 
					dincelstock_pickinglist p,dincelstock_pickinglist_line d,sale_order o 
					where p.pick_order_id=o.id and p.id=d.pickinglist_id and
						p.pick_order_id='%s' and d.product_id='%s' """ % (order_id, _id)
			if _custom:
				sql+=" and d.order_length='%s'"% (_len)
			
			
			cr.execute(sql)
			rows2 	= cr.dictfetchall()
		 
			for row2 in rows2:
				shipped+=row2['ship_qty']
				 
		
			_total +=reserve_qty- shipped
			
		return _total
			 