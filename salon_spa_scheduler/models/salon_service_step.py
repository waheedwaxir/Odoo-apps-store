from datetime import timedelta
from odoo import fields, models, api

class SalonServiceStep(models.Model):
    _name = 'salon.service.step'
    _description = 'Salon Service Step'
    _order = 'sequence, id'

    service_id = fields.Many2one('salon.service', string='Service', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Step Name', required=True)
    duration_minutes = fields.Integer(string='Duration (Minutes)', default=30, required=True)
    need_staff = fields.Boolean(string='Need Staff?', default=True)


class SalonAppointmentStep(models.Model):
    _name = 'salon.appointment.step'
    _description = 'Salon Appointment Step'
    _order = 'sequence, id'

    appointment_id = fields.Many2one('salon.appointment', string='Appointment', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Step Name', required=True)
    duration_minutes = fields.Integer(string='Duration (Minutes)', default=30, required=True)
    need_staff = fields.Boolean(string='Need Staff?', default=True)
    staff_id = fields.Many2one('salon.staff', string='Beautician')
    start_datetime = fields.Datetime(string='Start Time', compute='_compute_step_times', store=True, readonly=False)
    end_datetime = fields.Datetime(string='End Time', compute='_compute_step_times', store=True, readonly=False)

    @api.depends('appointment_id.start_datetime', 'sequence', 'duration_minutes', 'appointment_id.step_ids', 'appointment_id.step_ids.duration_minutes', 'appointment_id.step_ids.sequence')
    def _compute_step_times(self):
        for step in self:
            appt = step.appointment_id
            if appt and appt.start_datetime:
                current_time = appt.start_datetime
                sorted_steps = appt.step_ids.sorted(lambda s: (s.sequence, s.id or 0))
                for s in sorted_steps:
                    s_start = current_time
                    s_end = current_time + timedelta(minutes=s.duration_minutes or 30)
                    if s == step:
                        step.start_datetime = s_start
                        step.end_datetime = s_end
                        break
                    current_time = s_end
            elif not step.start_datetime:
                step.start_datetime = False
                step.end_datetime = False
