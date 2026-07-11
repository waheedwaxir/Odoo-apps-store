# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_enable_pos_logo = fields.Boolean(
        related='pos_config_id.enable_pos_logo',
        readonly=False,
        string="POS Logo"
    )
    pos_pos_logo_option = fields.Selection(
        related='pos_config_id.pos_logo_option',
        readonly=False,
        string="Logo Option"
    )
    pos_pos_custom_logo = fields.Binary(
        related='pos_config_id.pos_custom_logo',
        readonly=False,
        string="Custom POS Logo"
    )

    pos_enable_screen_saver_bg = fields.Boolean(
        related='pos_config_id.enable_screen_saver_bg',
        readonly=False,
        string="Screen Saver Background"
    )
    pos_pos_screen_saver_image = fields.Binary(
        related='pos_config_id.pos_screen_saver_image',
        readonly=False,
        string="Screen Saver Background Image"
    )
    pos_pos_timer_color = fields.Char(
        related='pos_config_id.pos_timer_color',
        readonly=False,
        string="Timer Color"
    )
    pos_pos_screen_timer = fields.Integer(
        related='pos_config_id.pos_screen_timer',
        readonly=False,
        string="Screen Timer"
    )

    pos_enable_receipt_logo = fields.Boolean(
        related='pos_config_id.enable_receipt_logo',
        readonly=False,
        string="Receipt Logo"
    )
    pos_receipt_logo_option = fields.Selection(
        related='pos_config_id.receipt_logo_option',
        readonly=False,
        string="Receipt Logo Option"
    )
    pos_receipt_custom_logo = fields.Binary(
        related='pos_config_id.receipt_custom_logo',
        readonly=False,
        string="Custom Receipt Logo"
    )
