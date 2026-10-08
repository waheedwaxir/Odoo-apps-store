# -*- coding: utf-8 -*-
"""19.0.1.10.2: "Required" moved from the appointment header to each service
line (salon.appointment.step.staff_required). Carry existing flags over so
already-booked appointments keep their REQ badge in the scheduler."""


def migrate(cr, version):
    if not version:
        return
    cr.execute("ALTER TABLE salon_appointment_step ADD COLUMN IF NOT EXISTS staff_required boolean")
    cr.execute(
        """
        UPDATE salon_appointment_step st
           SET staff_required = TRUE
          FROM salon_appointment a
         WHERE st.appointment_id = a.id AND a.staff_required IS TRUE
        """
    )
