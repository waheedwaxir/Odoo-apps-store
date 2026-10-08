from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class TsMembership(models.Model):
    _name = 'ts.membership'
    _description = 'Customer Membership'
    _inherit = ['mail.thread']
    _rec_name = 'partner_id'
    _order = 'start_date desc, id desc'
    _check_company_auto = True

    company_id = fields.Many2one(
        'res.company', string='Company', required=True, index=True,
        default=lambda self: self.env.company, tracking=True)
    plan_id = fields.Many2one(
        'ts.membership.plan', string='Plan', required=True, tracking=True,
        check_company=True)
    partner_id = fields.Many2one(
        'res.partner', string='Customer', required=True, index=True, tracking=True)
    start_date = fields.Date(default=fields.Date.context_today, tracking=True)
    end_date = fields.Date(
        compute='_compute_end_date', store=True, readonly=False, tracking=True,
        help="Computed from the plan duration; you can change it manually.")
    state = fields.Selection([
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ], default='active', required=True, tracking=True)

    @api.depends('start_date', 'plan_id.duration_months')
    def _compute_end_date(self):
        for rec in self:
            months = rec.plan_id.duration_months
            if rec.start_date and months > 0:
                rec.end_date = rec.start_date + relativedelta(months=months)
            elif not rec.end_date:
                rec.end_date = False

    @api.depends('partner_id', 'plan_id')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.partner_id.name or 'New'} - {rec.plan_id.name or ''}"

    @api.model
    def _cron_expire_memberships(self):
        """Mark memberships whose end date has passed as expired."""
        self.search([
            ('state', '=', 'active'),
            ('end_date', '!=', False),
            ('end_date', '<', fields.Date.context_today(self)),
        ]).write({'state': 'expired'})

    @api.model
    def _get_member_plan(self, partner_id, company_id=False):
        """Plan giving the best discount to a customer, or an empty recordset."""
        if not partner_id:
            return self.env['ts.membership.plan']
        today = fields.Date.context_today(self)
        memberships = self.sudo().search([
            ('partner_id', '=', partner_id),
            ('state', '=', 'active'),
            ('company_id', '=', company_id or self.env.company.id),
            ('plan_id.active', '=', True),
            ('plan_id.discount_percentage', '>', 0),
            '|', ('start_date', '=', False), ('start_date', '<=', today),
            '|', ('end_date', '=', False), ('end_date', '>=', today),
        ])
        if not memberships:
            return self.env['ts.membership.plan']
        return max(memberships.plan_id, key=lambda p: p.discount_percentage)

    @api.model
    def get_pos_member_discount(self, partner_id, company_id=False):
        """Membership offer for a customer, used by the POS.

        Always returns the discount product; 'discount' is 0 when the customer has
        no active membership. The POS adds a separate discount line named after the
        plan once the services reach 'min_spend'.
        """
        company = company_id or self.env.company.id
        product = self.env.ref(
            'ts_membership_pos_discount.product_product_membership_discount',
            raise_if_not_found=False)
        res = {
            'discount_product_id': product.id if product else False,
            'discount_product_tmpl_id': product.product_tmpl_id.id if product else False,
            'discount': 0.0,
            'min_spend': 0.0,
            'name': '',
        }
        plan = self._get_member_plan(partner_id, company)
        if plan and product:
            res.update({
                'discount': plan.discount_percentage,
                'min_spend': plan.min_spend,
                'name': plan.name,
            })
        return res
