from odoo import fields, models, api

class SalonCustomerHistory(models.Model):
    _name = 'salon.customer.history'
    _description = 'Customer Service History'
    _order = 'date desc'

    partner_id = fields.Many2one('res.partner', string='Customer', required=True, ondelete='cascade')
    date = fields.Datetime(string='Date', required=True)
    service_name = fields.Char(string='Service/Product', required=True)
    staff_name = fields.Char(string='Staff/Employee')
    state = fields.Char(string='Status')
    notes = fields.Text(string='Notes')
    price_unit = fields.Float(string='Price')
    origin = fields.Char(string='Source Document')

    @api.model
    def _populate_history_if_empty(self):
        # Populate history if empty
        if not self.search_count([]):
            history_vals = []
            # 1. Fetch completed appointments
            appointments = self.env['salon.appointment'].search([('state', '=', 'done')])
            for rec in appointments:
                if rec.partner_id:
                    for service in rec.service_ids:
                        history_vals.append({
                            'partner_id': rec.partner_id.id,
                            'date': rec.start_datetime or fields.Datetime.now(),
                            'service_name': service.name,
                            'staff_name': rec.staff_id.name,
                            'state': 'Completed',
                            'notes': rec.note or '',
                            'price_unit': service.list_price,
                            'origin': rec.name,
                        })
                    for line in rec.line_ids:
                        history_vals.append({
                            'partner_id': rec.partner_id.id,
                            'date': rec.start_datetime or fields.Datetime.now(),
                            'service_name': line.service_id.name,
                            'staff_name': line.staff_id.name or rec.staff_id.name,
                            'state': 'Completed',
                            'notes': rec.note or '',
                            'price_unit': line.price_unit,
                            'origin': rec.name,
                        })
            # 2. Fetch POS orders not linked to appointments
            pos_orders = self.env['pos.order'].search([('state', 'in', ['paid', 'done', 'invoiced'])])
            for order in pos_orders:
                appt = self.env['salon.appointment'].search([('pos_order_id', '=', order.id)], limit=1)
                if not appt and order.partner_id:
                    for line in order.lines:
                        history_vals.append({
                            'partner_id': order.partner_id.id,
                            'date': order.date_order,
                            'service_name': line.product_id.display_name,
                            'staff_name': order.user_id.name,
                            'state': 'Paid',
                            'notes': line.note or order.general_customer_note or order.internal_note or '',
                            'price_unit': line.price_subtotal_incl,
                            'origin': order.name,
                        })
            if history_vals:
                self.create(history_vals)
