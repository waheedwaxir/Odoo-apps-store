from odoo import fields, models

class SalonPackage(models.Model):
    _name = 'salon.package'
    _description = 'Service Package'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(required=True, tracking=True)
    description = fields.Text(tracking=True)
    price = fields.Float(required=True, tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    line_ids = fields.One2many('salon.package.line', 'package_id', string='Package Lines')

class SalonPackageLine(models.Model):
    _name = 'salon.package.line'
    _description = 'Package Line'

    package_id = fields.Many2one('salon.package', ondelete='cascade', required=True)
    service_id = fields.Many2one('salon.service', string='Service', required=True)
    quantity = fields.Integer(default=1)
