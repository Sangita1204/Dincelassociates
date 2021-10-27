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
import subprocess
from subprocess import Popen, PIPE, STDOUT
import urllib2
import simplejson
_logger = logging.getLogger(__name__)
class dincelmrp_schedule_print(osv.Model):
	_name = "dincelmrp.schedule.print"
	_description="Print Schedule"
	_order = 'schedule_start, sort_no'# order_item as in dcs , for summary #sequence_print,
	
	def _get_init_qty(self, cr, uid, context=None):
		return 1
		
	_columns = {
		'name':fields.char("Name"),
		'notes':fields.char("Notes"),
		'process_flag':fields.boolean("Process Flag"),
		'reset_sequence':fields.boolean("Reset Sequence"),
		'planned':fields.boolean("Planned Flag"),
		'print_line': fields.one2many('dincelmrp.schedule.print.line', 'schedule_print_id', 'Schedule Lines'),
		'qty':fields.float("Qty test"),
		'week_sn':fields.integer("Week"),
		'dt_from':fields.datetime("From Date"),	
	}
	_defaults = {
		'qty': _get_init_qty,
		'process_flag': False,
		'week_sn': 0,
		}	
	def on_change_date(self, cr, uid, ids, dt_from, context=None):
		if dt_from:
			#this date is coming as GMT date...so need to convert into AU date 
			#--------------------------------------------
			dt_from=self.pool.get('dincelstock.transfer').get_au_datetime(cr, uid, dt_from)
			dt_from=dateutil.parser.parse(str(dt_from))
			wk=dt_from.strftime("%V")
			#yy=dt_from.strftime("%Y")
			#_logger.error("on_change_dateon_change_date[["+str(dt_from)+"]["+str(wk)+"]")
			value={'week_sn':wk}
			return {'value': value}
		return {}
		
	def on_change_resetseq(self, cr, uid, ids, _flag,_lines, context=None):
		if context is None:
			context = {}
		if _lines and _flag:
			
			line_ids = self.resolve_2many_commands(cr, uid, 'print_line', _lines, ['process_flag'], context)
			 
			for line in line_ids:
				if line:

					line['sort_sn']= 0
					 
			return {'value': {'print_line': line_ids}}
			
		#return {'value':vals}
		
	def on_change_processflag(self, cr, uid, ids, _flag,_lines, context=None):
		vals={}
		context = context or {}
		
	 
		if _lines:
			
			line_ids = self.resolve_2many_commands(cr, uid, 'print_line', _lines, ['process_flag'], context)
			 
			for line in line_ids:
				if line:
				 
					line['process_flag']= _flag
					 
			return {'value': {'print_line': line_ids}}
			
		return {'value':vals}
		
	def on_change_qty(self, cr, uid, ids, _qty,_name_grp, context=None):
		_items=[]
		if context is None:
			context = {}
			
		_planned=False	
		_checked=False
		
		_obj=self.pool.get('dincelmrp.schedule') 
		#_product_arr=[]
		#_notes=""#e.g. load lines available for specific product...
		if context and context.get('active_ids'):
			_ids=context.get('active_ids')
			for line in _obj.browse(cr, uid, _ids, context=context): 
				if _checked == False: #very first one
					_checked=True
					#_planned=line.planned
					if line.planned:
						_planned=True
						
				if line.planned == 	_planned:	
					if line.order_id.origin:
						_name=line.order_id.origin
					else:
						_name=line.order_id.name
					vals={'schedule_ref':line.id,
						  'production_id':line.production_id.id,
						  'order_id':line.order_id.id,
						  'color_code':line.order_id.x_colorcode,
						  'order_code':_name,#line.order_id.origin,
						  'partner_id':line.partner_id.id,
						  'project_id':line.project_id.id,
						  'product':line.product,
						  'len_order':line.len_order,
						  'hrs_order':line.hrs_order,
						  'name':_name,#line.order_id.origin or line.order_id.name,
						  'state':line.state,
						  'notes':line.order_id.x_note_request,
						  'sort_sn':line.sequence_sort,
						  'week_sn':line.week_sn,
						}
					if line.route_id:
						vals['route_id']=line.route_id.id
					if line.order_id.x_dt_request:
						vals['date_request']=line.order_id.x_dt_request
					if line.order_id.x_dt_anticipate:
						vals['dt_anticipate']=line.order_id.x_dt_anticipate
					if line.date_deposit:
						vals['date_deposit']=line.date_deposit
					'''
					if line.order_id.x_deposit_exmpt or line.order_id.x_dep_paid=="NA":
						vals['date_deposit']=self.pool.get('dincelstock.transfer').get_au_date(cr, uid,line.order_id.date_order)
					else:
						if line.order_id.x_dep_paid=="paid":#i.id,,p.amount
							sql="select p.date from account_invoice i,dincelaccount_voucher_payline p where i.id=p.invoice_id and i.x_sale_order_id='%s'" % (line.order_id.id)
							cr.execute(sql)
							rows 	= cr.dictfetchall()
							for row in rows:
								vals['date_deposit']=row['date'] '''
					#_logger.error("on_change_qtyon_change_linelinelineline_idid["+str(line.id)+"]")	
					_items.append(vals)
					#if line.product not in _product_arr:
					#	_product_arr.append(line.product)
					#	_notes+="%s, " % (line.product)
		#else:
		#vals= {}
		#if len(_items)>0:
		#	#_items.sort(key=lambda item:item['date_deposit'], reverse=True)
		#	_items.sort(key=lambda item:item['date_deposit'])
		
		vals['print_line']=_items
		vals['planned']=_planned
		if not _planned:
			vals['dt_from']=self.pool.get('dincelstock.transfer').get_gmt_datetime(cr, uid,datetime.datetime.now().strftime("%Y-%m-%d 06:00:00"))
		#if _notes!="":
		#	_notes=_notes[:-2]
		#vals['notes']=_notes	#load lines available for specific product...
		return {'value':vals}	
	
	def move2schedule(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		record = self.browse(cr, uid, ids[0], context=context)
		for line in record.print_line:
			if line.schedule_ref and line.process_flag:
				 _id=line.schedule_ref
				 #_seq+=1
				 sql="update dincelmrp_schedule set schedule_start=null,planned='f' where id='%s'" % (str(_id))
				 cr.execute(sql)
		return True

	def button_calculate_date(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		_seq=0
		record = self.browse(cr, uid, ids[0], context=context)
		if record.planned:
			self.calculate_estimate_date_plan(cr, uid, ids,record.dt_from, context=context)	
		else:
			if not record.dt_from:
				raise osv.except_osv(_("Error!"), _("Please select or enter value in From Date."))
			self.calculate_estimate_date_active(cr, uid, ids,record.dt_from, context=context)		
		return False
		
	def calculate_estimate_date_active(self, cr, uid, ids,dt_from, context=None):		
		_weeks=[]
		_seq=0
		product=None
		planned="f"
		week_sn=None
		objsch=self.pool.get('dincelmrp.schedule')
		
		
		record = self.browse(cr, uid, ids[0], context=context)
		for line in record.print_line:	
			product=line.product
			if line.schedule_ref and line.process_flag:
				_id=line.schedule_ref
				_seq+=1
				sql="update dincelmrp_schedule set date_flag='t' " #sequence_sort='"+str(_seq)+"', #no chang on sequence sort ....
				sql+=" where id='"+str(_id)+"'"  
				cr.execute(sql)
		#if product and record.dt_from and week_sn:
		#	sql=""
		_lines	= objsch.get_lines_info_active(cr, uid, ids,  product,dt_from, context=context)
		#_logger.error("calculate_estimate_date_active_lines_lines["+str(_lines)+"]")	
		if len(_lines) == 0:
			raise osv.except_osv(_("Error!"), _("No any line routing configured for this product for current week."))
		_items = objsch.get_items_byweek(cr, uid, ids,week_sn, product, planned, context=context)		
		for _item in _items:
			idid=_item['id'];

			_start,_stop,_lineid, _lines=objsch.calculate_planned_dates(cr, uid, ids,_lines, _item, context=context)
		
			
			sql="""update dincelmrp_schedule set schedule_start='%s',schedule_stop='%s',route_id='%s' 
					,date_flag='f' 
					where id='%s' """ % (_start,_stop,_lineid, idid)
			cr.execute(sql)
				
		return True
		
	def calculate_estimate_date_plan(self, cr, uid, ids, dt_from, context=None):	
		_weeks=[]
		_seq=0
		product=""
		planned="t"
		objsch=self.pool.get('dincelmrp.schedule')
		record = self.browse(cr, uid, ids[0], context=context)
		for line in record.print_line:
			product=line.product
			if line.week_sn and line.week_sn not in _weeks:
				_weeks.append(line.week_sn)
				sql="""update dincelmrp_schedule set schedule_start=null,schedule_stop=null,route_id=null 
					,date_flag='f' 
					where week_sn='%s' and planned='t' """ % (line.week_sn)
				cr.execute(sql)
				
		for line in record.print_line:		
			if line.schedule_ref and line.process_flag:
				_id=line.schedule_ref
				_seq+=1
				sql="update dincelmrp_schedule set date_flag='t' " #sequence_sort='"+str(_seq)+"', #no chang on sequence sort ....
				sql+=" where id='"+str(_id)+"'" #% (_plan, str(_id))
				cr.execute(sql)
				
		for week_sn in _weeks:
			_lines	= objsch.get_lines_info(cr, uid, ids, week_sn, product, dt_from, context=context)
			if len(_lines) == 0:
				raise osv.except_osv(_("Error!"), _("No any line routing configured for this product for week %s." % (week_sn)))
			
			_items = objsch.get_items_byweek(cr, uid, ids,week_sn, product, planned, context=context)
			for _item in _items:
				idid=_item['id'];

				_start,_stop,_lineid, _lines=objsch.calculate_planned_dates(cr, uid, ids,_lines, _item, context=context)
			
				
				sql="""update dincelmrp_schedule set schedule_start='%s',schedule_stop='%s',route_id='%s' 
						,date_flag='f' 
						where id='%s' """ % (_start,_stop,_lineid, idid)
				cr.execute(sql)
		return True
		
	def button_reset_save_seq(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		_seq=0	
		sql = "";
		_log = "";
		record = self.browse(cr, uid, ids[0], context=context)	
		if record.reset_sequence:
			_log = str(_log) + str(record.reset_sequence)
			for line in record.print_line:
				_log = str(_log) + " " + str(line.schedule_ref) + " " + str(line.process_flag)
				if line.schedule_ref and line.process_flag:
					_id=line.schedule_ref
					_seq+=1  
					sql="update dincelmrp_schedule set " 
					sql +="sequence_sort='"+str(_seq)+"'"
					sql +=" where id='"+str(_id)+"'"
					_log = str(_log) + str(sql)
					cr.execute(sql)
		_logger.error("button_reset_save_seq111["+str(record.print_line)+"]")			
		
	def mark_as_printed_pq(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		_seq=0
		_today=fields.date.context_today(self,cr,uid,context=context)
		record = self.browse(cr, uid, ids[0], context=context)
		for line in record.print_line:
			if line.schedule_ref  and line.process_flag:
				if line.state and line.state in ['printed','done','closed','cancel','part']:
					_seq+=0 #do nothing...
				else:
					_id=line.schedule_ref
					_seq+=1
					sql="update dincelmrp_schedule set state='printed',sequence_print='%s',date_print='%s' where id='%s'" % (str(_seq),str(_today),str(_id))
					cr.execute(sql)
					if(line.order_id):
						self.pool.get('sale.order').order_produced_check(cr, uid, ids, line.order_id.id, context=context)
		return True
		#raise osv.except_osv(_('Success'),_('All record/s has been saved successfully !!'))
	
	
		
	 	
	def button_clear_date(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		url=""	
		_lines=[]
		#_seq=0
		record = self.browse(cr, uid, ids[0], context=context)
		
		if record.planned:
			_plan="t"
		else:
			_plan="f"
			
		for line in record.print_line:
			if line.schedule_ref and line.process_flag:
				_id=line.schedule_ref
				#_seq+=1
				
				if line.state == None:
					_state=",state='draft'"
				else:
					if line.state in ['printed','done','closed','cancel','part']:
						_state="" #if these do not change the status....
					else:
						_state=",state='draft'"
				
				sql="update dincelmrp_schedule set schedule_start=null,schedule_stop=null,line_flag='f'"+str(_state)+",planned='"+str(_plan)+"'" 
				#no change on sequence sort ....
				#sql +=",sequence_sort='"+str(_seq)+"'"
				sql +=" where id='"+str(_id)+"'"
				
				cr.execute(sql)
		''' 
		try:
			url=self.pool.get('dincelaccount.config.settings').get_odoo_api_url(cr, uid, ids, "mrpschedule", "", context=context)	
			
			if url:#rows and len(rows) > 0:
				url= str(url) + "&return=json&line_flag=1"
				f = urllib2.urlopen(url, timeout = 3) #3 seconds timeout
				response = f.read()
				#_logger.error("ex.error11.mrpdone.mrpschedulemrpschedule1111["+str(url)+"][ ]")
				#-------------------------------------------------------------------------------------------
				sql="select 1 from dincelbase_scheduletask where state='pending' and url='%s' and write_uid!='1'" % (url)
				#_logger.error("ex.error11.mrpdone.mrpschedulemrpschedule1111["+str(url)+"]["+str(sql)+" ]")
				cr.execute(sql)	
				rows = cr.fetchone()
				if rows == None or len(rows)==0:
					val={
						"url":url,
						"name":"mrpschedule",
						"ref_id":record.id,
						"action":"mrpschedule",
						"state":"pending",
					}
					self.pool.get('dincelbase.scheduletask').create(cr, uid, val, context=context)
		except Exception,e:
			_logger.error("ex.error.mrpdone.mrpschedulemrpschedule["+str(url)+"]["+str(e)+"]")
			pass'''
		return True
	def calculate_estimate_date(self, cr, uid, ids, context=None):
		if context is None:
			context = {}	
			
	def calculate_estimate_datexx(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		_seq=0
		record = self.browse(cr, uid, ids[0], context=context)
		if record.planned:
			_plan="t"
		else:
			_plan="f"
		for line in record.print_line:
			if line.schedule_ref and line.process_flag:
				_id=line.schedule_ref
				_seq+=1
				#_seq=line.sort_sn
				#vals={'sequence':_seq,'schedule_id':_id}
				#.append(vals)
				if line.state == None:
					_state=",state='draft'"
				else:
					_state=""
				sql="update dincelmrp_schedule set schedule_start=null"+str(_state)+",date_flag='t',planned='"+str(_plan)+"'"
				if _plan=="f":#only active schedule...not for planned ones...
					sql+=",sequence_sort='"+str(_seq)+"'"
				sql+=" where id='"+str(_id)+"'" #% (_plan, str(_id))
				#_logger.error("ex.calculate_estimate_datecalculate_estimate_datecalculate_estimate_date["+str(sql)+" ]")
				cr.execute(sql)
				 
		try:
			url=self.pool.get('dincelaccount.config.settings').get_odoo_api_url(cr, uid, ids, "mrpschedule", "", context=context)	
			
			if url:#rows and len(rows) > 0:
				url= str(url) + "&return=json"
				
				f = urllib2.urlopen(url, timeout = 3) #3 seconds timeout
				response = f.read()
				'''str1	 = simplejson.loads(response)
				#@_logger.error("updatelink_order_dcs.updatelink_order_dcs["+str(str1)+"]["+str(response)+"]")
				item 	 = str1['item']
				status1	 = str(item['post_status'])
				dcs_refcode	= str(item['dcs_refcode'])
				if status1 != "success":
					#_logger.error("updatelink_order_dcs.updatelink_order_dcsordercode["+str(ordercode)+"]")	
					#sql ="UPDATE res_partner SET x_dcs_id='"+dcs_refcode+"' WHERE id='"+str(ids[0])+"'"
					#cr.execute(sql)
					#return True
					#else:
					if item['errormsg']:
						str1=item['errormsg']
					else:
						str1="Error while updating order at DCS."
					_logger.error("error.mrpdone.update_order_dcsordercode["+str(dcs_refcode)+"]["+str(str1)+"]")'''
					
				#_logger.error("ex.error11.mrpdone.mrpschedulemrpschedule1111["+str(url)+"][ ]")
				#-------------------------------------------------------------------------------------------
				sql="select 1 from dincelbase_scheduletask where state='pending' and url='%s' and write_uid!='1'" % (url)
				#_logger.error("ex.error11.mrpdone.mrpschedulemrpschedule1111["+str(url)+"]["+str(sql)+" ]")
				cr.execute(sql)	
				rows = cr.fetchone()
				if rows == None or len(rows)==0:
					val={
						"url":url,
						"name":"mrpschedule",
						"ref_id":record.id,
						"action":"mrpschedule",
						"state":"pending",
					}
					self.pool.get('dincelbase.scheduletask').create(cr, uid, val, context=context)
		except Exception,e:
			_logger.error("ex.error11.mrpdone.mrpschedulemrpschedule["+str(url)+"]["+str(e)+"]")
			pass
		return True
		
	def btn_save_sequence_sort(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		#url=""
		#_ids=[]
		#_lines=[]
		_seq=0
		serial_found=False
		record = self.browse(cr, uid, ids[0], context=context)
		if record.week_sn and record.week_sn>0:
			week_sn=int(record.week_sn)
		else:
			week_sn=0
			
		for line in record.print_line:
			
			if line.schedule_ref and line.sort_sn and line.sort_sn>0:
				serial_found=True
		for line in record.print_line:
			if line.schedule_ref  and line.process_flag:
				_id=line.schedule_ref
				if serial_found:
					_seq=line.sort_sn or 0
				else:
					_seq+=1
				#_seq=line.sort_sn
				#vals={'sequence':_seq,'schedule_id':_id}
				#_lines.append(vals)
				if line.state == None:
					_state=",state='draft'"
				else:
					_state=""
				sql="update dincelmrp_schedule set sequence_print='"+str(_seq)+"'"+str(_state)+",sequence_sort='"+str(_seq)+"' "
				if week_sn and week_sn>0:
					sql += ",week_sn='"+str(week_sn)+"' "
				else:
					sql += ",week_sn=null "
				sql += " where id='"+str(_id)+"'"
				cr.execute(sql)
				_logger.error("btn_save_sequence_sort11111["+str(sql)+"]")
		#if len(_lines)>0:
		#	_lines.sort(key=lambda item:item['sequence'], reverse=True)
		return True
		
	def print_production(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		#_obj=self.pool.get('dincelmrp.schedule')	
		_str=""
		_ids=[]
		_lines=[]
		_seq=0
		record = self.browse(cr, uid, ids[0], context=context)
		for line in record.print_line:
			if line.schedule_ref and line.process_flag:
				 _id=line.schedule_ref
				 #_ids.append(_id)
				 #33_str+=str(_id)+"-"
				 #_seq+=1
				 _seq=line.sort_sn
				 vals={'sequence':_seq,'schedule_id':_id}
				 _lines.append(vals)
				 sql="update dincelmrp_schedule set sequence_print='%s' where id='%s'" % (str(_seq),str(_id))
				 cr.execute(sql)
				 
		if len(_lines)>0:
			_lines.sort(key=lambda item:item['sequence'], reverse=True)
		for line in _lines:
			_id=line['schedule_id']
			_str+=str(_id)+"-"
			_ids.append(_id)
			
		if _str and len(_str)>0:
			url=self.pool.get('dincelaccount.config.settings').report_preview_url(cr, uid, ids,"pqlist","0",context=context)	
			if url:			
				url+="&ids="+_str+"&uid=" +str(uid)
				fname_part=datetime.datetime.now().strftime("%Y%m%d")
				fname="pqlist_"+str(fname_part)+".pdf"
				save_path="/var/tmp/odoo/mrp"
				
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
				for _id in _ids:
					sql="update dincelmrp_schedule set state='queue' where id='%s' and (state is null or state in ('draft','pending'))  " % (_id)
					#_logger.error("on_change_qtyon_change_sqlsqlsql["+str(sql)+"]")	
					cr.execute(sql)
				return {
						'name': 'Production Qty',
						'res_model': 'ir.actions.act_url',
						'type' : 'ir.actions.act_url',
						'url': '/web/binary/download_file?model=dincelmrp.schedule&field=datas&id=1&path=%s&filename=%s' % (save_path,fname),
						'context': context}
		#return False				
		
	  
		
class dincelmrp_schedule_print_line(osv.osv_memory):
	_name="dincelmrp.schedule.print.line"
	#_order = 'id desc' order_item as in dcs , for summary
	_columns={
		'name': fields.char('Name'),
		'sequence':fields.integer('Sequence'),
		'sort_sn':fields.integer('Serial No'),
		'schedule_print_id': fields.many2one('dincelmrp.schedule.print','Print Reference'),
		'production_id': fields.many2one('dincelmrp.production', 'Production Reference',ondelete='cascade',),
		'order_id': fields.many2one('sale.order','Order'),
		'schedule_ref': fields.char('schedule_ref'),
		#'schedule_id': fields.many2one('dincelmrp.schedule','Schedule Reference'),
		'color_code': fields.related('order_id', 'x_colorcode', type='char', string='Color',store=False),
		'order_code': fields.related('order_id', 'origin', type='char', string='Order Code',store=False),
		'product': fields.char('Product'),
		'state':fields.char('State'),
		'partner_id': fields.many2one('res.partner','Customer'),	
		'project_id': fields.many2one('res.partner','Project / Site'),	
		'process_flag':fields.boolean('Process Flag'),	
		'schedule_start':fields.datetime('Schedule Start'),
		'schedule_stop':fields.datetime('Schedule Stop'),
		'date_request':fields.date('Date Request'),
		'dt_anticipate':fields.date('Date Anticipate'),
		'date_deposit':fields.date('Date Deposit'),
		'notes': fields.char('Notes'),
		'len_order': fields.float('Ordered Length', digits=(16,2)),
		'hrs_order': fields.float('Hrs', digits=(16,2)),
		'route_id': fields.many2one('mrp.routing','Routing/Line'),	
		'week_sn':fields.integer("Week"),
		}