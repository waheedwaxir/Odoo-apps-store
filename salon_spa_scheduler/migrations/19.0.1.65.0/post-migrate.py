# -*- coding: utf-8 -*-
"""Membership number moves from the membership to the customer.

19.0.1.64.0 kept a number per membership (member_number); the number is the
customer's corporate ID, so it now lives on the customer
(salon_membership_number) and the membership shows it. Numbers typed in
between are moved over to customers that have none yet.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute("""SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'salon_membership_line' AND column_name = 'member_number'""")
    if not cr.fetchone():
        return
    cr.execute("""
        UPDATE res_partner p SET salon_membership_number = l.member_number
          FROM (SELECT DISTINCT ON (partner_id) partner_id, member_number
                  FROM salon_membership_line
                 WHERE member_number IS NOT NULL AND member_number <> ''
              ORDER BY partner_id, id) l
         WHERE p.id = l.partner_id AND COALESCE(p.salon_membership_number, '') = ''
     RETURNING p.id
    """)
    moved = len(cr.fetchall())
    cr.execute("""UPDATE salon_membership_line l SET membership_number = p.salon_membership_number
                    FROM res_partner p WHERE p.id = l.partner_id""")
    cr.execute("ALTER TABLE salon_membership_line DROP COLUMN member_number")
    _logger.info("Membership numbers moved from memberships to customers: %s", moved)
