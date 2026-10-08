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

class SalonService(models.Model):
    _name = 'salon.service'
    _description = 'Salon/Spa Service'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'
    _check_company_auto = True

    sequence = fields.Integer(default=10, tracking=True)
    name = fields.Char(required=True, tracking=True)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True, index=True,
        default=lambda self: self.env.company, tracking=True)
    duration = fields.Float(string='Duration Hours', default=1.0, required=True, tracking=True)
    list_price = fields.Float(string='Price', tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    color = fields.Integer(default=2)
    category_id = fields.Many2one(
        'salon.service.category', string='Category', index=True,
        ondelete='set null', tracking=True)

    product_ids = fields.Many2many(
        'product.product',
        string='POS Products',
        domain="['|', ('is_a_salon', '=', True), ('available_in_pos', '=', True)]",
        tracking=True,
        check_company=True
    )
    product_id = fields.Many2one(
        'product.product',
        string='POS Product',
        compute='_compute_product_id',
        store=True,
        readonly=False,
        tracking=True,
        check_company=True
    )
    
    commission_type = fields.Selection([
        ('fixed', 'Fixed'),
        ('percentage', 'Percentage')
    ], default='fixed', tracking=True)
    commission_value = fields.Float(string='Commission Value', tracking=True)
    is_addon = fields.Boolean(string='Is Add-on', default=False, tracking=True)
    step_ids = fields.One2many('salon.service.step', 'service_id', string='Steps')
    staff_names = fields.Char(
        string='Beauticians', compute='_compute_staff_names',
        help="Beauticians who do this service: by its category or as an extra "
             "service. Beauticians with nothing picked do every service too.")

    def _compute_staff_names(self):
        for rec in self:
            staff = self.env['salon.staff'].search([
                '|', ('service_ids', 'in', rec.id),
                ('service_category_ids', 'in', rec.category_id.ids)])
            rec.staff_names = ", ".join(staff.mapped('name'))
    step_count = fields.Integer(string='Step Count', compute='_compute_step_count', store=True)
    has_steps = fields.Boolean(string='Has Steps', compute='_compute_step_count', store=True)

    @api.depends('step_ids')
    def _compute_step_count(self):
        for rec in self:
            rec.step_count = len(rec.step_ids)
            rec.has_steps = bool(rec.step_ids)

    @api.constrains('duration')
    def _check_duration(self):
        for rec in self:
            if rec.duration <= 0:
                raise ValidationError('Service duration must be greater than zero.')

    @api.depends('product_ids')
    def _compute_product_id(self):
        for rec in self:
            if rec.product_ids:
                rec.product_id = rec.product_ids[0].id
            else:
                rec.product_id = False

    @api.onchange('product_id')
    def _onchange_product_id_sync(self):
        if self.product_id and self.product_id not in self.product_ids:
            self.product_ids = [(4, self.product_id.id)]

    @api.onchange('product_ids')
    def _onchange_product_ids_price(self):
        if self.product_ids:
            self.list_price = sum(p.list_price for p in self.product_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'product_id' in vals and 'product_ids' not in vals:
                vals['product_ids'] = [(4, vals['product_id'])]
        return super().create(vals_list)

    def write(self, vals):
        if 'product_id' in vals and 'product_ids' not in vals:
            vals['product_ids'] = [(6, 0, [vals['product_id']])]
        return super().write(vals)
