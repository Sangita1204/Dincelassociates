from openerp.osv import osv, fields
from datetime import date
from dateutil.relativedelta import relativedelta
import base64
#import urllib
import time 
import datetime
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
'''
TYPE2DATES = {
	'tba': 'TBA',
	'na': 'NA',
	'dt': 'Date',
}'''
	
class dincelaccount_sale_order(osv.Model):
	_inherit="sale.order"
	#_order = 'id desc'
	def onchange_partner_id_v2(self, cr, uid, ids, part, project_id, context=None):
		if not part:
			return {'value': {'partner_invoice_id': False, 'partner_shipping_id': False,  'payment_term': False, 'fiscal_position': False}}

		part = self.pool.get('res.partner').browse(cr, uid, part, context=context)
		addr = self.pool.get('res.partner').address_get(cr, uid, [part.id], ['delivery', 'invoice', 'contact'])
		pricelist = part.property_product_pricelist and part.property_product_pricelist.id or False
		payment_term = part.property_payment_term and part.property_payment_term.id or False
		dedicated_salesman = part.user_id and part.user_id.id or uid
		val = {
			'partner_invoice_id': addr['invoice'],
			'partner_shipping_id': addr['delivery'],
			'payment_term': payment_term,
			'user_id': dedicated_salesman,
			'x_credit_limit': part.credit_limit,
			'x_deposit_exmpt': part.x_deposit_exmpt,
			'x_rate_note':part.x_rate_note,
			}
		#if part.x_deposit_exmpt:
		
			
		delivery_onchange = self.onchange_delivery_id(cr, uid, ids, False, part.id, addr['delivery'], False,  context=context)
		val.update(delivery_onchange['value'])
		if pricelist:
			val['pricelist_id'] = pricelist
		sale_note = self.get_salenote(cr, uid, ids, part.id, context=context)
		if sale_note: val.update({'note': sale_note})  
		
		c_ids3  = []
		proj_list = []
		#x_role_site_ids
		#obj		= self.pool.get('res.partner').browse(cr,uid,part.id,context=context)
		#_logger.error("change_payment_term:line.x_role_site_idsx_role_site_ids["+str(part.x_role_site_ids)+"]")
		for item in part.x_role_site_ids:
			proj_list.append(item.id) 
			c_ids3 = c_ids3 + self.pool.get('res.partner').search(cr, uid, [('parent_id', '=', item.id)], context=context)
		#x_role_site_ids
		
		c_ids1 = self.pool.get('res.partner').search(cr, uid, [('parent_id', '=', part.id)], context=context)
		if project_id:
			c_ids2 = self.pool.get('res.partner').search(cr, uid, [('parent_id', '=', project_id)], context=context)
			c_ids1 = c_ids1 + c_ids2
		else:
			c_ids1 = c_ids3
			
		if len(c_ids1) > 0:
			domain  = {'x_project_id': [('id','in', (proj_list))],'x_contact_id': [('id','in', (c_ids1))]}#domain['x_contact_id']=[('id','in', (my_list))]
		else:
			domain  = {'x_project_id': [('id','in', (proj_list))]}
			
		return {'value': val,'domain': domain}
		
	def onchange_projectsite(self, cr, uid, ids, project_id, context=None):
		_obj = self.pool.get('res.partner').browse(cr, uid, project_id, context=context)
		if _obj:
			street=""
			val = {
				#'x_street': str(_obj.street) + " " + str(_obj.street2),
				'x_postcode': _obj.zip,
				'x_suburb': _obj.city,
				}
			if _obj.street:
				street+= str(_obj.street)
			if _obj.street2:
				street+= " " +str(_obj.street2)
				
			val['x_street']=street	
			if _obj.state_id:
				val['x_state_id']=_obj.state_id.id
				val['x_coststate_id']=_obj.state_id.id
			if _obj.country_id:
				val['x_country_id']=_obj.country_id.id	
			return {'value': val}
	
	 
			
	def change_payment_term(self, cr, uid, ids, loc_id,partner_id=False, payment_term = False, dt_sale = False, order_lines= False, context=None):
		#order_id	= None
		rate		= 0.0
		#partner_obj = self.pool.get('res.partner')
		product_obj = self.pool.get('product.product')
		term_obj 	= self.pool.get('account.payment.term')
		
		rate_obj 	= self.pool.get('dincelcrm.customer.rate')
		term_obj 	= term_obj.browse(cr, uid, payment_term)
		code 	 	= term_obj.x_payterm_code
		#date_order = False
		
		#pricelist= self.pool.get('product.pricelist').search(cr, uid, [('type', '=', 'sale')], limit=1) 	
		
		#for record in self.browse(cr, uid, ids):
		#	date_order=record.date_order
			
		#if not date_order:
		#	date_order=datetime.today()
		#_logger.error("change_payment_termchange_payment_termline.payment_termpayment_term["+str(payment_term)+"]")
		#if partner_id:
		#	partner_obj = self.pool.get('res.partner').browse(cr,uid,partner_id,context=context)
		#	acs_c
		if code:	
			rate_id = rate_obj.find(cr, uid, dt_sale, partner_id, context=context)
			if rate_id:
				rate_id	 = rate_id[0]
				rate_obj =  rate_obj.browse(cr, uid, rate_id)
				if rate_obj:
					#if code == "30EOM":
					#	rate = rate_obj.rate_acct
					if code == "COD" or code=="immediate":
						rate = rate_obj.rate_cod
					else:
						rate = rate_obj.rate_acct
		#if not date_order:
		
		#if rate:
		if loc_id and rate>0.0:
			loc_obj = self.pool.get('stock.warehouse').browse(cr,uid,loc_id,context=context)
			rate = rate+loc_obj.x_cost_xtra
			 
		#_logger.error("change_payment_termchange_payment_termline.rate["+str(rate)+"]")
		#_logger.error("change_payment_termchange_payment_termline.order_line["+str(order_line)+"]")
		product_obj = self.pool.get('product.product')
		line_obj = self.pool.get('sale.order.line')
		order_line = []
		for line in order_lines:
			# create    (0, 0,  { fields })
			# update    (1, ID, { fields })
			if line[0] in [0, 1]:
				prod = None
				if line[2].get('product_id'):
					prod = product_obj.browse(cr, uid, line[2]['product_id'], context=context)
				elif line[1]:
					prod =  line_obj.browse(cr, uid, line[1], context=context).product_id
				if prod and prod.x_is_main=='1':
					line[2]['price_unit'] = rate#[[6, 0, fiscal_obj.map_tax(cr, uid, fpos, prod.taxes_id)]]
				else:
					if prod.list_price:
						line[2]['price_unit'] = prod.list_price 
				#	if prod and prod.list_price
				order_line.append(line)

			# link      (4, ID)
			# link all  (6, 0, IDS)
			elif line[0] in [4, 6]:
				line_ids = line[0] == 4 and [line[1]] or line[2]
				for line_id in line_ids:
					prod = line_obj.browse(cr, uid, line_id, context=context).product_id
					found=False
					if prod:
						if prod.x_is_main=='1':#prod.taxes_id:
							order_line.append([1, line_id, {'price_unit': rate}])
							found=True
						else:
							if prod.list_price:
								found=True
								order_line.append([1, line_id, {'price_unit': prod.list_price}])
					if found==False:# else:
						order_line.append([4, line_id])
			else:
				order_line.append(line)
		return {'value': {'order_line': order_line}}
			
	def has_custom_profile(self, cr, uid, ids, values, arg, context):
		x={}
		has_custom='0'
		for record in self.browse(cr, uid, ids):
			#check if deposit invoice already created. if then do not display create button
			sql = "select p.id from product_product p,product_template t,account_invoice o,account_invoice_line l where o.id=l.invoice_id and p.id=l.product_id and p.product_tmpl_id=t.id and t.x_prod_cat='deposit' and o.state not in('refund','cancel') and o.x_sale_order_id='%s' "% (record.id)
			cr.execute(sql)
			#if deposit invoice alredy created no need to create again
			rows1 = cr.fetchall()
			if len(rows1) > 0:
				has_custom = '0'
			else:	
				sql = "select p.id  from product_product p,product_template t,sale_order_line o where p.id=o.product_id and p.product_tmpl_id=t.id and t.x_prod_cat='customlength' and o.order_id='%s' " % (record.id)
				cr.execute(sql)
				rows = cr.fetchall()
				if len(rows) > 0:
					has_custom = '1'
				else:
					has_custom = '0'
			x[record.id] = has_custom 
		return x
		
	def cr_limit_over(self, cr, uid, ids, values, arg, context):
			
		x={}
		_over=False
		for record in self.browse(cr, uid, ids):
			if record.partner_id and record.partner_id.credit_limit>0:
				sql ="select sum(amount_total) from sale_order where partner_id='%s' and x_status='open'" % (record.partner_id.id)
				cr.execute(sql)
				rows = cr.fetchone()
				if rows == None or len(rows)==0:
					_over=False
				else:
					 if rows[0]!=None:
						if record.partner_id.credit_limit<rows[0]:
							_over=True
			x[record.id] = _over 
		return x
	def _get_tot_custom_lm(self, cr, uid, ids, context):
		_lm=0
		for record in self.browse(cr, uid, ids):
			for line in record.order_line:	
				if line.product_id.x_prod_cat=='customlength':
					_qty=line.x_order_qty
					_len=line.x_order_length
					_lm+= (_qty*_len*0.001)
		return _lm
		
	def create_deposit_chk(self, cr, uid, ids, values, arg, context):
		x={}
		_enabled=False
		for record in self.browse(cr, uid, ids):
			has_custom	= record.x_has_custom	 #--> checks if dep inv already created or not as well...
			if has_custom=='1':
				if not record.x_deposit_exmpt:
					_tot= self._get_tot_custom_lm(cr, uid, ids, context)
					#_logger.error("change_payment_term:line.create_deposit_chkcreate_deposit_chk11["+str(_tot)+"]["+str(record.id)+"]")
					if _tot>=200:
						_enabled=True
			x[record.id] = _enabled 
		return x	
	
	def tot_invoiced(self, cr, uid, ids, values, arg, context):
		x={}
		tot_amt = 0
		#id = ids[0]
		obj_inv = self.pool.get('account.invoice')
		args = [("x_sale_order_id", "=", ids[0])]
		#result = obj_inv.search(cr, uid, args, context=context)
		i=0
		for sale_id in obj_inv.search(cr, uid, args, context=context):
			#i+=1
			#_logger.error("change_payment_term:line.sale_id_sale_id["+str(sale_id)+"]["+str(i)+"]")
			_inv 	= obj_inv.browse(cr, uid, sale_id, context)
			tot_amt	+= _inv.amount_total
			
		for record in self.browse(cr, uid, ids):
			x[record.id]= tot_amt
		return x
	
	def tot_balance(self, cr, uid, ids, values, arg, context):
		x={}
		#tot_amt = 0
		#id = ids[0]
		for record in self.browse(cr, uid, ids):
			x[record.id]= record.amount_total-record.x_tot_invoiced
		return x
	
	def open_order_revise(self, cr, uid, ids, context=None):
		ctx = dict(context)
		compose_form_id		= self.pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'dincelaccount.view_dincelsale_order_revise_form')], limit=1) 	
		return {
				'name': _('Revise Order'),
				'type': 'ir.actions.act_window',
				'view_type': 'form',
				'view_mode': 'form',
				'res_model': 'dincelsale.order.revise',
				'views': [(compose_form_id, 'form')],
				'view_id': compose_form_id,
				'target': 'new',#current',#'target': 'new',
				'context': ctx,
			}
	
	def open_order_preview(self, cr, uid, ids, context=None):
		assert len(ids) == 1, 'This option should only be used for a single id at a time.'
		o = self.browse(cr, uid, ids)[0]
		if not o.x_order_attachs:
			self._create_sale_order_pdf(cr, uid, ids, context=context)
		
		#sql ="SELECT odoo_api_url FROM dincelaccount_config_settings"
		#cr.execute(sql)
		#rows = cr.fetchone()
		url=self.pool.get('dincelaccount.config.settings').report_preview_url(cr, uid, ids,"order",ids[0],context=context)		
		if url:#rows and len(rows) > 0:
			ctx = dict(context)
			#url= str(rows[0]) + "web/index.php?act=order&id="+str(ids[0])
			'''
			if o.x_order_attachs:
				ir_id=o.x_order_attachs.id
			else:
				fname="order_"+str(o.id)+".pdf"
				temp_path="/var/tmp/odoo/"+fname
				
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
					'datas_fname': fname, #           -> filename.csv 
					'res_model': self._name, #                                  -> My object_model
					'res_id': o.id,  #                                   -> the id linked to the attachment.
					'type': 'binary' 
					}
				
				ir_id = ir_attachement_obj.create(cr, uid, document_vals, context) 
				
				try:
					_obj = self.pool.get('sale.order')  
					_obj.write(cr, uid, o.id, {'x_order_attachs': ir_id})  
				except ValueError:
					ir_id = False #.......
			'''	
			return {
					  'name'     : 'Go to website',
					  'res_model': 'ir.actions.act_url',
					  'type'     : 'ir.actions.act_url',
					  'view_type': 'form',
					  'view_mode': 'form',
					  'target'   : 'current',
					  'url'      : url,
					  'context': ctx
				   }
		
	def open_invoice_preview(self, cr, uid, ids, context=None):
		assert len(ids) == 1, 'This option should only be used for a single id at a time.'
		o = self.browse(cr, uid, ids)[0]
		if o.x_account_ids:
			ctx = dict(context)
			#url="http://deverp.dincel.com.au/odoo/web/index.php?act=order_invoice&id="+str(o.id)
			#sql ="SELECT odoo_api_url FROM dincelaccount_config_settings"
			#cr.execute(sql)
			#rows = cr.fetchone()
			url=self.pool.get('dincelaccount.config.settings').report_preview_url(cr, uid, ids,"order_invoice",ids[0],context=context)		
			if url:#rows and len(rows) > 0:
				#url= str(rows[0]) + "web/index.php?act=order_invoice&id="+str(ids[0])
				if o.x_email_attachs:
					ir_id=o.x_email_attachs.id
				else:
					fname="order_invoice_"+str(o.id)+".pdf"
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
						'datas_fname': fname, #           -> filename.csv 
						'res_model': self._name, #                                  -> My object_model
						'res_id': o.id,  #                                   -> the id linked to the attachment.
						'type': 'binary' 
						}
					
					ir_id = ir_attachement_obj.create(cr, uid, document_vals, context) 
					
					try:
						_obj = self.pool.get('sale.order')  
						_obj.write(cr, uid, o.id, {'x_email_attachs': ir_id})  
					except ValueError:
						ir_id = False #.......
				
				return {
						  'name'     : 'Go to website',
						  'res_model': 'ir.actions.act_url',
						  'type'     : 'ir.actions.act_url',
						  'view_type': 'form',
						  'view_mode': 'form',
						  'target'   : 'current',
						  'url'      : url,
						  'context': ctx
					   }
		else:
			raise osv.except_osv(_('Invoice missing'),_('No invoice have been created yet.'))

	def _create_sale_order_pdf(self, cr, uid, ids, context=None):			
		assert len(ids) == 1, 'This option should only be used for a single id at a time.'
		o = self.browse(cr, uid, ids)[0]
		url=self.pool.get('dincelaccount.config.settings').report_preview_url(cr, uid, ids,"order",ids[0],context=context)		
		#if o.x_account_ids:
		ir_id = False
		if url:#rows and len(rows) > 0:
			ctx = dict(context)
			#url= str(rows[0]) + "web/index.php?act=order&id="+str(ids[0])
			if o.x_order_attachs:
				return o.x_order_attachs.id
			else:
				fname="order_"+str(o.id)+".pdf"
				temp_path="/var/tmp/odoo/"+fname
				
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
					'datas_fname': fname, #           -> filename.csv 
					'res_model': self._name, #                                  -> My object_model
					'res_id': o.id,  #                                   -> the id linked to the attachment.
					'type': 'binary' 
					}
				
				ir_id = ir_attachement_obj.create(cr, uid, document_vals, context) 
				
				try:
					_obj = self.pool.get('sale.order')  
					_obj.write(cr, uid, o.id, {'x_order_attachs': ir_id})  
				except ValueError:
					ir_id = False #......
					
		return ir_id
		
	def download_invoice_pdf(self, cr, uid, ids, context=None):
		fname="odoo_test.pdf"
		temp_path="/var/tmp/odoo/"+fname
		#if os.path.exists(temp_path):
		#	os.unlink(temp_path)
		#/f=open(temp_path,'w')
		#f.write(_str)
		#f.close();
		#_logger.error("generate_aba_testgenerate_aba_test2 ["+str(_str)+"]")
		return {'type' : 'ir.actions.act_url',
				'url': '/web/binary/some_html?f='+str(fname)+'&c=a',
				'target': 'self',}
	
	
	@api.multi 
	def loadsheet_pdf_byid(self, _id):
		o =self.env['sale.order'].browse(_id)
		#o=self.pool.get('sale.order').browse(cr, uid, _id, context)
		context = self._context.copy() 
		#url=self.pool.get('dincelaccount.config.settings').report_preview_url(cr, uid, ids,"loadsheet",_id,context=context)		
		url=self.env['dincelaccount.config.settings'].report_preview_url("loadsheet",_id)		
		if url:#rows and len(rows) > 0:
			
			fname="loadsheet"+str(o.id)+".pdf"
			save_path="/var/tmp/odoo/sale"
			
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
			#/web/binary/download_document?model=wizard.product.stock.report&amp;field=datas&amp;id=%s&amp;filename=product_stock.xls
			'''# 'name'     : 'Go to website',
					'res_model': 'ir.actions.act_url',
					'type'     : 'ir.actions.act_url',
					'view_type': 'form',
					'view_mode': 'form',
					'target'   : 'current',
					'url'      : url,
					'context': ctx'''
			return {
					'name': 'Load Sheet',
					'res_model': 'ir.actions.act_url',
					'type' : 'ir.actions.act_url',
					'url': '/web/binary/download_file?model=sale.order&field=datas&id=%s&path=%s&filename=%s' % (str(o.id),save_path,fname),
					'context': context}
	@api.multi 
	def print_pdf_load_sheet_dcs(self):
	#def print_pdf_load_sheet_dcs(self, cr, uid, ids, context=None):#self, cr, uid,  _id, context=None):
		#view_id = self.env.ref('dincelaccount.view_dincelaccount_voucher_invoice_form').id
		#context = self._context.copy()
		return self.loadsheet_pdf_byid(self.id)
					
	def send_invoice_email(self, cr, uid, ids, context=None):
		#compose_form_id=False
		#compose_form_id='dincelaccount_email_compose_message_form'	#False
		compose_form_id = self.pool.get('ir.ui.view').search(cr,uid,[('name', '=', 'dincelaccount.mail.compose.message.form')], limit=1)
		 
		_inv_ids=[]
		assert len(ids) == 1, 'This option should only be used for a single id at a time.'
		ir_model_data = self.pool.get('ir.model.data')
		o = self.browse(cr, uid, ids)[0]
		try:
			 
			template_id = ir_model_data.get_object_reference(cr, uid, 'dincelaccount', 'email_template_edi_saleorder_invoice')[1]
			email_obj   = self.pool.get('email.template')  
			 
			#get the id of the document, stored into field scanned
			#write the new attachment to mail template
			_atths=[]
			for line in o.x_account_ids:
				 
				if not line.x_invoice_attach:
					self.pool.get('account.invoice').create_invoice_pdf(cr, uid, ids,  {}, line.id)
				if line.x_invoice_attach and line.sent == False:
					_atths.append(line.x_invoice_attach.id)
					_inv_ids.append(line.id)
						#no_invoice=False
			if o.x_order_attachs and o.x_order_attachs.id:
				_atths.append(o.x_order_attachs.id)
			else:
				_id=self._create_sale_order_pdf(cr, uid, ids, context=context)
				if _id:
					_atths.append(_id)
			#ir_obj = self.pool.get('ir.attachement')
			ir_ids = self.pool['ir.attachment'].search(cr, uid, [('res_id', '=', ids[0]),('res_model', '=', 'sale.order'),], context=context)
			for _id in ir_ids:
				_atths.append(_id)
				
			email_obj.write(cr, uid, template_id, {'attachment_ids': [(6, 0, _atths)]})  #clears if any in session...if array is an empty....

		except ValueError:
			template_id = False #.......
		 
		_contact= self.pool.get('res.partner')
		
		lids1	= _contact.search(cr, uid, [('parent_id','=',o.partner_id.id),('x_is_project', '=', False)])	#site contacts
		lids2	= _contact.search(cr, uid, [('parent_id','=',o.x_project_id.id),('x_is_project', '=', False)])  #client contacts
		#_ids	= [lids1+lids2]
			
		fol_obj = self.pool.get('mail.followers')
		fol_ids = fol_obj.search(cr, uid, [
			('res_id', '=',  ids[0]),
			('res_model', '=', 'sale.order'),
		], context=context)
		
		lids3 = []
		def_ids = []
		'''
		for fol in fol_obj.browse(cr, uid, fol_ids, context=context):	
			lids3.append(fol.partner_id.id)
			def_ids.append(fol.partner_id.id)
		#if o.user_id and o.user_id.partner_id:
		#	if not o.user_id.parent_id.id in lids3:
		#		lids3.append(o.user_id.parent_id.id)
		if o.x_contact_id:
			def_ids.append(o.x_contact_id.id)
			'''
		lids4 = []
		_config_id = self.pool.get('dincelaccount.config.settings').search(cr,uid,[('id', '>', '0')], limit=1)
		if _config_id:
			_conf= self.pool.get('dincelaccount.config.settings').browse(cr, uid, _config_id, context=context)
			if _conf and _conf.invoice_cc_ids:
				#_logger.error("fol.partner_idfol.partner_idfol.partner_id ["+str(_config_id)+"]["+str(_conf.invoice_cc_ids)+"]")
				for _part in _conf.invoice_cc_ids:	
					lids4.append(_part.id)
					#_logger.error("fol.partner_idfol.partner_idfol.partner_id_id_id ["+str(_part.id)+"]")#	lids4.append(_id)
		#partner_ids+=[fol.partner_id]
			#_logger.error("fol.partner_idfol.partner_idfol.partner_id ["+str(fol.partner_id.id)+"]")
			#_ids.append(fol.partner_id.id)
		_ids = [lids1+lids2+lids3+lids4]		
		def_ids = [def_ids+lids4]
		
		#_logger.error("fol.partner_idfol.partner_idfol.lids1+lids2lids1+lids2 ["+str(lids1+lids2)+"]")
		#_logger.error("fol.partner_idfol.partner_idfol._ids_ids_ids ["+str(def_ids)+"]")
		
		ctx = dict(context)
		if template_id:
			ctx.update({
				'default_model': 'sale.order',
				'default_res_id': ids[0],
				'default_use_template': bool(template_id),
				'default_template_id': template_id,
				'default_subject': "Re. " + o.x_project_id.name,
				'default_composition_mode': 'comment',
				'mark_as_sent':True, #see below >>> inserit class >> "accountmail_compose_message"
				'default_inv_ids':_inv_ids,
				'domain_contact_ids':_ids,
				'default_contact_ids':_ids,
				'default_contact_sel_ids':def_ids,
				
			})
		
		return {
			'name': _('Compose Email'),
			'type': 'ir.actions.act_window',
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'mail.compose.message',
			'views': [(compose_form_id, 'form')],
			'view_id': compose_form_id,
			'target': 'new',#current',#'target': 'new',
			'context': ctx,
		}
		#return True
		
	def markas_send_email(self, cr, uid, ids, context=None):
		assert len(ids) == 1, 'This option should only be used for a single id at a time.'
		o = self.browse(cr, uid, ids)[0]
		for line in o.x_account_ids:
			if not line.x_invoice_attach:
				self.pool.get('account.invoice').create_invoice_pdf(cr, uid, ids,  {}, line.id)
		return self.pool.get('sale.order').write(cr, uid, ids[0], {'x_sent': True,'state':'sent'}) 
		
	def confirm_delivery_sales_order_xx(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		order_obj 	= self.pool.get('sale.order')
		obj_line 	= self.pool.get('sale.order.line')
		pick_obj 	= self.pool.get('dincelstock.pickinglist')
		line_obj 	= self.pool.get('dincelstock.pickinglist.line')
		ar_items_done 	= {}
		ar_items_rem  	= {}
		
		tot_qty_rem 	= 0
		found			= False
		for record in self.browse(cr, uid, ids, context=context):	
			sql = "select * from dincelstock_pickinglist_line where origin='%s' " % record.name
			cr.execute(sql)
			rows1 	= cr.dictfetchall()
			for row1 in rows1:
				ship_qty = row1['ship_qty']
				product_id = row1['product_id']
				order_length = row1['order_length']
				skey	= str(product_id) + "_" + str(order_length)
				if ar_items_done.has_key(skey) == False:
					ar_items_done[skey] = ship_qty
				else:
					ar_items_done[skey] += ship_qty
			
		
			for line in record.order_line:
				qty = line.x_order_qty
				product_id = line.product_id.id
				order_length = line.x_order_length
				skey	= str(product_id) + "_" + str(order_length)
				if ar_items_done.has_key(skey):
					qty = qty - ar_items_done[skey]
			
				tot_qty_rem += qty		
				
			#only if any remain qty is greater than zero
			if tot_qty_rem > 0 :
				sql = "select 1 from dincelstock_pickinglist  where origin='%s' " % record.name
				cr.execute(sql)
				count1 	= cr.rowcount
			
				sname_deli = record.name + "-" + str(count1+1)#"/"  #todo generated auto number
				vals = {
					'pick_order_id': record.id,
                    'origin': record.name,
                    'partner_id': record.partner_id.id,
					'name':sname_deli,
					'user_id':uid
					}
			
				vals['date_picking']=datetime.datetime.now() 
				#first create the invoice record
				pick_id = pick_obj.create(cr, uid, vals, context=context)
				
				#now loop throught all item lines and create invoice line if net qty remaining is greater than zero
				for line in record.order_line:
					qty = line.x_order_qty
					product_id = line.product_id.id
					order_length= line.x_order_length
					skey	= str(product_id) + "_" + str(order_length)
					if ar_items_done.has_key(skey):
						qty = qty - ar_items_done[skey]		
					if qty > 0:
						
						vals = {
							'product_id': product_id,
							'ship_qty': qty,
							'pickinglist_id': pick_id,
							'origin': record.name,
							'order_length': line.x_order_length,
							'price_unit': line.price_unit,
							'disc_pc':line.discount,
						}
						vals['name']= line.product_id.name
							
						line_obj.create(cr, uid, vals, context=context)
						
				found = True

				view_id = self.pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'dincelstock.delivery.form.view')], limit=1) 	
				#_logger.error("invoice_sales_validate.view_id["+str(view_id)+"]")
				value = {
                    'domain': str([('id', 'in', pick_id)]),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'dincelstock.pickinglist',
                    'view_id': view_id,
                    'type': 'ir.actions.act_window',
                    'name' : _('Delivery'),
                    'res_id': pick_id
                }
				return value				
				#return pick_id
		if found == False:
			raise osv.except_osv(_('No delivery remaining!'), _('No pending delivery found!'))
		return False
	
	def _over_due_check(self, cr, uid, ids, values, arg, context):
		
		x1={}
		_due=''
		for record in self.browse(cr, uid, ids):#for record in self.browse(cr, uid, ids):
			 
			sql ="SELECT i.date_invoice,t.x_payterm_code FROM account_invoice i,account_payment_term t WHERE i.payment_term=t.id and i.state='open' and i.x_inv_type in ('full','balance') and i.partner_id='%s' " % (str(record.partner_id.id))
			cr.execute(sql)
			#_logger.error("change_payment_term:_over_due_check_over_due_check["+str(sql)+"]")
			rows = cr.fetchall()
			if rows == None or len(rows)==0:
				_due= ''
			else:
				for row in rows:
					_dt=row[0]
					_term=row[1] #COD,30EOM,immediate,7DAYS,14DELI,14DAYS
					is_due=self._date_due_check(cr, uid, ids, _term, _dt, context)	
					if is_due:
						_due="Y"
						break
			x1[record.id] = _due 
		return x1
	
	def _date_due_check(self, cr, uid, ids, _term, _dt, context):
		#dt_due = date.today()
		dt_now = datetime.datetime.strptime(str(date.today()), '%Y-%m-%d')  #date.today()
		_dt1=datetime.datetime.strptime(_dt, '%Y-%m-%d')  
		#_logger.error("change_payment_term:_over_due_check_over_due_check_term_term["+str(_term)+"]["+str(_dt)+"]["+str(_dt1)+"]")
		if _term=="30EOM":
			_due = _dt1 + relativedelta(months=+2)
			_due_dt=str(_due.year) +"-"+str(_due.month)+"-1"
			dt_due=datetime.datetime.strptime(_due_dt, '%Y-%m-%d')
			#case "immediate":
			#case "COD":
			#	printf("n is a perfect square\n");
			#	break;
		elif _term=="7DAYS":
			dt_due = _dt1 + relativedelta(days=+7)
		elif _term=="14DELI" or _term=="14DAYS":
			dt_due = _dt1 + relativedelta(days=+14)
		else:
			#dt_due = date.today()
			dt_due=datetime.datetime.strptime(str(date.today()), '%Y-%m-%d')  
		if dt_due < dt_now:
			return True
		else:
			return False
	
	def get_colorname(self, cr, uid, ids, values, arg, context):
			
		x1={}
		_colr=''
		for record in self.browse(cr, uid, ids):#for record in self.browse(cr, uid, ids):
			if record.x_colorcode:
				sql ="SELECT name FROM dincelbase_color WHERE color_hex='%s' " % (record.x_colorcode)
				cr.execute(sql)
				rows = cr.fetchone()
				if rows == None or len(rows)==0:
					_colr= ''
				else:
					_colr= rows[0]
			else:
				_colr=''
			x1[record.id] = _colr 
		return x1
	
	def has_invoice(self, cr, uid, ids, values, arg, context):
		x={}
		_ret=False
		for record in self.browse(cr, uid, ids):
			if record.x_revise_sn>0:
				sql ="SELECT 1 FROM account_invoice WHERE x_sale_order_id='%s' AND x_revise_sn='%s' and state not in ('cancel','refund')" % (record.id, record.x_revise_sn)
			else:
				sql ="SELECT 1 FROM account_invoice WHERE x_sale_order_id='%s' AND x_inv_type = 'balance' and state not in ('cancel','refund') " % (record.id)
			cr.execute(sql)
			#_logger.error("invoice_sales_validate.has_invoicehas_invoice["+str(sql)+"]")
			rows = cr.fetchone()
			if rows:
				if len(rows)> 0:
					_ret = True
		x[record.id] = _ret 
		return x
	
	def _deposit_paid(self, cr, uid, ids, values, arg, context):
		x1={}
		_ret=''
		for record in self.browse(cr, uid, ids):#for record in self.browse(cr, uid, ids):
			#_ret = self._update_payment_deposit(cr, uid, ids, record.id, context=context)
			'''if record.x_deposit_exmpt:
				_ret= 'NA'
			else:
				sql ="SELECT 1 FROM sale_order_line l,product_product p,product_template t WHERE l.product_id=p.id AND t.id=p.product_tmpl_id AND l.order_id='%s' AND  t.x_prod_cat in('customlength')" % (record.id)
				cr.execute(sql)
				rows = cr.fetchone()
				if rows == None or len(rows)==0:
					_ret= 'NA'
				else:	
					sql ="SELECT state FROM account_invoice WHERE x_inv_type='deposit' AND type='out_invoice' AND x_sale_order_id='%s' " % (record.id)
					cr.execute(sql)
					rows = cr.fetchone()
					if rows == None or len(rows)==0:
						_ret= ''
					else:
						_ret= rows[0]'''
		
			x1[record.id] = _ret 
		return x1
	
	def _balance_paid(self, cr, uid, ids, values, arg, context):
		x1={}
		_ret=''
		#_paid=False
		#_other=False
		for record in self.browse(cr, uid, ids):#for record in self.browse(cr, uid, ids):
			'''sql ="SELECT state FROM account_invoice WHERE x_inv_type='balance' AND type='out_invoice' and state not in ('refund','cancel') AND x_sale_order_id='%s' " % (record.id)
			cr.execute(sql)
			rows_chk = cr.fetchall()
			if rows_chk == None or len(rows_chk)==0:
				_ret= ''
			else:
				for row in rows_chk: #if more than one invoice
					if row[0]=="paid":
						#@_paid=True
						_ret='paid'
					elif row[0]=="open" or row[0]=="draft": #state[paid/open/cancel/refund]
						if _ret=='paid':
							_ret='partial'
						elif _ret=='partial':
							_ret='partial'
						else:	
							_ret='open'
							'''
			#_ret = self._update_payment_balance(cr, uid, ids, record.id, context=context)#self._update_payment_deposit(cr, uid, ids, _id, context=context)	 
			#_ret = self._update_payment_balance(cr, uid, ids, record.id, context=context)#self._update_payment_deposit(cr, uid, ids, _id, context=context)	 
			x1[record.id] = _ret 
		return x1
		
	def _update_payment_deposit(self, cr, uid, ids, _id, context=None):
		obj 	= self.pool.get('sale.order').browse(cr, uid, _id, context=context)
		x_dep	= ''
		 
		if obj.x_deposit_exmpt:
			x_dep= 'NA'
		else:
			sql ="SELECT 1 FROM sale_order_line l,product_product p,product_template t WHERE l.product_id=p.id AND t.id=p.product_tmpl_id AND l.order_id='%s' AND  t.x_prod_cat in('customlength')" %  (str(_id))
			cr.execute(sql)
			rows = cr.fetchone()
			if rows == None or len(rows)==0:
				x_dep= 'NA'
			else:	
				sql ="SELECT state FROM account_invoice WHERE x_inv_type='deposit' AND type='out_invoice' AND x_sale_order_id='%s' " %  (str(_id))
				cr.execute(sql)
				rows = cr.fetchone()
				if rows == None or len(rows)==0:
					x_dep= ''
				elif rows[0]=="paid":
					x_dep= rows[0]
				else:
					x_dep= ''
		#if _id <832 and x_dep=="paid":
		#	x_dep="paid"
		#	pass
		#else:
			sql ="UPDATE sale_order SET  x_dep_paid='"+x_dep+"' "	# WHERE id='"+str(ids[0])+"'"
			sql += " WHERE id='"+str(_id)+"'"	
		#	#_logger.error("updatelink_order_dcs.updatelink_sqlsqlsql["+str(sql)+"]")	
			cr.execute(sql)		
		return x_dep  
		
	def _update_payment_balance(self, cr, uid, ids, _id, context=None):
		sql ="SELECT state FROM account_invoice WHERE x_inv_type='balance' AND state in ('open','paid') AND type='out_invoice' AND x_sale_order_id='%s' " % (str(_id))
		cr.execute(sql)
		rows_chk = cr.fetchall()
		x_bal=''
		if rows_chk == None or len(rows_chk)==0:
			x_bal= ''
		else:
			for row in rows_chk: #if more than one invoice
				if row[0]=="paid":
					#@_paid=True
					x_bal='paid'
				else:#found open (or not paid) if more than one invoice
					if x_bal=='paid':
						x_bal='part'
					elif x_bal=='part':
						x_bal='part'
					else:	
						x_bal=''
					#x_bal='part'
		#if _id <832 and x_bal=="paid":
		#	x_bal="paid"
		#	pass
		#else:
			sql ="UPDATE sale_order SET x_bal_paid='"+x_bal+"' "	# WHERE id='"+str(ids[0])+"'"
			sql += " WHERE id='"+str(_id)+"'"	
		#	#_logger.error("updatelink_order_dcs.updatelink_sqlsqlsql["+str(sql)+"]")	
			cr.execute(sql)
		return x_bal
		
	def update_payment_order(self, cr, uid, ids, _id, context=None):
		if context is None:
			context = {}
		
		self._update_payment_deposit(cr, uid, ids, _id, context=context)
		self._update_payment_balance(cr, uid, ids, _id, context=context)
		return True
		
	_columns={
		'x_account_ids': fields.one2many('account.invoice', 'x_sale_order_id', 'Invoices'),
		'x_credit_limit': fields.related('partner_id', 'credit_limit', type='float', string='Credit Limit', store=False),
		'x_rate_note': fields.related('partner_id', 'x_rate_note', type='char', string='Rate Note', store=False),
		'x_qty_tot_profile': fields.float('Total Profile Qty', digits=(16,2)),
		'x_origin_order': fields.many2one('dincelsale.ordersale','Origin Order'),
		#'x_colourname': fields.char('Colour'),	
		'x_cr_limit_over': fields.function(cr_limit_over, method=True, string='Cr Limit', type='boolean'),
		'x_create_deposit': fields.function(create_deposit_chk, method=True, string='create deposit chk', type='boolean'), #-- check if deposit invoice to create...
		#'x_create_balance': fields.function(create_balance_chk, method=True, string='create_balance_chk', type='boolean'),
		'x_has_custom': fields.function(has_custom_profile, method=True, string='Has custom profile', type='char'),
		'x_tot_invoiced': fields.function(tot_invoiced, method=True, string='Total Invoiced',type='float'),
		'x_tot_balance': fields.function(tot_balance, method=True, string='Balance Amount',type='float'),
		'x_pickinglist_ids': fields.one2many('dincelstock.pickinglist', 'pick_order_id','Deliveries'),
		'x_project_id': fields.many2one('res.partner','Project / Site'),	
		'x_project_suburb_id': fields.related('x_project_id', 'x_suburb_id',  string='Suburb', type="many2one", relation="dincelbase.suburb",store=True),		
		'x_contact_id': fields.many2one('res.partner','Contact Person'),		
		'x_quote_id': fields.many2one('account.analytic.account','Quote'),		
		'x_warehouse_id': fields.many2one('stock.warehouse','Dispatch Location'),		
		'x_street': fields.char('Street'),	
		'x_postcode': fields.char('Postcode'),	
		'x_suburb': fields.char('Suburb'),	
		'x_state_id': fields.many2one('res.country.state','State'),		
		'x_country_id': fields.many2one('res.country','Country'),
		'x_deposit_exmpt': fields.boolean('Deposit Exempt'),
		'x_sent': fields.boolean('Sent'),
		'x_pudel':fields.selection([
			('pu','Pickup'),
			('del','Delivery'),
			], 'Pickup/Delivery'),
		'x_ac_status':fields.selection([
			('hold','Hold'),
			('open','Open'),
			('part','Part'),
			('paid','Paid'),
			], 'A/c Status'),	
		'x_prod_status':fields.selection([
			('queue','Queue'),
			('part','Part'),
			('complete','Complete'),
			], 'Production Status'),		
		'x_del_status':fields.selection([
			('none','None'),
			('part','Part'),
			('delivered','Delivered'),
			], 'Delivery Status'),		
		'x_status':fields.selection([ #as in dcs open /close/ cancel
			('open','Open'),
			('close','Closed'),
			('cancel','Cancelled'),
			], 'Status'),	
		'x_dt_request':fields.date("Requested Date"),		
		'x_dt_process': fields.datetime("Order Entry Date"),
		'x_dt_anticipate': fields.date("Anticipate Date"),
		'x_dt_actual': fields.date("Actual Date"),
		'x_type_request': fields.selection([
				('tba', 'TBA'),
				('asap', 'ASAP'),
				('dt', 'Date')],"Type Requested"),
		'x_type_anticipate': fields.selection([
				('tba', 'TBA'),
				('na', 'NA'),
				('dt', 'Date')],"Type Anticipate"),
		'x_type_actual': fields.selection([
				('tba', 'TBA'),
				('na', 'NA'),
				('dt', 'Date')],"Type Actual"),
		#'x_dt_deposit': fields.date("Deposit Date"), #>> to be done by function...auto calculate date..but make store = true for sorting function
		#'x_dt_balance': fields.date("Balance Date"), #>> to be done by function...auto calculate date..but make store = true for sorting function
		'x_region_id': fields.many2one('dincelaccount.region', 'A/c Region'),
		'x_coststate_id':fields.many2one("res.country.state","Cost Centre"),
		'x_colorcode': fields.char('Colour Code'),	
		'x_colorname': fields.function(get_colorname, method=True, string='Colour Name',type='char'), 
		'x_over_due': fields.function(_over_due_check, method=True, string='Overdue?',type='char'), 
		#'x_get_quote': fields.function(get_quote_no, method=True, string='Quote',type='char'),
		#'x_new_lines': fields.one2many('sale.order.line.new', 'order_id', 'New Lines'),
		#'x_old_lines': fields.one2many('sale.order.line.old', 'order_id', 'Old Lines'),
		'x_email_attachs':fields.many2one('ir.attachment','Invoice Attachments'),
		'x_order_attachs':fields.many2one('ir.attachment','Order Attachments'),
		'x_origin_id':fields.many2one('sale.order','Order Origin'), #>>in case of revisions orders
		'x_revision_ids': fields.one2many('sale.order', 'x_origin_id','Revision History'),
		'x_revision_bak_ids': fields.one2many('sale.order.bak', 'origin_id','Revision History'),
		'x_revise_sn': fields.integer('Revise SN', size=2),	
		'x_has_invoice': fields.function(has_invoice, method=True, string='has invoice',type='boolean'),#fields.integer('Revise Count', size=2),
		'x_revision': fields.boolean('Is Revision'),
		'x_revise_type':fields.selection([ #>>as revise type
			('shipment','Shipment'),
			('rate','Price changed'),
			('order','Qty changed'),
			('other','Other'),
			], 'Revise type'),
		'x_type':fields.selection([ #>>as revise,cancel,normal
			('normal','Normal'),
			('revise','Revised'),
			('cancel','Cancelled'),
			], 'Type'),
		'state': fields.selection([	#>>overwrite the status....for labeling etc...
			('draft', 'Draft'),
			('sent', 'Sent'),
			('cancel', 'Cancelled'),
			('waiting_date', 'Waiting Schedule'),
			('progress', 'Progress'),
			('manual', 'Manual'),
			('shipping_except', 'Shipping Exception'),
			('invoice_except', 'Invoice Exception'),
			('done', 'Done'),
			], 'Status', readonly=True, copy=False, help="Gives the status of the sales order.\
			\nThe exception status is automatically set when a cancel operation occurs \
			in the invoice validation (Invoice Exception) or in the picking list process (Shipping Exception).\nThe 'Waiting Schedule' status is set when the invoice is confirmed\
			but waiting for the scheduler to run on the order date.", select=True),	
		'x_deposit_paid': fields.function(_deposit_paid, method=True, string='Deposit Paid',type='char'), #DO NOT USE
		'x_balance_paid': fields.function(_balance_paid, method=True, string='Balance Paid',type='char'), #DO NOT USE
		'x_dep_paid': fields.char('Deposit Paid', size=5),	
		'x_bal_paid': fields.char('Balance Paid', size=5),	
		'x_pending': fields.boolean('Payment Pending'),	
		
		}
	
	_defaults = {
		'x_revision':False,
		'x_pending':False,
		'x_revise_sn':0,
		'x_status': 'open',
		'x_type': 'normal',
		'x_ac_status': 'hold',
		'x_dt_process' : fields.date.context_today, 
	}
		
	def unlink(self, cr, uid, ids, context=None, check=True):
		context = dict(context or {})
		if context is None:
			context = {}
		lids 	= self.pool.get('account.invoice').search(cr, uid, [('x_sale_order_id', '=', ids[0])])
		if len(lids)>0:
			raise Warning(_('You cannot delete a sales order after an invoice has been generated.'))
			#raise osv.except_osv(_('Error!'), _('You cannot delete a sales order after an invoice has been generated.'))
		else:	 
			result = super(dincelaccount_sale_order, self).unlink(cr, uid, ids, context)
			return result
	
	def write(self, cr, uid, ids, vals, context=None):
		has_custom=None 
		#prod=self.pool.get("dincelmrp.production")
		res = super(dincelaccount_sale_order, self).write(cr, uid, ids, vals, context=context)
		for record in self.browse(cr, uid, ids):
			id			= record.id	
			has_custom	= record.x_has_custom	
			stateid=record.x_coststate_id
			if not stateid:
				raise osv.except_osv(_('Error!'), _('Project/site state is missing.'))
			self._update_payment_deposit(cr, uid, ids, id, context=context) 
		return res	
	
	def onchange_order_line_dcs(self, cr, uid, ids, order_line, x_region_id, context=None):
		context = context or {}
		#_logger.error("onchange_order_line_dcs.order_line["+str(order_line)+"]["+str(x_region_id)+"]")
		#if not order_line:
		#	return {}
		'''
		line_ids = self.resolve_2many_commands(cr, uid, 'order_line', order_line, ['x_region_id'], context)
		region_id= None
		#_logger.error("onchange_order_line_dcs.line_ids["+str(line_ids)+"]["+str(x_region_id)+"]["+str(order_line)+"]")	  
		for line in line_ids:
			if line['x_region_id']:
				region_id = line['x_region_id']
				#break 
		return {'value': {'x_region_id': region_id}}'''
		
	def last_day_of_month(self, any_day):
		next_month = any_day.replace(day=28) + datetime.timedelta(days=4)  # this will never fail
		return next_month - datetime.timedelta(days=next_month.day)
	
	def button_open_partner_form(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		for record in self.browse(cr, uid, ids, context=context):	
			partner_id=record.partner_id.id 
			#//obj = self.pool.get('sale.order')
			view_id = self.pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'dincelaccount.partner.new.form.view')], limit=1) 	
			value = {
				'type': 'ir.actions.act_window',
				'name': _('Partner'),
				'view_type': 'form',
				'view_mode': 'form',
				'res_model': 'res.partner',
				'domain': str([('id', 'in', partner_id)]),
				#'context':{'search_default_id': partner_id},
				'view_id': view_id,
				'res_id':partner_id
			}
			#_logger.error("button_open_partner_form_ididid["+str(view_id)+"]partner_id["+str(partner_id)+"]")	
			return value	
			
	def button_sales_orders(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		for record in self.browse(cr, uid, ids, context=context):	
			partner_id=record.partner_id.id 
			#obj = self.pool.get('sale.order')
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
	
	def _create_balance_normal(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		obj_inv 	= self.pool.get('account.invoice')	
		obj_invline	= self.pool.get('account.invoice.line')
		product_obj = self.pool.get('product.product')	
		tot_price 	= 0	
		for record in self.browse(cr, uid, ids, context=context):		
			vals = {
					'x_sale_order_id': record.id,
					'x_inv_type':'balance',
                    'origin': record.name,
                    'reference': record.name,
                    'partner_id': record.partner_id.id,
					'user_id':record.user_id.id,
					#'internal_number': record.name, #cannot delete once this value is recorded
					'section_id': 1,
                    'type': 'out_invoice',
					'account_id':record.partner_id.property_account_receivable.id
					}
			
			vals['date_invoice']=datetime.datetime.now() 
			vals['date_due']=vals['date_invoice']
			#_logger.error("invoice_sales_validate.payment_termpayment_term["+str(record.payment_term)+"]")
			if record.payment_term: 
				
				code 	 = record.payment_term.x_payterm_code
				vals['payment_term']=record.payment_term.id
				if code:	
					if code == "30EOM":
						dt1=vals['date_invoice'] + datetime.timedelta(365/12)
						vals['date_due']= self.last_day_of_month(dt1)
						#_logger.error("invoice_sales_validate.x_payterm_codex_payterm_code["+str(dt1)+"]["+str(vals['date_due'])+"]")
						#date_after_month = datetime.today()+ relativedelta(months=1) 
						#elif code == "COD":
						#	vals['date_due']=vals['date_invoice']
						
			proj_id = record.x_project_id and record.x_project_id.id  or False		
			if proj_id:
				vals['x_project_id']=proj_id
				
			#first create the invoice record
			inv_id = obj_inv.create(cr, uid, vals, context=context)
			
			for line in record.order_line:
				qty = line.product_uom_qty
				product_id = line.product_id.id
				#if ar_items_done.has_key(product_id):
				#	qty = qty - ar_items_done[product_id]		
				if qty > 0:
					
					vals = {
						'product_id': product_id,
						'quantity': qty,
						'invoice_id': inv_id,
						'origin': record.name,
						'discount':line.discount,
						'price_unit': line.price_unit,
						'price_subtotal': line.price_unit*qty,
						'x_order_length':line.x_order_length,
						'x_order_qty':line.x_order_qty,
					}
					vals['name']= line.product_id.name
					
					if line.x_region_id:
						vals['x_region_id']= line.x_region_id.id	
					if line.x_coststate_id:
						vals['x_coststate_id']= line.x_coststate_id.id	
						
					#_logger.error("change_payment_termvalsvals["+str(vals)+"]")
					#todo...somethiems taxes not being recorded in invoice...14/7/2016
					if line.product_id.taxes_id:
						vals['invoice_line_tax_id'] = [(6, 0, line.product_id.taxes_id.ids)]
								
					obj_invline.create(cr, uid, vals, context=context)
			
			#--------------------------------------------------------------------
			#now create deposit balance, as negative to balance out the total
			_ids = obj_inv.search(cr, uid, [('x_inv_type', '=', 'deposit'),('x_sale_order_id', '=', record.id),('state', '!=', 'cancel')]) 	
			for record1 in obj_inv.browse(cr, uid, _ids, context=context):	
				for line1 in record1.invoice_line:
					vals = {
						'product_id': line1.product_id.id,
						'quantity': line1.quantity,
						'invoice_id': inv_id,
						'origin': record.name,
						'discount':line1.discount,
						'price_unit': -line1.price_unit,
						'price_subtotal': -line1.price_unit*qty,
					}
					vals['name']= line1.product_id.name
					
					if line1.x_region_id:
						vals['x_region_id']= line1.x_region_id.id	
					if line1.x_coststate_id:
						vals['x_coststate_id']= line1.x_coststate_id.id		
						 
					#_logger.error("change_payment_termvalsvals["+str(vals)+"]")
					#todo...somethiems taxes not being recorded in invoice...14/7/2016
					if line1.product_id.taxes_id:
						vals['invoice_line_tax_id'] = [(6, 0, line1.product_id.taxes_id.ids)]
								
					obj_invline.create(cr, uid, vals, context=context)
			obj_inv = self.pool.get('account.invoice')
			obj_inv = obj_inv.browse(cr, uid, inv_id, context)
			obj_inv.button_compute(True) #For taxes
			
			#--------------
			if record.x_ac_status==None or record.x_ac_status=="hold":
				self.write(cr, uid, [record.id], {'x_ac_status':'open'})	
			#--------------
			
			#str1 = "amttax["+str(obj_inv.amount_tax) + "]amtuntax["+str(obj_inv.amount_untax) + "] calculated["+str(obj_inv.amount_untax*0.1) + "]" 
			#_logger.error("change_payment_term:tax_id_tax_id_tax_id_tax_id["+str1+"]")
			view_id 		= self.pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'dincelaccount.invoice.form')], limit=1) 	
			#_logger.error("invoice_sales_validate.view_id["+str(view_id)+"]")
			value = {
				'domain': str([('id', 'in', inv_id)]),
				'view_type': 'form',
				'view_mode': 'form',
				'res_model': 'account.invoice',
				'view_id': view_id,
				'type': 'ir.actions.act_window',
				'name' : _('Invoice'),
				'res_id': inv_id
			}
			return value
				
	def _find_in_itemsdone(self, cr, uid, ids, _arr, _item, context=None):
		vals1 ={
				'found':0,
				'qty':0,
				'rate':0,
				'qty1':0,
				'rate1':0,
			}
		
		for _line in _arr:
			if _line['product_id'] ==_item['product_id'] and _line['order_len'] ==_item['order_len']:
				vals1['found']=1
				vals1['qty']=_line['order_qty'] - _item['order_qty']
				vals1['rate']=_line['price_unit'] - _item['price_unit']
				vals1['qty1']= _item['order_qty']
				vals1['rate1']= _item['price_unit']
				
		return vals1
		
	def _create_balance_revised(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		obj_inv 	= self.pool.get('account.invoice')	
		obj_invline	= self.pool.get('account.invoice.line')
		product_obj = self.pool.get('product.product')	
		tot_price 	= 0	
		ar_items_done 	= []
		for record in self.browse(cr, uid, ids, context=context):		
			#for record in self.browse(cr, uid, ids, context=context):		
			vals = {
					'x_sale_order_id': record.id,
					'x_inv_type':'balance',
                    'origin': record.name,
                    'reference': record.name,
                    'partner_id': record.partner_id.id,
					'x_revise_sn': record.x_revise_sn,
					'user_id':record.user_id.id,
					#'internal_number': record.name, #cannot delete once this value is recorded
					'section_id': 1,
                    'type': 'out_invoice',
					'account_id':record.partner_id.property_account_receivable.id
					}
			
			vals['date_invoice']=datetime.datetime.now() 
			vals['date_due']=vals['date_invoice']
			#_logger.error("invoice_sales_validate.payment_termpayment_term["+str(record.payment_term)+"]")
			if record.payment_term: 
				
				code 	 = record.payment_term.x_payterm_code
				vals['payment_term']=record.payment_term.id
				if code:	
					if code == "30EOM":
						dt1=vals['date_invoice'] + datetime.timedelta(365/12)
						vals['date_due']= self.last_day_of_month(dt1)
						#_logger.error("invoice_sales_validate.x_payterm_codex_payterm_code["+str(dt1)+"]["+str(vals['date_due'])+"]")
						#date_after_month = datetime.today()+ relativedelta(months=1) 
						#elif code == "COD":
						#	vals['date_due']=vals['date_invoice']
						
			proj_id = record.x_project_id and record.x_project_id.id  or False		
			if proj_id:
				vals['x_project_id']=proj_id
				
			#first create the invoice record
			inv_id = obj_inv.create(cr, uid, vals, context=context)
			#balance out old invoice lines...
			_sn=len(record.order_line)#record1.invoice_line=
			_ids = obj_inv.search(cr, uid, [('x_inv_type', '=', 'balance'),('x_sale_order_id', '=', record.id)]) 	
			for record1 in obj_inv.browse(cr, uid, _ids, context=context):	
				for line1 in record1.invoice_line:
					vals1 ={
						'sequence':_sn,
						'product_id':line1.product_id.id,
						'x_order_length':line1.x_order_length,
						'x_order_qty':-line1.x_order_qty,
						'price_unit':line1.price_unit,
						'quantity':-line1.quantity,
						'invoice_id': inv_id,
						'origin': record.name,
						'name': line1.name + " *[INV " + str(line1.invoice_id.id) +"]",
						'discount':line1.discount,
						'price_subtotal': line1.price_unit*line1.quantity,
					}
					if line1.x_region_id:
						vals1['x_region_id']= line1.x_region_id.id	
					if line1.x_coststate_id:
						vals1['x_coststate_id']= line1.x_coststate_id.id		
						
					if line1.product_id.taxes_id:
						vals1['invoice_line_tax_id'] = [(6, 0, line1.product_id.taxes_id.ids)]	
						
					ar_items_done.append(vals1)
					obj_invline.create(cr, uid, vals1, context=context)
					_sn=_sn+1
					
			#new items....			
			_sn=0
			for line in record.order_line:
				qty = line.product_uom_qty
				product_id = line.product_id.id
				
				if qty > 0:
					
					vals = {
						'sequence':_sn,
						'product_id': product_id,
						'quantity': qty,
						'invoice_id': inv_id,
						'origin': record.name,
						'discount':line.discount,
						'price_unit': line.price_unit,
						'price_subtotal': line.price_unit*qty,
						'x_order_length':line.x_order_length,
						'x_order_qty':line.x_order_qty,
					}
					vals['name']= line.product_id.name
					
					if line.x_region_id:
						vals['x_region_id']= line.x_region_id.id	
					if line.x_coststate_id:
						vals['x_coststate_id']= line.x_coststate_id.id		
						 
					#_logger.error("change_payment_termvalsvals["+str(vals)+"]")
					#todo...somethiems taxes not being recorded in invoice...14/7/2016
					if line.product_id.taxes_id:
						vals['invoice_line_tax_id'] = [(6, 0, line.product_id.taxes_id.ids)]	
					obj_invline.create(cr, uid, vals, context=context)
					_sn=_sn+1
					
			obj_inv = self.pool.get('account.invoice')
			obj_inv = obj_inv.browse(cr, uid, inv_id, context)
			obj_inv.button_compute(True) #For taxes
			if obj_inv.amount_total<0: #then refund invoice
				sql ="UPDATE account_invoice SET type='out_refund' WHERE id=" + str(inv_id)
				cr.execute(sql)
			#--------------
			if record.x_ac_status==None or record.x_ac_status=="hold":
				self.write(cr, uid, [record.id], {'x_ac_status':'open'})	
			#--------------
			
			#str1 = "amttax["+str(obj_inv.amount_tax) + "]amtuntax["+str(obj_inv.amount_untax) + "] calculated["+str(obj_inv.amount_untax*0.1) + "]" 
			#_logger.error("change_payment_term:tax_id_tax_id_tax_id_tax_id["+str1+"]")
			view_id = self.pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'dincelaccount.invoice.form')], limit=1) 	
			#_logger.error("invoice_sales_validate.view_id["+str(view_id)+"]")
			value = {
				'domain': str([('id', 'in', inv_id)]),
				'view_type': 'form',
				'view_mode': 'form',
				'res_model': 'account.invoice',
				'view_id': view_id,
				'type': 'ir.actions.act_window',
				'name' : _('Invoice'),
				'res_id': inv_id
			}
			return value
		#_logger.error("_create_balance_revised.ar_items_donear_items_done["+str(ar_items_done)+"]")
		
	def create_balance_invoice(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		#for record in self.browse(cr, uid, ids, context=context):	
			#gets all invoiced items qty
		zero_price=True
		for record in self.browse(cr, uid, ids, context=context):	
			for line in record.order_line:
				if line.price_unit>0:
					zero_price=False
			if zero_price==True:
				raise osv.except_osv(_('Error'),
									_('Zero or invalid rate found.'))
			if record.x_revise_sn > 0:
				return self._create_balance_revised(cr, uid, ids, context=context)
			else:
				return self._create_balance_normal(cr, uid, ids, context=context)
				
	def create_balance_invoicexx(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		obj_inv 	= self.pool.get('account.invoice')	
		obj_invline	= self.pool.get('account.invoice.line')
		product_obj = self.pool.get('product.product')	
		tot_price 	= 0
		
		ar_items_done 	= {}
		ar_items_rem  	= {}
		
		tot_qty_rem 	= 0
		 
		#sname = None
		for record in self.browse(cr, uid, ids, context=context):	
			#gets all invoiced items qty
			#if record.x_revise_sn>0:
			#else:
			
			sql = "select * from account_invoice_line where origin='%s' " % record.name
			cr.execute(sql)
			rows1 	= cr.dictfetchall()
			for row1 in rows1:
				qty = row1['quantity']
				product_id = row1['product_id']
				if ar_items_done.has_key(product_id) == False:
					ar_items_done[product_id] = qty
				else:
					ar_items_done[product_id] += qty
			#now calculate the net remaining qty		
			for line in record.order_line:
				qty = line.product_uom_qty
				product_id = line.product_id.id
				if ar_items_done.has_key(product_id):
					qty = qty - ar_items_done[product_id]
			
				tot_qty_rem += qty		
			
			#only if any remain qty is greater than zero
			if tot_qty_rem > 0 :
				
				vals = {
					'x_sale_order_id': record.id,
					'x_inv_type':'balance',
                    'origin': record.name,
                    'reference': record.name,
                    'partner_id': record.partner_id.id,
					#'internal_number': record.name, #cannot delete once this value is recorded
					'section_id': 1,
                    'type': 'out_invoice',
					'account_id':record.partner_id.property_account_receivable.id
					}
			
				vals['date_invoice']=datetime.datetime.now() 
				vals['date_due']=vals['date_invoice']
				#_logger.error("invoice_sales_validate.payment_termpayment_term["+str(record.payment_term)+"]")
				if record.payment_term: 
					
					code 	 = record.payment_term.x_payterm_code
					vals['payment_term']=record.payment_term.id
					if code:	
						if code == "30EOM":
							dt1=vals['date_invoice'] + datetime.timedelta(365/12)
							vals['date_due']= self.last_day_of_month(dt1)
							#_logger.error("invoice_sales_validate.x_payterm_codex_payterm_code["+str(dt1)+"]["+str(vals['date_due'])+"]")
							#date_after_month = datetime.today()+ relativedelta(months=1) 
							#elif code == "COD":
							#	vals['date_due']=vals['date_invoice']
							
				proj_id = record.x_project_id and record.x_project_id.id  or False		
				if proj_id:
					vals['x_project_id']=proj_id
					
				#first create the invoice record
				inv_id = obj_inv.create(cr, uid, vals, context=context)
				
				#now loop throught all item lines and create invoice line if net qty remaining is greater than zero
				for line in record.order_line:
					qty = line.product_uom_qty
					product_id = line.product_id.id
					if ar_items_done.has_key(product_id):
						qty = qty - ar_items_done[product_id]		
					if qty > 0:
						
						vals = {
							'product_id': product_id,
							'quantity': qty,
							'invoice_id': inv_id,
							'origin': record.name,
							'discount':line.discount,
							'price_unit': line.price_unit,
							'price_subtotal': line.price_unit*qty,
						}
						vals['name']= line.product_id.name
						
						if line.x_region_id:
							vals['x_region_id']= line.x_region_id.id	
						if line.x_coststate_id:
							vals['x_coststate_id']= line.x_coststate_id.id	
						
						#_logger.error("change_payment_termvalsvals["+str(vals)+"]")
						#todo...somethiems taxes not being recorded in invoice...14/7/2016
						if line.product_id.taxes_id:
							vals['invoice_line_tax_id'] = [(6, 0, line.product_id.taxes_id.ids)]
									
						obj_invline.create(cr, uid, vals, context=context)
				
				#check if deposit items exists	
				product_id =  product_obj.find_deposit_product(cr, uid, context=context)
				if product_id:
					#_logger.error("change_payment_term:line.product_id["+str(product_id)+"]")
					product_id	 = product_id[0]
					product_obj  = product_obj.browse(cr, uid, product_id, context)
					tot_amt = 0
					args = [("product_id", "=", product_id),("origin", "=", record.name)]
					#now find the item in the invoice line list
					for line_id in obj_invline.search(cr, uid, args, context=context):
						_invl 	 = obj_invline.browse(cr, uid, line_id, context)
						tot_amt	+= _invl.price_subtotal
						#for _tax in _invl.invoice_line_tax_id:
						#	tot_amt	+= _tax.amount * _invl.price_subtotal
					#if it has deposit invoice. then create invoice line for balancing with negative value	
					if tot_amt > 0:	
						vals = {
							'product_id': product_id,
							'quantity': '1',
							'invoice_id': inv_id,
							'origin': record.name,
							'price_unit': -tot_amt,
							'price_subtotal': -tot_amt,
						}
						
						vals['name']	= product_obj.name
						#if x_region_id:
						#	vals['x_region_id']	= x_region_id
						#_logger.error("change_payment_term:line.tax_id_tax_id["+str(product_obj.taxes_id)+"]")
						if product_obj.taxes_id:
							vals['invoice_line_tax_id'] = [(6, 0, product_obj.taxes_id.ids)]
									
						obj_invline.create(cr, uid, vals, context=context)
				else:
					#no deposit invoice
					self.write(cr, uid, [record.id], {'state':'progress'})	
					
				#for taxes reset
				obj_inv = self.pool.get('account.invoice')
				obj_inv = obj_inv.browse(cr, uid, inv_id, context)
				obj_inv.button_compute(True) #For taxes
				
				#--------------
				if record.x_ac_status==None or record.x_ac_status=="hold":
					self.write(cr, uid, [record.id], {'x_ac_status':'open'})	
				#--------------
				
				#str1 = "amttax["+str(obj_inv.amount_tax) + "]amtuntax["+str(obj_inv.amount_untax) + "] calculated["+str(obj_inv.amount_untax*0.1) + "]" 
				#_logger.error("change_payment_term:tax_id_tax_id_tax_id_tax_id["+str1+"]")
				view_id 		= self.pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'dincelaccount.invoice.form')], limit=1) 	
				#_logger.error("invoice_sales_validate.view_id["+str(view_id)+"]")
				value = {
					'domain': str([('id', 'in', inv_id)]),
					'view_type': 'form',
					'view_mode': 'form',
					'res_model': 'account.invoice',
					'view_id': view_id,
					'type': 'ir.actions.act_window',
					'name' : _('Invoice'),
					'res_id': inv_id
				}
				return value	
	
	
	@api.multi
	def make_invoice_payment(self):
		view_id = self.env.ref('dincelaccount.view_dincelaccount_voucher_invoice_form').id
		context = self._context.copy()
		so =self.env['sale.order'].browse(self.id)# self.pool['sale.order'].browse(cr, uid, self.id, context=context)
		#_logger.error("_create_balance_revised.make_invoice_paymentmake_invoice_payment["+str(so.partner_id.id)+"]")
		context['partner_id']=so.partner_id.id
		context['type']="receipt"
		return {
			'name':'Invoice Payment',
			'view_type':'form',
			'view_mode':'form',
			'views' : [(view_id,'form')],
			'res_model':'account.voucher',
			'view_id':view_id,
			'type':'ir.actions.act_window',
			#'partner_id':so.partner_id.id,
			#'target':'new',
			'context':context,
		}
		
	'''def open_deposit_invoice(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		view_id 		= self.pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'dincelaccount.invoice.form')], limit=1) 	
		inv_id = 232
		value = {
			'domain': str([('id', 'in', inv_id)]),
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'account.invoice',
			'view_id': view_id,
			'type': 'ir.actions.act_window',
			'name' : _('Invoice'),
			'res_id': inv_id
		}
		return value	
	'''	
		
	def create_deposit_invoice(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		obj_inv 	= self.pool.get('account.invoice')	
		obj_invline	= self.pool.get('account.invoice.line')
		product_obj = self.pool.get('product.product')	
		tot_price = 0
		zero_price=True
		for record in self.browse(cr, uid, ids, context=context):	
			for line in record.order_line:
				if line.price_unit>0:
					zero_price=False
				if line.product_id.x_prod_cat =='customlength':
					qty = line.product_uom_qty
					price_unit=line.price_unit 
					tot_price += qty*price_unit
		if zero_price==True:
			raise osv.except_osv(_('Error'),
									_('Zero or invalid rate found.'))
		
		if tot_price > 0:
			tot_price = 0.33*tot_price #33 % of custom length
			#_logger.error("change_payment_term:line.tot_price["+str(tot_price)+"]")
			product_id =  product_obj.find_deposit_product(cr, uid, context=context)
			if product_id:
				#_logger.error("change_payment_term:line.product_id["+str(product_id)+"]")
				product_id	 = product_id[0]
				product_obj  =  product_obj.browse(cr, uid, product_id, context)
				vals = {
					'x_sale_order_id': record.id,
					'x_inv_type':'deposit',
                    'origin': record.name,
                    'reference': record.name,
                    'partner_id': record.partner_id.id,
					'user_id':record.user_id.id,
					#'internal_number': record.name,
					'section_id': 1,
                    'type': 'out_invoice',
					'account_id':record.partner_id.property_account_receivable.id
					}
			
				vals['date_invoice']=datetime.datetime.now() 
				vals['date_due']=vals['date_invoice']
				
				proj_id = record.x_project_id and record.x_project_id.id  or False		
				if proj_id:
					vals['x_project_id']=proj_id
				#if record.payment_term: 
				#	vals['payment_term']=record.payment_term.id	
				_payterm = 	self.pool.get('account.payment.term').search(cr, uid, [('x_payterm_code', '=', 'immediate')], limit=1)
				if _payterm:
					vals['payment_term']=_payterm[0]	
				
				inv_id = obj_inv.create(cr, uid, vals, context=context)
			
				vals = {
					'product_id': product_id,
					'quantity': '1',
					'invoice_id': inv_id,
					'origin': record.name,
					'price_unit': tot_price,
					'price_subtotal': tot_price,
				}
				vals['name'] = product_obj.name
				 
				#_logger.error("change_payment_term:line.tax_id_tax_id["+str(product_obj.taxes_id)+"]")
				
				if product_obj.taxes_id:
					vals['invoice_line_tax_id'] = [(6, 0, product_obj.taxes_id.ids)]
							
				obj_invline.create(cr, uid, vals, context=context)
				#for taxes
				#obj_inv = self.pool.get('account.invoice')
				obj_inv = obj_inv.browse(cr, uid, inv_id, context)
				obj_inv.button_compute(True) #For taxes
				
				#--------------
				val_sts={'state':'progress'}
				if  record.x_ac_status==None or record.x_ac_status=="hold":
					val_sts['x_ac_status']='open'
				#if record.x_dep_paid==None or record.x_dep_paid=="":
				#	val_sts['x_ac_status']='open'
					
				#self.write(cr, uid, [record.id], {'x_ac_status':'open'})	
				self.write(cr, uid, [record.id], val_sts)		
				#--------------
				view_id = self.pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'dincelaccount.invoice.form')], limit=1) 	
				#_logger.error("invoice_sales_validate.view_id["+str(view_id)+"]")
				value = {
                    'domain': str([('id', 'in', inv_id)]),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'account.invoice',
                    'view_id': view_id,
                    'type': 'ir.actions.act_window',
                    'name' : _('Invoice'),
                    'res_id': inv_id
                }
				return value	
				#return inv_id
		return False		
	
	def order_produced_check(self, cr, uid, ids, _id, context=None):
		if context is None:
			context = {}
		#obj = self.pool.get('sale.order').browse(cr, uid, _id, context=context)
		sql ="SELECT state from mrp_production where x_sale_order_id='%s'" %(str(_id))
		cr.execute(sql)
		rows = cr.fetchall()
		if rows and len(rows)>0:
			_state=""
			for row in rows:
				_st=row[0]
				if _st=="done" and _state=="":
					_state="complete"
				elif _st=="in_production":## or _st=="ready":
					_state="part"
				else:
					_st=""
			if _state!="":		
				sql ="UPDATE sale_order set x_prod_status='%s' where id='%s'" %(str(_state),str(_id))
				cr.execute(sql)
				
	def create_mo_order_dcs(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		#o_bom 	= self.pool.get('mrp.bom')	
		#o_prd 	= self.pool.get('mrp.production')	
	
				
	def updatelink_order_dcs(self, cr, uid, ids, context=None):
		if context is None:
			context = {}
		#order_id = ids[0]
		#request = urllib.urlopen("http://deverp.dincel.com.au/dcsapi/")
		#sql ="SELECT dcs_api_url FROM dincelaccount_config_settings";
		#cr.execute(sql)
		#rows = cr.fetchone()
		url=self.pool.get('dincelaccount.config.settings').get_dcs_api_url(cr, uid, ids, "getorder", ids[0], context=context)		
		if url:#rows and len(rows) > 0:
			#--- check flag of payment before update ---#
			self.pool.get('sale.order').update_payment_order(cr, uid, ids, ids[0], context=context)		
			#--- check flag of payment before update ---#
			
			#url="http://deverp.dincel.com.au/odoo/dcsapi/index.php?id="+str(ids[0])
			f = urllib2.urlopen(url)
			response = f.read()
			str1= simplejson.loads(response)
			
			item = str1['item']
			status1=str(item['post_status'])
			ordercode=str(item['curr_ordercode'])
			colorcode=str(item['curr_colourcode'])
			if status1=="success":
				
				sql ="UPDATE sale_order SET origin='"+ordercode+"' "	# WHERE id='"+str(ids[0])+"'"
				if colorcode:
					sql +=",x_colorcode='"+colorcode+"' "
				sql += " WHERE id='"+str(ids[0])+"'"	
				cr.execute(sql)
				return True
			else:
				if item['errormsg']:
					str1=item['errormsg']
				else:
					str1="Error while updating order."
				raise osv.except_osv(_('Error'), _(''+str1))
		
class dincelaccount_sale_order_line(osv.Model):
	_inherit="sale.order.line"
		
	def region_id_change(self, cr, uid, ids, x_region_id, x_region_id1, context=None):
		
		result 		= {}	
		context 	= context or {}
		result.update({'x_region_id': x_region_id1})
		#_logger.error("onchange_order_line_dcs.region_id_change["+str(result)+"]["+str(x_region_id1)+"]")
		return {'value': result}
		
	def product_qty_changed(self, cr, uid, ids, product, qty=0,length=0, partner_id=False, payment_term = False, dt_sale = False,loc_id =False, context=None):
		#result = super(dincelaccount_sale_order_line, self).product_qty_changed(cr, uid, ids, product, qty=qty, partner_id=partner_id, payment_term = payment_term, dt_sale = dt_sale, context=context)
		#result = super(dincelaccount_sale_order_line, self).product_qty_changed(cr, uid, ids, product, qty=0, partner_id=False, payment_term = False, dt_sale = False, context=None)
		result 		= {}	
		context 	= context or {}

		if not partner_id:
			raise osv.except_osv(_('No Customer Defined!'), _('Before choosing a product,\n select a customer in the sales form.'))
		
		warning 	= False
		
		domain 		= {}
		code 		= None
		
		order_id	= None
		#tot_qty  	= qty
		qty_lm 		= qty
		
		for record in self.browse(cr, uid, ids, context=context):
			order_id = record.order_id.id
			#tot_qty += record.product_uom_qty
			
		partner_obj = self.pool.get('res.partner')
		product_obj = self.pool.get('product.product')
		term_obj 	= self.pool.get('account.payment.term')
		
		rate_obj 	= self.pool.get('dincelcrm.customer.rate') 
		
		order_obj 	= self.pool.get('sale.order')
		order_obj 	= order_obj.browse(cr, uid, order_id)
		found_rate = False
		#loc_ob 	= self.pool.get('stock.warehouse')
		#if loc_id:
		#	loc_ob 	= loc_ob.browse(cr, uid, loc_id)
			
		partner 	= partner_obj.browse(cr, uid, partner_id)
		lang 		= partner.lang
		context 	= {'lang': lang, 'partner_id': partner_id}
		context_partner = {'lang': lang, 'partner_id': partner_id}
		
		warning_msgs = ''
		product_obj  = product_obj.browse(cr, uid, product, context=context_partner)
		
		#for line in order_obj.order_line:
		#	if line.product_id.x_is_calcrate:
		#		if line.product_id.id != product:
		#			tot_qty +=line.product_uom_qty
		#_logger.error("product_qty_changed:line.tot_qty.1["+str(tot_qty)+"]")
		#order_obj.x_qty_tot_profile = tot_qty
		#result['x_qty_tot_profile']= tot_qty
		
		#----------------------------------------------------------
		#converting [LM] into [M2]  LM->M2  LMtoM2 LM2M2
		#----------------------------------------------------------
		#rate_src=""
		cost_xtra=0.0
		rate=0.0
		if loc_id:
			loc_obj = self.pool.get('stock.warehouse').browse(cr,uid,loc_id,context=context)
			if loc_obj.x_cost_xtra and loc_obj.x_cost_xtra>0:
				cost_xtra = loc_obj.x_cost_xtra
		
		if payment_term:
			term_obj = term_obj.browse(cr, uid, payment_term)
			code 	 = term_obj.x_payterm_code
			found_rate = False
			if code:	
				rate_id = rate_obj.find(cr, uid, dt_sale, partner_id, context=context)
				
				#_logger.error("product_qty_changed:line.rate_idrate_id["+str(rate_id)+"]")
				
				if rate_id: #customer rate is present #-----------
					rate_id	 = rate_id[0]
				
					rate_obj =  rate_obj.browse(cr, uid, rate_id)
					#rate_src+=code+"-found_rt,"
					#elif code == "COD":
					if code == "COD" or code=="immediate":#if code == "30EOM":
						rate = rate_obj.rate_cod# cost_xtra
						found_rate = True #
					else:	
						rate = rate_obj.rate_acct#+cost_xtra
						found_rate = True #order_obj.button_dummy()
						
			'''		
			if found_rate == False:
				if loc_id:
					sql = "select rate1,rate2,rate3,id from dincelcrm_quote_rates where %s between from_val and to_val" % qty_lm
					cr.execute(sql)
					rows = cr.fetchone()
					if rows and len(rows) > 0:
						rate1= rows[0]
						rate3= rows[2]
						if code and code == "30EOM":
							rate = rate1+cost_xtra
						else:#elif code == "COD":
							rate= rate3+cost_xtra'''
		
		result.update({'x_qty_m2': False}) 		
		#_logger.error("product_qty_changed:line.rateproductproductproductproduct["+str(rate)+"]["+str(found_rate)+"]["+str(product)+"]")	
		if found_rate==False:
			rate=0.0
		if rate>0.0: #add only if rate is valid
			rate+=cost_xtra
		if product_obj.x_is_main=='1':#x_is_calcrate:
			if product_obj.x_m2_factor and product_obj.x_m2_factor>0:
				qty_lm = round((length*qty*0.001*product_obj.x_m2_factor),4) 	#M2 
			else:	
				qty_lm = round(((length*qty*0.001)/3),4) 	#M2 
			#if rate>0:
			#	result.update({'price_unit': rate})	
			result.update({'x_qty_m2': True}) 
			result.update({'price_unit': rate})	
			'''if payment_term:
				term_obj = term_obj.browse(cr, uid, payment_term)
				code 	 = term_obj.x_payterm_code
				found_rate = False
				if code:	
					rate_id = rate_obj.find(cr, uid, dt_sale, partner_id, context=context)
					if rate_id: #customer rate is present #-----------
						rate_id	 = rate_id[0]
					
						rate_obj =  rate_obj.browse(cr, uid, rate_id)
						rate_src+=code+"-found_rt,"
						if code == "30EOM":
							result.update({'price_unit': rate_obj.rate_acct+cost_xtra})
							found_rate = True #order_obj.button_dummy()
							
						elif code == "COD":
							result.update({'price_unit': rate_obj.rate_cod+cost_xtra})
							found_rate = True #
						
				if found_rate == False:
					#rate_id = None
					if loc_id:
						sql = "select rate1,rate2,rate3,id from dincelcrm_quote_rates where %s between from_val and to_val" % qty_lm
						cr.execute(sql)
						rows = cr.fetchone()
						if rows and len(rows) > 0:
							rate1= rows[0]
							rate3= rows[2]
							
							rate_src+=code+"-quote_rt,"
							
							if code and code == "30EOM":
								result.update({'price_unit': rate1+cost_xtra})
								#order_obj.button_dummy()
							else:#elif code == "COD":
								result.update({'price_unit': rate3+cost_xtra})'''
		else:
			#if length>0.0001:
			#	qty_lm = (length*qty*0.001)
			#else:
			#	qty_lm = qty
			#_logger.error("product_qty_changed:line.product_obj.x_prod_cat["+str(product_obj.x_prod_cat)+"]["+str(product)+"]["+str(qty)+"]")
			#if product_obj.x_prod_cat=="freight":
			#	qty_lm = qty
				#result.update({'x_order_qty': qty})
			qty_lm = qty	
			if partner.x_accs_m2convert:
				if product_obj.x_m2_factor and product_obj.x_m2_factor>0:
					qty_lm = round((qty*product_obj.x_m2_factor),4) 	
					if rate>0:
						result.update({'price_unit': rate})
					result.update({'x_qty_m2': True}) 
		
		
		#result.update({'x_rate_src': rate_src})	
		result.update({'product_uom_qty': qty_lm})
		
		return {'value': result, 'domain': domain, 'warning': warning}
	
	def product_id_change_v2(self, cr, uid, ids, pricelist, product, qty=0,
			uom=False, qty_uos=0, uos=False, name='', partner_id=False,
			lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False,loc_id =False, context=None):
		context = context or {}
		lang = lang or context.get('lang', False)
		if not partner_id:
			raise osv.except_osv(_('No Customer Defined!'), _('Before choosing a product,\n select a customer in the sales form.'))
		warning = False
		product_uom_obj = self.pool.get('product.uom')
		partner_obj = self.pool.get('res.partner')
		product_obj = self.pool.get('product.product')
		context = {'lang': lang, 'partner_id': partner_id}
		partner = partner_obj.browse(cr, uid, partner_id)
		lang = partner.lang
		context_partner = {'lang': lang, 'partner_id': partner_id}

		if not product:
			return {'value': {'th_weight': 0,
			'product_uos_qty': qty}, 'domain': {'product_uom': [],
			'product_uos': []}}
		if not date_order:
			date_order = time.strftime(DEFAULT_SERVER_DATE_FORMAT)

		result = {}
		warning_msgs = ''
		product_obj = product_obj.browse(cr, uid, product, context=context_partner)

		uom2 = False
		if uom:
			uom2 = product_uom_obj.browse(cr, uid, uom)
			if product_obj.uom_id.category_id.id != uom2.category_id.id:
				uom = False
		if uos:
			if product_obj.uos_id:
				uos2 = product_uom_obj.browse(cr, uid, uos)
				if product_obj.uos_id.category_id.id != uos2.category_id.id:
					uos = False
				else:
					uos = False

		fpos = False
		if not fiscal_position:
			fpos = partner.property_account_position or False
		else:
			fpos = self.pool.get('account.fiscal.position').browse(cr, uid, fiscal_position)
		if update_tax: #The quantity only have changed
			result['tax_id'] = self.pool.get('account.fiscal.position').map_tax(cr, uid, fpos, product_obj.taxes_id)

		if not flag:
			result['name'] = self.pool.get('product.product').name_get(cr, uid, [product_obj.id], context=context_partner)[0][1]
			if product_obj.description_sale:
				result['name'] += '\n'+product_obj.description_sale
		domain = {}
		if (not uom) and (not uos):
			result['product_uom'] = product_obj.uom_id.id
			if product_obj.uos_id:
				result['product_uos'] = product_obj.uos_id.id
				result['product_uos_qty'] = qty * product_obj.uos_coeff
				uos_category_id = product_obj.uos_id.category_id.id
			else:
				result['product_uos'] = False
				result['product_uos_qty'] = qty
				uos_category_id = False
			result['th_weight'] = qty * product_obj.weight
			domain = {'product_uom':
					[('category_id', '=', product_obj.uom_id.category_id.id)],
					'product_uos':
					[('category_id', '=', uos_category_id)]}
		elif uos and not uom: # only happens if uom is False
			result['product_uom'] = product_obj.uom_id and product_obj.uom_id.id
			result['product_uom_qty'] = qty_uos / product_obj.uos_coeff
			result['th_weight'] = result['product_uom_qty'] * product_obj.weight
		elif uom: # whether uos is set or not
			default_uom = product_obj.uom_id and product_obj.uom_id.id
			q = product_uom_obj._compute_qty(cr, uid, uom, qty, default_uom)
			if product_obj.uos_id:
				result['product_uos'] = product_obj.uos_id.id
				result['product_uos_qty'] = qty * product_obj.uos_coeff
			else:
				result['product_uos'] = False
				result['product_uos_qty'] = qty
			result['th_weight'] = q * product_obj.weight        # Round the quantity up

		if not uom2:
			uom2 = product_obj.uom_id
        # get unit price
		result.update({'x_order_length': product_obj.x_stock_length})
		
		if not pricelist:
			warn_msg = _('You have to select a pricelist or a customer in the sales form !\n'
			'Please set one before choosing a product.')
			warning_msgs += _("No Pricelist ! : ") + warn_msg +"\n\n"
		else:
			if product_obj.x_is_main=="1":
				result.update({'price_unit': 0.0})
			else:
				price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist],
						product, qty or 1.0, partner_id, {
						'uom': uom or result.get('product_uom'),
						'date': date_order,
						})[pricelist]
				if price is False:
					warn_msg = _("Cannot find a pricelist line matching this product and quantity.\n"
						"You have to change either the product, the quantity or the pricelist.")

					warning_msgs += _("No valid pricelist line found ! :") + warn_msg +"\n\n"
				else:
					result.update({'price_unit': price})
		if warning_msgs:
			warning = {
			'title': _('Configuration Error!'),
			'message' : warning_msgs
			}
		return {'value': result, 'domain': domain, 'warning': warning}
	
	def _total_lm_calc(self, cr, uid, ids, values, arg, context):
		x={}
		_lm=''
		for record in self.browse(cr, uid, ids):
			if record.product_id.x_prod_cat in ['customlength','stocklength']:
				_qty=record.x_order_qty
				_len=record.x_order_length
				_lm=_qty*_len*0.001
			else:
				_lm=''
			x[record.id] = _lm 
		return x
		
	_columns = {
		'x_order_length':fields.float("Ordered Len",digits_compute= dp.get_precision('Int Number')),	
		'x_order_qty':fields.float("Ordered Qty",digits_compute= dp.get_precision('Int Number')),	
		'x_total_lm': fields.function(_total_lm_calc, method=True, string='L/M', type='float'),
		'x_rate_src':fields.char("Rate Source"),	
		'x_qty_m2':fields.boolean("m2 rate?"),
		'x_region_id': fields.many2one('dincelaccount.region', 'A/c Region'),
		'x_coststate_id':fields.many2one("res.country.state","Cost Centre"),
	}	
	_defaults = {
		'x_order_qty': 1
	}	
	
	#def _get_default_currency(self, cr, uid, context=None):
	#	res = self.pool.get('res.company').search(cr, uid, [('currency_id','=','EUR')], context=context)
	#return res and res[0] or False
