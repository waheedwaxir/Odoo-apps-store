# -*- coding: utf-8 -*-
import datetime
from odoo import http, fields
from odoo.http import request

class SalonWebsiteBooking(http.Controller):

    @http.route(['/salon/booking'], type='http', auth="public", website=True)
    def booking_index(self, **kwargs):
        branches = request.env['salon.branch'].sudo().search([])
        services = request.env['salon.service'].sudo().search([('active', '=', True)])
        beauticians = request.env['salon.staff'].sudo().search([('active', '=', True)])
        
        values = {
            'branches': branches,
            'services': services,
            'beauticians': beauticians,
            'error': kwargs.get('error', ''),
            'success': kwargs.get('success', '')
        }
        return request.render("salon_spa_scheduler.website_booking_page", values)

    @http.route(['/salon/booking/submit'], type='http', auth="public", methods=['POST'], website=True, csrf=True)
    def booking_submit(self, **post):
        try:
            partner_name = post.get('customer_name')
            phone = post.get('phone')
            email = post.get('email')
            branch_id = int(post.get('branch_id')) if post.get('branch_id') else 0
            
            service_ids_raw = request.httprequest.form.getlist('service_ids')
            if not service_ids_raw and post.get('service_id'):
                service_ids_raw = [post.get('service_id')]
            service_ids = [int(sid) for sid in service_ids_raw if sid]
            
            staff_id = int(post.get('staff_id')) if post.get('staff_id') else 0
            start_date_str = post.get('booking_date') # YYYY-MM-DD
            start_time_str = post.get('booking_time') # HH:MM

            if not all([partner_name, phone, branch_id, service_ids, staff_id, start_date_str, start_time_str]):
                return request.redirect('/salon/booking?error=Please fill in all fields.')

            # Find or create partner
            partner = request.env['res.partner'].sudo().search([('phone', '=', phone)], limit=1)
            if not partner and email:
                partner = request.env['res.partner'].sudo().search([('email', '=', email)], limit=1)
            if not partner:
                partner = request.env['res.partner'].sudo().create({
                    'name': partner_name,
                    'phone': phone,
                    'email': email,
                })

            # Calculate times in UTC based on staff/employee timezone
            start_dt_str = f"{start_date_str} {start_time_str}:00"
            start_datetime = datetime.datetime.strptime(start_dt_str, "%Y-%m-%d %H:%M:%S")

            staff = request.env['salon.staff'].sudo().browse(staff_id)
            if staff and staff.employee_id:
                import pytz
                tz_name = staff.employee_id.tz or staff.employee_id.resource_calendar_id.tz or 'UTC'
                try:
                    local_tz = pytz.timezone(tz_name)
                    local_dt = local_tz.localize(start_datetime)
                    start_datetime = local_dt.astimezone(pytz.utc).replace(tzinfo=None)
                except Exception:
                    pass

            services = request.env['salon.service'].sudo().browse(service_ids)
            total_duration = sum(s.duration for s in services)
            end_datetime = start_datetime + datetime.timedelta(hours=total_duration)

            # Create Appointment
            appointment = request.env['salon.appointment'].sudo().create({
                'partner_id': partner.id,
                'branch_id': branch_id,
                'service_ids': [(6, 0, service_ids)],
                'staff_id': staff_id,
                'start_datetime': start_datetime,
                'end_datetime': end_datetime,
                'state': 'confirmed',
                'is_walkin': False
            })

            return request.redirect(f'/salon/booking?success=Your booking has been scheduled successfully! Your Appointment Ref is {appointment.name}.')
        except Exception as e:
            request.env.cr.rollback()
            return request.redirect(f'/salon/booking?error=Error: {str(e)}')
