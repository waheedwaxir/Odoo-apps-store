# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import api, fields, models, _


class HrSmartAlert(models.Model):
    """
    Smart HR Alert System — proactively surfaces actionable HR events
    with severity levels, dismissal, and categorisation.
    """
    _name = 'hr.smart.alert'
    _description = 'HR Smart Alert'
    _order = 'severity_order asc, due_date asc'
    _rec_name = 'message'

    alert_type = fields.Selection([
        ('document_expiry',        '📄 Document Expiry'),
        ('contract_renewal',       '📋 Contract Renewal'),
        ('probation_end',          '⏱ Probation Period End'),
        ('birthday',               '🎂 Employee Birthday'),
        ('anniversary',            '🎉 Work Anniversary'),
        ('appraisal_due',          '📈 Appraisal Due'),
        ('training_due',           '🎓 Training Due'),
        ('leave_balance_critical', '🌴 Leave Balance Critical'),
        ('attendance_anomaly',     '⚠️ Attendance Anomaly'),
        ('disciplinary_followup',  '🚨 Disciplinary Follow-up'),
    ], string='Alert Type', required=True)

    severity = fields.Selection([
        ('critical', 'Critical'),
        ('warning',  'Warning'),
        ('info',     'Info'),
    ], string='Severity', required=True, default='info')

    severity_order = fields.Integer(compute='_compute_severity_order', store=True)

    employee_id = fields.Many2one(
        'hr.employee', string='Employee',
        ondelete='cascade', index=True
    )
    employee_name = fields.Char(related='employee_id.name', store=True, string='Employee Name')
    department     = fields.Char(compute='_compute_department', store=True, string='Department')
    photo_url      = fields.Char(compute='_compute_photo_url', string='Photo URL')

    message   = fields.Char(string='Alert Message', required=True)
    detail    = fields.Text(string='Additional Detail')
    due_date  = fields.Date(string='Due / Event Date')
    days_left = fields.Integer(string='Days Remaining', compute='_compute_days_left', store=True)

    is_dismissed = fields.Boolean(string='Dismissed', default=False, index=True)
    created_date = fields.Date(string='Alert Created', default=fields.Date.today)
    dismissed_by = fields.Many2one('res.users', string='Dismissed By')

    # Source record link
    related_model = fields.Char(string='Source Model')
    related_id    = fields.Integer(string='Source Record ID')

    # ------------------------------------------------------------------ #
    #  Computed                                                            #
    # ------------------------------------------------------------------ #
    @api.depends('severity')
    def _compute_severity_order(self):
        order_map = {'critical': 1, 'warning': 2, 'info': 3}
        for rec in self:
            rec.severity_order = order_map.get(rec.severity, 3)

    @api.depends('employee_id')
    def _compute_department(self):
        for rec in self:
            rec.department = getattr(getattr(rec.employee_id, 'department_id', False), 'name', False) or 'General'

    def _compute_photo_url(self):
        for rec in self:
            if rec.employee_id:
                rec.photo_url = f'/web/image?model=hr.employee&id={rec.employee_id.id}&field=avatar_128'
            else:
                rec.photo_url = '/web/static/img/avatar.png'

    @api.depends('due_date')
    def _compute_days_left(self):
        today = fields.Date.today()
        for rec in self:
            if rec.due_date:
                rec.days_left = (rec.due_date - today).days
            else:
                rec.days_left = 0

    # ------------------------------------------------------------------ #
    #  Alert Generation Engine                                            #
    # ------------------------------------------------------------------ #
    @api.model
    def generate_smart_alerts(self, employee_ids=None):
        """
        Scan the HR data and generate/refresh smart alerts.
        Clears non-dismissed alerts first, then rebuilds.
        Called by get_dashboard_data() on demand.
        """
        today = fields.Date.today()
        domain = [('is_dismissed', '=', False)]
        if employee_ids:
            domain.append(('employee_id', 'in', employee_ids))
        self.search(domain).unlink()

        employees = self.env['hr.employee'].search([('active', '=', True)])
        if employee_ids:
            employees = employees.filtered(lambda e: e.id in employee_ids)

        alerts_to_create = []

        for emp in employees:
            emp_name = emp.name or 'Employee'
            emp_dept = getattr(getattr(emp, 'department_id', False), 'name', False) or 'General'

            # ---- Document: Visa expiry ----------------------------------
            if hasattr(emp, 'visa_expire') and emp.visa_expire:
                days = (emp.visa_expire - today).days
                if 0 <= days <= 60:
                    severity = 'critical' if days <= 7 else ('warning' if days <= 30 else 'info')
                    alerts_to_create.append({
                        'alert_type':    'document_expiry',
                        'severity':      severity,
                        'employee_id':   emp.id,
                        'message':       _('Visa expiring in %d day(s) — %s') % (days, emp_name),
                        'detail':        _('Visa No: %s | Dept: %s') % (getattr(emp, 'visa_no', 'N/A') or 'N/A', emp_dept),
                        'due_date':      emp.visa_expire,
                        'related_model': 'hr.employee',
                        'related_id':    emp.id,
                    })

            # ---- Document: National ID ---------------------------
            if hasattr(emp, 'id_expiry_date') and emp.id_expiry_date:
                days = (emp.id_expiry_date - today).days
                if 0 <= days <= 60:
                    severity = 'critical' if days <= 7 else ('warning' if days <= 30 else 'info')
                    alerts_to_create.append({
                        'alert_type':    'document_expiry',
                        'severity':      severity,
                        'employee_id':   emp.id,
                        'message':       _('National ID expiring in %d day(s) — %s') % (days, emp_name),
                        'detail':        _('ID: %s | Dept: %s') % (getattr(emp, 'identification_id', 'N/A') or 'N/A', emp_dept),
                        'due_date':      emp.id_expiry_date,
                        'related_model': 'hr.employee',
                        'related_id':    emp.id,
                    })

        # ---- Contract renewals & Probation -----------------------------
        contract_emp_ids = set()
        if 'hr.contract' in self.env:
            try:
                contracts = self.env['hr.contract'].search([('state', 'in', ['draft', 'open'])])
                for c in contracts:
                    contract_emp_ids.add(c.employee_id.id if c.employee_id else False)
                    if hasattr(c, 'date_end') and c.date_end:
                        days = (c.date_end - today).days
                        if 0 <= days <= 60:
                            emp = c.employee_id
                            severity = 'critical' if days <= 14 else ('warning' if days <= 30 else 'info')
                            alerts_to_create.append({
                                'alert_type':    'contract_renewal',
                                'severity':      severity,
                                'employee_id':   emp.id if emp else False,
                                'message':       _('Contract expiring in %d day(s) — %s') % (days, emp.name if emp else 'Employee'),
                                'detail':        _('Contract: %s | Wage: %s') % (c.name or 'N/A', getattr(c, 'wage', 'N/A')),
                                'due_date':      c.date_end,
                                'related_model': 'hr.contract',
                                'related_id':    c.id,
                            })
                    # Probation check
                    if hasattr(c, 'trial_date_end') and c.trial_date_end and 0 <= (c.trial_date_end - today).days <= 14:
                        days_p = (c.trial_date_end - today).days
                        emp = c.employee_id
                        alerts_to_create.append({
                            'alert_type':    'probation_end',
                            'severity':      'info' if days_p > 7 else 'warning',
                            'employee_id':   emp.id if emp else False,
                            'message':       _('Probation ends in %d day(s) — %s') % (days_p, emp.name if emp else 'Employee'),
                            'detail':        _('Contract: %s') % (c.name or 'N/A'),
                            'due_date':      c.trial_date_end,
                            'related_model': 'hr.contract',
                            'related_id':    c.id,
                        })
            except Exception as e:
                _logger.warning("Failed to query hr.contract states for smart alerts, falling back to Odoo 19 native fields: %s", str(e))
        
        # Odoo 19 native fallback using hr.employee fields directly
        for emp in employees:
            if emp.id in contract_emp_ids:
                continue
            if hasattr(emp, 'contract_date_end') and emp.contract_date_end:
                days = (emp.contract_date_end - today).days
                if 0 <= days <= 60:
                    severity = 'critical' if days <= 14 else ('warning' if days <= 30 else 'info')
                    alerts_to_create.append({
                        'alert_type':    'contract_renewal',
                        'severity':      severity,
                        'employee_id':   emp.id,
                        'message':       _('Contract expiring in %d day(s) — %s') % (days, emp.name),
                        'detail':        _('Contract End: %s') % (emp.contract_date_end.strftime('%Y-%m-%d')),
                        'due_date':      emp.contract_date_end,
                        'related_model': 'hr.employee',
                        'related_id':    emp.id,
                    })
            if hasattr(emp, 'trial_date_end') and emp.trial_date_end:
                days_p = (emp.trial_date_end - today).days
                if 0 <= days_p <= 14:
                    alerts_to_create.append({
                        'alert_type':    'probation_end',
                        'severity':      'info' if days_p > 7 else 'warning',
                        'employee_id':   emp.id,
                        'message':       _('Probation ends in %d day(s) — %s') % (days_p, emp.name),
                        'detail':        _('Probation End: %s') % (emp.trial_date_end.strftime('%Y-%m-%d')),
                        'due_date':      emp.trial_date_end,
                        'related_model': 'hr.employee',
                        'related_id':    emp.id,
                    })

        # ---- Birthdays this week ---------------------------------------
        week_end = today + timedelta(days=7)
        for emp in employees:
            if not getattr(emp, 'birthday', False) or not emp.birthday:
                continue
            try:
                bday_this_year = emp.birthday.replace(year=today.year)
            except ValueError:
                bday_this_year = emp.birthday.replace(year=today.year, day=28)
            if today <= bday_this_year <= week_end:
                days_to_bday = (bday_this_year - today).days
                alerts_to_create.append({
                    'alert_type':    'birthday',
                    'severity':      'info',
                    'employee_id':   emp.id,
                    'message':       _('Birthday in %d day(s) — %s 🎂') % (days_to_bday, emp.name),
                    'detail':        _('Consider sending a birthday greeting or scheduling a celebration.'),
                    'due_date':      bday_this_year,
                    'related_model': 'hr.employee',
                    'related_id':    emp.id,
                })

        # ---- Work anniversaries this month -----------------------------
        for emp in employees:
            if not emp.create_date:
                continue
            join_date = emp.create_date.date()
            if join_date.month == today.month and join_date.day >= today.day:
                years = today.year - join_date.year
                if years > 0:
                    alerts_to_create.append({
                        'alert_type':    'anniversary',
                        'severity':      'info',
                        'employee_id':   emp.id,
                        'message':       _('%d-Year Work Anniversary this month — %s 🎉') % (years, emp.name),
                        'detail':        _('Joined on %s. Consider recognition or service award.') % str(join_date),
                        'due_date':      today.replace(day=join_date.day),
                        'related_model': 'hr.employee',
                        'related_id':    emp.id,
                    })

        # ---- Appraisals overdue (>365 days since last) -----------------
        if 'hr.appraisal' in self.env:
            for emp in employees:
                last_ap = self.env['hr.appraisal'].search(
                    [('employee_id', '=', emp.id), ('state', '=', 'done')],
                    order='date_close desc', limit=1
                )
                if last_ap:
                    ap_date = getattr(last_ap, 'date_close', False)
                    if ap_date and (today - ap_date.date()).days > 365:
                        alerts_to_create.append({
                            'alert_type':    'appraisal_due',
                            'severity':      'warning',
                            'employee_id':   emp.id,
                            'message':       _('Appraisal overdue (last: %s) — %s') % (str(ap_date.date()), emp.name),
                            'detail':        _('Last performance review was over a year ago. Schedule an appraisal.'),
                            'due_date':      today,
                            'related_model': 'hr.appraisal',
                            'related_id':    last_ap.id,
                        })

        # ---- Missing checkout anomalies --------------------------------
        if 'hr.attendance' in self.env:
            yesterday_start = fields.Datetime.now() - timedelta(hours=36)
            missing_atts = self.env['hr.attendance'].search([
                ('check_out', '=', False),
                ('check_in', '<=', yesterday_start),
            ], limit=20)
            for att in missing_atts:
                emp = att.employee_id
                if emp:
                    alerts_to_create.append({
                        'alert_type':    'attendance_anomaly',
                        'severity':      'warning',
                        'employee_id':   emp.id,
                        'message':       _('Missing check-out since %s — %s') % (
                            att.check_in.strftime('%d %b %H:%M') if att.check_in else 'N/A', emp.name
                        ),
                        'detail':        _('Employee has an open attendance record with no check-out.'),
                        'due_date':      today,
                        'related_model': 'hr.attendance',
                        'related_id':    att.id,
                    })

        if alerts_to_create:
            self.create(alerts_to_create)

        return len(alerts_to_create)

    @api.model
    def dismiss_alert(self, alert_id):
        """Mark a single alert as dismissed."""
        alert = self.browse(int(alert_id))
        if alert.exists():
            alert.write({'is_dismissed': True, 'dismissed_by': self.env.uid})
            return {'success': True, 'message': _('Alert dismissed.')}
        return {'success': False, 'message': _('Alert not found.')}

    @api.model
    def get_alerts_summary(self):
        """Return a structured summary of current active alerts for the dashboard."""
        alerts = self.search([('is_dismissed', '=', False)], order='severity_order asc, due_date asc')
        result = {'critical': [], 'warning': [], 'info': [], 'total': len(alerts)}
        for a in alerts:
            entry = {
                'id':            a.id,
                'alert_type':    a.alert_type,
                'message':       a.message,
                'detail':        a.detail or '',
                'due_date':      str(a.due_date) if a.due_date else '',
                'days_left':     a.days_left,
                'employee_id':   a.employee_id.id if a.employee_id else 0,
                'employee_name': a.employee_name or '',
                'department':    a.department or '',
                'photo_url':     a.photo_url or '',
                'related_model': a.related_model or '',
                'related_id':    a.related_id or 0,
            }
            if a.severity in result:
                result[a.severity].append(entry)
        result['unread'] = len(result['critical']) + len(result['warning'])
        return result

    # ------------------------------------------------------------------ #
    #  Email Notifications                                                 #
    # ------------------------------------------------------------------ #
    @api.model
    def send_daily_digest(self):
        """
        Called by the ir.cron daily at 08:00.
        Sends the digest email to every user in hr.group_hr_manager.
        """
        import logging
        _logger = logging.getLogger(__name__)

        summary = self.get_alerts_summary()
        if summary['total'] == 0:
            _logger.info("HR 360 digest: no active alerts, skipping email.")
            return True

        template = self.env.ref(
            'wu_hr_employee360.email_template_hr360_daily_digest', raise_if_not_found=False
        )
        if not template:
            _logger.warning("HR 360 digest template not found.")
            return False

        # Build dashboard URL
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        dashboard_url = f"{base_url}/odoo/hr-employee-360" if base_url else '#'

        today_str = fields.Date.today().strftime('%d %b %Y')

        # Send to all HR managers
        managers = self.env['res.users'].search([
            ('groups_id', 'in', [self.env.ref('hr.group_hr_manager').id]),
            ('active', '=', True),
            ('email', '!=', False),
        ])

        for manager in managers:
            if not manager.email:
                continue
            ctx = {
                'today_date':      today_str,
                'critical_count':  len(summary['critical']),
                'warning_count':   len(summary['warning']),
                'info_count':      len(summary['info']),
                'critical_alerts': summary['critical'][:10],   # cap at 10
                'warning_alerts':  summary['warning'][:10],
                'dashboard_url':   dashboard_url,
                'recipient_email': manager.email,
                'lang':            manager.lang or 'en_US',
            }
            try:
                # Use a dummy employee record as the template object
                dummy_emp = self.env['hr.employee'].search([], limit=1)
                if dummy_emp:
                    template.with_context(**ctx).send_mail(dummy_emp.id, force_send=True)
                    _logger.info("HR 360 digest sent to %s", manager.email)
            except Exception as e:
                _logger.error("HR 360 digest email failed for %s: %s", manager.email, e)

        return True

    @api.model
    def send_critical_instant_alert(self, alert_id):
        """
        Send an immediate email for a single critical alert.
        Called when a critical alert is first generated.
        """
        import logging
        _logger = logging.getLogger(__name__)

        alert = self.browse(int(alert_id))
        if not alert.exists() or alert.severity != 'critical':
            return False

        template = self.env.ref(
            'wu_hr_employee360.email_template_hr360_critical_instant', raise_if_not_found=False
        )
        if not template:
            return False

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        dashboard_url = f"{base_url}/odoo/hr-employee-360" if base_url else '#'

        managers = self.env['res.users'].search([
            ('groups_id', 'in', [self.env.ref('hr.group_hr_manager').id]),
            ('active', '=', True),
            ('email', '!=', False),
        ])

        for manager in managers:
            if not manager.email:
                continue
            ctx = {
                'alert_message':   alert.message or '',
                'employee_name':   alert.employee_name or 'N/A',
                'department':      alert.department or 'N/A',
                'due_date':        str(alert.due_date) if alert.due_date else 'N/A',
                'alert_type':      (alert.alert_type or '').replace('_', ' ').title(),
                'dashboard_url':   dashboard_url,
                'recipient_email': manager.email,
                'lang':            manager.lang or 'en_US',
            }
            try:
                dummy_emp = alert.employee_id or self.env['hr.employee'].search([], limit=1)
                if dummy_emp:
                    template.with_context(**ctx).send_mail(dummy_emp.id, force_send=True)
            except Exception as e:
                _logger.error("HR 360 critical instant email failed: %s", e)

        return True

    @api.model
    def send_digest_now(self):
        """
        Manually trigger digest — callable from dashboard UI button.
        Returns success/failure dict for OWL notification.
        """
        try:
            self.send_daily_digest()
            managers = self.env['res.users'].search([
                ('groups_id', 'in', [self.env.ref('hr.group_hr_manager').id]),
                ('active', '=', True), ('email', '!=', False),
            ])
            emails = [m.email for m in managers if m.email]
            return {
                'success': True,
                'message': _('Digest sent to %d HR Manager(s): %s') % (
                    len(emails), ', '.join(emails[:3]) + ('...' if len(emails) > 3 else '')
                )
            }
        except Exception as e:
            return {'success': False, 'message': str(e)}

    # ------------------------------------------------------------------ #
    #  WhatsApp Deep-Link Generator                                        #
    # ------------------------------------------------------------------ #
    @api.model
    def get_whatsapp_link(self, alert_id):
        """
        Generate a wa.me deep-link pre-filled with the alert details.
        HR clicks the link → WhatsApp opens with the message ready to send.
        No WhatsApp API key or Meta Business account required.
        """
        alert = self.browse(int(alert_id))
        if not alert.exists():
            return {'success': False, 'url': '', 'message': 'Alert not found'}

        import urllib.parse
        emp = alert.employee_id
        phone = ''
        if emp:
            phone = (
                getattr(emp, 'mobile_phone', '') or
                getattr(emp, 'work_phone', '') or
                getattr(emp, 'phone', '') or ''
            )
            # Strip non-digits except leading +
            phone = ''.join(c for c in phone if c.isdigit() or c == '+')

        lines = [
            f"📊 *HR 360 Alert Notification*",
            f"",
            f"⚠️ *{(alert.severity or 'info').upper()} ALERT*",
            f"📋 {alert.message or ''}",
        ]
        if alert.employee_name:
            lines.append(f"👤 Employee: {alert.employee_name}")
        if alert.department:
            lines.append(f"🏢 Department: {alert.department}")
        if alert.due_date:
            lines.append(f"📅 Due: {alert.due_date}")
        if alert.detail:
            lines.append(f"ℹ️ {alert.detail}")
        lines.append(f"")
        lines.append(f"— Sent from HR 360 Dashboard Pro")

        text = urllib.parse.quote('\n'.join(lines))

        if phone:
            url = f"https://wa.me/{phone.lstrip('+').replace('+','')}?text={text}"
        else:
            # Open WhatsApp Web with no number — HR can choose the contact
            url = f"https://web.whatsapp.com/send?text={text}"

        return {
            'success': True,
            'url': url,
            'has_phone': bool(phone),
            'message': _('WhatsApp link generated for %s') % (alert.employee_name or 'employee'),
        }
