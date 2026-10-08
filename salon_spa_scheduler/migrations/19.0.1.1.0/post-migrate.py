# -*- coding: utf-8 -*-
"""19.0.1.1.0 data migration.

1. Move the scheduler settings from global ``ir.config_parameter`` to per-company
   fields on ``res.company`` (start/end hour, max cancellations), then drop the
   obsolete parameters.
2. Give every existing company its own ``SAL/`` appointment sequence (numbering
   was previously shared across all companies).
"""
from odoo import SUPERUSER_ID, api

PARAM_MAP = {
    'salon_start_hour': 'salon_spa_scheduler.start_hour',
    'salon_end_hour': 'salon_spa_scheduler.end_hour',
    'salon_max_cancellations': 'salon_spa_scheduler.max_cancellations',
}


def migrate(cr, version):
    if not version:
        return

    env = api.Environment(cr, SUPERUSER_ID, {})
    icp = env['ir.config_parameter'].sudo()

    values = {}
    for field_name, param_key in PARAM_MAP.items():
        raw = icp.get_param(param_key)
        if raw in (None, False, ''):
            continue
        try:
            values[field_name] = int(raw)
        except (TypeError, ValueError):
            continue

    if values:
        # write() runs the res.company @api.constrains checks; guard against a
        # previously invalid global config blocking the whole upgrade.
        try:
            env['res.company'].search([]).write(values)
        except Exception:  # noqa: BLE001
            for company in env['res.company'].search([]):
                for field_name, val in values.items():
                    try:
                        company.write({field_name: val})
                    except Exception:  # noqa: BLE001
                        pass

    icp.search([('key', 'in', list(PARAM_MAP.values()))]).unlink()

    # Per-company appointment sequences.
    env['res.company'].search([])._create_salon_appointment_sequence()
