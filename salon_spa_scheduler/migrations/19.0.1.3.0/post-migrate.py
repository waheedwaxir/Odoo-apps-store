# -*- coding: utf-8 -*-
"""19.0.1.3.0 data migration.

``salon.appointment`` now supports multiple "Main Beauticians" via the new
``staff_ids`` many2many; ``staff_id`` becomes the derived primary. Backfill the
relation table so every existing appointment keeps its beautician in the new set.
"""
import logging

_logger = logging.getLogger(__name__)

REL_TABLE = 'salon_appointment_staff_rel'


def _table_exists(cr, table):
    cr.execute("SELECT 1 FROM information_schema.tables WHERE table_name = %s", (table,))
    return bool(cr.fetchone())


def migrate(cr, version):
    if not version:
        return

    if not _table_exists(cr, REL_TABLE):
        _logger.warning("%s not found; skipping staff_ids backfill.", REL_TABLE)
        return

    cr.execute(
        """
        INSERT INTO {rel} (appointment_id, staff_id)
        SELECT a.id, a.staff_id
          FROM salon_appointment a
         WHERE a.staff_id IS NOT NULL
           AND NOT EXISTS (
               SELECT 1 FROM {rel} r
                WHERE r.appointment_id = a.id AND r.staff_id = a.staff_id
           )
        """.format(rel=REL_TABLE)
    )
    _logger.info("Backfilled %s row(s) into %s.", cr.rowcount, REL_TABLE)
