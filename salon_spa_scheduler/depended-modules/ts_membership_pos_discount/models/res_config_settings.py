from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_ts_discount_services_only = fields.Boolean(
        related='pos_config_id.ts_discount_services_only', readonly=False)
