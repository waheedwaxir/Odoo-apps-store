from odoo import models, fields, api

class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    staff_id = fields.Many2one('salon.staff', string='Staff Member (Tip)')

    @api.model
    def _load_pos_data_fields(self, config):
        fields_list = super(PosOrderLine, self)._load_pos_data_fields(config)
        if 'staff_id' not in fields_list:
            fields_list.append('staff_id')
        return fields_list

    @api.model
    def _order_line_fields(self, line, session_id=None):
        res = super(PosOrderLine, self)._order_line_fields(line, session_id)
        line_dict = line[2] if isinstance(line, (list, tuple)) and len(line) >= 3 and isinstance(line[2], dict) else (line if isinstance(line, dict) else {})
        res_dict = res[2] if isinstance(res, (list, tuple)) and len(res) >= 3 and isinstance(res[2], dict) else (res if isinstance(res, dict) else {})
        if line_dict and 'staff_id' in line_dict:
            res_dict['staff_id'] = line_dict.get('staff_id') or False
        return res

class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def _order_fields(self, ui_order):
        fields_dict = super(PosOrder, self)._order_fields(ui_order)
        ui_lines = ui_order.get('lines', [])
        for idx, line in enumerate(fields_dict.get('lines', [])):
            if isinstance(line, (list, tuple)) and len(line) >= 3 and isinstance(line[2], dict):
                res_dict = line[2]
                if idx < len(ui_lines):
                    ui_l = ui_lines[idx]
                    ui_dict = ui_l[2] if isinstance(ui_l, (list, tuple)) and len(ui_l) >= 3 and isinstance(ui_l[2], dict) else (ui_l if isinstance(ui_l, dict) else {})
                    if 'staff_id' in ui_dict:
                        res_dict['staff_id'] = ui_dict.get('staff_id') or False
        return fields_dict

    def _create_staff_tips(self):
        for order in self:
            if order.state in ['paid', 'done', 'invoiced'] or order.amount_paid >= order.amount_total:
                for line in order.lines:
                    if line.staff_id and (line.price_subtotal > 0 or line.price_subtotal_incl > 0):
                        tip_amt = line.price_subtotal_incl if line.price_subtotal_incl > 0 else line.price_subtotal
                        existing_tip = self.env['salon.staff.tip'].search([
                            ('order_id', '=', order.id),
                            ('staff_id', '=', line.staff_id.id),
                        ], limit=1)
                        if not existing_tip:
                            self.env['salon.staff.tip'].create({
                                'staff_id': line.staff_id.id,
                                'amount': tip_amt,
                                'order_id': order.id,
                                'date': order.date_order or fields.Datetime.now(),
                                'state': 'unpaid'
                            })
                        elif existing_tip.amount != tip_amt and existing_tip.state == 'unpaid':
                            existing_tip.write({'amount': tip_amt})

    def _process_saved_order(self, draft):
        res = super(PosOrder, self)._process_saved_order(draft)
        self._create_staff_tips()
        return res

    def action_pos_order_paid(self):
        res = super(PosOrder, self).action_pos_order_paid()
        self._create_staff_tips()
        return res

    def write(self, vals):
        res = super(PosOrder, self).write(vals)
        if vals.get('state') in ['paid', 'done', 'invoiced']:
            self._create_staff_tips()
        return res
