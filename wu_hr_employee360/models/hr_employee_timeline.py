# -*- coding: utf-8 -*-
from datetime import date
from odoo import api, fields, models, _


class HrEmployeeTimelineEvent(models.Model):
    """
    Chronological milestone journal for every employee.
    Stores manually entered HR events AND auto-synthesised events from
    hr.leave, hr.contract, hr.appraisal, etc.
    """
    _name = 'hr.employee.timeline.event'
    _description = 'Employee Timeline Event'
    _order = 'event_date desc, id desc'
    _rec_name = 'title'

    employee_id = fields.Many2one(
        'hr.employee', string='Employee',
        required=True, ondelete='cascade', index=True
    )
    event_date = fields.Date(string='Event Date', required=True, default=fields.Date.today)
    event_type = fields.Selection([
        ('joining',         'Joining / Onboarding'),
        ('promotion',       'Promotion'),
        ('transfer',        'Transfer'),
        ('salary_revision', 'Salary Revision'),
        ('leave',           'Leave / Absence'),
        ('appraisal',       'Performance Appraisal'),
        ('training',        'Training / Certification'),
        ('award',           'Award / Recognition'),
        ('warning',         'Disciplinary Warning'),
        ('disciplinary',    'Disciplinary Action'),
        ('separation',      'Resignation / Termination'),
        ('note',            'General HR Note'),
    ], string='Event Type', required=True, default='note')

    title = fields.Char(string='Event Title', required=True)
    description = fields.Text(string='Description / Details')

    color = fields.Selection([
        ('green',   'Green  — Positive'),
        ('blue',    'Blue   — Informational'),
        ('orange',  'Orange — Transfer / Change'),
        ('purple',  'Purple — Achievement'),
        ('red',     'Red    — Warning / Negative'),
        ('teal',    'Teal   — Training'),
        ('gray',    'Gray   — General'),
    ], string='Badge Color', compute='_compute_color', store=True, readonly=False)

    # Optional soft-link to a source record
    related_model = fields.Char(string='Source Model', help='Technical model name of the originating record')
    related_id    = fields.Integer(string='Source Record ID')
    is_synthetic  = fields.Boolean(string='Auto-Synthesised', default=False,
                                   help='True when this event was generated automatically from other Odoo data')

    # Computed display helpers
    days_ago = fields.Integer(string='Days Ago', compute='_compute_days_ago')

    # ------------------------------------------------------------------ #
    #  Computed fields                                                     #
    # ------------------------------------------------------------------ #
    @api.depends('event_type')
    def _compute_color(self):
        color_map = {
            'joining':         'green',
            'promotion':       'purple',
            'transfer':        'orange',
            'salary_revision': 'blue',
            'leave':           'teal',
            'appraisal':       'blue',
            'training':        'teal',
            'award':           'purple',
            'warning':         'red',
            'disciplinary':    'red',
            'separation':      'red',
            'note':            'gray',
        }
        for rec in self:
            if not rec.color:
                rec.color = color_map.get(rec.event_type, 'gray')

    @api.depends('event_date')
    def _compute_days_ago(self):
        today = fields.Date.today()
        for rec in self:
            if rec.event_date:
                rec.days_ago = (today - rec.event_date).days
            else:
                rec.days_ago = 0

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #
    @api.model
    def get_or_create_joining_event(self, employee):
        """
        Ensure a 'joining' event exists for the employee.
        Uses create_date as the joining date proxy (or date_start from first contract).
        """
        existing = self.search([('employee_id', '=', employee.id), ('event_type', '=', 'joining')], limit=1)
        if existing:
            return existing

        join_date = None
        if 'hr.contract' in self.env:
            first_contract = self.env['hr.contract'].search(
                [('employee_id', '=', employee.id)],
                order='date_start asc', limit=1
            )
            if first_contract and first_contract.date_start:
                join_date = first_contract.date_start

        if not join_date and employee.create_date:
            join_date = employee.create_date.date()

        if not join_date:
            join_date = fields.Date.today()

        dept = getattr(getattr(employee, 'department_id', False), 'name', False) or 'General'
        return self.create({
            'employee_id': employee.id,
            'event_date':  join_date,
            'event_type':  'joining',
            'title':       _('Joined the Organisation'),
            'description': _('Employee onboarded. Department: %s.') % dept,
            'color':       'green',
            'is_synthetic': True,
        })

    @api.model
    def synthesise_timeline_for_employee(self, employee_id):
        """
        Scan all related Odoo data for an employee and create synthetic
        timeline events that do not yet exist.  Called lazily when the
        360 drawer opens.
        """
        employee = self.env['hr.employee'].browse(int(employee_id))
        if not employee.exists():
            return

        # ---- 1. Joining event ----------------------------------------
        self.get_or_create_joining_event(employee)

        # ---- 2. Salary revisions from contract history ----------------
        if 'hr.contract' in self.env:
            contracts = self.env['hr.contract'].search(
                [('employee_id', '=', employee.id)],
                order='date_start asc'
            )
            prev_wage = None
            for c in contracts:
                wage = getattr(c, 'wage', None)
                if wage and wage != prev_wage and c.date_start:
                    existing = self.search([
                        ('employee_id', '=', employee.id),
                        ('event_type', '=', 'salary_revision'),
                        ('related_model', '=', 'hr.contract'),
                        ('related_id', '=', c.id),
                    ], limit=1)
                    if not existing:
                        currency = getattr(getattr(c, 'company_id', False), 'currency_id', False)
                        sym = getattr(currency, 'symbol', '') or ''
                        change_label = ''
                        if prev_wage is not None:
                            diff = wage - prev_wage
                            pct  = round((diff / prev_wage) * 100, 1) if prev_wage else 0
                            change_label = _(' (+%s%s / %s%%)') % (sym, round(diff, 2), pct) if diff > 0 else _(' (-%s%s / %s%%)') % (sym, abs(round(diff, 2)), abs(pct))
                        self.create({
                            'employee_id':   employee.id,
                            'event_date':    c.date_start,
                            'event_type':    'salary_revision',
                            'title':         _('Salary Revised: %s%s%s') % (sym, round(wage, 2), change_label),
                            'description':   _('Contract: %s. Effective %s.') % (c.name or 'N/A', str(c.date_start)),
                            'color':         'blue',
                            'related_model': 'hr.contract',
                            'related_id':    c.id,
                            'is_synthetic':  True,
                        })
                    prev_wage = wage

        # ---- 3. Validated leave records (recent 1 year) ---------------
        if 'hr.leave' in self.env:
            one_year_ago = fields.Date.today().replace(year=fields.Date.today().year - 1)
            leaves = self.env['hr.leave'].search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'validate'),
                ('date_from', '>=', one_year_ago),
            ], order='date_from desc', limit=20)
            for lv in leaves:
                existing = self.search([
                    ('employee_id', '=', employee.id),
                    ('event_type', '=', 'leave'),
                    ('related_model', '=', 'hr.leave'),
                    ('related_id', '=', lv.id),
                ], limit=1)
                if not existing:
                    lv_type = lv.holiday_status_id.name if lv.holiday_status_id else 'Time Off'
                    days    = round(getattr(lv, 'number_of_days', 0) or 0, 1)
                    self.create({
                        'employee_id':   employee.id,
                        'event_date':    lv.date_from.date() if lv.date_from else fields.Date.today(),
                        'event_type':    'leave',
                        'title':         _('%s — %s day(s)') % (lv_type, days),
                        'description':   _('From %s to %s.') % (
                            str(lv.date_from.date()) if lv.date_from else '-',
                            str(lv.date_to.date()) if lv.date_to else '-'
                        ),
                        'color':         'teal',
                        'related_model': 'hr.leave',
                        'related_id':    lv.id,
                        'is_synthetic':  True,
                    })

        # ---- 4. Performance appraisals --------------------------------
        if 'hr.appraisal' in self.env:
            appraisals = self.env['hr.appraisal'].search([
                ('employee_id', '=', employee.id),
            ], order='date_close desc', limit=10)
            for ap in appraisals:
                existing = self.search([
                    ('employee_id', '=', employee.id),
                    ('event_type', '=', 'appraisal'),
                    ('related_model', '=', 'hr.appraisal'),
                    ('related_id', '=', ap.id),
                ], limit=1)
                if not existing:
                    ap_date = getattr(ap, 'date_close', False) or getattr(ap, 'create_date', False)
                    if ap_date:
                        ap_date = ap_date.date() if hasattr(ap_date, 'date') else ap_date
                    else:
                        ap_date = fields.Date.today()
                    rating_val = getattr(ap, 'rating', False) or ''
                    self.create({
                        'employee_id':   employee.id,
                        'event_date':    ap_date,
                        'event_type':    'appraisal',
                        'title':         _('Performance Appraisal Completed'),
                        'description':   _('Rating: %s. State: %s.') % (rating_val or 'N/A', (ap.state or 'done').capitalize()),
                        'color':         'blue',
                        'related_model': 'hr.appraisal',
                        'related_id':    ap.id,
                        'is_synthetic':  True,
                    })

        # ---- 5. Training (hr.resume.line type == 'training') ----------
        if 'hr.resume.line' in self.env:
            trainings = self.env['hr.resume.line'].search([
                ('employee_id', '=', employee.id),
                ('line_type_id.name', 'ilike', 'train'),
            ], limit=10)
            for tr in trainings:
                existing = self.search([
                    ('employee_id', '=', employee.id),
                    ('event_type', '=', 'training'),
                    ('related_model', '=', 'hr.resume.line'),
                    ('related_id', '=', tr.id),
                ], limit=1)
                if not existing and tr.date_start:
                    self.create({
                        'employee_id':   employee.id,
                        'event_date':    tr.date_start,
                        'event_type':    'training',
                        'title':         _('Training: %s') % (tr.name or 'Professional Development'),
                        'description':   _('Duration: %s to %s.') % (str(tr.date_start), str(tr.date_end) if tr.date_end else 'Ongoing'),
                        'color':         'teal',
                        'related_model': 'hr.resume.line',
                        'related_id':    tr.id,
                        'is_synthetic':  True,
                    })
