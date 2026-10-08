# -*- coding: utf-8 -*-
###############################################################################
#    Techman Solutions W.L.L. - Qatar
#
#    Copyright (C) 2026-TODAY Techman Solutions W.L.L.
#    Author: Engr. Waheed Ullah
#    Website: https://www.techman.qa
#    Email: waheed@techman.qa
#    Phone: +97430643395
#
#    Salon & Spa Management System
#
#    This software is a commercial product developed by Techman Solutions
#    W.L.L. It is not free software and is provided under the applicable
#    commercial license and terms of use.
#
#    Unauthorized copying, distribution, modification, or resale of this
#    software is prohibited unless expressly authorized by Techman Solutions
#    W.L.L.
#    For licensing, complete Salon & Spa modules, customization,
#    implementation, integration, or support, please contact:
#
###############################################################################

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrJob(models.Model):
    """Monthly sales targets that come with a job position (Junior, Senior,
    ...). A beautician's targets are filled from their position."""
    _inherit = 'hr.job'

    salon_target_1 = fields.Float(
        string='Target 1',
        help="Monthly service sales from which the Target 1 % incentive applies.")
    salon_target_1_rate = fields.Float(string='Target 1 %', default=5.0)
    salon_target_2 = fields.Float(
        string='Target 2',
        help="Monthly service sales from which the Target 2 % incentive applies "
             "instead of Target 1 %.")
    salon_target_2_rate = fields.Float(string='Target 2 %', default=10.0)
    salon_staff_ids = fields.One2many('salon.staff', 'job_id', string='Beauticians')
    salon_staff_count = fields.Integer(string='Number of Beauticians', compute='_compute_salon_staff_count')

    @api.depends('salon_staff_ids')
    def _compute_salon_staff_count(self):
        for job in self:
            job.salon_staff_count = len(job.salon_staff_ids)

    @api.constrains('salon_target_1', 'salon_target_2')
    def _check_salon_targets(self):
        for job in self:
            if job.salon_target_1 and job.salon_target_2 and job.salon_target_2 < job.salon_target_1:
                raise ValidationError(_("%s: Target 2 has to be at least Target 1.", job.name))
