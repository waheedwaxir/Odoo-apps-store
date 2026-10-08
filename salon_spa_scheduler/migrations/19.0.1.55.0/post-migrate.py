# -*- coding: utf-8 -*-
"""Unlink bookings from POS orders that were cancelled (e.g. by closing the
session unpaid), so they can be sent to the POS again."""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute("""
        UPDATE salon_appointment a SET pos_order_id = NULL
          FROM pos_order o
         WHERE o.id = a.pos_order_id AND o.state = 'cancel'
     RETURNING a.name
    """)
    _logger.info("Bookings unlinked from a cancelled POS order: %s", [r[0] for r in cr.fetchall()])