#---------------------------------------------------------------------------------------------	
#For revisoin of the sales order......14/10/2016
#Conditions.......	
#	1.Rate change due to COD to A/C or Discount Allowed
#	2.Panel Qty changed by customers
#	3.Delivery added from Pickup option or vice versa
#---------------------------------------------------------------------------------------------
class dincelaccount_sale_order_line_new(osv.Model):
	_name="sale.order.line.new"
	_columns = {
		'order_id': fields.many2one('sale.order', 'Sale Order'),
		'product_id': fields.many2one('product.product', 'Product'),
		'name': fields.char('Name',size=64),
		'order_length':fields.float("Ordered Len"),	
		'order_qty':fields.float("Ordered Qty"),	
		'product_uom': fields.many2one('product.uom', 'Unit of Measure'),
		'region_id': fields.many2one('dincelaccount.region', 'A/c Region'),
		'coststate_id':fields.many2one("res.country.state","Cost Centre"),
		'price_unit':fields.float("Unit Price"),	
		'tax_id': fields.many2one('account.tax', 'Tax'),
	}	
#not in use	
class dincelaccount_sale_order_line_old(osv.Model):
	_name="sale.order.line.old"
	_columns = {
		'name': fields.char('Name',size=64),
	}
#not in use		
class dincelaccount_journal_dcstest(osv.Model):
	_name="dincelaccount.journal.dcstest"
	_columns = {
		'name': fields.char('Name',size=64),
	}	
	
