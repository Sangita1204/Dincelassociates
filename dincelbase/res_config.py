# -*- coding: utf-8 -*-

from openerp.osv import fields, osv



class dcs_config_settings(osv.TransientModel):
	_name = 'dcs.config.settings'
	_inherit = 'res.config.settings'
	_columns = {
		'dcs_api_url': fields.char('DCS API URL', size=200),
	}

class dcsbase_config_settings(osv.TransientModel):
	_inherit = 'base.config.settings'
	_columns = {
		'dcs_api_url': fields.char('DCS API URL', size=200),
	}
