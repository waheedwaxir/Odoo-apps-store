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

class SalonPackage(models.Model):
    _name = 'salon.package'
    _description = 'Service Package'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(required=True, tracking=True)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True, index=True,
        default=lambda self: self.env.company, tracking=True)
    description = fields.Text(tracking=True)
    price = fields.Float(required=True, tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    line_ids = fields.One2many('salon.package.line', 'package_id', string='Package Lines')

class SalonPackageLine(models.Model):
    _name = 'salon.package.line'
    _description = 'Package Line'
    _check_company_auto = True

    package_id = fields.Many2one('salon.package', ondelete='cascade', required=True)
    company_id = fields.Many2one(related='package_id.company_id', store=True, index=True, readonly=True)
    service_id = fields.Many2one('salon.service', string='Service', required=True, check_company=True)
    quantity = fields.Integer(default=1)