#-------------------------------------------------------------
#--- used for sale order revise only...not use same table, cause of search criteria.., dropdown, etc...	
#-------------------------------------------------------------
class dincelaccount_sale_order_bak(osv.Model):
	_name="sale.order.bak"	
	_inherit = ['mail.thread']
	_description = "Sales Order Revise"
	
	def _amount_wrapper(self, cr, uid, ids, field_name, arg, context=None):
		res = {}
		_total=0.0
		#_logger.error("updatelink_order_dcs._amount_untaxed_amount_untaxed0000["+str(_total)+"]")	
		for record in self.browse(cr, uid, ids):
			res[record.id] = {
				'amount_untaxed': 0.0,
				'amount_tax': 0.0,
				'amount_total': 0.0,
			}
			for line in record.item_lines:
				price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
				_total=_total+(price*line.product_uom_qty)
				#_logger.error("updatelink_order_dcs._amount_untaxed_amount_untaxed["+str(_total)+"]")	
			#x[record.id] = _total 
			res[record.id]['amount_tax'] = _total*0.1
			res[record.id]['amount_untaxed'] = _total
			res[record.id]['amount_total'] = res[record.id]['amount_untaxed'] + res[record.id]['amount_tax']
		return res
	'''
	def _amount_tax(self, cr, uid, ids, values, arg, context):
		x={}
		_total=0
		for record in self.browse(cr, uid, ids):
			for line in record.item_lines:
				price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
				_total= _total+(price*line.product_uom_qty)
		x[record.id] = _total*0.1 
		return x
	
	def _amount_total(self, cr, uid, ids, values, arg, context):
		x={}
		_total=0
		for record in self.browse(cr, uid, ids):
			for line in record.item_lines:
				price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
				_total= _total+(price*line.product_uom_qty)
		x[record.id] = _total*1.1
		return x'''
		
	_columns = {
		'name': fields.char('Name',size=64),
		'date_order': fields.datetime('Date'),
		'origin_id':fields.many2one('sale.order', 'Origin OrderId'),
		'partner_id': fields.many2one('res.partner', 'Customer'),
		'user_id': fields.many2one('res.users', 'Salesperson'),
		'region_id': fields.many2one('dincelaccount.region', 'A/c Region'),
		'item_lines':fields.one2many('sale.order.bak.line', 'order_bak_id', 'Invoies'),
		'payment_term': fields.many2one('account.payment.term', 'Payment Term'),
		'project_id': fields.many2one('res.partner','Project / Site'),		
		'contact_id': fields.many2one('res.partner','Contact Person'),		
		'quote_id': fields.many2one('account.analytic.account','Quote'),		
		'warehouse_id': fields.many2one('stock.warehouse','Dispatch Location'),		
		'street': fields.char('Street'),	
		'postcode': fields.char('Postcode'),	
		'suburb': fields.char('Suburb'),	
		'state_id': fields.many2one('res.country.state','State'),		
		'country_id': fields.many2one('res.country','Country'),
		'deposit_exmpt': fields.boolean('Deposit Exempt'),
		'revise_sn': fields.integer('Revise SN', size=2),	
		'pudel':fields.selection([
			('pu','Pickup'),
			('del','Delivery'),
			], 'Pickup/Delivery'),
		'ac_status':fields.selection([
			('hold','Hold'),
			('open','Open'),
			('part','Partial'),
			('paid','Paid'),
			], 'A/c Status'),	
		'prod_status':fields.selection([
			('queue','Queue'),
			('part','Partial'),
			('complete','Complete'),
			], 'Production Status'),		
		'del_status':fields.selection([
			('none','None'),
			('part','Partial'),
			('delivered','Delivered'),
			], 'Delivery Status'),		
		'status':fields.selection([ #as in dcs open /close/ cancel
			('open','Open'),
			('close','Closed'),
			('cancel','Cancelled'),
			], 'Status'),	
		'revise_type':fields.selection([ #>>as revise type
			('shipment','Shipment'),
			('rate','Price changed'),
			('order','Qty changed'),
			('other','Other'),
			], 'Revise type'),	
		'dt_request':fields.date("Requested Date"),		
		'dt_process': fields.datetime("Order Entry Date"),
		'note': fields.text('Note'),
		'pricelist_id': fields.many2one('product.pricelist', 'Pricelist'), 
		'currency_id': fields.related('pricelist_id', 'currency_id', type="many2one", relation="res.currency", string="Currency", readonly=True),
		'amount_untaxed':fields.function(_amount_wrapper, digits_compute=dp.get_precision('Account'), string='Untaxed Amount',multi='sums',store=True),
		'amount_tax':fields.function(_amount_wrapper, digits_compute=dp.get_precision('Account'), string='Taxes',multi='sums',store=True),
		'amount_total':fields.function(_amount_wrapper, digits_compute=dp.get_precision('Account'), string='Total Amount',multi='sums',store=True),
	}	
	
