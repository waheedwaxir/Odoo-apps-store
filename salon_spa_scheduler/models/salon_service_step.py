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

from datetime import timedelta
from odoo import fields, models, api, _
from odoo.exceptions import UserError

class SalonServiceStep(models.Model):
    _name = 'salon.service.step'
    _description = 'Salon Service Step'
    _order = 'sequence, id'

    service_id = fields.Many2one('salon.service', string='Service', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='service_id.company_id', store=True, index=True, readonly=True)
    sequence = fields.Integer(string='Sequence', default=10)
    source_service_id = fields.Many2one(
        'salon.service', string='From Service', ondelete='set null',
        help="Build this step from an existing service. Its name and duration are "
             "copied over (you can still override the step name below).")
    name = fields.Char(string='Step Name', required=True)
    duration_minutes = fields.Integer(string='Duration (Minutes)', default=30, required=True)
    need_staff = fields.Boolean(string='Need Staff?', default=True)
    run_parallel = fields.Boolean(
        string='Run In Parallel',
        help="Start this step at the same time as the previous step instead of "
             "after it finishes - e.g. a second beautician working on the "
             "customer at once. Ignored for the first step.")
    is_processing_break = fields.Boolean(
        string='Processing Time',
        help="A gap where the treatment continues but nobody is working on the "
             "customer - colour developing, a mask setting. Modelled as a step "
             "with no staff, so the timeline reserves the chair without "
             "reserving a beautician.")

    @api.onchange('source_service_id')
    def _onchange_source_service_id(self):
        if self.source_service_id:
            self.name = self.source_service_id.name
            if self.source_service_id.duration:
                self.duration_minutes = int(round(self.source_service_id.duration * 60))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # A processing break never occupies a beautician.
            if vals.get('is_processing_break'):
                vals['need_staff'] = False
            if not vals.get('name') and vals.get('source_service_id'):
                source = self.env['salon.service'].browse(vals['source_service_id'])
                vals['name'] = source.name
                if not vals.get('duration_minutes') and source.duration:
                    vals['duration_minutes'] = int(round(source.duration * 60))
        return super().create(vals_list)


