from openerp.osv import fields, osv
import datetime
import dateutil.parser
from datetime import timedelta
from openerp.tools.translate import _
import logging
_logger = logging.getLogger(__name__)

PROD_GROUP_SELECTION =[
	('none', 'None'),
	('P110', '110mm'),
	('P155', '155mm'),
	('P200', '200mm'),
	('P275', '275mm'),
	('stock', 'Stock'),
	('acs', 'Accessories'),
	]	
WEEK_SELECTION=[
	('mon','MON'),
	('tue','TUE'),
	('wed','WED'),
	('thu','THU'),
	('fri','FRI'),
	('sat','SAT'),
	('sun','SUN'),
	]
		
class dincelmrp_schedule(osv.Model):
	_name="dincelmrp.schedule"
	_order = 'schedule_start, sequence_sort'# order_item as in dcs , for summary #sequence_print,
	#_order = 'id desc' order_item as in dcs , for summary
	
	def _hrs_remain(self, cr, uid, ids, values, arg, context):
		x={}
		for record in self.browse(cr, uid, ids):
			_rem	=record.len_remain
			_speed	=record.produce_speed
			if not _speed or _speed==0:
				_speed=1.0
			_hrs	=round((_rem/(_speed*60)), 2) 
			x[record.id]=_hrs
		return x	
		
	def _len_remain(self, cr, uid, ids, values, arg, context):
		x={}
		for record in self.browse(cr, uid, ids):
			_rem=record.len_order
			if record.len_complete:
				_rem-=record.len_complete
			x[record.id]=_rem
		return x	
	def _late_prod(self, cr, uid, ids, values, arg, context):
		x={}
		for record in self.browse(cr, uid, ids):
			_ant_date = record.x_dt_anticipate
			_sch_date = record.schedule_stop
			
			if(_ant_date):
				if _ant_date < _sch_date:
					x[record.id] = '1'
				else:
					x[record.id] = '0'
			else:
				x[record.id] = '0'
		return x	
	def _late_anticipate(self, cr, uid, ids, values, arg, context):
		x={}
		for record in self.browse(cr, uid, ids):
			_ant_date = record.x_dt_anticipate
			_req_date = record.x_dt_request
			
			if(_req_date):
				if  _req_date < _ant_date:
					x[record.id] = '1'
				else:
					x[record.id] = '0'
			else:
				x[record.id] = '0'
		return x
		
	_columns={
		'name': fields.char('name'),
		'production_id': fields.many2one('dincelmrp.production', 'Production Reference',ondelete='cascade',),
		'order_id': fields.many2one('sale.order','Order'),
		'routing_schedule_id': fields.many2one('dincelmrp.routing.schedule','Schedule'),
		'color_code': fields.related('order_id', 'x_colorcode', type='char', string='Color',store=False),
		'order_code': fields.related('order_id', 'origin', type='char', string='Order Code',store=False),
		'note_request': fields.related('order_id', 'x_note_request', type='char', string='Note Request Date',store=False),
		'x_dt_anticipate': fields.related('order_id', 'x_dt_anticipate', type='date', string='Anticipate Date',store=False),
		'x_dt_request':fields.related('order_id', 'x_dt_request', type='date', string='Requested Date',store=False),
		'x_late_production': fields.function(_late_prod, method=True, string='Late Production?',type='char', store=False), #Red for late production
		'x_late_anticipate': fields.function(_late_anticipate, method=True, string='Late Anticipate?',type='char', store=False), #Red for late anticipate
		'product': fields.char('Product Group'),
		'part_no':fields.integer('Part', size=2), #1,2,3,...
		'actual_start':fields.datetime('Actual Start'),
		'actual_stop':fields.datetime('Actual Stop'),
		'schedule_start':fields.datetime('Schedule Start'),
		'schedule_stop':fields.datetime('Schedule Stop'),
		#'date_start':fields.datetime('StartX'),
		#'date_stop':fields.datetime('StopX'),
		'date_request':fields.date('Date Request'),
		'date_deposit':fields.date('Date Deposit'),
		'date_anticipate':fields.date('Date Anticipate'),
		#'priority':fields.integer('Priority'),
		'is_start': fields.boolean('Is Start'),
		'len_order': fields.float('Ordered Length', digits=(16,2)),
		'len_remain': fields.function(_len_remain, method=True, string='Remain L/M',type='float', digits=(16,2)),
		'hrs_remain': fields.function(_hrs_remain, method=True, string='Remain Hrs',type='float', digits=(16,2)),
		'hrs_order': fields.float('Hrs', digits=(16,2)),
		'len_complete': fields.float('Completed Length', digits=(16,2)),
		'produce_speed': fields.float('Prodction Speed', digits=(8,2)),
		'process_status': fields.char('Process Status'),
		'project_id': fields.many2one('res.partner','Project / Site'),	
		'partner_id': fields.many2one('res.partner','Customer'),	
		'route_id': fields.many2one('mrp.routing','Routing/Line'),	
		'progress':fields.float('Progress'),
		'process_flag':fields.boolean('Process Flag'), #default False...if true then pending the start/end calculation...after set to 
		'date_flag':fields.boolean('Date Flag'), #start/end date flag
		'line_flag':fields.boolean('Routing Flag'), #routing line flag
		'delete_flag':fields.boolean('Delete Flag'),
		'date_print':fields.date('Date Printed'),
		'planned':fields.boolean('Planned Only?'),
		'schedule_line': fields.one2many('mrp.production', 'x_schedule_id', 'Schedule Lines'),
		'sequence_print':fields.integer('Sequence Print'), #print sequence given to the 
		'sequence_sort':fields.integer('SN'),
		'week_sn':fields.integer("Week"),
		'due_by': fields.selection([
			('', 'Undefined'),
			('tba', 'ASAP'),
			('wk1', 'Week 1'),
			('wk2', 'Week 2-4'),
			('wk4', 'Week 4-8'),
			('wk8', 'Week 8+'),
			], 'Due By',select=True),	
		'priority': fields.selection([
			('3', '3'),
			('2', '2'),
			('1', '1'),
			('0', '0'),
			], 'Priority',select=True),	
		'stage': fields.selection([
			('scheduled', 'Scheduled'),	
			('planned', 'Planned'),	
			('preplan', 'Pending Planned'),	
			], 'Stage',select=True),	
		'state': fields.selection([
			('draft', 'Draft'),
			('pending', 'Pending'), 	#pending to be printing/queue
			('queue', 'Queue'), 		#queue ed for production
			('done', 'Completed'), 		#production complete but has to be in schdule until closed...for just in case if needed to be displayed in gantt chart
			('closed', 'Closed'), 		#production complete and closed
			('cancel', 'Cancelled'), 	#production Cancelled
			('part', 'Partial'),
			('printed', 'Printed'),
			('confirmed','Confirmed'),
			], 'Status',select=True),	
		}
	_defaults = {
		'sequence_print': 0,
		'produce_speed':1,
		'part_no':1,
		'state':'draft',
		'due_by':'',
		'process_flag':False,
		'date_flag':False,
		'line_flag':False,
		'delete_flag':False,
		'planned':False,
		'post_planned':False,
		}
		
	def unlink(self, cr, uid, ids, context=None, check=True):
		context = dict(context or {})
		if context is None:
			context = {}
		for record in self.browse(cr, uid, ids):
			if record.schedule_start and record.schedule_stop:
				raise osv.except_osv(_('Error'), _('You cannot delete the item with start/end date assigned. Try reseting the dates first.'))#Warning(_())
			if record.state and record.state in ['part','done']: 
				raise osv.except_osv(_('Error'), _('You cannot delete schedule after it has been produced partially or in full.'))#Warning(_())  
			elif record.state and record.state == "printed": 	
				sql ="UPDATE sale_order set x_prod_status='' where x_prod_status='printed' and id='%s'" %(str(record.order_id.id))
				cr.execute(sql)
				#_logger.error("updatelink_sqlsqlsql["+str(sql)+"]")	
		result = super(dincelmrp_schedule, self).unlink(cr, uid, ids, context)
		return result
		
	def confirm_with_client(self, cr, uid, ids, context=None):	
		for record in self.browse(cr, uid, ids):
			sql = "update dincelmrp_schedule set state = 'confirmed' where id='%s'" %(record.id)
			cr.execute(sql)
			if record.order_id:
				self.pool.get('sale.order').order_produced_check(cr, uid, ids, record.order_id.id, context=context)
		return True
		
	def make_a_draft(self, cr, uid, ids, context=None):	
		for record in self.browse(cr, uid, ids):
			sql = "update dincelmrp_schedule set state = 'draft' where id='%s'" %(record.id)
			cr.execute(sql)
			if record.order_id:
				self.pool.get('sale.order').order_produced_check(cr, uid, ids, record.order_id.id, context=context)
		return True
		
	def button_calculate_estdates(self, cr, uid, ids, context=None):
		_obj=self.browse(cr,uid,ids[0],context=context)
		week_sn=_obj.week_sn
		product=_obj.product
		_lines=self.get_lines_info(cr, uid, ids, week_sn, product, None, context=context)
		if len(_lines)==0:
			raise osv.except_osv(_("Error!"), _("No any line routing configured for this product for week %s." % (week_sn)))
		
		planned="t"
		_items = self.get_items_byweek(cr, uid, ids,week_sn, product, planned, context=context)
		for _item in _items:
			idid=_item['id'];
			
		
			_start,_stop,_lineid, _lines=self.calculate_planned_dates(cr, uid, ids,_lines, _item, context=context)
		
			
			sql="""update dincelmrp_schedule set schedule_start='%s',schedule_stop='%s',route_id='%s' 
					,date_flag='f' 
					where id='%s' """ % (_start,_stop,_lineid, idid)
			cr.execute(sql)
		return True
	
	
	def get_items_byweek(self, cr, uid, ids, week_sn, product, planned="t",context=None):	
		
		_items=[]
		str_wk=""
		if planned=="t" and week_sn:
			str_wk=" and s.week_sn='%s'  " % (week_sn)
		#else:
		#	cstr=""
		cstr="and s.date_flag='t'  " #always.....
		sql="""select s.*,o.origin from dincelmrp_schedule s, sale_order o where
				s.order_id=o.id %s and
				s.product='%s' and s.state not in ('closed','cancel','done') and 
				s.planned='%s'  %s order by s.sequence_sort""" % (cstr, product, planned, str_wk)
		cr.execute(sql)
		rows 	= cr.dictfetchall()
		for row in rows:
			id	 		 = row['id']
			partner_id	 = row['partner_id']
			sequence_sort= row['sequence_sort']
			hrs_order	 = row['hrs_order']
			order_id	 = row['order_id']
			produce_speed=row['produce_speed']
			len_order	 = row['len_order']
			len_complete = row['len_complete']
			if not len_complete:
				len_complete=0
			state		 = row['state']
			len_remain	 = float(len_order)-float(len_complete)
			hrs_remain	 = round((len_remain/(produce_speed*60)),2)
			
			val={'id':id,
				'partner_id':partner_id,
				'sequence_sort':sequence_sort,
				'hrs_order':hrs_order,
				'len_remain':len_remain,
				'hrs_remain':hrs_remain,
				'order_id':order_id,
				'state':state,
				}
			_items.append(val)
		
		return _items
			
	def change_dt_request(self, cr, uid, ids, context=None):	
		return False
		
	def get_product_info(self, cr, uid, ids, product, context=None):
		produce_speed=1.0
		sql="select produce_speed from dincelsale_productsummary where code='P%s' and type='product'" % (product)
		cr.execute(sql)
		rows 	= cr.dictfetchall()
		for row in rows:
			produce_speed	 = float(row['produce_speed'])
		return produce_speed
	#for active week	
	def get_lines_info_active(self, cr, uid, ids, product, dt_from, context=None):	
		_lines=[]
		sql		= "select * from mrp_routing where x_default_prod='P%s'" % (product)
		cr.execute(sql)
		rows 	= cr.dictfetchall()
		for row in rows:
			routing_id		= row['id']
			default_start	= row['x_default_start']
			#default_start=dateutil.parser.parse(str(default_start))
			strt=default_start
			if dt_from:
				strt=dt_from
			#open_hr	=row['x_open_hr']
			#close_hr	=row['x_close_hr']
			#open_day	=str(row['x_open_day']).lower()
			#close_day	=str(row['x_close_day']).lower()
			#default_prod=row['x_default_prod']
			val={'routing_id':routing_id,'product':product,'start_date':strt}
			_lines.append(val)
			
		return _lines
		
	#for planned weeks....	
	def get_lines_info(self, cr, uid, ids, week_sn, product, start_dt=None, context=None):
		_lines=[]
	
		today	= fields.date.context_today(self,cr,uid,context=context)
		today	= dateutil.parser.parse(str(today))
		dt 		= "%s %s" % (today.year, week_sn)
		strt 	= str(datetime.datetime.strptime(dt + ' 1', "%Y %W %w"))
		#strt	= dateutil.parser.parse(str(strt))
		#----------------------------------------------------
		#hardcoded 10am ....later....read from database...GMT time sotred...(+10 is assumed)
		strt 	= "%s %s" % (strt[:10], "00:00:00")#datetime.datetime.strptime(str(strt), "%Y-%m-%d 10:00:00")
		if start_dt:
			strt=start_dt
		sql="select * from dincelmrp_routing_available where active='t' and dt_week='%s' and dt_year='%s' and prod_group='P%s'" % (week_sn, today.year, product)
		cr.execute(sql)
		rows 	= cr.dictfetchall()
		for row in rows:
			routing_id=row['routing_id']
			val={'routing_id':routing_id,'product':product,'start_date':strt}
			_lines.append(val)
			
		return _lines
		
	def calculate_planned_dates(self, cr, uid, ids, _lines, _item, context=None):
		lowest		= None
		lineid		= None
		start_dt	= None
		end_date	= None
		job_minutes = 0
		
		#get lowesest/first available line
		for line in _lines:
			if lowest:
				dtnew=line['start_date']
				lowest=dateutil.parser.parse(str(lowest))
				dtnew=dateutil.parser.parse(str(dtnew))
				if dtnew < lowest:
					lowest	=dtnew
					lineid	=line['routing_id']
			else:
				lowest		=line['start_date']
				lineid		=line['routing_id']
				
		if lineid:
			#start_dt	= lowest
			#job_hrs		= _item['hrs_order']
			hrs_remain		= _item['hrs_remain']
			#job_minutes	= int(job_hrs*60)
			job_minutes	= int(hrs_remain*60)
			start_dt=dateutil.parser.parse(str(lowest))
			end_date	= start_dt + datetime.timedelta(minutes=job_minutes)
		
		for line in _lines:
			if lineid and lineid==line['routing_id']:
				line['start_date']=end_date #set new start date for the line
		_logger.error("calculate_planned_dates start_dt[%s]end_date[%s][%s]" % (start_dt, end_date, lineid))		
		return start_dt, end_date, lineid, _lines
		
		
