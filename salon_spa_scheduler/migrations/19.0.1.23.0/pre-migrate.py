# -*- coding: utf-8 -*-
"""Take ``res.partner.salon_first_visit_date`` over from salon_shortcuts_import.

Moving the field's external ids here first means the import module's next
update finds nothing of its own to clean up, so it cannot drop the column and
the imported first-visit dates survive.
"""
import logging

_logger = logging.getLogger(__name__)

OLD = 'salon_shortcuts_import'
NEW = 'salon_spa_scheduler'

# res.users inherits the partner's fields and gets its own reflection of them.
MOVED_NAMES = [
    'field_res_partner__salon_first_visit_date',
    'field_res_users__salon_first_visit_date',
]


def migrate(cr, version):
    if not version:
        return

    # Where both modules already hold the same name, keep the scheduler's.
    cr.execute("""
        DELETE FROM ir_model_data old
         USING ir_model_data new
         WHERE old.module = %s AND new.module = %s
           AND old.name = new.name AND old.name = ANY(%s)
    """, (OLD, NEW, MOVED_NAMES))

    cr.execute("""
        UPDATE ir_model_data SET module = %s
         WHERE module = %s AND name = ANY(%s)
    """, (NEW, OLD, MOVED_NAMES))
    _logger.info("salon_first_visit_date: %s external ids moved from %s.", cr.rowcount, OLD)
