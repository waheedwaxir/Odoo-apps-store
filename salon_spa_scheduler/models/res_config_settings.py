# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    salon_start_hour = fields.Integer(
        string="Scheduler Start Hour",
        config_parameter='salon_spa_scheduler.start_hour',
        default=8
    )
    salon_end_hour = fields.Integer(
        string="Scheduler End Hour",
        config_parameter='salon_spa_scheduler.end_hour',
        default=22
    )
    salon_max_cancellations = fields.Integer(
        string="Max Cancellations Allowed",
        config_parameter='salon_spa_scheduler.max_cancellations',
        default=3
    )

    @api.constrains('salon_start_hour', 'salon_end_hour')
    def _check_scheduler_hours(self):
        for record in self:
            if not (0 <= record.salon_start_hour <= 23):
                raise ValidationError(_("Start hour must be between 0 and 23."))
            if not (0 <= record.salon_end_hour <= 23):
                raise ValidationError(_("End hour must be between 0 and 23."))
            if record.salon_start_hour >= record.salon_end_hour:
                raise ValidationError(_("Start hour must be strictly less than end hour."))

    @api.constrains('salon_max_cancellations')
    def _check_max_cancellations(self):
        for record in self:
            if record.salon_max_cancellations < 0:
                raise ValidationError(_("Max Cancellations Allowed must be 0 (disabled) or greater."))
