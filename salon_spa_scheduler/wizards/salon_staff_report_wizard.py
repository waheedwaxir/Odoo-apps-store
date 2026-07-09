# -*- coding: utf-8 -*-
from odoo import fields, models, api

class SalonStaffReportWizard(models.TransientModel):
    _name = 'salon.staff.report.wizard'
    _description = 'Salon Employee Performance Report Wizard'

    date_from = fields.Date(string='Start Date', required=True, default=fields.Date.context_today)
    date_to = fields.Date(string='End Date', required=True, default=fields.Date.context_today)
    staff_ids = fields.Many2many('salon.staff', string='Employees')
    branch_ids = fields.Many2many('salon.branch', string='Branches')

    def action_print_staff_report(self):
        data = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'staff_ids': self.staff_ids.ids,
            'branch_ids': self.branch_ids.ids,
        }
        return self.env.ref('salon_spa_scheduler.action_report_salon_staff_performance_pdf').report_action(self, data=data)
