# -*- coding: utf-8 -*-
from datetime import date, datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError




class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    blood_group = fields.Selection([
        ('A+', 'A+'), ('A-', 'A-'), ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'), ('O+', 'O+'), ('O-', 'O-')
    ], string="Blood Group")
    religion = fields.Char(string="Religion")
    emergency_contact_name = fields.Char(string="Emergency Contact Name")
    emergency_contact_phone = fields.Char(string="Emergency Contact Phone")
    emergency_contact_relation = fields.Char(string="Relation")

    @api.model_create_multi
    def create(self, vals_list):
        res = super(HrEmployee, self).create(vals_list)
        self.env['bus.bus']._sendone('hr_dashboard_updates', 'hr_dashboard_updates', {})
        return res

    def write(self, vals):
        res = super(HrEmployee, self).write(vals)
        self.env['bus.bus']._sendone('hr_dashboard_updates', 'hr_dashboard_updates', {})
        return res

    def unlink(self):
        res = super(HrEmployee, self).unlink()
        self.env['bus.bus']._sendone('hr_dashboard_updates', 'hr_dashboard_updates', {})
        return res

    def _get_timesheet_only_360_details(self, public_employee):
        """Return the safe profile shell used when only Timesheets is available."""
        return {
            'id': public_employee.id,
            'timesheet_only': True,
            'personal': {
                'photo_url': f'/web/image?model=hr.employee.public&id={public_employee.id}&field=avatar_128',
                'name': public_employee.name or '',
                'job_title': public_employee.job_id.name if public_employee.job_id else '',
                'employee_id': f"EMP-{public_employee.id:04d}",
                'work_email': public_employee.work_email or '',
                'work_phone': public_employee.work_phone or public_employee.mobile_phone or '',
                'private_email': '',
                'dob': '',
                'age': 0,
                'gender': 'Not available',
                'nationality': 'Not available',
                'blood_group': 'Not available',
                'marital': 'Not available',
                'religion': 'Not available',
                'address': '',
                'emergency_contact': 'Not available',
            },
            'employment': {
                'joining_date': '',
                'department': public_employee.department_id.name if public_employee.department_id else 'No Department',
                'manager': 'Not available',
                'coach': 'Not available',
                'company': public_employee.company_id.name if public_employee.company_id else '',
                'work_location': public_employee.work_location_id.name if public_employee.work_location_id else '',
                'resource_calendar': public_employee.resource_calendar_id.name if public_employee.resource_calendar_id else '',
                'attrition_risk': 0.0,
                'attrition_level': 'low',
            },
            'documents': [],
            'attendance': {
                'present_today': False,
                'check_in_time': '-',
                'check_out_time': '-',
                'weekly_hours': 0.0,
                'monthly_hours': 0.0,
                'late_count': 0,
                'absent_count': 0,
                'overtime_balance': '0.0 Hrs',
                'attendance_rate': '0%',
            },
            'leave': {
                'annual_balance': 0.0,
                'sick_balance': 0.0,
                'pending_requests': [],
                'recent_leaves': [],
            },
            'payroll': {'has_access': False, 'current_salary': 0.0, 'currency': '', 'allowances': '', 'payslips': []},
            'performance': {'rating': 0.0, 'rating_label': '', 'goals_completed': 0, 'warnings_count': 0, 'rewards_count': 0},
            'skills': [],
            'assets': [],
            'projects': {'active_projects_count': 0, 'open_tasks_count': 0, 'completion_rate': 0.0},
            'notes': '',
            'timeline': [],
        }


    @api.model
    def get_employee_360_details(self, employee_id):
        """
        Returns a comprehensive 13-Facet JSON package for the slide-over 360 Drawer modal.
        Loads data across all installed modules safely.
        """
        try:
            emp = self.browse(int(employee_id))
        except (TypeError, ValueError):
            emp = self.browse()
        if not emp.exists():
            return {'error': _('Employee is not available.')}

        try:
            emp.check_access('read')
        except AccessError:
            timesheet_context = self.env['hr.dashboard.metrics']._get_timesheet_employee_context(emp.id)
            if not timesheet_context or not self.env['account.analytic.line'].has_access('read'):
                return {'error': _('Employee is not available.')}
            _employee, public_employee, _is_own, _can_read_private, _can_manage = timesheet_context
            return self._get_timesheet_only_360_details(public_employee)

        personal = {
            'photo_url': f'/web/image?model=hr.employee&id={emp.id}&field=avatar_128',
            'name': emp.name or '',
            'job_title': getattr(emp, 'job_title', False) or getattr(getattr(emp, 'job_id', False), 'name', False) or '',
            'employee_id': getattr(emp, 'barcode', False) or f"EMP-{emp.id:04d}",
            'work_email': getattr(emp, 'work_email', '') or '',
            'work_phone': getattr(emp, 'work_phone', False) or getattr(emp, 'mobile_phone', False) or '',
            'private_email': getattr(emp, 'private_email', '') or '',
            'dob': str(emp.birthday) if getattr(emp, 'birthday', False) else '',
            'age': round((fields.Date.today() - emp.birthday).days / 365.25, 1) if getattr(emp, 'birthday', False) else 0,
            'gender': getattr(emp, 'gender', 'Not Specified') or 'Not Specified',
            'nationality': getattr(getattr(emp, 'country_id', False), 'name', False) or 'Not Specified',
            'blood_group': getattr(emp, 'blood_group', 'N/A') or 'N/A',
            'marital': getattr(emp, 'marital', 'N/A') or 'N/A',
            'religion': getattr(emp, 'religion', 'N/A') or 'N/A',
            'address': getattr(emp, 'private_street', False) or getattr(getattr(emp, 'work_location_id', False), 'name', '') or '',
            'emergency_contact': f"{getattr(emp, 'emergency_contact', getattr(emp, 'emergency_contact_name', 'N/A')) or 'N/A'} - {getattr(emp, 'emergency_phone', getattr(emp, 'emergency_contact_phone', '')) or ''}"
        }

        # Compute dynamic health and attrition without polluting hr.employee model
        dynamic_score = 90.0
        if 'hr.attendance' in self.env:
            work_days = len(self.env['hr.attendance'].search([('employee_id', '=', emp.id), ('check_in', '>=', fields.Datetime.now() - timedelta(days=30))]))
            dynamic_score = min(100.0, work_days * 4.5)
        dynamic_grade = 'A+' if dynamic_score >= 95 else ('A' if dynamic_score >= 85 else ('B' if dynamic_score >= 75 else 'C'))

        dynamic_risk = 15.0
        if emp.create_date and (fields.Datetime.now() - emp.create_date).days > 730:
            dynamic_risk += 20.0
        dynamic_level = 'high' if dynamic_risk >= 70 else ('medium' if dynamic_risk >= 40 else 'low')

        # Contract & probation information
        contract_type_name = getattr(getattr(emp, 'contract_type_id', False), 'name', False) or 'Not Set'
        trial_date_end_val = getattr(emp, 'trial_date_end', False)
        is_on_probation = bool(trial_date_end_val and trial_date_end_val >= fields.Date.today())
        if trial_date_end_val:
            contract_status = 'On Probation' if is_on_probation else 'Confirmed'
        else:
            contract_status = 'Permanent'

        employment = {
            'joining_date': str(emp.create_date.date()) if getattr(emp, 'create_date', False) else '',
            'department': getattr(getattr(emp, 'department_id', False), 'name', False) or 'No Department',
            'manager': getattr(getattr(emp, 'parent_id', False), 'name', False) or 'No Direct Manager',
            'coach': getattr(getattr(emp, 'coach_id', False), 'name', False) or 'None',
            'company': getattr(getattr(emp, 'company_id', False), 'name', False) or '',
            'work_location': getattr(getattr(emp, 'work_location_id', False), 'name', False) or 'HQ Office',
            'resource_calendar': getattr(getattr(emp, 'resource_calendar_id', False), 'name', False) or 'Standard 40h/Week',
            'attrition_risk': round(dynamic_risk, 1),
            'attrition_level': dynamic_level,
            'contract_type': contract_type_name,
            'trial_date_end': str(trial_date_end_val) if trial_date_end_val else '',
            'is_on_probation': is_on_probation,
            'contract_status': contract_status,
        }

        documents = []
        if hasattr(emp, 'passport_id') and emp.passport_id:
            documents.append({
                'name': 'Passport',
                'number': emp.passport_id,
                'expiry_date': str(emp.passport_expiry_date) if hasattr(emp, 'passport_expiry_date') and emp.passport_expiry_date else 'N/A',
                'status': 'green',
                'status_label': 'Safe'
            })
        if hasattr(emp, 'visa_no') and emp.visa_no:
            documents.append({
                'name': 'Visa / Residency',
                'number': emp.visa_no,
                'expiry_date': str(emp.visa_expire) if hasattr(emp, 'visa_expire') and emp.visa_expire else 'N/A',
                'status': 'green',
                'status_label': 'Safe'
            })
        if hasattr(emp, 'identification_id') and emp.identification_id:
            documents.append({
                'name': 'National ID',
                'number': emp.identification_id,
                'expiry_date': str(emp.id_expiry_date) if hasattr(emp, 'id_expiry_date') and emp.id_expiry_date else 'N/A',
                'status': 'green',
                'status_label': 'Safe'
            })

        # Dynamic attendance stats
        attendance = {
            'present_today': False,
            'check_in_time': 'Not Checked In',
            'check_out_time': '-',
            'weekly_hours': 0.0,
            'monthly_hours': 0.0,
            'late_count': 0,
            'absent_count': 0,
            'overtime_balance': '0.0 Hrs',
            'attendance_rate': '0%'
        }
        if 'hr.attendance' in self.env:
            today = fields.Date.today()
            today_start = datetime.combine(today, datetime.min.time())
            today_att = self.env['hr.attendance'].search([
                ('employee_id', '=', emp.id),
                ('check_in', '>=', today_start)
            ], order='check_in desc', limit=1)
            if today_att:
                attendance['present_today'] = True
                attendance['check_in_time'] = today_att.check_in.strftime('%H:%M:%S') if today_att.check_in else '-'
                if today_att.check_out:
                    attendance['check_out_time'] = today_att.check_out.strftime('%H:%M:%S')
                else:
                    attendance['check_out_time'] = 'Active In Office'

            thirty_days_ago = datetime.combine(today - timedelta(days=30), datetime.min.time())
            seven_days_ago = datetime.combine(today - timedelta(days=7), datetime.min.time())
            recent_atts = self.env['hr.attendance'].search([
                ('employee_id', '=', emp.id),
                ('check_in', '>=', thirty_days_ago)
            ])
            weekly_hrs = 0.0
            monthly_hrs = 0.0
            late_cnt = 0
            ot_hrs = 0.0
            work_days = len(recent_atts)
            for a in recent_atts:
                dur = (a.check_out - a.check_in).total_seconds() / 3600.0 if a.check_in and a.check_out else 0.0
                monthly_hrs += dur
                if a.check_in and a.check_in >= seven_days_ago:
                    weekly_hrs += dur
                if a.check_in and (a.check_in.hour > 9 or (a.check_in.hour == 9 and a.check_in.minute > 15)):
                    late_cnt += 1
                if dur > 8.0:
                    ot_hrs += (dur - 8.0)

            attendance['weekly_hours'] = round(weekly_hrs, 1)
            attendance['monthly_hours'] = round(monthly_hrs, 1)
            attendance['late_count'] = late_cnt
            attendance['overtime_balance'] = f"{'+' if ot_hrs >= 0 else ''}{round(ot_hrs, 1)} Hrs"
            att_rate = min(100.0, round((work_days / 22.0) * 100, 1)) if work_days > 0 else 0.0
            attendance['attendance_rate'] = f"{att_rate}%"

        # Dynamic leave stats
        leave = {
            'annual_balance': 0.0,
            'sick_balance': 0.0,
            'pending_requests': [],
            'recent_leaves': []
        }
        if 'hr.leave' in self.env:
            pending = self.env['hr.leave'].search([('employee_id', '=', emp.id), ('state', 'in', ['confirm', 'validate1'])], limit=5)
            for l in pending:
                leave['pending_requests'].append({
                    'id': l.id,
                    'type': l.holiday_status_id.name if l.holiday_status_id else 'Time Off',
                    'days': l.number_of_days,
                    'from_date': str(l.date_from.date()) if l.date_from else '',
                    'to_date': str(l.date_to.date()) if l.date_to else ''
                })
            recent = self.env['hr.leave'].search([('employee_id', '=', emp.id), ('state', '=', 'validate')], order='date_from desc', limit=5)
            for r in recent:
                leave['recent_leaves'].append({
                    'id': r.id,
                    'type': r.holiday_status_id.name if r.holiday_status_id else 'Time Off',
                    'days': r.number_of_days,
                    'from_date': str(r.date_from.date()) if r.date_from else '',
                    'to_date': str(r.date_to.date()) if r.date_to else ''
                })

        if 'hr.leave.allocation' in self.env:
            allocs = self.env['hr.leave.allocation'].search([('employee_id', '=', emp.id), ('state', '=', 'validate')])
            for a in allocs:
                name = (a.holiday_status_id.name or '').lower() if a.holiday_status_id else ''
                if 'sick' in name:
                    leave['sick_balance'] += (getattr(a, 'number_of_days', 0.0) or 0.0)
                else:
                    leave['annual_balance'] += (getattr(a, 'number_of_days', 0.0) or 0.0)

        payroll = {
            'has_access': self.env.user.has_group('hr.group_hr_manager') or self.env.user.id == emp.user_id.id,
            'current_salary': 0.0,
            'currency': emp.company_id.currency_id.symbol if emp.company_id and emp.company_id.currency_id else '$',
            'allowances': 'Standard Package',
            'payslips': []
        }
        if payroll['has_access']:
            if getattr(emp, 'contract_id', False):
                payroll['current_salary'] = getattr(emp.contract_id, 'wage', 0.0)
            if 'hr.payslip' in self.env:
                slips = self.env['hr.payslip'].search([('employee_id', '=', emp.id)], order='date_to desc', limit=3)
                for s in slips:
                    payroll['payslips'].append({
                        'id': s.id,
                        'name': s.name,
                        'date': str(s.date_to) if s.date_to else '',
                        'state': s.state,
                        'net_wage': getattr(s, 'net_wage', 0.0) or 0.0
                    })

        # Dynamic performance stats
        perf_score = getattr(emp, 'health_score', 90.0) or 90.0
        perf_rating = round(perf_score / 20.0, 1)
        perf_label = 'Exceeds Expectations' if perf_rating >= 4.5 else ('Meets Expectations' if perf_rating >= 3.5 else 'Needs Improvement')
        performance = {
            'rating': perf_rating,
            'rating_label': perf_label,
            'goals_completed': 0,
            'warnings_count': 0,
            'rewards_count': 0
        }
        if 'hr.appraisal' in self.env:
            apps = self.env['hr.appraisal'].search([('employee_id', '=', emp.id), ('state', '=', 'done')])
            performance['goals_completed'] = len(apps)

        # Dynamic skills
        skills = []
        if 'hr.employee.skill' in self.env:
            for sk in self.env['hr.employee.skill'].search([('employee_id', '=', emp.id)]):
                skills.append({
                    'name': sk.skill_id.name if sk.skill_id else 'Skill',
                    'level': sk.skill_level_id.name if sk.skill_level_id else 'Level',
                    'progress': getattr(sk.skill_level_id, 'level_progress', 50) or 50
                })

        # Dynamic assets
        assets = []
        if 'maintenance.equipment' in self.env:
            for eq in self.env['maintenance.equipment'].search([('employee_id', '=', emp.id)]):
                assets.append({
                    'name': eq.name,
                    'serial': eq.serial_no or 'N/A',
                    'assigned_date': str(eq.assign_date) if hasattr(eq, 'assign_date') and eq.assign_date else 'N/A',
                    'status': 'Assigned'
                })

        # Dynamic projects
        projects = {
            'active_projects_count': 0,
            'open_tasks_count': 0,
            'completion_rate': 0.0,
        }
        if 'project.task' in self.env and getattr(emp, 'user_id', False):
            user_tasks = self.env['project.task'].search([('user_ids', 'in', emp.user_id.ids)])
            open_tasks = user_tasks.filtered(lambda t: getattr(t.stage_id, 'fold', False) is False)
            closed_tasks = user_tasks.filtered(lambda t: getattr(t.stage_id, 'fold', False) is True)
            projects['open_tasks_count'] = len(open_tasks)
            projects['active_projects_count'] = len(set(user_tasks.mapped('project_id').ids))
            total_t = len(user_tasks)
            if total_t > 0:
                projects['completion_rate'] = round((len(closed_tasks) / float(total_t)) * 100, 1)

        notes = getattr(emp, 'notes', False) or getattr(emp, 'additional_note', False) or _("No confidential HR notes logged.")

        # ---- Employee Timeline: synthesise + retrieve ------------------
        timeline = []
        if 'hr.employee.timeline.event' in self.env:
            try:
                # Synthesise missing events from existing Odoo data (idempotent)
                self.env['hr.employee.timeline.event'].synthesise_timeline_for_employee(emp.id)
                # Retrieve all events for this employee, newest first
                events = self.env['hr.employee.timeline.event'].search(
                    [('employee_id', '=', emp.id)],
                    order='event_date desc, id desc',
                    limit=100
                )
                color_icon_map = {
                    'joining':         ('green',  '🟢'),
                    'promotion':       ('purple', '🏆'),
                    'transfer':        ('orange', '🔄'),
                    'salary_revision': ('blue',   '💰'),
                    'leave':           ('teal',   '🌴'),
                    'appraisal':       ('blue',   '📈'),
                    'training':        ('teal',   '🎓'),
                    'award':           ('purple', '⭐'),
                    'warning':         ('red',    '⚠️'),
                    'disciplinary':    ('red',    '🚨'),
                    'separation':      ('red',    '🚪'),
                    'note':            ('gray',   '📝'),
                }
                for ev in events:
                    color, icon = color_icon_map.get(ev.event_type, ('gray', '📌'))
                    timeline.append({
                        'id':          ev.id,
                        'date':        str(ev.event_date) if ev.event_date else '',
                        'type':        ev.event_type,
                        'type_label':  dict(self.env['hr.employee.timeline.event']._fields['event_type'].selection).get(ev.event_type, ev.event_type),
                        'title':       ev.title or '',
                        'description': ev.description or '',
                        'color':       ev.color or color,
                        'icon':        icon,
                        'days_ago':    ev.days_ago,
                        'is_synthetic': ev.is_synthetic,
                    })
            except Exception as e:
                import logging
                _logger = logging.getLogger(__name__)
                _logger.warning("Timeline synthesis error for employee %s: %s", emp.id, e)

        return {
            'id': emp.id,
            'personal': personal,
            'employment': employment,
            'documents': documents,
            'attendance': attendance,
            'leave': leave,
            'payroll': payroll,
            'performance': performance,
            'skills': skills,
            'assets': assets,
            'projects': projects,
            'notes': notes,
            'timeline': timeline
        }

    @api.model
    def get_employee_timesheet_dashboard(self, employee_id, period='this_month'):
        """Return a focused, record-rule-aware timesheet view for one employee."""
        metrics = self.env['hr.dashboard.metrics']
        employee_context = metrics._get_timesheet_employee_context(employee_id)
        if not employee_context:
            return metrics._empty_timesheet_dashboard(
                message=_('Employee is not available.'),
            )
        employee, _public_employee, is_own_employee, _can_read_private, can_manage_timesheets = employee_context

        today = fields.Date.today()
        period_options = {
            'this_week': (
                today - timedelta(days=today.weekday()),
                today,
                _('This week'),
            ),
            'last_month': (
                (today.replace(day=1) - timedelta(days=1)).replace(day=1),
                today.replace(day=1) - timedelta(days=1),
                _('Last month'),
            ),
            'this_quarter': (
                date(today.year, ((today.month - 1) // 3) * 3 + 1, 1),
                today,
                _('This quarter'),
            ),
            'last_30': (
                today - timedelta(days=29),
                today,
                _('Last 30 days'),
            ),
        }
        start_date, end_date, period_label = period_options.get(
            period,
            (today.replace(day=1), today, _('This month')),
        )
        dashboard = metrics._get_timesheet_dashboard(
            employee,
            start_date,
            end_date,
            include_missing=False,
            include_employee_details=False,
        )
        can_log_for_employee = (
            is_own_employee
            or can_manage_timesheets
        )
        dashboard.update({
            'employee_id': employee.id,
            'period_key': period if period in period_options else 'this_month',
            'period_label': period_label,
            'can_create': bool(dashboard['can_create'] and can_log_for_employee),
        })
        return dashboard

    def action_open_360_profile(self):
        """Smart button action from standard employee form view to open the OWL SPA focusing on this employee."""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'wu_hr_employee360.DashboardClientAction',
            'params': {'open_employee_id': self.id}
        }
