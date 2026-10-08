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


class SalonCustomerNote(models.Model):
    _name = 'salon.customer.note'
    _description = 'Salon Customer Note'
    _order = 'date desc, id desc'

    partner_id = fields.Many2one('res.partner', string='Customer', required=True, ondelete='cascade', index=True)
    date = fields.Datetime(string='Date', required=True, default=fields.Datetime.now)
    user_id = fields.Many2one('res.users', string='Recorded By', default=lambda self: self.env.user)
    # A comment staff write about the customer: rude, a complaint, did not
    # pay... These are what the Comments lists show and add.
    comment_type = fields.Selection([
        ('complaint', 'Complaint'),
        ('rude', 'Rude / Behaviour'),
        ('unpaid', 'Did Not Pay'),
        ('other', 'Other'),
    ], string='Type')
    comment = fields.Text(string='Comment')
    # Written by res.partner.write: what Allergies / Preferences said after
    # each change. Kept as a log; not shown with the comments.
    allergies = fields.Text(string='Allergies / Medical Notes')
    preferences = fields.Text(string='Preferences / Styling Notes')
