# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    salon_start_hour = fields.Integer(string="Scheduler Start Hour", default=8)
    salon_end_hour = fields.Integer(string="Scheduler End Hour", default=22)
    salon_max_cancellations = fields.Integer(string="Max Cancellations Allowed", default=3)
    salon_allow_done_without_payment = fields.Boolean(
        string="Allow Done Without POS Payment",
        default=False,
        help="Let staff mark an appointment as Done before it has been paid "
             "in Point of Sale, for clients who pay at a later visit. "
             "\"Send to POS\" stays available on the appointment afterwards "
             "so it can still be charged once the client pays.")
    salon_allow_edit_done_staff = fields.Boolean(
        string="Managers Can Edit Bookings After Start",
        default=False,
        help="The Beauticians & Services lines of a booking can always be "
             "edited until it starts (Draft, Confirmed). With this on, a Salon "
             "manager may also edit them once it is In Progress or Done, as "
             "long as it is not paid in Point of Sale - beautician, service, "
             "time, price, notes, add or remove lines - to correct a mistake. "
             "On a Done booking the Sales History and commissions follow.")
    salon_allow_reset_cancelled = fields.Boolean(
        string="Managers Can Reset Cancelled to Draft",
        default=False,
        help="Let Salon Managers move a cancelled appointment back to Draft.")
    salon_general_notes_warning = fields.Boolean(
        string="Warn About General Notes",
        default=False,
        help="Show a customer's General Notes (allergies, preferences) in a "
             "popup when they are picked on a booking - once, not again each "
             "time the booking is opened.")
    salon_allow_extend_started = fields.Boolean(
        string="Add Services to Started Appointments",
        default=False,
        help="Let staff add another service to an appointment that is already "
             "confirmed or in progress - the customer is in the chair and asks "
             "for more. The booking is extended on the scheduler and the extra "
             "service is billed at checkout.")

    @api.constrains('salon_start_hour', 'salon_end_hour')
    def _check_salon_scheduler_hours(self):
        for company in self:
            if not (0 <= company.salon_start_hour <= 23):
                raise ValidationError(_("Scheduler start hour must be between 0 and 23."))
            if not (0 <= company.salon_end_hour <= 23):
                raise ValidationError(_("Scheduler end hour must be between 0 and 23."))
            if company.salon_start_hour >= company.salon_end_hour:
                raise ValidationError(_("Scheduler start hour must be strictly less than the end hour."))

    @api.constrains('salon_max_cancellations')
    def _check_salon_max_cancellations(self):
        for company in self:
            if company.salon_max_cancellations < 0:
                raise ValidationError(_("Max Cancellations Allowed must be 0 (disabled) or greater."))

    def _create_salon_appointment_sequence(self):
        """Ensure every company has its own SAL/ appointment sequence.

        New sequences start from the current value of the company-less fallback
        sequence so numbers do not collide with appointments already created
        under the shared sequence.
        """
        Sequence = self.env['ir.sequence'].sudo()
        fallback = Sequence.search(
            [('code', '=', 'salon.appointment'), ('company_id', '=', False)], limit=1)
        start = fallback.number_next_actual if fallback else 1
        for company in self:
            exists = Sequence.search([
                ('code', '=', 'salon.appointment'),
                ('company_id', '=', company.id),
            ], limit=1)
            if not exists:
                Sequence.create({
                    'name': 'Salon Appointment',
                    'code': 'salon.appointment',
                    'prefix': 'SAL/',
                    'padding': 5,
                    'company_id': company.id,
                    'number_next': start,
                })

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        companies._create_salon_appointment_sequence()
        return companies
