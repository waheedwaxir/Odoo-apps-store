# -*- coding: utf-8 -*-
"""Subtotal of open bookings from the Beauticians & Services table.

Only bookings still open (draft, confirmed, in progress) are recomputed;
finished and imported ones keep the amount they were closed with.
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    appts = env['salon.appointment'].search([('state', 'in', ('draft', 'confirmed', 'progress'))])
    before = {a.id: a.amount_subtotal for a in appts}
    appts._compute_amount_subtotal()
    changed = [a.name for a in appts if abs(a.amount_subtotal - before[a.id]) > 0.001]
    _logger.info("Open bookings whose subtotal now includes every service in the table: %s %s",
                 len(changed), changed[:20])