class dincelmrp_routing_schedule(osv.Model):
	_name = "dincelmrp.routing.schedule"
	_description="Routing Schedule"
		
	def _get_init_qty(self, cr, uid, context=None):
		return 1
		
	_columns = {
		'name':fields.char("Name"),
		'schedule_line': fields.one2many('dincelmrp.schedule', 'routing_schedule_id', 'Schedule Lines'),
		'pq110_ids' : fields.many2many('dincelmrp.production', 'rel_mrp_routing_schedule', 'production_id', 'route_schedule_id', string = "PQ 110mm"),
		'pq155_ids' : fields.many2many('dincelmrp.production', 'rel_mrp_routing_schedule', 'production_id', 'route_schedule_id', string = "PQ 155mm"),
		'pq200_ids' : fields.many2many('dincelmrp.production', 'rel_mrp_routing_schedule', 'production_id', 'route_schedule_id', string = "PQ 200mm"),
		'pq275_ids' : fields.many2many('dincelmrp.production', 'rel_mrp_routing_schedule', 'production_id', 'route_schedule_id', string = "PQ 275mm"),
		'qty':fields.float("Qty test"),
	}
	_defaults = {
		'qty': _get_init_qty,
		}	

		
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
				if _obj.produce_speed and _obj.produce_speed>0.0:
					_speed=_obj.produce_speed
					
			sql="select p.id from dincelmrp_production p,sale_order o where p.order_id=o.id and o.x_prod_status !='complete'"
			cr.execute(sql)
			rows 	= cr.dictfetchall()
			for row in rows:
				_id	 = row['id']
				_obj = self.pool.get('dincelmrp.production').browse(cr, uid, _id, context=context)
				if _name_grp=="110":
					if _obj.has_110:
						if _obj.status_110=="":
							dep_paid,_item=self.get_item_row(cr, uid, ids, _obj,_name_grp,_speed, context)
							if dep_paid:
								_items.append(_item)
				elif _name_grp=="155":
					if _obj.has_155:
						if _obj.status_155=="":
							dep_paid,_item=self.get_item_row(cr, uid, ids, _obj,_name_grp,_speed, context)
							if dep_paid:
								_items.append(_item)
				elif _name_grp=="200":
					if _obj.has_200:
						if _obj.status_200=="":
							dep_paid,_item=self.get_item_row(cr, uid, ids, _obj,_name_grp,_speed, context)
							if dep_paid:
								dep_paid,_items.append(_item)
				elif _name_grp=="275":
					if _obj.has_275:
						if _obj.status_275=="":
							dep_paid,_item=self.get_item_row(cr, uid, ids, _obj,_name_grp,_speed, context)
							if dep_paid:
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
	
	def save_production(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		_obj=self.pool.get('dincelmrp.schedule')	
		record = self.browse(cr, uid, ids[0], context=context)
		if record.schedule_line:
			_grp 	= record.name
			_routes	= []
			#_logger.error("save_productionsave_production_grp["+str(_grp)+"]")	
			dt_from		= datetime.datetime.today()
			sql ="select * from dincelmrp_routing_available where prod_group='P%s' and active='t' and dt_from >'%s'" % (str(_grp),str(dt_from))
			cr.execute(sql)
			rows 	= cr.dictfetchall()
			for row in rows:
				vals={
						'routing_id':row['routing_id'],
						'prod_group':row['prod_group'],
						'dt_from':row['dt_from'],
					  }
				_routes.append(vals)
				
			for line in record.schedule_line:
				priority		=line.priority
				date_request	=line.date_request
				if line.process_flag:
					_hrs		=line.hrs_order
					routing_id, dt_start, end_date = self.get_routing_ref(cr, uid, ids, _routes, _hrs)
					if routing_id:
						vals2={'production_id':line.production_id.id,
							  'order_id':line.order_id.id,
							  'partner_id':line.partner_id.id,
							  'project_id':line.project_id.id,
							  'schedule_start':dt_start,
							  'schedule_stop':end_date,
							  'product':_grp,
							  'routing_id':routing_id,
							  'name':line.order_id.name,
							}
						#_logger.error("save_productionsave_createcreate111["+str(_grp)+"]["+str(vals2)+"]")	
						_sch_id=_obj.create(cr, uid, vals2, context) #.create(vals, context)	
						
						
						return _sch_id
		return False				
		
	def get_date_end(self,cr,uid,ids,dt_from,hrs):
		#end_date=dt_from
		dtnew		=dt_from
		end_date 	=dtnew  + datetime.timedelta(hours=hrs)
		return end_date
		
	def get_routing_ref(self,cr,uid,ids,_routes,_hrs):
		routing_id	= None
		end_date	= None
		dt_start	= None
		if len(_routes)==1:
			routing_id	=	_routes[0]['routing_id']
			dt_start	=	_routes[0]['dt_from']
			end_date	=	self.get_date_end(cr,uid,ids,_routes[0]['dt_from'],_hrs)
			_routes[0]['dt_from']=end_date
		else:
			_tmp=None
			for _route in _routes:
				
				end_date	=	self.get_date_end(cr,uid,ids,_route['dt_from'],_hrs)
				if _tmp==None:
					_tmp=end_date
					routing_id	=	_route['routing_id']
				else:
					if _tmp>end_date:
						_tmp=end_date
						routing_id	=	_route['routing_id']
						dt_start	=	_route['dt_from']
						_route['dt_from']=end_date
						
		return routing_id, dt_start, end_date
		
	def get_item_row(self, cr, uid, ids, mrpid,_name_grp,_speed, context=None):
		vals={'order_id':mrpid.order_id.id,
			  'process_flag':True,
			  'color_code':mrpid.order_id.x_colorcode,
			  'partner_id':mrpid.partner_id.id,
			  'project_id':mrpid.project_id.id,
			  'product':_name_grp,
			  'production_id':mrpid.id,
			  }
		dep_paid=False	  
		if mrpid.order_id.x_dt_request:
			vals['date_request']=mrpid.order_id.x_dt_request
		if mrpid.order_id.x_deposit_exmpt or mrpid.order_id.x_dep_paid=="NA":
			vals['date_deposit']=self.pool.get('dincelstock.transfer').get_au_date(cr, uid,mrpid.order_id.date_order)
			dep_paid=True
		else:
			if mrpid.order_id.x_dep_paid=="paid":#i.id,,p.amount
				sql="select p.date from account_invoice i,dincelaccount_voucher_payline p where i.id=p.invoice_id and i.x_sale_order_id='%s'" % (mrpid.order_id.id)
				cr.execute(sql)
				rows 	= cr.dictfetchall()
				for row in rows:
					vals['date_deposit']=row['date']
					dep_paid=True
					
		if dep_paid:	
			
			sql="select m.x_order_qty,m.x_order_length,t.x_dcs_group from dincelmrp_production p,mrp_production m,product_template t, product_product d where p.id=m.x_production_id and t.id=d.product_tmpl_id and m.product_id=d.id and p.id='%s' and t.x_dcs_group='P%s'" % (mrpid.id,_name_grp)	 
			cr.execute(sql)
			rows 	= cr.dictfetchall()
			_total	= 0.0
			for row in rows:
				_qty	=row['x_order_qty']
				_length	=row['x_order_length']
				_lm		=_qty*_length*0.001
				_total	+=_lm
			
			vals['len_order']=_total
			vals['hrs_order']=_total/(_speed*60)
			'''if _name_grp=="110":
			elif _name_grp=="155":
				vals={'pq155_ids':_items}
			elif _name_grp=="200":
				vals={'pq200_ids':_items}
			elif _name_grp=="275":
				vals={'pq275_ids':_items}'''
		return dep_paid, vals
			
class dincelmrp_routing(osv.Model):
	_inherit = "mrp.routing"
	
	def _current_info(self, cr, uid, ids, _id, context):
		_group=''
		_to=''
		_now=datetime.datetime.now()
		sql="select prod_group,dt_to from dincelmrp_routing_available where '%s' between dt_from and dt_to and routing_id='%s' and active='t'" % ( str(_now), str(_id) )
		cr.execute(sql)
		rows 	= cr.dictfetchall()
		for row in rows:
			_group	=row['prod_group']
			_to	=row['dt_to']
		return _group,_to
		
	def _current_product(self, cr, uid, ids, values, arg, context):
		x={}
		_ret=''
		for record in self.browse(cr, uid, ids):
			_ret,_to=self._current_info(cr, uid, ids, record.id, context)
			x[record.id] = _ret
		return x
		
	def _product_till(self, cr, uid, ids, values, arg, context):
		x={}
		_to=''
		for record in self.browse(cr, uid, ids):
			_ret,_to=self._current_info(cr, uid, ids, record.id, context)
			x[record.id] = _to
		return x
		
	_columns = {
		'x_available_ids': fields.one2many('dincelmrp.routing.available', 'routing_id', 'Routing available'),
		'x_current_product': fields.function(_current_product, method=True, string='Current Product', type='char'),
		'x_product_till': fields.function(_product_till, method=True, string='Product Till', type='char'),
		#'x_mrp_pq_ids': fields.one2many('dincelmrp.production', 'mrp_route_id', 'Production Quantities'),
		'x_mrp_pq_ids' : fields.many2many('dincelmrp.production', 'rel_mrp_routing', 'production_id', 'route_id', string = "PQs"),
		'x_default_prod': fields.selection(PROD_GROUP_SELECTION, 'Default Product'),
		'x_default_start': fields.datetime('Schedule Start Next'),
		'x_planned_start': fields.datetime('Planned Start Next'),
		'x_open_day': fields.selection(WEEK_SELECTION, 'Opening Day'),
		'x_open_hr': fields.char('Opening Hr'),
		'x_close_day': fields.selection(WEEK_SELECTION, 'Closing Day'),
		'x_close_hr': fields.char('Closing Hr'),
		
	}
	
	def button_schedule_mrp_110(self, cr, uid, ids, context=None):
		return self.button_schedule_mrp(cr, uid, ids, "110", context=None)
	def button_schedule_mrp_155(self, cr, uid, ids, context=None):
		return self.button_schedule_mrp(cr, uid, ids, "155", context=None)
	def button_schedule_mrp_200(self, cr, uid, ids, context=None):
		return self.button_schedule_mrp(cr, uid, ids, "200", context=None)
	def button_schedule_mrp_275(self, cr, uid, ids, context=None):
		return self.button_schedule_mrp(cr, uid, ids, "275", context=None)
		
	def button_schedule_mrp(self, cr, uid, ids, product, context=None):
		if context is None:
			context = {}	
		return {
			'type': 'ir.actions.act_window',
			'res_model': 'dincelmrp.routing.schedule.tmp',
			'view_type': 'form',
			'view_mode': 'form',
			#'res_id': 'id_of_the_wizard',
			'context':{'default_route_id':ids[0],'default_name':product},
			'target': 'new',
		}
		
class dincelmrp_routing_available(osv.Model):
	_name 	= "dincelmrp.routing.available"
	_description ="Routing available"
	_columns = {
		'routing_id': fields.many2one('mrp.routing', 'Routing Reference', required=True),
		'name': fields.char('Name'),
		'name_week': fields.char('Week'),
		'dt_from':fields.datetime("From Date"),	
		'dt_to':fields.datetime("Date Till"),	
		'dt_year':fields.integer("Year"),
		'dt_week':fields.integer("Week"),
		'comments':fields.text("Comments"),	
		'prod_group': fields.selection(PROD_GROUP_SELECTION, 'Product'),
		'product_id': fields.many2one('product.product','Specific Product'),	
		'is_ever': fields.boolean('Until Notified'),
		'active':fields.boolean("Active"),	
	}
	
	def on_change_date(self, cr, uid, ids, dt_from, context=None):
		if dt_from:
			dt_from=self.pool.get('dincelstock.transfer').get_au_datetime(cr, uid, dt_from)
			dt_from=dateutil.parser.parse(str(dt_from))
			wk=dt_from.strftime("%V")
			yy=dt_from.strftime("%Y")
			value={'dt_year':yy,'dt_week':wk}
			return {'value': value}
		return {}
		
	def create(self, cr, uid, vals, context=None):
		if vals.get('name','/')=='/':
			if vals.get('routing_id'):
				obj 	= self.pool.get('mrp.routing').browse(cr, uid, vals.get('routing_id'), context=context)
				vals['name'] = obj.name
			if vals.get('dt_week'):
				vals['name_week'] = "Week %s" % (vals.get('dt_week'))
		return super(dincelmrp_routing_available, self).create(cr, uid, vals, context=context)
		
	def write(self, cr, uid, ids, vals, context=None):
		
		res = super(dincelmrp_routing_available, self).write(cr, uid, ids, vals, context=context)
		for record in self.browse(cr, uid, ids):
			sql="update dincelmrp_routing_available set name_week='Week %s' where id='%s'" % (record.dt_week, record.id)
			cr.execute(sql)
			#make old weeks as deactivate...
			_wk=datetime.datetime.now().strftime ("%V")
			sql="update dincelmrp_routing_available set active='f' where active='t' and dt_week<%s " % (_wk)
			cr.execute(sql)
			#_logger.error("dincelmrp_routing_availabledincelmrp_routing_available["+str(sql)+"]")	
		return res	
	_defaults = {
		'active': True,
		'name': '/',
		}