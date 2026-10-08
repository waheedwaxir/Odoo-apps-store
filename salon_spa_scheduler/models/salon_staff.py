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

from datetime import datetime, time, timedelta

import pytz

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class SalonStaff(models.Model):
    _name = 'salon.staff'
    _description = 'Salon/Spa Staff'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'pos.load.mixin']
    _order = 'sequence, name'
    _check_company_auto = True

    sequence = fields.Integer(default=10, tracking=True)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True, index=True,
        default=lambda self: self.env.company, tracking=True)
    # No check_company: staff may be shared (company_id = False) while the linked
    # hr.employee belongs to a specific company.
    employee_id = fields.Many2one('hr.employee', string='Employee', tracking=True)
    department_id = fields.Many2one(
        'hr.department', string='Department',
        related='employee_id.department_id', store=True, readonly=True)
    partner_id = fields.Many2one('res.partner', string='Contact', required=True, ondelete='cascade', tracking=True)
    name = fields.Char(related='partner_id.name', store=True, readonly=False, tracking=True)
    image_1920 = fields.Image(related='partner_id.image_1920', readonly=False)
    user_id = fields.Many2one('res.users', string='Related User', tracking=True)
    # What a beautician does: whole service categories, plus single services
    # outside them. Nothing picked = every service.
    service_category_ids = fields.Many2many(
        'salon.service.category', 'salon_staff_service_category_rel', 'staff_id', 'category_id',
        string='Service Categories', tracking=True,
        help="Every service in these categories. Leave both this and Extra "
             "Services empty for a beautician who does everything.")
    service_ids = fields.Many2many(
        'salon.service', string='Extra Services', tracking=True, check_company=True,
        help="Single services this beautician does besides the categories above.")
    effective_service_ids = fields.Many2many(
        'salon.service', string='Services', compute='_compute_effective_service_ids',
        help="The services this beautician does: the categories' plus the extra "
             "ones; empty means every service.")
    tip_ids = fields.One2many('salon.staff.tip', 'staff_id', string='Tips')
    total_unpaid_tips = fields.Float(string='Total Unpaid Tips', compute='_compute_unpaid_tips')
    total_tips = fields.Float(string='Total Tips', compute='_compute_unpaid_tips')
    appointment_count = fields.Integer(string='Bookings', compute='_compute_appointment_count')
    # --- Monthly sales targets (incentive) --------------------------------
    # Two thresholds on the month's service sales, as the salon's incentive
    # sheet has them: past Target 1 the beautician earns Target 1 % of the
    # month's services, past Target 2 the Target 2 % instead.
    # Filled from the Position; can still be changed for one beautician.
    # Changing the Position's targets updates everyone in that position.
    job_id = fields.Many2one(
        'hr.job', string='Position', tracking=True, check_company=True,
        compute='_compute_job_id', store=True, readonly=False,
        help="Job Position (Employees > Configuration, or Salon > Configuration > "
             "Positions); taken from the employee and brings its monthly targets.")
    target_1 = fields.Float(string='Target 1', tracking=True,
                            compute='_compute_targets', store=True, readonly=False,
                            help="Monthly service sales from which the Target 1 % incentive applies.")
    target_1_rate = fields.Float(string='Target 1 %', default=5.0, tracking=True,
                                 compute='_compute_targets', store=True, readonly=False)
    target_2 = fields.Float(string='Target 2', tracking=True,
                            compute='_compute_targets', store=True, readonly=False,
                            help="Monthly service sales from which the Target 2 % incentive applies "
                                 "instead of Target 1 %.")
    target_2_rate = fields.Float(string='Target 2 %', default=10.0, tracking=True,
                                 compute='_compute_targets', store=True, readonly=False)
    month_reached = fields.Float(
        string='Reached (Month)', compute='_compute_month_target',
        help="This month's service sales (Sales History, net of discounts).")
    month_achieved = fields.Float(
        string='% of Target 1', compute='_compute_month_target',
        help="This month's service sales against Target 1.")
    month_incentive_rate = fields.Float(string='Incentive %', compute='_compute_month_target')
    month_incentive = fields.Float(string='Incentive (Month)', compute='_compute_month_target')
    last_pos_session_id = fields.Many2one(
        'pos.session', string='Last POS Session', compute='_compute_earned_last_session')
    earned_last_session = fields.Float(
        string='Last Session', compute='_compute_earned_last_session',
        help="What this beautician's services brought in during the branch's "
             "latest POS session (the open one, if there is one).")
    earned_today = fields.Float(
        string='Earned Today', compute='_compute_earned_today',
        help="What this beautician's services brought in today (Sales History, "
             "net of discounts), e.g. to check against the till at closing.")
    active = fields.Boolean(default=True, tracking=True)
    color = fields.Integer(default=1)
    
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    job_title = fields.Char(string='Job Title')

    # --- Time blocks ------------------------------------------------------
    block_ids = fields.One2many('salon.block', 'staff_id', string='Time Blocks')
    block_count = fields.Integer(string='Blocks', compute='_compute_block_count')

    def _compute_block_count(self):
        Block = self.env['salon.block']
        for staff in self:
            staff.block_count = Block.search_count(
                [('staff_id', '=', staff.id)]) if isinstance(staff.id, int) else 0

    def action_view_blocks(self):
        """Every stretch this beautician is off the floor without a customer."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Time Blocks - %s', self.name),
            'res_model': 'salon.block',
            'view_mode': 'list,form',
            'domain': [('staff_id', '=', self.id)],
            'context': {'default_staff_id': self.id},
        }

    def _appointment_domain(self):
        """Every appointment this beautician is involved in - as the primary
        beautician, one of the Main Beauticians, or on any service step."""
        self.ensure_one()
        return [
            '|', '|',
            ('staff_id', '=', self.id),
            ('staff_ids', 'in', self.id),
            ('step_ids.staff_id', '=', self.id),
        ]

    def _compute_appointment_count(self):
        Appointment = self.env['salon.appointment']
        for staff in self:
            if isinstance(staff.id, int):
                staff.appointment_count = Appointment.search_count(staff._appointment_domain())
            else:
                staff.appointment_count = 0

    def action_view_appointments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Booking History - %s', self.name),
            'res_model': 'salon.appointment',
            'view_mode': 'list,form,calendar',
            'domain': self._appointment_domain(),
            'context': {
                'default_staff_id': self.id,
                'default_staff_ids': [(4, self.id)],
            },
        }

    # --- Who may do which service ----------------------------------------
    @api.depends('service_category_ids', 'service_ids')
    def _compute_effective_service_ids(self):
        Service = self.env['salon.service']
        for staff in self:
            services = staff.service_ids
            if staff.service_category_ids:
                services |= Service.search([('category_id', 'in', staff.service_category_ids.ids)])
            staff.effective_service_ids = services

    def _can_do(self, service):
        """Whether this beautician does ``service``."""
        self.ensure_one()
        return not self.effective_service_ids or service in self.effective_service_ids

    def _allowed_services(self):
        """The services these beauticians do (together)."""
        Service = self.env['salon.service']
        allowed = Service
        for staff in self:
            if not staff.effective_service_ids:
                return Service.search([])
            allowed |= staff.effective_service_ids
        return allowed

    # --- Point of Sale: the branch's beauticians, to put on a line -------
    pos_service_product_ids = fields.Many2many(
        'product.product', string='POS Products of Allowed Services',
        compute='_compute_pos_service_product_ids',
        help="The POS products of the services this beautician may do; empty "
             "means every service (as on the scheduler).")

    @api.depends('effective_service_ids')
    def _compute_pos_service_product_ids(self):
        for staff in self:
            services = staff.effective_service_ids
            staff.pos_service_product_ids = services.product_ids | services.product_id

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [('active', '=', True), ('company_id', '=', config.company_id.id)]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['id', 'name', 'pos_service_product_ids']

    def _today_utc_range(self):
        """Start and end of today in the user's timezone, as naive UTC."""
        tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
        start = tz.localize(datetime.combine(fields.Date.context_today(self), time.min))
        start = start.astimezone(pytz.utc).replace(tzinfo=None)
        return start, start + timedelta(days=1)

    def _month_utc_range(self, day=None):
        """First day of ``day``'s month (default today) to the first of the
        next month, in the user's timezone, as naive UTC."""
        tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
        day = day or fields.Date.context_today(self)
        first = day.replace(day=1)
        nxt = (first + timedelta(days=32)).replace(day=1)
        to_utc = lambda d: tz.localize(datetime.combine(d, time.min)).astimezone(pytz.utc).replace(tzinfo=None)
        return to_utc(first), to_utc(nxt)

    def _incentive_rate(self, reached):
        """The incentive % the month's service sales earn."""
        self.ensure_one()
        if self.target_2 and reached >= self.target_2:
            return self.target_2_rate
        if self.target_1 and reached >= self.target_1:
            return self.target_1_rate
        return 0.0

    @api.depends('employee_id.job_id')
    def _compute_job_id(self):
        for staff in self:
            staff.job_id = staff.employee_id.job_id or staff.job_id

    @api.depends('job_id.salon_target_1', 'job_id.salon_target_1_rate',
                 'job_id.salon_target_2', 'job_id.salon_target_2_rate')
    def _compute_targets(self):
        for staff in self:
            job = staff.job_id
            if job:
                staff.target_1 = job.salon_target_1
                staff.target_1_rate = job.salon_target_1_rate
                staff.target_2 = job.salon_target_2
                staff.target_2_rate = job.salon_target_2_rate
            else:
                # No title: keep what was typed for this beautician.
                staff.target_1 = staff.target_1
                staff.target_1_rate = staff.target_1_rate or 5.0
                staff.target_2 = staff.target_2
                staff.target_2_rate = staff.target_2_rate or 10.0

    def _service_sales(self, start, end):
        """{staff: service sales between two naive-UTC datetimes}."""
        staff_ids = [s._origin.id for s in self if isinstance(s._origin.id, int) and s._origin.id]
        if not staff_ids:
            return {}
        return dict(self.env['salon.customer.history']._read_group(
            [('staff_id', 'in', staff_ids), ('item_type', '=', 'service'),
             ('state', '!=', 'Cancelled'), ('date', '>=', start), ('date', '<', end)],
            ['staff_id'], ['price_unit:sum']))

    @api.depends('target_1', 'target_1_rate', 'target_2', 'target_2_rate')
    def _compute_month_target(self):
        start, end = self._month_utc_range()
        totals = self._service_sales(start, end)
        for staff in self:
            reached = totals.get(staff._origin, 0.0)
            rate = staff._incentive_rate(reached)
            staff.month_reached = reached
            staff.month_achieved = reached / staff.target_1 * 100.0 if staff.target_1 else 0.0
            staff.month_incentive_rate = rate
            staff.month_incentive = reached * rate / 100.0

    # --- Monthly incentive -> Commissions ----------------------------------
    def _create_month_incentives(self, day):
        """One Monthly Incentive commission per beautician for the month of
        ``day``, from that month's service sales and their targets. A draft
        one for the same month is replaced (so a re-run after a correction
        is right); a paid one is left alone. Nothing below Target 1."""
        Commission = self.env['salon.commission'].sudo()
        period = day.replace(day=1)
        month_end = (period + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        start, end = self._month_utc_range(day)
        totals = self._service_sales(start, end)
        created = Commission
        for staff in self:
            existing = Commission.search([
                ('staff_id', '=', staff.id), ('kind', '=', 'incentive'), ('period', '=', period)])
            if existing.filtered(lambda c: c.state == 'paid'):
                continue
            existing.unlink()
            reached = totals.get(staff, 0.0)
            rate = staff._incentive_rate(reached)
            currency = staff.company_id.currency_id
            amount = currency.round(reached * rate / 100.0)
            if amount:
                created |= Commission.create({
                    'company_id': staff.company_id.id,
                    'staff_id': staff.id,
                    'kind': 'incentive',
                    'period': period,
                    'reached': reached,
                    'rate': rate,
                    'commission_amount': amount,
                    'date': month_end,
                    'state': 'draft',
                })
        return created

    @api.model
    def _incentive_tz(self, company):
        return (company.partner_id.tz or self.env.ref('base.user_admin').tz or 'UTC')

    @api.model
    def _cron_monthly_incentives(self):
        """Scheduled on the 1st: last month's incentives, branch by branch in
        the branch's own timezone."""
        for company in self.env['res.company'].search([]):
            staff = self.with_company(company).with_context(tz=self._incentive_tz(company)).search([
                ('company_id', '=', company.id), ('active', '=', True),
                '|', ('target_1', '>', 0), ('target_2', '>', 0)])
            if staff:
                today = fields.Date.context_today(staff)
                staff._create_month_incentives(today.replace(day=1) - timedelta(days=1))

    def action_create_last_month_incentives(self):
        """Beautician Targets button: last month's incentives now, for the
        selected beauticians or every active one with a target."""
        staff = self or self.search([('active', '=', True), '|', ('target_1', '>', 0), ('target_2', '>', 0)])
        today = fields.Date.context_today(self)
        created = staff._create_month_incentives(today.replace(day=1) - timedelta(days=1))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Monthly Incentives'),
            'res_model': 'salon.commission',
            'view_mode': 'list,form',
            'domain': [('id', 'in', created.ids)],
        }

    @api.constrains('target_1', 'target_2')
    def _check_targets(self):
        for staff in self:
            if staff.target_1 and staff.target_2 and staff.target_2 < staff.target_1:
                raise ValidationError(_("%s: Target 2 has to be at least Target 1.", staff.name))

    def _earnings_domain(self):
        self.ensure_one()
        return [('staff_id', '=', self.id), ('state', '!=', 'Cancelled')]

    def _compute_earned_today(self):
        History = self.env['salon.customer.history']
        start, end = self._today_utc_range()
        totals = {}
        staff_ids = [s.id for s in self if isinstance(s.id, int)]
        if staff_ids:
            totals = dict(History._read_group(
                [('staff_id', 'in', staff_ids), ('state', '!=', 'Cancelled'),
                 ('date', '>=', start), ('date', '<', end)],
                ['staff_id'], ['price_unit:sum']))
        for staff in self:
            staff.earned_today = totals.get(staff._origin, 0.0)

    def _compute_earned_last_session(self):
        History = self.env['salon.customer.history']
        Session = self.env['pos.session']
        sessions = {}
        for staff in self:
            company = staff.company_id
            if company not in sessions:
                sessions[company] = Session.search(
                    [('config_id.company_id', '=', company.id)],
                    order='start_at desc, id desc', limit=1)
            session = sessions[company]
            staff.last_pos_session_id = session
            if session and isinstance(staff.id, int):
                staff.earned_last_session = sum(History.search(
                    staff._earnings_domain() + [('pos_session_id', '=', session.id)]
                ).mapped('price_unit'))
            else:
                staff.earned_last_session = 0.0

    def action_view_earnings_session(self):
        """This beautician's Sales History lines paid in the latest POS session."""
        self.ensure_one()
        session = self.last_pos_session_id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Earnings - %(staff)s - %(session)s',
                      staff=self.name, session=session.name or _('no POS session')),
            'res_model': 'salon.customer.history',
            'view_mode': 'list,form',
            'domain': self._earnings_domain() + [('pos_session_id', '=', session.id)],
            'search_view_id': [self.env.ref('salon_spa_scheduler.view_salon_customer_history_search').id],
            'context': {'create': False},
        }

    def action_view_earnings(self):
        """Every Sales History line credited to this beautician, opened on
        today so the total matches the button."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Earnings - %s', self.name),
            'res_model': 'salon.customer.history',
            'view_mode': 'list,form',
            'domain': self._earnings_domain(),
            'search_view_id': [self.env.ref('salon_spa_scheduler.view_salon_customer_history_search').id],
            'context': {'search_default_filter_today': 1, 'create': False},
        }

    @api.depends('tip_ids.amount', 'tip_ids.state')
    def _compute_unpaid_tips(self):
        for staff in self:
            unpaid_tips = staff.tip_ids.filtered(lambda t: t.state == 'unpaid')
            staff.total_unpaid_tips = sum(unpaid_tips.mapped('amount'))
            staff.total_tips = sum(staff.tip_ids.mapped('amount'))

    def action_view_tips(self):
        """Every tip this beautician was given at the till, paid or not; the
        Unpaid / Paid filters narrow it down."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Tips - %s', self.name),
            'res_model': 'salon.staff.tip',
            'view_mode': 'list,form',
            'domain': [('staff_id', '=', self.id)],
            'search_view_id': [self.env.ref('salon_spa_scheduler.view_salon_staff_tip_search').id],
            'context': {'create': False, 'default_staff_id': self.id},
        }

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            self.phone = self.employee_id.work_phone or self.employee_id.mobile_phone
            self.email = self.employee_id.work_email
            self.job_title = self.employee_id.job_title
            
            if self.employee_id.work_contact_id:
                self.partner_id = self.employee_id.work_contact_id.id
            elif self.employee_id.user_id and self.employee_id.user_id.partner_id:
                self.partner_id = self.employee_id.user_id.partner_id.id
            else:
                # search for partner with same name
                partner = self.env['res.partner'].search([('name', '=', self.employee_id.name)], limit=1)
                if not partner:
                    partner = self.env['res.partner'].create({
                        'name': self.employee_id.name,
                        'email': self.employee_id.work_email,
                        'phone': self.employee_id.work_phone or self.employee_id.mobile_phone,
                    })
                self.partner_id = partner.id
