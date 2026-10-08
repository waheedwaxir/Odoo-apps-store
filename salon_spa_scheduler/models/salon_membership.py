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

class SalonMembership(models.Model):
    _name = 'salon.membership'
    _description = 'Membership Plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(required=True, tracking=True)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True, index=True,
        default=lambda self: self.env.company, tracking=True)
    plan_type = fields.Selection([
        ('silver', 'Silver'),
        ('gold', 'Gold'),
        ('platinum', 'Platinum')
    ], default='silver', tracking=True)
    duration_months = fields.Integer(default=12, tracking=True)
    price = fields.Float(tracking=True)
    discount_percentage = fields.Float(default=0.0, tracking=True)
    min_spend = fields.Float(
        string='Minimum Spend per Session', tracking=True,
        help="The discount is applied to the salon services of a POS order only "
             "once their total reaches this amount. 0 = no minimum.")
    active = fields.Boolean(default=True, tracking=True)

class SalonMembershipLine(models.Model):
    _name = 'salon.membership.line'
    _description = 'Customer Membership'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'partner_id'
    _check_company_auto = True

    company_id = fields.Many2one(
        'res.company', string='Company', required=True, index=True,
        default=lambda self: self.env.company, tracking=True)
    membership_id = fields.Many2one('salon.membership', required=True, tracking=True, check_company=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True)
    membership_number = fields.Char(
        related='partner_id.salon_membership_number', store=True, readonly=False,
        string='Membership Number')
    start_date = fields.Date(default=fields.Date.context_today, tracking=True)
    end_date = fields.Date(tracking=True)
    state = fields.Selection([
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled')
    ], default='active', tracking=True)

    @api.depends('membership_id', 'partner_id')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.partner_id.name or 'New'} - {rec.membership_id.name or ''}"

    @api.model
    def _get_member_offer(self, partner_id, company_id=False):
        """Membership plan giving the best discount to a customer, or an empty recordset."""
        if not partner_id:
            return self.env['salon.membership']
        today = fields.Date.context_today(self)
        lines = self.sudo().search([
            ('partner_id', '=', partner_id),
            ('state', '=', 'active'),
            ('company_id', '=', company_id or self.env.company.id),
            ('membership_id.active', '=', True),
            ('membership_id.discount_percentage', '>', 0),
            '|', ('start_date', '=', False), ('start_date', '<=', today),
            '|', ('end_date', '=', False), ('end_date', '>=', today),
        ])
        if not lines:
            return self.env['salon.membership']
        return max(lines.membership_id, key=lambda m: m.discount_percentage)

    @api.model
    def get_pos_member_discount(self, partner_id, company_id=False):
        """Membership offer for a customer, used by the POS.

        Always returns the discount product; 'discount' is 0 when the customer
        has no active membership. The POS adds a separate discount line named
        after the plan once the services reach 'min_spend'.
        """
        company = company_id or self.env.company.id
        product = self.env.ref(
            'salon_spa_scheduler.product_product_membership_discount', raise_if_not_found=False)
        tip = self.env.ref('salon_spa_scheduler.product_product_staff_tip', raise_if_not_found=False)
        services = self.env['salon.service'].sudo().search([('company_id', '=', company)])
        # Only products linked to a Salon Service count as services ("Is a Salon
        # Product" is set on almost every POS product, retail goods included).
        products = services.product_ids | services.product_id
        res = {
            'discount_product_id': product.id if product else False,
            'discount_product_tmpl_id': product.product_tmpl_id.id if product else False,
            'tip_product_id': tip.id if tip else False,
            # used by the POS to group the order lines into Services / Products
            'service_product_ids': products.ids,
            'discount': 0.0,
            'min_spend': 0.0,
            'name': '',
        }
        plan = self._get_member_offer(partner_id, company)
        if not plan or not product:
            return res
        res.update({
            'discount': plan.discount_percentage,
            'min_spend': plan.min_spend,
            'name': plan.name,
        })
        return res
