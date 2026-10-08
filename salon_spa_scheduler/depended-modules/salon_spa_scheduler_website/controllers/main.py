# -*- coding: utf-8 -*-
import datetime
import json
import logging
from urllib.parse import urlencode

import pytz

from odoo import http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)

# Start times on the same 15-minute grid as the backend scheduler
# (scheduler_data's slot_minutes), so every time reception could book is
# offered online too.
SLOT_STEP_MINUTES = 15


class SalonWebsiteBooking(http.Controller):

    def _redirect(self, **params):
        """Safe redirect back to the booking page with URL-encoded params."""
        url = '/salon/booking'
        if params:
            url += '?' + urlencode({k: v for k, v in params.items() if v})
        return request.redirect(url)

    @http.route(['/salon/booking'], type='http', auth="public", website=True, sitemap=True)
    def booking_index(self, **kwargs):
        company = request.env.company
        company_domain = [('company_id', 'in', [False, company.id])]
        # Branches are companies: this website's company and any of its branches.
        branches = request.env['res.company'].sudo().search([('id', 'child_of', company.id)])
        services = request.env['salon.service'].sudo().search(
            [('active', '=', True), ('is_addon', '=', False)] + company_domain)
        # Everyone who can be booked online; the page hides the ones who do
        # not do the picked services, and the times step shows who is at work.
        beauticians = self._bookable_staff(request.env['salon.service'])

        values = {
            'branches': branches,
            'services': services,
            'beauticians': beauticians,
            'error': kwargs.get('error', ''),
            'success': kwargs.get('success', ''),
        }
        return request.render("salon_spa_scheduler_website.website_booking_page", values)

    def _json(self, payload, status=200):
        return request.make_response(
            json.dumps(payload), status=status,
            headers=[('Content-Type', 'application/json')])

    # ------------------------------------------------------------------
    # Availability - the same rules as the backend scheduler
    # ------------------------------------------------------------------
    def _salon_tz(self):
        """The salon's wall clock. Every time the customer sees or picks is
        in it, whatever timezone their own browser is in."""
        company = request.env.company.sudo()  # the public user cannot read it
        return pytz.timezone(company.partner_id.tz or company.resource_calendar_id.tz or 'UTC')

    def _parse_services(self, raw):
        company = request.env.company
        ids = [int(s) for s in (raw or '').split(',') if s.strip().isdigit()]
        return request.env['salon.service'].sudo().search([
            ('id', 'in', ids), ('active', '=', True),
            ('company_id', 'in', [False, company.id])])

    def _bookable_staff(self, services, staff_id=None):
        """Beauticians a customer may book online for ``services``.

        Only those linked to an employee: on the scheduler that is what puts
        a beautician under Planning, and a published shift is what says they
        are at work. A beautician whose services are limited must do every
        one picked (an empty list means they do everything).
        """
        company = request.env.company
        domain = [('active', '=', True), ('employee_id', '!=', False),
                  ('company_id', 'in', [False, company.id])]
        if staff_id:
            domain.append(('id', '=', staff_id))
        staff = request.env['salon.staff'].sudo().search(domain, order='sequence, name')
        return staff.filtered(
            lambda s: not s.effective_service_ids or not (services - s.effective_service_ids))

    def _day_availability(self, staff, day, duration):
        """Free start times on ``day`` for each of ``staff`` who is at work.

        Mirrors the scheduler board: a beautician is at work when they have a
        published Planning shift that day, and a time is free when the whole
        treatment fits inside one of those shifts without touching anything
        on their column - a booking (draft ones too: an online request holds
        its time until reception confirms or cancels it), one of its steps,
        or a time block (break, leave, training, duty at the other branch).

        Returns ``[{'staff': record, 'shift_hint': '10:00-19:00',
        'slots': ['10:00', ...]}]`` for the beauticians on shift, in board
        order. Times are the salon's local wall clock.
        """
        tz = self._salon_tz()
        company = request.env.company
        env = request.env

        def to_utc(local_naive):
            return tz.localize(local_naive).astimezone(pytz.utc).replace(tzinfo=None)

        def to_local(utc_naive):
            return pytz.utc.localize(utc_naive).astimezone(tz).replace(tzinfo=None)

        day_start = to_utc(datetime.datetime.combine(day, datetime.time.min))
        day_end = to_utc(datetime.datetime.combine(day + datetime.timedelta(days=1), datetime.time.min))
        if not staff:
            return []

        shifts = {}
        for slot in env['planning.slot'].sudo().search([
                ('employee_id', 'in', staff.employee_id.ids),
                ('company_id', 'child_of', company.id),
                ('state', '=', 'published'),
                ('start_datetime', '<', day_end),
                ('end_datetime', '>', day_start)], order='start_datetime'):
            shifts.setdefault(slot.employee_id.id, []).append(
                (slot.start_datetime, slot.end_datetime))

        # Bookings are read the way scheduler_data() draws them, not from the
        # stored step times alone: a step may have no end saved (or no start),
        # and the board then places it after the previous step and gives it
        # its duration. Searching steps by their stored times missed those,
        # and offered a gap the board shows as taken.
        busy = {s.id: [] for s in staff}
        appointments = env['salon.appointment'].sudo().search([
            ('state', '!=', 'cancel'),
            ('start_datetime', '<', day_end),
            ('end_datetime', '>', day_start)])
        for appt in appointments:
            if appt.step_ids:
                cursor = appt.start_datetime
                for step in appt.step_ids.sorted('sequence'):
                    begin = step.start_datetime or cursor
                    end = step.end_datetime or (
                        begin + datetime.timedelta(minutes=step.duration_minutes or 30))
                    cursor = end
                    if step.need_staff and step.staff_id.id in busy:
                        busy[step.staff_id.id].append((begin, end))
            else:
                end = appt.end_datetime or (
                    appt.start_datetime + datetime.timedelta(hours=appt.duration or 1.0))
                for member in (appt.staff_ids or appt.staff_id):
                    if member.id in busy:
                        busy[member.id].append((appt.start_datetime, end))
        blocks = env['salon.block'].sudo().search([
            ('state', '!=', 'cancel'),
            ('staff_id', 'in', staff.ids),
            ('block_type_id.blocks_booking', '=', True),
            ('start_datetime', '<', day_end),
            ('end_datetime', '>', day_start)])
        for block in blocks:
            busy[block.staff_id.id].append((block.start_datetime, block.end_datetime))

        now = datetime.datetime.utcnow()
        step = datetime.timedelta(minutes=SLOT_STEP_MINUTES)
        result = []
        for member in staff:
            ranges = shifts.get(member.employee_id.id)
            if not ranges:
                continue  # not at work that day
            taken = busy[member.id]
            starts = set()
            for shift_start, shift_end in ranges:
                # Start on the scheduler's quarter-hour grid, not at whatever minute
                # the shift happens to begin.
                local = to_local(shift_start)
                offset = (local.minute * 60 + local.second) % (SLOT_STEP_MINUTES * 60)
                cursor = local + datetime.timedelta(
                    seconds=(SLOT_STEP_MINUTES * 60 - offset) if offset else 0)
                while True:
                    begin = to_utc(cursor)
                    end = begin + duration
                    if end > shift_end:
                        break
                    if begin >= now and begin >= day_start and begin < day_end \
                            and not any(b0 < end and b1 > begin for b0, b1 in taken):
                        starts.add(cursor.strftime('%H:%M'))
                    cursor += step
            result.append({
                'staff': member,
                # dict.fromkeys: the same shift published twice reads once.
                'shift_hint': ", ".join(dict.fromkeys(
                    "%s-%s" % (to_local(s0).strftime('%H:%M'), to_local(s1).strftime('%H:%M'))
                    for s0, s1 in ranges)),
                'slots': sorted(starts),
            })
        return result

    @staticmethod
    def _duration(services):
        return datetime.timedelta(hours=sum(services.mapped('duration')) or 1.0)

    @http.route(['/salon/booking/availability'], type='http', auth="public",
                methods=['GET'], website=True, csrf=False, sitemap=False)
    def booking_availability(self, **kwargs):
        """Free times on one day, per beautician at work - read live from the
        scheduler, so what the customer is offered is what reception sees."""
        try:
            day = datetime.datetime.strptime(kwargs.get('date') or '', "%Y-%m-%d").date()
            staff_id = int(kwargs.get('staff_id') or 0)
        except (TypeError, ValueError):
            return self._json({'error': "Please pick a valid date."}, status=400)
        services = self._parse_services(kwargs.get('service_ids'))
        if not services:
            return self._json({'error': "Please select at least one service first."}, status=400)
        today = datetime.datetime.now(self._salon_tz()).date()
        if day < today:
            return self._json({'error': "Please pick today or a later day."}, status=400)

        staff = self._bookable_staff(services, staff_id or None)
        if staff_id and not staff:
            return self._json({'error': "This beautician is not available for these services."}, status=404)
        duration = self._duration(services)
        rows = self._day_availability(staff, day, duration)

        def payload(rows_):
            return [{'id': r['staff'].id, 'name': r['staff'].name,
                     'shift_hint': r['shift_hint'], 'slots': r['slots']} for r in rows_]

        free = [r for r in rows if r['slots']]
        message = ''
        next_date = False
        if not free:
            if staff_id:
                message = ("%s is not at work on this day." % staff.name) if not rows \
                    else ("%s is fully booked on this day." % staff.name)
            else:
                message = "No free times on this day."
            # Point the customer at the next day that has room.
            for ahead in range(1, 31):
                later = day + datetime.timedelta(days=ahead)
                if any(r['slots'] for r in self._day_availability(staff, later, duration)):
                    next_date = later.strftime('%Y-%m-%d')
                    break

        return self._json({
            'date': day.strftime('%Y-%m-%d'),
            'today': today.strftime('%Y-%m-%d'),
            'staff': payload(free),
            'message': message,
            'next_date': next_date,
        })

    @http.route(['/salon/booking/submit'], type='http', auth="public",
                methods=['POST'], website=True, csrf=True, sitemap=False)
    def booking_submit(self, **post):
        # Honeypot: real users never see or fill this field; bots do.
        if post.get('contact_url'):
            return self._redirect(success="Your booking request has been received.")

        # Google reCAPTCHA v3 (no-op if the admin has not configured keys).
        try:
            request.env['ir.http']._verify_request_recaptcha_token('salon_booking')
        except (UserError, ValidationError):
            return self._redirect(
                error="Anti-spam verification failed. Please reload the page and try again.")

        try:
            partner_name = (post.get('customer_name') or '').strip()
            phone = (post.get('phone') or '').strip()
            email = (post.get('email') or '').strip()
            try:
                branch_id = int(post.get('branch_id') or 0)
                staff_id = int(post.get('staff_id') or 0)
                service_ids_raw = request.httprequest.form.getlist('service_ids')
                if not service_ids_raw and post.get('service_id'):
                    service_ids_raw = [post.get('service_id')]
                service_ids = [int(sid) for sid in service_ids_raw if sid]
            except (TypeError, ValueError):
                return self._redirect(error="Please choose a valid branch, service and specialist.")

            start_date_str = post.get('booking_date')  # YYYY-MM-DD
            start_time_str = post.get('booking_time')  # HH:MM

            if not all([partner_name, phone, branch_id, service_ids, staff_id,
                        start_date_str, start_time_str]):
                return self._redirect(error="Please fill in all fields.")

            # Only accept branch / services / staff that belong to this website's
            # company (or are shared). Blocks stale or crafted cross-company POSTs.
            company = request.env.company
            company_domain = [('company_id', 'in', [False, company.id])]
            branch = request.env['res.company'].sudo().search(
                [('id', '=', branch_id), ('id', 'child_of', company.id)], limit=1)
            valid_services = request.env['salon.service'].sudo().search(
                [('id', 'in', service_ids), ('active', '=', True)] + company_domain)
            staff = self._bookable_staff(valid_services, staff_id)
            if not branch or not staff or len(valid_services) != len(set(service_ids)):
                return self._redirect(
                    error="Your selection is no longer available. Please start again.")

            try:
                start_local = datetime.datetime.strptime(
                    f"{start_date_str} {start_time_str}:00", "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return self._redirect(error="Please pick a valid date and time.")

            # The page may have been open a while: check the time against the
            # scheduler as it is now, with the same rules that offered it.
            duration = self._duration(valid_services)
            # Two customers sending the same time at once: the second waits
            # here until the first booking is saved, then sees it as taken.
            request.env.cr.execute(
                "SELECT id FROM salon_staff WHERE id = %s FOR UPDATE", [staff.id])
            rows = self._day_availability(staff, start_local.date(), duration)
            if not rows or start_local.strftime('%H:%M') not in rows[0]['slots']:
                return self._redirect(error=(
                    "Sorry, %s is no longer free at %s on %s. Please pick another time."
                    % (staff.name, start_time_str, start_date_str)))
            start_datetime = self._salon_tz().localize(start_local).astimezone(
                pytz.utc).replace(tzinfo=None)

            # Find or create the customer contact.
            partner = request.env['res.partner'].sudo().search(
                [('phone', '=', phone)], limit=1)
            if not partner and email:
                partner = request.env['res.partner'].sudo().search(
                    [('email', '=', email)], limit=1)
            if not partner:
                partner = request.env['res.partner'].sudo().create({
                    'name': partner_name,
                    'phone': phone,
                    'email': email or False,
                })

            end_datetime = start_datetime + duration

            # Created as draft: staff review and confirm before the customer is
            # emailed. Never auto-confirm an anonymous public submission.
            appointment = request.env['salon.appointment'].sudo().create({
                'company_id': company.id,
                'partner_id': partner.id,
                'branch_id': branch.id,
                'service_ids': [(6, 0, valid_services.ids)],
                'staff_id': staff.id,
                'start_datetime': start_datetime,
                'end_datetime': end_datetime,
                'state': 'draft',
                'is_walkin': False,
            })

            return self._redirect(success=(
                "Your booking request has been received. Reference: %s. "
                "Our team will confirm your appointment shortly." % appointment.name))
        except (UserError, ValidationError) as e:
            # Someone else booked the same slot, or the roster changed, between
            # the customer loading the page and submitting - surface the real
            # reason instead of a generic error so they can pick another time.
            request.env.cr.rollback()
            return self._redirect(error=str(e))
        except Exception:  # noqa: BLE001
            request.env.cr.rollback()
            _logger.exception("Salon website booking failed")
            return self._redirect(
                error="Something went wrong while saving your booking. Please try again "
                      "or contact the salon directly.")
