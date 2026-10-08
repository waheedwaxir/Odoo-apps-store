{
    'name': ' Salon & Spa Management ',
    'version': '19.0.1.79.0',
    'category': 'Services/Appointment',
    'summary': 'POS Salon and Spa , Salon ,Complete Salon and Spa Setup ,Salon and spa system, Advanced dashboard , Advanced Salon and Spa Management with Scheduler, POS, Customer History, Tips, Memberships,Shift, Employee Shift , Product Arabic Name, Services, Packages, Time Blocks, Multi-Branch, Multi Language, Multi-Company and Reports.',
    'description': """
Salon & Spa Management
==============================
An enterprise-grade luxury salon and spa management application.

Key Features:
- Advanced Real-time Branch-wise Timeline Scheduler for staff allocations and bookings.
- Seamless Point of Sale (POS) integration for checkout and session-based payments.
- Multi-Service and Package Bookings handling multiple packages and lines.
- Online Website Booking Engine for customer-facing self-service reservations
  (optional: provided by the auto-installed "salon_spa_scheduler_website" bridge
  module whenever the Website app is installed).
- Automated Email & SMS Reminders via backend cron jobs (30-Minute Reminders).
- Treatment Rooms and Branches setup configuration.
- Staff allocation and beautician availability shift conflict checking.
- Member management and Membership Plans.
- Review and Feedback analytics collection.
- Commission Calculations for staff members based on fixed values or percentages.
- Time Blocks for non-customer time: training, meetings, breaks, duty at another
  branch and absences - shown on the scheduler, optionally published as Planning
  shifts and raised as Time Off.
- Advanced Reports: Multi-Branch & Multi-State filtered Appointments & Sales summary PDF reports.
- Granular Security Rights: View Only, Create Appointments, Create Payments, and Manager access levels.
    """,
    'author': 'Engr Waheed , Techman Solutions' ,
    'website': 'https://www.techman-solutions.com/',
    'license': 'LGPL-3',
    'price': 119.00,
    'currency': 'USD',
    'images': [
        'static/description/banner.png',
        'static/description/icon.png',
        'static/description/screenshots/02_analytics_dashboard.png',
        'static/description/screenshots/03_timeline_scheduler.png',
        'static/description/screenshots/13_security_groups_access.png',
        'static/description/screenshots/14_website_online_booking.png',
        'static/description/screenshots/15_services_steps.png'
    ],
    'depends': ['base', 'base_setup', 'mail', 'calendar', 'contacts', 'hr', 'hr_holidays', 'planning', 'point_of_sale', 'pos_discount', 'product', 'stock'],
    'data': [
        'security/salon_security.xml',
        'security/ir.model.access.csv',
        'security/salon_multicompany_rules.xml',
        'views/report_sale_details_views.xml',
        'data/sequences.xml',
        'data/mail_templates.xml',
        'data/cron_jobs.xml',
        'data/salon_block_type_data.xml',
        'data/pos_tip_data.xml',
        'data/membership_discount_data.xml',
        'reports/salon_reports.xml',
        'reports/salon_appointments_report_templates.xml',
        'reports/salon_staff_performance_report_templates.xml',
        'views/res_config_settings_views.xml',
        'views/salon_room_views.xml',
        'views/salon_block_type_views.xml',
        'views/salon_service_category_views.xml',
        'views/salon_service_views.xml',
        'views/salon_package_views.xml',
        'views/salon_membership_views.xml',
        'views/salon_commission_views.xml',
        'views/salon_review_views.xml',
        'views/res_partner_views.xml',
        'views/salon_staff_tip_views.xml',
        'wizards/salon_staff_import_wizard_views.xml',
        'views/salon_staff_views.xml',
        'views/salon_appointment_views.xml',
        'views/salon_block_views.xml',
        'views/salon_scheduler_action.xml',
        'wizards/salon_report_wizard_views.xml',
        'wizards/salon_staff_report_wizard_views.xml',
        'wizards/salon_client_report_wizard_views.xml',
        'wizards/salon_appointment_add_service_views.xml',
        'views/salon_product_template_views.xml',
        'views/salon_customer_history_views.xml',
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
            'salon_spa_scheduler/static/src/js/salon_staff_import_cog_menu.js',
            'salon_spa_scheduler/static/src/xml/salon_staff_import_cog_menu.xml',
        ],
        'web.assets_web_dark': [
            'salon_spa_scheduler/static/src/scss/salon_scheduler.dark.scss',
        ],
        'point_of_sale._assets_pos': [
            'salon_spa_scheduler/static/src/js/pos_patch.js',
            'salon_spa_scheduler/static/src/js/TipStaffPopup.js',
            'salon_spa_scheduler/static/src/js/TipStaffButton.js',
            'salon_spa_scheduler/static/src/js/BeauticianButton.js',
            'salon_spa_scheduler/static/src/xml/pos_tip_templates.xml',
            'salon_spa_scheduler/static/src/xml/salon_pos_sections.xml',
            'salon_spa_scheduler/static/src/js/salon_pos_navbar.js',
            'salon_spa_scheduler/static/src/xml/salon_pos_navbar.xml',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': True,
}
