# -*- coding: utf-8 -*-
"""Give existing beauticians a Position.

The Position comes from the linked employee's Job Position. A beautician
without one but with the old free-text Job Title gets the Job Position of
that name in their branch, created without targets when there is none.
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Job = env['hr.job'].with_context(active_test=False)
    linked = 0
    for staff in env['salon.staff'].with_context(active_test=False).search(
            [('job_title', '!=', False), ('job_id', '=', False)]):
        name = staff.job_title.strip()
        job = Job.search([('name', '=ilike', name), ('company_id', 'in', (False, staff.company_id.id))], limit=1) \
            or Job.create({'name': name, 'company_id': staff.company_id.id})
        # Straight to the column: through the ORM the new position's (empty)
        # targets would be copied over the beautician's own.
        cr.execute("UPDATE salon_staff SET job_id = %s WHERE id = %s", (job.id, staff.id))
        linked += 1
    _logger.info("Beauticians given a Position from their old Job Title text: %s", linked)
