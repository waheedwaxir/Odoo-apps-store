# -*- coding: utf-8 -*-
from datetime import datetime, date, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError


class HrDashboardMetrics(models.Model):
    _name = 'hr.dashboard.metrics'
    _description = 'HR Employee 360 High-Speed Metrics & Aggregation Engine'
    _auto = False

    @api.model
    def _get_user_role(self):
        """
        Determine the current user's HR dashboard role.
        Returns: 'hr_manager' | 'hr_officer' | 'dept_manager' | 'employee'
        """
        user = self.env.user
        if user.has_group('hr.group_hr_manager') or user.has_group('base.group_system'):
            return 'hr_manager'
        if user.has_group('hr.group_hr_user'):
            return 'hr_officer'
        # Check if the user is a department manager
        emp = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
        if emp and emp.child_ids:
            return 'dept_manager'
        return 'employee'

    @api.model
    def _empty_timesheet_dashboard(self, start_date=None, end_date=None, message=None):
        return {
            'available': 'account.analytic.line' in self.env,
            'allowed': False,
            'can_create': False,
            'can_view_team': False,
            'is_limited': True,
            'scope_label': _('No timesheet access'),
            'message': message or _('Timesheet data is unavailable.'),
            'period': {
                'date_from': str(start_date) if start_date else '',
                'date_to': str(end_date) if end_date else '',
            },
            'summary': {
                'total_hours': 0.0,
                'entry_count': 0,
                'logging_employees': 0,
                'active_employees': 0,
                'logging_rate': 0.0,
                'average_hours_per_logger': 0.0,
                'average_hours_per_entry': 0.0,
            },
            'daily': [],
            'by_project': [],
            'by_employee': [],
            'recent_entries': [],
            'missing_loggers': [],
        }

    @api.model
    def _get_timesheet_employee_context(self, employee_id):
        """Resolve a target through public employee access before reading time data."""
        try:
            target_id = int(employee_id)
        except (TypeError, ValueError):
            return False

        try:
            public_employee = self.env['hr.employee.public'].browse(target_id).exists()
            if not public_employee:
                return False
            public_employee.check_access('read')
        except AccessError:
            return False

        employee = self.env['hr.employee'].browse(target_id)
        is_own_employee = target_id == self.env.user.employee_id.id
        can_manage_timesheets = (
            self.env.user.has_group('hr_timesheet.group_hr_timesheet_approver')
            or self.env.user.has_group('hr_timesheet.group_timesheet_manager')
        )
        can_read_private_employee = employee.has_access('read')
        if not (is_own_employee or can_manage_timesheets or can_read_private_employee):
            return False
        return (
            employee,
            public_employee,
            is_own_employee,
            can_read_private_employee,
            can_manage_timesheets,
        )

    @api.model
    def _get_timesheet_dashboard(
        self,
        employees,
        start_date,
        end_date,
        include_missing=True,
        include_employee_details=True,
    ):
        """Build permission-aware time intelligence for the selected employees."""
        if start_date > end_date:
            start_date, end_date = end_date, start_date

        dashboard = self._empty_timesheet_dashboard(start_date, end_date)
        if 'account.analytic.line' not in self.env or 'project_id' not in self.env['account.analytic.line']._fields or not employees:
            dashboard['message'] = _('The Timesheets application is not installed.')
            return dashboard

        Timesheet = self.env['account.analytic.line']
        if not Timesheet.has_access('read'):
            dashboard['message'] = _('You need Timesheets access to view work logs.')
            return dashboard

        can_view_team = (
            self.env.user.has_group('hr_timesheet.group_timesheet_manager')
            or self.env.user.has_group('project.group_project_manager')
        )
        dashboard.update({
            'allowed': True,
            'can_create': Timesheet.has_access('create'),
            'can_view_team': can_view_team,
            'is_limited': not can_view_team,
            'scope_label': (
                _('Full team visibility') if can_view_team
                else _('Only timesheets you are allowed to access')
            ),
            'message': '',
            'summary': {
                'total_hours': 0.0,
                'entry_count': 0,
                'logging_employees': 0,
                'active_employees': len(employees),
                'logging_rate': 0.0,
                'average_hours_per_logger': 0.0,
                'average_hours_per_entry': 0.0,
            },
        })
        if not employees:
            return dashboard

        hour_uom = self.env.ref('uom.product_uom_hour', raise_if_not_found=False)

        def _to_hours(company, product_uom, amount):
            source_uom = product_uom or (company and company.timesheet_encode_uom_id) or hour_uom
            if not source_uom or not hour_uom:
                return round(float(amount or 0.0), 2)
            try:
                return round(
                    source_uom._compute_quantity(
                        amount or 0.0,
                        hour_uom,
                        raise_if_failure=False,
                    ),
                    2,
                )
            except (TypeError, ValueError):
                return round(float(amount or 0.0), 2)

        domain = [
            ('project_id', '!=', False),
            ('employee_id', 'in', employees.ids),
            ('date', '>=', start_date),
            ('date', '<=', end_date),
        ]

        try:
            total_hours = 0.0
            entry_count = 0
            total_groups = Timesheet._read_group(
                domain,
                ['company_id', 'product_uom_id'],
                ['unit_amount:sum', '__count'],
            )
            for company, product_uom, unit_amount, count in total_groups:
                total_hours += _to_hours(company, product_uom, unit_amount)
                entry_count += count or 0

            employee_totals = {}
            if include_employee_details:
                employee_groups = Timesheet._read_group(
                    domain,
                    ['employee_id', 'company_id', 'product_uom_id'],
                    ['unit_amount:sum', '__count'],
                )
                for employee, company, product_uom, unit_amount, count in employee_groups:
                    if not employee:
                        continue
                    values = employee_totals.setdefault(employee.id, {
                        'employee_id': employee.id,
                        'name': employee.name,
                        'department': employee.department_id.name if employee.department_id else '',
                        'photo_url': f'/web/image?model=hr.employee&id={employee.id}&field=avatar_128',
                        'hours': 0.0,
                        'entries': 0,
                    })
                    values['hours'] += _to_hours(company, product_uom, unit_amount)
                    values['entries'] += count or 0

            project_totals = {}
            project_groups = Timesheet._read_group(
                domain,
                ['project_id', 'company_id', 'product_uom_id'],
                ['unit_amount:sum', '__count'],
            )
            for project, company, product_uom, unit_amount, count in project_groups:
                if not project:
                    continue
                values = project_totals.setdefault(project.id, {
                    'project_id': project.id,
                    'name': project.name,
                    'hours': 0.0,
                    'entries': 0,
                })
                values['hours'] += _to_hours(company, product_uom, unit_amount)
                values['entries'] += count or 0

            daily = []
            trend_end = min(end_date, fields.Date.today())
            if trend_end >= start_date:
                trend_start = max(start_date, trend_end - timedelta(days=13))
                daily_totals = {}
                daily_groups = Timesheet._read_group(
                    domain + [('date', '>=', trend_start), ('date', '<=', trend_end)],
                    ['date:day', 'company_id', 'product_uom_id'],
                    ['unit_amount:sum'],
                )
                for day, company, product_uom, unit_amount in daily_groups:
                    if not day:
                        continue
                    day_value = fields.Date.to_date(day)
                    day_text = str(day_value)
                    daily_totals[day_text] = daily_totals.get(day_text, 0.0) + _to_hours(
                        company,
                        product_uom,
                        unit_amount,
                    )
                daily = [
                    {
                        'date': str(day),
                        'label': day.strftime('%d %b'),
                        'hours': round(daily_totals.get(str(day), 0.0), 2),
                    }
                    for day in (
                        trend_start + timedelta(days=offset)
                        for offset in range((trend_end - trend_start).days + 1)
                    )
                ]

            recent_entries = []
            for line in Timesheet.search(domain, order='date desc, id desc', limit=12):
                recent_entries.append({
                    'id': line.id,
                    'employee_id': line.employee_id.id if include_employee_details else False,
                    'employee_name': line.employee_id.name if include_employee_details else '',
                    'date': str(line.date),
                    'project': line.project_id.name,
                    'task': line.task_id.name if line.task_id else '',
                    'description': line.name or '',
                    'hours': _to_hours(line.company_id, line.product_uom_id, line.unit_amount),
                })
        except AccessError:
            return self._empty_timesheet_dashboard(
                start_date,
                end_date,
                _('You do not have permission to read these timesheets.'),
            )

        for values in employee_totals.values():
            values['hours'] = round(values['hours'], 2)
        for values in project_totals.values():
            values['hours'] = round(values['hours'], 2)

        logged_employee_count = (
            len(employee_totals) if include_employee_details else int(bool(entry_count))
        )
        dashboard['summary'] = {
            'total_hours': round(total_hours, 2),
            'entry_count': entry_count,
            'logging_employees': logged_employee_count,
            'active_employees': len(employees),
            'logging_rate': round((logged_employee_count / max(1, len(employees))) * 100, 1),
            'average_hours_per_logger': round(total_hours / max(1, logged_employee_count), 2),
            'average_hours_per_entry': round(total_hours / max(1, entry_count), 2),
        }
        if include_employee_details:
            dashboard['by_employee'] = sorted(
                employee_totals.values(),
                key=lambda values: (-values['hours'], values['name']),
            )[:8]
        dashboard['by_project'] = sorted(
            project_totals.values(),
            key=lambda values: (-values['hours'], values['name']),
        )[:8]
        dashboard['recent_entries'] = recent_entries
        dashboard['daily'] = daily
        if include_missing and can_view_team and include_employee_details:
            dashboard['missing_loggers'] = [
                {
                    'employee_id': employee.id,
                    'name': employee.name,
                    'department': employee.department_id.name if employee.department_id else '',
                    'photo_url': f'/web/image?model=hr.employee&id={employee.id}&field=avatar_128',
                }
                for employee in sorted(employees, key=lambda employee: employee.name or '')
                if employee.id not in employee_totals
            ][:8]
        return dashboard

    @api.model
    def get_dashboard_data(self, filters=None):
        if filters is None:
            filters = {}

        # Access control check
        ICP = self.env['ir.config_parameter'].sudo()
        access_managers_only = ICP.get_param('hr_dashboard.access_managers_only', default='False') == 'True'
        is_manager = self.env.user.has_group('hr.group_hr_manager') or self.env.user.has_group('base.group_system')
        is_admin = is_manager

        if access_managers_only and not is_manager:
            return {
                'is_admin': False,
                'access_managers_only': True,
                'is_restricted': True,
                'kpis': {},
                'charts': {
                    'by_department': {}, 'by_company': {}, 'by_manager': {}, 'by_job': {},
                    'by_gender': {}, 'by_nationality': {}, 'by_employment_type': {},
                    'by_age_group': {}, 'by_experience': {}, 'by_grade': {}
                },
                'attendance_dashboard': {
                    'present_today': 0, 'absent_today': 0, 'attendance_rate': 0, 'absent_rate': 0,
                    'wfh_today': 0, 'late_today': 0, 'present_emp_ids': [], 'late_today_emp_ids': [],
                    'early_checkout_emp_ids': [], 'overtime_today_emp_ids': [], 'missing_checkout_emp_ids': []
                },
                'leave_dashboard': {
                    'approved_leave': 0, 'annual_leave': 0, 'sick_leave': 0, 'unpaid_leave': 0,
                    'pending_leave': 0, 'on_leave_today_list': [], 'on_vacation_today_list': [],
                    'allocation_records': [], 'leave_records': []
                },
                'payroll_overview': {'total_payroll_cost': '$0', 'avg_cost_per_employee': '$0', 'this_month_payslips': 0},
                'department_overview': [],
                'employee_distribution': {'total': 0, 'male': 0, 'female': 0, 'male_pct': 0, 'female_pct': 0, 'locals': 0, 'locals_pct': 0, 'expats': 0, 'expats_pct': 0, 'nationalities': 0},
                'recruitment_dashboard': {'open_positions': 0, 'candidates': 0, 'interviews_today': 0, 'hired_month': 0, 'applicant_records': [], 'interview_records': []},
                'compliance_dashboard': {'expiring_list': []},
                'today_activities': {'birthdays_today': 0, 'interviews_scheduled': 0, 'work_anniversaries': 0, 'contracts_expiring': 0, 'employees_on_leave': 0, 'attendance_missing': 0},
                'top_performers': [],
                'leave_requests': [],
                'lifecycle_dashboard': {'lifecycle_records': []},
                'calendar_events': [],
                'employee_list': [],
                'timesheet_dashboard': self._empty_timesheet_dashboard(
                    message=_('Timesheet data is unavailable while dashboard access is restricted.')
                ),
            }

        # ---- Role-based scoping (dept managers only see their dept) ----
        user_role = self._get_user_role()
        if user_role == 'dept_manager':
            current_emp = self.env['hr.employee'].search(
                [('user_id', '=', self.env.uid)], limit=1
            )
            if current_emp and current_emp.department_id:
                filters['department_id'] = current_emp.department_id.id
        elif user_role == 'employee':
            current_emp = self.env['hr.employee'].search(
                [('user_id', '=', self.env.uid)], limit=1
            )
            if current_emp:
                filters['_employee_self_id'] = current_emp.id

        domain = []
        # Employee self-service: only their own record
        if filters.get('_employee_self_id'):
            domain.append(('id', '=', int(filters['_employee_self_id'])))
        else:
            if filters.get('employee_search'):
                domain.append('|')
                domain.append(('name', 'ilike', filters['employee_search']))
                domain.append(('user_id.name', 'ilike', filters['employee_search']))
            if filters.get('company_id') and 'company_id' in self.env['hr.employee']._fields:
                domain.append(('company_id', '=', int(filters['company_id'])))
            if filters.get('department_id') and 'department_id' in self.env['hr.employee']._fields:
                domain.append(('department_id', '=', int(filters['department_id'])))
            if filters.get('branch_id') and 'branch_id' in self.env['hr.employee']._fields:
                domain.append(('branch_id', '=', int(filters['branch_id'])))
            if filters.get('manager_id') and 'parent_id' in self.env['hr.employee']._fields:
                domain.append(('parent_id', '=', int(filters['manager_id'])))
            if filters.get('job_id') and 'job_id' in self.env['hr.employee']._fields:
                domain.append(('job_id', '=', int(filters['job_id'])))
            if filters.get('gender') and 'gender' in self.env['hr.employee']._fields:
                domain.append(('gender', '=', filters['gender']))
            if filters.get('nationality') and 'country_id' in self.env['hr.employee']._fields:
                domain.append(('country_id.name', 'ilike', filters['nationality']))
            if filters.get('employment_type') and 'employee_type' in self.env['hr.employee']._fields:
                domain.append(('employee_type', '=', filters['employment_type']))
            if filters.get('employment_status'):
                # 'probation' | 'new_joiner' | 'confirmed' | 'resigned'
                status = filters['employment_status']
                if status == 'probation' and 'hr.contract' in self.env:
                    prob_ids = self.env['hr.contract'].search([
                        ('trial_date_end', '>=', fields.Date.today()),
                        ('state', '=', 'open')
                    ]).mapped('employee_id.id')
                    domain.append(('id', 'in', prob_ids))
                elif status == 'new_joiner':
                    thirty_days_ago = fields.Date.today() - timedelta(days=30)
                    domain.append(('create_date', '>=', thirty_days_ago))
            if filters.get('hire_date_from'):
                try:
                    hdf = filters['hire_date_from']
                    if isinstance(hdf, str):
                        hdf = datetime.strptime(hdf, '%Y-%m-%d').date()
                    domain.append(('create_date', '>=', hdf))
                except Exception:
                    pass
            if filters.get('hire_date_to'):
                try:
                    hdt = filters['hire_date_to']
                    if isinstance(hdt, str):
                        hdt = datetime.strptime(hdt, '%Y-%m-%d').date()
                    domain.append(('create_date', '<=', hdt))
                except Exception:
                    pass

        Employee = self.env['hr.employee']
        employees = Employee.search(domain)
        total_count = len(employees)

        today = fields.Date.today()
        # Compute dynamic date range based on date_filter parameter (20 options + custom)
        date_filter = filters.get('date_filter', 'this_month')
        start_date = today
        end_date = today

        if date_filter == 'today':
            start_date = today
            end_date = today
        elif date_filter == 'yesterday':
            start_date = today - timedelta(days=1)
            end_date = today - timedelta(days=1)
        elif date_filter == 'last_7':
            start_date = today - timedelta(days=7)
            end_date = today
        elif date_filter == 'last_15':
            start_date = today - timedelta(days=15)
            end_date = today
        elif date_filter == 'last_30':
            start_date = today - timedelta(days=30)
            end_date = today
        elif date_filter == 'last_60':
            start_date = today - timedelta(days=60)
            end_date = today
        elif date_filter == 'last_90':
            start_date = today - timedelta(days=90)
            end_date = today
        elif date_filter == 'last_180':
            start_date = today - timedelta(days=180)
            end_date = today
        elif date_filter == 'last_365':
            start_date = today - timedelta(days=365)
            end_date = today
        elif date_filter == 'this_week':
            start_date = today - timedelta(days=today.weekday())
            end_date = start_date + timedelta(days=6)
        elif date_filter == 'last_week':
            end_date = today - timedelta(days=today.weekday() + 1)
            start_date = end_date - timedelta(days=6)
        elif date_filter == 'this_month':
            start_date = today.replace(day=1)
            next_month = today.replace(day=28) + timedelta(days=4)
            end_date = next_month - timedelta(days=next_month.day)
        elif date_filter == 'last_month':
            end_date = today.replace(day=1) - timedelta(days=1)
            start_date = end_date.replace(day=1)
        elif date_filter == 'this_quarter':
            quarter = (today.month - 1) // 3
            start_date = date(today.year, 3 * quarter + 1, 1)
            next_quarter = date(today.year + (1 if quarter == 3 else 0), (3 * (quarter + 1) + 1) % 12 or 12, 1)
            end_date = next_quarter - timedelta(days=1)
        elif date_filter == 'last_quarter':
            quarter = (today.month - 1) // 3
            if quarter == 0:
                start_date = date(today.year - 1, 10, 1)
                end_date = date(today.year - 1, 12, 31)
            else:
                start_date = date(today.year, 3 * (quarter - 1) + 1, 1)
                next_quarter = date(today.year, 3 * quarter + 1, 1)
                end_date = next_quarter - timedelta(days=1)
        elif date_filter == 'this_year':
            start_date = date(today.year, 1, 1)
            end_date = date(today.year, 12, 31)
        elif date_filter == 'last_year':
            start_date = date(today.year - 1, 1, 1)
            end_date = date(today.year - 1, 12, 31)
        elif date_filter == 'next_7':
            start_date = today
            end_date = today + timedelta(days=7)
        elif date_filter == 'next_30':
            start_date = today
            end_date = today + timedelta(days=30)
        elif date_filter == 'custom':
            if filters.get('start_date'):
                start_date = fields.Date.from_string(filters['start_date'])
            if filters.get('end_date'):
                end_date = fields.Date.from_string(filters['end_date'])

        today_start = datetime.combine(start_date, datetime.min.time())
        today_end = datetime.combine(end_date, datetime.max.time())

        present_emp_ids = set()
        checked_in_ids = set()
        checked_out_ids = set()
        late_today_emp_ids = set()
        early_checkout_emp_ids = set()
        overtime_today_emp_ids = set()
        missing_checkout_emp_ids = set()
        late_count = 0
        early_checkout_count = 0
        overtime_today_count = 0
        missing_checkout_count = 0

        if 'hr.attendance' in self.env and employees:
            today_atts = self.env['hr.attendance'].search([
                ('employee_id', 'in', employees.ids),
                ('check_in', '>=', today_start),
                ('check_in', '<=', today_end)
            ])
            for att in today_atts:
                present_emp_ids.add(att.employee_id.id)
                if hasattr(att, 'check_out') and not att.check_out:
                    checked_in_ids.add(att.employee_id.id)
                else:
                    checked_out_ids.add(att.employee_id.id)
                
                # Dynamic check for late attendance using shift start hour (default 9:00 AM + 15m grace)
                shift_start_hour = 9.0
                if att.employee_id.resource_calendar_id:
                    shift_start_hour = 9.0
                if att.check_in:
                    checkin_float = att.check_in.hour + (att.check_in.minute / 60.0)
                    if checkin_float > (shift_start_hour + 0.25):
                        late_count += 1
                        late_today_emp_ids.add(att.employee_id.id)
                if hasattr(att, 'check_out') and att.check_out:
                    checkout_float = att.check_out.hour + (att.check_out.minute / 60.0)
                    if checkout_float < 17.0 and (att.check_out - att.check_in).total_seconds() < 28800:
                        early_checkout_count += 1
                        early_checkout_emp_ids.add(att.employee_id.id)
                    elif (att.check_out - att.check_in).total_seconds() > 32400:
                        overtime_today_count += 1
                        overtime_today_emp_ids.add(att.employee_id.id)
                elif hasattr(att, 'check_in') and att.check_in:
                    if (fields.Datetime.now() - att.check_in).total_seconds() > 36000:
                        missing_checkout_count += 1
                        missing_checkout_emp_ids.add(att.employee_id.id)

        present_count = len(present_emp_ids)
        on_leave_count = 0
        on_vacation_count = 0
        today_leave_emp_ids = set()
        on_vacation_emp_ids = set()
        if 'hr.leave' in self.env and employees:
            today_leaves = self.env['hr.leave'].search([
                ('employee_id', 'in', employees.ids),
                ('state', '=', 'validate'),
                ('date_from', '<=', today_end),
                ('date_to', '>=', today_start)
            ])
            on_leave_count = len(today_leaves.mapped('employee_id'))
            today_leave_emp_ids = set(today_leaves.mapped('employee_id').ids)
            for lv in today_leaves:
                lv_name = (lv.holiday_status_id.name or '').lower() if lv.holiday_status_id else ''
                if any(k in lv_name for k in ['annual', 'vacation', 'casual']):
                    on_vacation_count += 1
                    if lv.employee_id:
                        on_vacation_emp_ids.add(lv.employee_id.id)

        absent_count = max(0, total_count - present_count - on_leave_count)

        # Dynamic contract & probation checks
        probation_count = 0
        contract_expiring_count = 0
        probation_emp_ids = set()
        contract_expiring_emp_ids = set()
        sixty_days_future = end_date + timedelta(days=60)
        thirty_days_ago = start_date - timedelta(days=30)
        if 'hr.contract' in self.env and employees:
            try:
                active_contracts = self.env['hr.contract'].search([
                    ('employee_id', 'in', employees.ids),
                    ('state', 'in', ['draft', 'open'])
                ])
                for c in active_contracts:
                    if hasattr(c, 'trial_date_end') and c.trial_date_end and c.trial_date_end >= today:
                        probation_count += 1
                        probation_emp_ids.add(c.employee_id.id)
                    if hasattr(c, 'date_end') and c.date_end and today <= c.date_end <= sixty_days_future:
                        contract_expiring_count += 1
                        contract_expiring_emp_ids.add(c.employee_id.id)
            except Exception as e:
                _logger.warning("Failed to query hr.contract states, falling back to Odoo 19 native fields: %s", str(e))
        
        # Odoo 19 native fallback using hr.employee/hr.version fields
        if not probation_emp_ids and not contract_expiring_emp_ids and employees:
            for emp in employees:
                if hasattr(emp, 'trial_date_end') and emp.trial_date_end and emp.trial_date_end >= today:
                    probation_count += 1
                    probation_emp_ids.add(emp.id)
                if hasattr(emp, 'contract_date_end') and emp.contract_date_end and today <= emp.contract_date_end <= sixty_days_future:
                    contract_expiring_count += 1
                    contract_expiring_emp_ids.add(emp.id)

        # Dynamic document expiry checks directly from hr.employee
        visa_expiring_count = 0
        id_expiring_count = 0
        visa_expiring_emp_ids = set()
        id_expiring_emp_ids = set()
        for emp in employees:
            if hasattr(emp, 'visa_expire') and emp.visa_expire and today <= emp.visa_expire <= sixty_days_future:
                visa_expiring_count += 1
                visa_expiring_emp_ids.add(emp.id)
            if hasattr(emp, 'id_expiry_date') and emp.id_expiry_date and today <= emp.id_expiry_date <= sixty_days_future:
                id_expiring_count += 1
                id_expiring_emp_ids.add(emp.id)

        # Birthday: match employees whose birthday (month/day) falls within the selected date range.
        # We compare by constructing this year's (or next year's) birthday date and checking the range.
        birthday_emp_ids = set()
        birthday_today_exact_emp_ids = set()  # Exact birthday TODAY
        for emp in employees:
            if not (getattr(emp, 'birthday', False) and emp.birthday):
                continue
            # Build this-year's birthday within the filter window
            bday = emp.birthday
            for yr in [start_date.year, start_date.year + 1]:
                try:
                    bday_this_year = bday.replace(year=yr)
                except ValueError:  # Feb 29 in non-leap year
                    bday_this_year = bday.replace(year=yr, day=28)
                if start_date <= bday_this_year <= end_date:
                    birthday_emp_ids.add(emp.id)
                    break
            # Check exact birthday today
            try:
                bday_today = bday.replace(year=today.year)
            except ValueError:
                bday_today = bday.replace(year=today.year, day=28)
            if bday_today == today:
                birthday_today_exact_emp_ids.add(emp.id)
        birthday_today_count = len(birthday_emp_ids)

        # Work Anniversaries: employees whose join date (create_date) anniversary falls on today
        work_anniversary_emp_ids = set()
        work_anniversary_period_emp_ids = set()
        for emp in employees:
            if not (getattr(emp, 'create_date', False) and emp.create_date):
                continue
            join_date = emp.create_date.date() if hasattr(emp.create_date, 'date') else emp.create_date
            if join_date.year == today.year:
                continue  # Skip employees who joined this year (< 1 yr)
            try:
                anniv_this_year = join_date.replace(year=today.year)
            except ValueError:
                anniv_this_year = join_date.replace(year=today.year, day=28)
            if anniv_this_year == today:
                work_anniversary_emp_ids.add(emp.id)
            if start_date <= anniv_this_year <= end_date:
                work_anniversary_period_emp_ids.add(emp.id)

        # New Joiners: employees whose join date (create_date) falls within the selected date range.
        new_joiner_emp_ids = set(employees.filtered(
            lambda e: e.create_date and start_date <= e.create_date.date() <= end_date
        ).ids)
        new_joiners_count = len(new_joiner_emp_ids)
        
        last_month_start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        last_month_end = today.replace(day=1) - timedelta(days=1)
        last_month_joined_count = len(employees.filtered(
            lambda e: e.create_date and last_month_start <= e.create_date.date() <= last_month_end
        ))

        # Leaving employees: departure_date within the selected date range.
        leaving_emp_ids = set(employees.filtered(
            lambda e: hasattr(e, 'departure_date') and e.departure_date
            and start_date <= e.departure_date <= end_date
        ).ids)
        leaving_this_month_count = len(leaving_emp_ids)

        resigned_emp_ids = set(employees.filtered(
            lambda e: hasattr(e, 'departure_reason_id') and e.departure_reason_id and 'resig' in (e.departure_reason_id.name or '').lower()
        ).ids)
        resigned_count = len(resigned_emp_ids)

        wfh_today_count = 0
        for emp in employees:
            if hasattr(emp, 'work_location_id') and emp.work_location_id:
                loc_name = (emp.work_location_id.name or '').lower()
                if any(k in loc_name for k in ['remote', 'home', 'wfh']):
                    wfh_today_count += 1

        total_for_pct = total_count if total_count > 0 else 1
        present_pct = round((present_count / total_for_pct) * 100)
        on_leave_pct = round((on_leave_count / total_for_pct) * 100)
        on_vacation_pct = round((on_vacation_count / total_for_pct) * 100)
        late_pct = round((late_count / total_for_pct) * 100)
        early_checkout_pct = round((early_checkout_count / total_for_pct) * 100)
        overtime_pct = round((overtime_today_count / total_for_pct) * 100)
        probation_pct = round((probation_count / total_for_pct) * 100)

        # vs last month calculations
        last_month_for_pct = last_month_joined_count if last_month_joined_count > 0 else 1
        new_joiners_diff_pct = round(((new_joiners_count - last_month_joined_count) / last_month_for_pct) * 100) if last_month_joined_count > 0 else (100 if new_joiners_count > 0 else 0)
        
        prev_total = total_count - new_joiners_count + resigned_count
        prev_total_for_pct = prev_total if prev_total > 0 else 1
        total_diff_pct = round(((total_count - prev_total) / prev_total_for_pct) * 100, 1) if prev_total > 0 else 0.0

        resigned_diff_pct = round(((resigned_count) / total_for_pct) * 100)

        kpis = {
            'total_employees': total_count,
            'present_today': present_count,
            'on_leave_today': on_leave_count,
            'on_vacation_today': on_vacation_count,
            'late_today': late_count,
            'early_checkout': early_checkout_count,
            'overtime_today': overtime_today_count,
            'missing_checkout': missing_checkout_count,
            'new_joiners': new_joiners_count,
            'leaving_this_month': leaving_this_month_count,
            'resigned_employees': resigned_count,
            'contract_expiring': contract_expiring_count,
            'visa_expiring': visa_expiring_count,
            'id_expiring': id_expiring_count,
            'birthday_today': birthday_today_count,
            'probation_employees': probation_count,
            'last_month_joined': last_month_joined_count,
            'checked_in': len(checked_in_ids),
            'checked_out': len(checked_out_ids),
            'wfh_today': wfh_today_count,
            'present_pct': _("%s%% of total") % present_pct,
            'on_leave_pct': _("%s%% of total") % on_leave_pct,
            'on_vacation_pct': _("%s%% of total") % on_vacation_pct,
            'late_pct': _("%s%% of total") % late_pct,
            'early_checkout_pct': _("%s%% of total") % early_checkout_pct,
            'overtime_pct': _("%s%% of total") % overtime_pct,
            'probation_pct': _("%s%% of total") % probation_pct,
            'total_emp_vs_last': _("%s %s%% vs last month") % ('↑' if total_diff_pct >= 0 else '↓', abs(total_diff_pct)),
            'new_joiners_vs_last': _("%s %s%% vs last month") % ('↑' if new_joiners_diff_pct >= 0 else '↓', abs(new_joiners_diff_pct)),
            'resigned_vs_last': _("%s %s%% of total") % ('↓' if resigned_count > 0 else '•', resigned_diff_pct) if resigned_count > 0 else _("0%% of total"),
            # Dynamic date period label shown in KPI card subtitles
            'date_label': {
                'today': _('Today'),
                'yesterday': _('Yesterday'),
                'this_week': _('This Week'),
                'last_week': _('Last Week'),
                'this_month': _('This Month'),
                'last_month': _('Last Month'),
                'this_quarter': _('This Quarter'),
                'last_quarter': _('Last Quarter'),
                'this_year': _('This Year'),
                'last_year': _('Last Year'),
            }.get(date_filter, f"{start_date.strftime('%b %d')} – {end_date.strftime('%b %d')}"),

        }

        charts = {
            'by_department': self._aggregate_chart(employees, lambda e: getattr(getattr(e, 'department_id', False), 'name', False) or 'No Department'),
            'by_company': self._aggregate_chart(employees, lambda e: getattr(getattr(e, 'company_id', False), 'name', False) or 'General Company'),
            'by_manager': self._aggregate_chart(employees, lambda e: getattr(getattr(e, 'parent_id', False), 'name', False) or 'No Manager', limit=8),
            'by_gender': self._aggregate_chart(employees, lambda e: (getattr(e, 'sex', False) or getattr(e, 'gender', False) or 'Not Specified').capitalize()),
            'by_nationality': self._aggregate_chart(employees, lambda e: getattr(getattr(e, 'country_id', False) or getattr(e, 'country_of_birth', False) or getattr(e, 'private_country_id', False), 'name', False) or 'Local / Unassigned', limit=6),
            'by_employment_type': self._aggregate_chart(employees, lambda e: getattr(e, 'employee_type', False) or 'Full-time'),
            'by_age_group': self._compute_age_groups(employees),
            'by_experience': self._compute_experience_groups(employees),
            'by_job': self._aggregate_chart(employees, lambda e: getattr(getattr(e, 'job_id', False), 'name', False) or 'No Job Title', limit=8),
            'by_grade': self._aggregate_chart(employees, lambda e: getattr(e, 'health_grade', False) or 'Grade A', limit=5)
        }

        # Dynamic weekly attendance calculation
        weekly_att = {'Mon': 0, 'Tue': 0, 'Wed': 0, 'Thu': 0, 'Fri': 0}
        top_late_list = []
        top_ot_list = []
        if 'hr.attendance' in self.env and employees:
            week_start = datetime.combine(today - timedelta(days=7), datetime.min.time())
            week_atts = self.env['hr.attendance'].search([
                ('employee_id', 'in', employees.ids),
                ('check_in', '>=', week_start),
                ('check_in', '<=', today_end)
            ])
            for a in week_atts:
                day_name = a.check_in.strftime('%a')
                if day_name in weekly_att:
                    weekly_att[day_name] += 1

            # Top late
            late_map = {}
            ot_map = {}
            for a in week_atts:
                if a.check_in and (a.check_in.hour > 9 or (a.check_in.hour == 9 and a.check_in.minute > 15)):
                    late_map[a.employee_id] = late_map.get(a.employee_id, 0) + 1
                if a.check_out and a.check_in:
                    dur = (a.check_out - a.check_in).total_seconds() / 3600.0
                    if dur > 8.5:
                        ot_map[a.employee_id] = ot_map.get(a.employee_id, 0.0) + (dur - 8.0)

            for emp, l_cnt in sorted(late_map.items(), key=lambda x: x[1], reverse=True)[:5]:
                top_late_list.append({
                    'name': emp.name,
                    'department': getattr(getattr(emp, 'department_id', False), 'name', False) or 'General',
                    'late_count': l_cnt,
                    'photo_url': f'/web/image?model=hr.employee&id={emp.id}&field=avatar_128'
                })
            for emp, ot_hrs in sorted(ot_map.items(), key=lambda x: x[1], reverse=True)[:5]:
                top_ot_list.append({
                    'name': emp.name,
                    'department': getattr(getattr(emp, 'department_id', False), 'name', False) or 'General',
                    'ot_hours': round(ot_hrs, 1),
                    'photo_url': f'/web/image?model=hr.employee&id={emp.id}&field=avatar_128'
                })

        attendance_dashboard = {
            'present_today': kpis['present_today'],
            'absent_today': absent_count,
            'late_today': kpis['late_today'],
            'wfh_today': kpis['wfh_today'],
            'attendance_rate': round((kpis['present_today'] / max(1, kpis['total_employees'])) * 100, 1),
            'absent_rate': round((absent_count / max(1, kpis['total_employees'])) * 100, 1),
            'weekly_attendance': weekly_att,
            'top_late_employees': top_late_list,
            'top_overtime_employees': top_ot_list
        }

        # Dynamic leave dashboard
        leave_bal = 0.0
        leave_taken = 0.0
        pending_leave_cnt = 0
        approved_leave_cnt = 0
        rejected_leave_cnt = 0
        sick_cnt = 0
        annual_cnt = 0
        unpaid_cnt = 0
        upcoming_cnt = 0
        top_leave_list = []
        leave_records = []  # Individual leave records for drill-down
        leave_trend_map = {'Jan': 0, 'Feb': 0, 'Mar': 0, 'Apr': 0, 'May': 0, 'Jun': 0, 'Jul': 0, 'Aug': 0, 'Sep': 0, 'Oct': 0, 'Nov': 0, 'Dec': 0}

        if 'hr.leave' in self.env and employees:
            year_start = today.replace(month=1, day=1)
            emp_leaves = self.env['hr.leave'].search([
                ('employee_id', 'in', employees.ids),
                ('date_from', '>=', datetime.combine(year_start, datetime.min.time()))
            ])
            for lv in emp_leaves:
                # Build common record dict for drill-down
                lv_type_name = lv.holiday_status_id.name if lv.holiday_status_id else 'Leave Request'
                lv_days = getattr(lv, 'number_of_days', 0.0) or 0.0
                lv_dept = getattr(getattr(lv.employee_id, 'department_id', False), 'name', False) or 'General'
                lv_record = {
                    'id': lv.id,
                    'employee_name': lv.employee_id.name,
                    'employee_id': lv.employee_id.id,
                    'leave_type': lv_type_name,
                    'date_from': lv.date_from.strftime('%d %b %Y') if lv.date_from else '-',
                    'date_to': lv.date_to.strftime('%d %b %Y') if lv.date_to else '-',
                    'days': round(lv_days, 1),
                    'state': lv.state,
                    'status_label': dict(lv._fields['state'].selection).get(lv.state, lv.state).capitalize() if hasattr(lv._fields.get('state', object()), 'selection') else lv.state,
                    'department': lv_dept,
                    'photo_url': f'/web/image?model=hr.employee&id={lv.employee_id.id}&field=avatar_128',
                    'categories': [],  # Will be tagged with applicable categories
                }

                if lv.state == 'confirm' or lv.state == 'validate1':
                    pending_leave_cnt += 1
                    lv_record['status_label'] = 'Pending'
                    lv_record['categories'].append('pending')
                elif lv.state == 'validate':
                    approved_leave_cnt += 1
                    lv_record['status_label'] = 'Approved'
                    lv_record['categories'].append('approved')
                    days = lv_days
                    leave_taken += days
                    m_name = lv.date_from.strftime('%b') if lv.date_from else 'Jan'
                    if m_name in leave_trend_map:
                        leave_trend_map[m_name] += int(days or 1)
                    if lv.date_from and lv.date_from.date() > today:
                        upcoming_cnt += 1
                        lv_record['categories'].append('upcoming')
                    
                    lv_name = (lv.holiday_status_id.name or '').lower() if lv.holiday_status_id else ''
                    if 'sick' in lv_name:
                        sick_cnt += 1
                        lv_record['categories'].append('sick')
                    elif 'annual' in lv_name or 'vacation' in lv_name:
                        annual_cnt += 1
                        lv_record['categories'].append('annual')
                    elif 'unpaid' in lv_name:
                        unpaid_cnt += 1
                        lv_record['categories'].append('unpaid')
                elif lv.state == 'refuse':
                    rejected_leave_cnt += 1
                    lv_record['status_label'] = 'Refused'
                    lv_record['categories'].append('refused')

                leave_records.append(lv_record)

            # Top leave employees
            l_map = {}
            for lv in emp_leaves.filtered(lambda l: l.state == 'validate'):
                l_map[lv.employee_id] = l_map.get(lv.employee_id, 0.0) + (getattr(lv, 'number_of_days', 0.0) or 0.0)
            for emp, l_days in sorted(l_map.items(), key=lambda x: x[1], reverse=True)[:5]:
                top_leave_list.append({
                    'name': emp.name,
                    'department': getattr(getattr(emp, 'department_id', False), 'name', False) or 'General',
                    'days_taken': round(l_days, 1),
                    'type': 'Approved Leaves'
                })

        # Build allocation records for Total Leave Balance drill-down
        allocation_records = []
        if 'hr.leave.allocation' in self.env and employees:
            allocs = self.env['hr.leave.allocation'].search([
                ('employee_id', 'in', employees.ids),
                ('state', '=', 'validate')
            ])
            leave_bal = sum(getattr(a, 'number_of_days', 0.0) or 0.0 for a in allocs) - leave_taken
            for alloc in allocs:
                alloc_days = getattr(alloc, 'number_of_days', 0.0) or 0.0
                allocation_records.append({
                    'id': alloc.id,
                    'employee_name': alloc.employee_id.name,
                    'employee_id': alloc.employee_id.id,
                    'leave_type': alloc.holiday_status_id.name if alloc.holiday_status_id else 'Allocation',
                    'allocated_days': round(alloc_days, 1),
                    'department': getattr(getattr(alloc.employee_id, 'department_id', False), 'name', False) or 'General',
                    'photo_url': f'/web/image?model=hr.employee&id={alloc.employee_id.id}&field=avatar_128',
                })

        leave_dashboard = {
            'leave_balance': round(leave_bal, 1),
            'leave_taken': round(leave_taken, 1),
            'pending_leave': pending_leave_cnt,
            'approved_leave': approved_leave_cnt,
            'rejected_leave': rejected_leave_cnt,
            'sick_leave': sick_cnt,
            'annual_leave': annual_cnt,
            'unpaid_leave': unpaid_cnt,
            'upcoming_leave': upcoming_cnt,
            'leave_trend': leave_trend_map,
            'department_leave': charts['by_department'],
            'top_leave_employees': top_leave_list,
            'leave_records': leave_records,
            'allocation_records': allocation_records,
        }

        # Dynamic payroll overview
        total_payroll = 0.0
        this_month_slips_cnt = 0
        paid_slips_cnt = 0
        unpaid_slips_cnt = 0
        cost_trend_map = {}
        if 'hr.payslip' in self.env and employees:
            m_start = today.replace(day=1)
            slips = self.env['hr.payslip'].search([
                ('employee_id', 'in', employees.ids),
                ('date_from', '>=', m_start)
            ])
            this_month_slips_cnt = len(slips)
            for s in slips:
                if s.state in ['done', 'paid']:
                    paid_slips_cnt += 1
                else:
                    unpaid_slips_cnt += 1
                total_payroll += getattr(s, 'net_wage', 0.0) or 0.0
        elif 'hr.contract' in self.env and employees:
            contracts = self.env['hr.contract'].search([
                ('employee_id', 'in', employees.ids),
                ('state', '=', 'open')
            ])
            total_payroll = sum(getattr(c, 'wage', 0.0) or 0.0 for c in contracts)

        avg_cost = total_payroll / max(1, total_count) if total_count > 0 else 0.0

        payroll_overview = {
            'total_payroll_cost': f"${round(total_payroll):,}",
            'avg_cost_per_employee': f"${round(avg_cost, 2):,}",
            'this_month_payslips': this_month_slips_cnt,
            'paid_payslips': paid_slips_cnt,
            'unpaid_payslips': unpaid_slips_cnt,
            'cost_trend': cost_trend_map or {today.strftime('%b'): round(total_payroll)}
        }

        # Dynamic alerts list
        alerts_list = []
        if kpis['contract_expiring'] > 0:
            alerts_list.append({'category': 'Contracts Expiring Soon', 'count': kpis['contract_expiring'], 'severity': 'warning', 'detail': 'Employment contracts ending within 60 days'})
        if kpis['visa_expiring'] > 0:
            alerts_list.append({'category': 'Visa Expiring Soon', 'count': kpis['visa_expiring'], 'severity': 'danger', 'detail': 'Requires ministry residency renewal'})
        if kpis['missing_checkout'] > 0:
            alerts_list.append({'category': 'Missing Attendance Checkout', 'count': kpis['missing_checkout'], 'severity': 'danger', 'detail': 'Employees missing checkout records today'})
        if kpis['probation_employees'] > 0:
            alerts_list.append({'category': 'Probation Evaluation Due', 'count': kpis['probation_employees'], 'severity': 'warning', 'detail': 'Active probation periods'})

        missing_bank_cnt = len(employees.filtered(lambda e: hasattr(e, 'bank_account_id') and not e.bank_account_id))
        if missing_bank_cnt > 0:
            alerts_list.append({'category': 'Missing Bank Account', 'count': missing_bank_cnt, 'severity': 'warning', 'detail': 'IBAN not provided for salary processing'})

        # Dynamic department overview
        department_overview = []
        all_depts = self.env['hr.department'].search([]) if 'hr.department' in self.env else []
        for d in all_depts:
            d_emps = employees.filtered(lambda e: getattr(e.department_id, 'id', False) == d.id)
            d_cnt = len(d_emps)
            if d_cnt > 0:
                d_present = len([e for e in d_emps if e.id in present_emp_ids])
                d_leave = len([e for e in d_emps if e.id in today_leave_emp_ids])
                d_cost = 0.0
                if 'hr.contract' in self.env:
                    d_contracts = self.env['hr.contract'].search([('employee_id', 'in', d_emps.ids), ('state', '=', 'open')])
                    d_cost = sum(getattr(c, 'wage', 0.0) or 0.0 for c in d_contracts)
                department_overview.append({
                    'dept': d.name,
                    'emp': d_cnt,
                    'att_pct': f"{round((d_present / max(1, d_cnt)) * 100)}%",
                    'leave_pct': f"{round((d_leave / max(1, d_cnt)) * 100)}%",
                    'cost': f"${round(d_cost):,}"
                })

        # Dynamic employee distribution
        male_cnt = len(employees.filtered(lambda e: (getattr(e, 'sex', '') or getattr(e, 'gender', '') or '').lower() == 'male'))
        female_cnt = len(employees.filtered(lambda e: (getattr(e, 'sex', '') or getattr(e, 'gender', '') or '').lower() == 'female'))

        def _is_local(e):
            company_country = self.env.company.country_id
            if not company_country:
                return False
            for fname in ['country_id', 'country_of_birth', 'private_country_id']:
                c = getattr(e, fname, False)
                if c and c.id == company_country.id:
                    return True
            return False

        locals_cnt = len(employees.filtered(_is_local))
        expats_cnt = max(0, total_count - locals_cnt)
        unique_nations = len(set((getattr(e, 'country_id', False) or getattr(e, 'country_of_birth', False) or getattr(e, 'private_country_id', False)).id for e in employees if (getattr(e, 'country_id', False) or getattr(e, 'country_of_birth', False) or getattr(e, 'private_country_id', False))))

        employee_distribution = {
            'total': total_count,
            'male': male_cnt,
            'male_pct': round((male_cnt / max(1, total_count)) * 100) if total_count > 0 else 0,
            'female': female_cnt,
            'female_pct': round((female_cnt / max(1, total_count)) * 100) if total_count > 0 else 0,
            'locals': locals_cnt,
            'locals_pct': round((locals_cnt / max(1, total_count)) * 100) if total_count > 0 else 0,
            'expats': expats_cnt,
            'expats_pct': round((expats_cnt / max(1, total_count)) * 100) if total_count > 0 else 0,
            'nationalities': unique_nations
        }

        # Dynamic recruitment dashboard
        open_pos = 0
        candidates_cnt = 0
        interviews_today_cnt = 0
        hired_month_cnt = kpis['new_joiners']
        stage_map = {'interview': 0, 'offer': 0, 'accepted': 0, 'rejected': 0}
        rec_trend = {}
        by_source_map = {}
        applicant_list = []

        # Precompute 6-month labels and dates
        months_list = []
        for i in range(5, -1, -1):
            m_num = today.month - i
            y_num = today.year
            while m_num < 1:
                m_num += 12
                y_num -= 1
            m_dt = date(y_num, m_num, 1)
            m_label = m_dt.strftime('%b')
            if m_num == 12:
                m_end = date(y_num + 1, 1, 1) - timedelta(days=1)
            else:
                m_end = date(y_num, m_num + 1, 1) - timedelta(days=1)
            months_list.append((m_label, m_dt, m_end))
            rec_trend[m_label] = 0

        if 'hr.job' in self.env:
            jobs = self.env['hr.job'].search([('no_of_recruitment', '>', 0)]) if 'no_of_recruitment' in self.env['hr.job']._fields else self.env['hr.job'].search([])
            open_pos = sum(getattr(j, 'no_of_recruitment', 1) or 1 for j in jobs)
        if 'hr.applicant' in self.env:
            apps = self.env['hr.applicant'].search([])
            candidates_cnt = len(apps)
            for a in apps:
                st_name = (a.stage_id.name or '').lower() if getattr(a, 'stage_id', False) else ''
                if 'interv' in st_name:
                    stage_map['interview'] += 1
                elif 'offer' in st_name:
                    stage_map['offer'] += 1
                elif 'hired' in st_name or 'accept' in st_name:
                    stage_map['accepted'] += 1
                elif 'refus' in st_name or 'reject' in st_name:
                    stage_map['rejected'] += 1
                
                src_name = a.source_id.name if getattr(a, 'source_id', False) and a.source_id.name else 'Direct / Career Page'
                by_source_map[src_name] = by_source_map.get(src_name, 0) + 1

                c_date = a.create_date if getattr(a, 'create_date', False) and a.create_date else fields.Datetime.now()
                c_dt_date = c_date.date() if hasattr(c_date, 'date') else today
                month_str = c_dt_date.strftime('%b')
                if month_str in rec_trend:
                    rec_trend[month_str] += 1

                applicant_list.append({
                    'id': a.id,
                    'name': getattr(a, 'partner_name', False) or getattr(a, 'name', 'Applicant') or 'Applicant',
                    'job': getattr(a.job_id, 'name', 'General Position') if getattr(a, 'job_id', False) else 'General Position',
                    'stage': getattr(a.stage_id, 'name', 'New Application') if getattr(a, 'stage_id', False) else 'New Application',
                    'source': src_name,
                    'create_date': c_date.strftime('%Y-%m-%d'),
                    'create_month': month_str,
                })
        else:
            by_source_map = {'Direct / Career Page': kpis['new_joiners']}
            rec_trend[today.strftime('%b')] = kpis['new_joiners']

        recruitment_dashboard = {
            'open_positions': open_pos,
            'candidates': candidates_cnt,
            'interviews_today': interviews_today_cnt,
            'hired_month': hired_month_cnt,
            'applicants': candidates_cnt,
            'interview': stage_map['interview'],
            'offer': stage_map['offer'],
            'accepted': stage_map['accepted'],
            'rejected': stage_map['rejected'],
            'new_joiners': kpis['new_joiners'],
            'cost_per_hire': '$0',
            'time_to_hire': 'N/A',
            'recruitment_trend': rec_trend,
            'by_source': by_source_map or {'Direct / Career Page': kpis['new_joiners']},
            'applicant_list': applicant_list,
        }

        # Dynamic compliance expiring list
        # Dynamic compliance expiring list directly from hr.employee
        expiring_list = []
        for emp in employees:
            if hasattr(emp, 'visa_expire') and emp.visa_expire and today <= emp.visa_expire <= sixty_days_future:
                days_left = (emp.visa_expire - today).days
                expiring_list.append({
                    'emp_name': emp.name,
                    'employee_id': emp.id,
                    'photo_url': f'/web/image?model=hr.employee&id={emp.id}&field=avatar_128',
                    'doc_type': 'Visa / Residency',
                    'doc_category': 'visa',
                    'doc_number': getattr(emp, 'visa_no', 'N/A') or 'N/A',
                    'expiry_date': emp.visa_expire.strftime('%Y-%m-%d'),
                    'days_left': days_left,
                    'department': getattr(getattr(emp, 'department_id', False), 'name', False) or 'General',
                    'status': 'Critical Alert' if days_left <= 15 else 'Warning'
                })
            if hasattr(emp, 'id_expiry_date') and emp.id_expiry_date and today <= emp.id_expiry_date <= sixty_days_future:
                days_left = (emp.id_expiry_date - today).days
                expiring_list.append({
                    'emp_name': emp.name,
                    'employee_id': emp.id,
                    'photo_url': f'/web/image?model=hr.employee&id={emp.id}&field=avatar_128',
                    'doc_type': 'National ID',
                    'doc_category': 'passport',
                    'doc_number': getattr(emp, 'identification_id', 'N/A') or 'N/A',
                    'expiry_date': emp.id_expiry_date.strftime('%Y-%m-%d'),
                    'days_left': days_left,
                    'department': getattr(getattr(emp, 'department_id', False), 'name', False) or 'General',
                    'status': 'Critical Alert' if days_left <= 15 else 'Warning'
                })

        # Add contract expiring employees to expiring_list
        for emp in employees.filtered(lambda e: e.id in contract_expiring_emp_ids):
            expiring_list.append({
                'emp_name': emp.name,
                'employee_id': emp.id,
                'photo_url': f'/web/image?model=hr.employee&id={emp.id}&field=avatar_128',
                'doc_type': 'Employment Contract',
                'doc_category': 'contract',
                'doc_number': '-',
                'expiry_date': '-',
                'days_left': '-',
                'department': getattr(getattr(emp, 'department_id', False), 'name', False) or 'General',
                'status': 'Renewal Due'
            })
        # Add probation ending employees to expiring_list
        for emp in employees.filtered(lambda e: e.id in probation_emp_ids):
            expiring_list.append({
                'emp_name': emp.name,
                'employee_id': emp.id,
                'photo_url': f'/web/image?model=hr.employee&id={emp.id}&field=avatar_128',
                'doc_type': 'Probation Period',
                'doc_category': 'probation',
                'doc_number': '-',
                'expiry_date': '-',
                'days_left': '-',
                'department': getattr(getattr(emp, 'department_id', False), 'name', False) or 'General',
                'status': 'Evaluation Due'
            })

        compliance_dashboard = {
            'visa_expiring': kpis['visa_expiring'],
            'passport_expiring': 0,
            'work_permit_expiring': 0,
            'medical_card_expiring': 0,
            'contract_renewal': kpis['contract_expiring'],
            'probation_end': kpis['probation_employees'],
            'expiring_list': expiring_list
        }

        today_activities = {
            'birthdays_today': birthday_today_count,
            'work_anniversaries': len(work_anniversary_period_emp_ids),
            'employees_on_leave': kpis['on_leave_today'],
            'interviews_scheduled': stage_map['interview'],
            'contracts_expiring': kpis['contract_expiring'],
            'attendance_missing': kpis['missing_checkout']
        }

        # Dynamic top performers based on recent attendance / tenure / appraisals
        top_performers = []
        for emp in employees[:5]:
            score = 90.0
            if 'hr.attendance' in self.env:
                work_days = len(self.env['hr.attendance'].search([('employee_id', '=', emp.id), ('check_in', '>=', fields.Datetime.now() - timedelta(days=30))]))
                score = min(100.0, max(75.0, work_days * 4.5))
            initials = ''.join([p[0] for p in emp.name.split() if p]).upper()[:2] if emp.name else 'EM'
            top_performers.append({
                'name': emp.name,
                'dept': getattr(getattr(emp, 'department_id', False), 'name', False) or 'General',
                'rating': round(score / 20.0, 1),
                'initials': initials,
                'color': 'bg-primary'
            })

        # Dynamic leave requests
        leave_requests = []
        if 'hr.leave' in self.env and employees:
            pending_lvs = self.env['hr.leave'].search([
                ('employee_id', 'in', employees.ids),
                ('state', 'in', ['confirm', 'validate1'])
            ], limit=10, order='date_from asc')
            for lv in pending_lvs:
                leave_requests.append({
                    'name': lv.employee_id.name,
                    'type': lv.holiday_status_id.name if lv.holiday_status_id else 'Leave Request',
                    'date': lv.date_from.strftime('%d %b') if lv.date_from else '-',
                    'status': 'Pending'
                })

        # Dynamic Employee List (All matching filtered records)
        employee_list = []
        for emp in employees:
            try:
                job = getattr(emp, 'job_title', False) or getattr(getattr(emp, 'job_id', False), 'name', False) or 'Employee'
                dept = getattr(getattr(emp, 'department_id', False), 'name', False) or 'General'
                manager = getattr(getattr(emp, 'parent_id', False), 'name', False) or '-'
                company = getattr(getattr(emp, 'company_id', False), 'name', False) or 'General Company'
                gender = (getattr(emp, 'sex', '') or getattr(emp, 'gender', '') or 'Not Specified').capitalize()
                nationality = getattr(getattr(emp, 'country_id', False) or getattr(emp, 'country_of_birth', False) or getattr(emp, 'private_country_id', False), 'name', False) or 'Local / Unassigned'
                employment_type = getattr(emp, 'employee_type', False) or 'Full-time'
                if getattr(emp, 'birthday', False) and emp.birthday:
                    age_val = (today - emp.birthday).days / 365.25
                    age_group = 'Gen Z (< 25)' if age_val < 25 else ('Gen Y (25 - 34)' if age_val <= 34 else ('Gen X (35 - 49)' if age_val <= 49 else 'Boomers (50+)'))
                else:
                    age_group = 'Unknown'
                if getattr(emp, 'create_date', False) and emp.create_date:
                    c_dt = emp.create_date.date() if hasattr(emp.create_date, 'date') else today
                    join_month = c_dt.strftime('%b')
                    years_val = (today - c_dt).days / 365.25
                    experience_group = '0 - 1 Yr' if years_val <= 1 else ('1 - 3 Yrs' if years_val <= 3 else ('3 - 5 Yrs' if years_val <= 5 else ('5 - 10 Yrs' if years_val <= 10 else '10+ Yrs')))
                else:
                    join_month = today.strftime('%b')
                    experience_group = '0 - 1 Yr'
                
                attrition_risk = 35.0 if (emp.create_date and (fields.Datetime.now() - emp.create_date).days > 730) else 15.0
                status = 'Present' if emp.id in present_emp_ids else ('On Leave' if emp.id in today_leave_emp_ids else 'Absent')
                bday_str = emp.birthday.strftime('%b %d') if getattr(emp, 'birthday', False) and emp.birthday else '-'
            except Exception:
                job, dept, manager, company, gender, nationality, employment_type, age_group, experience_group, join_month, attrition_risk, status, bday_str = 'Employee', 'General', '-', 'General Company', 'Not Specified', 'Local / Unassigned', 'Full-time', 'Unknown', '0 - 1 Yr', today.strftime('%b'), 15.0, 'Present', '-'

            employee_list.append({
                'id': emp.id,
                'name': emp.name,
                'photo_url': f'/web/image?model=hr.employee&id={emp.id}&field=avatar_128',
                'job_title': job,
                'department': dept,
                'manager': manager,
                'company': company,
                'gender': gender,
                'nationality': nationality,
                'employment_type': employment_type,
                'age_group': age_group,
                'experience_group': experience_group,
                'join_month': join_month,
                'attrition_risk': attrition_risk,
                'status': status,
                'birthday': bday_str,
                'is_birthday_this_month': emp.id in birthday_emp_ids,
                'is_birthday_today': emp.id in birthday_today_exact_emp_ids,
                'is_anniversary_today': emp.id in work_anniversary_emp_ids,
                'is_late': emp.id in late_today_emp_ids,
                'is_probation': emp.id in probation_emp_ids,
                'is_contract_expiring': emp.id in contract_expiring_emp_ids,
                'is_visa_expiring': emp.id in visa_expiring_emp_ids,
                'is_new_joiner': emp.id in new_joiner_emp_ids,
                'is_resigned': emp.id in resigned_emp_ids,
                'is_on_vacation': emp.id in on_vacation_emp_ids,
                'is_checked_in': emp.id in checked_in_ids,
                'is_checked_out': emp.id in checked_out_ids,
                'is_early_checkout': emp.id in early_checkout_emp_ids,
                'is_overtime': emp.id in overtime_today_emp_ids,
                'is_missing_checkout': emp.id in missing_checkout_emp_ids,
            })

        # Dynamic GPS map points
        gps_points = []
        if 'hr.work.location' in self.env:
            for loc in self.env['hr.work.location'].search([]):
                # If custom or standard lat/lng exist on work location or address
                lat = getattr(loc, 'latitude', False)
                lng = getattr(loc, 'longitude', False)
                if not lat and getattr(loc, 'address_id', False):
                    lat = getattr(loc.address_id, 'partner_latitude', False)
                    lng = getattr(loc.address_id, 'partner_longitude', False)
                if lat and lng:
                    gps_points.append({
                        'name': f"{loc.name} (Geofence Center)",
                        'lat': float(lat),
                        'lng': float(lng),
                        'type': 'location',
                        'radius': getattr(loc, 'geofence_radius', 500) or 500
                    })
        
        if 'hr.attendance' in self.env and employees:
            for att in self.env['hr.attendance'].search([('employee_id', 'in', employees.ids), ('check_in', '>=', today_start)]):
                lat = getattr(att, 'in_latitude', False) or getattr(att, 'latitude', False)
                lng = getattr(att, 'in_longitude', False) or getattr(att, 'longitude', False)
                if lat and lng:
                    gps_points.append({
                        'name': f"{att.employee_id.name} ({'Present' if not att.check_out else 'Checked Out'})",
                        'lat': float(lat),
                        'lng': float(lng),
                        'type': 'employee',
                        'time': att.check_in.strftime('%I:%M %p') if att.check_in else '-',
                        'is_breach': False
                    })

        lifecycle_dashboard = {
            'onboarding': kpis['new_joiners'],
            'probation': kpis['probation_employees'],
            'confirmation': max(0, total_count - kpis['probation_employees']),
            'promotions': 0,
            'transfers': 0,
            'salary_revisions': 0,
            'training': 0,
            'reviews': 0,
            'exit_interviews': 0,
            'resignations': kpis['resigned_employees'],
            'terminations': 0,
            'retirements': 0,
            'stages': {
                'Onboarding': kpis['new_joiners'],
                'Probation': kpis['probation_employees'],
                'Confirmed Core': max(0, total_count - kpis['probation_employees']),
                'Leadership': len(employees.filtered(lambda e: getattr(e, 'parent_id', False) and not getattr(e, 'child_ids', False))),
                'Offboarding': kpis['leaving_this_month']
            },
            'lifecycle_records': [],
        }
        # Build lifecycle records for drill-down
        for emp in employees:
            emp_job = getattr(emp, 'job_title', False) or getattr(getattr(emp, 'job_id', False), 'name', False) or 'Employee'
            emp_dept = getattr(getattr(emp, 'department_id', False), 'name', False) or 'General'
            emp_photo = f'/web/image?model=hr.employee&id={emp.id}&field=avatar_128'
            emp_cats = []
            if emp.id in new_joiner_emp_ids:
                emp_cats.append('onboarding')
            if emp.id in probation_emp_ids:
                emp_cats.append('probation')
            if emp.id not in probation_emp_ids and emp.id not in new_joiner_emp_ids:
                emp_cats.append('confirmation')
            if emp.id in resigned_emp_ids:
                emp_cats.append('resignations')
            if emp_cats:
                lifecycle_dashboard['lifecycle_records'].append({
                    'id': emp.id,
                    'name': emp.name,
                    'job_title': emp_job,
                    'department': emp_dept,
                    'photo_url': emp_photo,
                    'categories': emp_cats,
                    'status': 'Probation' if emp.id in probation_emp_ids else ('New Joiner' if emp.id in new_joiner_emp_ids else ('Resigned' if emp.id in resigned_emp_ids else 'Confirmed')),
                })

        # Dynamic calendar events
        calendar_events = []
        if 'calendar.event' in self.env:
            evs = self.env['calendar.event'].search([('start', '>=', today_start), ('start', '<=', today_start + timedelta(days=14))], limit=10)
            for ev in evs:
                calendar_events.append({
                    'title': ev.name or 'Event',
                    'date': ev.start.strftime('%Y-%m-%d') if ev.start else '-',
                    'type': 'meeting',
                    'icon': 'fa-calendar-check-o text-primary',
                    'emp_id': False
                })
        for emp in employees.filtered(lambda e: getattr(e, 'birthday', False) and e.birthday and e.birthday.month == today.month):
            try:
                bday_str = emp.birthday.replace(year=today.year).strftime('%Y-%m-%d')
            except Exception:
                bday_str = f"{today.year}-{emp.birthday.month:02d}-{emp.birthday.day:02d}"
            calendar_events.append({
                'title': f"{emp.name} - Birthday ({emp.birthday.strftime('%b %d')})",
                'date': bday_str,
                'type': 'birthday',
                'icon': 'fa-birthday-cake text-danger',
                'emp_id': emp.id
            })

        headcount_trend_map = {}
        hiring_trend_map = {}
        termination_trend_map = {}
        for m_label, m_dt, m_end in months_list:
            hc_cnt = len([e for e in employees if getattr(e, 'create_date', False) and (e.create_date.date() if hasattr(e.create_date, 'date') else today) <= m_end])
            if hc_cnt == 0 and total_count > 0:
                hc_cnt = total_count
            headcount_trend_map[m_label] = hc_cnt

            h_cnt = len([e for e in employees if getattr(e, 'create_date', False) and m_dt <= (e.create_date.date() if hasattr(e.create_date, 'date') else today) <= m_end])
            hiring_trend_map[m_label] = h_cnt

            t_cnt = len([e for e in employees if hasattr(e, 'departure_date') and getattr(e, 'departure_date', False) and m_dt <= (e.departure_date if isinstance(e.departure_date, date) else e.departure_date.date()) <= m_end])
            termination_trend_map[m_label] = t_cnt

        analytics_dashboard = {
            'headcount_trend': headcount_trend_map,
            'hiring_trend': hiring_trend_map,
            'termination_trend': termination_trend_map,
            'attrition_rate': round((kpis['resigned_employees'] / max(1, total_count)) * 100, 1) if total_count > 0 else 0.0,
            'retention_rate': round(100.0 - ((kpis['resigned_employees'] / max(1, total_count)) * 100), 1) if total_count > 0 else 100.0,
            'absenteeism_rate': round((absent_count / max(1, total_count)) * 100, 1) if total_count > 0 else 0.0,
            'avg_salary': f"${round(avg_cost):,}",
            'avg_tenure': f"{round(sum((datetime.now() - e.create_date).days / 365.25 for e in employees if getattr(e, 'create_date', False)) / max(1, total_count), 1)} Years" if total_count > 0 else '0 Years',
            'avg_age': f"{round(sum((today - e.birthday).days / 365.25 for e in employees if getattr(e, 'birthday', False)) / max(1, len([e for e in employees if getattr(e, 'birthday', False)])), 1)} Years" if any(getattr(e, 'birthday', False) for e in employees) else 'N/A',
            'gender_ratio': f"{round((male_cnt/max(1, total_count))*100)}% Male / {round((female_cnt/max(1, total_count))*100)}% Female" if total_count > 0 else 'N/A',
            'department_growth': {}
        }

        timesheet_dashboard = self._get_timesheet_dashboard(
            employees,
            start_date,
            end_date,
        )

        # ---- Smart Alert Engine ----------------------------------------
        smart_alerts = {'critical': [], 'warning': [], 'info': [], 'total': 0, 'unread': 0}
        if 'hr.smart.alert' in self.env:
            try:
                self.env['hr.smart.alert'].generate_smart_alerts(
                    employee_ids=employees.ids if employees else None
                )
                smart_alerts = self.env['hr.smart.alert'].get_alerts_summary()
            except Exception as e:
                import logging
                _logger = logging.getLogger(__name__)
                _logger.warning("Smart alert generation error: %s", e)

        can_edit = self.env.user.has_group('wu_hr_employee360.group_hr_dashboard_manager')

        return {
            'can_edit': can_edit,
            'kpis': kpis,
            'charts': charts,
            'attendance_dashboard': attendance_dashboard,
            'leave_dashboard': leave_dashboard,
            'payroll_overview': payroll_overview,
            'department_overview': department_overview,
            'employee_distribution': employee_distribution,
            'recruitment_dashboard': recruitment_dashboard,
            'compliance_dashboard': compliance_dashboard,
            'today_activities': today_activities,
            'top_performers': top_performers,
            'leave_requests': leave_requests,
            'lifecycle_dashboard': lifecycle_dashboard,
            'calendar_events': calendar_events,
            'alerts_list': alerts_list,
            'smart_alerts': smart_alerts,
            'analytics_dashboard': analytics_dashboard,
            'timesheet_dashboard': timesheet_dashboard,
            'employee_list': employee_list,
            'gps_points': gps_points,
            'timestamp': fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'is_admin': is_admin,
            'user_role': user_role,
            'active_filters': {k: v for k, v in filters.items() if v and not k.startswith('_')},
            'access_managers_only': access_managers_only,
            'installed_modules': {
                'timesheet': 'account.analytic.line' in self.env and 'project_id' in self.env['account.analytic.line']._fields,
                'leave': 'hr.leave' in self.env,
                'payroll': 'hr.payslip' in self.env,
                'recruitment': 'hr.applicant' in self.env,
                'performance': 'hr.appraisal' in self.env,
                'contracts': 'hr.contract' in self.env,
                'loan': 'hr.loan' in self.env,
                'documents': 'hr.employee.document' in self.env or 'documents.document' in self.env,
            },
            'is_restricted': False
        }

    @api.model
    def action_open_timesheet_form(self, timesheet_id=False):
        """Open an entry with the native Timesheets form, never Analytic Items."""
        Timesheet = self.env['account.analytic.line']
        form_view = self.env.ref('hr_timesheet.timesheet_view_form_user')
        if timesheet_id:
            try:
                line_id = int(timesheet_id)
            except (TypeError, ValueError):
                line_id = False
            line = Timesheet.search([('id', '=', line_id)], limit=1) if line_id else Timesheet.browse()
            if not line:
                raise AccessError(_('Timesheet entry is not available.'))
            action = self.env['ir.actions.act_window']._for_xml_id(
                'hr_timesheet.timesheet_action_all'
            )
            action.update({
                'res_id': line.id,
                'view_mode': 'form',
                'views': [(form_view.id, 'form')],
            })
            return action

        Timesheet.browse().check_access('create')
        action = self.env['ir.actions.act_window']._for_xml_id(
            'hr_timesheet.act_hr_timesheet_line'
        )
        action.update({
            'view_mode': 'form',
            'views': [(form_view.id, 'form')],
        })
        return action

    @api.model
    def action_open_employee_timesheets(self, employee_id):
        """Open the standard employee-scoped Timesheets action after access checks."""
        employee_context = self._get_timesheet_employee_context(employee_id)
        if not employee_context:
            raise AccessError(_('Employee is not available.'))
        employee, _public_employee, _is_own, _can_read_private, _can_manage = employee_context
        self.env['account.analytic.line'].browse().check_access('read')
        return employee.action_timesheet_from_employee()

    @api.model
    def toggle_dashboard_access(self, managers_only):
        if not (self.env.user.has_group('hr.group_hr_manager') or self.env.user.has_group('base.group_system')):
            raise UserError("Only Administrators can modify access control settings.")
        self.env['ir.config_parameter'].sudo().set_param('hr_dashboard.access_managers_only', str(managers_only))
        return True

    def _aggregate_chart(self, employees, key_func, limit=10):
        counts = {}
        for emp in employees:
            try:
                key = key_func(emp) or 'Others / Unassigned'
            except Exception:
                key = 'Others / Unassigned'
            counts[key] = counts.get(key, 0) + 1
        sorted_items = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        if len(sorted_items) > limit:
            top = dict(sorted_items[:limit])
            top['Others'] = sum(v for k, v in sorted_items[limit:])
            return top
        return dict(sorted_items)

    def _compute_age_groups(self, employees):
        today = fields.Date.today()
        groups = {'Gen Z (< 25)': 0, 'Gen Y (25 - 34)': 0, 'Gen X (35 - 49)': 0, 'Boomers (50+)': 0, 'Unknown': 0}
        for emp in employees:
            try:
                if getattr(emp, 'birthday', False):
                    age = (today - emp.birthday).days / 365.25
                    if age < 25:
                        groups['Gen Z (< 25)'] += 1
                    elif age <= 34:
                        groups['Gen Y (25 - 34)'] += 1
                    elif age <= 49:
                        groups['Gen X (35 - 49)'] += 1
                    else:
                        groups['Boomers (50+)'] += 1
                else:
                    groups['Unknown'] += 1
            except Exception:
                groups['Unknown'] += 1
        return groups

    def _compute_experience_groups(self, employees):
        today = fields.Date.today()
        groups = {'0 - 1 Yr': 0, '1 - 3 Yrs': 0, '3 - 5 Yrs': 0, '5 - 10 Yrs': 0, '10+ Yrs': 0}
        for emp in employees:
            try:
                if getattr(emp, 'create_date', False):
                    years = (datetime.now() - emp.create_date).days / 365.25
                    if years <= 1:
                        groups['0 - 1 Yr'] += 1
                    elif years <= 3:
                        groups['1 - 3 Yrs'] += 1
                    elif years <= 5:
                        groups['3 - 5 Yrs'] += 1
                    elif years <= 10:
                        groups['5 - 10 Yrs'] += 1
                    else:
                        groups['10+ Yrs'] += 1
                else:
                    groups['0 - 1 Yr'] += 1
            except Exception:
                groups['0 - 1 Yr'] += 1
        return groups

    @api.model
    def action_quick_checkin(self, employee_id):
        emp = self.env['hr.employee'].browse(int(employee_id))
        if not emp.exists():
            raise UserError(_("Employee record does not exist."))
        if 'hr.attendance' in self.env:
            last_att = self.env['hr.attendance'].search([
                ('employee_id', '=', emp.id),
                ('check_out', '=', False)
            ], limit=1)
            if last_att:
                last_att.check_out = fields.Datetime.now()
                return {'success': True, 'action': 'checked_out', 'message': _("%s successfully checked out.", emp.name)}
            else:
                self.env['hr.attendance'].create({
                    'employee_id': emp.id,
                    'check_in': fields.Datetime.now()
                })
                return {'success': True, 'action': 'checked_in', 'message': _("%s successfully checked in.", emp.name)}
        return {'success': False, 'message': _("Attendance module is not installed.")}

    @api.model
    def action_quick_leave(self, vals):
        if 'hr.leave' not in self.env:
            raise UserError(_("Time Off / Leave module (hr_holidays) is not installed."))
        emp_id = int(vals.get('employee_id'))
        holiday_status_id = int(vals.get('holiday_status_id'))
        date_from = vals.get('date_from')
        date_to = vals.get('date_to')
        leave = self.env['hr.leave'].create({
            'employee_id': emp_id,
            'holiday_status_id': holiday_status_id,
            'date_from': date_from,
            'date_to': date_to,
            'name': vals.get('reason', _("Created via Employee 360 Dashboard Pro"))
        })
        return {'success': True, 'leave_id': leave.id, 'message': _("Leave request created successfully.")}
