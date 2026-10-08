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

from odoo import api, models, _


class ReportSaleDetails(models.AbstractModel):
    _inherit = 'report.point_of_sale.report_saledetails'

    @api.model
    def get_sale_details(self, date_start=False, date_stop=False, config_ids=False, session_ids=False, **kwargs):
        """Discounts by kind. Odoo only counts a % taken off a line; the salon's
        membership discount - and pos_discount's global discount - are lines of
        their own, so the report said "0 discounts" on a day full of them.
        Each membership plan is its own group (the line carries the plan's
        name), then the global discount, then % taken off lines."""
        res = super().get_sale_details(date_start, date_stop, config_ids, session_ids, **kwargs)
        if not session_ids:
            date_start, date_stop = self._get_date_start_and_date_stop(date_start, date_stop)
        orders = self.env['pos.order'].search(
            self._get_domain(date_start, date_stop, config_ids, session_ids, **kwargs))
        lines = orders.lines

        membership = self.env.ref(
            'salon_spa_scheduler.product_product_membership_discount', raise_if_not_found=False)
        global_products = orders.config_id.mapped('discount_product_id') \
            if 'discount_product_id' in self.env['pos.config']._fields else self.env['product.product']

        groups = {}

        def add(name, count, amount):
            entry = groups.setdefault(name, {'name': name, 'count': 0, 'amount': 0.0})
            entry['count'] += count
            entry['amount'] += amount

        for line in lines:
            if membership and line.product_id == membership:
                add(line.full_product_name or line.product_id.display_name, 1, -line.price_subtotal_incl)
            elif line.product_id in global_products:
                add(_('Global discount'), 1, -line.price_subtotal_incl)
        line_discounts = lines.filtered(lambda l: l.discount > 0)
        if line_discounts:
            add(_('Discount on lines'), len(line_discounts),
                sum(l._get_discount_amount() for l in line_discounts))

        salon_discounts = sorted(groups.values(), key=lambda g: (-g['count'], g['name']))

        # Tips: a tip line carries the beautician it is for (staff_id).
        tips = {}
        for line in lines.filtered('staff_id'):
            entry = tips.setdefault(line.staff_id.id, {'name': line.staff_id.name, 'count': 0, 'amount': 0.0})
            entry['count'] += 1
            entry['amount'] += line.price_subtotal_incl
        salon_tips = sorted(tips.values(), key=lambda t: (-t['amount'], t['name']))
        res.update({
            'salon_tips': salon_tips,
            'salon_tips_count': sum(t['count'] for t in salon_tips),
            'salon_tips_total': sum(t['amount'] for t in salon_tips),
            'salon_discounts': salon_discounts,
            'discount_number': sum(g['count'] for g in salon_discounts),
            'discount_amount': sum(g['amount'] for g in salon_discounts),
        })
        return res
