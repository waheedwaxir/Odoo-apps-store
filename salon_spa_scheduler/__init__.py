# -*- coding: utf-8 -*-

from . import models
from . import controllers
from . import wizards
from . import reports

def post_init_hook(env):
    env['salon.customer.history']._populate_history_if_empty()

