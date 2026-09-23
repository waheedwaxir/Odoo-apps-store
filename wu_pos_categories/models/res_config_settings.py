# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_iface_single_line_categories = fields.Boolean(
        related='pos_config_id.iface_single_line_categories',
        readonly=False,
        string="Single-Line Categories",
        help="Display product categories in a single horizontal line with scroll capability instead of a grid."
    )
