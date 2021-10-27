from openerp import models, fields

class Configuration(models.TransientModel):
	_name = 'dincelaccount.test.config.settings'
	_inherit = 'res.config.settings'

	default_account_id = fields.Char(
		string='Account Id',
		required=True,
		help="Test Identifier",
		default_model='dincelaccount.test.config.settings',
	)