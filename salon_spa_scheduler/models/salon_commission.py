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

class SalonCommission(models.Model):
    _name = 'salon.commission'
    _description = 'Staff Commission'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'
    _rec_name = 'staff_id'
    _check_company_auto = True

    company_id = fields.Many2one(
        'res.company', string='Company', required=True, index=True,
        default=lambda self: self.env.company, tracking=True)
    staff_id = fields.Many2one('salon.staff', string='Beautician/Staff', required=True, tracking=True, check_company=True)
    appointment_id = fields.Many2one('salon.appointment', string='Appointment', tracking=True, check_company=True)
    commission_amount = fields.Float(required=True, tracking=True)
    kind = fields.Selection([
        ('service', 'Service'),
        ('incentive', 'Monthly Incentive'),
    ], string='Type', default='service', required=True, index=True,
        help="Service: worked out per booking from the services' commission. "
             "Monthly Incentive: the beautician's month against their targets.")
    period = fields.Date(string='Month', index=True,
                         help="First day of the month a Monthly Incentive is for.")
    reached = fields.Float(string='Service Sales',
                           help="The month's service sales the incentive was worked out on.")
    rate = fields.Float(string='Incentive %')
    date = fields.Date(default=fields.Date.context_today, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('paid', 'Paid')
    ], default='draft', tracking=True)

    @api.depends('staff_id', 'commission_amount')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"Commission - {rec.staff_id.name or 'New'} ({rec.commission_amount})"

    def action_pay(self):
        self.write({'state': 'paid'})
