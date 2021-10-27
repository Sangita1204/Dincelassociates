{
	'name': 'DINCEL PURCHASE ',
	'version':'1.0',
	'description':"""
		DINCEL PURCHASE Module
		""",
	'author':'Shukra Rai',
	'website':'www.dincel.com.au',
	'depends':['base','base_setup','purchase', 'crm','dincelaccount'],
	'data':[
			'dincelpurchase.xml',
			'dincelpurchase_menu.xml',
			'dincelpurchase_nonstock.xml',
			'views/report_purchase_invoice.xml',
			'views/report_po_nonstock.xml'
			],
	'init_xml': [],
	'js': [],
	'css': [],
	'qweb': [], 
	'demo':[],
	'installable':True,
	'auto_install':False,
}


