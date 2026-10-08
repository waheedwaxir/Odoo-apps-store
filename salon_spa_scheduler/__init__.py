# -*- coding: utf-8 -*-

from . import models
from . import wizards
from . import reports

def post_init_hook(env):
    env['res.company'].search([])._create_salon_appointment_sequence()
    env['salon.customer.history']._populate_history_if_empty()

