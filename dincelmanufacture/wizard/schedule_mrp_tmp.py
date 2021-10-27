from datetime import date
#from openerp.addons.base_status.base_state import base_state
import time 
import datetime
from datetime import timedelta
import dateutil.parser
from openerp.osv import fields, osv
from openerp.tools.translate import _
import logging
import openerp.addons.decimal_precision as dp
_logger = logging.getLogger(__name__)
class dincelmrp_routing_schedule_tmp(osv.Model):
	_name = "dincelmrp.routing.schedule.tmp"
	_description="Routing Schedule"
		
	def _get_init_qty(self, cr, uid, context=None):
		return 1
		
	_columns = {
		'name':fields.char("Name"),
		'process_flag':fields.boolean("Process Flag"),
		'schedule_line': fields.one2many('dincelmrp.schedule.line', 'routing_schedule_id', 'Schedule Lines'),
		'qty':fields.float("Qty test"),
	}
	_defaults = {
		'qty': _get_init_qty,
		'process_flag': False,
		}	

	def on_change_processflag(self, cr, uid, ids, _flag,_lines, context=None):
		vals={}
		context = context or {}
		
		#amt = 0.0
		#amt_fee = 0.0 
		
		if _lines:
			
			line_ids = self.resolve_2many_commands(cr, uid, 'schedule_line', _lines, ['process_flag'], context)
			#_logger.error("error.mrpdone.update_order_dcsordercodevvvv"+str(_lines)+"]["+str(line_ids)+"]")
			for line in line_ids:
				if line:
					#if _flag:
					line['process_flag']= _flag
					#else:
					#	line['qty_curr_produce']= 0
					#_logger.error("updatelink_order_dcs.onchange_pay_lineslinelineleine2222["+str(line['qty_curr_produce'])+"]["+str(_isfull)+"]")		
			return {'value': {'schedule_line': line_ids}}
			
		return {'value':vals}
		
	def on_change_qty(self, cr, uid, ids, _qty,_name_grp, context=None):
		#_logger.error("on_change_qtyon_change_qtyproduceproduce["+str(context)+"]")
		if context is None:
			context = {}
		#record = self.browse(cr, uid, ids, context=context)
		#if _name:
		#	#_name=record.name
		#	raise osv.except_osv(_('Info'), _(str(_name)))
		if context and context.get('active_ids'):
			_ids=context.get('active_ids')
			#_name=context.get('name')
		_items=[]	
		if _name_grp:
			_speed=1.0
			_obj=self.pool.get('dincelsale.productsummary')
			_mids = _obj.search(cr, uid, [('code', '=', str("P"+_name_grp))], context=context)
			if _mids and _mids[0]:
				_obj=_obj.browse(cr, uid, _mids[0], context=context)
				if _obj.produce_speed and _obj.produce_speed > 0.0:
					_speed=_obj.produce_speed
					
			sql="select p.id from dincelmrp_production p,sale_order o where p.order_id=o.id and o.x_prod_status !='complete'"
			cr.execute(sql)
			rows 	= cr.dictfetchall()
			for row in rows:
				_id	 = row['id']
				_obj = self.pool.get('dincelmrp.production').browse(cr, uid, _id, context=context)
				_deli= _obj.order_id.x_del_status
				_prod= _obj.order_id.x_prod_status
				
				if _deli and _deli =="delivered":#in['delivered','part']:
					sql="select 1 from dincelstock_pickinglist where pick_order_id='%s'" %(_obj.order_id.id)
					#_logger.error("move2schedule.issue.x_del_status_sql_sql_sql ["+str(sql)+"] invalid even though no docket found...")	
					cr.execute(sql)
					rows 	= cr.fetchall()
					if len(rows)==0:
						_deli="" #reset to blank
						sql="update  sale_order set  x_del_status='' where id='%s'" %(_obj.order_id.id)
						cr.execute(sql)
						_logger.error("move2schedule.issue.x_del_status for ["+str(_obj.order_id.id)+"] invalid even though no docket found...")	
				#else:
				#	_deli=""
					
				if (_deli and _deli=="delivered") or (_prod and _prod=="complete"):
					_esc=True
				else:	
					sql="select 1 from dincelmrp_schedule where product='%s' and order_id='%s' " % (_name_grp, _obj.order_id.id)
					cr.execute(sql)
					rows1 	= cr.fetchall()
					if rows1 and len(rows1)>0:
						_esc=True#exists alreadyy
					else:
						_esc=False
					
				if _esc == False:
				
					if _name_grp=="110":
						if _obj.has_110:
							if _obj.status_110=="":
								add_queue,_item=self.get_item_row(cr, uid, ids, _obj,_name_grp,_speed, context)
								if add_queue:
									_items.append(_item)
					elif _name_grp=="155":
						if _obj.has_155:
							if _obj.status_155=="":
								add_queue,_item=self.get_item_row(cr, uid, ids, _obj,_name_grp,_speed, context)
								if add_queue:
									_items.append(_item)
					elif _name_grp=="200":
						if _obj.has_200:
							if _obj.status_200=="":
								add_queue,_item=self.get_item_row(cr, uid, ids, _obj,_name_grp,_speed, context)
								if add_queue:
									add_queue,_items.append(_item)
					elif _name_grp=="275":
						if _obj.has_275:
							if _obj.status_275=="":
								add_queue,_item=self.get_item_row(cr, uid, ids, _obj,_name_grp,_speed, context)
								if add_queue:
									_items.append(_item)
					#else:
				#	_logger.error("on_change_qtyon_change_qtypr_obj_obj["+str(_obj)+"]")
		
		#if _name_grp=="110":
		#	vals={'pq110_ids':_items}
		#elif _name_grp=="155":
		#	vals={'pq155_ids':_items}
		#elif _name_grp=="200":
		#	vals={'pq200_ids':_items}
		#elif _name_grp=="275":
		#	vals={'pq275_ids':_items}
		#	
		#else:
		vals= {}
		if len(_items)>0:
			#_items.sort(key=lambda item:item['date_deposit'], reverse=True)
			_items.sort(key=lambda item:item['date_deposit'])
		#	_items=_items.sort(key=lambda x: datetime.datetime.strptime(x['date_deposit'], '%Y-%m-%d'))
		#_logger.error("on_change_qtyon_change_qtypr___items_items["+str(_items)+"]")	
		vals['schedule_line']=_items
		return {'value':vals}	
	
	def get_start_xx(self, cr, uid, ids, dt1, dt2db, routing_id, context=None):
		dtnew1=dateutil.parser.parse(str(dt1))
		dt_ret=dt1
		if dt2db:
			dtnew2=dateutil.parser.parse(str(dt2db))
			if dtnew2>dtnew1:
				dt_ret=dt2db
			#else:
			#	dt_ret= dt2db
		sql ="select schedule_stop as dt from dincelmrp_schedule where route_id='%s' order by schedule_stop desc limit 1 " % (routing_id)
		cr.execute(sql)
		
		rows 	= cr.dictfetchall()
		for row in rows:
			dtmp=row['dt']
			
			if dtmp:
				dtnew2=dateutil.parser.parse(str(dt_ret))
				dtnew1=dateutil.parser.parse(str(dtmp))
				
				if dtnew1>dtnew2:
					dt_ret=dtmp
				
					
			#else:
			#dt_ret= dt2
		
		return dt_ret
		
	def get_start_init(self, cr,uid, ids, dt1, dt2db, routing_id, context=None):
		if not dt1:
			dt_from	= datetime.datetime.today()
		else:
			dt_from	= dateutil.parser.parse(str(dt1))
		if not dt2db:
			return dt_from
		else:	
			
			dt_ret = self.get_date_lowest_reverse(cr, uid, ids, dt_from, dt2db)
			
				
			sql ="select schedule_stop as dt from dincelmrp_schedule where route_id='%s' order by schedule_stop desc limit 1 " % (routing_id)
			cr.execute(sql)
			rows= cr.dictfetchall()	
			for row in rows:
				dtmp=row['dt']
				if dtmp:
					dt_ret = self.get_date_lowest_reverse(cr, uid, ids, dt_ret, dtmp)
		
			return dt_ret
	def get_date_lowest_reverse(self, cr, uid, ids, dt1, dt2, context=None):
		dtnew1 = dateutil.parser.parse(str(dt1))
		dtnew2 = dateutil.parser.parse(str(dt2))
		if dtnew2 > dtnew1:
			return dt2
		else:
			return dt1		
	def get_date_lowest(self, cr, uid, ids, dt1, dt2, context=None):
		dtnew1 = dateutil.parser.parse(str(dt1))
		dtnew2 = dateutil.parser.parse(str(dt2))
		if dtnew2 > dtnew1:
			return dt1
		else:
			return dt2
		
	def get_routes_init(self, cr, uid, ids, _grp, context=None):		
		_routes=[]
		dt_from	= datetime.datetime.today()
		sql ="select * from mrp_routing where x_default_prod='P%s'" % (_grp)
		cr.execute(sql)
		rows 	= cr.dictfetchall()
		for row in rows:
			vals={
				'routing_id':row['id'],
				'prod_group':row['x_default_prod'],
				'dt_from':self.get_start_init(cr,uid, ids, dt_from, row['x_default_start'],row['id']),
			  }
			_routes.append(vals)
			break
		return _routes	
		
	def _save_mrp_schedule(self,cr,uid,ids,planned,context=None):
		_obj=self.pool.get('dincelmrp.schedule')	
		record = self.browse(cr, uid, ids[0], context=context)
		if record.schedule_line:
			_grp 	= record.name
			
			#_routes	=	self.get_routes_init(cr, uid, ids, _grp)
				 
			_prev=None
			for line in record.schedule_line:
				priority		=line.priority
				date_request	=line.date_request
				_hrs		=line.hrs_order
				
				if line.process_flag:
					vals2={'production_id':line.production_id.id,
						  'order_id':line.order_id.id,
						  'partner_id':line.partner_id.id,
						  'project_id':line.project_id.id,
						  'product':_grp,
						  'len_order':line.len_order,
						  'hrs_order':_hrs,
						  'produce_speed':line.produce_speed,
						  'planned':planned,
						  'name':line.order_id.origin or line.order_id.name,
						  #'sequence_sort':'',
						}
					if line.date_deposit:
						vals2['date_deposit']=line.date_deposit
					if line.date_request:
						vals2['date_request']=line.date_request	
					
				
					_sch_id=_obj.create(cr, uid, vals2, context) #.create(vals, context)	
				
				
				
	def plan_production(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		self._save_mrp_schedule(cr,uid,ids,True,context=context)
		return True	
		
	def save_production(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		self._save_mrp_schedule(cr,uid,ids,False,context=context)
		return True		
		
	def save_productionxx(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		#_skips=[]	
		_obj=self.pool.get('dincelmrp.schedule')	
		record = self.browse(cr, uid, ids[0], context=context)
		if record.schedule_line:
			_grp 	= record.name
			
			_routes	=	self.get_routes_init(cr, uid, ids, _grp)
				 
			_prev=None
			for line in record.schedule_line:
				priority		=line.priority
				date_request	=line.date_request
				if line.process_flag:
					_hrs		=line.hrs_order
					#_routes, routing_id, dt_start, end_date = self.get_date_start(cr, uid, ids, _routes, _hrs,_prev)
					
					#_prev=routing_id
					vals2={'production_id':line.production_id.id,
						  'order_id':line.order_id.id,
						  'partner_id':line.partner_id.id,
						  'project_id':line.project_id.id,
						  'product':_grp,
						  'len_order':line.len_order,
						  'hrs_order':_hrs,
						  'name':line.order_id.origin or line.order_id.name,
						  #@#'sequence_sort':'',
						}
					if line.date_deposit:
						vals2['date_deposit']=line.date_deposit
					if line.date_request:
						vals2['date_request']=line.date_request	
					#if routing_id:	
					#	vals2['route_id']=routing_id
					#if dt_start:	
					#	vals2['schedule_start']=dt_start
					#if end_date:	
					#	vals2['schedule_stop']=end_date
				
					_sch_id=_obj.create(cr, uid, vals2, context) #.create(vals, context)	
					
				
		return True				
		
	def get_date_end(self,cr,uid,ids,dt_from,hrs):
		#end_date=dt_from
		_hrs1=0
		if hrs:
			_hrs1=float(str(hrs))
		if dt_from:
			dtnew		=dateutil.parser.parse(str(dt_from)) #dt_now 	= dateutil.parser.parse(str(dt_now))
		else:
			dtnew		= datetime.datetime.today()
		end_date 	=dtnew  + timedelta(hours=_hrs1)
		return end_date
		
	def get_date_start(self,cr,uid,ids,_routes,_hrs,_previd): #get_routing_ref
		routing_id	= None
		end_date	= None
		dt_start	= None
		if len(_routes)==1:
			routing_id	=	_routes[0]['routing_id']
			dt_start	=	_routes[0]['dt_from']
			end_date	=	self.get_date_end(cr,uid,ids,dt_start,_hrs)
			_routes[0]['dt_from']=end_date
		else:
			_tmp=None
			_tmp_start=None
			for _route in _routes:

				dt_start	=	_route['dt_from']
				end_date	=	self.get_date_end(cr,uid,ids,dt_start,_hrs)
				if _tmp==None:
					_tmp=end_date
					_tmp_start=dt_start
					routing_id	=	_route['routing_id']
				else:
					dt1=dateutil.parser.parse(str(_tmp))
					dt2=dateutil.parser.parse(str(end_date))
					if dt2<dt1:#take the least start line
						_tmp=end_date
						_tmp_start=dt_start
						routing_id	=	_route['routing_id']
			
			for _route in _routes:
				if str(routing_id)	==	str(_route['routing_id']):
					_route['dt_from']=_tmp
					end_date=_tmp
					dt_start=_tmp_start #todo...check if the date is weekend or repair etc...move to next date
		return _routes, routing_id, dt_start, end_date
		
	def get_item_row(self, cr, uid, ids, mrpid,_name_grp,_speed, context=None):
		vals={'order_id':mrpid.order_id.id,
			  'process_flag':False,
			  'color_code':mrpid.order_id.x_colorcode,
			  'order_code':mrpid.order_id.origin or mrpid.order_id.name,
			  'partner_id':mrpid.partner_id.id,
			  'project_id':mrpid.project_id.id,
			  'product':_name_grp,
			  'production_id':mrpid.id,
			  'notes':mrpid.order_id.x_note_request,
			  'date_deposit':'',
			  }
		dep_paid=False	
		del_status=mrpid.order_id.x_del_status
		add_queue=False	
		
		if mrpid.order_id.x_dt_request:
			vals['date_request']=mrpid.order_id.x_dt_request
				
		#if not del_status or del_status !="delivered":
		if mrpid.partner_id.x_mrp_exmpt or mrpid.partner_id.x_deposit_exmpt:
			dep_paid=True #all the mrp excemption...eg advance deposit payment customers like Dasco...
		#else:			
			
		if mrpid.order_id.x_deposit_exmpt or mrpid.order_id.x_dep_paid=="NA":
			vals['date_deposit']=self.pool.get('dincelstock.transfer').get_au_date(cr, uid,mrpid.order_id.date_order)
			dep_paid=True
		else:
			if mrpid.order_id.x_dep_paid=="paid":#i.id,,p.amount
				sql="""select v.date from 
					account_invoice i,dincelaccount_voucher_payline p,account_voucher v 
					where i.x_inv_type='deposit' and i.id=p.invoice_id and v.id =p.voucher_id and i.x_sale_order_id='%s'""" % (mrpid.order_id.id)
				cr.execute(sql)
				rows 	= cr.dictfetchall()
				for row in rows:
					vals['date_deposit']=row['date']
					dep_paid=True
			if dep_paid == False:
				_amount_total=mrpid.order_id.amount_total
				if _amount_total:
					_invoiced=0.0
					_amount_total= float(_amount_total)
					sql="select sum(amount_total) from account_invoice where x_sale_order_id='%s' and state not in('draft','close')" % (mrpid.order_id.id)
					cr.execute(sql)
					rows1 	= cr.fetchall()
					for row1 in rows1:
						if row1[0]:
							_invoiced	+= float(row1[0])
					_diff = _amount_total-_invoiced 
					if abs(_diff)<0.90:
						dep_paid	= True #eg even thought deposit invoice required...they invoice in full (one invoice only)....
				#else:
				#	
					#vals['date_deposit']=''
		if dep_paid:	
			
			sql="select m.x_order_qty,m.x_order_length,t.x_dcs_group,m.x_produced_qty from dincelmrp_production p,mrp_production m,product_template t, product_product d where p.id=m.x_production_id and t.id=d.product_tmpl_id and m.product_id=d.id and p.id='%s' and t.x_dcs_group='P%s'" % (mrpid.id,_name_grp)	 
			cr.execute(sql)
			rows 		= cr.dictfetchall()
			_total		= 0.0
			_total_done	= 0.0
			for row in rows:
				_qty		= row['x_order_qty']
				_qty_done	= row['x_produced_qty']
				_length		= row['x_order_length']
				_lm			= _qty*_length*0.001
				_lm_done	= _qty_done*_length*0.001
				_total	+=_lm
				_total_done	+=_lm_done
				
			_remain = _total-_total_done
			
			if _remain <= 0.0:
				add_queue = False
			else:
				add_queue = True
				vals['len_order']	= _total
				vals['hrs_order']	= _total/(_speed*60)
				vals['len_done']	= _total_done
				vals['hrs_done']	= _total_done/(_speed*60)
				vals['produce_speed']=_speed
			'''if _name_grp=="110":
			elif _name_grp=="155":
				vals={'pq155_ids':_items}
			elif _name_grp=="200":
				vals={'pq200_ids':_items}
			elif _name_grp=="275":
				vals={'pq275_ids':_items}'''
		if str(mrpid.partner_id.id)=="55517":		
			_logger.error("partner_idpartner_id.line_idsx_deposit_exmpt["+str(mrpid.partner_id.x_deposit_exmpt)+"]add_queue["+str(add_queue)+"]dep_paid["+str(dep_paid)+"]")	
		return add_queue, vals
		
class dincelmrp_schedule_line(osv.osv_memory):
	_name="dincelmrp.schedule.line"
	#_order = 'id desc' order_item as in dcs , for summary
	_columns={
		'name': fields.char('name'),
		'sequence':fields.integer('Sequence'),
		'production_id': fields.many2one('dincelmrp.production', 'Production Reference',ondelete='cascade',),
		'order_id': fields.many2one('sale.order','Order'),
		'routing_schedule_id': fields.many2one('dincelmrp.routing.schedule.tmp','Schedule'),
		'color_code': fields.related('order_id', 'x_colorcode', type='char', string='Color',store=False),
		'order_code': fields.related('order_id', 'origin', type='char', string='Order Code',store=False),
		'product': fields.char('Product Group'),
		'actual_start':fields.datetime('Actual Start'),
		'actual_stop':fields.datetime('Actual Stop'),
		'schedule_start':fields.datetime('Schedule Start'),
		'schedule_stop':fields.datetime('Schedule Stop'),
		'date_start':fields.datetime('StartX'),
		'date_stop':fields.datetime('StopX'),
		'date_request':fields.date('Date Request'),
		'date_deposit':fields.date('Date Deposit'),
		'notes': fields.char('Notes'),
		'is_start': fields.boolean('Is Start'),
		'len_order': fields.float('Ordered Length', digits=(16,2)),
		'hrs_order': fields.float('Hrs', digits=(16,2)),
		'produce_speed': fields.float('Prodction Speed', digits=(8,2)),
		'len_complete': fields.float('Completed Length', digits=(16,2)),
		'process_status': fields.char('Process Status'),
		'project_id': fields.many2one('res.partner','Project / Site'),	
		'partner_id': fields.many2one('res.partner','Customer'),	
		'route_id': fields.many2one('mrp.routing','Routing/Line'),	
		'progress':fields.float('Progress'),
		'process_flag':fields.boolean('Process Flag'),
		'priority': fields.selection([
			('3', '3'),
			('2', '2'),
			('1', '1'),
			('0', '0'),
			], 'Priority',select=True),	
		'state': fields.selection([
			('draft', 'Draft'),
			('done', 'Complete'),
			('part', 'Partial'),
			], 'Status',select=True),	
		}