from openerp.osv import osv, fields
from openerp import api #for  @api.multi
from datetime import date
#from openerp.addons.base_status.base_state import base_state
import base64
import time 
import datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import os 
import csv
import logging
import urllib2
import simplejson
import subprocess
from subprocess import Popen, PIPE, STDOUT
#from dinceljournal import dincelaccount_journal
import pytz
from openerp import tools
from dincel_journal import dincelaccount_journal
from openerp.tools.translate import _
from openerp.exceptions import except_orm, Warning, RedirectWarning
from time import gmtime, strftime
import openerp.addons.decimal_precision as dp
_logger = logging.getLogger(__name__)

class dincelaccount_act_invoice(osv.Model):
	_inherit = "account.invoice"
	
	def get_today_au(self, cr, uid, ids, context=None):
		_from_date 	=  datetime.datetime.strptime(str(datetime.datetime.now()),"%Y-%m-%d %H:%M:%S.%f")
		time_zone	='Australia/Sydney'
		tz 			= pytz.timezone(time_zone)
		tzoffset 	= tz.utcoffset(_from_date)
		
		dt 	= str((_from_date + tzoffset).strftime("%Y-%m-%d"))
		return dt
		
	def invoice_update_dcs(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		inv_id		= ids[0]
		#return self.invoice_validate(cr, uid, ids, inv_id, context)
		url=self.pool.get('dincelaccount.config.settings').get_dcs_api_url(cr, uid, ids, "invoice", inv_id, context=context)		
		#_logger.error("updatelink_order_dcs.invoice_update_dcsinvoice_update_dcs["+str(url)+"]")
		#order_id = ids[0]
		#request = urllib.urlopen("http://deverp.dincel.com.au/dcsapi/")
		#sql ="SELECT dcs_api_url FROM dincelaccount_config_settings";
		#cr.execute(sql)
		#rows = cr.fetchone()
		#url=self.pool.get('dincelaccount.config.settings').get_dcs_api_url(cr, uid, ids,"getorder",ids[0],context=context)		
		if url:#rows and len(rows) > 0:
			#url= str(rows[0]) + "?id="+str(ids[0])
			#url="http://deverp.dincel.com.au/dcsapi/index.php?id="+str(ids[0])
				
			f = urllib2.urlopen(url)
			response = f.read()
			str1= simplejson.loads(response)
			#_logger.error("updatelink_order_dcs.invoice_update_dcs["+str(str1)+"]["+str(response)+"]")
			item = str1['item']
			status1=str(item['post_status'])
			ordercode=str(item['curr_ordercode'])
			#colorcode=str(item['curr_colourcode'])
			if status1=="success":
				#_logger.error("updatelink_order_dcs.updatelink_order_dcsordercode["+str(ordercode)+"]")	
				#sql ="UPDATE sale_order SET origin='"+ordercode+"' "	# WHERE id='"+str(ids[0])+"'"
				#if colorcode:
				#	sql +=",x_colorcode='"+colorcode+"' "
				#sql += " WHERE id='"+str(ids[0])+"'"	
				#cr.execute(sql)
				return True
			else:
				if item['errormsg']:
					str1=item['errormsg']
				else:
					str1="Error while updating order."
				raise osv.except_osv(_('Error'), _(''+str1))
		return True
		
	#def cancel_purchase_invoice_dcs(self, cr, uid, ids, context=None):
		
	#def validate_purchase_invoice_dcs(self, cr, uid, ids, context=None):
	#	
	#	inv_id		= ids[0]
	#	return self.invoice_validate(cr, uid, ids, inv_id, context)
		
	def invoice_sales_validate_btn(self, cr, uid, ids, context=None):
		
		inv_id		= ids[0]
		_obj 	= self.pool.get('account.invoice').browse(cr, uid, inv_id, context=context)
		#_obj_inv_tax = self.pool.get('account.invoice.tax')
		tot_base = 0.0
		#for record in self.browse(cr, uid, ids, context=context):
		for line in _obj.tax_line:
			tot_base += float(line.base)
		if(round(float(_obj.amount_untaxed),2) != round(float(tot_base),2)):
			raise osv.except_osv(_('Error'), _('The tax amount is not correct. Click on "Edit" then "Update" to recalculate the tax amount.'))
		#_obj 	= self.pool.get('account.invoice').browse(cr, uid, inv_id, context=context)
		if _obj.amount_total == 0.0:
			str1="Invalid or zero invoice amount found !!"
			raise osv.except_osv(_('Error'), _(''+str1))
			
		for line in _obj.invoice_line:	
			if (line.quantity<0.0 and _obj.x_inv_type in ["refund","refundreturn"]) or line.price_unit==0.0 or line.quantity==0:
				str1="Invalid or zero amount found !!"
				if (_obj.x_authorise_refund == False and _obj.x_authorise_cancel==False and _obj.x_cancel_offset==False):
					if _obj.x_sale_order_id:
						_order_id=_obj.x_sale_order_id.id
					else:
						_order_id=None
					type="discount"
					subtype="invoice"
					
					return self.open_popup_approve_request(cr, uid, _order_id, _obj.id, type, subtype, context)
					
				#raise osv.except_osv(_('Error'), _(''+str1))
		#if _obj.x_sale_order_id:
		#	chk=self.pool.get('sale.order').check_discount_allowed_message(cr, uid, ids, _obj.x_sale_order_id.id) 
		#	if chk!=1:
		#		return
		if _obj.state == "draft" and _obj.type=="out_refund":
			_custom_found=False
			for _line in _obj.invoice_line:
				if _line.product_id.x_prod_cat in ['customlength']:
					_custom_found=True
					break
			if _custom_found == True and (_obj.x_authorise_refund == False and _obj.x_authorise_cancel==False and _obj.x_cancel_offset==False):
				if _obj.x_sale_order_id:
					_order_id=_obj.x_sale_order_id.id
				else:
					_order_id=None
				type="refund"
				subtype="invoice"
				
				return self.open_popup_approve_request(cr, uid, _order_id, _obj.id, type, subtype, context)
				
				
		_ret = self.invoice_validate(cr, uid, ids, inv_id, context)
		try:
			url=self.pool.get('dincelaccount.config.settings').get_dcs_api_url(cr, uid, ids, "invoice", inv_id, context=context)		
			if url:
				val={
					"url":url,
					"name":_obj.name,
					"ref_id":_obj.id,
					"action":"getorder",
					"state":"pending",
				}
				self.pool.get('dincelbase.scheduletask').create(cr, uid, val, context=context)
				
			#NOTE: just in case if invoice deleted...cancelled...and removed line items....just to reset the payment
			
			if _obj.x_sale_order_id:
				self.pool.get('sale.order').update_payment_order(cr, uid, ids, _obj.x_sale_order_id.id, context=context)			
		except Exception,e:
			_ret=None#_logger.error("invoice_sales_validate_btn.invoice_err["+str(e)+"]")	
		return _ret
		#ret = _obj.sales_invoice2journals(cr, uid, ids, new_id, context=context)
		#if ret and ret > 0:
		'''_obj 		= self.pool.get('account.invoice')
		invoice 	= _obj.browse(cr, uid, new_id, context=context)
		
		if invoice.type=="in_invoice":
			self.validate_purchase_invoice_dcs(cr, uid, ids, context)
		elif invoice.type=="in_refund":
			self.validate_purchase_invoice_dcs(cr, uid, ids, context)
		elif invoice.type=="out_refund":
			_name = self.pool.get('ir.sequence').get(cr, uid, 'refund.invoice')	#custom sequence number
			self.write(cr, uid, new_id, {'state':'open',  'number':_name,'internal_number':_name})	
			_obj = self.pool.get('dincelaccount.journal')
			ret  = _obj.sales_invoice2journals(cr, uid, ids, new_id, context=context) #cause invoice.number is referenced in journal name (account_move) for report
		elif invoice.type=="out_invoice":
			_name = self.pool.get('ir.sequence').get(cr, uid, 'invoice.number')	#custom sequence number
			self.write(cr, uid, new_id, {'state':'open',  'number':_name,'internal_number':_name})	
			_obj = self.pool.get('dincelaccount.journal')
			ret  = _obj.sales_invoice2journals(cr, uid, ids, new_id, context=context) #cause invoice.number is referenced in journal name (account_move) for report
		else:
			_logger.error("invoice_sales_validate:invalid invoice type.ret["+str(new_id)+"]")'''
	
	def invoice_validate(self, cr, uid, ids, inv_id, context=None):
		_obj 		= self.pool.get('account.invoice')
		invoice 	= _obj.browse(cr, uid, inv_id, context=context)
		if invoice.state == "draft":
			if invoice.type=="in_invoice":
				#self.validate_purchase_invoice_dcs(cr, uid, ids, context)
				return self.invoice_validate_purchase(cr, uid, ids, inv_id, context)
			elif invoice.type=="in_refund":
				#self.validate_purchase_invoice_dcs(cr, uid, ids, context)
				return self.invoice_validate_purchase(cr, uid, ids, inv_id, context)
			elif invoice.type=="out_refund":
				_name = self.pool.get('ir.sequence').get(cr, uid, 'refund.invoice')	#custom sequence number
				self.write(cr, uid, inv_id, {'state':'open',  'number':_name,'internal_number':_name})	
				_obj = self.pool.get('dincelaccount.journal')
				ret  = _obj.sales_invoice2journals(cr, uid, ids, inv_id, context=context) #cause invoice.number is referenced in journal name (account_move) for report
			elif invoice.type=="out_invoice":
				_name = self.pool.get('ir.sequence').get(cr, uid, 'invoice.number')	#custom sequence number
				self.write(cr, uid, inv_id, {'state':'open',  'number':_name,'internal_number':_name})	
				_obj = self.pool.get('dincelaccount.journal')
				ret  = _obj.sales_invoice2journals(cr, uid, ids, inv_id, context=context) #cause invoice.number is referenced in journal name (account_move) for report
			else:
				return None#_logger.error("invoice_sales_validate:invalid invoice type.ret["+str(inv_id)+"]")
		#else:
		#	_logger.error("invoice_sales_validate:already validated invoice ["+str(inv_id)+"]")
		
	def invoice_purchase_validate(self, cr, uid, ids, context=None):
		_obj 		= self.pool.get('dincelaccount.journal')
		new_id		= ids[0]
		ret = _obj.sales_invoice2journals(cr, uid, ids, new_id, context=context)
		if ret and ret > 0:
			self.write(cr, uid, new_id, {'state':'open'})	
			
	def invoice_make_refund(self, cr, uid, new_id, _date_invoice, _comment, _journal_id, context=None):
		#_obj 		= self.pool.get('dincelaccount.journal')
		#new_id		= ids[0]
		#ret = _obj.sales_invoice2journals(cr, uid, ids, new_id ,context=context)
		#if ret and ret > 0:
		#	self.write(cr, uid, new_id, {'state':'open'})	
		#new_id		= ids[0]
		
		invalid		= True
		_objperiod 	= self.pool.get('account.period') 
		_objprod 	= self.pool.get('product.product')
		_obj 		= self.pool.get('account.invoice')
		#_obj_new	= self.pool.get('account.invoice')
		_obj_line 		= self.pool.get('account.invoice.line') 
		
		invoice 		= _obj.browse(cr, uid, new_id, context=context)
		_reference		= invoice.reference
		_company_id 	= invoice.company_id.id
		_partner_id 	= invoice.partner_id.id
		
		_amount_untaxed = invoice.amount_untaxed
		_amount_tax 	= invoice.amount_tax
		_amount_total 	= invoice.amount_total
		_account_id 	= invoice.account_id.id
		 
		_name			= ""#"REF_"+str(invoice.name)
		
		#_date_invoice	= datetime.datetime.today()
		#_comment		= ""
		_period_id		= _objperiod.find(cr, uid, _date_invoice, context=context)[0]
		vals={
			'type':'out_refund',	
			'state':'draft',
			'x_inv_type':'refund',
			'x_cancel_offset':True,
			'journal_id':_journal_id,
			'account_id':_account_id,
			'name':_name,
			'comment':_comment,
			'reference':_reference,
			'company_id':_company_id,
			'date_invoice':_date_invoice,
			'period_id':_period_id,
			'partner_id':_partner_id,
			#'x_project_id':invoice.x_project_id.id,
			'amount_tax':_amount_tax,
			'amount_total':_amount_total,
			'amount_untaxed':_amount_untaxed,
		}
		if invoice.user_id:
			vals['user_id']=invoice.user_id.id
		if invoice.x_project_id:
			vals['x_project_id']=invoice.x_project_id.id
		if invoice.x_sale_order_id:
			vals['x_sale_order_id']=invoice.x_sale_order_id.id
			vals['origin']=invoice.x_sale_order_id.name
			#  'origin': record.name,
            #        'reference': record.name,
		_id = _obj.create(cr, uid, vals, context=context)
		
		if _id:
			for line in invoice.invoice_line:
				_price_subtotal	= line.price_subtotal
				_price_unit		= line.price_unit
				_product_id 	= line.product_id.id
				_qty			= line.quantity
				_origin			= line.origin
				_discount		= line.discount
				
				_name			= line.product_id.name
				_qty = _qty * -1 #convert into negative for refund...so that it will balances out the invoice in s.o.
				vals = {
					'name':_name,
					'account_id':_account_id,
					'company_id':_company_id,
					'invoice_id':_id,
					'partner_id':_partner_id,
					'product_id':_product_id,
					'quantity':_qty,
					'price_subtotal':_price_subtotal,
					'price_unit':_price_unit,
					'origin':_origin,
					'discount':_discount,
				}
				if line.x_order_qty:
					vals['x_order_qty'] = line.x_order_qty * -1
				if line.x_order_length:
					vals['x_order_length'] = line.x_order_length 	
					
				#instead of product settings ...pick from line items....eg nz do not have tax 1/3/2017
				if line.invoice_line_tax_id:
					vals['invoice_line_tax_id'] = [(6, 0, line.invoice_line_tax_id.ids)]
				#if line.product_id.taxes_id:
				#	vals['invoice_line_tax_id'] = [(6, 0, line.product_id.taxes_id.ids)]
				if line.x_coststate_id:
					vals['x_coststate_id'] = line.x_coststate_id.id 
					
				_obj_line.create(cr, uid, vals, context=context)	
				
			 #---for auto tax calculation
			obj_inv = _obj.browse(cr, uid, _id, context)
			obj_inv.button_compute(True)	
			
		return _id
		
	def invoice_make_purchase_refund(self, cr, uid, new_id, _date_invoice, _comment, _journal_id, context=None):
		#_obj 		= self.pool.get('dincelaccount.journal')
		#new_id		= ids[0]
		#ret = _obj.sales_invoice2journals(cr, uid, ids, new_id ,context=context)
		#if ret and ret > 0:
		#	self.write(cr, uid, new_id, {'state':'open'})	
		#new_id		= ids[0]
		
		invalid		= True
		_objperiod 	= self.pool.get('account.period') 
		_objprod 	= self.pool.get('product.product')
		_obj 		= self.pool.get('account.invoice')
		#_obj_new	= self.pool.get('account.invoice')
		_obj_line 		= self.pool.get('account.invoice.line') 
		
		invoice 		= _obj.browse(cr, uid, new_id, context=context)
		_reference		= invoice.reference
		_company_id 	= invoice.company_id.id
		_partner_id 	= invoice.partner_id.id
		
		_amount_untaxed = invoice.amount_untaxed
		_amount_tax 	= invoice.amount_tax
		_amount_total 	= invoice.amount_total
		_account_id 	= invoice.account_id.id
		 
		_name			= ""#"REF_"+str(invoice.name)
		
		#_date_invoice	= datetime.datetime.today()
		#_comment		= ""
		_period_id		= _objperiod.find(cr, uid, _date_invoice, context=context)[0]
		vals={
			'type':'in_refund',	
			'state':'draft',
			'journal_id':_journal_id,
			'account_id':_account_id,
			'name':_name,
			'comment':_comment,
			'reference':_reference,
			'company_id':_company_id,
			'date_invoice':_date_invoice,
			'period_id':_period_id,
			'partner_id':_partner_id,
			#'x_project_id':invoice.x_project_id.id,
			'amount_tax':_amount_tax,
			'amount_total':_amount_total,
			'x_inv_type':'refund',
			'amount_untaxed':_amount_untaxed
		}
		if invoice.x_project_id:
			vals['x_project_id']=invoice.x_project_id.id
		if invoice.x_sale_order_id:
			vals['x_sale_order_id']=invoice.x_sale_order_id.id
			vals['origin']=invoice.x_sale_order_id.name
			#  'origin': record.name,
            #        'reference': record.name,
		_id = _obj.create(cr, uid, vals, context=context)
		
		if _id:
			for line in invoice.invoice_line:
				_price_subtotal	= line.price_subtotal
				_price_unit		= line.price_unit
				if line.product_id:
					_product_id 	= line.product_id.id
					_name			= line.product_id.name
				else:
					_product_id = None
					_name			= line.name
				
				if line.account_id:
					_account_id 	= line.account_id.id
				else:
					_account_id=None
				_qty			= line.quantity
				_origin			= line.origin
				_discount		= line.discount
				#if _product_id:
					
				_qty = _qty * -1 #convert into negative for refund...so that it will balances out the invoice in s.o.
				vals = {
					'name':_name,
					#'account_id':_account_id,
					'company_id':_company_id,
					'invoice_id':_id,
					'partner_id':_partner_id,
					#'product_id':_product_id,
					'quantity':_qty,
					'price_subtotal':_price_subtotal,
					'price_unit':_price_unit,
					'origin':_origin,
					'discount':_discount,
				}
				
				if _account_id:
					vals['account_id'] = _account_id
				if _product_id:
					vals['product_id'] = _product_id
				#instead of product settings ...pick from line items....eg nz do not have tax 1/3/2017
				if line.invoice_line_tax_id:
					vals['invoice_line_tax_id'] = [(6, 0, line.invoice_line_tax_id.ids)]
				#if line.product_id.taxes_id:
				#	vals['invoice_line_tax_id'] = [(6, 0, line.product_id.taxes_id.ids)]
				if line.x_coststate_id:
					vals['x_coststate_id'] = line.x_coststate_id.id 
					
				_obj_line.create(cr, uid, vals, context=context)	
				
			 #---for auto tax calculation
			obj_inv = _obj.browse(cr, uid, _id, context)
			obj_inv.button_compute(True)	
			
		return _id
		
	def invoice_sales_validate_final(self, cr, uid, ids, context=None):
		new_id		= ids[0]
		_obj 		= self.pool.get('account.invoice')
		invoice 	= _obj.browse(cr, uid, new_id, context=context)
		
		
	def invoice_sales_validate2xx(self, cr, uid, ids, context=None):
		
		      
		return {}
		
	def invoice_print_dcs(self, cr, uid, ids, context=None):		
		'''assert len(ids) == 1, 'This option should only be used for a single id at a time.'
		o = self.browse(cr, uid, ids)[0]
		#url="http://deverp.dincel.com.au/odoo/web/index.php?act=order_invoice&id="+str(o.id)
		sql ="SELECT odoo_api_url FROM dincelaccount_config_settings"
		cr.execute(sql)
		rows = cr.fetchone()
		if rows and len(rows) > 0:
			url= str(rows[0]) + "web/index.php?act=invoice&id="+str(ids[0])'''
		url=self.pool.get('dincelaccount.config.settings').report_preview_url(cr, uid, ids,"invoice",ids[0],context=context)		
		return {
				  'name'     : 'Go to website',
				  'res_model': 'ir.actions.act_url',
				  'type'     : 'ir.actions.act_url',
				  'view_type': 'form',
				  'view_mode': 'form',
				  'target'   : 'new',
				  'url'      : url
			   }
				   
	def invoice_print_dcs_xxx(self, cr, uid, ids, context=None):	
		if context is None:
			context = {}
		#datas = {'ids': context.get('active_ids', [])}
		datas = {'ids': []}
		datas['form']  = self.read(cr, uid, ids, context=context)[0]
		#_logger.error("invoice_print_pdf_dcs:datas["+str(datas)+"]")
		return self.pool['report'].get_action(cr, uid, [], 'account.report_partner_invoice', data=datas, context=context)			
	
	#self, cr, uid, ids, args, field_name, context=None
	def create_invoice_pdf(self, cr, uid, ids, args, _id, context=None):#self, cr, uid,  _id, context=None):
		
		o=self.pool.get('account.invoice').browse(cr, uid, _id, context)
		if o.x_invoice_attach and o.x_invoice_attach.id:
			#return True
			self.pool['ir.attachment'].unlink(cr, uid, [o.x_invoice_attach.id], context=context)
		#else:	
		#sql ="SELECT odoo_api_url FROM dincelaccount_config_settings"
		#cr.execute(sql)
		#rows = cr.fetchone()
		url2=self.pool.get('dincelaccount.config.settings').report_preview_url(cr, uid, ids,"invoice",_id,context=context)		
		urlpdf=self.pool.get('dincelaccount.config.settings').report_preview_url(cr, uid, ids,"file","",context=context)		
		if url2:#rows and len(rows) > 0:
			url=url2.replace("erp.dincel.com.au/", "localhost/")
			
			#_logger.error("urlurlurl:url["+str(url)+"]["+str(url2)+"]")
			_obj = self.pool.get('account.invoice')  
			#not validate invoice unless manually done
			#...6/2/2017 ---removed automatic validate button below
			#_obj.invoice_validate(cr, uid, ids, _id, context) #//validate and create journals....
				
			#url= str(rows[0]) + "web/index.php?act=invoice&id="+str(_id)
			#if o.x_invoice_attach:
			#	return True
			if not o.x_inv_type:
				_type=""
			else:
				_type=str(o.x_inv_type)+"_"
			if o.state and o.state=="draft":
				fname		= "%sinv_%s_draft.pdf" % (_type, o.id) 				#_type+"inv_"+str(o.id)+"_draft.pdf"
				fname_img	= "%sinv_%s_draft.png" % (_type, o.id)				#fname1=str(o.x_inv_type)+"_inv_"+str(o.id)+"_draft.jpg"
			else:
				fname		= "%sinv_%s.pdf" % (_type, o.number)				#fname = str(o.x_inv_type)+"_inv_"+str(o.number)+".pdf"
				fname 		= fname.replace('/', '_')
				fname_img	= "%sinv_%s.png" % (_type, o.number)				#fname1 = str(o.x_inv_type)+"_inv_"+str(o.number)+".jpg"
				fname_img 	= fname_img.replace('/', '_')
			
			urlpdf+="&f="+fname_img
			
			root_path="/var/tmp/odoo/account/"
			root_path_img="/var/www/html/images/"
			
			temp_path_img=root_path_img+fname_img
			temp_path=root_path+fname
			
			#_logger.error("invoice_print_pdf_dcs:wkhtmltoimagewkhtmltoimage[%s][%s][%s]" % (url,temp_path_img,temp_path))
			'''
			process_img=subprocess.Popen(["wkhtmltoimage",
						'--width', '800', 
						'--quality', '100', 
						url, temp_path_img],stdin=PIPE,stdout=PIPE)
			out, err = process_img.communicate()
			if process_img.returncode not in [0, 1]:
				raise osv.except_osv(_('Report (PDF)'),
									_('Wkhtmltopdf failed (error code: %s). '
									'Message: %s') % (str(process_img.returncode), err)) 
			
			process=subprocess.Popen(["wkhtmltopdf", urlpdf, temp_path],stdin=PIPE,stdout=PIPE)'''
			process=subprocess.Popen(["wkhtmltopdf", url, temp_path],stdin=PIPE,stdout=PIPE)
			
			
			out, err = process.communicate()
			if process.returncode not in [0, 1]:
				raise osv.except_osv(_('Report (PDF)'),
									_('Wkhtmltopdf failed (error code: %s). '
									'Message: %s') % (str(process.returncode), err))
										
			f=open(temp_path,'r')
			_data = f.read()
			_data = base64.b64encode(_data)
			f.close()
			#os.chmod(temp_path, 0400)
			
			ir_attachement_obj=self.pool.get('ir.attachment')
			document_vals = {
				'name': fname,   #                     -> filename.csv
				'datas': _data,    #                                              -> path to my file (under Windows)
				'datas_fname': fname, #           -> filename.csv 
				'res_model': self._name, #                                  -> My object_model
				'res_id': o.id,  #                                   -> the id linked to the attachment.
				'type': 'binary' 
				}
			
			ir_id = ir_attachement_obj.create(cr, uid, document_vals, context) 
			
			try:
				#_obj = self.pool.get('account.invoice')  
				#_obj.invoice_validate(cr, uid, ids, _id, context) #//validate and create journals....
				_obj.write(cr, uid, o.id, {'sent':False,'x_invoice_attach': ir_id})  #set invoice sent to false as well...for reseting for all created pdf..if somehow deleted...
				if context and context.get('download_file') !=None:
					if context.get('download_file')=="1":
						return {
							'name': 'Invoice',
							'res_model': 'ir.actions.act_url',
							'type' : 'ir.actions.act_url',
							'url': '/web/binary/download_file?model=sale.order&field=datas&id=%s&path=%s&filename=%s' % (str(o.id),root_path,fname),
							'context': context}
				return True
			except ValueError:
				return False
					
	def invoice_print_pdf_dcs(self, cr, uid, ids, context=None):
		ctx = context.copy()
		#ctx['download_file']="1"
		return self.create_invoice_pdf(cr, uid, ids,  {}, ids[0], context=ctx)
	
	def invoice_download_pdf_dcs(self, cr, uid, ids, context=None):
		ctx = context.copy()
		ctx['download_file']="1"
		return self.create_invoice_pdf(cr, uid, ids,  {}, ids[0], context=ctx)
	 
	def invoice_print_pdf_dcsxx(self, cr, uid, ids, context=None):
		assert len(ids) == 1, 'This option should only be used for a single id at a time.'
		o = self.browse(cr, uid, ids)[0]
		#url="http://deverp.dincel.com.au/odoo/web/index.php?act=order_invoice&id="+str(o.id)
		sql ="SELECT odoo_api_url FROM dincelaccount_config_settings"
		cr.execute(sql)
		rows = cr.fetchone()
		if rows and len(rows) > 0:
			url= str(rows[0]) + "web/index.php?act=invoice&id="+str(ids[0])
			url=str.replace("erp.dincel.com.au/", "localhost/")
			if o.x_invoice_attach:
				return True #TODO...may popup warning. or hide the create button if already created...
			else:
				fname=o.x_inv_type+"_inv_"+str(o.number)+".pdf"
				temp_path="/var/tmp/odoo/account/"+fname
				
				process=subprocess.Popen(["wkhtmltopdf", url, temp_path],stdin=PIPE,stdout=PIPE)
				
				out, err = process.communicate()
				if process.returncode not in [0, 1]:
					raise osv.except_osv(_('Report (PDF)'),
										_('Wkhtmltopdf failed (error code: %s). '
										'Message: %s') % (str(process.returncode), err))
											
				f=open(temp_path,'r')
				_data = f.read()
				_data = base64.b64encode(_data)
				f.close()
				
				ir_attachement_obj=self.pool.get('ir.attachment')
				document_vals = {
					'name': fname,   #                     -> filename.csv
					'datas': _data,    #                                              -> path to my file (under Windows)
					'datas_fname': temp_path, #           -> filename.csv 
					'res_model': self._name, #                                  -> My object_model
					'res_id': o.id,  #                                   -> the id linked to the attachment.
					'type': 'binary' 
					}
				
				ir_id = ir_attachement_obj.create(cr, uid, document_vals, context) 
				
				try:
					_obj = self.pool.get('account.invoice')  
					_obj.write(cr, uid, o.id, {'x_invoice_attach': ir_id})  
					return True
				except ValueError:
					return False
					
	def invoice_print_pdf_dcs_xxx(self, cr, uid, ids, context=None):	
		if context is None:
			context = {}
		datas = {'ids': context.get('active_ids', [])}
	 
		datas['form']  = self.read(cr, uid, ids, context=context)[0]
		
		return self.pool['report'].get_action(cr, uid, [], 'account.report_partner_invoice_pdf', data=datas, context=context)			
		#return {}	
		
	def invoice_sales_refund2(self, cr, uid, ids, context=None):	
		sql= "select id from account_journal where type='sale_refund'"
		#sql = "select id from account_move where ref='%s' and journal_id='%s'" %(invoice_name,journal_id)
		cr.execute(sql)
		rowsk 		= cr.fetchone()
		if rowsk == None or len(rowsk)==0:
			invalid	= True
		else:	
			journal_id=rowsk[0]
			
		return {}	
	
	def cr_limit_over(self, cr, uid, ids, values, arg, context):
			
		x={}
		_over=False
		for record in self.browse(cr, uid, ids):
			if record.partner_id and record.partner_id.credit_limit>0:
				_over=self.pool.get('sale.order').get_over_limit2(cr, uid, record.partner_id.id, record.partner_id.credit_limit,context)
			else:
				_over=False
				'''sql ="select sum(amount_total) from sale_order where partner_id='%s' and x_status='open'" % (record.partner_id.id)
				cr.execute(sql)
				rows = cr.fetchone()
				if rows == None or len(rows)==0:
					_over=False
				else:
					 if rows[0]!=None:
						if record.partner_id.credit_limit<rows[0]:
							_over=True'''
		x[record.id] = _over 
		return x
		
	#def _last_day_of_month(self, any_day):
	#	next_month = any_day.replace(day=28) + datetime.timedelta(days=4)  # this will never fail
	#	return next_month - datetime.timedelta(days=next_month.day)
	#onchange_partner_id_new2(self, cr, uid, ids, type, partner_id, date_invoice,  payment_term, partner_bank_id, company_id, context=None):	
	def onchange_pay_terms_dcs(self, cr, uid, ids,_termid, _date, context = None):
		vals={} 
		if _termid and _date:
			#obj=self.pool.get('account.payment.term').browse(cr, uid, _termid,context) 
			
			#if obj and  obj.x_payterm_code:
			#	#dt1=_date + datetime.timedelta(365/12)
			#	vals['date_due']= self.pool.get('sale.order').get_due_date(cr, uid, ids, obj.x_payterm_code, _date, _date, context)
			vals['date_due']= self.pool.get('sale.order').get_due_date_v2(cr, uid, ids, _termid, _date, _date, context)
			#	#vals['date_due']= self._last_day_of_month(dt1)
			#if len(c_ids1) > 0:
			#domain  = {'x_sale_order_id': [('id','in', (c_ids1))]}
		return {'value': vals}
		
	def onchange_projectsite(self, cr, uid, ids, partner_id, project_id, context = None):
		userid=None 
		c_ids1=[]
		domain={}
		val = {}
		if project_id:
			c_ids1 = self.pool.get('sale.order').search(cr, uid, [('x_project_id', '=', project_id)], context=context)
		 
			#,('state', 'not in', ['cancel','done'])
			#if len(c_ids1) > 0:
			domain  = {'x_sale_order_id': [('id','in', (c_ids1))]}
			
		if partner_id:
			_obj2 = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context)
			if _obj2.x_site_branch:
				if _obj.user_id:
					userid=_obj.user_id.id 
			if userid==None:	
				if _obj2.user_id:
					userid=_obj2.user_id.id 
				
		if userid==None:
			obj1 = self.pool.get('res.users').search(cr, uid, [('x_code', '=', "INSL")], context=context)#[0]
			if obj1:
				userid=obj1[0]
		if userid:		
			val['user_id']=userid
			
		return {'value': val,'domain': domain}#@return True
		
	def onchange_journal_refund(self, cr, uid, ids, _journal_id,  context):
		if _journal_id:
			journal =  self.pool.get('account.journal').browse(cr, uid,_journal_id, context=context)
			return {
				'value': {
					'x_refund_account_id': journal.default_credit_account_id.id
				}
			}
			
	def _balance_amt(self, cr, uid, ids, values, arg, context):
		x={}
		_bal=0.0
		for record in self.browse(cr, uid, ids):
			_bal=record.amount_total
			_paid=0.0
			sql="."
			try:
				
				#if record.partner_id and record.partner_id.credit_limit>0:
				sql ="select sum(p.amount) from dincelaccount_voucher_payline p,account_invoice a where a.id=p.invoice_id and p.invoice_id='%s'" % (record.id)
				cr.execute(sql)
				
				rows = cr.fetchone()
				#_logger.error("updatelink_order_dcs.dincelaccount_voucher_payline["+str(sql)+"]["+str(rows)+"]")
				if rows and len(rows)>0:
					if rows[0]:
						_paid=float(rows[0])
			except ValueError:
				_paid=0.0#_logger.error("updatelink_order_dcs.dincelaccount_voucher_payline["+str(sql)+"]["+str(ValueError)+"]")
				pass
				
			x[record.id] = (_bal -_paid)
		return x
		
	def onchange_payment_term_date_invoice_new2(self, cr, uid, ids, payment_term, date_invoice, context=None):
		#if not date_invoice:
		#    date_invoice = fields.Date.context_today(self)
		#if not payment_term:
		#    # To make sure the invoice due date should contain due date which is
		#    # entered by user when there is no payment term defined
		#    return {'value': {'date_due': self.date_due or date_invoice}}
		if payment_term and date_invoice:
			#obj=self.pool.get('account.payment.term').browse(cr, uid, payment_term,context) 
			
			#if obj and  obj.x_payterm_code:
				#dt1=_date + datetime.timedelta(365/12)
			_dt= self.pool.get('sale.order').get_due_date_v2(cr, uid, ids, payment_term, date_invoice, date_invoice, context)
			return {'value': {'date_due': _dt}}
		return {}
		#return True
	#onchange_partner_id_new(type, partner_id, date_invoice, payment_term, partner_bank_id, company_id)
	#res = self.onchange_partner_id(type, partner_id, date_invoice,  payment_term, partner_bank_id, company_id, context)
	def onchange_partner_id_new2(self, cr, uid, ids, type, partner_id, date_invoice,  payment_term, partner_bank_id, company_id, context=None):
		account_id = False
		payment_term_id = False
		fiscal_position = False
		bank_id = False
		salesman = False
		domain={}
		if partner_id:
			p = self.pool.get('res.partner').browse(cr, uid, partner_id)
			salesman = p.user_id and p.user_id.id# or uid
			rec_account = p.property_account_receivable
			pay_account = p.property_account_payable
			if company_id:
				if p.property_account_receivable.company_id and \
						p.property_account_receivable.company_id.id != company_id and \
						p.property_account_payable.company_id and \
						p.property_account_payable.company_id.id != company_id:
					prop = self.pool.get('ir.property')
					rec_dom = [('name', '=', 'property_account_receivable'), ('company_id', '=', company_id)]
					pay_dom = [('name', '=', 'property_account_payable'), ('company_id', '=', company_id)]
					res_dom = [('res_id', '=', 'res.partner,%s' % partner_id)]
					rec_prop = prop.search(rec_dom + res_dom) or prop.search(rec_dom)
					pay_prop = prop.search(pay_dom + res_dom) or prop.search(pay_dom)
					rec_account = rec_prop.get_by_record(rec_prop)
					pay_account = pay_prop.get_by_record(pay_prop)
					if not rec_account and not pay_account:
						action = self.pool.get('account.action_account_config')#self.env.ref('account.action_account_config')
						msg = _('Cannot find a chart of accounts for this company, You should configure it. \nPlease go to Account Configuration.')
						raise osv.except_osv(_('Error'), msg)#raise RedirectWarning(msg, action.id, _('Go to the configuration panel'))

			if type in ('out_invoice', 'out_refund'):
				account_id = rec_account.id
				payment_term_id = p.property_payment_term.id
			else:
				account_id = pay_account.id
				payment_term_id = p.property_supplier_payment_term.id
			fiscal_position = p.property_account_position.id
			bank_id = p.bank_ids and p.bank_ids[0].id or False
			
			proj_list = []
			for item in p.x_role_site_ids:
				proj_list.append(item.id) 
			domain  = {'x_project_id': [('id','in', (proj_list))]}	
				
		result = {'value': {
			'user_id': salesman,
			'account_id': account_id,
			'payment_term': payment_term_id,
			'fiscal_position': fiscal_position,
			},'domain': domain}

		if type in ('in_invoice', 'in_refund'):
			result['value']['partner_bank_id'] = bank_id

		if payment_term != payment_term_id:
			if payment_term_id:
				to_update = self.onchange_payment_term_date_invoice_new2(cr, uid, ids, payment_term_id, date_invoice)
				result['value'].update(to_update.get('value', {}))
			else:
				result['value']['date_due'] = False

		if partner_bank_id != bank_id:
			to_update = self.onchange_partner_bank(cr, uid, ids, bank_id)
			result['value'].update(to_update.get('value', {}))

		return result
		#return res	
	_columns = {
		'x_invoice_ref': fields.many2one('account.invoice', 'Origin Invoice', help="Origin of invoice for refund, etc."),
		'x_refund_journal_id': fields.many2one('account.journal', 'Refund Journal'),
		'x_refund_account_id': fields.many2one('account.account', 'Refund Account'),
		'x_cr_limit_over': fields.function(cr_limit_over, method=True, string='Cr Limit', type='boolean'),
		'x_balance_amt': fields.function(_balance_amt, method=True, string='Balance', type='float'),
		'x_full_delivered':fields.boolean('Full Delivered'),
		'x_sale_order_id': fields.many2one('sale.order','Sale Order Reference'),
		'x_order_code': fields.related('x_sale_order_id', 'origin', type='char', string='DCS Order',store=False),
		'x_project_id': fields.many2one('res.partner','Project / Site'),
		'x_credit_limit': fields.related('partner_id', 'credit_limit', type='float', string='Credit Limit',store=False),
		'x_invoice_attach':fields.many2one('ir.attachment','Invoice Attachments'),
		'x_revise_sn': fields.integer('Revise SN', size=2),	
		'x_edit_so': fields.boolean('Edit SO'),
		'x_cancel_offset': fields.boolean('Cancellation C.Note'),
		'x_dt_refund':fields.date("Date Refund"),
		'x_function':fields.selection([
			('marketing', 'Marketing'),
			('hr', 'Human Resource')], 'Function'),
		'x_pay_line_ids': fields.one2many('dincelaccount.voucher.payline', 'invoice_id','Payments'),
		'x_authorise_cancel':fields.boolean('Authorise Cancel'),
		'x_authorise_refund':fields.boolean('Authorise Refund',help="Authorise refund of custom length"),
		#'x_invoice_pdf':fields.many2one('ir.attachment','Invoice Attachments'),
		'x_inv_type':fields.selection([
			('none', 'None'),
            ('deposit', 'Deposit Invoice'),
            ('balance', 'Balance Invoice'),
			('balance1', 'Balance1 Invoice'),
			('full', 'Full Invoice'),
			('refund', 'Refund Invoice'),
			('refundreturn', 'Refund Return'),
			], 'Invoice Type'), ##make sure to reflect if changes is made in INV_TYPE_SELECTION in dincelaccount.voucher.payline
		'state':fields.selection([
			('draft','Draft'),
			('proforma','Pro-forma'),
			('proforma2','Pro-forma'),
			('open','Open'),
			('paid','Paid'),
			('close','Closed'),
			('offset','Offset'),
			('cancel','Cancelled'),
		], string='Status', index=True, readonly=True, default='draft',
		track_visibility='onchange', copy=False,
		help=" * The 'Draft' status is used when a user is encoding a new and unconfirmed Invoice.\n"
			 " * The 'Pro-forma' when invoice is in Pro-forma status,invoice does not have an invoice number.\n"
			 " * The 'Open' status is used when user create invoice,a invoice number is generated.Its in open status till user does not pay invoice.\n"
			 " * The 'Paid' status is set automatically when the invoice is paid. Its related journal entries may or may not be reconciled.\n"
			 " * The 'Cancelled' status is used when user cancel invoice."),	
	}
	_defaults = {
		'x_revise_sn':0,
		'x_cancel_offset':False,
		'x_authorise_cancel':False,
	}
	
	def invoice_refund_bank_dcs(self, cr, uid, ids, context=None):
		inv_id=ids[0]
		ret  =False
		_obj = self.pool.get('dincelaccount.journal')
		for record in self.browse(cr, uid, ids, context=context):	
			inv_id=record.id 
			if record.x_balance_amt==0 or record.x_balance_amt>0:
				raise Warning(_('Invalid invoice type or balance amount!'))
			else:
				if not record.x_refund_journal_id or not record.x_refund_account_id or not record.x_dt_refund:
					raise Warning(_('Please select journal, bank account and date!'))
				else:
				
					journal_id = record.x_refund_journal_id.id 
					account_id = record.x_refund_account_id.id
					
					_dt		=	record.x_dt_refund
					
					
					ret  = _obj.invoice_refund_bank_journal(cr, uid, ids, inv_id, journal_id, account_id, _dt, context=context)	
					if ret==True:
						_name = self.pool.get('ir.sequence').get(cr, uid, 'sales.pay.number')	#custom sequence number
						vals1={
							"partner_id":record.partner_id.id,
							"journal_id":journal_id,
							"state":"posted",
							"amount":record.x_balance_amt,
							"account_id":account_id,
							#"number":_name,
							"name":_name,
							"date":_dt,
							"company_id":record.company_id.id,
							"type":"receipt",
							"pay_now":"pay_now",
						}
						voucher_id=self.pool.get('account.voucher').create(cr,uid, vals1,context)
						
						vals={
							"invoice_id":inv_id,
							"amount":record.x_balance_amt,
							"state":"done",
							"amount_fee":0,
							"account_id":account_id,
							"inv_state":"paid",
							"type":"pay_invoice",
							"name":record.name,
							"date":_dt,
							"date_due":_dt,
							"voucher_id":voucher_id,
						}
						id=self.pool.get('dincelaccount.voucher.payline').create(cr,uid, vals,context)
						if id:
							
							self.pool.get('account.voucher').write(cr, uid, voucher_id, {'state':'posted',  'number':_name})	 #some reasons default was "draft"..so force to make it posted
						
					return self.write(cr, uid, inv_id, {'state':'paid','x_refund_journal_id':journal_id,'x_refund_account_id':account_id,'x_dt_refund':_dt})	
		return True
	
	def button_sales_orders(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		for record in self.browse(cr, uid, ids, context=context):	
			partner_id=record.partner_id.id 
			obj = self.pool.get('sale.order')
			view_id = self.pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'dincelmanufacture.dincelmrp_sale_order_tree')], limit=1) 	
			

			value = {
				'type': 'ir.actions.act_window',
				'name': _('Sale Orders'),
				'view_type': 'form',
				'view_mode': 'tree,form',
				'res_model': 'sale.order',
				'domain':[('partner_id','=',partner_id)],
				'context':{'search_default_partner_id': partner_id},
				'view_id': view_id,
				
			}

			return value
			
	def button_refund_invoice(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		for record in self.browse(cr, uid, ids, context=context):	
			#partner_id=record.partner_id.id 
			#obj = self.pool.get('sale.order')
			#if obj.account_id.x_sale_order_id:
			sale=record.x_sale_order_id
			type="cancel"
			subtype="invoice"
			#sale=obj.x_sale_order_id
			if sale and sale.x_prod_status in ["part","complete"]:
				if record.x_authorise_cancel==False:
					return self.open_popup_approve_request(cr, uid, sale.id, record.id, type, subtype, context)
					
			value = {
				'view_type': 'form',
				'view_mode': 'form',
				'res_model': 'dincelaccount.refund_invoice',
				'type': 'ir.actions.act_window',
				'name' : _('Refund Invoice'),
				'context':{
						'default_account_id': record.id, 
						#'default_request_uid': uid, 
						#'default_type': type, 
						#'default_subtype': subtype, 
						#'default_approve_pending': _pending, 
				},
				'target': 'new',
			}
			return value
			
	def button_cancel_invoice(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		for record in self.browse(cr, uid, ids, context=context):	
			#partner_id=record.partner_id.id 
			#obj = self.pool.get('sale.order')
			#if obj.account_id.x_sale_order_id:
			sale=record.x_sale_order_id
			type="cancel"
			subtype="invoice"
			#sale=obj.x_sale_order_id
			if sale and sale.x_prod_status in ["part","complete"]:
				if record.x_authorise_cancel==False:
					return self.open_popup_approve_request(cr, uid, sale.id, record.id, type, subtype, context)
					
			value = {
				'view_type': 'form',
				'view_mode': 'form',
				'res_model': 'dincelaccount.refund_invoice',
				'type': 'ir.actions.act_window',
				'name' : _('Cancel Invoice'),
				'context':{
						'default_account_id': record.id, 
						'default_cancel': True, 
						#'default_request_uid': uid, 
						#'default_type': type, 
						#'default_subtype': subtype, 
						#'default_approve_pending': _pending, 
				},
				'target': 'new',
			}
			return value	
			
	def open_popup_approve_request(self, cr, uid, _orderid,inv_id,type, subtype=None,  context=None):
		#if chk==-1:
		#	type="credit"
		#else:
		#	type="discount"
		if subtype==None:
			subtype="order"
		if _orderid:
			sql="select 1 from dincelsale_order_approve where order_id='%s' and state='open' and invoice_id='%s' " % (_orderid, inv_id)	
		else:
			sql="select 1 from dincelsale_order_approve where  state='open' and invoice_id='%s' " % (inv_id)	
		cr.execute(sql)
		rows1 = cr.fetchall()
		if len(rows1) > 0:
			_pending=True 
		else:
			_pending=False
		value = {
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'saleorder.approve.request',
			'type': 'ir.actions.act_window',
			'name' : _('Approval request'),
			'context':{
					'default_order_id': _orderid, 
					'default_invoice_id': inv_id, 
					'default_request_uid': uid, 
					'default_type': type, 
					'default_subtype': subtype, 
					'default_approve_pending': _pending, 
			},
			'target': 'new',
		}
		return value	
		
class dincelaccount_act_invoice_line(osv.Model):
	_inherit = "account.invoice.line"
	_columns={
		'x_qty_left': fields.float('Qty Left', digits=(16,2)),
		'x_region_id': fields.many2one('dincelaccount.region', 'A/c Region'),
		'x_order_length':fields.float("Ordered Len"),	
		'x_order_qty':fields.integer("Ordered Qty"),	
		'x_coststate_id':fields.many2one("res.country.state","Cost Centre"),
		'x_incgst_price': fields.float("Inc. Tax",digits_compute= dp.get_precision('Purchase Price') ),	
	}
	 
	@api.multi
	def product_id_change_v2(self, product, uom_id, qty=0, name='', type='out_invoice',
			partner_id=False, fposition_id=False, price_unit=False, currency_id=False,
			company_id=None):
		context = self._context
		company_id = company_id if company_id is not None else context.get('company_id', False)
		self = self.with_context(company_id=company_id, force_company=company_id)

		if not partner_id:
			raise except_orm(_('No Partner Defined!'), _("You must first select a partner!"))
		if not product:
			if type in ('in_invoice', 'in_refund'):
				return {'value': {}, 'domain': {'product_uom': []}}
			else:
				return {'value': {'price_unit': 0.0}, 'domain': {'product_uom': []}}

		values = {}

		part = self.env['res.partner'].browse(partner_id)
		fpos = self.env['account.fiscal.position'].browse(fposition_id)

		if part.lang:
			self = self.with_context(lang=part.lang)
		product = self.env['product.product'].browse(product)

		values['name'] = product.partner_ref
		if type in ('out_invoice', 'out_refund'):
			account = product.property_account_income or product.categ_id.property_account_income_categ
		else:
			account = product.property_account_expense or product.categ_id.property_account_expense_categ
		account = fpos.map_account(account)
		if account:
			values['account_id'] = account.id

		if type in ('out_invoice', 'out_refund'):
			taxes = product.taxes_id or account.tax_ids
			if product.description_sale:
				values['name'] += '\n' + product.description_sale
		else:
			taxes = product.supplier_taxes_id or account.tax_ids
			if product.description_purchase:
				values['name'] += '\n' + product.description_purchase

		taxes = fpos.map_tax(taxes)
		values['invoice_line_tax_id'] = taxes.ids
		if product.x_prod_cat and product.x_prod_cat in ['stocklength','customlength']:
			values['price_unit'] = 0  
		else:
			if type in ('in_invoice', 'in_refund'):
				values['price_unit'] = price_unit or product.standard_price
			else:
				values['price_unit'] = product.list_price

		values['uos_id'] = uom_id or product.uom_id.id
		domain = {'uos_id': [('category_id', '=', product.uom_id.category_id.id)]}

		company = self.env['res.company'].browse(company_id)
		currency = self.env['res.currency'].browse(currency_id)

		if company and currency:
			if company.currency_id != currency:
				if type in ('in_invoice', 'in_refund'):
					values['price_unit'] = product.standard_price
				values['price_unit'] = values['price_unit'] * currency.rate

			if values['uos_id'] and values['uos_id'] != product.uom_id.id:
				values['price_unit'] = self.env['product.uom']._compute_price(
					product.uom_id.id, values['price_unit'], values['uos_id'])

		return {'value': values, 'domain': domain}
		
	def calc_exgst_price(self, cr, uid, ids, _incgst,_unitprice, taxes, is_unitprice, context = None):
		if is_unitprice:
			_taxamt	=0.0
			_unitprice = float(_unitprice)
			if taxes:
				_taxamt	=0.0
				_obj	=self.pool.get('account.tax')
				if len(taxes[0]) >= 3 and taxes[0][2]:
					tax = _obj.browse(cr, uid, taxes[0][2], context)
					for line in tax:
						_taxamt+=float(_unitprice)*float(line.amount)
				 
			return {'value':{'x_incgst_price':(_unitprice+_taxamt)}}
		else:
			_taxamt	=0.0
			_incgst = float(_incgst)
			if taxes:
				_taxamt	=0.0
				_obj	=self.pool.get('account.tax')
				if len(taxes[0]) >= 3 and taxes[0][2]:
					tax = _obj.browse(cr, uid, taxes[0][2], context)
					for line in tax:
						_extax	=float(_incgst)/float(line.amount+1.00)
						_taxamt+=(_incgst-_extax)
				 
			return {'value':{'price_unit':(_incgst-_taxamt)}}
			
	def item_change(self, cr, uid, ids, name, company_id, account_id, tax_id, type, context = None):
		
		if type in ('in_invoice', 'in_refund') and company_id:
			_obj=self.pool.get('account.tax')
			_ids = _obj.search(cr, uid, [('name','=','GST-Purchase')], order='id desc', limit=1)	
			
			if _ids:
				_id=_ids[0]
				_obj2 = self.pool.get('account.account').browse(cr, uid, account_id, context=context)
				if _obj2.tax_ids and _obj2.tax_ids.id !=_id:
					return {'value':{'invoice_line_tax_id':[_obj2.tax_ids.id]}}
				else:
					return {'value':{'invoice_line_tax_id':[_id]}}
			
	'''			
	def item_changexx(self, cr, uid, ids, name, company_id, type, context = None):
		
		if type in ('in_invoice', 'in_refund') and company_id:
			_obj=self.pool.get('account.tax')
			_ids = _obj.search(cr, uid, [('name','=','GST-Purchase')], order='id desc', limit=1)	
			#record = _obj.browse(cr, uid, _ids, context=context)
			#ir_values = self.pool.get('ir.values')
			#taxes_id = ir_values.get_default(cr, uid, 'product.template', 'supplier_taxes_id', company_id=company_id)
			#_logger.error("updatelink_order_dcs.item_changeitem_change22["+str(_ids)+"]["+str(type)+"]") 
			
			if _ids:
				#tax_ids=[]
				return {'value':{'invoice_line_tax_id':_ids}}
	'''
class dincelaccount_product_template(osv.Model):
	_inherit="product.template"
	
	def is_main_profile(self, cr, uid, ids, values, arg, context):
		x={}
		is_main='0'
		for record in self.browse(cr, uid, ids):
			if record.x_prod_cat:
				if record.x_prod_cat=='stocklength'	or record.x_prod_cat=='customlength':
					is_main = '1'
				else:	
					is_main = '0'
			x[record.id] = is_main 
		return x
		
	_columns={
		'x_is_calcrate': fields.boolean('Is Main Profile'), #not in use, due to -> is_main_profile()
		'x_prod_type': fields.char("Product Type",size=5),#acs: accessories others blank...or future use...due to x_prod_cat="stocklength" being used for rate calc to m2....conflicting logic....
		'x_prod_cat': fields.selection([
            ('none', 'None'),
            ('deposit', 'Deposit'),
			('balance', 'Balance'),
			('balance1', 'Balance1'),
            ('stocklength', 'Stock Length'),
            ('customlength', 'Custom Length'),
            ('accessories', 'Accessories'),
            ('freight', 'Freight'),
            ], 'Product Category'),
		'x_stock_length': fields.float("Stock Length"),	
		'x_m2_factor': fields.float("x M2 Factor (qty x len x factor)",digits_compute= dp.get_precision('Rate Factor') ),	
		'x_stock_width': fields.float("Width"),	
		'x_stock_height': fields.float("Depth"),	
		'x_price_account': fields.float("Sale Price (A/C)"),	
		'x_dcs_itemcode': fields.char('DCS Item Code',size=20),
		'x_pack10': fields.boolean('Pack 10'),  #if Pack 10 is active
		'x_pack12': fields.boolean('Pack 12'),	#if Pack 12 is active
		'x_pack14': fields.boolean('Pack 14'),	#if Pack 14 is active
		'x_pack20': fields.boolean('Pack 20'),	#if Pack 20 is active
		'x_pick_journal': fields.boolean('Pick Ac Journal'),
		'x_sort_sn': fields.integer('Sort SN', size=2),	
		'x_len_min': fields.integer('Length Min (mm)', help="Minimum length in mm for production."),	
		'x_len_max': fields.integer('Length Max (mm)', help="Maximum length in mm for production."),	
		'x_len_inc': fields.integer('Increment (mm)', help="Allowed increments in mm for production."),	
		'x_is_main': fields.function(is_main_profile, method=True, string='Is Main', type='char'),
		'x_bom_cat': fields.selection([
            ('none', 'None'),
            ('material', 'Material'),
            ('labour', 'Labour'),
            ('overheads', 'Overheads'),
            ], 'BOM Category'),
		'x_produce_speed': fields.float("Produce (metre / min)"),#>> TODO for more complex...do settings per line (production line)..
		'x_dcs_group': fields.selection([
			('none', 'None'),
			('P110', '110mm'),
			('P155', '155mm'),
			('P200', '200mm'),
			('P275', '275mm'),
			], 'DCS Product Group'),
		'standard_price': fields.property(type = 'float', digits_compute=dp.get_precision('Purchase Price'), 
			help="Cost price of the product template used for standard stock valuation in accounting and used as a base price on purchase orders. "
			"Expressed in the default unit of measure of the product.",
			groups="base.group_user", string="Cost Price"),
			}
	
	_defaults = {
		'x_bom_cat': 'none',
		'x_prod_cat': 'none',
		'x_pick_journal': False,
		'x_produce_speed': 1.0,
	}
	

		
class dincelaccount_supplierinfo(osv.Model):
	_inherit="product.supplierinfo"
	_columns={
		'x_cost_price': fields.float("Supplier Cost"),	
	}
	
class dincelaccount_payment_term(osv.Model):
	_inherit="account.payment.term"
	_columns={
		'x_payterm_code': fields.char('Code',size=10),
		'x_eom': fields.boolean('EOM'),
		'x_days': fields.integer('Days'),
	}
class dincelaccount_partner_bank(osv.Model):
	_inherit="res.partner.bank"
	_columns={
		'x_bank_userid': fields.char('Bank User Id',size=6),
		'x_bank_bsb': fields.char('Bank BSB',size=7),
	}
	
class dincelaccount_company(osv.Model):
	_inherit="res.company"
	_columns={
		'x_site_address': fields.char('Site Address'),
	}
	
class dincelaccount_myob_product(osv.Model):
	_name="dincelaccount.myob.product"
	_columns={
		'name': fields.char('Name'),
		'code': fields.char('Code'),
		'dcs_code': fields.char('Dcs Code'),
		'erp_name': fields.char('Erp Name'),
	} 
	
class dincelaccount_partner_due(osv.osv):
    _name = "dincelaccount.partner.due"
    
    _auto = False
    
    _columns = {
        'partner_id': fields.many2one('res.partner', 'Partner', readonly=True),
        'sumtax': fields.float('Total Tax', readonly=True),
		'sumuntax': fields.float('Total Untaxed', readonly=True),
		'sumtot': fields.float('Total Due', readonly=True),
		'subtot': fields.float('Subtotal', readonly=True),
    }
    
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'dincelaccount_partner_due')
        cr.execute("""
            create or replace view dincelaccount_partner_due as (
                select min(a.id) as id,
                  a.partner_id,
				  sum(a.amount_tax) as sumtax,
				  sum(a.amount_untaxed) as sumuntax,
				  sum(a.amount_total) as sumtot,
				  sum(a.subtotal_wo_discount) as subtot 
				  from account_invoice a 
				  where a.type='out_invoice' and a.state='open'
				  group by a.partner_id         )
			""")	
			
class dashboard_sales(osv.Model):
	_name = "dashboard.sales"
	_description = "Dashboard"
	#for test.	