# -*- coding: utf-8 -*-
"""Give existing Beauticians & Services lines their service.

A line built from a service's steps was created with the step name
("Service - Step") but no service, so the Service column stayed empty. The
service is found by that name among the booking's own services first, then
among all services of the booking's company (a line added after the booking
was made need not be in its service list); a line that matches none is left
as it is. A one-step line named "X - X" becomes "X".
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute("""
        UPDATE salon_appointment_step st
           SET service_id = m.service_id
          FROM (
                SELECT DISTINCT ON (st.id) st.id AS step_id, sv.id AS service_id
                  FROM salon_appointment_step st
                  JOIN salon_appointment_salon_service_rel rel
                    ON rel.salon_appointment_id = st.appointment_id
                  JOIN salon_service sv ON sv.id = rel.salon_service_id
                 WHERE st.service_id IS NULL
                   AND (st.name = sv.name OR st.name LIKE sv.name || ' - %')
              ORDER BY st.id, length(sv.name) DESC
               ) m
         WHERE st.id = m.step_id
    """)
    _logger.info("Beauticians & Services lines given their service: %s", cr.rowcount)
    cr.execute("""
        UPDATE salon_appointment_step st
           SET service_id = m.service_id
          FROM (
                SELECT DISTINCT ON (st.id) st.id AS step_id, sv.id AS service_id
                  FROM salon_appointment_step st
                  JOIN salon_appointment a ON a.id = st.appointment_id
                  JOIN salon_service sv
                    ON sv.company_id = a.company_id
                 WHERE st.service_id IS NULL
                   AND (st.name = sv.name OR st.name LIKE sv.name || ' - %')
              ORDER BY st.id, length(sv.name) DESC, sv.active DESC, sv.id
               ) m
         WHERE st.id = m.step_id
    """)
    _logger.info("... matched by name in the company: %s", cr.rowcount)
    cr.execute("""
        UPDATE salon_appointment_step st
           SET name = sv.name
          FROM salon_service sv
         WHERE sv.id = st.service_id
           AND st.name = sv.name || ' - ' || sv.name
    """)
    _logger.info("Lines renamed from 'X - X' to 'X': %s", cr.rowcount)
