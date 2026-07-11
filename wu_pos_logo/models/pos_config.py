# -*- coding: utf-8 -*-
from odoo import fields, models, api


class PosConfig(models.Model):
    _inherit = 'pos.config'

    enable_pos_logo = fields.Boolean(string="POS Logo", default=False)
    pos_logo_option = fields.Selection([
        ('company', 'Company'),
        ('custom_image', 'Custom Image'),
        ('no_logo', 'No Logo'),
    ], string="Logo Option", default='custom_image')
    pos_custom_logo = fields.Binary(string="Custom POS Logo")

    enable_screen_saver_bg = fields.Boolean(string="Screen Saver Background", default=False)
    pos_screen_saver_image = fields.Binary(string="Screen Saver Background Image")
    pos_timer_color = fields.Char(string="Timer Color", default="#000000")
    pos_screen_timer = fields.Integer(string="Screen Timer", default=1)

    enable_receipt_logo = fields.Boolean(string="Receipt Logo", default=False)
    receipt_logo_option = fields.Selection([
        ('company', 'Company'),
        ('custom_image', 'Custom Image'),
        ('no_logo', 'No Logo'),
    ], string="Receipt Logo Option", default='custom_image')
    receipt_custom_logo = fields.Binary(string="Custom Receipt Logo")

    @api.model
    def _load_pos_data_fields(self, config):
        fields_list = super()._load_pos_data_fields(config)
        if isinstance(fields_list, list) and fields_list:
            fields_list += [
                'enable_pos_logo',
                'pos_logo_option',
                'pos_custom_logo',
                'enable_screen_saver_bg',
                'pos_screen_saver_image',
                'pos_timer_color',
                'pos_screen_timer',
                'enable_receipt_logo',
                'receipt_logo_option',
                'receipt_custom_logo',
            ]
        return fields_list
