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


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Per-company scheduler settings. Stored on res.company; the settings form
    # exposes them for the company selected in its header (company_id).
    salon_start_hour = fields.Integer(
        string="Scheduler Start Hour",
        related='company_id.salon_start_hour', readonly=False)
    salon_end_hour = fields.Integer(
        string="Scheduler End Hour",
        related='company_id.salon_end_hour', readonly=False)
    salon_max_cancellations = fields.Integer(
        string="Max Cancellations Allowed",
        related='company_id.salon_max_cancellations', readonly=False)
    salon_allow_reset_cancelled = fields.Boolean(
        string="Managers Can Reset Cancelled to Draft",
        related='company_id.salon_allow_reset_cancelled', readonly=False)
    salon_allow_done_without_payment = fields.Boolean(
        string="Allow Done Without POS Payment",
        related='company_id.salon_allow_done_without_payment', readonly=False)
    salon_allow_edit_done_staff = fields.Boolean(
        string="Managers Can Edit Bookings After Start",
        related='company_id.salon_allow_edit_done_staff', readonly=False)
    salon_general_notes_warning = fields.Boolean(
        string="Warn About General Notes",
        related='company_id.salon_general_notes_warning', readonly=False)
    salon_allow_extend_started = fields.Boolean(
        string="Add Services to Started Appointments",
        related='company_id.salon_allow_extend_started', readonly=False)

    pos_salon_discount_services_only = fields.Boolean(
        related='pos_config_id.salon_discount_services_only', readonly=False)
    pos_salon_show_beautician = fields.Boolean(
        related='pos_config_id.salon_show_beautician', readonly=False)
    pos_salon_arabic_sections = fields.Boolean(
        related='pos_config_id.salon_arabic_sections', readonly=False)
