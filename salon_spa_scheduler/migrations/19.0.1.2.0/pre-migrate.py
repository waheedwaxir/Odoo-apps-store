# -*- coding: utf-8 -*-
"""19.0.1.2.0 schema migration.

The standalone ``salon.branch`` model is removed. Branches are now a direct
reflection of the databases's companies, so every ``branch_id`` column
(``salon.appointment``, ``salon.room``) is re-pointed from ``salon.branch`` to
``res.company``.

This runs *before* the ORM retargets the ``branch_id`` foreign keys, so the old
``salon_branch`` table is still available for the id -> company_id mapping.
"""
import logging

_logger = logging.getLogger(__name__)

BRANCH_TABLES = ('salon_appointment', 'salon_room')


def _table_exists(cr, table):
    cr.execute("SELECT 1 FROM information_schema.tables WHERE table_name = %s", (table,))
    return bool(cr.fetchone())


def _column_exists(cr, table, column):
    cr.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = %s AND column_name = %s",
        (table, column),
    )
    return bool(cr.fetchone())


def migrate(cr, version):
    if not version:
        return

    if not _table_exists(cr, 'salon_branch'):
        _logger.info("salon_branch table absent; nothing to remap.")
        return

    fallback_company = None
    cr.execute("SELECT id FROM res_company ORDER BY id LIMIT 1")
    row = cr.fetchone()
    if row:
        fallback_company = row[0]

    for table in BRANCH_TABLES:
        if not _column_exists(cr, table, 'branch_id'):
            continue

        # Drop the stale FK(s) to salon_branch so the values can be rewritten.
        cr.execute(
            """
            SELECT conname FROM pg_constraint
            WHERE conrelid = %s::regclass AND contype = 'f'
              AND confrelid = 'salon_branch'::regclass
            """,
            (table,),
        )
        for (conname,) in cr.fetchall():
            cr.execute('ALTER TABLE "%s" DROP CONSTRAINT "%s"' % (table, conname))

        # Remap: branch -> that branch's company.
        cr.execute(
            """
            UPDATE {table} t
               SET branch_id = b.company_id
              FROM salon_branch b
             WHERE t.branch_id = b.id
            """.format(table=table)
        )

        # Anything still not pointing at a real company: null it, or fall back to
        # the first company for the NOT NULL salon_room.branch_id column.
        if table == 'salon_room' and fallback_company:
            cr.execute(
                """
                UPDATE salon_room
                   SET branch_id = %s
                 WHERE branch_id IS NULL
                    OR branch_id NOT IN (SELECT id FROM res_company)
                """,
                (fallback_company,),
            )
        else:
            cr.execute(
                """
                UPDATE {table}
                   SET branch_id = NULL
                 WHERE branch_id IS NOT NULL
                   AND branch_id NOT IN (SELECT id FROM res_company)
                """.format(table=table)
            )

    # Drop the obsolete table and its m2m relations (report wizards). The ORM
    # recreates the transient wizard relations against res_company on load.
    cr.execute("DROP TABLE IF EXISTS salon_branch CASCADE")
    _logger.info("salon.branch removed; branch_id columns now reference res.company.")
