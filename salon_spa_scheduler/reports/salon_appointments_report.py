# -*- coding: utf-8 -*-
from odoo import api, models

class ReportSalonAppointments(models.AbstractModel):
    _name = 'report.salon_spa_scheduler.report_salon_appointments_temp'
    _description = 'Salon Appointments Report Data Source'

    @api.model
    def _get_report_values(self, docids, data=None):
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        branch_ids = data.get('branch_ids') or []
        staff_ids = data.get('staff_ids') or []
        
        # Build states list
        states = []
        if data.get('filter_draft'): states.append('draft')
        if data.get('filter_confirmed'): states.append('confirmed')
        if data.get('filter_progress'): states.append('progress')
        if data.get('filter_done'): states.append('done')
        if data.get('filter_cancel'): states.append('cancel')

        domain = [
            ('start_datetime', '>=', date_from),
            ('start_datetime', '<=', f"{date_to} 23:59:59"),
            ('state', 'in', states)
        ]
        if branch_ids:
            domain.append(('branch_id', 'in', branch_ids))
        if staff_ids:
            domain.extend(['|', ('staff_id', 'in', staff_ids), ('step_ids.staff_id', 'in', staff_ids)])

        appointments = self.env['salon.appointment'].sudo().search(domain, order='branch_id asc, start_datetime asc')

        # Compile summaries
        total_revenue = 0.0
        state_summary = {s: {'count': 0, 'revenue': 0.0} for s in states}
        branch_summary = {}

        # Prepopulate branches if filtered
        if branch_ids:
            branches = self.env['salon.branch'].sudo().browse(branch_ids)
            for b in branches:
                branch_summary[b.id] = {'name': b.name, 'count': 0, 'revenue': 0.0, 'appointments': []}
        else:
            all_branches = self.env['salon.branch'].sudo().search([])
            for b in all_branches:
                branch_summary[b.id] = {'name': b.name, 'count': 0, 'revenue': 0.0, 'appointments': []}

        # Catch-all branch for appointments with no branch
        branch_summary[False] = {'name': 'No Branch Assigned', 'count': 0, 'revenue': 0.0, 'appointments': []}

        for appt in appointments:
            appt_total = appt.service_id.list_price + sum(line.price_unit for line in appt.line_ids)
            total_revenue += appt_total
            
            # State summary
            if appt.state in state_summary:
                state_summary[appt.state]['count'] += 1
                state_summary[appt.state]['revenue'] += appt_total
                
            # Branch summary
            b_id = appt.branch_id.id if appt.branch_id else False
            if b_id not in branch_summary:
                branch_summary[b_id] = {'name': appt.branch_id.name or 'No Branch Assigned', 'count': 0, 'revenue': 0.0, 'appointments': []}
            branch_summary[b_id]['count'] += 1
            branch_summary[b_id]['revenue'] += appt_total
            branch_summary[b_id]['appointments'].append(appt)

        # Remove empty branch entries if we had no filter
        if not branch_ids:
            branch_summary = {k: v for k, v in branch_summary.items() if v['count'] > 0}

        staff_summary = {}
        if staff_ids:
            staffs = self.env['salon.staff'].sudo().browse(staff_ids)
            for st in staffs:
                staff_summary[st.id] = {'name': st.name}
        else:
            all_staffs = self.env['salon.staff'].sudo().search([])
            for st in all_staffs:
                staff_summary[st.id] = {'name': st.name}

        # Helper mapping for state label display
        state_labels = {
            'draft': 'Draft',
            'confirmed': 'Confirmed',
            'progress': 'In Progress',
            'done': 'Done',
            'cancel': 'Cancelled'
        }

        return {
            'doc_ids': docids,
            'doc_model': 'salon.report.wizard',
            'data': data,
            'appointments': appointments,
            'total_revenue': total_revenue,
            'state_summary': state_summary,
            'branch_summary': branch_summary,
            'staff_summary': staff_summary,
            'state_labels': state_labels,
        }
