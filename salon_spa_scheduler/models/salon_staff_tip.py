from odoo import models, fields, api

class SalonStaffTip(models.Model):
    _name = 'salon.staff.tip'
    _description = 'Salon Staff Tip'
    _order = 'date desc, id desc'

    name = fields.Char(string='Reference', compute='_compute_name', store=True)
    staff_id = fields.Many2one('salon.staff', string='Staff Member', required=True, index=True)
    amount = fields.Float(string='Tip Amount', required=True)
    order_id = fields.Many2one('pos.order', string='POS Order', ondelete='cascade')
    date = fields.Datetime(string='Date', default=fields.Datetime.now, required=True)
    state = fields.Selection([
        ('unpaid', 'Unpaid'),
        ('paid', 'Paid')
    ], string='Status', default='unpaid', required=True, tracking=True)

    @api.depends('staff_id', 'date', 'order_id')
    def _compute_name(self):
        for tip in self:
            order_ref = tip.order_id.pos_reference if tip.order_id else 'Manual'
            tip.name = f"Tip for {tip.staff_id.name or 'Unknown'} ({order_ref})"

    def action_mark_paid(self):
        self.write({'state': 'paid'})

    def action_mark_unpaid(self):
        self.write({'state': 'unpaid'})
