# -*- coding: utf-8 -*-
"""Write services added at the till back into bookings already paid.

For every booking whose POS order is paid, services charged there but
missing from the booking become Additional Services lines (and lines in
Beauticians & Services); its Sales History and commissions are rewritten.
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    appts = env['salon.appointment'].search([
        ('pos_order_id.state', 'in', ('paid', 'done', 'invoiced')),
        ('state', '=', 'done'),
    ])
    changed = []
    for appt in appts:
        before = len(appt.line_ids)
        appt._absorb_pos_services_safe(appt.pos_order_id)
        if len(appt.line_ids) != before:
            appt._log_sale_history()
            appt._sync_commissions()
            changed.append(appt.name)
    _logger.info("Bookings given the services added at the till: %s", changed)
