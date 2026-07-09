from odoo import api, fields, models

class SalonReview(models.Model):
    _name = 'salon.review'
    _description = 'Customer Review'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'
    _rec_name = 'appointment_id'

    partner_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True)
    staff_id = fields.Many2one('salon.staff', string='Staff/Beautician', tracking=True)
    appointment_id = fields.Many2one('salon.appointment', string='Appointment', tracking=True, domain="[('review_ids', '=', False)]")
    
    _appointment_uniq = models.Constraint(
        'unique(appointment_id)',
        "An appointment can only be reviewed once!",
    )
    rating = fields.Selection([
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5')
    ], required=True, string='Rating (1-5)', default='5', tracking=True)
    comment = fields.Text(tracking=True)
    date = fields.Date(default=fields.Date.context_today, tracking=True)

    @api.depends('appointment_id', 'partner_id')
    def _compute_display_name(self):
        for rec in self:
            name = ""
            if rec.appointment_id:
                name = rec.appointment_id.display_name or rec.appointment_id.name
            elif rec.partner_id:
                name = rec.partner_id.name
            rec.display_name = f"Review - {name or 'New'}"

    @api.onchange('appointment_id')
    def _onchange_appointment_id(self):
        if self.appointment_id:
            self.partner_id = self.appointment_id.partner_id
            self.staff_id = self.appointment_id.staff_id
