# -*- coding: utf-8 -*-
from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    iface_single_line_categories = fields.Boolean(
        string="Single-Line Categories",
        default=True,
        help="Display product categories in a single horizontal line with scroll capability instead of a grid."
    )
