{
	'name': 'DINCEL MANUFACTURE ',
	'version':'1.0',
	'description':"""
		DINCEL MANUFACTURE Module
		""",
	'author':'Shukra Rai',
	'website':'www.dincel.com.au',
	'depends':['base','base_setup','sale', 'crm','mrp','dincelproduct'],
	'data':['dincelmanufacture.xml',
			'dincelmrp.xml',
			#'wizard/sale_make_mo.xml',
			'dincelmanufacture_menu.xml',
			'dincelmrp_saleorder.xml',
			'wizard/schedule_mrp.xml',
			'views/report_mo_pqreport.xml',
			'wizard/mrp_produce.xml',
			'wizard/schedule_delivery.xml',
			'wizard/mrp_produce_new.xml',
			],
	'init_xml': [],
	'js': [],
	'css': [],
	'qweb': [], 
	'demo':[],
	'installable':True,
	'auto_install':False,
}