class SalonAppointmentStep(models.Model):
    _name = 'salon.appointment.step'
    _description = 'Salon Appointment Step'
    _order = 'sequence, id'
    _check_company_auto = True

    appointment_id = fields.Many2one('salon.appointment', string='Appointment', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='appointment_id.company_id', store=True, index=True, readonly=True)
    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Step Name')
    service_id = fields.Many2one('salon.service', string='Service', check_company=True)
    allowed_service_ids = fields.Many2many(
        'salon.service',
        compute='_compute_allowed_service_ids',
        string='Allowed Services',
    )
    # For information only (checkout bills the services and Additional
    # Services lines). Read-only: a writable related field here rewrote the
    # service's list price from inside a booking.
    price_unit = fields.Float(string='Price', compute='_compute_price_unit')
    duration_minutes = fields.Integer(string='Duration (Minutes)', default=30, required=True)
    need_staff = fields.Boolean(string='Need Staff?', default=True)
    is_processing_break = fields.Boolean(string='Processing Time')
    timing_mode = fields.Selection([
        ('sequential', 'After Previous Step'),
        ('parallel', 'Same Time As Previous Step'),
        ('manual', 'Manual Time'),
    ], string='Timing', default='sequential', required=True,
        help="After Previous Step: starts once the previous step finishes (default).\n"
             "Same Time As Previous Step: starts alongside the current block - e.g. a "
             "second beautician working on the customer at once.\n"
             "Manual Time: set the Start Time yourself - lets this step (and any "
             "sequential steps after it) sit in a gap between other appointments "
             "instead of chaining automatically. Ignored for the first step, which "
             "always anchors to the appointment's start time.")
    staff_id = fields.Many2one('salon.staff', string='Beautician', check_company=True)
    note = fields.Text(
        string='Note',
        help="A note for this line only - what this beautician needs to know. "
             "The booking's own note (Notes tab) is for the whole visit.")
    staff_required = fields.Boolean(
        string='Required',
        help="The customer specifically requested this beautician for this service. "
             "Do not reassign to another beautician without checking with them first.")
    start_datetime = fields.Datetime(string='Start Time', compute='_compute_step_times', store=True, readonly=False)
    end_datetime = fields.Datetime(string='End Time', compute='_compute_step_times', store=True, readonly=False)

    @api.onchange('start_datetime')
    def _onchange_start_datetime_manual(self):
        # A start time typed in by hand sticks: the line leaves the chain
        # ("After Previous Step") and keeps its own time.
        for rec in self:
            if rec.start_datetime and rec.timing_mode != 'manual' \
                    and rec.start_datetime != rec._origin.start_datetime:
                rec.timing_mode = 'manual'

    @api.depends('staff_id', 'staff_id.service_ids', 'staff_id.service_category_ids', 'appointment_id.staff_service_ids')
    def _compute_allowed_service_ids(self):
        all_services = self.env['salon.service'].search([])
        for rec in self:
            if rec.staff_id:
                rec.allowed_service_ids = rec.staff_id._allowed_services()
            elif rec.appointment_id and rec.appointment_id.staff_service_ids:
                rec.allowed_service_ids = rec.appointment_id.staff_service_ids
            else:
                rec.allowed_service_ids = all_services

    @api.depends('service_id.list_price', 'sequence', 'appointment_id.step_ids.service_id')
    def _compute_price_unit(self):
        """The service's price on its first line only: a service built from
        several steps has one line per step, and the column total would count
        its price once per step."""
        for step in self:
            first = step.appointment_id.step_ids.filtered(
                lambda s: s.service_id == step.service_id
            ).sorted(lambda s: (s.sequence, s._origin.id or 0))[:1] if step.appointment_id else step
            step.price_unit = step.service_id.list_price if step.service_id and first == step else 0.0

    @api.onchange('service_id')
    def _onchange_service_id(self):
        if self.service_id:
            self.name = self.service_id.name
            if self.service_id.duration:
                self.duration_minutes = int(round(self.service_id.duration * 60))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name'):
                service = self.env['salon.service'].browse(vals['service_id']) if vals.get('service_id') else False
                vals['name'] = service.name if service else _('Service')
        steps = super().create(vals_list)
        done = steps.appointment_id.filtered(lambda a: a.state == 'done')
        if done and self._user_edit():
            self._check_done_editable(done)
            self._resync_done(done)
        return steps

    # What the Sales History and commissions of a booking are built from.
    _SALE_FIELDS = {'staff_id', 'service_id', 'price_unit', 'need_staff'}

    def _user_edit(self):
        """A person editing the booking, not the module's own bookkeeping
        (writing the till's services back at payment runs as superuser)."""
        return not self.env.su and not self.env.context.get('salon_internal_step_edit')

    def _check_done_editable(self, appts):
        """A Done booking stays as it was, except that a Salon manager may
        correct it while unpaid ("Edit Bookings After Start" in Settings)."""
        for appt in appts.filtered(lambda a: a.state == 'done'):
            if not appt.can_edit_steps:
                raise UserError(_(
                    "%s is Done: it can only be changed by a Salon manager, while it is "
                    "unpaid, with \"Edit Bookings After Start\" on in the Settings.", appt.name))

    def _resync_done(self, appts):
        """After a correction the booking follows its lines: Main Beauticians
        (as after a drag on the board) and Services - what the booking
        charges - so a service swapped or removed in the table is not still
        billed. Then the Sales History and commissions are rewritten."""
        appts = appts.exists().filtered(lambda a: a.state == 'done')
        History = self.env['salon.customer.history']
        for appt in appts:
            vals = {}
            step_staff = appt.step_ids.filtered(lambda s: s.need_staff and s.staff_id).staff_id
            if step_staff and set(step_staff.ids) != set(appt.staff_ids.ids):
                vals['staff_ids'] = [(6, 0, step_staff.ids)]
            services = appt._services_from_steps()
            if services and services.ids != appt.service_ids.ids:
                vals['service_ids'] = [(6, 0, services.ids)]
                # The lines are already right: don't rebuild them from Services.
                vals['step_ids'] = []
            if vals:
                appt.write(vals)
            imported = History.search([
                ('appointment_id', '=', appt.id), ('origin', '!=', appt.name),
                ('state', '!=', 'Cancelled')])
            if imported:
                # Imported from Shortcuts: those rows are what was really
                # charged, so keep them and only move each service row to the
                # beautician now on its line.
                performed = [(service, staff) for service, staff, _p, _s in appt._billable_services()]
                for row in imported.filtered(lambda r: r.item_type == 'service' and r.service_id):
                    match = next((m for m in performed if m[0] == row.service_id), None)
                    if match and match[1]:
                        performed.remove(match)
                        row.write({'staff_id': match[1].id, 'staff_name': match[1].name})
            else:
                appt._log_sale_history()
        appts._sync_commissions()

    def write(self, vals):
        corrected = self.env['salon.appointment']
        if self._user_edit() and self._SALE_FIELDS & set(vals):
            done = self.appointment_id.filtered(lambda a: a.state == 'done')
            if 'staff_id' in vals:
                changed = self.filtered(lambda s: s.staff_id.id != (vals['staff_id'] or False))
                done = done & changed.appointment_id
                self._check_done_editable(done)
                for step in changed.filtered(lambda s: s.appointment_id in done):
                    step.appointment_id.message_post(body=_(
                        "%(service)s: beautician changed from %(old)s to %(new)s.",
                        service=step.service_id.name or step.name,
                        old=step.staff_id.name or '-',
                        new=self.env['salon.staff'].browse(vals['staff_id']).name or '-'))
            else:
                self._check_done_editable(done)
            corrected = done
        res = super().write(vals)
        if corrected:
            self._resync_done(corrected)
        return res

    def unlink(self):
        done = self.appointment_id.filtered(lambda a: a.state == 'done') if self._user_edit() \
            else self.env['salon.appointment']
        self._check_done_editable(done)
        res = super().unlink()
        if done:
            self._resync_done(done)
        return res

    @api.depends(
        'appointment_id.start_datetime', 'sequence', 'duration_minutes', 'timing_mode',
        'appointment_id.step_ids', 'appointment_id.step_ids.duration_minutes',
        'appointment_id.step_ids.sequence', 'appointment_id.step_ids.timing_mode')
    def _compute_step_times(self):
        for step in self:
            appt = step.appointment_id
            if appt and appt.start_datetime:
                # Steps normally chain one after another (sequential). A step
                # set to "Same Time As Previous Step" instead starts alongside
                # the current block - e.g. a second beautician working on the
                # customer at once. A step set to "Manual Time" keeps whatever
                # start time was typed in for it instead of being chained -
                # this lets it (and every sequential step after it) sit in a
                # gap between other appointments. The cursor only advances to
                # the latest end time once a block is known, so a later
                # sequential step waits for every parallel step in that block.
                cursor = appt.start_datetime
                block_start = cursor
                sorted_steps = appt.step_ids.sorted(lambda s: (s.sequence, s.id or 0))
                for s in sorted_steps:
                    if s.timing_mode == 'manual':
                        # Reading s.start_datetime here returns its existing
                        # stored value (this step's own compute hasn't
                        # assigned a new one yet), so a manually-typed time
                        # survives every recompute instead of being chained.
                        s_start = s.start_datetime or cursor
                        block_start = s_start
                    elif s.timing_mode == 'parallel':
                        s_start = block_start
                    else:
                        s_start = cursor
                        block_start = s_start
                    s_end = s_start + timedelta(minutes=s.duration_minutes or 30)
                    if s == step:
                        step.start_datetime = s_start
                        step.end_datetime = s_end
                        break
                    cursor = max(cursor, s_end)
            elif not step.start_datetime:
                step.start_datetime = False
                step.end_datetime = False
