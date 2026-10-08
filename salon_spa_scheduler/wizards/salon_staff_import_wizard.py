# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class SalonStaffImportWizard(models.TransientModel):
    _name = 'salon.staff.import.wizard'
    _description = 'Import Employees as Salon Staff'

    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company)
    employee_ids = fields.Many2many(
        'hr.employee', string='Employees to Import',
        domain=lambda self: [('id', 'not in', self._linked_employee_ids())],
        help="Pick the employees to add as beauticians / staff. Employees that "
             "are already linked to a staff record are not listed.")

    @api.model
    def _linked_employee_ids(self):
        """hr.employee ids already tied to a salon.staff record (incl. archived)."""
        return self.env['salon.staff'].with_context(active_test=False).search(
            [('employee_id', '!=', False)]).employee_id.ids

    def _prepare_staff_vals(self, employee):
        """Mirror salon.staff._onchange_employee_id for a fresh record."""
        partner = employee.work_contact_id
        if not partner and employee.user_id:
            partner = employee.user_id.partner_id
        if not partner:
            partner = self.env['res.partner'].search([('name', '=', employee.name)], limit=1)
        if not partner:
            partner = self.env['res.partner'].create({
                'name': employee.name,
                'email': employee.work_email or False,
                'phone': employee.work_phone or employee.mobile_phone or False,
            })
        return {
            'employee_id': employee.id,
            'company_id': (self.company_id or employee.company_id or self.env.company).id,
            'partner_id': partner.id,
            'user_id': employee.user_id.id if employee.user_id else False,
            'phone': employee.work_phone or employee.mobile_phone or False,
            'email': employee.work_email or False,
            'job_title': employee.job_title or False,
            'job_id': employee.job_id.id or False,
        }

    def action_import(self):
        self.ensure_one()
        Staff = self.env['salon.staff']
        already_linked = set(self._linked_employee_ids())
        created = Staff.browse()
        for employee in self.employee_ids:
            if employee.id in already_linked:
                continue
            created |= Staff.create(self._prepare_staff_vals(employee))

        if not created:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Nothing imported"),
                    'message': _("The selected employees are already staff members."),
                    'type': 'warning',
                    'sticky': False,
                },
            }
        return {
            'type': 'ir.actions.act_window',
            'name': _("Imported Staff"),
            'res_model': 'salon.staff',
            'view_mode': 'list,form',
            'domain': [('id', 'in', created.ids)],
            'target': 'current',
        }
