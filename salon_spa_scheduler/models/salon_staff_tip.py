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
from odoo import models, fields, api


class SalonStaffTip(models.Model):
    _name = 'salon.staff.tip'
    _description = 'Salon Staff Tip'
    _order = 'date desc, id desc'
    _check_company_auto = True

    name = fields.Char(string='Reference', compute='_compute_name', store=True)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True, index=True,
        default=lambda self: self.env.company)
    staff_id = fields.Many2one('salon.staff', string='Staff Member', required=True, index=True, check_company=True)
    amount = fields.Float(string='Tip Amount', required=True)
    order_id = fields.Many2one('pos.order', string='POS Order', ondelete='cascade', check_company=True)
    date = fields.Datetime(string='Date', default=fields.Datetime.now, required=True)
    state = fields.Selection([
        ('unpaid', 'Unpaid'),
        ('paid', 'Paid')
    ], string='Status', default='unpaid', required=True)

    @api.depends('staff_id', 'date', 'order_id')
    def _compute_name(self):
        for tip in self:
            order_ref = tip.order_id.pos_reference if tip.order_id else 'Manual'
            tip.name = f"Tip for {tip.staff_id.name or 'Unknown'} ({order_ref})"

    def action_mark_paid(self):
        self.write({'state': 'paid'})

    def action_mark_unpaid(self):
        self.write({'state': 'unpaid'})
