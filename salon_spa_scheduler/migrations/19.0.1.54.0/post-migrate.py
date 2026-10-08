# -*- coding: utf-8 -*-
"""Draft bookings are not "arrived": clear the mark left by Reset to Draft."""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute("UPDATE salon_appointment SET is_arrived = false WHERE state = 'draft' AND is_arrived RETURNING name")
    _logger.info("Draft bookings no longer marked Arrived: %s", [r[0] for r in cr.fetchall()])
