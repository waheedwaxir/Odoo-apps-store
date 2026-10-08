from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    ts_membership_ids = fields.One2many(
        'ts.membership', 'partner_id', string='Memberships')
    ts_membership_summary = fields.Char(
        string='Membership Plans', compute='_compute_ts_membership_summary',
        help="Comma-separated list of the membership plans this customer holds.")

    @api.depends('ts_membership_ids.plan_id')
    def _compute_ts_membership_summary(self):
        for partner in self:
            names = partner.ts_membership_ids.plan_id.mapped('name')
            partner.ts_membership_summary = ', '.join(sorted(set(filter(None, names))))
