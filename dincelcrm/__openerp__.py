{
	'name': 'DINCEL CRM ',
	'version':'1.0',
	'description':"""
		DINCEL CRM
		Custom Module
		""",
	'author':'Shukra Rai',
	'website':'www.dincel.com.au',
	'depends':['base','base_setup','sale', 'crm','crm_helpdesk'],
	'data':[
		'security/security.xml',
		'security/ir.model.access.csv',
		'dincelcrm_quotation.xml',
		'dincelcrm_contractquote.xml',
		'dincelcrm_view.xml',
		'dincelcrm_report.xml',
		'dincelcrm_mail.xml',
		'dincelquoteschedule.xml',
		'views/report_quotation_new.xml',
		'views/report_quotation_newV2.xml',
		'views/report_newcontact.xml',
		#'views/dincelcrm_report_views.xml',
		'crmcomplaints.xml',
		'crmcomplaints_data.xml',
		'dincelcrm_menu.xml',
		'dincelcrm_manage.xml',
		'wizard/followup_create.xml',
		'views/mail_template.xml',
		'helpdesk_menu.xml',
		],
		
	'init_xml': [],
	'js': [],
	'css': [],
	'qweb': [], 
	'demo':[],
	'installable':True,
	'auto_install':False,
}


