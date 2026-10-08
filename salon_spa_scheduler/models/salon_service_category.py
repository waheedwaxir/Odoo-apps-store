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

# -*- coding: utf-8 -*-
from odoo import fields, models


class SalonServiceCategory(models.Model):
    """Service category - Nails, Hair Color, Waxing, Massage and so on.

    Without a category on salon.service no report can group turnover by
    treatment type. The salon works with 23 of them.
    """
    _name = 'salon.service.category'
    _description = 'Salon Service Category'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(help="Short label as it appeared in the previous system.")
    sequence = fields.Integer(default=10)
    parent_id = fields.Many2one('salon.service.category', string='Parent Category',
                                ondelete='set null', index=True)
    child_ids = fields.One2many('salon.service.category', 'parent_id', string='Sub-categories')
    service_ids = fields.One2many('salon.service', 'category_id', string='Services')
    service_count = fields.Integer(compute='_compute_service_count')
    color = fields.Integer()
    active = fields.Boolean(default=True)

    def _compute_service_count(self):
        data = self.env['salon.service']._read_group(
            [('category_id', 'in', self.ids)], ['category_id'], ['__count'])
        counts = {category.id: count for category, count in data}
        for rec in self:
            rec.service_count = counts.get(rec.id, 0)

    def action_view_services(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.name,
            'res_model': 'salon.service',
            'view_mode': 'list,form',
            'domain': [('category_id', '=', self.id)],
            'context': {'default_category_id': self.id},
        }