class dincelaccount_sale_order_bak_line(osv.Model):
	_name="sale.order.bak.line"
	def _amount_line(self, cr, uid, ids, field_name, arg, context=None):
		tax_obj = self.pool.get('account.tax')
		cur_obj = self.pool.get('res.currency')
		res = {}
		if context is None:
			context = {}
		for line in self.browse(cr, uid, ids, context=context):
			price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
			_total= price*line.product_uom_qty
			#taxes = tax_obj.compute_all(cr, uid, line.tax_id, price, line.product_uom_qty, line.product_id, line.order_bak_id.partner_id)
			#_logger.error("dincelaccount_sale_order_bak_line["+str(price)+"]["+str(taxes)+"]")
			#cur = line.order_bak_id.pricelist_id.currency_id
			res[line.id] = _total#;cur_obj.round(cr, uid, cur, taxes['total'])
		return res

	_columns = {
		'order_bak_id': fields.many2one('sale.order.bak', 'Back Order'),
		'sequence': fields.integer('Sequence'),
		'product_id': fields.many2one('product.product', 'Product'),
		'name': fields.char('Name',size=64),
		'order_length':fields.float("Ordered Len"),	
		'order_qty':fields.float("Ordered Qty"),	
		'product_uom': fields.many2one('product.uom', 'Unit of Measure'),
		'product_uom_qty': fields.float('Quantity'),
		'region_id': fields.many2one('dincelaccount.region', 'A/c Region'),
		'price_unit':fields.float("Unit Price"),	
		'tax_id': fields.many2one('account.tax', 'Tax'),
		'price_subtotal': fields.function(_amount_line, string='Subtotal', digits_compute= dp.get_precision('Account')),
		'discount': fields.float('Discount (%)'),
	}	
	_defaults = {
		'discount': 0.0,
		'price_unit': 0.0,
	}

	
