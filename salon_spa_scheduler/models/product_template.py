from odoo import fields, models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_a_salon = fields.Boolean(
        string='Is a Salon Product',
        default=False,
        help='Check this box if the product is related to salon/spa services.'
    )
