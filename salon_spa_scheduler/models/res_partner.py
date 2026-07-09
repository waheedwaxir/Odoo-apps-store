from odoo import fields, models, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    salon_allergies = fields.Text(string='Allergy Information', help="Customer's allergies or medical conditions.")
    salon_preferences = fields.Text(string='Customer Preferences', help="Customer's preferences or special requests.")
    salon_favorite_staff_id = fields.Many2one('salon.staff', string='Favorite Beautician', help="The customer's preferred beautician/staff member.")
    customer_history_ids = fields.One2many('salon.customer.history', 'partner_id', string='Service History', help="The customer's complete past service history logs.")

    @api.model
    def name_search(self, name='', domain=None, operator='ilike', limit=100):
        if name and not operator.startswith('^'):
            search_fields = []
            if 'phone' in self._fields:
                search_fields.append(('phone', operator, name))
            if 'mobile' in self._fields:
                search_fields.append(('mobile', operator, name))
            
            if search_fields:
                if len(search_fields) == 2:
                    phone_domain = ['|'] + search_fields
                else:
                    phone_domain = search_fields
                partners = self.search(phone_domain + (domain or []), limit=limit)
                if partners:
                    return [(p.id, p.display_name) for p in partners]
        return super().name_search(name=name, domain=domain, operator=operator, limit=limit)
