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

from odoo import api, fields, models

class SalonReview(models.Model):
    _name = 'salon.review'
    _description = 'Customer Review'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'
    _rec_name = 'appointment_id'
    _check_company_auto = True

    company_id = fields.Many2one(
        'res.company', string='Company', required=True, index=True,
        default=lambda self: self.env.company, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True)
    staff_id = fields.Many2one('salon.staff', string='Staff/Beautician', tracking=True, check_company=True)
    appointment_id = fields.Many2one('salon.appointment', string='Appointment', tracking=True, check_company=True, domain="[('review_ids', '=', False)]")
    
    _appointment_uniq = models.Constraint(
        'unique(appointment_id)',
        "An appointment can only be reviewed once!",
    )
    rating = fields.Selection([
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5')
    ], required=True, string='Rating (1-5)', default='5', tracking=True)
    comment = fields.Text(tracking=True)
    date = fields.Date(default=fields.Date.context_today, tracking=True)

    @api.depends('appointment_id', 'partner_id')
    def _compute_display_name(self):
        for rec in self:
            name = ""
            if rec.appointment_id:
                name = rec.appointment_id.display_name or rec.appointment_id.name
            elif rec.partner_id:
                name = rec.partner_id.name
            rec.display_name = f"Review - {name or 'New'}"

    @api.onchange('appointment_id')
    def _onchange_appointment_id(self):
        if self.appointment_id:
            self.partner_id = self.appointment_id.partner_id
            self.staff_id = self.appointment_id.staff_id
