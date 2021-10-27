import time
from functools import partial
#from openerp.osv import osv
from openerp.osv import fields, osv
from openerp.report import report_sxw
#from common_report_header import common_report_header
#from common_report_header1 import common_report_header1
import datetime
import base64
import subprocess
from subprocess import Popen, PIPE, STDOUT
import logging
_logger = logging.getLogger(__name__)

#mo production quantity report
class dincelstock_stockreport(report_sxw.rml_parse):

	def __init__(self, cr, uid, name, context=None):
		super(dincelstock_stockreport, self).__init__(cr, uid, name, context=context)
		self.localcontext.update( {
			'lines': self._get_lines_stock,
			'lines_155': self._get_lines_155,
			'lines_200': self._get_lines_200,
			'lines_275': self._get_lines_275,
		})
		self.context = context 
	
 	def _get_lines(self, prod_id, prod):
		sql ="SELECT a.product_qty,a.state,a.product_id,a.name,a.x_order_length,a.x_sale_order_id,a.x_order_qty,  \
				a.x_pack_xtra,a.x_pack_20,a.x_pack_14,a.x_pack_10,a.x_pack_12, \
				b.name_template,c.x_dcs_itemcode \
				FROM  mrp_production a LEFT JOIN  product_product b ON a.product_id=b.id \
				LEFT JOIN product_template c ON b.product_tmpl_id = c.id \
				WHERE a.x_production_id='%s' AND c.x_dcs_group='%s' ORDER BY c.x_dcs_itemcode,a.x_order_length" 
		sql = sql % (str(prod_id), str(prod))
		
		self.cr.execute(sql)
		res = self.cr.dictfetchall()
		return res
		
	def _get_lines_stock(self, context):
		res = []
		if context.get('form', False) and context['form'].get('location_id', False):
			location_id= context['form']['location_id'][0]
			#//moved in (destination location)
			sql ="SELECT a.product_id ,a.product_qty,c.name \
					FROM  stock_move a LEFT JOIN  product_product b ON a.product_id=b.id \
					LEFT JOIN product_template c ON b.product_tmpl_id = c.id \
					WHERE a.location_dest_id='%s' AND a.state='done' AND c.x_prod_cat in('accessories','stocklength') order by c.name" 
			sql = sql % (str(location_id))
			
			self.cr.execute(sql)
			res1 = self.cr.dictfetchall()
			for row in res1:
				_pid=row['product_id']
				_qty=int(row['product_qty'])
				_name=row['name']
				#res[str(_pid)]=_qty
				vals = {"product_id": _pid, "name1": _name, "qty": _qty}
				res.append(vals)
			#for item in res1:
			#//moved out (source location)
			sql ="SELECT a.product_id ,a.product_qty,c.name \
					FROM  stock_move a LEFT JOIN  product_product b ON a.product_id=b.id \
					LEFT JOIN product_template c ON b.product_tmpl_id = c.id \
					WHERE a.location_id='%s' AND a.state='done' AND c.x_prod_cat in('accessories','stocklength') order by c.name" 
			sql = sql % (str(location_id))
			
			self.cr.execute(sql)
			res2 = self.cr.dictfetchall()	
			for row in res2:
				_pid=row['product_id']
				_qty=int(row['product_qty'])
				_name=row['name']
				for row1 in res:
					if row1['product_id']==_pid:
						row1['qty']=row1['qty']-_qty
						continue
				else:
					vals = {"product_id": _pid, "name1": _name, "qty": -_qty}
					res.append(vals)
			#_logger.error("print_reportprint_reportprint_report["+str(res)+"]")			
		return res
		
	def _get_lines_275(self, context):
		res = []
		if context.get('form', False):
			prod_id= context['form']['id'] 
			res = self._get_lines(prod_id, 'P275')
		return res
		
	def _get_lines_155(self, context):
		res = []
		if context.get('form', False):
			prod_id= context['form']['id'] 
			res = self._get_lines(prod_id, 'P155')
		return res

	def _get_lines_200(self, context):
		res = []
		if context.get('form', False):
			prod_id= context['form']['id'] 
			res = self._get_lines(prod_id, 'P200')
		return res	
		
class report_stockreport(osv.AbstractModel):
	_name = 'report.dincelstock.report_stockreport'
	_inherit = 'report.abstract_report'
	_template = 'dincelstock.report_stockreport' #///NOTE "dincelmanufacture"
	_wrapped_report_class = dincelstock_stockreport
	 
		
