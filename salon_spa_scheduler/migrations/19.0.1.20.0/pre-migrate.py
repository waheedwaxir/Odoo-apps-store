# -*- coding: utf-8 -*-
"""Take the Sales History ledger over from salon_shortcuts_import.

The ledger fields on ``salon.customer.history`` (service, category, product,
staff, appointment, item type, discount, cost, margin, payment...), the list
and search views, the action and the Sales History menu used to be added by the
Shortcuts import module. Moving their external ids here first means the
import module's next update finds nothing of its own to clean up, so it cannot
drop the columns and the imported ledger survives intact.

``shortcuts_id`` and ``is_migrated`` stay with the import module.
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
MOVED_NAMES = ['field_salon_customer_history__%s' % f for f in LEDGER_FIELDS] + [
    'view_salon_customer_history_list',
    'view_salon_customer_history_search',
    'action_salon_customer_history',
    'menu_salon_sales_history',
]
SELECTION_PREFIX = 'selection__salon_customer_history__item_type__'


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
    """, (OLD, NEW, MOVED_NAMES, SELECTION_PREFIX + '%'))

    cr.execute("""
        UPDATE ir_model_data SET module = %s
         WHERE module = %s AND (name = ANY(%s) OR name LIKE %s)
    """, (NEW, OLD, MOVED_NAMES, SELECTION_PREFIX + '%'))

    _logger.info("Sales History ledger: %s external ids moved from %s.", cr.rowcount, OLD)
