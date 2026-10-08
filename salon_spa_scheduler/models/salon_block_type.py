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
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

CATEGORIES = [
    ('block', 'Time Block'),
    ('duty', 'Duty / Other Branch'),
    ('training', 'Training'),
    ('meeting', 'Meeting'),
    ('break', 'Break'),
    ('absence', 'Absence'),
]


class SalonBlockType(models.Model):
    """What kind of non-customer time this is.

    The type carries the policy - colour, default length, and whether the block
    should also exist as a Planning shift or a Time Off request - so the person
    creating a block on the floor only has to pick a name.
    """
    _name = 'salon.block.type'
    _description = 'Salon Time Block Type'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(help="Short label, e.g. as it appeared in the previous system.")
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    color = fields.Integer(default=1)
    company_id = fields.Many2one(
        'res.company', string='Company', index=True,
        default=lambda self: self.env.company,
        help="Leave empty to make the type available to every branch.")

    category = fields.Selection(
        CATEGORIES, string='Category', default='block', required=True,
        help="Groups block types for reporting, and decides the sensible "
             "defaults for the Planning and Time Off bridges.")
    default_duration_minutes = fields.Integer(
        string='Default Duration (Minutes)', default=60, required=True)

    # --- Planning bridge ---------------------------------------------------
    create_planning_slot = fields.Boolean(
        string='Publish as Planning Shift', default=True,
        help="Publishes a Planning shift for the beautician covering this block. "
             "Salon & Spa Management already checks published shifts before it "
             "lets anyone be booked, so this is what makes a block actually "
             "protect the time.")

    # --- Time Off bridge ---------------------------------------------------
    create_leave = fields.Boolean(
        string='Raise Time Off', default=False,
        help="Creates a Time Off request against the linked employee. Use it for "
             "sick leave and holidays so HR and the salon floor agree on who is in.")
    leave_type_id = fields.Many2one(
        'hr.leave.type', string='Time Off Type',
        help="Which Time Off type to raise. Required when Raise Time Off is on.")

    # --- Branch ------------------------------------------------------------
    target_branch_id = fields.Many2one(
        'res.company', string='Works At Branch',
        help="For duty at another location. A block of this type means the "
             "beautician is working, just not here - their hours count against "
             "that branch rather than reading as idle time on this board.")

    blocks_booking = fields.Boolean(
        string='Prevents Booking', default=True,
        help="Refuses an appointment that overlaps this block. Turn it off for "
             "purely informational markers such as reminders.")

    block_count = fields.Integer(compute='_compute_block_count')

    _name_company_unique = models.Constraint(
        'unique(name, company_id)',
        "A block type with this name already exists for this company.",
    )

    def _compute_block_count(self):
        data = self.env['salon.block']._read_group(
            [('block_type_id', 'in', self.ids)], ['block_type_id'], ['__count'])
        counts = {block_type.id: count for block_type, count in data}
        for rec in self:
            rec.block_count = counts.get(rec.id, 0)

    @api.constrains('create_leave', 'leave_type_id')
    def _check_leave_type(self):
        for rec in self:
            if rec.create_leave and not rec.leave_type_id:
                raise ValidationError(_(
                    "Pick a Time Off type for %(name)s, or turn off Raise Time Off.",
                    name=rec.name))

    @api.constrains('default_duration_minutes')
    def _check_duration(self):
        for rec in self:
            if rec.default_duration_minutes <= 0:
                raise ValidationError(_("Default duration must be greater than zero."))

    @api.onchange('category')
    def _onchange_category(self):
        """Sensible defaults per category - all still overridable."""
        if self.category == 'absence':
            self.create_leave = True
            self.create_planning_slot = False
            self.blocks_booking = True
        elif self.category == 'break':
            self.create_planning_slot = False
            self.create_leave = False
            self.blocks_booking = True
        elif self.category == 'duty':
            self.create_planning_slot = True
            self.create_leave = False
            self.blocks_booking = True

    def action_view_blocks(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.name,
            'res_model': 'salon.block',
            'view_mode': 'list,form',
            'domain': [('block_type_id', '=', self.id)],
            'context': {'default_block_type_id': self.id},
        }
