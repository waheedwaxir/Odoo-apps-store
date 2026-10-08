# -*- coding: utf-8 -*-
"""Take the processing-break flag over from salon_shortcuts_import.

``is_processing_break`` on ``salon.service.step`` and
``salon.appointment.step`` used to be added by the Shortcuts import module.
Moving the field external ids here first means the import module's next
update finds nothing of its own to clean up, so it cannot drop the columns
and the flags already imported survive.

The import module's inherited view that put the toggle on the service form is
removed: the scheduler's own form carries it now.
"""
import logging

_logger = logging.getLogger(__name__)

OLD = 'salon_shortcuts_import'
NEW = 'salon_spa_scheduler'

MOVED_NAMES = [
    'field_salon_service_step__is_processing_break',
    'field_salon_appointment_step__is_processing_break',
]
OBSOLETE_VIEWS = ['view_salon_service_form_break']


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
    moved = cr.rowcount

    cr.execute("""
        SELECT res_id FROM ir_model_data
         WHERE module = %s AND model = 'ir.ui.view' AND name = ANY(%s)
    """, (OLD, OBSOLETE_VIEWS))
    view_ids = [row[0] for row in cr.fetchall()]
    if view_ids:
        cr.execute("DELETE FROM ir_ui_view WHERE id = ANY(%s)", (view_ids,))
        cr.execute("""
            DELETE FROM ir_model_data
             WHERE module = %s AND model = 'ir.ui.view' AND name = ANY(%s)
        """, (OLD, OBSOLETE_VIEWS))

    _logger.info(
        "is_processing_break: %s external ids moved from %s, %s obsolete views removed.",
        moved, OLD, len(view_ids))
