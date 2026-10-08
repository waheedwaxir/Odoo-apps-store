from odoo import fields, models


class TsMembershipPlan(models.Model):
    _name = 'ts.membership.plan'
    _description = 'Membership Plan'
    _inherit = ['mail.thread']
    _order = 'sequence, name'

    name = fields.Char(required=True, tracking=True)
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True, index=True,
        default=lambda self: self.env.company, tracking=True)
    plan_type = fields.Selection([
        ('silver', 'Silver'),
        ('gold', 'Gold'),
        ('platinum', 'Platinum'),
    ], string='Tier', default='silver', tracking=True)
    duration_months = fields.Integer(
        string='Duration (Months)', default=12, tracking=True,
        help="Used to compute the end date of a membership. 0 = no end date.")
    price = fields.Float(tracking=True)
    discount_percentage = fields.Float(string='Discount (%)', default=0.0, tracking=True)
    min_spend = fields.Float(
        string='Minimum Spend per Session', tracking=True,
        help="The discount is applied in the POS only once the services of the order "
             "reach this amount. 0 = no minimum.")
    active = fields.Boolean(default=True, tracking=True)
    membership_count = fields.Integer(compute='_compute_membership_count')

    def _compute_membership_count(self):
        data = self.env['ts.membership']._read_group(
            [('plan_id', 'in', self.ids)], ['plan_id'], ['__count'])
        counts = {plan.id: count for plan, count in data}
        for plan in self:
            plan.membership_count = counts.get(plan.id, 0)

    def action_view_memberships(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.name,
            'res_model': 'ts.membership',
            'view_mode': 'list,form',
            'domain': [('plan_id', '=', self.id)],
            'context': {'default_plan_id': self.id},
        }
