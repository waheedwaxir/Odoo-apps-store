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

from odoo import _, api, fields, models

ITEM_TYPES = [
    ('service', 'Service'),
    ('product', 'Retail Product'),
    ('sundry', 'Sundry / Tip'),
    ('package', 'Package'),
    ('other', 'Other'),
]


class SalonCustomerHistory(models.Model):
    _name = 'salon.customer.history'
    _description = 'Customer Service History'
    _order = 'date desc'

    partner_id = fields.Many2one('res.partner', string='Customer', required=True, ondelete='cascade')
    company_id = fields.Many2one(
        'res.company', string='Company', required=True, index=True,
        default=lambda self: self.env.company)
    date = fields.Datetime(string='Date', required=True)
    service_name = fields.Char(string='Service/Product', required=True)
    staff_name = fields.Char(string='Staff/Employee')
    state = fields.Char(string='Status')
    notes = fields.Text(string='Notes')
    price_unit = fields.Float(string='Price')
    origin = fields.Char(string='Source Document')

    # --- Ledger ------------------------------------------------------------
    # The names above are enough to show a customer what they had last time;
    # the ids below are what "how much did we take on Gel Polish in March and
    # what did it cost us" needs. service_name / staff_name stay populated.
    service_id = fields.Many2one('salon.service', string='Service', index=True, ondelete='set null')
    category_id = fields.Many2one(
        'salon.service.category', string='Category', related='service_id.category_id',
        store=True, index=True, readonly=True)
    product_id = fields.Many2one('product.product', string='Product', index=True, ondelete='set null')
    staff_id = fields.Many2one('salon.staff', string='Beautician', index=True, ondelete='set null')
    pos_session_id = fields.Many2one(
        'pos.session', string='POS Session', related='appointment_id.pos_order_id.session_id',
        store=True, index=True,
        help="The till session the booking was paid in.")
    appointment_id = fields.Many2one('salon.appointment', string='Appointment',
                                     index=True, ondelete='set null')
    item_type = fields.Selection(ITEM_TYPES, string='Item Type', default='service', index=True)

    # --- Money -------------------------------------------------------------
    # price_unit is the NET amount - what was actually charged.
    quantity = fields.Float(string='Quantity', default=1.0)
    price_gross = fields.Float(string='Gross Price', help="List price before anything came off.")
    discount_amount = fields.Float(
        string='Discount', help="Reduction booked through the discount function.")
    discount_percent = fields.Float(string='Discount %')
    discount_reason = fields.Char(
        string='Discount Reason', index=True,
        help="Which scheme the reduction came from - a staff rate, a corporate "
             "agreement, a promotion, or a discount typed in by hand.")
    cost_amount = fields.Float(string='Cost of Goods')
    block = fields.Integer(string='Block',
                           help="Which block of a multi-step treatment this line paid for.")
    sale_ref = fields.Char(string='Sale Reference', index=True)

    # --- Payment -----------------------------------------------------------
    payment_method = fields.Char(
        string='Paid With', index=True,
        help="How the sale this line belongs to was settled. A sale split across "
             "two cards lists both.")
    payment_amount = fields.Float(
        string='Sale Payment Total',
        help="Total taken for the whole sale, not for this line alone.")
    is_split_payment = fields.Boolean(string='Split Payment')

    # --- Computed ----------------------------------------------------------
    margin = fields.Float(string='Margin', compute='_compute_margin', store=True)
    reduction_total = fields.Float(
        string='Total Reduction', compute='_compute_price_override', store=True,
        help="Discount plus price override - the real gap between list and takings.")
    price_override = fields.Float(
        string='Price Override', compute='_compute_price_override', store=True,
        help="What was given away by typing a different price at the till rather "
             "than applying a discount.")

    @api.depends('price_unit', 'cost_amount')
    def _compute_margin(self):
        for rec in self:
            rec.margin = (rec.price_unit or 0.0) - (rec.cost_amount or 0.0)

    @api.depends('price_gross', 'discount_amount', 'price_unit')
    def _compute_price_override(self):
        """Gross minus the booked discount rarely equals what was taken - the
        price was often simply typed over at the till. price_unit is the truth;
        the gap is exposed instead of quietly lost."""
        for rec in self:
            reduction = (rec.price_gross or 0.0) - (rec.price_unit or 0.0)
            rec.reduction_total = reduction
            rec.price_override = reduction - (rec.discount_amount or 0.0)

    # ------------------------------------------------------------------
    # Row builders - every place that writes history goes through these, so
    # the text columns and the ledger columns are always filled together.
    # ------------------------------------------------------------------
    @api.model
    def _payment_vals(self, order):
        """How the POS sale behind a line was settled."""
        if not order:
            return {}
        methods = order.payment_ids.filtered(lambda p: p.amount > 0).payment_method_id
        return {
            'sale_ref': order.name,
            'payment_method': ", ".join(methods.mapped('name')) or False,
            'payment_amount': order.amount_paid,
            'is_split_payment': len(methods) > 1,
        }

    @api.model
    def _appointment_service_vals(self, appointment, service, staff, price, state='Completed', notes=None):
        """One service performed in an appointment."""
        vals = {
            'company_id': appointment.company_id.id,
            'partner_id': appointment.partner_id.id,
            'date': appointment.start_datetime or fields.Datetime.now(),
            'service_name': service.name,
            'staff_name': staff.name,
            'state': state,
            'notes': (appointment.note or '') if notes is None else notes,
            'price_unit': price,
            'origin': appointment.name,
            'service_id': service.id,
            'staff_id': staff.id,
            'appointment_id': appointment.id,
            'item_type': 'service',
            'quantity': 1.0,
            'price_gross': price,
            'sale_ref': appointment.name,
        }
        vals.update(self._payment_vals(appointment.pos_order_id))
        return vals

    @api.model
    def _pos_line_item(self, line):
        """(item_type, salon.service) for a POS order line."""
        product = line.product_id
        tip = self.env.ref('salon_spa_scheduler.product_product_staff_tip', raise_if_not_found=False)
        membership = self.env.ref(
            'salon_spa_scheduler.product_product_membership_discount', raise_if_not_found=False)
        if tip and product == tip:
            return 'sundry', self.env['salon.service']
        if membership and product == membership:
            return 'other', self.env['salon.service']
        service = self.env['salon.service'].search([
            '|', ('product_id', '=', product.id), ('product_ids', 'in', product.id),
        ], limit=1)
        if service:
            return 'service', service
        return 'product', service

    @api.model
    def _pos_cashier_staff(self, order):
        """The beautician behind the employee logged in at the till, if any."""
        employee = order.employee_id if 'employee_id' in order._fields else False
        if not employee:
            return self.env['salon.staff']
        return self.env['salon.staff'].with_context(active_test=False).search(
            [('employee_id', '=', employee.id)], limit=1)

    @api.model
    def _pos_cashier_name(self, order):
        employee = order.employee_id if 'employee_id' in order._fields else False
        return (employee and employee.name) or order.user_id.name

    @api.model
    def _pos_line_vals(self, order, line):
        """One line of a POS sale that is not tied to an appointment.

        ``price_unit`` stays what it always was here - the line total with tax,
        i.e. what was actually taken. Gross is the same line before its
        percentage discount, so the discount is the gap between the two.
        """
        item_type, service = self._pos_line_item(line)
        net = line.price_subtotal_incl
        gross = self._pos_amount_incl(order, line, line.price_unit)
        discount = gross - net if line.discount else 0.0
        reason = _('Discount at the till') if line.discount else False
        if item_type == 'other':
            # The membership discount travels as its own negative line.
            gross, discount = 0.0, -net
            reason = line.full_product_name or line.product_id.display_name
        vals = {
            'company_id': order.company_id.id,
            'partner_id': order.partner_id.id,
            'date': order.date_order,
            'service_name': line.product_id.display_name,
            # A tip: who it is for; else picked at the till, else ("Default")
            # the employee logged in there.
            'staff_name': (line.staff_id.name or line.salon_beautician_id.name
                           or self._pos_cashier_name(order)),
            'state': 'Paid',
            'notes': line.note or order.general_customer_note or order.internal_note or '',
            'price_unit': net,
            'origin': order.name,
            'service_id': service.id,
            'product_id': line.product_id.id,
            # A tip line: the beautician the tip is for; any other line: the
            # beautician picked at the till, else the cashier when they are a
            # beautician themselves.
            'staff_id': (line.staff_id or line.salon_beautician_id
                         or (self._pos_cashier_staff(order) if item_type in ('product', 'service')
                             else self.env['salon.staff'])).id,
            'item_type': item_type,
            'quantity': line.qty,
            'price_gross': gross,
            'discount_amount': discount,
            'discount_percent': line.discount,
            'discount_reason': reason,
            'cost_amount': line.total_cost if 'total_cost' in line._fields else 0.0,
        }
        vals.update(self._payment_vals(order))
        return vals

    @api.model
    def _pos_amount_incl(self, order, line, unit_price):
        """``unit_price`` x the line's quantity, with the line's taxes."""
        return line.tax_ids_after_fiscal_position.compute_all(
            unit_price, currency=order.currency_id, quantity=line.qty,
            product=line.product_id, partner=order.partner_id)['total_included']

    @api.model
    def _appointment_pos_line_vals(self, appointment, line, performed=None):
        """One line of the POS order an appointment was checked out through.

        What was actually charged, taken from the till. A service line's gross
        is the price the checkout put on it (the service's list price), so a
        price typed over at the till shows up as Price Override and a % taken
        off as Discount. Retail added at the till and the membership discount
        line are recorded against the appointment too.
        """
        order = appointment.pos_order_id
        vals = self._pos_line_vals(order, line)
        vals.update({
            'date': appointment.start_datetime or order.date_order,
            'state': 'Completed',
            'notes': appointment.note or vals['notes'],
            'origin': appointment.name,
            'appointment_id': appointment.id,
        })
        product = line.product_id
        # The beautician is the one on the POS line when the till has it,
        # else the one on the booking's Beauticians & Services line.
        # ``performed`` is shared by all lines of the order: a service done
        # twice is matched to its two beauticians in turn, not twice to one.
        if performed is None:
            performed = [(service, staff) for service, staff, _p, _s
                         in appointment._billable_services()]
        match = next(((service, staff) for service, staff in performed
                      if product in service.product_ids), None)
        if match:
            performed.remove(match)
            service, staff = match
            staff = line.salon_beautician_id or staff
            expected = (service.list_price if len(service.product_ids) == 1
                        else (product.list_price or service.list_price))
            vals.update({
                'item_type': 'service',
                'service_id': service.id,
                'service_name': service.name,
                'staff_id': staff.id,
                'staff_name': staff.name,
                'price_gross': self._pos_amount_incl(order, line, expected),
            })
        elif line.salon_beautician_id:
            # Added at the till and given a beautician there.
            vals['staff_id'] = line.salon_beautician_id.id
            vals['staff_name'] = line.salon_beautician_id.name
        elif vals['item_type'] == 'product':
            # Retail left on "Default": it stays with the cashier (as set by
            # _pos_line_vals).
            pass
        elif vals['item_type'] != 'sundry':
            vals['staff_name'] = appointment.staff_id.name
        return vals

    @api.model
    def _log_pos_order(self, order):
        """(Re)write the history of a paid POS order with no appointment behind it."""
        self.search([('origin', '=', order.name)]).unlink()
        vals_list = [self._pos_line_vals(order, line) for line in order.lines]
        if vals_list:
            self.create(vals_list)

    @api.model
    def _populate_history_if_empty(self):
        # Populate history if empty
        if not self.search_count([]):
            # 1. Completed appointments - from their POS lines when paid there
            self.env['salon.appointment'].search([('state', '=', 'done')])._log_sale_history()
            history_vals = []
            # 1b. Log cancelled appointments
            cancelled = self.env['salon.appointment'].search([('state', '=', 'cancel')])
            for rec in cancelled:
                if rec.partner_id:
                    history_vals.append(rec._cancelled_history_vals(rec.note or ''))
            if history_vals:
                self.create(history_vals)
            # 2. Fetch POS orders not linked to appointments
            pos_orders = self.env['pos.order'].search([('state', 'in', ['paid', 'done', 'invoiced'])])
            for order in pos_orders:
                appt = self.env['salon.appointment'].search([('pos_order_id', '=', order.id)], limit=1)
                if not appt and order.partner_id:
                    self._log_pos_order(order)