class dcsreport_stock_report(osv.osv_memory):
	_name = 'dcsreport.stock.report'
	_columns = {
		'location_id': fields.many2one('stock.location', 'By Location'),
		'product_id': fields.many2one('product.product', 'By Product', domain=[('sale_ok', '=', True)],),
		'date': fields.date('Date'),
		#'grid_loc': fields.boolean('Grid Location'),
		'date_to': fields.date('To Date'),
		'line_ids':fields.one2many('dcsreport.stock.report.line','dcsreport_id', 'Items'),
		'report_type':fields.selection([
			('acspacked', 'Packed Accessories'),
            ('stock', 'Stock Report Preview'),
			('stockvaluation', 'Stock Valuation by Location'),
			('stockvaluation_product', 'Stock Valuation by Product'),
			('sales_report', 'Accessories Sales Quantity Report'),
			('delivery_report', 'Delivered Quantity Report'),
            ], 'Report Type'), 
	}
	_defaults = {
		'date': fields.date.context_today, #lambda *a: time.strftime('%Y-%m-%d'),
		'date_to': fields.date.context_today, #lambda *a: time.strftime('%Y-%m-%d'),
	}
	
	def get_prodname(self,cr,uid,ids,prod_id,context =None):
		name=''
		sql="select t.name from product_template t,product_product p where p.product_tmpl_id=t.id and p.id='%s'" % (prod_id)
		cr.execute(sql)
		rows= cr.dictfetchall()
		for row in rows:
			name=row['name']
		return name	
	
	def onchange_product(self, cr, uid, ids, product_id, context=None):
		if context is None:
			context = {}
		new_lines=[]	
		vals={}
		_objres=self.pool.get("dincelmrp.production.reserve")
		prod=self.pool.get("product.product")
		if product_id:
			sql="""select l.location_id,l.product_id,l.prod_length,sum(l.qty_in-l.qty_out) as net 
				FROM 
				dincelstock_journal_line l,dincelstock_journal j,stock_location s,product_product p WHERE
				l.location_id=s.id AND l.product_id=p.id AND 
				l.journal_id=j.id AND s.usage='internal' AND 
				l.is_acs != 't' and l.product_id='%s' group by l.location_id,l.product_id,l.prod_length"""	 % (product_id)
			cr.execute(sql)
			rows= cr.dictfetchall()
			for row in rows:
				location_id=row['location_id']
				prod_length=row['prod_length']
				qty_net=row['net']
				if qty_net and abs(qty_net)>0:#show > zero and negatives.... No zeros....
					pname=self.get_prodname(cr,uid,ids,product_id,context)
					qty_reserve		=	_objres.qty_reserved_total( cr, uid, product_id, location_id, prod_length)
					vals={'location_id':location_id,'product':pname,'product_id':product_id,'prod_length':prod_length,'qty_stock':qty_net,'custom':True,'qty_reserve':qty_reserve}
					new_lines.append(vals)
			_obj=self.pool.get('stock.quant')
			domain1=[('product_id', '=', product_id)]
			_qids=_obj.search(cr, uid, domain1, context=context)
			for item in _obj.browse(cr, uid, _qids, context=context):
				if item.product_id.x_prod_type and item.product_id.x_prod_type =="acs":
					if item.location_id.usage == "internal":
						_found=False
						location_id=item.location_id.id 
						for line in new_lines:
							if line['location_id']==location_id:
								_newqty=line['qty_stock']+item.qty
								qty_reserve		=prod.stock_reserve_qty(cr, uid, item.product_id.id, location_id, False, False, context=context)
								line.update ( {'qty_stock': _newqty,'qty_reserve': qty_reserve  } ) 
								_found=True
								
						if _found == False:
							#qty_reserve		= _objres.qty_reserved_total( cr, uid, item.product_id.id, location_id, False)
							pname=self.get_prodname(cr,uid,ids,item.product_id.id,context)
							qty_reserve		=prod.stock_reserve_qty(cr, uid, item.product_id.id, location_id, False, False, context=context)
							vals={'location_id':location_id,'product':pname,'product_id':item.product_id.id,'prod_length':item.product_id.x_stock_length,'qty_stock':item.qty,'custom':False,'qty_reserve':qty_reserve}
							new_lines.append(vals)
						
			if len(new_lines)>0:
				new_lines.sort(key=lambda item:item['location_id'])
			vals= {'line_ids': new_lines}	
		return {'value':vals}
		
	def onchange_location(self, cr, uid, ids, location_id, context=None):
		if context is None:
			context = {}
		new_lines=[]	
		vals={}
		_objres=self.pool.get("dincelmrp.production.reserve")
		prod=self.pool.get("product.product")
		if location_id:
			sql="""select l.product_id,l.prod_length,sum(l.qty_in-l.qty_out) as net 
				FROM 
				dincelstock_journal_line l,dincelstock_journal j,stock_location s,product_product p WHERE
				l.location_id=s.id AND l.product_id=p.id AND 
				l.journal_id=j.id AND 
				l.is_acs != 't' and l.location_id='%s' group by l.product_id,l.prod_length"""	 % (location_id)
			cr.execute(sql)
			rows= cr.dictfetchall()
			for row in rows:
				product_id=row['product_id']
				prod_length=row['prod_length']
				qty_net=row['net']
				if qty_net and abs(qty_net)>0:#show > zero and negatives.... No zeros....
					pname=self.get_prodname(cr,uid,ids,product_id,context)
					qty_reserve		=	_objres.qty_reserved_total( cr, uid, product_id, location_id, prod_length)
					vals={'location_id':location_id,'product':pname,'product_id':product_id,'prod_length':prod_length,'qty_stock':qty_net,'custom':True,'qty_reserve':qty_reserve}
					new_lines.append(vals)
			
			_obj=self.pool.get('stock.quant')
			domain1=[('location_id', '=', location_id)]
			_qids=_obj.search(cr, uid, domain1, context=context)
			for item in _obj.browse(cr, uid, _qids, context=context):
				if item.product_id.x_prod_type and item.product_id.x_prod_type =="acs":
					_found=False
					for line in new_lines:
						if line['product_id']==item.product_id.id:
							_newqty=line['qty_stock']+item.qty
							qty_reserve		=prod.stock_reserve_qty(cr, uid, item.product_id.id, location_id, False, False, context=context)
							line.update ( {'qty_stock': _newqty,'qty_reserve': qty_reserve  } ) 
							_found=True
							
					if _found == False:
						#qty_reserve		= _objres.qty_reserved_total( cr, uid, item.product_id.id, location_id, False)
						pname=self.get_prodname(cr,uid,ids,item.product_id.id,context)
						qty_reserve		=prod.stock_reserve_qty(cr, uid, item.product_id.id, location_id, False, False, context=context)
						vals={'location_id':location_id,'product':pname,'product_id':item.product_id.id,'prod_length':item.product_id.x_stock_length,'qty_stock':item.qty,'custom':False,'qty_reserve':qty_reserve}
						new_lines.append(vals)
			#for line in new_lines:
			#	if not line['custom']:
			#		qty_reserve		= _objres.qty_reserved_total( cr, uid, line['product_id'], location_id, None)
			#		_newqty=line['qty_stock']-qty_reserve
			#		line.update ( {'qty_stock': _newqty } ) 
			if len(new_lines)>0:
				new_lines.sort(key=lambda item:item['product'])
			vals= {'line_ids': new_lines}	
		return {'value':vals}
	
	def print_report_stock(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		_id=ids[0]	
		obj = self.browse(cr, uid, ids[0], context=context)
		if obj.report_type:
			report_type=obj.report_type
		else:
			report_type="acspacked"
		if (report_type == "sales_report"):
			datas = {'ids': context.get('active_ids', [])}
			datas['form']  = self.read(cr, uid, ids, context=context)[0]

			for field in datas['form'].keys():
				if isinstance(datas['form'][field], tuple):
					datas['form'][field] = datas['form'][field][0]
			#_logger.write("dcs_create_stock_value_77777111 : " + str(datas))
			
			#return self.pool['report'].get_action(cr, uid, [], data=datas, context=context)
			return self.pool['report'].get_action(cr, uid, [], 'dincelstock.report_stock_value', data=datas, context=context)
			#return self.pool['report'].get_action(cr, uid, [], 'account.report_tax_statement', data=datas, context=context)
		elif(report_type == "delivery_report"):
			datas = {'ids': context.get('active_ids', [])}
			datas['form']  = self.read(cr, uid, ids, context=context)[0]

			for field in datas['form'].keys():
				if isinstance(datas['form'][field], tuple):
					datas['form'][field] = datas['form'][field][0]
			return self.pool['report'].get_action(cr, uid, [], 'dincelstock.report_stock_delivery', data=datas, context=context)
		else:
		
			url=self.pool.get('dincelaccount.config.settings').report_preview_url(cr, uid, ids, report_type, _id, context=context)	
			if url:
				url=url.replace("erp.dincel.com.au/", "localhost/")
				url += "&dt=" + (obj.date)
				'''return {
					  'name'     : 'Go to website',
					  'res_model': 'ir.actions.act_url',
					  'type'     : 'ir.actions.act_url',
					  'view_type': 'form',
					  'view_mode': 'form',
					  'target'   : 'current',
					  'url'      : url,
					  'context': context
				   }	'''
				fname="report_%s.pdf" % (report_type)#+str(report_type)+str(obj.id)+".pdf"
				save_path="/var/tmp/odoo/stock"
				
				process=subprocess.Popen(["wkhtmltopdf", 
							'--margin-top','1', 
							'--margin-left','1', 
							'--margin-right','1', 
							'--margin-bottom','1', url, save_path+"/"+fname],stdin=PIPE,stdout=PIPE)
				
				out, err = process.communicate()
				if process.returncode not in [0, 1]:
					raise osv.except_osv(_('Report (PDF)'),
										_('Wkhtmltopdf failed (error code: %s). '
										'Message: %s') % (str(process.returncode), err))
				
				return {
						'name': 'Load Sheet',
						'res_model': 'ir.actions.act_url',
						'type' : 'ir.actions.act_url',
						'url': '/web/binary/download_file?model=sale.order&field=datas&id=%s&path=%s&filename=%s' % (str(obj.id),save_path,fname),
						'context': context}   
	
	def preview_stock_report(self, cr, uid, ids, context=None):
		return self._preview_report(cr, uid, ids, 'stock')
	def preview_stock_valuation(self, cr, uid, ids, context=None):
		return self._preview_report(cr, uid, ids, 'stockvaluation')
	def preview_stock_produced(self, cr, uid, ids, context=None):
		return self._preview_report(cr, uid, ids, 'produced')
	
	def _preview_report(self, cr, uid, ids, report, context=None):
		if context is None:
			context = {}
		_id=''		
		'''if(report == 'stock'):
			report_type = "stock&dtl=1"
		if(report == 'valuation'):
			report_type = "stockvaluation&dtl=1&dt=%s" % (datetime.datetime.today().strftime('%Y-%m-%d'))
		if(report == 'produced'):
			report_type = "produced&dtl=1&except=custom"
		'''	
		url=self.pool.get('dincelaccount.config.settings').report_preview_url(cr, uid, ids, report, _id, context=context)
		if(report == 'stock'):
			url += "&dtl=1"
		if(report == 'stockvaluation'):
			url += "&dtl=1&dt=%s" % (datetime.datetime.today().strftime('%Y-%m-%d'))
		if(report == 'produced'):
			url += "&dtl=1&except=custom"
		return {
				  'name'     : 'Go to website',
				  'res_model': 'ir.actions.act_url',
				  'type'     : 'ir.actions.act_url',
				  'view_type': 'form',
				  'view_mode': 'form',
				  'target'   : 'current',
				  'url'      : url,
				  'context': context
			}
			
	def print_report(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		datas = {'ids': context.get('active_ids', [])}
	 
		datas['form']  = self.read(cr, uid, ids, context=context)[0]
		#_logger.error("print_reportprint_reportprint_report["+str(datas['form'])+"]")	
		return self.pool['report'].get_action(cr, uid, [], 'dincelstock.report_stockreport', data=datas, context=context)			
	'''	
	def dcs_aging_report_pdf(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		datas = {'ids': context.get('active_ids', [])}
	 
		datas['form']  = self.read(cr, uid, ids, context=context)[0]

		return self.pool['report'].get_action(cr, uid, [], 'account.report_partner_aging_pdf', data=datas, context=context)		'''
		
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
class dcsreport_stock_report_line(osv.osv_memory):
	_name = "dcsreport.stock.report.line"
	_columns = {
		'dcsreport_id': fields.many2one('dcsreport.stock.report', 'Reference'),
		'location_id': fields.many2one('stock.location', 'Location'),
		'product_id': fields.many2one('product.product', 'Product'),
		'prod_length':fields.integer('Length'),
		'qty_stock': fields.integer("Stock Qty"),	
		'qty_reserve': fields.integer("Stock Reserve"),	
		'custom': fields.boolean("Is Custom"),	
		'product':fields.char('Product'),
		}
		