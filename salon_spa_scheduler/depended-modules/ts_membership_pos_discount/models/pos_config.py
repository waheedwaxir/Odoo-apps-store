from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    ts_discount_services_only = fields.Boolean(
        string='Discount Button on Services Only',
        default=True,
        help="When checked, the global Discount button of the POS applies only to "
             "services. Uncheck it to discount services and products.")
