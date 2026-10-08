# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SalonAppointmentAddService(models.TransientModel):
    """Add one more service to an appointment that has already started."""
    _name = 'salon.appointment.add.service'
    _description = 'Add Service to Appointment'

    appointment_id = fields.Many2one('salon.appointment', required=True, readonly=True)
    company_id = fields.Many2one(related='appointment_id.company_id')
    partner_id = fields.Many2one(related='appointment_id.partner_id', string='Customer')
    current_end = fields.Datetime(related='appointment_id.end_datetime', string='Currently Ends')
    service_id = fields.Many2one(
        'salon.service', string='Service', required=True,
        domain="[('company_id', 'in', (company_id, False))]")
    currency_id = fields.Many2one(related='company_id.currency_id')
    price = fields.Monetary(
        string='Price', currency_field='currency_id', compute='_compute_price',
        help="The service's list price - what the added service is charged at.")
    staff_id = fields.Many2one(
        'salon.staff', string='Beautician',
        default=lambda self: self.env['salon.appointment'].browse(
            self.env.context.get('default_appointment_id')).staff_id)
    duration_minutes = fields.Integer(
        string='Duration (Minutes)', compute='_compute_duration_minutes',
        store=True, readonly=False)
    timing_mode = fields.Selection([
        ('sequential', 'After the last service'),
        ('parallel', 'At the same time as the last service'),
    ], string='When', default='sequential', required=True,
        help="After: the appointment gets longer. Same time: a second beautician "
             "works on the customer alongside the last service.")

    @api.depends('service_id')
    def _compute_price(self):
        for wiz in self:
            wiz.price = wiz.service_id.list_price

    @api.depends('service_id')
    def _compute_duration_minutes(self):
        for wiz in self:
            wiz.duration_minutes = int(round((wiz.service_id.duration or 0.5) * 60))

    def action_add(self):
        self.ensure_one()
        if self.duration_minutes <= 0:
            raise UserError(_("The duration must be greater than zero."))
        self.appointment_id._add_extra_service(
            self.service_id, self.staff_id, self.duration_minutes, self.timing_mode)
        return {'type': 'ir.actions.act_window_close'}
