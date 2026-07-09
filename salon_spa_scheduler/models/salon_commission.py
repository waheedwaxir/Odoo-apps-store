from odoo import api, fields, models

class SalonCommission(models.Model):
    _name = 'salon.commission'
    _description = 'Staff Commission'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'
    _rec_name = 'staff_id'

    staff_id = fields.Many2one('salon.staff', string='Beautician/Staff', required=True, tracking=True)
    appointment_id = fields.Many2one('salon.appointment', string='Appointment', tracking=True)
    commission_amount = fields.Float(required=True, tracking=True)
    date = fields.Date(default=fields.Date.context_today, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('paid', 'Paid')
    ], default='draft', tracking=True)

    @api.depends('staff_id', 'commission_amount')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"Commission - {rec.staff_id.name or 'New'} ({rec.commission_amount})"

    def action_pay(self):
        self.write({'state': 'paid'})
