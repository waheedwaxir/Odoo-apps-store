# -*- coding: utf-8 -*-
###############################################################################
#    Techman Solutions W.L.L. - Qatar
#
#    Copyright (C) 2026-TODAY Techman Solutions W.L.L.
#    Author: Engr. Waheed Ullah
#    Website: https://www.techman.qa
#    Email: waheed@techman.qa
#    Phone: +97430643395
#
#    Salon & Spa Management System
#
#    This software is a commercial product developed by Techman Solutions
#    W.L.L. It is not free software and is provided under the applicable
#    commercial license and terms of use.
#
#    Unauthorized copying, distribution, modification, or resale of this
#    software is prohibited unless expressly authorized by Techman Solutions
#    W.L.L.
#    For licensing, complete Salon & Spa modules, customization,
#    implementation, integration, or support, please contact:
#
###############################################################################
from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    salon_discount_services_only = fields.Boolean(
        string='Discount Button on Services Only',
        default=True,
        help="When checked, the global Discount button of the POS applies only to "
             "salon services. Uncheck it to discount services and products.")
    salon_show_beautician = fields.Boolean(
        string='Beautician on POS Lines',
        default=False,
        help="A booking checked out to this POS carries, on each service line, "
             "the beautician who does it - shown under the line on the POS "
             "screen and on the receipt.")
    salon_arabic_sections = fields.Boolean(
        string='Arabic Section Titles',
        default=False,
        help="Show the Services / Products / Tips headings of the order in "
             "English and Arabic, on the POS screen and on the printed receipt.")
