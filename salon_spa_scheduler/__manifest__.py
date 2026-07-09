{
    'name': 'Salon & Spa Management',
    'version': '19.0.1.0.0',
    'category': 'Services/Appointment',
    'summary': 'Advanced Salon and Spa Management with Scheduler, POS, Customer History, Tips, Memberships, Packages, Multi-Branch and Reports.',
    'description': """
Salon & Spa Management
==============================
An enterprise-grade luxury salon and spa management application.

Key Features:
- Advanced Real-time Branch-wise Timeline Scheduler for staff allocations and bookings.
- Seamless Point of Sale (POS) integration for checkout and session-based payments.
- Multi-Service and Package Bookings handling multiple packages and lines.
- Online Website Booking Engine for customer-facing self-service reservations.
- Automated Email & SMS Reminders via backend cron jobs (30-Minute Reminders).
- Treatment Rooms and Branches setup configuration.
- Staff allocation and beautician availability shift conflict checking.
- Member management and Membership Plans.
- Review and Feedback analytics collection.
- Commission Calculations for staff members based on fixed values or percentages.
- Advanced Reports: Multi-Branch & Multi-State filtered Appointments & Sales summary PDF reports.
- Granular Security Rights: View Only, Create Appointments, Create Payments, and Manager access levels.
    """,
    'author': 'Engr Waheed',
    'website': 'https://www.techmansolutions.com',
    'license': 'LGPL-3',
    'price': 75.00,
    'currency': 'USD',
    'images': [
        'static/description/banner.png',
        'static/description/icon.png',
        'static/description/screenshots/02_analytics_dashboard.png',
        'static/description/screenshots/03_timeline_scheduler.png',
        'static/description/screenshots/13_security_groups_access.png',
        'static/description/screenshots/14_website_online_booking.png'
    ],
    'depends': ['base', 'mail', 'calendar', 'contacts', 'hr', 'point_of_sale', 'product', 'stock', 'website'],
    'data': [
        'security/salon_security.xml',
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'data/mail_templates.xml',
        'data/cron_jobs.xml',
        'data/pos_tip_data.xml',
        'reports/salon_reports.xml',
        'reports/salon_appointments_report_templates.xml',
        'reports/salon_staff_performance_report_templates.xml',
        'views/res_config_settings_views.xml',
        'views/salon_branch_views.xml',
        'views/salon_room_views.xml',
        'views/salon_service_views.xml',
        'views/salon_package_views.xml',
        'views/salon_membership_views.xml',
        'views/salon_commission_views.xml',
        'views/salon_review_views.xml',
        'views/res_partner_views.xml',
        'views/salon_staff_tip_views.xml',
        'views/salon_staff_views.xml',
        'views/salon_appointment_views.xml',
        'views/salon_scheduler_action.xml',
        'views/website_booking_templates.xml',
        'wizards/salon_report_wizard_views.xml',
        'wizards/salon_staff_report_wizard_views.xml',
        'views/salon_product_template_views.xml',
        'views/menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'salon_spa_scheduler/static/src/js/salon_scheduler.js',
            'salon_spa_scheduler/static/src/xml/salon_scheduler.xml',
            'salon_spa_scheduler/static/src/scss/salon_scheduler.scss',
            'salon_spa_scheduler/static/src/js/salon_dashboard.js',
            'salon_spa_scheduler/static/src/xml/salon_dashboard.xml',
            'salon_spa_scheduler/static/src/scss/salon_dashboard.scss',
        ],
        'point_of_sale._assets_pos': [
            'salon_spa_scheduler/static/src/js/pos_patch.js',
            'salon_spa_scheduler/static/src/js/TipStaffPopup.js',
            'salon_spa_scheduler/static/src/js/TipStaffButton.js',
            'salon_spa_scheduler/static/src/xml/pos_tip_templates.xml',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': True,
}
