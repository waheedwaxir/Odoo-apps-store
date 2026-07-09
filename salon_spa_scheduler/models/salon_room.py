from odoo import fields, models

class SalonRoom(models.Model):
    _name = 'salon.room'
    _description = 'Chair'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(tracking=True)
    branch_id = fields.Many2one('salon.branch', string='Branch', required=True, tracking=True)
    capacity = fields.Integer(default=1, tracking=True)
    room_type = fields.Selection([
        ('styling', 'Styling Chair'),
        ('wash', 'Wash Chair'),
        ('waiting', 'Waiting Chair'),
        ('vip', 'VIP Chair')
    ], string='Chair Type', default='styling', tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    color = fields.Integer(default=4)
