{
	'name': 'DINCEL STOCK ',
	'version':'1.0',
	'description':"""
		DINCEL STOCK Module
		""",
	'author':'Shukra Rai',
	'website':'www.dincel.com.au',
	'depends':['base','base_setup','sale', 'crm', 'account','dincelbase','stock'],
	'data':[
		'dincelstock.xml',
		'dincelstock_inventory.xml',
		'dincelstock_move.xml',
		'dincelstock_transfer.xml',
		'dincelstock_base.xml',
		'dincelstock_valuation.xml',
		'dincelstock_adjustment.xml',
		'dincelstock_ibt_manifest.xml',
		'views/report_docket_report.xml',
		'views/report_stockreport.xml',
		'views/report_stock_value.xml',
		'views/report_stock_delivery.xml',
		'wizard/ibt_manifest.xml',
		],
	'init_xml': [],
	'js': [],
	'css': [],
	'qweb': [], 
	'demo':[],
	'installable':True,
	'auto_install':False,
}


