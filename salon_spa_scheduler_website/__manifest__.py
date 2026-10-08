{
    'name': 'Salon & Spa Management - Online Booking',
    'version': '19.0.1.3.0',
    'category': 'Services/Appointment',
    'summary': 'Website online booking engine for the Salon & Spa Management module.',
    'description': """
Salon & Spa Management - Online Booking
======================================
Bridge module that adds the customer-facing website booking page
(``/salon/booking``) to the Salon & Spa Management application.

It is installed automatically whenever both **Salon & Spa Management**
(``salon_spa_scheduler``) and the **Website** app are present, so the core
module no longer needs a hard dependency on ``website``. Uninstall this module
to remove the public booking page while keeping the rest of the app intact.
    """,
    'author': 'Engr Waheed, Techman Solutions',
    'website': 'https://www.techmansolutions.com',
    'license': 'LGPL-3',
    'images': [
        'static/description/banner.png',
        'static/description/icon.png',
        'static/description/screenshots/14_website_online_booking.png',
    ],
    'depends': ['salon_spa_scheduler', 'website', 'google_recaptcha'],
    'data': [
        'views/website_booking_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'salon_spa_scheduler_website/static/src/js/salon_booking.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': True,
}
