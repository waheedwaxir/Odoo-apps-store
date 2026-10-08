# -*- coding: utf-8 -*-
###############################################################################
#    Techman Solutions W.L.L. - Qatar
#
#    Copyright (C) 2026-TODAY Techman Solutions W.L.L.
#    Author: Engr. Waheed Ullah
#    Website: https://www.techman.qa
#    Email: waheed@techman.qa
#    Phone: +97430643395
#
#    Salon & Spa Management System
#
#    This software is a commercial product developed by Techman Solutions
#    W.L.L. It is not free software and is provided under the applicable
#    commercial license and terms of use.
#
#    Unauthorized copying, distribution, modification, or resale of this
#    software is prohibited unless expressly authorized by Techman Solutions
#    W.L.L.
#    For licensing, complete Salon & Spa modules, customization,
#    implementation, integration, or support, please contact:
#
###############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    staff_id = fields.Many2one('salon.staff', string='Staff Member (Tip)')
    # Who performs the service: set at checkout ("Beautician on POS Lines")
    # or picked at the till with Beautician. Separate from staff_id, which
    # makes a line a tip.
    salon_beautician_id = fields.Many2one('salon.staff', string='Beautician', index='btree_not_null')
    salon_beautician_name = fields.Char(string='Beautician Name')

    @api.model
    def _load_pos_data_fields(self, config):
        fields_list = super(PosOrderLine, self)._load_pos_data_fields(config)
        for name in ('staff_id', 'salon_beautician_id', 'salon_beautician_name'):
            if name not in fields_list:
                fields_list.append(name)
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
                                'company_id': order.company_id.id,
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


class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def _load_pos_data_models(self, config):
        # Beauticians, so a line can be given the one who does it.
        return super()._load_pos_data_models(config) + ['salon.staff']

    @api.model
    def action_open_salon_pos(self):
        """Jump straight into the current company's open POS session - the
        same session lookup and act_url redirect salon.appointment's "Send to
        POS" button uses - instead of the POS app's config-picker kanban.
        """
        domain = [('state', '=', 'opened'), ('company_id', '=', self.env.company.id)]
        session = self.search(domain + [('user_id', '=', self.env.user.id)], limit=1)
        if not session:
            session = self.search(domain, limit=1)
        if not session:
            raise UserError(_(
                "Please open a Point of Sale session for %s first.", self.env.company.display_name))
        return {
            'type': 'ir.actions.act_url',
            'url': '/pos/ui/%d/' % session.config_id.id,
            'target': 'self',
        }
