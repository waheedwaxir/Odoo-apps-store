from datetime import datetime, time, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError, AccessError

class SalonAppointment(models.Model):
    _name = 'salon.appointment'
    _description = 'Salon/Spa Appointment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_datetime desc'

    name = fields.Char(default='New', copy=False)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True)
    phone = fields.Char(related='partner_id.phone', readonly=False)
    branch_id = fields.Many2one('salon.branch', string='Branch')
    room_id = fields.Many2one('salon.room', string='Chair', help="The chair/seat allocated for this salon appointment.")
    staff_id = fields.Many2one('salon.staff', required=True, tracking=True, string='Main Beautician')
    service_ids = fields.Many2many('salon.service', string='Services', required=True)
    staff_service_ids = fields.Many2many(
        'salon.service',
        compute='_compute_staff_service_ids',
        string='Staff Allowed Services'
    )
    service_id = fields.Many2one('salon.service', string='Primary Service', compute='_compute_service_id', store=True, readonly=False, tracking=True)
    amount_subtotal = fields.Float(string='Subtotal', compute='_compute_amount_subtotal', store=True)

    @api.depends('staff_id', 'staff_id.service_ids')
    def _compute_staff_service_ids(self):
        all_services = self.env['salon.service'].search([])
        for rec in self:
            if rec.staff_id and rec.staff_id.service_ids:
                rec.staff_service_ids = rec.staff_id.service_ids
            else:
                rec.staff_service_ids = all_services

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

    @api.depends('start_datetime', 'step_ids', 'step_ids.duration_minutes', 'service_ids', 'duration_selection')
    def _compute_end_datetime(self):
        for rec in self:
            if not rec.start_datetime:
                rec.end_datetime = False
                continue

            if rec.duration_selection:
                val_hours = float(rec.duration_selection)
                if rec.step_ids:
                    steps = rec.step_ids.sorted('sequence')
                    other_steps_dur = sum(s.duration_minutes for s in steps[:-1])
                    target_total_mins = int(val_hours * 60)
                    last_step_dur = max(15, target_total_mins - other_steps_dur)
                    if steps[-1].duration_minutes != last_step_dur:
                        steps[-1].duration_minutes = last_step_dur
                    current_time = rec.start_datetime
                    for step in steps:
                        step.start_datetime = current_time
                        current_time += timedelta(minutes=step.duration_minutes)
                        step.end_datetime = current_time
                    rec.end_datetime = current_time
                else:
                    rec.end_datetime = rec.start_datetime + timedelta(hours=val_hours)
            else:
                if rec.step_ids:
                    current_time = rec.start_datetime
                    for step in rec.step_ids.sorted('sequence'):
                        step.start_datetime = current_time
                        current_time += timedelta(minutes=step.duration_minutes)
                        step.end_datetime = current_time
                    rec.end_datetime = current_time
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
                other_steps_dur = sum(s.duration_minutes for s in steps[:-1])
                target_total_mins = int(val_hours * 60)
                last_step_dur = max(15, target_total_mins - other_steps_dur)
                steps[-1].duration_minutes = last_step_dur
            else:
                self.end_datetime = self.start_datetime + timedelta(hours=val_hours)

    @api.onchange('service_ids')
    def _onchange_service_ids_populate_steps(self):
        if self.service_ids:
            step_lines = []
            seq = 10
            for service in self.service_ids:
                if service.step_ids:
                    for step in service.step_ids:
                        step_lines.append((0, 0, {
                            'sequence': seq,
                            'name': f"{service.name} - {step.name}",
                            'duration_minutes': step.duration_minutes,
                            'need_staff': step.need_staff,
                            'staff_id': self.staff_id.id if step.need_staff else False,
                        }))
                        seq += 10
                else:
                    step_lines.append((0, 0, {
                        'sequence': seq,
                        'name': service.name,
                        'duration_minutes': int(service.duration * 60),
                        'need_staff': True,
                        'staff_id': self.staff_id.id,
                    }))
                    seq += 10
            self.step_ids = [(5, 0, 0)] + step_lines
            if self.duration_selection and self.start_datetime:
                self._onchange_duration_selection()

    @api.onchange('staff_id')
    def _onchange_staff_id_update_steps(self):
        if self.staff_id:
            for step in self.step_ids:
                if step.need_staff and not step.staff_id:
                    step.staff_id = self.staff_id.id

    def _compute_color(self):
        for rec in self:
            rec.color = (rec.id % 10) + 1 if rec.id else 4

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

    @api.depends('service_ids', 'service_ids.list_price', 'line_ids.price_unit')
    def _compute_amount_subtotal(self):
        for rec in self:
            primary_price = sum(s.list_price for s in rec.service_ids)
            lines_price = sum(line.price_unit for line in rec.line_ids)
            rec.amount_subtotal = primary_price + lines_price

    @api.onchange('service_ids', 'line_ids')
    def _onchange_services_subtotal(self):
        self._compute_amount_subtotal()

    @api.onchange('service_ids', 'start_datetime')
    def _onchange_service_time(self):
        for rec in self:
            if rec.service_ids and rec.start_datetime:
                total_duration = sum(s.duration for s in rec.service_ids)
                rec.end_datetime = rec.start_datetime + timedelta(hours=total_duration)

    @api.constrains('staff_id', 'start_datetime', 'end_datetime', 'state', 'room_id')
    def _check_overlap(self):
        for rec in self:
            if not rec.staff_id or not rec.start_datetime or not rec.end_datetime or rec.state == 'cancel':
                continue
            if rec.end_datetime <= rec.start_datetime:
                raise ValidationError(_('End time must be after start time.'))
            
            # Staff working hours check
            if rec.staff_id.employee_id:
                employee = rec.staff_id.employee_id
                calendar = employee.resource_calendar_id or employee.company_id.resource_calendar_id
                if calendar:
                    import pytz
                    start_aware = rec.start_datetime.replace(tzinfo=pytz.utc)
                    end_aware = rec.end_datetime.replace(tzinfo=pytz.utc)
                    
                    work_intervals = calendar._work_intervals_batch(
                        start_aware,
                        end_aware,
                        resources=employee.resource_id
                    )[employee.resource_id.id]
                    
                    intervals_list = [(start, end) for start, end, meta in work_intervals]
                    is_covered = any(start <= start_aware and end >= end_aware for start, end in intervals_list)
                    
                    if not is_covered:
                        day_start = datetime.combine(rec.start_datetime.date(), time.min).replace(tzinfo=pytz.utc)
                        day_end = datetime.combine(rec.start_datetime.date(), time.max).replace(tzinfo=pytz.utc)
                        
                        day_work_intervals = calendar._work_intervals_batch(
                            day_start,
                            day_end,
                            resources=employee.resource_id
                        )[employee.resource_id.id]
                        
                        tz_name = employee.tz or calendar.tz or 'UTC'
                        local_tz = pytz.timezone(tz_name)
                        
                        available_shifts = []
                        for start, end, meta in day_work_intervals:
                            start_local = start.astimezone(local_tz)
                            end_local = end.astimezone(local_tz)
                            available_shifts.append(f"{start_local.strftime('%I:%M %p')} to {end_local.strftime('%I:%M %p')}")
                            
                        if available_shifts:
                            shifts_str = " or ".join(available_shifts)
                            raise ValidationError(_("%(name)s is only available from %(shifts)s on this time.") % {
                                'name': employee.name,
                                'shifts': shifts_str
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
            else:
                # Fallback: Standard staff overlap check
                domain = [
                    ('id', '!=', rec.id),
                    ('staff_id', '=', rec.staff_id.id),
                    ('state', '!=', 'cancel'),
                    ('start_datetime', '<', rec.end_datetime),
                    ('end_datetime', '>', rec.start_datetime),
                ]
                step_overlaps = self.env['salon.appointment.step'].search_count([
                    ('appointment_id', '!=', rec.id),
                    ('appointment_id.state', '!=', 'cancel'),
                    ('staff_id', '=', rec.staff_id.id),
                    ('need_staff', '=', True),
                    ('start_datetime', '<', rec.end_datetime),
                    ('end_datetime', '>', rec.start_datetime),
                ])
                if self.search_count(domain) or step_overlaps:
                    raise ValidationError(_('This staff member already has an appointment during this time.'))

            # Room/Chair overlap check
            if rec.room_id:
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
            
        import pytz
        start_aware = self.start_datetime.replace(tzinfo=pytz.utc)
        end_aware = self.end_datetime.replace(tzinfo=pytz.utc)
        
        work_intervals = calendar._work_intervals_batch(
            start_aware,
            end_aware,
            resources=employee.resource_id
        )[employee.resource_id.id]
        
        intervals_list = [(start, end) for start, end, meta in work_intervals]
        is_covered = any(start <= start_aware and end >= end_aware for start, end in intervals_list)
        
        if not is_covered:
            day_start = datetime.combine(self.start_datetime.date(), time.min).replace(tzinfo=pytz.utc)
            day_end = datetime.combine(self.start_datetime.date(), time.max).replace(tzinfo=pytz.utc)
            
            day_work_intervals = calendar._work_intervals_batch(
                day_start,
                day_end,
                resources=employee.resource_id
            )[employee.resource_id.id]
            
            tz_name = employee.tz or calendar.tz or 'UTC'
            local_tz = pytz.timezone(tz_name)
            
            available_shifts = []
            for start, end, meta in day_work_intervals:
                start_local = start.astimezone(local_tz)
                end_local = end.astimezone(local_tz)
                available_shifts.append(f"{start_local.strftime('%I:%M %p')} to {end_local.strftime('%I:%M %p')}")
                
            if available_shifts:
                shifts_str = " or ".join(available_shifts)
                message = _("%(name)s is only available from %(shifts)s on this day.") % {
                    'name': employee.name,
                    'shifts': shifts_str
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

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env['ir.sequence'].sudo()
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = seq.next_by_code('salon.appointment') or 'New'
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
                    staff_id = vals.get('staff_id')
                    for service in services:
                        if service.step_ids:
                            for step in service.step_ids:
                                step_lines.append((0, 0, {
                                    'sequence': seq_num,
                                    'name': f"{service.name} - {step.name}",
                                    'duration_minutes': step.duration_minutes,
                                    'need_staff': step.need_staff,
                                    'staff_id': staff_id if step.need_staff else False,
                                }))
                                seq_num += 10
                        else:
                            step_lines.append((0, 0, {
                                'sequence': seq_num,
                                'name': service.name,
                                'duration_minutes': int(service.duration * 60),
                                'need_staff': True,
                                'staff_id': staff_id,
                            }))
                            seq_num += 10
                    if step_lines:
                        vals['step_ids'] = step_lines

        records = super().create(vals_list)
        
        # Send confirmation email immediately if created as confirmed
        template = self.env.ref('salon_spa_scheduler.email_template_appointment_confirmation', raise_if_not_found=False)
        if template:
            for rec in records:
                if rec.state == 'confirmed' and not rec.confirmation_sent:
                    template.send_mail(rec.id, force_send=True)
                    rec.confirmation_sent = True
        return records

    def write(self, vals):
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
            staff_id = vals.get('staff_id') or (self and self[0].staff_id.id)
            for service in services:
                if service.step_ids:
                    for step in service.step_ids:
                        step_lines.append((0, 0, {
                            'sequence': seq_num,
                            'name': f"{service.name} - {step.name}",
                            'duration_minutes': step.duration_minutes,
                            'need_staff': step.need_staff,
                            'staff_id': staff_id if step.need_staff else False,
                        }))
                        seq_num += 10
                else:
                    step_lines.append((0, 0, {
                        'sequence': seq_num,
                        'name': service.name,
                        'duration_minutes': int(service.duration * 60),
                        'need_staff': True,
                        'staff_id': staff_id,
                    }))
                    seq_num += 10
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
                        template.send_mail(rec.id, force_send=True)
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
                
                # Auto compute commissions
                self.env['salon.commission'].create({
                    'staff_id': rec.staff_id.id,
                    'appointment_id': rec.id,
                    'commission_amount': service.commission_value if service.commission_type == 'fixed' else (service.list_price * service.commission_value / 100.0),
                    'date': fields.Date.context_today(self),
                    'state': 'draft'
                })
            
            # Create Customer History
            if rec.partner_id:
                self.env['salon.customer.history'].search([('origin', '=', rec.name)]).unlink()
                history_vals = []
                for service in rec.service_ids:
                    history_vals.append({
                        'partner_id': rec.partner_id.id,
                        'date': rec.start_datetime or fields.Datetime.now(),
                        'service_name': service.name,
                        'staff_name': rec.staff_id.name,
                        'state': 'Completed',
                        'notes': rec.note or '',
                        'price_unit': service.list_price,
                        'origin': rec.name,
                    })
                for line in rec.line_ids:
                    history_vals.append({
                        'partner_id': rec.partner_id.id,
                        'date': rec.start_datetime or fields.Datetime.now(),
                        'service_name': line.service_id.name,
                        'staff_name': line.staff_id.name or rec.staff_id.name,
                        'state': 'Completed',
                        'notes': rec.note or '',
                        'price_unit': line.price_unit,
                        'origin': rec.name,
                    })
                if history_vals:
                    self.env['salon.customer.history'].create(history_vals)

        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancel'})
        for rec in self:
            if rec.partner_id:
                cancel_count = self.env['salon.appointment'].search_count([
                    ('partner_id', '=', rec.partner_id.id),
                    ('state', '=', 'cancel'),
                ])
                limit = int(self.env['ir.config_parameter'].sudo().get_param('salon_spa_scheduler.max_cancellations', 3))
                if limit > 0 and cancel_count >= limit:
                    rec._send_cancellation_limit_email(cancel_count, limit)

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    def action_create_pos_order(self):
        if not self.env.user.has_group('salon_spa_scheduler.group_salon_create_payment') and not self.env.user.has_group('salon_spa_scheduler.group_salon_manager'):
            raise AccessError(_("You do not have permission to send orders to Point of Sale."))
        for rec in self:
            if not rec.service_ids:
                raise ValidationError(_("No services selected on the appointment."))
            # Find the opened session of the current user, or fallback to the first opened session
            session = self.env['pos.session'].search([
                ('state', '=', 'opened'),
                ('user_id', '=', self.env.user.id)
            ], limit=1)
            if not session:
                session = self.env['pos.session'].search([('state', '=', 'opened')], limit=1)
            
            if not session:
                raise ValidationError(_("Please open a Point of Sale session first."))
            
            lines = []
            
            # Services (Many2many)
            for service in rec.service_ids:
                if not service.product_ids:
                    raise ValidationError(_("The selected service '%s' does not have any linked POS products.") % service.name)
                
                for idx, product in enumerate(service.product_ids):
                    price_unit = service.list_price if len(service.product_ids) == 1 else (product.list_price or service.list_price)
                    tax_ids = product.taxes_id.filtered(lambda t: t.company_id == session.company_id)
                    fpos = session.config_id.default_fiscal_position_id
                    tax_ids_after_fpos = fpos.map_tax(tax_ids) if fpos else tax_ids
                    
                    comp = tax_ids_after_fpos.compute_all(
                        price_unit,
                        currency=session.currency_id,
                        quantity=1.0,
                        product=product,
                        partner=rec.partner_id
                    )
                    
                    lines.append((0, 0, {
                        'product_id': product.id,
                        'qty': 1,
                        'price_unit': price_unit,
                        'price_subtotal': comp['total_excluded'],
                        'price_subtotal_incl': comp['total_included'],
                        'tax_ids': [(6, 0, tax_ids.ids)],
                        'full_product_name': product.display_name,
                    }))
            
            for line in rec.line_ids:
                if line.service_id.product_ids:
                    for idx, add_product in enumerate(line.service_id.product_ids):
                        add_price_unit = line.service_id.list_price if len(line.service_id.product_ids) == 1 else (add_product.list_price or line.service_id.list_price)
                        add_tax_ids = add_product.taxes_id.filtered(lambda t: t.company_id == session.company_id)
                        add_tax_ids_after_fpos = fpos.map_tax(add_tax_ids) if fpos else add_tax_ids
                        
                        add_comp = add_tax_ids_after_fpos.compute_all(
                            add_price_unit,
                            currency=session.currency_id,
                            quantity=1.0,
                            product=add_product,
                            partner=rec.partner_id
                        )
                        
                        lines.append((0, 0, {
                            'product_id': add_product.id,
                            'qty': 1,
                            'price_unit': add_price_unit,
                            'price_subtotal': add_comp['total_excluded'],
                            'price_subtotal_incl': add_comp['total_included'],
                            'tax_ids': [(6, 0, add_tax_ids.ids)],
                            'full_product_name': add_product.display_name,
                        }))

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
        start_hour = int(self.env['ir.config_parameter'].sudo().get_param('salon_spa_scheduler.start_hour', 8))
        end_hour = int(self.env['ir.config_parameter'].sudo().get_param('salon_spa_scheduler.end_hour', 22))
        if not (0 <= start_hour <= 23):
            start_hour = 8
        if not (0 <= end_hour <= 23):
            end_hour = 22
        if start_hour >= end_hour:
            start_hour, end_hour = 8, 22

        import pytz
        tz_name = self.env.context.get('tz') or self.env.user.tz or 'UTC'
        user_tz = pytz.timezone(tz_name)
        local_start = user_tz.localize(datetime.combine(day, time(start_hour, 0)))
        local_end = user_tz.localize(datetime.combine(day, time(end_hour, 0)))
        start = local_start.astimezone(pytz.utc).replace(tzinfo=None)
        end = local_end.astimezone(pytz.utc).replace(tzinfo=None)
        staff = self.env['salon.staff'].search([('active', '=', True)], order='sequence, name')
        appointments = self.search([
            ('start_datetime', '<', end),
            ('end_datetime', '>', start),
            ('state', '!=', 'cancel'),
        ])
        appointments_list = []
        for a in appointments:
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
                            'staff_id': step.staff_id.id,
                            'branch_id': a.branch_id.id,
                            'service': step.name,
                            'start': fields.Datetime.to_string(step_start) if step_start else "",
                            'end': fields.Datetime.to_string(step_end) if step_end else "",
                            'duration': step.duration_minutes / 60.0,
                            'state': a.state,
                            'is_arrived': a.is_arrived,
                            'payment_state': a.payment_state,
                            'color': a.color,
                        })
            else:
                a_start = a.start_datetime or start
                a_end = a.end_datetime or (a_start + timedelta(hours=a.duration or 1.0))
                appointments_list.append({
                    'id': str(a.id),
                    'appointment_id': a.id,
                    'name': a.name,
                    'customer': a.partner_id.name,
                    'phone': a.phone or '',
                    'staff_id': a.staff_id.id,
                    'branch_id': a.branch_id.id,
                    'service': ", ".join(a.service_ids.mapped('name')),
                    'start': fields.Datetime.to_string(a_start) if a_start else "",
                    'end': fields.Datetime.to_string(a_end) if a_end else "",
                    'duration': a.duration,
                    'state': a.state,
                    'is_arrived': a.is_arrived,
                    'payment_state': a.payment_state,
                    'color': a.color,
                })

        return {
            'date': fields.Date.to_string(day),
            'start_hour': start_hour,
            'end_hour': end_hour,
            'slot_minutes': 15,
            'staff': [{'id': s.id, 'name': s.name, 'color': s.color} for s in staff],
            'branches': [{'id': b.id, 'name': b.name} for b in self.env['salon.branch'].search([])],
            'appointments': appointments_list,
            'services': [{'id': s.id, 'name': s.name, 'duration': s.duration} for s in self.env['salon.service'].search([('active', '=', True)])],
        }

    @api.model
    def scheduler_quick_create(self, vals):
        partner_name = vals.get('customer_name')
        partner = self.env['res.partner'].search([('name', '=', partner_name)], limit=1)
        if not partner:
            partner = self.env['res.partner'].create({'name': partner_name, 'phone': vals.get('phone')})
        service = self.env['salon.service'].browse(int(vals['service_id']))
        start_dt = fields.Datetime.from_string(vals['start_datetime'])
        end_dt = start_dt + timedelta(hours=service.duration)
        
        # Select first branch if not specified
        branch = self.env['salon.branch'].search([], limit=1)
        if not branch:
            branch = self.env['salon.branch'].create({'name': 'Main Branch'})

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
            appt.write({'is_arrived': True})
        return True

    @api.model
    def scheduler_move(self, appointment_id, staff_id, start_datetime):
        step_id = None
        if '_' in str(appointment_id):
            parts = str(appointment_id).split('_')
            appt_id = int(parts[0])
            step_id = int(parts[1])
        else:
            appt_id = int(appointment_id)

        appt = self.browse(appt_id).exists()
        if not appt:
            return False
        start_dt = fields.Datetime.from_string(start_datetime)

        if step_id and appt.step_ids:
            step = appt.step_ids.filtered(lambda s: s.id == step_id)
            if step:
                # Find sum of durations of all steps before this step in sequence order
                prior_steps = appt.step_ids.filtered(lambda s: s.sequence < step.sequence or (s.sequence == step.sequence and s.id < step.id))
                prior_duration_mins = sum(s.duration_minutes for s in prior_steps)
                new_start_dt = start_dt - timedelta(minutes=prior_duration_mins)

                appt.write({
                    'start_datetime': new_start_dt,
                })
                # Update staff for this step specifically
                step.write({
                    'staff_id': int(staff_id),
                })
                return True

        # Fallback if no steps
        duration = appt.end_datetime - appt.start_datetime
        appt.write({'staff_id': int(staff_id), 'start_datetime': start_dt, 'end_datetime': start_dt + duration})
        return True

    @api.model
    def scheduler_resize(self, appointment_id, new_duration_hours):
        step_id = None
        if '_' in str(appointment_id):
            parts = str(appointment_id).split('_')
            appt_id = int(parts[0])
            step_id = int(parts[1])
        else:
            appt_id = int(appointment_id)

        appt = self.browse(appt_id).exists()
        if not appt:
            return False

        new_hours = max(0.25, float(new_duration_hours))
        str_val = str(round(new_hours * 4) / 4)
        has_str_val = str_val in dict(appt._fields['duration_selection'].selection).keys()

        if step_id and appt.step_ids:
            step = appt.step_ids.filtered(lambda s: s.id == step_id)
            if step:
                step.write({
                    'duration_minutes': max(15, int(new_hours * 60))
                })
                total_hours = sum(s.duration_minutes for s in appt.step_ids) / 60.0
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
    def get_dashboard_data(self, date_filter='all'):
        try:
            self.env['pos.order'].search([('state', 'in', ['paid', 'done', 'invoiced'])])._create_staff_tips()
        except Exception:
            pass

        domain = []
        now = fields.Datetime.now()
        
        if date_filter == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)
            domain += [('start_datetime', '>=', start_date), ('start_datetime', '<=', end_date)]
        elif date_filter == 'this_week':
            weekday = now.weekday()
            start_date = (now - timedelta(days=weekday)).replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = (start_date + timedelta(days=6)).replace(hour=23, minute=59, second=59, microsecond=999999)
            domain += [('start_datetime', '>=', start_date), ('start_datetime', '<=', end_date)]
        elif date_filter == 'this_month':
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if start_date.month == 12:
                next_month = start_date.replace(year=start_date.year + 1, month=1)
            else:
                next_month = start_date.replace(month=start_date.month + 1)
            end_date = (next_month - timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=999999)
            domain += [('start_datetime', '>=', start_date), ('start_datetime', '<=', end_date)]

        appointments = self.search(domain)
        
        total_count = len(appointments)
        draft_count = len(appointments.filtered(lambda a: a.state == 'draft'))
        confirmed_count = len(appointments.filtered(lambda a: a.state == 'confirmed'))
        ongoing_count = len(appointments.filtered(lambda a: a.state == 'progress'))
        done_count = len(appointments.filtered(lambda a: a.state == 'done'))
        cancel_count = len(appointments.filtered(lambda a: a.state == 'cancel'))

        active_appts = appointments.filtered(lambda a: a.state != 'cancel')
        total_revenue = sum(active_appts.mapped('amount_subtotal'))
        paid_revenue = sum(active_appts.filtered(lambda a: a.payment_state == 'paid').mapped('amount_subtotal'))
        unpaid_revenue = sum(active_appts.filtered(lambda a: a.payment_state == 'not_paid').mapped('amount_subtotal'))
        
        avg_value = total_revenue / total_count if total_count > 0 else 0.0
        
        commission_domain = []
        tip_domain = []
        if date_filter != 'all':
            if appointments:
                commission_domain += [('appointment_id', 'in', appointments.ids)]
            if date_filter in ['today', 'this_week', 'this_month']:
                tip_domain += [('date', '>=', start_date), ('date', '<=', end_date)]

        commissions = self.env['salon.commission'].search(commission_domain)
        total_commissions = sum(commissions.mapped('commission_amount'))
        paid_commissions = sum(commissions.filtered(lambda c: c.state == 'paid').mapped('commission_amount'))
        pending_commissions = sum(commissions.filtered(lambda c: c.state == 'draft').mapped('commission_amount'))

        tips = self.env['salon.staff.tip'].search(tip_domain)
        total_tips = sum(tips.mapped('amount'))
        paid_tips = sum(tips.filtered(lambda t: t.state == 'paid').mapped('amount'))
        unpaid_tips = sum(tips.filtered(lambda t: t.state == 'unpaid').mapped('amount'))

        waitlist_count = 0

        reviews = self.env['salon.review'].search([])
        avg_rating = sum(int(r.rating) for r in reviews) / len(reviews) if reviews else 5.0

        staff_data = []
        staff_members = self.env['salon.staff'].search([('active', '=', True)])
        for staff in staff_members:
            staff_appts = appointments.filtered(lambda a: a.staff_id == staff)
            staff_done_appts = staff_appts.filtered(lambda a: a.state == 'done')
            staff_revenue = sum(staff_done_appts.mapped('amount_subtotal'))
            
            # Commissions can be filtered by either active appointments or all
            staff_comm = commissions.filtered(lambda c: c.staff_id == staff)
            staff_commissions = sum(staff_comm.mapped('commission_amount'))

            staff_tips_records = tips.filtered(lambda t: t.staff_id == staff)
            staff_tips = sum(staff_tips_records.mapped('amount'))
            
            if len(staff_appts) > 0 or staff_revenue > 0 or staff_tips > 0:
                staff_data.append({
                    'id': staff.id,
                    'name': staff.name,
                    'appt_count': len(staff_appts),
                    'done_count': len(staff_done_appts),
                    'revenue': staff_revenue,
                    'commissions': staff_commissions,
                    'tips': staff_tips,
                })
        staff_data = sorted(staff_data, key=lambda x: x['revenue'], reverse=True)

        service_data = {}
        for appt in appointments:
            if appt.state == 'cancel':
                continue
            for s in appt.service_ids:
                if s.name not in service_data:
                    service_data[s.name] = {'count': 0, 'revenue': 0.0}
                service_data[s.name]['count'] += 1
                service_data[s.name]['revenue'] += s.list_price
        
        service_list = [{'name': name, 'count': data['count'], 'revenue': data['revenue']} for name, data in service_data.items()]
        service_list = sorted(service_list, key=lambda x: x['count'], reverse=True)[:5]

        recent_appointments = [{
            'id': a.id,
            'name': a.name,
            'customer': a.partner_id.name,
            'staff': a.staff_id.name,
            'service': ", ".join(a.service_ids.mapped('name')),
            'start': fields.Datetime.to_string(a.start_datetime),
            'state': a.state,
            'payment_state': a.payment_state,
            'amount': a.amount_subtotal
        } for a in appointments.sorted(key=lambda x: x.start_datetime, reverse=True)[:6]]

        return {
            'total_count': total_count,
            'draft_count': draft_count,
            'confirmed_count': confirmed_count,
            'ongoing_count': ongoing_count,
            'done_count': done_count,
            'cancel_count': cancel_count,
            'total_revenue': total_revenue,
            'paid_revenue': paid_revenue,
            'unpaid_revenue': unpaid_revenue,
            'avg_value': avg_value,
            'total_commissions': total_commissions,
            'paid_commissions': paid_commissions,
            'pending_commissions': pending_commissions,
            'total_tips': total_tips,
            'paid_tips': paid_tips,
            'unpaid_tips': unpaid_tips,
            'waitlist_count': waitlist_count,
            'avg_rating': round(avg_rating, 1),
            'staff_stats': staff_data,
            'service_stats': service_list,
            'recent_appointments': recent_appointments,
        }

    @api.constrains('partner_id', 'state')
    def _check_cancellation_limit(self):
        for rec in self:
            if rec.state not in ['draft', 'cancel'] and rec.partner_id:
                cancel_count = self.env['salon.appointment'].search_count([
                    ('partner_id', '=', rec.partner_id.id),
                    ('state', '=', 'cancel'),
                    ('id', '!=', rec.id),
                ])
                limit = int(self.env['ir.config_parameter'].sudo().get_param('salon_spa_scheduler.max_cancellations', 3))
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

    appointment_id = fields.Many2one('salon.appointment', ondelete='cascade', required=True)
    service_id = fields.Many2one('salon.service', string='Service', required=True)
    staff_id = fields.Many2one('salon.staff', string='Beautician/Staff')
    price_unit = fields.Float(related='service_id.list_price', readonly=False)
    allowed_service_ids = fields.Many2many(
        'salon.service',
        compute='_compute_allowed_service_ids',
        string='Allowed Services'
    )

    @api.depends('staff_id', 'staff_id.service_ids', 'appointment_id.staff_service_ids')
    def _compute_allowed_service_ids(self):
        all_services = self.env['salon.service'].search([])
        for rec in self:
            if rec.staff_id and rec.staff_id.service_ids:
                rec.allowed_service_ids = rec.staff_id.service_ids
            elif rec.appointment_id and rec.appointment_id.staff_service_ids:
                rec.allowed_service_ids = rec.appointment_id.staff_service_ids
            else:
                rec.allowed_service_ids = all_services


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def write(self, vals):
        res = super().write(vals)
        if 'state' in vals and vals['state'] in ['paid', 'done', 'invoiced']:
            appointments = self.env['salon.appointment'].sudo().search([
                ('pos_order_id', 'in', self.ids),
                ('state', '=', 'progress')
            ])
            if appointments:
                appointments.action_done()
            
            # Log POS history for orders that are NOT linked to appointments
            for order in self:
                if order.state in ['paid', 'done', 'invoiced']:
                    appt = self.env['salon.appointment'].sudo().search([('pos_order_id', '=', order.id)], limit=1)
                    if not appt and order.partner_id:
                        self.env['salon.customer.history'].search([('origin', '=', order.name)]).unlink()
                        history_vals = []
                        for line in order.lines:
                            history_vals.append({
                                'partner_id': order.partner_id.id,
                                'date': order.date_order,
                                'service_name': line.product_id.display_name,
                                'staff_name': order.user_id.name,
                                'state': 'Paid',
                                'notes': line.note or order.general_customer_note or order.internal_note or '',
                                'price_unit': line.price_subtotal_incl,
                                'origin': order.name,
                            })
                        if history_vals:
                            self.env['salon.customer.history'].create(history_vals)
        return res

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        for order in orders:
            if order.state in ['paid', 'done', 'invoiced']:
                appointments = self.env['salon.appointment'].sudo().search([
                    ('pos_order_id', '=', order.id),
                    ('state', '=', 'progress')
                ])
                if appointments:
                    appointments.action_done()
                
                # Log POS history for orders that are NOT linked to appointments
                appt = self.env['salon.appointment'].sudo().search([('pos_order_id', '=', order.id)], limit=1)
                if not appt and order.partner_id:
                    self.env['salon.customer.history'].search([('origin', '=', order.name)]).unlink()
                    history_vals = []
                    for line in order.lines:
                        history_vals.append({
                            'partner_id': order.partner_id.id,
                            'date': order.date_order,
                            'service_name': line.product_id.display_name,
                            'staff_name': order.user_id.name,
                            'state': 'Paid',
                            'notes': line.note or order.general_customer_note or order.internal_note or '',
                            'price_unit': line.price_subtotal_incl,
                            'origin': order.name,
                        })
                    if history_vals:
                        self.env['salon.customer.history'].create(history_vals)
        return orders
