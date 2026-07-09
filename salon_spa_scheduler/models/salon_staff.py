from odoo import api, fields, models, _

class SalonStaff(models.Model):
    _name = 'salon.staff'
    _description = 'Salon/Spa Staff'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    sequence = fields.Integer(default=10, tracking=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', tracking=True)
    partner_id = fields.Many2one('res.partner', string='Contact', required=True, ondelete='cascade', tracking=True)
    name = fields.Char(related='partner_id.name', store=True, readonly=False, tracking=True)
    image_1920 = fields.Image(related='partner_id.image_1920', readonly=False)
    user_id = fields.Many2one('res.users', string='Related User', tracking=True)
    service_ids = fields.Many2many('salon.service', string='Allowed Services', tracking=True)
    tip_ids = fields.One2many('salon.staff.tip', 'staff_id', string='Tips')
    total_unpaid_tips = fields.Float(string='Total Unpaid Tips', compute='_compute_unpaid_tips')
    active = fields.Boolean(default=True, tracking=True)
    color = fields.Integer(default=1)
    
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    job_title = fields.Char(string='Job Title')

    @api.depends('tip_ids.amount', 'tip_ids.state')
    def _compute_unpaid_tips(self):
        for staff in self:
            unpaid_tips = staff.tip_ids.filtered(lambda t: t.state == 'unpaid')
            staff.total_unpaid_tips = sum(unpaid_tips.mapped('amount'))

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            self.phone = self.employee_id.work_phone or self.employee_id.mobile_phone
            self.email = self.employee_id.work_email
            self.job_title = self.employee_id.job_title
            
            if self.employee_id.work_contact_id:
                self.partner_id = self.employee_id.work_contact_id.id
            elif self.employee_id.user_id and self.employee_id.user_id.partner_id:
                self.partner_id = self.employee_id.user_id.partner_id.id
            else:
                # search for partner with same name
                partner = self.env['res.partner'].search([('name', '=', self.employee_id.name)], limit=1)
                if not partner:
                    partner = self.env['res.partner'].create({
                        'name': self.employee_id.name,
                        'email': self.employee_id.work_email,
                        'phone': self.employee_id.work_phone or self.employee_id.mobile_phone,
                    })
                self.partner_id = partner.id
