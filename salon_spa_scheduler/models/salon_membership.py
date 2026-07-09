from odoo import api, fields, models

class SalonMembership(models.Model):
    _name = 'salon.membership'
    _description = 'Membership Plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(required=True, tracking=True)
    plan_type = fields.Selection([
        ('silver', 'Silver'),
        ('gold', 'Gold'),
        ('platinum', 'Platinum')
    ], default='silver', tracking=True)
    duration_months = fields.Integer(default=12, tracking=True)
    price = fields.Float(tracking=True)
    discount_percentage = fields.Float(default=0.0, tracking=True)
    active = fields.Boolean(default=True, tracking=True)

class SalonMembershipLine(models.Model):
    _name = 'salon.membership.line'
    _description = 'Customer Membership'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'partner_id'

    membership_id = fields.Many2one('salon.membership', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True)
    start_date = fields.Date(default=fields.Date.context_today, tracking=True)
    end_date = fields.Date(tracking=True)
    state = fields.Selection([
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled')
    ], default='active', tracking=True)

    @api.depends('membership_id', 'partner_id')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.partner_id.name or 'New'} - {rec.membership_id.name or ''}"
