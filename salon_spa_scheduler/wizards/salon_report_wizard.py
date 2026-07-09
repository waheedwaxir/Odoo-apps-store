# -*- coding: utf-8 -*-
from odoo import fields, models, api

class SalonReportWizard(models.TransientModel):
    _name = 'salon.report.wizard'
    _description = 'Salon Report Wizard'

    date_from = fields.Date(string='Start Date', required=True, default=fields.Date.context_today)
    date_to = fields.Date(string='End Date', required=True, default=fields.Date.context_today)
    branch_ids = fields.Many2many('salon.branch', string='Branches')
    staff_ids = fields.Many2many('salon.staff', string='Employees')
    
    # State Filters
    filter_draft = fields.Boolean(string='Draft', default=True)
    filter_confirmed = fields.Boolean(string='Confirmed', default=True)
    filter_progress = fields.Boolean(string='In Progress', default=True)
    filter_done = fields.Boolean(string='Done', default=True)
    filter_cancel = fields.Boolean(string='Cancelled', default=False)

    def action_print_report(self):
        data = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'branch_ids': self.branch_ids.ids,
            'staff_ids': self.staff_ids.ids,
            'filter_draft': self.filter_draft,
            'filter_confirmed': self.filter_confirmed,
            'filter_progress': self.filter_progress,
            'filter_done': self.filter_done,
            'filter_cancel': self.filter_cancel,
        }
        return self.env.ref('salon_spa_scheduler.action_report_salon_appointments_pdf').report_action(self, data=data)
