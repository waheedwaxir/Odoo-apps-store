# -*- coding: utf-8 -*-
from collections import Counter

from odoo import api, fields, models, _


class SalonClientReport(models.TransientModel):
    _name = 'salon.client.report'
    _description = 'Client Report'

    partner_id = fields.Many2one('res.partner', string='Client', required=True)

    @api.depends('partner_id')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = (
                _('Client Report - %s', rec.partner_id.display_name)
                if rec.partner_id else _('Client Report')
            )

    date_from = fields.Date(string='From')
    date_to = fields.Date(string='To')
    currency_id = fields.Many2one('res.currency', compute='_compute_stats')

    # Volume
    appointment_count = fields.Integer(string='Appointment Count', compute='_compute_stats')
    draft_count = fields.Integer(string='Draft', compute='_compute_stats')
    confirmed_count = fields.Integer(string='Confirmed', compute='_compute_stats')
    progress_count = fields.Integer(string='In Progress', compute='_compute_stats')
    done_count = fields.Integer(string='Completed', compute='_compute_stats')
    cancel_count = fields.Integer(string='Cancelled', compute='_compute_stats')
    noshow_count = fields.Integer(string='No-show / Missed', compute='_compute_stats')
    arrived_count = fields.Integer(string='Marked Arrived', compute='_compute_stats')
    cancel_rate = fields.Float(string='Cancellation Rate (%)', digits=(16, 1), compute='_compute_stats')

    # Money
    total_spent = fields.Monetary(string='Total Value', compute='_compute_stats', currency_field='currency_id')
    paid_amount = fields.Monetary(string='Paid', compute='_compute_stats', currency_field='currency_id')
    unpaid_amount = fields.Monetary(string='Unpaid', compute='_compute_stats', currency_field='currency_id')
    avg_ticket = fields.Monetary(string='Average Ticket', compute='_compute_stats', currency_field='currency_id')

    # Profile
    first_visit = fields.Date(string='First Visit', compute='_compute_stats')
    last_visit = fields.Date(string='Last Visit', compute='_compute_stats')
    favorite_staff_id = fields.Many2one('salon.staff', string='Most Booked Beautician', compute='_compute_stats')
    favorite_service_id = fields.Many2one('salon.service', string='Most Booked Service', compute='_compute_stats')
    avg_rating = fields.Float(string='Average Review', digits=(16, 1), compute='_compute_stats')
    review_count = fields.Integer(string='Reviews', compute='_compute_stats')
    membership_summary = fields.Char(string='Memberships', compute='_compute_stats')

    appointment_ids = fields.Many2many('salon.appointment', string='Appointments', compute='_compute_stats')
    history_ids = fields.Many2many('salon.customer.history', string='Service History', compute='_compute_stats')

    def _appointment_domain(self):
        self.ensure_one()
        domain = [('partner_id', '=', self.partner_id.id)] if self.partner_id else [('id', '=', 0)]
        if self.date_from:
            domain.append(('start_datetime', '>=', fields.Datetime.to_datetime(self.date_from)))
        if self.date_to:
            # include the whole end day
            end = fields.Datetime.to_datetime(self.date_to).replace(hour=23, minute=59, second=59)
            domain.append(('start_datetime', '<=', end))
        return domain

    def _history_domain(self):
        self.ensure_one()
        domain = [('partner_id', '=', self.partner_id.id)] if self.partner_id else [('id', '=', 0)]
        if self.date_from:
            domain.append(('date', '>=', fields.Datetime.to_datetime(self.date_from)))
        if self.date_to:
            end = fields.Datetime.to_datetime(self.date_to).replace(hour=23, minute=59, second=59)
            domain.append(('date', '<=', end))
        return domain

    @api.depends('partner_id', 'date_from', 'date_to')
    def _compute_stats(self):
        Appointment = self.env['salon.appointment']
        now = fields.Datetime.now()
        for rec in self:
            rec.currency_id = rec.env.company.currency_id
            appts = Appointment.search(rec._appointment_domain(), order='start_datetime')

            rec.appointment_ids = appts
            rec.appointment_count = len(appts)
            rec.draft_count = len(appts.filtered(lambda a: a.state == 'draft'))
            rec.confirmed_count = len(appts.filtered(lambda a: a.state == 'confirmed'))
            rec.progress_count = len(appts.filtered(lambda a: a.state == 'progress'))
            rec.done_count = len(appts.filtered(lambda a: a.state == 'done'))
            rec.cancel_count = len(appts.filtered(lambda a: a.state == 'cancel'))
            rec.arrived_count = len(appts.filtered(lambda a: a.is_arrived))
            rec.noshow_count = len(appts.filtered(
                lambda a: a.state in ('draft', 'confirmed')
                and not a.is_arrived
                and a.start_datetime and a.start_datetime < now
            ))
            rec.cancel_rate = (rec.cancel_count / rec.appointment_count * 100.0) if rec.appointment_count else 0.0

            active = appts.filtered(lambda a: a.state != 'cancel')
            rec.total_spent = sum(active.mapped('amount_subtotal'))
            rec.paid_amount = sum(active.filtered(lambda a: a.payment_state == 'paid').mapped('amount_subtotal'))
            rec.unpaid_amount = sum(active.filtered(lambda a: a.payment_state != 'paid').mapped('amount_subtotal'))
            rec.avg_ticket = (rec.total_spent / len(active)) if active else 0.0

            dates = sorted(active.mapped('start_datetime'))
            rec.first_visit = dates[0].date() if dates else False
            rec.last_visit = dates[-1].date() if dates else False

            # Count occurrences per appointment (recordset.mapped() would de-duplicate).
            staff_counter = Counter(a.staff_id.id for a in active if a.staff_id)
            rec.favorite_staff_id = staff_counter.most_common(1)[0][0] if staff_counter else False
            service_counter = Counter(sid for a in active for sid in a.service_ids.ids)
            rec.favorite_service_id = service_counter.most_common(1)[0][0] if service_counter else False

            reviews = self.env['salon.review'].search([('partner_id', '=', rec.partner_id.id)]) if rec.partner_id else self.env['salon.review']
            rec.review_count = len(reviews)
            rec.avg_rating = (sum(int(r.rating) for r in reviews) / len(reviews)) if reviews else 0.0

            rec.membership_summary = rec.partner_id.salon_membership_summary if rec.partner_id else ''

            rec.history_ids = self.env['salon.customer.history'].search(rec._history_domain(), order='date desc')

    def action_view_appointments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Appointments - %s', self.partner_id.name),
            'res_model': 'salon.appointment',
            'domain': self._appointment_domain(),
            'views': [[False, 'list'], [False, 'form']],
            'target': 'current',
        }

    def action_open_partner(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'res_id': self.partner_id.id,
            'views': [[False, 'form']],
            'target': 'current',
        }
