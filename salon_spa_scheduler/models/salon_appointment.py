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

from contextlib import contextmanager
from datetime import datetime, time, timedelta
import pytz
from dateutil.relativedelta import relativedelta
from collections import Counter
import logging

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError, AccessError

_logger = logging.getLogger(__name__)

class SalonAppointment(models.Model):
    _name = 'salon.appointment'
    _description = 'Salon/Spa Appointment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_datetime desc'
    _check_company_auto = True

    name = fields.Char(default='New', copy=False)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True, index=True,
        default=lambda self: self.env.company, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True)
    # General Notes tab: the customer's allergies and preferences, edited in
    # place. Each is saved on the customer on its own (res.partner.write logs
    # the change in the note history), so editing one never resets the other.
    general_allergies = fields.Text(
        string='Allergies / Medical Notes',
        compute='_compute_general_notes', inverse='_inverse_general_allergies')
    general_preferences = fields.Text(
        string='Preferences / Styling Notes',
        compute='_compute_general_notes', inverse='_inverse_general_preferences')
    general_notes_text = fields.Text(compute='_compute_general_notes')
    general_notes_warning = fields.Boolean(
        compute='_compute_general_notes',
        help="The customer has General Notes and the company asks for a popup.")
    partner_comment_ids = fields.One2many(
        related='partner_id.salon_comment_ids', string='Comments', readonly=False)
    phone = fields.Char(related='partner_id.phone', readonly=False)
    branch_id = fields.Many2one(
        'res.company', string='Branch',
        default=lambda self: self.env.company,
        domain="[('id', 'in', allowed_company_ids)]",
        help="Company / branch this appointment belongs to. Branches mirror the "
             "companies configured for the database (Settings > Companies).")
    room_id = fields.Many2one('salon.room', string='Chair', help="The chair/seat allocated for this salon appointment.", check_company=True)
    staff_required = fields.Boolean(
        string='Required', compute='_compute_staff_required', store=True,
        help="Set when at least one service line in Beauticians & Services is "
             "marked Required (the customer specifically requested that beautician).")
    @api.depends('step_ids.staff_required')
    def _compute_staff_required(self):
        for rec in self:
            rec.staff_required = any(rec.step_ids.mapped('staff_required'))

    staff_ids = fields.Many2many(
        'salon.staff', 'salon_appointment_staff_rel', 'appointment_id', 'staff_id',
        string='Main Beauticians', required=True, tracking=True, check_company=True)
    staff_id = fields.Many2one(
        'salon.staff', string='Primary Beautician', required=True, tracking=True, check_company=True,
        compute='_compute_staff_id', store=True, readonly=False,
        help="Primary beautician - the first of the Main Beauticians. Used as the default "
             "assignee for service steps, commissions, tips and reports.")
    service_ids = fields.Many2many('salon.service', string='Services', required=True, check_company=True)
    staff_service_ids = fields.Many2many(
        'salon.service',
        compute='_compute_staff_service_ids',
        string='Staff Allowed Services'
    )
    service_id = fields.Many2one('salon.service', string='Primary Service', compute='_compute_service_id', store=True, readonly=False, tracking=True, check_company=True)
    amount_subtotal = fields.Float(string='Subtotal', compute='_compute_amount_subtotal', store=True)

    staff_multi = fields.Boolean(compute='_compute_staff_multi', string='Has Multiple Beauticians')

    @api.depends('staff_ids')
    def _compute_staff_id(self):
        for rec in self:
            # Primary = first of the selected beauticians; only realign when the
            # current primary is no longer part of the set.
            if rec.staff_ids and rec.staff_id not in rec.staff_ids:
                rec.staff_id = rec.staff_ids[0]
            else:
                rec.staff_id = rec.staff_id

    @api.depends('staff_ids')
    def _compute_staff_multi(self):
        for rec in self:
            rec.staff_multi = len(rec.staff_ids) > 1

    @api.onchange('staff_id')
    def _onchange_staff_id_sync_multi(self):
        # Keep the primary beautician inside the Main Beauticians set.
        if self.staff_id and self.staff_id not in self.staff_ids:
            self.staff_ids = [(4, self.staff_id.id)]

    @api.depends('staff_ids', 'staff_ids.service_ids', 'staff_ids.service_category_ids')
    def _compute_staff_service_ids(self):
        all_services = self.env['salon.service'].search([])
        for rec in self:
            rec.staff_service_ids = rec.staff_ids._allowed_services() if rec.staff_ids else all_services

    @api.model
    def _pick_staff_for_service(self, staff_pool, service, fallback_staff=False):
        # With several Main Beauticians selected, each step should go to
        # whichever of them can actually perform it - not always the primary.
        # Preference order: (1) a beautician whose Allowed Services explicitly
        # lists this service, (2) a beautician with no Allowed Services
        # restriction at all (open to anything), (3) the given fallback
        # (usually the primary beautician).
        # Returns a salon.staff recordset (0 or 1 records) rather than an id:
        # during an onchange, ids are NewId objects whose __bool__ is always
        # False, so truthiness/equality checks must stay at the record level
        # - callers convert to .id only when writing into a vals dict.
        if service and staff_pool:
            qualified = staff_pool.filtered(lambda s: service in s.effective_service_ids)
            if qualified:
                return qualified[0]
            unrestricted = staff_pool.filtered(lambda s: not s.effective_service_ids)
            if unrestricted:
                return unrestricted[0]
        if fallback_staff:
            return fallback_staff
        return staff_pool[:1]

    @api.model
    def _default_timing_mode(self, prev_staff, assigned_staff):
        # Auto-generated steps default to chaining sequentially, EXCEPT when
        # this step lands on a different beautician than the previous one -
        # two different beauticians can work the same customer at once, so
        # default that to Same Time As Previous Step instead of making the
        # second beautician wait idle. Still just a default: any step's
        # Timing can be changed by hand afterwards. Comparison must stay at
        # the record level (see _pick_staff_for_service) - not .id.
        if prev_staff and assigned_staff and assigned_staff != prev_staff:
            return 'parallel'
        return 'sequential'

    start_datetime = fields.Datetime(required=True, tracking=True)
    end_datetime = fields.Datetime(compute='_compute_end_datetime', store=True, readonly=False, required=True, tracking=True, help="End date and time of the appointment, automatically computed based on selected services' durations.")
    duration = fields.Float(compute='_compute_duration', store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('progress', 'In Progress'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], default='draft', tracking=True)
    
    payment_state = fields.Selection([
        ('not_paid', 'Not Paid'),
        ('paid', 'Paid'),
    ], string='Payment State', compute='_compute_payment_state', store=True)
    
    pos_order_id = fields.Many2one('pos.order', readonly=True)
    pos_order_state = fields.Selection(related='pos_order_id.state', string='POS Order Status')
    allow_reset_cancelled = fields.Boolean(
        related='company_id.salon_allow_reset_cancelled', readonly=True)
    allow_done_without_payment = fields.Boolean(
        related='company_id.salon_allow_done_without_payment', readonly=True)
    can_add_service = fields.Boolean(compute='_compute_can_add_service')
    can_edit_steps = fields.Boolean(
        compute='_compute_can_edit_steps',
        help="The Beauticians & Services lines can be edited: always until the "
             "booking starts (Draft, Confirmed); after that - In Progress, or "
             "Done and unpaid - only for a Salon manager with \"Edit Bookings "
             "After Start\" on in the Settings.")
    note = fields.Text()
    color = fields.Integer(compute='_compute_color')
    salon_allergies = fields.Text(related='partner_id.salon_allergies', string='Allergy Information', readonly=False)
    salon_preferences = fields.Text(related='partner_id.salon_preferences', string='Customer Preferences', readonly=False)
    salon_favorite_staff_id = fields.Many2one('salon.staff', related='partner_id.salon_favorite_staff_id', string='Favorite Beautician', readonly=True)
    customer_history_ids = fields.Many2many(
        'salon.customer.history', 
        string='Customer History', 
        compute='_compute_customer_history_ids'
    )

    @api.depends('partner_id')
    def _compute_customer_history_ids(self):
        for rec in self:
            if rec.partner_id:
                rec.customer_history_ids = self.env['salon.customer.history'].search([
                    ('partner_id', '=', rec.partner_id.id)
                ], order='date desc')
            else:
                rec.customer_history_ids = [(5, 0, 0)]

    @api.depends('state', 'payment_state', 'company_id.salon_allow_edit_done_staff')
    @api.depends_context('uid')
    def _compute_can_edit_steps(self):
        manager = self.env.user.has_group('salon_spa_scheduler.group_salon_manager')
        for rec in self:
            rec.can_edit_steps = rec.state in ('draft', 'confirmed') or bool(
                manager and rec.state in ('progress', 'done') and rec.payment_state != 'paid'
                and rec.company_id.salon_allow_edit_done_staff)

    @api.depends('pos_order_id', 'pos_order_id.state')
    def _compute_payment_state(self):
        for rec in self:
            if rec.pos_order_id and rec.pos_order_id.state in ['paid', 'done', 'invoiced']:
                rec.payment_state = 'paid'
            else:
                rec.payment_state = 'not_paid'
    
    # Advanced / Walk-in / Consent / Photos
    is_walkin = fields.Boolean(
        string='Walk-in Queue',
        default=False,
        help="Walk-in Toggle (is_walkin): Selecting walk-in automatically sets the start time to the current timestamp and triggers the duration lookup based on selected services. Auto-Allocation Algorithm: Added a backend check that scans for available"
    )
    consent_signed = fields.Boolean(string='Consent Signed', default=False)
    is_arrived = fields.Boolean(string='Arrived', default=False, tracking=True)
    before_image = fields.Binary(string='Before Photo')
    after_image = fields.Binary(string='After Photo')
    qr_code = fields.Binary(string='QR Code Check-in', readonly=True)

    # Multi-service sub-lines
    line_ids = fields.One2many('salon.appointment.line', 'appointment_id', string='Additional Services')
    review_ids = fields.One2many('salon.review', 'appointment_id', string='Reviews')
    step_ids = fields.One2many('salon.appointment.step', 'appointment_id', string='Steps')
    duration_selection = fields.Selection([
        ('0.25', '15 Mins'),
        ('0.5', '30 Mins'),
        ('0.75', '45 Mins'),
        ('1.0', '1 Hour'),
        ('1.25', '1 Hour 15 Mins'),
        ('1.5', '1.5 Hours'),
        ('1.75', '1 Hour 45 Mins'),
        ('2.0', '2 Hours'),
        ('2.5', '2.5 Hours'),
        ('3.0', '3 Hours'),
        ('4.0', '4 Hours'),
    ], string='Adjust Duration', help="Manually override and adjust the appointment duration.")

    def _assign_step_times(self, steps, start):
        # Mirrors SalonAppointmentStep._compute_step_times: steps chain one
        # after another (sequential), except a step set to "Same Time As
        # Previous Step" (starts alongside the current block) or "Manual
        # Time" (keeps its own typed start time, dragging the block anchor to
        # it) - see that method's docstring for the full rationale. The
        # returned cursor is the latest end time across every step, i.e. when
        # the whole appointment is actually free again.
        cursor = start
        block_start = cursor
        for step in steps:
            if step.timing_mode == 'manual':
                s_start = step.start_datetime or cursor
                block_start = s_start
            elif step.timing_mode == 'parallel':
                s_start = block_start
            else:
                s_start = cursor
                block_start = s_start
            s_end = s_start + timedelta(minutes=step.duration_minutes or 30)
            step.start_datetime = s_start
            step.end_datetime = s_end
            cursor = max(cursor, s_end)
        return cursor

    @api.depends('start_datetime', 'step_ids', 'step_ids.duration_minutes', 'step_ids.timing_mode', 'service_ids', 'duration_selection')
    def _compute_end_datetime(self):
        for rec in self:
            if not rec.start_datetime:
                rec.end_datetime = False
                continue

            if rec.duration_selection:
                val_hours = float(rec.duration_selection)
                if rec.step_ids:
                    steps = rec.step_ids.sorted('sequence')
                    other_steps_dur = sum(s.duration_minutes for s in steps[:-1] if s.timing_mode == 'sequential')
                    target_total_mins = int(val_hours * 60)
                    last_step_dur = max(15, target_total_mins - other_steps_dur)
                    if steps[-1].duration_minutes != last_step_dur:
                        steps[-1].duration_minutes = last_step_dur
                    rec.end_datetime = rec._assign_step_times(steps, rec.start_datetime)
                else:
                    rec.end_datetime = rec.start_datetime + timedelta(hours=val_hours)
            else:
                if rec.step_ids:
                    rec.end_datetime = rec._assign_step_times(rec.step_ids.sorted('sequence'), rec.start_datetime)
                else:
                    total_duration = sum(s.duration for s in rec.service_ids) if rec.service_ids else 1.0
                    rec.end_datetime = rec.start_datetime + timedelta(hours=total_duration)

    @api.depends('start_datetime', 'end_datetime', 'duration_selection')
    def _compute_duration(self):
        for rec in self:
            if rec.start_datetime and rec.end_datetime:
                rec.duration = (rec.end_datetime - rec.start_datetime).total_seconds() / 3600
            elif rec.duration_selection:
                rec.duration = float(rec.duration_selection)
            else:
                rec.duration = 0

    @api.onchange('duration_selection')
    def _onchange_duration_selection(self):
        if self.duration_selection and self.start_datetime:
            val_hours = float(self.duration_selection)
            if self.step_ids:
                steps = self.step_ids.sorted('sequence')
                other_steps_dur = sum(s.duration_minutes for s in steps[:-1] if s.timing_mode == 'sequential')
                target_total_mins = int(val_hours * 60)
                last_step_dur = max(15, target_total_mins - other_steps_dur)
                steps[-1].duration_minutes = last_step_dur
            else:
                self.end_datetime = self.start_datetime + timedelta(hours=val_hours)

    @api.model
    def _step_line_name(self, service, step):
        """Name of a Beauticians & Services line built from a service's step.
        A one-step service whose step carries the service's own name would
        read "X - X"; it is just "X"."""
        if step.name == service.name:
            return service.name
        return f"{service.name} - {step.name}"

    @api.depends('partner_id.salon_allergies', 'partner_id.salon_preferences',
                 'partner_id.salon_comment_ids.comment', 'partner_id.salon_comment_ids.comment_type',
                 'company_id.salon_general_notes_warning')
    def _compute_general_notes(self):
        for rec in self:
            partner = rec.partner_id
            rec.general_allergies = partner.salon_allergies
            rec.general_preferences = partner.salon_preferences
            text = partner._salon_general_notes_text() if partner else ''
            rec.general_notes_text = text or False
            rec.general_notes_warning = bool(text) and rec.company_id.salon_general_notes_warning

    def _inverse_general_allergies(self):
        for rec in self.filtered('partner_id'):
            rec.partner_id.salon_allergies = rec.general_allergies or False

    def _inverse_general_preferences(self):
        for rec in self.filtered('partner_id'):
            rec.partner_id.salon_preferences = rec.general_preferences or False

    @api.onchange('partner_id')
    def _onchange_partner_general_notes(self):
        if self.general_notes_warning:
            return {'warning': {
                'title': _("General Notes - %s", self.partner_id.display_name),
                'message': _("This customer has General Notes - see the General Notes tab.")
                           + "\n\n" + self.general_notes_text,
            }}

    @api.onchange('service_ids')
    def _onchange_service_ids_populate_steps(self):
        if self.service_ids:
            step_lines = []
            seq = 10
            staff_pool = self.staff_ids or self.staff_id
            prev_staff = self.env['salon.staff']
            for service in self.service_ids:
                if service.step_ids:
                    for step in service.step_ids:
                        assigned_staff = self._pick_staff_for_service(
                            staff_pool, step.source_service_id or service, self.staff_id
                        ) if step.need_staff else self.env['salon.staff']
                        # A service template author explicitly set Run In Parallel
                        # per step, so honour that as-is rather than the auto-guess.
                        timing_mode = 'parallel' if step.run_parallel else self._default_timing_mode(prev_staff, assigned_staff)
                        step_lines.append((0, 0, {
                            'sequence': seq,
                            'name': self._step_line_name(service, step),
                            'service_id': service.id,
                            'duration_minutes': step.duration_minutes,
                            'need_staff': step.need_staff,
                            'timing_mode': timing_mode,
                            'staff_id': assigned_staff.id if assigned_staff else False,
                        }))
                        seq += 10
                        if step.need_staff:
                            prev_staff = assigned_staff
                else:
                    assigned_staff = self._pick_staff_for_service(staff_pool, service, self.staff_id)
                    step_lines.append((0, 0, {
                        'sequence': seq,
                        'name': service.name,
                        'service_id': service.id,
                        'duration_minutes': int(service.duration * 60),
                        'need_staff': True,
                        'timing_mode': self._default_timing_mode(prev_staff, assigned_staff),
                        'staff_id': assigned_staff.id if assigned_staff else False,
                    }))
                    seq += 10
                    prev_staff = assigned_staff
            self.step_ids = [(5, 0, 0)] + step_lines
            if self.duration_selection and self.start_datetime:
                self._onchange_duration_selection()

    @api.onchange('staff_id', 'staff_ids')
    def _onchange_staff_id_update_steps(self):
        if self.staff_id:
            for step in self.step_ids:
                if step.need_staff and not step.staff_id:
                    step.staff_id = self.staff_id.id

    @api.depends('state', 'is_arrived', 'confirmation_sent')
    def _compute_color(self):
        # Scheduler colour is driven by status, not by the record id:
        #   orange  -> booking (draft)
        #   green   -> default (confirmed, confirmation sent)
        #   yellow  -> not confirmed (confirmed, confirmation not sent yet)
        #   blue    -> arrived (not started yet)
        #   purple  -> in progress
        #   grey    -> completed / checked out (done)
        #   red     -> cancelled
        for rec in self:
            if rec.state == 'cancel':
                rec.color = 1  # red
            elif rec.state == 'done':
                rec.color = 9  # grey
            elif rec.state == 'progress':
                rec.color = 6  # purple
            elif rec.is_arrived:
                rec.color = 5  # blue
            elif rec.state == 'draft':
                rec.color = 2  # orange
            elif rec.state == 'confirmed' and not rec.confirmation_sent:
                rec.color = 3  # yellow
            else:
                rec.color = 4  # green

    @api.onchange('is_walkin', 'service_ids', 'branch_id')
    def _onchange_walkin_allocation(self):
        if self.is_walkin and self.branch_id:
            now = fields.Datetime.now()
            self.start_datetime = now
            total_duration = sum(s.duration for s in self.service_ids) if self.service_ids else 1.0
            self.end_datetime = now + timedelta(hours=total_duration)
            
            # Find an available staff member
            available_staff = self.env['salon.staff'].search([
                ('active', '=', True)
            ])
            assigned_staff = False
            for staff in available_staff:
                overlap_count = self.env['salon.appointment'].search_count([
                    ('staff_id', '=', staff.id),
                    ('state', '!=', 'cancel'),
                    ('start_datetime', '<', self.end_datetime),
                    ('end_datetime', '>', self.start_datetime),
                ])
                if not overlap_count:
                    assigned_staff = staff
                    break
            if assigned_staff:
                self.staff_id = assigned_staff
                
            # Find an available chair (room) in this branch
            available_chairs = self.env['salon.room'].search([
                ('branch_id', '=', self.branch_id.id),
                ('active', '=', True)
            ])
            assigned_chair = False
            for chair in available_chairs:
                overlap_count = self.env['salon.appointment'].search_count([
                    ('room_id', '=', chair.id),
                    ('state', '!=', 'cancel'),
                    ('start_datetime', '<', self.end_datetime),
                    ('end_datetime', '>', self.start_datetime),
                ])
                if not overlap_count:
                    assigned_chair = chair
                    break
            if assigned_chair:
                self.room_id = assigned_chair

    @api.depends('service_ids')
    def _compute_service_id(self):
        for rec in self:
            if rec.service_ids:
                rec.service_id = rec.service_ids[0].id
            else:
                rec.service_id = False

    @api.onchange('service_id')
    def _onchange_service_id_sync(self):
        if self.service_id and self.service_id not in self.service_ids:
            self.service_ids = [(4, self.service_id.id)]

    @api.onchange('service_ids')
    def _onchange_service_ids_sync(self):
        if self.service_ids:
            self.service_id = self.service_ids[0].id
        else:
            self.service_id = False

    @api.depends('service_ids', 'service_ids.list_price', 'line_ids.price_unit',
                 'line_ids.service_id', 'step_ids.service_id', 'step_ids.sequence')
    def _compute_amount_subtotal(self):
        for rec in self:
            rec.amount_subtotal = sum(price for _s, _st, price, _k in rec._billable_services())

    def _billable_services(self):
        """What this booking charges: [(service, beautician, price, source)].

        The Beauticians & Services table is what was done. Each service in
        it is charged once per time it was done - a service built from k
        steps once per k lines - to the beautician on its (first) line:
        - the booking's Services, at list price ('booking');
        - Additional Services lines, at their own price and beautician
          ('line');
        - anything else the table has, e.g. a second service typed into the
          table or the same service again for another beautician, at list
          price ('table').
        """
        self.ensure_one()
        steps = self.step_ids.filtered('service_id').sorted(
            lambda s: (s.sequence, s._origin.id or 0))
        runs = {}
        for service in steps.service_id:
            lines = steps.filtered(lambda s, sv=service: s.service_id == sv)
            size = max(len(service.step_ids), 1)
            runs[service] = [lines[i:i + size].filtered('staff_id')[:1].staff_id
                             for i in range(0, len(lines), size)]
        result = []
        for service in self.service_ids:
            staff = runs[service].pop(0) if runs.get(service) else False
            result.append((service, staff or self.staff_id, service.list_price, 'booking'))
        for line in self.line_ids.filtered('service_id'):
            if runs.get(line.service_id):
                # Add Service puts its steps at the end of the table.
                runs[line.service_id].pop()
            result.append((line.service_id, line.staff_id or self.staff_id, line.price_unit, 'line'))
        for service, rest in runs.items():
            for staff in rest:
                result.append((service, staff or self.staff_id, service.list_price, 'table'))
        return result

    def _services_from_steps(self):
        """The booking's Services as its Beauticians & Services table has
        them: each service in the table once, unless every time it was done
        is already an Additional Services line (those bill on their own)."""
        self.ensure_one()
        steps = self.step_ids.filtered('service_id').sorted('sequence')
        result = self.env['salon.service']
        for service in steps.service_id:
            size = max(len(service.step_ids), 1)
            done = -(-len(steps.filtered(lambda s, sv=service: s.service_id == sv)) // size)
            extra = len(self.line_ids.filtered(lambda l, sv=service: l.service_id == sv))
            if done > extra:
                result |= service
        return result

    @api.onchange('service_ids', 'line_ids', 'step_ids')
    def _onchange_services_subtotal(self):
        self._compute_amount_subtotal()

    @api.onchange('service_ids', 'start_datetime')
    def _onchange_service_time(self):
        for rec in self:
            if rec.service_ids and rec.start_datetime:
                total_duration = sum(s.duration for s in rec.service_ids)
                rec.end_datetime = rec.start_datetime + timedelta(hours=total_duration)

    def _working_hours_check(self, employee, calendar, start_dt, end_dt):
        """Return (is_covered, [shift strings]) for the employee's calendar on the
        day of start_dt. Shift strings are de-duplicated and ordered."""
        start_aware = start_dt.replace(tzinfo=pytz.utc)
        end_aware = end_dt.replace(tzinfo=pytz.utc)

        work_intervals = calendar._work_intervals_batch(
            start_aware, end_aware, resources=employee.resource_id
        )[employee.resource_id.id]
        intervals_list = [(s, e) for s, e, _m in work_intervals]
        is_covered = any(s <= start_aware and e >= end_aware for s, e in intervals_list)

        day_start = datetime.combine(start_dt.date(), time.min).replace(tzinfo=pytz.utc)
        day_end = datetime.combine(start_dt.date(), time.max).replace(tzinfo=pytz.utc)
        day_work_intervals = calendar._work_intervals_batch(
            day_start, day_end, resources=employee.resource_id
        )[employee.resource_id.id]

        local_tz = pytz.timezone(employee.tz or calendar.tz or 'UTC')
        shifts = []
        for s, e, _m in day_work_intervals:
            label = "%s to %s" % (
                s.astimezone(local_tz).strftime('%I:%M %p'),
                e.astimezone(local_tz).strftime('%I:%M %p'),
            )
            if label not in shifts:
                shifts.append(label)
        return is_covered, shifts

    def _tz(self):
        return pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')

    def _planning_shift_ranges(self, staff, ref_dt):
        """Published ``planning.slot`` records for ``staff``'s employee on the
        local calendar day of ``ref_dt``, as a list of ``(start, end)`` naive-UTC
        datetime tuples (ordered). An empty list means the employee has no
        published shift that day. Beauticians not linked to an ``hr.employee``
        are not managed by Planning and return ``None`` (no gate)."""
        if not staff or not staff.employee_id or not ref_dt:
            return None
        tz = self._tz()
        local_day = pytz.utc.localize(ref_dt).astimezone(tz).date()
        day_start = tz.localize(datetime.combine(local_day, time.min)).astimezone(pytz.utc).replace(tzinfo=None)
        day_end = tz.localize(datetime.combine(local_day + timedelta(days=1), time.min)).astimezone(pytz.utc).replace(tzinfo=None)
        slots = self.env['planning.slot'].sudo().search([
            ('employee_id', '=', staff.employee_id.id),
            ('company_id', 'in', self.env.companies.ids),
            ('state', '=', 'published'),
            ('start_datetime', '<', day_end),
            ('end_datetime', '>', day_start),
        ], order='start_datetime')
        return [(s.start_datetime, s.end_datetime) for s in slots]

    def _planning_shift_hint(self, ranges):
        return ", ".join(
            "%s-%s" % (
                fields.Datetime.context_timestamp(self, r0).strftime('%H:%M'),
                fields.Datetime.context_timestamp(self, r1).strftime('%H:%M'),
            )
            for r0, r1 in (ranges or [])
        )

    def _check_planning_shift(self, staff, start_dt, end_dt):
        """Raise unless the ``[start_dt, end_dt]`` window for ``staff`` lies fully
        inside one of that beautician's published Planning shifts for the day.
        A beautician with no shift that day cannot be booked; one not linked to an
        employee is unrestricted. Enforced even for scheduler drag/resize - a
        Planning shift is a hard limit, unlike the resource-calendar roster."""
        if not start_dt or not end_dt:
            return
        ranges = self._planning_shift_ranges(staff, start_dt)
        if ranges is None:
            return
        if any(r0 <= start_dt and end_dt <= r1 for r0, r1 in ranges):
            return
        if ranges:
            raise ValidationError(_(
                "%(name)s is only scheduled %(hours)s on this day (Planning shift).",
                name=staff.name, hours=self._planning_shift_hint(ranges),
            ))
        raise ValidationError(_(
            "%(name)s has no Planning shift on this day.", name=staff.name,
        ))

    @api.constrains('staff_id', 'staff_ids', 'start_datetime', 'end_datetime', 'state')
    def _check_salon_block_clash(self):
        """No booking on top of a confirmed time block.

        Blocks are how the salon says "this beautician is not on the floor" -
        training, a meeting, duty at the other branch. The migration context
        switches this off, because two years of imported history contains
        bookings and blocks that genuinely overlapped.
        """
        if self.env.context.get('skip_salon_overlap_check') \
                or self.env.context.get('skip_salon_block_overlap'):
            return
        Block = self.env['salon.block']
        for rec in self:
            if rec.state in ('cancel', 'draft') or not rec.start_datetime or not rec.end_datetime:
                continue
            staff = rec.staff_ids | rec.staff_id | rec.step_ids.staff_id
            if not staff:
                continue
            clash = Block.search([
                ('staff_id', 'in', staff.ids),
                ('state', '=', 'confirmed'),
                ('block_type_id.blocks_booking', '=', True),
                ('start_datetime', '<', rec.end_datetime),
                ('end_datetime', '>', rec.start_datetime),
            ], limit=1)
            if clash:
                raise ValidationError(_(
                    '%(staff)s is blocked out for "%(block)s" at this time.',
                    staff=clash.staff_id.name, block=clash.name))

    @api.constrains('staff_id', 'staff_ids', 'start_datetime', 'end_datetime', 'state', 'room_id')
    def _check_overlap(self):
        # Bulk import of historical data: technicians there genuinely overlapped
        # across chairs. Live booking still validates as normal.
        if self.env.context.get('skip_salon_overlap_check'):
            return
        for rec in self:
            if not rec.staff_id or not rec.start_datetime or not rec.end_datetime or rec.state == 'cancel':
                continue
            if rec.end_datetime <= rec.start_datetime:
                raise ValidationError(_('End time must be after start time.'))

            # Availability check (only while the booking can still be moved).
            # A beautician linked to an employee is governed by their published
            # Planning shifts: the booking must fall inside a shift, and this is a
            # hard limit even for a deliberate scheduler drag. Beauticians with no
            # linked employee fall back to the resource-calendar roster, which a
            # drag/resize may still override (skip_working_hours_check).
            # Draft is still just a tentative hold, same as the staff/room overlap
            # checks below - it can freely move anywhere, no matter how many
            # steps/beauticians it has, until it's Confirmed and becomes a real
            # commitment.
            if rec.state == 'confirmed':
                planning_staff = set()
                if rec.step_ids:
                    checks = [
                        (step.staff_id, step.start_datetime, step.end_datetime)
                        for step in rec.step_ids
                        if step.need_staff and step.staff_id and step.start_datetime and step.end_datetime
                    ]
                    checks.append((rec.staff_id, rec.start_datetime, rec.end_datetime))
                else:
                    checks = [
                        (staff, rec.start_datetime, rec.end_datetime)
                        for staff in (rec.staff_ids or rec.staff_id)
                    ]
                for staff, s_dt, e_dt in checks:
                    if staff.employee_id:
                        rec._check_planning_shift(staff, s_dt, e_dt)
                        planning_staff.add(staff.id)

                if (rec.staff_id.employee_id and rec.staff_id.id not in planning_staff
                        and not self.env.context.get('skip_working_hours_check')):
                    employee = rec.staff_id.employee_id
                    calendar = employee.resource_calendar_id or employee.company_id.resource_calendar_id
                    if calendar:
                        is_covered, available_shifts = rec._working_hours_check(
                            employee, calendar, rec.start_datetime, rec.end_datetime)
                        if not is_covered:
                            if available_shifts:
                                raise ValidationError(_("%(name)s is only available from %(shifts)s on this time.") % {
                                    'name': employee.name,
                                    'shifts': " or ".join(available_shifts),
                                })
                            else:
                                raise ValidationError(_("%(name)s is not working on this time.") % {
                                    'name': employee.name
                                })

            # Staff overlap check (step-based validation)
            if rec.step_ids:
                for step in rec.step_ids:
                    if not step.need_staff or not step.staff_id or not step.start_datetime or not step.end_datetime:
                        continue

                    # Parallel steps are allowed to overlap in time, but not for
                    # the *same* beautician - a step marked to run alongside
                    # another one must use a different staff member.
                    sibling_overlap = any(
                        other.id != step.id
                        and other.need_staff and other.staff_id == step.staff_id
                        and other.start_datetime and other.end_datetime
                        and other.start_datetime < step.end_datetime
                        and other.end_datetime > step.start_datetime
                        for other in rec.step_ids
                    )
                    if sibling_overlap:
                        raise ValidationError(_('%s is assigned to two overlapping steps (%s - %s) on this appointment. Assign a different beautician to one of them.') % (
                            step.staff_id.name,
                            fields.Datetime.context_timestamp(self, step.start_datetime).strftime('%H:%M'),
                            fields.Datetime.context_timestamp(self, step.end_datetime).strftime('%H:%M')
                        ))

                    # A Draft booking is just a tentative hold - it's fine for it
                    # to overlap another beautician's existing appointment(s) for
                    # now. The hard double-booking check only kicks in once this
                    # booking itself is Confirmed (or later), at which point it
                    # becomes a real commitment.
                    if rec.state == 'draft':
                        continue

                    # Check against other appointments' steps
                    other_steps_overlap = self.env['salon.appointment.step'].search_count([
                        ('appointment_id', '!=', rec.id),
                        ('appointment_id.state', '!=', 'cancel'),
                        ('staff_id', '=', step.staff_id.id),
                        ('need_staff', '=', True),
                        ('start_datetime', '<', step.end_datetime),
                        ('end_datetime', '>', step.start_datetime),
                    ])
                    if other_steps_overlap:
                        raise ValidationError(_('Staff member %s already has an appointment step booked during %s - %s.') % (
                            step.staff_id.name,
                            fields.Datetime.context_timestamp(self, step.start_datetime).strftime('%H:%M'),
                            fields.Datetime.context_timestamp(self, step.end_datetime).strftime('%H:%M')
                        ))

                    # Check against other appointments that have NO steps (fallback overlap check)
                    other_appts_no_steps = self.search([
                        ('id', '!=', rec.id),
                        ('state', '!=', 'cancel'),
                        ('staff_id', '=', step.staff_id.id),
                        ('start_datetime', '<', step.end_datetime),
                        ('end_datetime', '>', step.start_datetime),
                    ])
                    for other_appt in other_appts_no_steps:
                        if not other_appt.step_ids:
                            raise ValidationError(_('Staff member %s is busy with appointment %s during %s - %s.') % (
                                step.staff_id.name,
                                other_appt.name,
                                fields.Datetime.context_timestamp(self, step.start_datetime).strftime('%H:%M'),
                                fields.Datetime.context_timestamp(self, step.end_datetime).strftime('%H:%M')
                            ))
            elif rec.state != 'draft':
                # Fallback: Standard staff overlap check - one per selected beautician.
                # Skipped while still Draft (see comment above) - a tentative
                # booking may overlap another beautician's appointment until
                # it's Confirmed.
                for staff in (rec.staff_ids or rec.staff_id):
                    domain = [
                        ('id', '!=', rec.id),
                        ('staff_ids', 'in', staff.id),
                        ('state', '!=', 'cancel'),
                        ('start_datetime', '<', rec.end_datetime),
                        ('end_datetime', '>', rec.start_datetime),
                    ]
                    step_overlaps = self.env['salon.appointment.step'].search_count([
                        ('appointment_id', '!=', rec.id),
                        ('appointment_id.state', '!=', 'cancel'),
                        ('staff_id', '=', staff.id),
                        ('need_staff', '=', True),
                        ('start_datetime', '<', rec.end_datetime),
                        ('end_datetime', '>', rec.start_datetime),
                    ])
                    if self.search_count(domain) or step_overlaps:
                        raise ValidationError(_('%s already has an appointment during this time.') % staff.name)

            # Room/Chair overlap check. Same tentative-hold logic as the staff
            # checks above: a Draft can freely overlap another booking's chair
            # (or another Draft's) until it's Confirmed and becomes a real
            # commitment.
            if rec.room_id and rec.state != 'draft':
                room_domain = [
                    ('id', '!=', rec.id),
                    ('room_id', '=', rec.room_id.id),
                    ('state', '!=', 'cancel'),
                    ('start_datetime', '<', rec.end_datetime),
                    ('end_datetime', '>', rec.start_datetime),
                ]
                if self.search_count(room_domain):
                    raise ValidationError(_('This chair is already booked during this time.'))

    @api.onchange('staff_id', 'start_datetime', 'end_datetime')
    def _onchange_staff_working_hours(self):
        if not self.staff_id or not self.staff_id.employee_id or not self.start_datetime or not self.end_datetime:
            return
            
        employee = self.staff_id.employee_id
        calendar = employee.resource_calendar_id or employee.company_id.resource_calendar_id
        if not calendar:
            return

        is_covered, available_shifts = self._working_hours_check(
            employee, calendar, self.start_datetime, self.end_datetime)

        if not is_covered:
            if available_shifts:
                message = _("%(name)s is only available from %(shifts)s on this day.") % {
                    'name': employee.name,
                    'shifts': " or ".join(available_shifts),
                }
            else:
                message = _("%(name)s is not working on this day.") % {
                    'name': employee.name
                }
                
            return {
                'warning': {
                    'title': _("Staff Scheduling Warning"),
                    'message': message,
                }
            }

    # Reminder and confirmation track
    reminder_sent_30m = fields.Boolean(string='30-Min Reminder Sent', default=False)
    confirmation_sent = fields.Boolean(string='Confirmation Email Sent', default=False, copy=False)

    @staticmethod
    def _sync_branch_company_vals(vals):
        """Branch and company are the same thing - branches mirror companies -
        but the form shows both. Whichever one is given sets the other, so the
        scheduler (which filters on branch) and the company checks on staff,
        services and chairs (which look at company) can never disagree."""
        if vals.get('branch_id') and 'company_id' not in vals:
            vals['company_id'] = vals['branch_id']
        elif vals.get('company_id') and 'branch_id' not in vals:
            vals['branch_id'] = vals['company_id']
        return vals

    @api.onchange('branch_id')
    def _onchange_branch_id_company(self):
        if self.branch_id and self.company_id != self.branch_id:
            self.company_id = self.branch_id

    @api.onchange('company_id')
    def _onchange_company_id_branch(self):
        if self.company_id and self.branch_id != self.company_id:
            self.branch_id = self.company_id

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env['ir.sequence'].sudo()
        default_company_id = self.env.company.id
        for vals in vals_list:
            self._sync_branch_company_vals(vals)
            if vals.get('name', 'New') == 'New':
                company_id = vals.get('company_id') or default_company_id
                vals['name'] = seq.with_company(company_id).next_by_code('salon.appointment') or 'New'
            # Back-compat: callers that only pass a single staff_id still work.
            if vals.get('staff_id') and not vals.get('staff_ids'):
                vals['staff_ids'] = [(6, 0, [vals['staff_id']])]
            # The normal form flow is the other way around: the widget only sends
            # staff_ids (staff_id is a readonly compute in the view). staff_id is a
            # required, stored column though, and required+computed fields skip
            # the friendly ORM validation - a compute that hasn't run yet leaves it
            # NULL and Postgres raises a raw "mandatory field" error instead. Set it
            # directly here so the column always has a value at insert time.
            if vals.get('staff_ids') and not vals.get('staff_id'):
                for cmd in vals['staff_ids']:
                    if isinstance(cmd, int):
                        vals['staff_id'] = cmd
                        break
                    if isinstance(cmd, (list, tuple)) and cmd[0] == 6 and cmd[2]:
                        vals['staff_id'] = cmd[2][0]
                        break
                    if isinstance(cmd, (list, tuple)) and cmd[0] == 4:
                        vals['staff_id'] = cmd[1]
                        break
            if 'service_id' in vals and 'service_ids' not in vals:
                vals['service_ids'] = [(4, vals['service_id'])]
            elif 'service_ids' in vals and 'service_id' not in vals:
                s_ids = vals['service_ids']
                flat_ids = []
                for cmd in s_ids:
                    if cmd[0] == 6:
                        flat_ids.extend(cmd[2])
                    elif cmd[0] == 4:
                        flat_ids.append(cmd[1])
                if flat_ids:
                    vals['service_id'] = flat_ids[0]
            
            # Populate step_ids if service(s) are selected on create
            if ('service_ids' in vals or 'service_id' in vals) and 'step_ids' not in vals:
                s_ids = []
                if 'service_ids' in vals:
                    for cmd in vals['service_ids']:
                        if isinstance(cmd, (list, tuple)) and len(cmd) == 3:
                            if cmd[0] == 6:
                                s_ids.extend(cmd[2])
                            elif cmd[0] == 4:
                                s_ids.append(cmd[1])
                elif 'service_id' in vals:
                    s_ids = [vals['service_id']]
                
                if s_ids:
                    services = self.env['salon.service'].browse(s_ids)
                    step_lines = []
                    seq_num = 10
                    staff_id_list = []
                    if vals.get('staff_id'):
                        staff_id_list.append(vals['staff_id'])
                    for cmd in vals.get('staff_ids') or []:
                        if isinstance(cmd, int):
                            staff_id_list.append(cmd)
                        elif isinstance(cmd, (list, tuple)) and cmd[0] == 6 and cmd[2]:
                            staff_id_list.extend(cmd[2])
                        elif isinstance(cmd, (list, tuple)) and cmd[0] == 4:
                            staff_id_list.append(cmd[1])
                    staff_id_list = list(dict.fromkeys(staff_id_list))
                    staff_pool = self.env['salon.staff'].browse(staff_id_list)
                    primary_staff = self.env['salon.staff'].browse(
                        vals.get('staff_id') or (staff_id_list[0] if staff_id_list else False)
                    )
                    prev_staff = self.env['salon.staff']
                    for service in services:
                        if service.step_ids:
                            for step in service.step_ids:
                                assigned_staff = self._pick_staff_for_service(
                                    staff_pool, step.source_service_id or service, primary_staff
                                ) if step.need_staff else self.env['salon.staff']
                                timing_mode = 'parallel' if step.run_parallel else self._default_timing_mode(prev_staff, assigned_staff)
                                step_lines.append((0, 0, {
                                    'sequence': seq_num,
                                    'name': self._step_line_name(service, step),
                                    'service_id': service.id,
                                    'duration_minutes': step.duration_minutes,
                                    'need_staff': step.need_staff,
                                    'timing_mode': timing_mode,
                                    'staff_id': assigned_staff.id if assigned_staff else False,
                                }))
                                seq_num += 10
                                if step.need_staff:
                                    prev_staff = assigned_staff
                        else:
                            assigned_staff = self._pick_staff_for_service(staff_pool, service, primary_staff)
                            step_lines.append((0, 0, {
                                'sequence': seq_num,
                                'name': service.name,
                                'service_id': service.id,
                                'duration_minutes': int(service.duration * 60),
                                'need_staff': True,
                                'timing_mode': self._default_timing_mode(prev_staff, assigned_staff),
                                'staff_id': assigned_staff.id if assigned_staff else False,
                            }))
                            seq_num += 10
                            prev_staff = assigned_staff
                    if step_lines:
                        vals['step_ids'] = step_lines

        records = super().create(vals_list)
        
        # Queue the confirmation email (force_send=False) so a slow/unavailable
        # mail server never blocks the caller - e.g. the website booking request.
        template = self.env.ref('salon_spa_scheduler.email_template_appointment_confirmation', raise_if_not_found=False)
        if template:
            for rec in records:
                if rec.state == 'confirmed' and not rec.confirmation_sent:
                    template.send_mail(rec.id, force_send=False)
                    rec.confirmation_sent = True
        return records

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        for rec, vals in zip(self, vals_list):
            # A duplicate is always a fresh, unpaid, unconfirmed booking - never
            # carry over the source's lifecycle/visit-specific state.
            vals['state'] = 'draft'
            vals['pos_order_id'] = False
            vals['is_arrived'] = False
            vals['consent_signed'] = False
            vals['before_image'] = False
            vals['after_image'] = False
            vals['qr_code'] = False
            vals['review_ids'] = [(5, 0, 0)]
            # The source appointment still occupies its own time slot, so keeping
            # the exact same start/end would make the duplicate immediately
            # conflict with it. Shift both by a day, preserving the original
            # duration, unless the caller explicitly asked for a specific start.
            if not (default or {}).get('start_datetime') and rec.start_datetime and rec.end_datetime:
                delta = timedelta(days=1)
                vals['start_datetime'] = rec.start_datetime + delta
                # end_datetime is a required, stored computed field: required
                # fields that are also computed skip the friendly ORM "required"
                # check (the compute is trusted to fill them in), so if it
                # doesn't run in time during create() the column hits Postgres
                # as NULL and surfaces as a raw DB error. Set it explicitly
                # instead of relying on the compute to run during create().
                vals['end_datetime'] = rec.end_datetime + delta
            # Each step's start/end are computed too but NOT required, so it's
            # safe to just drop the stale copied values and let them recompute
            # from the appointment's (now shifted) start_datetime.
            for cmd in vals.get('step_ids') or []:
                if isinstance(cmd, (list, tuple)) and cmd[0] == 0 and isinstance(cmd[2], dict):
                    cmd[2].pop('start_datetime', None)
                    cmd[2].pop('end_datetime', None)
        return vals_list

    def write(self, vals):
        self._sync_branch_company_vals(vals)
        # Arrival follows confirmation: a booking put back to Draft is not
        # "arrived" any more (the board would still show it blue).
        if vals.get('state') == 'draft':
            vals['is_arrived'] = False
        if 'service_id' in vals and 'service_ids' not in vals:
            vals['service_ids'] = [(6, 0, [vals['service_id']])]
        elif 'service_ids' in vals and 'service_id' not in vals:
            s_ids = vals['service_ids']
            flat_ids = []
            for cmd in s_ids:
                if cmd[0] == 6:
                    flat_ids.extend(cmd[2])
                elif cmd[0] == 4:
                    flat_ids.append(cmd[1])
            if flat_ids:
                vals['service_id'] = flat_ids[0]
            elif s_ids == [(5, 0, 0)] or s_ids == [(5,)]:
                vals['service_id'] = False
        
        # Populate step_ids if service(s) are modified on write
        if 'service_ids' in vals and 'step_ids' not in vals:
            s_ids = []
            for cmd in vals['service_ids']:
                if isinstance(cmd, (list, tuple)) and len(cmd) == 3:
                    if cmd[0] == 6:
                        s_ids.extend(cmd[2])
                    elif cmd[0] == 4:
                        s_ids.append(cmd[1])
            
            services = self.env['salon.service'].browse(s_ids)
            step_lines = [(5, 0, 0)]
            seq_num = 10
            # Prefer the beauticians being set in this same write; otherwise
            # fall back to what's already stored on the record.
            if 'staff_ids' in vals:
                staff_id_list = []
                for cmd in vals['staff_ids']:
                    if isinstance(cmd, int):
                        staff_id_list.append(cmd)
                    elif isinstance(cmd, (list, tuple)) and cmd[0] == 6 and cmd[2]:
                        staff_id_list.extend(cmd[2])
                    elif isinstance(cmd, (list, tuple)) and cmd[0] == 4:
                        staff_id_list.append(cmd[1])
                staff_pool = self.env['salon.staff'].browse(list(dict.fromkeys(staff_id_list)))
            else:
                staff_pool = self[0].staff_ids if self else self.env['salon.staff']
            primary_staff = self.env['salon.staff'].browse(
                vals.get('staff_id') or (self and self[0].staff_id.id) or (staff_pool[:1].id)
            )
            prev_staff = self.env['salon.staff']
            for service in services:
                if service.step_ids:
                    for step in service.step_ids:
                        assigned_staff = self._pick_staff_for_service(
                            staff_pool, step.source_service_id or service, primary_staff
                        ) if step.need_staff else self.env['salon.staff']
                        timing_mode = 'parallel' if step.run_parallel else self._default_timing_mode(prev_staff, assigned_staff)
                        step_lines.append((0, 0, {
                            'sequence': seq_num,
                            'name': self._step_line_name(service, step),
                            'service_id': service.id,
                            'duration_minutes': step.duration_minutes,
                            'need_staff': step.need_staff,
                            'timing_mode': timing_mode,
                            'staff_id': assigned_staff.id if assigned_staff else False,
                        }))
                        seq_num += 10
                        if step.need_staff:
                            prev_staff = assigned_staff
                else:
                    assigned_staff = self._pick_staff_for_service(staff_pool, service, primary_staff)
                    step_lines.append((0, 0, {
                        'sequence': seq_num,
                        'name': service.name,
                        'service_id': service.id,
                        'duration_minutes': int(service.duration * 60),
                        'need_staff': True,
                        'timing_mode': self._default_timing_mode(prev_staff, assigned_staff),
                        'staff_id': assigned_staff.id if assigned_staff else False,
                    }))
                    seq_num += 10
                    prev_staff = assigned_staff
            vals['step_ids'] = step_lines

        # If staff_id changed, update corresponding steps
        if 'staff_id' in vals and 'step_ids' not in vals:
            new_staff_id = vals['staff_id']
            step_commands = []
            for rec in self:
                for step in rec.step_ids:
                    if step.need_staff and step.staff_id.id == rec.staff_id.id:
                        step_commands.append((1, step.id, {'staff_id': new_staff_id}))
            if step_commands:
                vals['step_ids'] = step_commands

        res = super().write(vals)
        if vals.get('state') == 'confirmed':
            template = self.env.ref('salon_spa_scheduler.email_template_appointment_confirmation', raise_if_not_found=False)
            if template:
                for rec in self:
                    if not rec.confirmation_sent:
                        template.send_mail(rec.id, force_send=False)
                        rec.confirmation_sent = True
        return res

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def _cron_send_30m_reminders(self):
        now = fields.Datetime.now()
        thirty_mins_later = now + timedelta(minutes=30)
        # Search for confirmed appointments starting within 30 minutes where reminder hasn't been sent
        domain = [
            ('state', '=', 'confirmed'),
            ('start_datetime', '>=', now),
            ('start_datetime', '<=', thirty_mins_later),
            ('reminder_sent_30m', '=', False)
        ]
        appointments = self.search(domain)
        template = self.env.ref('salon_spa_scheduler.email_template_appointment_reminder_30m', raise_if_not_found=False)
        if template:
            for appt in appointments:
                template.send_mail(appt.id, force_send=True)
                appt.write({'reminder_sent_30m': True})

    def action_progress(self):
        self.write({'state': 'progress'})

    def action_done(self):
        # Auto product consumption / inventory handling when done
        for rec in self:
            for service in rec.service_ids:
                if service.product_ids:
                    # Trigger automatic consumption logic here if needed
                    pass

            rec._log_sale_history()
            rec._sync_commissions()

        self.write({'state': 'done'})

    def _sync_commissions(self):
        """(Re)build the commissions of these appointments from Sales History.

        The salon's rule: commission is earned on what was actually charged,
        after discounts; when several beauticians work on one booking each
        earns on the lines they did; tips never count. So every service line
        of the booking's history goes to the beautician on that line, and the
        membership discount - which the till books as one negative line for
        the whole order - is spread over the service lines in proportion to
        their price. One commission per beautician per booking.

        Commissions already marked Paid are never touched: that money has gone
        out. Draft ones are replaced, so re-running after the POS order is
        paid (and the history is rewritten from the till) corrects them.
        """
        Commission = self.env['salon.commission']
        History = self.env['salon.customer.history']
        for rec in self:
            existing = Commission.search([('appointment_id', '=', rec.id)])
            if existing.filtered(lambda c: c.state == 'paid'):
                continue
            existing.unlink()
            lines = History.search([('appointment_id', '=', rec.id), ('state', '!=', 'Cancelled')])
            service_lines = lines.filtered(
                lambda l: l.item_type == 'service' and l.staff_id and l.service_id)
            service_total = sum(service_lines.mapped('price_unit'))
            order_discount = sum(lines.filtered(lambda l: l.item_type == 'other').mapped('price_unit'))
            factor = 1.0
            if service_total > 0 and order_discount:
                factor = max(0.0, (service_total + order_discount) / service_total)
            per_staff = {}
            for line in service_lines:
                service = line.service_id
                if service.commission_type == 'fixed':
                    amount = service.commission_value * (line.quantity or 1.0)
                else:
                    amount = line.price_unit * factor * service.commission_value / 100.0
                per_staff[line.staff_id] = per_staff.get(line.staff_id, 0.0) + amount
            currency = rec.company_id.currency_id
            vals_list = [{
                'company_id': rec.company_id.id,
                'staff_id': staff.id,
                'appointment_id': rec.id,
                'commission_amount': currency.round(amount),
                'date': fields.Date.context_today(self),
                'state': 'draft',
            } for staff, amount in per_staff.items() if currency.round(amount)]
            if vals_list:
                Commission.create(vals_list)

    def _log_sale_history(self):
        """(Re)write the Sales History of these appointments.

        Checked out through the Point of Sale: one row per POS line, with what
        was actually charged, discounts, the membership discount and any retail
        added at the till. Not (yet) paid through the POS: one row per service
        at its list price, as before.
        """
        History = self.env['salon.customer.history']
        for rec in self:
            if not rec.partner_id:
                continue
            History.search([('origin', '=', rec.name)]).unlink()
            order = rec.pos_order_id
            if order and order.state in ('paid', 'done', 'invoiced') and order.lines:
                performed = [(service, staff) for service, staff, _p, _s in rec._billable_services()]
                history_vals = [History._appointment_pos_line_vals(rec, line, performed)
                                for line in order.lines]
            else:
                history_vals = [History._appointment_service_vals(rec, service, staff, price)
                                for service, staff, price, _s in rec._billable_services()]
            if history_vals:
                History.create(history_vals)

    def _cancelled_history_vals(self, note):
        """The history row that records a cancellation. Nothing was sold, so
        quantity and money stay at zero; the links say what was cancelled."""
        self.ensure_one()
        services = self.service_ids
        return {
            'company_id': self.company_id.id,
            'partner_id': self.partner_id.id,
            'date': self.start_datetime or fields.Datetime.now(),
            'service_name': ", ".join(services.mapped('name')) or _('Appointment'),
            'staff_name': self.staff_id.name,
            'state': 'Cancelled',
            'notes': note,
            'price_unit': 0.0,
            'origin': self.name,
            'service_id': services.id if len(services) == 1 else False,
            'staff_id': self.staff_id.id,
            'appointment_id': self.id,
            'item_type': 'service',
            'quantity': 0.0,
            'price_gross': 0.0,
            'sale_ref': self.name,
        }

    def action_cancel(self):
        # Records that are actually transitioning into 'cancel' now.
        newly_cancelled = self.filtered(lambda r: r.state != 'cancel')
        self.write({'state': 'cancel'})

        History = self.env['salon.customer.history']
        for rec in newly_cancelled:
            if not rec.partner_id:
                continue
            # Refresh any earlier cancellation log for this appointment so a
            # reset-to-draft then re-cancel does not stack duplicates.
            History.search([('origin', '=', rec.name), ('state', '=', 'Cancelled')]).unlink()
            when = fields.Datetime.context_timestamp(rec, fields.Datetime.now()).strftime('%Y-%m-%d %H:%M')
            note = _('Cancelled on %(when)s by %(user)s.', when=when, user=self.env.user.name)
            if rec.note:
                note = "%s\n%s" % (note, rec.note)
            History.create(rec._cancelled_history_vals(note))

        for rec in self:
            if rec.partner_id:
                cancel_count = self.env['salon.appointment'].search_count([
                    ('partner_id', '=', rec.partner_id.id),
                    ('state', '=', 'cancel'),
                ])
                limit = rec.company_id.salon_max_cancellations
                if limit > 0 and cancel_count >= limit:
                    rec._send_cancellation_limit_email(cancel_count, limit)

    def action_reset_draft(self):
        if self.filtered(lambda r: r.state == 'cancel') and not (
                self.env.user.has_group('salon_spa_scheduler.group_salon_manager')
                and all(r.company_id.salon_allow_reset_cancelled for r in self)):
            raise AccessError(_(
                "Only Salon Managers can reset a cancelled appointment to Draft, "
                "and only when enabled in Salon & Spa settings."))
        # Drop the cancellation log entry - the appointment is live again.
        for rec in self:
            self.env['salon.customer.history'].search([
                ('origin', '=', rec.name), ('state', '=', 'Cancelled'),
            ]).unlink()
        self.write({'state': 'draft'})

    def _service_staff(self, service):
        """The beautician who performs ``service`` on this booking: the first
        Beauticians & Services line of that service with a beautician on it,
        else the main beautician. Sales History, commissions and the POS
        lines credit this person."""
        self.ensure_one()
        step = self.step_ids.filtered(
            lambda s: s.service_id == service and s.staff_id
        ).sorted(lambda s: (s.sequence, s.id))[:1]
        return step.staff_id or self.staff_id

    def _pos_service_line_commands(self, service, price, session, required=True, staff=None):
        """POS order line commands for one service at ``price``.

        One line per linked POS product: a single product carries the whole
        price, several fall back to their own list price. Taxes follow the
        session's fiscal position. Used by checkout and by Add Service, so an
        added service is priced exactly as if it had been booked from the
        start.
        """
        self.ensure_one()
        if not service.product_ids:
            if required:
                raise ValidationError(_(
                    "The selected service '%s' does not have any linked POS products.") % service.name)
            return []
        fpos = session.config_id.default_fiscal_position_id
        commands = []
        for product in service.product_ids:
            unit = price if len(service.product_ids) == 1 else (product.list_price or price)
            tax_ids = product.taxes_id.filtered(lambda t: t.company_id == session.company_id)
            taxes = fpos.map_tax(tax_ids) if fpos else tax_ids
            comp = taxes.compute_all(
                unit, currency=session.currency_id, quantity=1.0,
                product=product, partner=self.partner_id)
            vals = {
                'product_id': product.id,
                'qty': 1,
                'price_unit': unit,
                'price_subtotal': comp['total_excluded'],
                'price_subtotal_incl': comp['total_included'],
                'tax_ids': [(6, 0, tax_ids.ids)],
                'full_product_name': product.display_name,
            }
            # "Beautician on POS Lines" (POS settings): who does the service,
            # shown under the line at the till and on the receipt.
            if staff and session.config_id.salon_show_beautician:
                vals['salon_beautician_id'] = staff.id
                vals['salon_beautician_name'] = staff.name
            commands.append((0, 0, vals))
        return commands

    def _pos_membership_line_command(self, line_commands, session):
        """The membership discount line for these service lines, or None.

        One separate last line named after the plan, once the services reach
        the plan's minimum spend.
        """
        self.ensure_one()
        plan = self.env['salon.membership.line']._get_member_offer(
            self.partner_id.id, self.company_id.id)
        disc_product = self.env.ref(
            'salon_spa_scheduler.product_product_membership_discount', raise_if_not_found=False)
        if not plan or not disc_product:
            return None
        total = sum(vals['price_unit'] * vals['qty'] for _c, _i, vals in line_commands)
        if total <= 0 or total < plan.min_spend:
            return None
        amount = session.currency_id.round(total * plan.discount_percentage / 100.0)
        tax_sets = {tuple(vals['tax_ids'][0][2]) for _c, _i, vals in line_commands}
        disc_tax_ids = list(tax_sets.pop()) if len(tax_sets) == 1 else []
        disc_taxes = self.env['account.tax'].browse(disc_tax_ids)
        disc_fpos = session.config_id.default_fiscal_position_id
        if disc_fpos:
            disc_taxes = disc_fpos.map_tax(disc_taxes)
        comp = disc_taxes.compute_all(
            -amount, currency=session.currency_id, quantity=1.0,
            product=disc_product, partner=self.partner_id)
        return (0, 0, {
            'product_id': disc_product.id,
            'qty': 1,
            'price_unit': -amount,
            'price_subtotal': comp['total_excluded'],
            'price_subtotal_incl': comp['total_included'],
            'tax_ids': [(6, 0, disc_tax_ids)],
            'full_product_name': plan.name,
        })

    def action_send_to_pos(self):
        """Form's Send to POS: open the booking's unpaid POS order at the till
        (adding the services missing from it), or create one."""
        self.ensure_one()
        order = self.pos_order_id
        if order and order.state == 'draft':
            if not self.env.user.has_group('salon_spa_scheduler.group_salon_create_payment') \
                    and not self.env.user.has_group('salon_spa_scheduler.group_salon_manager'):
                raise AccessError(_("You do not have permission to send orders to Point of Sale."))
            if order.session_id.state != 'opened':
                raise UserError(_(
                    "The POS session of order %s is closed. Open a Point of Sale "
                    "session first.", order.name))
            self._sync_pos_order_services()
            return {
                'type': 'ir.actions.act_url',
                'url': '/pos/ui/%d/product/%s' % (order.session_id.config_id.id, order.uuid),
                'target': 'self',
            }
        if order and order.state != 'cancel':
            raise UserError(_("%s has already been paid at the Point of Sale.", self.name))
        return self.action_create_pos_order()

    def action_create_pos_order(self):
        if not self.env.user.has_group('salon_spa_scheduler.group_salon_create_payment') and not self.env.user.has_group('salon_spa_scheduler.group_salon_manager'):
            raise AccessError(_("You do not have permission to send orders to Point of Sale."))
        for rec in self:
            if not rec.service_ids:
                raise ValidationError(_("No services selected on the appointment."))
            # Only consider sessions of the appointment's company so the POS order,
            # its taxes and its journal entries stay within the right company.
            company_domain = [('company_id', '=', rec.company_id.id)]
            # Find the opened session of the current user, or fallback to the first opened session
            session = self.env['pos.session'].search([
                ('state', '=', 'opened'),
                ('user_id', '=', self.env.user.id),
            ] + company_domain, limit=1)
            if not session:
                session = self.env['pos.session'].search(
                    [('state', '=', 'opened')] + company_domain, limit=1)

            if not session:
                raise ValidationError(_(
                    "Please open a Point of Sale session for %s first.", rec.company_id.display_name))
            
            # One POS line per service done, as the Beauticians & Services
            # table has it (see _billable_services); an Additional Services
            # line keeps its own price.
            lines = []
            for service, staff, price, source in rec._billable_services():
                lines += rec._pos_service_line_commands(
                    service, price, session, required=source != 'line', staff=staff)
            membership = rec._pos_membership_line_command(lines, session)
            if membership:
                lines.append(membership)

            order = self.env['pos.order'].create({
                'session_id': session.id,
                'partner_id': rec.partner_id.id,
                'lines': lines,
                'amount_tax': 0.0,
                'amount_total': 0.0,
                'amount_paid': 0.0,
                'amount_return': 0.0,
            })
            order._compute_prices()
            rec.pos_order_id = order.id

            # Return the redirection action to the Point of Sale screen with the order UUID
            return {
                'type': 'ir.actions.act_url',
                'url': '/pos/ui/%d/product/%s' % (session.config_id.id, order.uuid),
                'target': 'self',
            }

    @api.model
    def scheduler_data(self, date_str=False):
        day = fields.Date.from_string(date_str) if date_str else fields.Date.context_today(self)
        company = self.env.company
        start_hour = company.salon_start_hour or 8
        end_hour = company.salon_end_hour or 22
        if not (0 <= start_hour <= 23):
            start_hour = 8
        if not (0 <= end_hour <= 23):
            end_hour = 22
        if start_hour >= end_hour:
            start_hour, end_hour = 8, 22

        tz_name = self.env.context.get('tz') or self.env.user.tz or 'UTC'
        user_tz = pytz.timezone(tz_name)
        local_start = user_tz.localize(datetime.combine(day, time(start_hour, 0)))
        local_end = user_tz.localize(datetime.combine(day, time(end_hour, 0)))
        start = local_start.astimezone(pytz.utc).replace(tzinfo=None)
        end = local_end.astimezone(pytz.utc).replace(tzinfo=None)
        staff = self.env['salon.staff'].search([('active', '=', True)], order='sequence, name')

        # Planning shifts for the shown day. A beautician linked to an employee is
        # governed by their published planning.slot records: the column shows the
        # shift hours, slots outside every shift are greyed AND refuse bookings
        # (enforced server-side in _check_overlap). Staff with no linked employee
        # are unrestricted.
        local_day_start = user_tz.localize(datetime.combine(day, time.min))
        day_start = local_day_start.astimezone(pytz.utc).replace(tzinfo=None)
        day_end = (local_day_start + timedelta(days=1)).astimezone(pytz.utc).replace(tzinfo=None)
        shifts_by_employee = {}
        employee_ids = staff.employee_id.ids
        if employee_ids:
            slots = self.env['planning.slot'].sudo().search([
                ('employee_id', 'in', employee_ids),
                ('company_id', 'in', self.env.companies.ids),
                ('state', '=', 'published'),
                ('start_datetime', '<', day_end),
                ('end_datetime', '>', day_start),
            ], order='start_datetime')
            for slot in slots:
                shifts_by_employee.setdefault(slot.employee_id.id, []).append(slot)

        def _fmt_local(dt):
            return fields.Datetime.context_timestamp(self, dt).strftime('%H:%M')

        # Cancelled appointments stay on the scheduler (rendered red) so staff can
        # still see the slot history; they just no longer block new bookings.
        # The search window is the full local calendar day (day_start/day_end),
        # not the narrower company-hours window (start/end): a booking made
        # outside business hours must still show up instead of silently
        # vanishing from the board.
        appointments = self.search([
            ('start_datetime', '<', day_end),
            ('end_datetime', '>', day_start),
        ])
        appointments_list = []
        # Distinct (non-cancelled) appointments each beautician is involved in on
        # this day - shown as a count badge on the staff column headers.
        staff_appt_ids = {}
        for a in appointments:
            if a.state != 'cancel':
                if a.step_ids:
                    involved = a.step_ids.filtered(lambda s: s.need_staff and s.staff_id).mapped('staff_id')
                else:
                    involved = a.staff_ids or a.staff_id
                for bs in involved:
                    staff_appt_ids.setdefault(bs.id, set()).add(a.id)
        for a in appointments:
            general_notes = a.partner_id._salon_general_notes_text() if a.partner_id else ""
            if a.step_ids:
                curr_time = a.start_datetime or start
                for step in a.step_ids.sorted('sequence'):
                    step_start = step.start_datetime or curr_time
                    step_end = step.end_datetime or (step_start + timedelta(minutes=step.duration_minutes or 30))
                    curr_time = step_end
                    if step.need_staff and step.staff_id:
                        appointments_list.append({
                            'id': f"{a.id}_{step.id}",
                            'appointment_id': a.id,
                            'name': f"{a.name} ({step.name})",
                            'customer': a.partner_id.name,
                            'phone': a.phone or '',
                            'staff_required': step.staff_required,
                            'note': a.note or '',
                            # This beautician's own note on the line.
                            'step_id': step.id,
                            'step_note': step.note or '',
                            'general_notes': general_notes,
                            'has_general_notes': bool(general_notes),
                            'staff_id': step.staff_id.id,
                            'branch_id': a.branch_id.id,
                            'service': step.name,
                            'start': fields.Datetime.to_string(step_start) if step_start else "",
                            'end': fields.Datetime.to_string(step_end) if step_end else "",
                            'duration': step.duration_minutes / 60.0,
                            'state': a.state,
                            'is_arrived': a.is_arrived,
                            'payment_state': a.payment_state,
                            'amount': a.amount_subtotal,
                            'can_checkout': a._scheduler_checkout_available(),
                        'can_add_service': a.can_add_service,
                            'can_add_service': a.can_add_service,
                            'color': a.color,
                        })
            else:
                a_start = a.start_datetime or start
                a_end = a.end_datetime or (a_start + timedelta(hours=a.duration or 1.0))
                # Render the block under every assigned beautician
                block_staff = a.staff_ids or a.staff_id
                for bs in block_staff:
                    appointments_list.append({
                        'id': f"{a.id}_s{bs.id}" if len(block_staff) > 1 else str(a.id),
                        'appointment_id': a.id,
                        'name': a.name,
                        'customer': a.partner_id.name,
                        'phone': a.phone or '',
                        'staff_required': a.staff_required,
                        'note': a.note or '',
                        'general_notes': general_notes,
                        'has_general_notes': bool(general_notes),
                        'staff_id': bs.id,
                        'branch_id': a.branch_id.id,
                        'service': ", ".join(a.service_ids.mapped('name')),
                        'start': fields.Datetime.to_string(a_start) if a_start else "",
                        'end': fields.Datetime.to_string(a_end) if a_end else "",
                        'duration': a.duration,
                        'state': a.state,
                        'is_arrived': a.is_arrived,
                        'payment_state': a.payment_state,
                        'amount': a.amount_subtotal,
                        'can_checkout': a._scheduler_checkout_available(),
                        'can_add_service': a.can_add_service,
                        'color': a.color,
                    })

        # Business hours only set the *default* grid range; a booking outside
        # them (see the day-wide search above) still needs a row to render
        # in, so widen start_hour/end_hour to cover it rather than clipping
        # it off the board.
        for a in appointments:
            if a.state == 'cancel' or not a.start_datetime or not a.end_datetime:
                continue
            a_start_local = fields.Datetime.context_timestamp(self, a.start_datetime)
            a_end_local = fields.Datetime.context_timestamp(self, a.end_datetime)
            if a_start_local.date() == day:
                start_hour = min(start_hour, a_start_local.hour)
            if a_end_local.date() > day:
                # Runs past local midnight: the JS grid can't render an
                # "hour 24" row, so just extend to the last row of the day.
                end_hour = 23
            elif a_end_local.date() == day:
                extra = 1 if (a_end_local.minute or a_end_local.second) else 0
                end_hour = max(end_hour, min(a_end_local.hour + extra, 23))
        start_hour = max(0, min(start_hour, 23))
        end_hour = max(start_hour + 1, min(end_hour, 23))

        return {
            'date': fields.Date.to_string(day),
            'user_can_checkout': self._user_can_checkout(),
            'start_hour': start_hour,
            'end_hour': end_hour,
            'slot_minutes': 15,
            'staff': [{
                'id': s.id,
                'name': s.name,
                # The branch the beautician works for - the board shows only the
                # selected branch's columns and books new work there.
                'company_id': s.company_id.id,
                'color': s.color,
                'appt_count': len(staff_appt_ids.get(s.id, ())),
                # planning_gated: bookings are limited to shift_ranges (naive-UTC
                # "YYYY-MM-DD HH:MM:SS" pairs, same format as slot.datetime).
                'planning_gated': bool(s.employee_id),
                'on_shift': (not s.employee_id) or bool(shifts_by_employee.get(s.employee_id.id)),
                'shift_hint': ", ".join(
                    "%s-%s" % (_fmt_local(sl.start_datetime), _fmt_local(sl.end_datetime))
                    for sl in shifts_by_employee.get(s.employee_id.id, [])
                ),
                'shift_ranges': [
                    [fields.Datetime.to_string(sl.start_datetime), fields.Datetime.to_string(sl.end_datetime)]
                    for sl in shifts_by_employee.get(s.employee_id.id, [])
                ],
            } for s in staff],
            'branches': [{'id': b.id, 'name': b.name} for b in self.env.companies],
            'appointments': appointments_list + self._scheduler_block_entries(day_start, day_end),
            'services': [{'id': s.id, 'name': s.name, 'duration': s.duration} for s in self.env['salon.service'].search([('active', '=', True)])],
            'block_types': [
                {'id': bt.id, 'name': bt.name, 'color': bt.color,
                 'duration': bt.default_duration_minutes,
                 'category': bt.category}
                for bt in self.env['salon.block.type'].search([])
            ],
        }

    @api.model
    def _scheduler_block_entries(self, day_start, day_end):
        """The day's time blocks, shaped like board cards.

        Training, a staff meeting, a day on duty at another branch, a stretch
        marked "do not book" - the chair is taken and there is no customer
        behind it. They ride in the same list the timeline already renders and
        carry every key an appointment card carries, so the template needs no
        special case; `is_block` is what tells the click and drag handlers to
        open salon.block instead of a booking.
        """
        blocks = self.env['salon.block'].search([
            ('start_datetime', '<', day_end),
            ('end_datetime', '>', day_start),
            ('state', '!=', 'cancel'),
            ('staff_id', '!=', False),
        ])
        entries = []
        for block in blocks:
            label = block.name or block.block_type_id.name
            if block.works_at_branch_id:
                label = "%s @ %s" % (label, block.works_at_branch_id.name)
            entries.append({
                'id': "b%s" % block.id,
                'is_block': True,
                'block_id': block.id,
                'block_type': block.block_type_id.name,
                'works_at': block.works_at_branch_id.name or '',
                'blocks_booking': block.block_type_id.blocks_booking,
                'appointment_id': False,
                'name': label,
                'customer': block.block_type_id.name,
                'phone': '',
                'staff_required': False,
                'note': block.note or '',
                'general_notes': '',
                'has_general_notes': False,
                'staff_id': block.staff_id.id,
                'branch_id': (block.branch_id or block.company_id).id,
                'service': block.block_type_id.name,
                'start': fields.Datetime.to_string(block.start_datetime),
                'end': fields.Datetime.to_string(block.end_datetime),
                'duration': block.duration_hours,
                'state': block.state,
                'is_arrived': False,
                'payment_state': 'not_paid',
                'amount': 0.0,
                'can_checkout': False,
                'color': block.color or 1,
            })
        return entries

    @api.model
    def scheduler_move_block(self, block_id, staff_id, start_datetime):
        """Drag a time block to another beautician or time slot."""
        block = self.env['salon.block'].browse(int(block_id))
        block.ensure_one()
        start = fields.Datetime.from_string(start_datetime)
        block.write({
            'staff_id': int(staff_id),
            'start_datetime': start,
            'end_datetime': start + timedelta(minutes=block.duration_minutes or 60),
        })
        return True

    @api.model
    def scheduler_resize_block(self, block_id, duration_hours):
        """Drag a time block's bottom edge on the board."""
        block = self.env['salon.block'].browse(int(block_id))
        block.ensure_one()
        minutes = max(15, int(round(float(duration_hours) * 60)))
        block.write({
            'duration_minutes': minutes,
            'end_datetime': block.start_datetime + timedelta(minutes=minutes),
        })
        return True

    @api.model
    def scheduler_cancel_block(self, block_id):
        """Take a block off the board, straight from its popup."""
        block = self.env['salon.block'].browse(int(block_id))
        block.ensure_one()
        block.action_cancel()
        return True

    @api.model
    def scheduler_quick_create(self, vals):
        partner_name = vals.get('customer_name')
        partner = self.env['res.partner'].search([('name', '=', partner_name)], limit=1)
        if not partner:
            partner = self.env['res.partner'].create({'name': partner_name, 'phone': vals.get('phone')})
        service = self.env['salon.service'].browse(int(vals['service_id']))
        start_dt = fields.Datetime.from_string(vals['start_datetime'])
        end_dt = start_dt + timedelta(hours=service.duration)
        
        # Branch defaults to the acting company when not specified.
        branch = self.env.company

        appt = self.create({
            'partner_id': partner.id,
            'phone': vals.get('phone'),
            'staff_id': int(vals['staff_id']),
            'service_ids': [(6, 0, [service.id])],
            'start_datetime': start_dt,
            'end_datetime': end_dt,
            'branch_id': branch.id,
            'state': 'confirmed',
        })
        return appt.id

    @api.model
    def scheduler_mark_arrived(self, appointment_id):
        if '_' in str(appointment_id):
            appt_id = int(str(appointment_id).split('_')[0])
        else:
            appt_id = int(appointment_id)
        appt = self.browse(appt_id).exists()
        if appt:
            # Arrival follows confirmation: the board offers Confirm first.
            if appt.state == 'draft':
                raise UserError(_("Confirm %s before marking the customer as arrived.", appt.name))
            appt.write({'is_arrived': True})
        return True

    @api.model
    def scheduler_set_step_note(self, step_id, note):
        """Note on one Beauticians & Services line, typed in the scheduler
        popup - for that beautician only."""
        step = self.env['salon.appointment.step'].browse(int(step_id)).exists()
        if not step:
            raise UserError(_("This line no longer exists."))
        if step.appointment_id.state in ('done', 'cancel'):
            raise UserError(_("%s is finished; its notes can no longer be changed.",
                              step.appointment_id.name))
        step.write({'note': (note or '').strip() or False})
        return True

    @api.model
    def scheduler_set_note(self, appointment_id, note):
        """Booking note typed in the scheduler popup (the note behind the
        note icon on the booking card)."""
        appt = self.browse(int(str(appointment_id).split('_')[0])).exists()
        if not appt:
            raise UserError(_("This appointment no longer exists."))
        if appt.state in ('done', 'cancel'):
            raise UserError(_("%s is finished; its note can no longer be changed.", appt.name))
        appt.write({'note': (note or '').strip() or False})
        return True

    @api.model
    def scheduler_complete(self, appointment_id):
        """Board Completed: the work is finished and the booking is Done -
        paid now with Checkout or on a later visit. A Done booking takes no
        more services."""
        appt = self.browse(int(str(appointment_id).split('_')[0])).exists()
        if not appt:
            raise UserError(_("This appointment no longer exists."))
        if appt.state != 'progress':
            raise UserError(_("%s can be marked Completed once it is In Progress.", appt.name))
        appt.action_done()
        return True

    @api.model
    def scheduler_start_service(self, appointment_id):
        """Board Start Service: a confirmed booking whose customer has
        arrived goes In Progress, which is what makes Checkout available."""
        appt = self.browse(int(str(appointment_id).split('_')[0])).exists()
        if not appt:
            raise UserError(_("This appointment no longer exists."))
        if appt.state != 'confirmed' or not appt.is_arrived:
            raise UserError(_("%s can be started once it is confirmed and the customer "
                              "has arrived.", appt.name))
        appt.action_progress()
        return True

    @api.model
    def scheduler_confirm(self, appointment_id):
        appt = self.browse(int(str(appointment_id).split('_')[0])).exists()
        if appt and appt.state == 'draft':
            appt.action_confirm()
        return True

    @api.model
    def _user_can_checkout(self):
        user = self.env.user
        return user.has_group('salon_spa_scheduler.group_salon_create_payment') \
            or user.has_group('salon_spa_scheduler.group_salon_manager')

    def _scheduler_checkout_available(self):
        """Whether the board's Checkout button applies: a confirmed / in-progress
        booking (or a Done one when the company allows finishing unpaid) that
        is not paid yet and has no POS order - or only a still-draft one, which
        Checkout then reopens. Only once the work is finished (Completed puts
        it in Done): Confirm -> Mark Arrived -> Start -> Completed -> Checkout,
        now or on a later visit."""
        self.ensure_one()
        if self.payment_state == 'paid':
            return False
        if self.pos_order_id and self.pos_order_id.state != 'draft':
            return False
        return self.state == 'done'

    # ------------------------------------------------------------------
    # Extending a started appointment
    # ------------------------------------------------------------------
    @api.depends('state', 'pos_order_id', 'pos_order_id.state', 'company_id.salon_allow_extend_started')
    def _compute_can_add_service(self):
        # A draft booking can always take another service; a confirmed or
        # started one when the company allows extending them.
        for rec in self:
            rec.can_add_service = (
                (rec.state == 'draft'
                 or (rec.state in ('confirmed', 'progress') and rec.company_id.salon_allow_extend_started))
                and (not rec.pos_order_id or rec.pos_order_id.state == 'draft'))

    def _check_can_add_service(self):
        self.ensure_one()
        if self.state not in ('draft', 'confirmed', 'progress'):
            raise UserError(_("Only a draft, confirmed or in-progress appointment can be extended."))
        if self.state != 'draft' and not self.company_id.salon_allow_extend_started:
            raise UserError(_(
                "Adding services to a started appointment is switched off. "
                "Turn on \"Add Services to Started Appointments\" in Salon settings."))
        order = self.pos_order_id
        if order and order.state != 'draft':
            raise UserError(_(
                "%s has already been paid at the Point of Sale. Add the service "
                "there as a new sale.", self.name))
        if order and order.session_id.state != 'opened':
            raise UserError(_(
                "The POS session of order %s is closed. Open a Point of Sale "
                "session first.", order.name))

    def action_open_add_service(self):
        self.ensure_one()
        self._check_can_add_service()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Add Service'),
            'res_model': 'salon.appointment.add.service',
            'view_mode': 'form',
            # Spelled out: the scheduler hands this straight to doAction,
            # which - unlike a form button - does not derive it from view_mode.
            'views': [(False, 'form')],
            'target': 'new',
            'context': {'default_appointment_id': self.id},
        }

    @api.model
    def scheduler_open_add_service(self, appointment_id):
        """Board popup: the same Add Service dialog as the form."""
        appt = self.browse(int(str(appointment_id).split('_')[0])).exists()
        if not appt:
            raise UserError(_("This appointment no longer exists."))
        return appt.action_open_add_service()

    def _add_extra_service(self, service, staff, minutes, timing_mode='sequential'):
        """Extend a started appointment with one more service.

        Billing and time are kept apart, the same way the booking form keeps
        them: an Additional Services line is what checkout charges, and new
        steps at the end of the step list are what extend the booking on the
        scheduler. Existing steps are left exactly as they are - rewriting
        service_ids would rebuild them and lose times already under way. The
        usual overlap and block checks still decide whether the beautician is
        free.
        """
        self.ensure_one()
        self._check_can_add_service()
        last_seq = max(self.step_ids.mapped('sequence') or [0])
        steps = []
        if service.step_ids:
            template = service.step_ids.sorted('sequence')
            scale = (minutes / sum(template.mapped('duration_minutes'))
                     if minutes and sum(template.mapped('duration_minutes')) else 1.0)
            for idx, step in enumerate(template):
                if idx == 0:
                    mode = timing_mode
                else:
                    mode = 'parallel' if step.run_parallel else 'sequential'
                steps.append({
                    'name': self._step_line_name(service, step),
                    'service_id': service.id,
                    'duration_minutes': max(5, int(round(step.duration_minutes * scale))),
                    'need_staff': step.need_staff,
                    'is_processing_break': step.is_processing_break,
                    'timing_mode': mode,
                    'staff_id': staff.id if step.need_staff else False,
                })
        else:
            steps.append({
                'name': service.name,
                'service_id': service.id,
                'duration_minutes': minutes or int(round(service.duration * 60)) or 30,
                'need_staff': True,
                'timing_mode': timing_mode,
                'staff_id': staff.id,
            })
        commands = []
        for offset, vals in enumerate(steps, start=1):
            vals['sequence'] = last_seq + 10 * offset
            commands.append((0, 0, vals))
        write_vals = {
            'step_ids': commands,
            'line_ids': [(0, 0, {'service_id': service.id, 'staff_id': staff.id})],
            # A fixed total length would squeeze the new step into the old
            # end time; the steps decide the length from here on.
            'duration_selection': False,
        }
        if staff and staff not in self.staff_ids:
            write_vals['staff_ids'] = [(4, staff.id)]
        self.write(write_vals)
        # The new end time is recomputed rather than written, which does not
        # reliably fire the constraints - run them here. A clash raises and
        # rolls the whole addition back.
        self._check_overlap()
        self._check_salon_block_clash()
        if self.pos_order_id:
            self._add_service_to_pos_order(service)
        end = (fields.Datetime.context_timestamp(self, self.end_datetime).strftime('%H:%M')
               if self.end_datetime else "-")
        self.message_post(body=_(
            "Service added: %(service)s with %(staff)s. The appointment now ends at %(end)s.",
            service=service.name, staff=staff.name or "-", end=end))
        return True

    def _add_service_to_pos_order(self, service):
        """Put a service added after checkout onto the booking's unpaid POS
        order, priced as checkout would, and recompute the membership
        discount for the new total of services."""
        self.ensure_one()
        order = self.pos_order_id
        session = order.session_id
        added = self.line_ids.filtered(lambda l: l.service_id == service)[-1:]
        new_lines = self._pos_service_line_commands(
            service, service.list_price, session, required=False,
            staff=added.staff_id or self._service_staff(service))
        if not new_lines:
            self.message_post(body=_(
                "%s has no POS product, so it could not be added to order %s - "
                "charge it at the till.", service.name, order.name))
            return
        self._add_pos_service_lines(new_lines)
        self.message_post(body=_(
            "%(service)s added to POS order %(order)s. If the order is open at "
            "the till, reopen it there to see the new line.",
            service=service.name, order=order.name))

    def _add_pos_service_lines(self, new_lines):
        """Write service lines onto the booking's unpaid POS order and redo
        the membership discount for the new total of services."""
        self.ensure_one()
        order = self.pos_order_id
        session = order.session_id
        disc_product = self.env.ref(
            'salon_spa_scheduler.product_product_membership_discount', raise_if_not_found=False)
        old_discount = order.lines.filtered(lambda l: disc_product and l.product_id == disc_product)
        # The membership discount applies to the booking's services, as at checkout.
        service_products = self.env['salon.service'].union(
            *[s for s, _st, _p, _k in self._billable_services()]).product_ids
        base = [(0, 0, {'price_unit': l.price_unit, 'qty': l.qty,
                        'tax_ids': [(6, 0, l.tax_ids.ids)]})
                for l in order.lines - old_discount if l.product_id in service_products]
        commands = [(2, l.id) for l in old_discount] + new_lines
        discount = self._pos_membership_line_command(base + new_lines, session)
        if discount:
            commands.append(discount)
        order.write({'lines': commands})
        order._compute_prices()

    def _absorb_pos_services(self, order):
        """Services charged on the booking's POS order that the booking does
        not have - added at the till - are written back into the booking: an
        Additional Services line (charged price, the line's beautician) and a
        line at the end of Beauticians & Services. The work is done and paid,
        so shift and overlap checks do not apply."""
        self.ensure_one()
        Service = self.env['salon.service'].sudo()
        covered = Counter()
        for service, _staff, _price, _source in self._billable_services():
            covered[service.product_ids[:1].id] += 1
        added = []
        for line in order.lines.filtered(lambda l: l.qty > 0):
            service = Service.search([('product_ids', 'in', line.product_id.id),
                                      ('company_id', '=', self.company_id.id)], limit=1)
            # A service sold as several products is one service: count its first.
            if not service or service.product_ids[:1] != line.product_id:
                continue
            if covered[line.product_id.id]:
                covered[line.product_id.id] -= 1
                continue
            added.append((service, line.salon_beautician_id or self.staff_id, line.price_unit))
        if not added:
            return
        last_seq = max(self.step_ids.mapped('sequence') or [0])
        steps, lines = [], []
        for offset, (service, staff, price) in enumerate(added, start=1):
            lines.append((0, 0, {'service_id': service.id, 'staff_id': staff.id, 'price_unit': price}))
            steps.append((0, 0, {
                'sequence': last_seq + 10 * offset,
                'name': service.name,
                'service_id': service.id,
                'staff_id': staff.id,
                'duration_minutes': int(round(service.duration * 60)) or 30,
                'need_staff': True,
                'timing_mode': 'sequential',
            }))
        unchecked = self.with_context(skip_salon_overlap_check=True, skip_salon_block_overlap=True,
                                      skip_working_hours_check=True)
        unchecked.write({'line_ids': lines, 'step_ids': steps, 'duration_selection': False})
        # The checks run when the new times are computed, at flush: flush here,
        # still without them.
        unchecked.env.flush_all()
        self.message_post(body=_(
            "Added at the till and charged on %(order)s: %(services)s.",
            order=order.name,
            services=", ".join("%s (%s)" % (s.name, st.name or "-") for s, st, _p in added)))

    def _absorb_pos_services_safe(self, order):
        """_absorb_pos_services that never stops the payment going through."""
        for appt in self:
            try:
                with self.env.cr.savepoint():
                    appt._absorb_pos_services(order)
            except Exception as exc:  # noqa: BLE001 - the till must not fail
                _logger.warning("Could not write POS services back into %s: %s", appt.name, exc)
                appt.message_post(body=_(
                    "Services added at the till on %(order)s could not be written back "
                    "into this booking: %(error)s", order=order.name, error=exc))

    def _sync_pos_order_services(self):
        """Checkout of a booking whose unpaid POS order is reopened: add the
        services done since (or missing from it), one line each, with their
        beautician. Lines already on the order - and anything the till added -
        stay as they are."""
        self.ensure_one()
        order = self.pos_order_id
        if not order or order.state != 'draft':
            return
        have = Counter()
        for line in order.lines.filtered(lambda l: l.qty > 0):
            have[line.product_id.id] += 1
        missing = []
        for service, staff, price, source in self._billable_services():
            for command in self._pos_service_line_commands(
                    service, price, order.session_id, required=False, staff=staff):
                product_id = command[2]['product_id']
                if have[product_id]:
                    have[product_id] -= 1
                else:
                    missing.append(command)
        if missing:
            self._add_pos_service_lines(missing)

    @api.model
    def scheduler_checkout(self, appointment_id):
        """Board Checkout: send the booking to the Point of Sale (same as the
        form's Send to POS) and open it there. A Confirmed booking is moved to
        In Progress first, so paying the POS order completes it. If the booking
        already has an unpaid POS order, that order is reopened instead of
        creating a second one."""
        appt = self.browse(int(str(appointment_id).split('_')[0])).exists()
        if not appt:
            raise UserError(_("This appointment no longer exists."))
        if not self._user_can_checkout():
            raise AccessError(_("You do not have permission to send orders to Point of Sale."))
        if not appt._scheduler_checkout_available():
            raise UserError(_(
                "This appointment can't be checked out yet: mark it Completed once "
                "the work is finished (it must be Done and not paid)."))
        order = appt.pos_order_id
        if order:
            if order.session_id.state != 'opened':
                raise UserError(_(
                    "The POS session of order %s is closed. Open a Point of Sale "
                    "session first.", order.name))
            appt._sync_pos_order_services()
            return {
                'type': 'ir.actions.act_url',
                'url': '/pos/ui/%d/product/%s' % (order.session_id.config_id.id, order.uuid),
                'target': 'self',
            }
        if appt.state == 'confirmed':
            appt.action_progress()
        return appt.action_create_pos_order()

    def action_rebook(self):
        """Open a fresh appointment form pre-filled from this one (same customer,
        services, beauticians, branch, chair, notes). The manager just picks the
        new time. Nothing is written until they save."""
        self.ensure_one()
        ctx = dict(self.env.context)
        ctx.update({
            'default_partner_id': self.partner_id.id,
            'default_branch_id': self.branch_id.id or False,
            'default_service_ids': [(6, 0, self.service_ids.ids)],
            'default_staff_ids': [(6, 0, self.staff_ids.ids)],
            'default_staff_id': self.staff_id.id or False,
            'default_room_id': self.room_id.id or False,
            'default_note': self.note or False,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Rebook - %s', self.partner_id.name),
            'res_model': 'salon.appointment',
            'view_mode': 'form',
            'views': [[False, 'form']],
            'target': 'current',
            'context': ctx,
        }

    @api.model
    def scheduler_rebook(self, appointment_id):
        """Board entry point for :meth:`action_rebook` - accepts the scheduler's
        composite ``<appt>_s<staff>`` block ids."""
        appt_id = int(str(appointment_id).split('_')[0])
        orig = self.browse(appt_id).exists()
        if not orig:
            raise UserError(_("This appointment no longer exists."))
        return orig.action_rebook()

    def _check_board_editable(self):
        """A Done booking moves on the board only as its lines can be edited
        on the form: unpaid, by a Salon manager, "Edit Bookings After Start" on."""
        self.env['salon.appointment.step']._check_done_editable(self)

    @contextmanager
    def _resync_done_after(self):
        """Moved or resized while Done: its Sales History follows (date,
        beautician), as after an edit of its lines."""
        yield
        if self.state == 'done':
            self.env['salon.appointment.step']._resync_done(self)

    @api.model
    def scheduler_move(self, appointment_id, staff_id, start_datetime):
        step_id = None
        parts = str(appointment_id).split('_')
        appt_id = int(parts[0])
        if len(parts) > 1 and parts[1].isdigit():
            step_id = int(parts[1])

        appt = self.browse(appt_id).exists()
        if not appt:
            return False
        appt._check_board_editable()
        # A drag on the board is an explicit manager decision - don't hard-block it
        # on the beautician's roster hours (overlap / room checks still apply).
        appt = appt.with_context(skip_working_hours_check=True)
        with appt._resync_done_after():
            return appt._scheduler_move(step_id, staff_id, start_datetime)

    def _scheduler_move(self, step_id, staff_id, start_datetime):
        appt = self
        start_dt = fields.Datetime.from_string(start_datetime)
        if not start_dt:
            raise UserError(_("Could not read the drop target time."))

        if step_id and appt.step_ids:
            step = appt.step_ids.filtered(lambda s: s.id == step_id)
            if step:
                # A step block carries two independent bits of information:
                #  - which column it sits in  -> that step's beautician
                #  - where it sits vertically -> its own start time
                # A drop can change either or both, independently of the other
                # steps: only the FIRST step anchors the appointment (moving it
                # shifts start_datetime, so every chained step follows, same as
                # dragging the whole block). Any other step is pinned exactly
                # where it's dropped and switched to Manual Time, so it holds
                # there instead of snapping back to its chained position on the
                # next recompute - each service can be carried independently to
                # a different beautician or time without pre-configuring Manual
                # Time by hand first.
                new_staff = int(staff_id)
                step_start = step.start_datetime or appt.start_datetime
                moved_staff = step.staff_id.id != new_staff
                moved_time = bool(
                    step_start and abs((start_dt - step_start).total_seconds()) >= 60
                )
                is_first_step = bool(appt.step_ids) and appt.step_ids.sorted('sequence')[0].id == step.id

                if moved_time and is_first_step and appt.start_datetime:
                    appt.write({
                        'start_datetime': appt.start_datetime + (start_dt - step_start),
                    })
                elif moved_time:
                    step.write({
                        'timing_mode': 'manual',
                        'start_datetime': start_dt,
                        'end_datetime': start_dt + timedelta(minutes=step.duration_minutes or 30),
                    })

                if moved_staff:
                    step.write({'staff_id': new_staff})
                    # Re-derive "Main Beauticians" from the step assignments: the
                    # dragged beautician replaces the previous one, and anyone no
                    # longer running a step drops off (a beautician still on
                    # another step of this appointment is kept).
                    step_staff = appt.step_ids.filtered(
                        lambda s: s.need_staff and s.staff_id
                    ).mapped('staff_id')
                    if step_staff and set(step_staff.ids) != set(appt.staff_ids.ids):
                        appt.write({'staff_ids': [(6, 0, step_staff.ids)]})

                if moved_time or moved_staff:
                    # Re-run the double-booking / working-hours validation, which a
                    # bare step write would otherwise skip.
                    appt._check_overlap()
                return True

        # Fallback if no steps - reassign the appointment to the drop target beautician
        if appt.start_datetime and appt.end_datetime:
            duration = appt.end_datetime - appt.start_datetime
        else:
            duration = timedelta(hours=appt.duration or 1.0)
        appt.write({
            'staff_ids': [(6, 0, [int(staff_id)])],
            'staff_id': int(staff_id),
            'start_datetime': start_dt,
            'end_datetime': start_dt + duration,
        })
        return True

    @api.model
    def scheduler_resize(self, appointment_id, new_duration_hours):
        step_id = None
        parts = str(appointment_id).split('_')
        appt_id = int(parts[0])
        if len(parts) > 1 and parts[1].isdigit():
            step_id = int(parts[1])

        appt = self.browse(appt_id).exists()
        if not appt:
            return False
        appt._check_board_editable()
        appt = appt.with_context(skip_working_hours_check=True)
        with appt._resync_done_after():
            return appt._scheduler_resize(step_id, new_duration_hours)

    def _scheduler_resize(self, step_id, new_duration_hours):
        appt = self
        new_hours = max(0.25, float(new_duration_hours))
        str_val = str(round(new_hours * 4) / 4)
        has_str_val = str_val in dict(appt._fields['duration_selection'].selection).keys()

        if step_id and appt.step_ids:
            step = appt.step_ids.filtered(lambda s: s.id == step_id)
            if step:
                step.write({
                    'duration_minutes': max(15, int(new_hours * 60))
                })
                # Parallel steps don't add linearly - use the actual elapsed
                # time (last step to finish) rather than summing durations.
                end_cursor = appt._assign_step_times(appt.step_ids.sorted('sequence'), appt.start_datetime)
                total_hours = (end_cursor - appt.start_datetime).total_seconds() / 3600.0
                str_total = str(round(total_hours * 4) / 4)
                if str_total in dict(appt._fields['duration_selection'].selection).keys():
                    appt.write({'duration_selection': str_total})
                elif appt.duration_selection:
                    appt.write({'duration_selection': False})
                return True

        # Fallback if no steps or simple appointment
        if has_str_val:
            appt.write({'duration_selection': str_val, 'end_datetime': appt.start_datetime + timedelta(hours=new_hours)})
        else:
            appt.write({'duration_selection': False, 'end_datetime': appt.start_datetime + timedelta(hours=new_hours)})
            
        return True

    @api.model
    def _dashboard_period(self, date_filter):
        """(start, end) in naive UTC for a dashboard filter, or (False, False).

        Days, weeks and months begin at midnight where the salon is, not at
        midnight UTC - otherwise the first three hours of a Doha month land in
        the previous one.
        """
        tz = pytz.timezone(self.env.user.tz or 'Asia/Qatar')
        now = datetime.now(tz)
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if date_filter == 'today':
            start, end = today, today + relativedelta(days=1)
        elif date_filter == 'this_week':
            start = today - timedelta(days=today.weekday())
            end = start + relativedelta(weeks=1)
        elif date_filter == 'this_month':
            start = today.replace(day=1)
            end = start + relativedelta(months=1)
        elif date_filter == 'last_6_months':
            start, end = today - relativedelta(months=6), today + relativedelta(days=1)
        elif date_filter == 'last_year':
            start, end = today - relativedelta(years=1), today + relativedelta(days=1)
        else:
            return False, False
        to_utc = lambda dt: tz.normalize(tz.localize(dt.replace(tzinfo=None))).astimezone(pytz.utc).replace(tzinfo=None)
        return to_utc(start), to_utc(end)

    def _dashboard_settled(self):
        """Appointments whose money is already in: paid through the POS, or
        brought over from the previous system, where every visit was settled
        at the till there. (``is_migrated`` comes from the import module and
        is simply absent without it.)"""
        migrated = 'is_migrated' in self._fields
        return self.filtered(lambda a: a.payment_state == 'paid' or (migrated and a.is_migrated))

    @api.model
    def dashboard_collected_action(self, date_filter='all'):
        """The Sales History behind the dashboard's Collected figure."""
        start_date, end_date = self._dashboard_period(date_filter)
        domain = [('state', '!=', 'Cancelled'), ('item_type', '!=', 'sundry')]
        if start_date:
            domain += [('date', '>=', start_date), ('date', '<', end_date)]
        settled = ['|', ('appointment_id', '=', False), ('appointment_id.payment_state', '=', 'paid')]
        if 'is_migrated' in self._fields:
            settled = ['|'] + settled + [('appointment_id.is_migrated', '=', True)]
        action = self.env['ir.actions.act_window']._for_xml_id(
            'salon_spa_scheduler.action_salon_customer_history')
        action.update({
            'name': _('Collected'),
            'domain': domain + settled,
            'context': {'create': False},
        })
        return action

    @api.model
    def get_dashboard_data(self, date_filter='all'):
        """Dashboard figures.

        Counts come from the appointments. Money comes from Sales History
        (salon.customer.history) - what was actually charged, after discounts
        and price changes at the till, line by line with the beautician who
        did the work. Summing list prices over appointments, as the dashboard
        used to, overstated takings by well over half on the migrated data.
        """
        # Tips are created when an order is paid (pos_order.py); this is only
        # a safety net for one that slipped through. It looks at the last week
        # and at orders that carry a tip line - going through every paid order
        # ever, as it did, grows slower with each day of trading.
        try:
            self.env['pos.order'].search([
                ('state', 'in', ['paid', 'done', 'invoiced']),
                ('date_order', '>=', fields.Datetime.now() - timedelta(days=7)),
                ('lines.staff_id', '!=', False),
            ])._create_staff_tips()
        except Exception:
            pass

        start_date, end_date = self._dashboard_period(date_filter)
        domain = []
        if start_date:
            domain = [('start_datetime', '>=', start_date), ('start_datetime', '<', end_date)]
        appointments = self.search(domain)
        by_state = {state: appointments.filtered(lambda a, s=state: a.state == s)
                    for state in ('draft', 'confirmed', 'progress', 'done', 'cancel')}
        total_count = len(appointments)
        # Services booked, counted as the bookings charge them: every service
        # of a booking, its Additional Services, and a service done twice
        # twice (see _billable_services). Cancelled bookings don't count.
        services_done = sum(len(a._billable_services()) for a in by_state['done'])
        services_booked = services_done + sum(
            len(a._billable_services()) for a in appointments
            if a.state not in ('done', 'cancel'))

        # --- Money: the ledger ------------------------------------------
        # Summed in the database: on a few years of trading this is tens of
        # thousands of lines.
        History = self.env['salon.customer.history']
        ledger_domain = [('state', '!=', 'Cancelled'), ('item_type', '!=', 'sundry')]
        if start_date:
            ledger_domain += [('date', '>=', start_date), ('date', '<', end_date)]

        def ledger_sum(extra=()):
            [(total,)] = History._read_group(ledger_domain + list(extra), [], ['price_unit:sum'])
            return total or 0.0

        # A booking finished without payment is logged at list price, but the
        # money is not in yet - it belongs under Unpaid, not Paid.
        unsettled_domain = [('appointment_id', '!=', False),
                            ('appointment_id.payment_state', '!=', 'paid')]
        if 'is_migrated' in self._fields:
            unsettled_domain.append(('appointment_id.is_migrated', '=', False))
        paid_revenue = ledger_sum() - ledger_sum(unsettled_domain)

        # Collected, split: services (and packages), retail, discounts - the
        # membership discount line, negative - and anything else (misc items
        # imported from Shortcuts). Discounts taken on a line at the till are
        # already off that line's amount.
        def collected(extra):
            return ledger_sum(extra) - ledger_sum(extra + unsettled_domain)
        collected_services = collected([('item_type', 'in', ['service', 'package'])])
        collected_products = collected([('item_type', '=', 'product')])
        collected_discounts = collected([('item_type', '=', 'other'), ('price_unit', '<', 0)])
        collected_other = collected([('item_type', '=', 'other'), ('price_unit', '>=', 0)])

        open_appts = (by_state['confirmed'] | by_state['progress'] | by_state['done'])
        unpaid_appts = open_appts - open_appts._dashboard_settled()
        unpaid_revenue = sum(unpaid_appts.mapped('amount_subtotal'))
        total_revenue = paid_revenue + unpaid_revenue
        # To collect, split: finished but nobody took the money (act on it),
        # and bookings still to come or under way.
        unpaid_done = unpaid_appts.filtered(lambda a: a.state == 'done')
        unpaid_upcoming = unpaid_appts - unpaid_done

        done_count = len(by_state['done'])
        avg_value = paid_revenue / done_count if done_count else 0.0

        # --- Commissions and tips ---------------------------------------
        commission_domain = [('appointment_id', 'in', appointments.ids)] if start_date else []
        commissions = self.env['salon.commission'].search(commission_domain)
        total_commissions = sum(commissions.mapped('commission_amount'))
        paid_commissions = sum(commissions.filtered(lambda c: c.state == 'paid').mapped('commission_amount'))
        pending_commissions = sum(commissions.filtered(lambda c: c.state == 'draft').mapped('commission_amount'))

        tip_domain = [('date', '>=', start_date), ('date', '<', end_date)] if start_date else []
        tips = self.env['salon.staff.tip'].search(tip_domain)
        total_tips = sum(tips.mapped('amount'))
        paid_tips = sum(tips.filtered(lambda t: t.state == 'paid').mapped('amount'))
        unpaid_tips = sum(tips.filtered(lambda t: t.state == 'unpaid').mapped('amount'))

        reviews = self.env['salon.review'].search([])
        # No reviews is not the same as five stars.
        avg_rating = round(sum(int(r.rating) for r in reviews) / len(reviews), 1) if reviews else False

        # --- Beauticians: whoever did the work on a line gets it --------
        service_domain = ledger_domain + [('item_type', '=', 'service')]
        revenue_by_staff = {
            staff.id: total for staff, total in
            History._read_group(service_domain + [('staff_id', '!=', False)],
                                ['staff_id'], ['price_unit:sum'])}
        # One pass over the bookings: each counts for every beautician on it.
        involved_count, done_by_staff = {}, {}
        for appt in appointments:
            for staff in (appt.staff_id | appt.staff_ids | appt.step_ids.staff_id):
                involved_count[staff.id] = involved_count.get(staff.id, 0) + 1
                if appt.state == 'done':
                    done_by_staff[staff.id] = done_by_staff.get(staff.id, 0) + 1
        commission_by_staff, tips_by_staff = {}, {}
        for commission in commissions:
            commission_by_staff[commission.staff_id.id] = (
                commission_by_staff.get(commission.staff_id.id, 0.0) + commission.commission_amount)
        for tip in tips:
            tips_by_staff[tip.staff_id.id] = tips_by_staff.get(tip.staff_id.id, 0.0) + tip.amount
        staff_data = []
        for staff in self.env['salon.staff'].search([('active', '=', True)]):
            revenue = revenue_by_staff.get(staff.id, 0.0)
            staff_tips = tips_by_staff.get(staff.id, 0.0)
            if involved_count.get(staff.id) or revenue or staff_tips:
                staff_data.append({
                    'id': staff.id,
                    'name': staff.name,
                    'appt_count': involved_count.get(staff.id, 0),
                    'done_count': done_by_staff.get(staff.id, 0),
                    'revenue': revenue,
                    'commissions': commission_by_staff.get(staff.id, 0.0),
                    'tips': staff_tips,
                })
        staff_data.sort(key=lambda x: x['revenue'], reverse=True)

        # --- Services: what was sold, at what was charged ----------------
        service_data = {}
        for service, count, total in History._read_group(
                service_domain + [('service_id', '!=', False)],
                ['service_id'], ['__count', 'price_unit:sum']):
            service_data[service.name] = {'count': count, 'revenue': total}
        for name, count, total in History._read_group(
                service_domain + [('service_id', '=', False)],
                ['service_name'], ['__count', 'price_unit:sum']):
            entry = service_data.setdefault(name or _('Other'), {'count': 0, 'revenue': 0.0})
            entry['count'] += count
            entry['revenue'] += total
        service_list = sorted(
            ({'name': name, **data} for name, data in service_data.items()),
            key=lambda x: x['count'], reverse=True)[:5]

        recent_appointments = [{
            'id': a.id,
            'name': a.name,
            'customer': a.partner_id.name,
            'staff': a.staff_id.name,
            'service': ", ".join(a.service_ids.mapped('name')),
            'start': fields.Datetime.to_string(a.start_datetime),
            'state': a.state,
            'payment_state': 'paid' if a in a._dashboard_settled() else a.payment_state,
            'amount': a.amount_subtotal
        } for a in appointments.sorted(key=lambda x: x.start_datetime, reverse=True)[:6]]

        return {
            'total_count': total_count,
            'draft_count': len(by_state['draft']),
            'confirmed_count': len(by_state['confirmed']),
            'ongoing_count': len(by_state['progress']),
            'services_booked': services_booked,
            'services_done': services_done,
            'done_count': done_count,
            'cancel_count': len(by_state['cancel']),
            'total_revenue': total_revenue,
            'paid_revenue': paid_revenue,
            'unpaid_revenue': unpaid_revenue,
            'avg_value': avg_value,
            'collected_services': collected_services,
            'collected_products': collected_products,
            'collected_discounts': collected_discounts,
            'collected_other': collected_other,
            'unpaid_done_amount': sum(unpaid_done.mapped('amount_subtotal')),
            'unpaid_done_ids': unpaid_done.ids,
            'unpaid_upcoming_amount': sum(unpaid_upcoming.mapped('amount_subtotal')),
            'unpaid_upcoming_ids': unpaid_upcoming.ids,
            'total_commissions': total_commissions,
            'paid_commissions': paid_commissions,
            'pending_commissions': pending_commissions,
            'total_tips': total_tips,
            'paid_tips': paid_tips,
            'unpaid_tips': unpaid_tips,
            'waitlist_count': 0,
            'avg_rating': avg_rating,
            'review_count': len(reviews),
            'staff_stats': staff_data,
            'service_stats': service_list,
            'recent_appointments': recent_appointments,
            'currency': {
                'name': self.env.company.currency_id.name,
                'symbol': self.env.company.currency_id.symbol,
                'position': self.env.company.currency_id.position,
                'decimal_places': self.env.company.currency_id.decimal_places,
            },
        }

    @api.constrains('partner_id', 'state')
    def _check_cancellation_limit(self):
        # Bulk import of historical data: cancellations made in the old system
        # must not trip the limit. Live booking still validates as normal.
        if self.env.context.get('skip_salon_cancellation_limit'):
            return
        for rec in self:
            if rec.state not in ['draft', 'cancel'] and rec.partner_id:
                cancel_count = self.env['salon.appointment'].search_count([
                    ('partner_id', '=', rec.partner_id.id),
                    ('state', '=', 'cancel'),
                    ('id', '!=', rec.id),
                ])
                limit = rec.company_id.salon_max_cancellations
                if limit > 0 and cancel_count >= limit:
                    raise ValidationError(_("This customer (%s) has cancelled %s appointments and has exceeded the allowed limit (%s). Booking is blocked.") % (rec.partner_id.name, cancel_count, limit))

    def _send_cancellation_limit_email(self, cancel_count, limit):
        template = self.env.ref('salon_spa_scheduler.email_template_cancellation_limit_reached', raise_if_not_found=False)
        if template:
            template.with_context(cancel_count=cancel_count, limit=limit).send_mail(self.id, force_send=True)

    def unlink(self):
        for rec in self:
            if rec.state not in ['draft', 'cancel']:
                raise UserError(_("You can only delete appointments that are in 'Draft' or 'Cancel' state."))
        return super(SalonAppointment, self).unlink()


class SalonAppointmentLine(models.Model):
    _name = 'salon.appointment.line'
    _description = 'Appointment Service Line'
    _check_company_auto = True

    appointment_id = fields.Many2one('salon.appointment', ondelete='cascade', required=True)
    company_id = fields.Many2one(related='appointment_id.company_id', store=True, index=True, readonly=True)
    service_id = fields.Many2one('salon.service', string='Service', required=True, check_company=True)
    staff_id = fields.Many2one('salon.staff', string='Beautician/Staff', check_company=True)
    # The line's own price: filled from the price list when the service is
    # picked, then free to change for this booking. (It used to be a writable
    # related field, so changing it here rewrote the service's list price for
    # every future booking.)
    price_unit = fields.Float(
        string='Price', compute='_compute_price_unit', store=True, readonly=False,
        precompute=True)
    allowed_service_ids = fields.Many2many(
        'salon.service',
        compute='_compute_allowed_service_ids',
        string='Allowed Services'
    )

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

    @api.depends('service_id')
    def _compute_price_unit(self):
        # Only a change of service resets the price - a later price-list
        # change must not rewrite bookings already made.
        for rec in self:
            rec.price_unit = rec.service_id.list_price


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def write(self, vals):
        res = super().write(vals)
        if vals.get('state') == 'cancel':
            # An order cancelled at the till (closing the session cancels the
            # unpaid ones) no longer bills its booking: unlink it so the
            # booking can be sent to the POS again.
            self.env['salon.appointment'].sudo().search(
                [('pos_order_id', 'in', self.ids)]).write({'pos_order_id': False})
        if 'state' in vals and vals['state'] in ['paid', 'done', 'invoiced']:
            linked = self.env['salon.appointment'].sudo().search([
                ('pos_order_id', 'in', self.ids),
                ('state', 'in', ('progress', 'done')),
            ])
            for order in self:
                linked.filtered(lambda a, o=order: a.pos_order_id == o)._absorb_pos_services_safe(order)
            in_progress = linked.filtered(lambda a: a.state == 'progress')
            if in_progress:
                in_progress.action_done()
            # Closed before the customer paid: rewrite from what was charged.
            (linked - in_progress)._log_sale_history()
            (linked - in_progress)._sync_commissions()
            
            # Log POS history for orders that are NOT linked to appointments
            for order in self:
                if order.state in ['paid', 'done', 'invoiced']:
                    appt = self.env['salon.appointment'].sudo().search([('pos_order_id', '=', order.id)], limit=1)
                    if not appt and order.partner_id:
                        self.env['salon.customer.history']._log_pos_order(order)
        return res

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        for order in orders:
            if order.state in ['paid', 'done', 'invoiced']:
                linked = self.env['salon.appointment'].sudo().search([
                    ('pos_order_id', '=', order.id),
                    ('state', 'in', ('progress', 'done')),
                ])
                linked._absorb_pos_services_safe(order)
                in_progress = linked.filtered(lambda a: a.state == 'progress')
                if in_progress:
                    in_progress.action_done()
                (linked - in_progress)._log_sale_history()
                (linked - in_progress)._sync_commissions()
                
                # Log POS history for orders that are NOT linked to appointments
                appt = self.env['salon.appointment'].sudo().search([('pos_order_id', '=', order.id)], limit=1)
                if not appt and order.partner_id:
                    self.env['salon.customer.history']._log_pos_order(order)
        return orders
