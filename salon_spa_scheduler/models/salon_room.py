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

from odoo import fields, models

class SalonRoom(models.Model):
    _name = 'salon.room'
    _description = 'Chair'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    _check_company_auto = True

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(tracking=True)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True, index=True,
        default=lambda self: self.env.company, tracking=True)
    branch_id = fields.Many2one(
        'res.company', string='Branch', required=True, tracking=True,
        default=lambda self: self.env.company,
        domain="[('id', 'in', allowed_company_ids)]",
        help="Company / branch this chair belongs to. Branches are the companies "
             "configured for the database (Settings > Companies).")
    capacity = fields.Integer(default=1, tracking=True)
    room_type = fields.Selection([
        ('styling', 'Styling Chair'),
        ('wash', 'Wash Chair'),
        ('waiting', 'Waiting Chair'),
        ('vip', 'VIP Chair')
    ], string='Chair Type', default='styling', tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    color = fields.Integer(default=4)
