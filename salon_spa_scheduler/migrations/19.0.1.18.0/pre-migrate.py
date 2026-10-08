# -*- coding: utf-8 -*-
"""Take ``salon.service.category`` over from salon_shortcuts_import.

The category model, its views, action, menu and access rules - and the
``category_id`` field on ``salon.service`` - used to live in the Shortcuts
import module. They now belong to Salon & Spa Management. Moving the external
ids first means the import module's next update finds nothing of its own left
to clean up, so it cannot drop the table, the column or the categories
already imported.

The import module's three inherited views that put ``category_id`` on the
service list/form/search are removed here: the scheduler's own views carry
the field now, and those views are gone from the import module anyway.
"""
import logging

_logger = logging.getLogger(__name__)

OLD = 'salon_shortcuts_import'
NEW = 'salon_spa_scheduler'

MOVED_NAMES = [
    'model_salon_service_category',
    'field_salon_service__category_id',
    'access_salon_service_category_view',
    'access_salon_service_category_mgr',
    'view_salon_service_category_list',
    'view_salon_service_category_form',
    'action_salon_service_category',
    'menu_salon_service_categories',
]
MOVED_PREFIX = 'field_salon_service_category__'

OBSOLETE_VIEWS = [
    'view_salon_service_form_category',
    'view_salon_service_list_category',
    'view_salon_service_search_category',
]


def migrate(cr, version):
    if not version:
        return

    # Where both modules already hold the same name, keep the scheduler's.
    cr.execute("""
        DELETE FROM ir_model_data old
         USING ir_model_data new
         WHERE old.module = %s AND new.module = %s
           AND old.name = new.name
           AND (old.name = ANY(%s) OR old.name LIKE %s)
    """, (OLD, NEW, MOVED_NAMES, MOVED_PREFIX + '%'))

    cr.execute("""
        UPDATE ir_model_data
           SET module = %s
         WHERE module = %s
           AND (name = ANY(%s) OR name LIKE %s)
    """, (NEW, OLD, MOVED_NAMES, MOVED_PREFIX + '%'))
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
        "salon.service.category: %s external ids moved from %s, %s obsolete views removed.",
        moved, OLD, len(view_ids))