class accountmail_compose_message(osv.Model):
	_inherit = 'mail.compose.message'
 
	#@api.multi #res = super(dincelreport_res_partner, self).write(cr, uid, ids, vals, context=context)
	def send_mail(self, cr, uid, ids, context=None):
		#context = self._context
		#_logger.error("accountmail_compose_messageaccountmail_compose_message111["+str(context)+"]")
		if context.get('default_model') == 'sale.order' and context.get('mark_as_sent'):
			if context.get('default_inv_ids'):
				for _id in context.get('default_inv_ids'):
					#invoice = self.pool.get('account.invoice').browse(_id)
					#invoice=self.pool.get('account.invoice').browse(cr, uid, _id, context)
					#invoice = invoice.with_context(mail_post_autofollow=True)
					self.pool.get('account.invoice').write(cr, uid, _id, {'sent': True})
					#invoice.message_post(body=_("Invoice sent"))
			if context.get('default_res_id'):
				_id=context.get('default_res_id')
				#order =self.pool.get('sale.order').browse(cr, uid, _id, context)#= self.env['sale.order'].browse(_id)
				self.pool.get('sale.order').write(cr, uid, _id, {'x_sent': True,'state':'sent'}) #email_obj.write(cr, uid, template_id, {'attachment_ids': [(6, 0, _atths)]})  
		return super(accountmail_compose_message, self).send_mail(cr, uid, ids, context=context)