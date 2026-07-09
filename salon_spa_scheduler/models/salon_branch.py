from odoo import fields, models

class SalonBranch(models.Model):
    _name = 'salon.branch'
    _description = 'Salon Branch'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    phone = fields.Char(tracking=True)
    street = fields.Char(tracking=True)
    street2 = fields.Char(tracking=True)
    city = fields.Char(tracking=True)
    state_id = fields.Many2one('res.country.state', string='State', tracking=True)
    zip = fields.Char(tracking=True)
    country_id = fields.Many2one('res.country', string='Country', tracking=True)
