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
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class SalonBlock(models.Model):
    """Time on the scheduler that belongs to no customer.

    Training, a staff meeting, a photoshoot, a shift on duty at another branch,
    a stretch marked "do not book". It occupies the beautician exactly the way
    an appointment does, but it has no customer and no service - which is
    precisely why salon.appointment cannot hold it.
    """
    _name = 'salon.block'
    _description = 'Salon Time Block'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_datetime desc, id desc'
    _check_company_auto = True

    name = fields.Char(
        string='Title', compute='_compute_name', store=True, readonly=False,
        help="Defaults to the block type; overwrite it to say what this one is about.")
    block_type_id = fields.Many2one(
        'salon.block.type', string='Type', required=True, tracking=True,
        ondelete='restrict', check_company=True)
    category = fields.Selection(
        related='block_type_id.category', store=True, index=True, readonly=True)

    company_id = fields.Many2one(
        'res.company', string='Company', required=True, index=True,
        default=lambda self: self.env.company, tracking=True)
    branch_id = fields.Many2one(
        'res.company', string='Branch', required=True, tracking=True,
        default=lambda self: self.env.company,
        domain="[('id', 'in', allowed_company_ids)]",
        help="The branch whose board this block sits on.")
    works_at_branch_id = fields.Many2one(
        'res.company', string='Working At', tracking=True,
        help="Set for duty elsewhere: the beautician is working, just not here.")

    staff_id = fields.Many2one(
        'salon.staff', string='Beautician', required=True, index=True,
        tracking=True, ondelete='cascade')
    employee_id = fields.Many2one(
        'hr.employee', related='staff_id.employee_id', store=True, readonly=True)

    start_datetime = fields.Datetime(required=True, tracking=True,
                                     default=lambda self: fields.Datetime.now())
    end_datetime = fields.Datetime(
        required=True, tracking=True, compute='_compute_end_datetime',
        store=True, readonly=False)
    duration_minutes = fields.Integer(
        string='Duration (Minutes)', compute='_compute_duration', store=True, readonly=False)
    duration_hours = fields.Float(
        string='Hours', compute='_compute_duration_hours', store=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancel', 'Cancelled'),
    ], default='confirmed', required=True, tracking=True,
        help="Only a confirmed block protects the time.")
    note = fields.Text(string='Notes')
    color = fields.Integer(related='block_type_id.color', readonly=True)

    planning_slot_id = fields.Many2one(
        'planning.slot', string='Planning Shift', readonly=True, copy=False, ondelete='set null')
    leave_id = fields.Many2one(
        'hr.leave', string='Time Off', readonly=True, copy=False, ondelete='set null')

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends('block_type_id')
    def _compute_name(self):
        for rec in self:
            if not rec.name or rec.name == (rec._origin.block_type_id.name or ''):
                rec.name = rec.block_type_id.name or _('Time Block')

    @api.depends('start_datetime', 'duration_minutes')
    def _compute_end_datetime(self):
        from datetime import timedelta
        for rec in self:
            if rec.start_datetime and rec.duration_minutes:
                rec.end_datetime = rec.start_datetime + timedelta(minutes=rec.duration_minutes)
            elif not rec.end_datetime:
                rec.end_datetime = rec.start_datetime

    @api.depends('start_datetime', 'end_datetime')
    def _compute_duration(self):
        for rec in self:
            if rec.start_datetime and rec.end_datetime and rec.end_datetime > rec.start_datetime:
                rec.duration_minutes = int(
                    (rec.end_datetime - rec.start_datetime).total_seconds() // 60)
            elif not rec.duration_minutes:
                rec.duration_minutes = rec.block_type_id.default_duration_minutes or 60

    @api.depends('duration_minutes')
    def _compute_duration_hours(self):
        for rec in self:
            rec.duration_hours = (rec.duration_minutes or 0) / 60.0

    @api.onchange('block_type_id')
    def _onchange_block_type_id(self):
        if self.block_type_id:
            self.name = self.block_type_id.name
            if self.block_type_id.default_duration_minutes:
                self.duration_minutes = self.block_type_id.default_duration_minutes
            if self.block_type_id.target_branch_id:
                self.works_at_branch_id = self.block_type_id.target_branch_id

    @api.constrains('start_datetime', 'end_datetime')
    def _check_range(self):
        for rec in self:
            if rec.start_datetime and rec.end_datetime and rec.end_datetime <= rec.start_datetime:
                raise ValidationError(_("A block must end after it starts."))

    @api.constrains('staff_id', 'start_datetime', 'end_datetime', 'state')
    def _check_block_overlap(self):
        """Two confirmed blocks cannot own the same beautician at once."""
        if self.env.context.get('skip_salon_block_overlap'):
            return
        for rec in self:
            if rec.state != 'confirmed' or not rec.staff_id:
                continue
            clash = self.search([
                ('id', '!=', rec.id),
                ('staff_id', '=', rec.staff_id.id),
                ('state', '=', 'confirmed'),
                ('start_datetime', '<', rec.end_datetime),
                ('end_datetime', '>', rec.start_datetime),
            ], limit=1)
            if clash:
                raise ValidationError(_(
                    "%(staff)s already has \"%(other)s\" booked over this time.",
                    staff=rec.staff_id.name, other=clash.display_name))

    # ------------------------------------------------------------------
    # Bridges to Planning and Time Off
    # ------------------------------------------------------------------
    def _planning_slot_vals(self):
        """Built against the live registry - planning.slot field names have
        moved between versions and a migration should not die over it."""
        self.ensure_one()
        Slot = self.env['planning.slot']
        available = Slot._fields
        resource = self.employee_id.resource_id if self.employee_id else False
        if not resource:
            return {}
        vals = {
            'resource_id': resource.id,
            'start_datetime': self.start_datetime,
            'end_datetime': self.end_datetime,
            'company_id': (self.works_at_branch_id or self.branch_id or self.company_id).id,
            'name': self.name,
            'state': 'published',
            'allocated_hours': self.duration_hours,
        }
        return {key: value for key, value in vals.items() if key in available}

    def _sync_planning_slot(self):
        for rec in self:
            wants = (rec.block_type_id.create_planning_slot
                     and rec.state == 'confirmed' and rec.employee_id)
            if not wants:
                if rec.planning_slot_id:
                    rec.planning_slot_id.sudo().unlink()
                    rec.planning_slot_id = False
                continue
            vals = rec._planning_slot_vals()
            if not vals:
                continue
            try:
                if rec.planning_slot_id:
                    rec.planning_slot_id.sudo().write(vals)
                else:
                    rec.planning_slot_id = self.env['planning.slot'].sudo().create(vals)
            except Exception as exc:  # noqa: BLE001 - never block the floor over a bridge
                _logger.warning("Salon block %s: planning shift not synced: %s", rec.id, exc)
                rec.message_post(body=_("Planning shift could not be synced: %s", exc))

    def _sync_leave(self):
        for rec in self:
            wants = (rec.block_type_id.create_leave and rec.state == 'confirmed'
                     and rec.employee_id and rec.block_type_id.leave_type_id)
            if not wants:
                if rec.leave_id:
                    try:
                        rec.leave_id.sudo().action_refuse()
                    except Exception:  # noqa: BLE001
                        pass
                    rec.leave_id = False
                continue
            vals = {
                'name': rec.name,
                'employee_id': rec.employee_id.id,
                'holiday_status_id': rec.block_type_id.leave_type_id.id,
                'request_date_from': rec.start_datetime.date(),
                'request_date_to': rec.end_datetime.date(),
            }
            try:
                if rec.leave_id:
                    rec.leave_id.sudo().write(vals)
                else:
                    rec.leave_id = self.env['hr.leave'].sudo().with_context(
                        leave_skip_date_check=True, mail_notrack=True).create(vals)
            except Exception as exc:  # noqa: BLE001
                # Allocation limits and overlapping leaves are HR's business, not
                # the scheduler's - record the block either way and say why.
                _logger.warning("Salon block %s: time off not raised: %s", rec.id, exc)
                rec.message_post(body=_("Time Off could not be raised: %s", exc))

    def _sync_bridges(self):
        self._sync_planning_slot()
        self._sync_leave()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if not self.env.context.get('skip_salon_block_bridges'):
            records._sync_bridges()
        return records

    def write(self, vals):
        result = super().write(vals)
        watched = {'start_datetime', 'end_datetime', 'duration_minutes', 'staff_id',
                   'state', 'block_type_id', 'name', 'branch_id', 'works_at_branch_id'}
        if watched & set(vals) and not self.env.context.get('skip_salon_block_bridges'):
            self._sync_bridges()
        return result

    def unlink(self):
        slots = self.planning_slot_id
        leaves = self.leave_id
        result = super().unlink()
        if slots:
            slots.sudo().unlink()
        for leave in leaves:
            try:
                leave.sudo().action_refuse()
            except Exception:  # noqa: BLE001
                pass
        return result

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_open_planning_slot(self):
        self.ensure_one()
        if not self.planning_slot_id:
            raise UserError(_("This block has no Planning shift."))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'planning.slot',
            'res_id': self.planning_slot_id.id,
            'view_mode': 'form',
        }

    def action_open_leave(self):
        self.ensure_one()
        if not self.leave_id:
            raise UserError(_("This block has no Time Off request."))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.leave',
            'res_id': self.leave_id.id,
            'view_mode': 'form',
        }

    @api.depends('name', 'staff_id', 'start_datetime')
    def _compute_display_name(self):
        for rec in self:
            who = rec.staff_id.name or ''
            rec.display_name = f"{rec.name or _('Block')} - {who}" if who else (rec.name or _('Block'))

    # ------------------------------------------------------------------
    # Scheduler helper
    # ------------------------------------------------------------------
    @api.model
    def scheduler_create(self, vals):
        """Quick-create from the timeline board."""
        block_type = self.env['salon.block.type'].browse(vals.get('block_type_id'))
        if not block_type.exists():
            block_type = self.env['salon.block.type'].search([], limit=1)
            if not block_type:
                raise UserError(_("Create a block type first."))
        start = fields.Datetime.from_string(vals['start_datetime'])
        minutes = vals.get('duration_minutes') or block_type.default_duration_minutes or 60
        from datetime import timedelta
        vals_create = {
            'block_type_id': block_type.id,
            'staff_id': int(vals['staff_id']),
            'start_datetime': start,
            'end_datetime': start + timedelta(minutes=minutes),
            'duration_minutes': minutes,
            'note': vals.get('note') or False,
        }
        if vals.get('branch_id'):
            # The branch picked on the board, so the new block stays visible there.
            vals_create['branch_id'] = int(vals['branch_id'])
            vals_create['company_id'] = int(vals['branch_id'])
        if block_type.target_branch_id:
            vals_create['works_at_branch_id'] = block_type.target_branch_id.id
        record = self.create(vals_create)
        return record.id
