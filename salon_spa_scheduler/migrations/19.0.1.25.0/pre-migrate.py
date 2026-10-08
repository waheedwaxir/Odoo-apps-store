# -*- coding: utf-8 -*-
"""Clean up after an old copy of salon_shortcuts_import.

19.0.1.18.0 - 19.0.1.23.0 moved service categories, processing breaks, the
Sales History ledger and the first-visit date from salon_shortcuts_import into
this module, handing their external ids over. A database that kept loading an
older copy of the import module (an out-of-date folder earlier in the addons
path) re-created its own views, actions, menus and access rules for them
afterwards - so the same menu shows up twice - and re-registered its external
ids for the moved fields.

Here, for every moved name that both modules now hold:
- records that exist twice (views, actions, menus, access rules): the import
  module's copy is deleted, the scheduler's stays;
- records that are shared (models, fields, selection values): only the import
  module's external id goes, so a later update of the import module cannot
  drop a column the scheduler owns.

Nothing to do - and nothing done - on a database that never had the old copy.
"""
import logging

_logger = logging.getLogger(__name__)

OLD = 'salon_shortcuts_import'
NEW = 'salon_spa_scheduler'

LEDGER_FIELDS = [
    'service_id', 'category_id', 'product_id', 'staff_id', 'appointment_id',
    'item_type', 'quantity', 'price_gross', 'discount_amount', 'discount_percent',
    'discount_reason', 'cost_amount', 'block', 'sale_ref', 'payment_method',
    'payment_amount', 'is_split_payment', 'margin', 'reduction_total',
    'price_override',
]
MOVED_NAMES = [
    'model_salon_service_category',
    'field_salon_service__category_id',
    'access_salon_service_category_view',
    'access_salon_service_category_mgr',
    'view_salon_service_category_list',
    'view_salon_service_category_form',
    'action_salon_service_category',
    'menu_salon_service_categories',
    'field_salon_service_step__is_processing_break',
    'field_salon_appointment_step__is_processing_break',
    'view_salon_customer_history_list',
    'view_salon_customer_history_search',
    'action_salon_customer_history',
    'menu_salon_sales_history',
    'field_res_partner__salon_first_visit_date',
    'field_res_users__salon_first_visit_date',
] + ['field_salon_customer_history__%s' % f for f in LEDGER_FIELDS]
MOVED_PREFIXES = [
    'field_salon_service_category__',
    'selection__salon_customer_history__item_type__',
]
# Views the old import module added on top of the scheduler's service form.
OBSOLETE_VIEWS = [
    'view_salon_service_form_category',
    'view_salon_service_list_category',
    'view_salon_service_search_category',
    'view_salon_service_form_break',
]
TABLES = {
    'ir.ui.view': 'ir_ui_view',
    'ir.ui.menu': 'ir_ui_menu',
    'ir.actions.act_window': 'ir_act_window',
    'ir.model.access': 'ir_model_access',
}


def migrate(cr, version):
    if not version:
        return

    name_filter = "(o.name = ANY(%s) OR " + " OR ".join(["o.name LIKE %s"] * len(MOVED_PREFIXES)) + ")"
    params = [MOVED_NAMES] + [p + '%' for p in MOVED_PREFIXES]

    cr.execute(f"""
        SELECT o.id, o.model, o.res_id, n.res_id
          FROM ir_model_data o
          JOIN ir_model_data n ON n.module = %s AND n.name = o.name AND n.model = o.model
         WHERE o.module = %s AND {name_filter}
    """, [NEW, OLD] + params)
    duplicates, shared = 0, 0
    for imd_id, model, old_res, new_res in cr.fetchall():
        if old_res != new_res and model in TABLES:
            cr.execute(f'DELETE FROM "{TABLES[model]}" WHERE id = %s', (old_res,))
            duplicates += 1
        else:
            shared += 1
        cr.execute("DELETE FROM ir_model_data WHERE id = %s", (imd_id,))

    cr.execute("""
        SELECT id, res_id FROM ir_model_data
         WHERE module = %s AND model = 'ir.ui.view' AND name = ANY(%s)
    """, (OLD, OBSOLETE_VIEWS))
    obsolete = cr.fetchall()
    for imd_id, view_id in obsolete:
        cr.execute("DELETE FROM ir_ui_view WHERE id = %s", (view_id,))
        cr.execute("DELETE FROM ir_model_data WHERE id = %s", (imd_id,))

    _logger.info(
        "Old salon_shortcuts_import leftovers: %s duplicate records removed, "
        "%s shared external ids released, %s obsolete views removed.",
        duplicates, shared, len(obsolete))
