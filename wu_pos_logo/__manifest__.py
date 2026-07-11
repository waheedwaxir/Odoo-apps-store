# -*- coding: utf-8 -*-
{
    'name': 'POS Logo And Screen Saver',
    'version': '19.0.1.1.0',
    'category': 'Point of Sale',
    'summary': 'Personalize your POS branding with custom POS header logo, custom receipt printed logo, and idle screen saver background image or GIF.',
    'description': """
POS Logo & Screen Saver Configuration
=====================================
Personalize your Point of Sale - your brand, your way!
Replace the default Odoo POS logo with your company logo, a custom image, or choose to hide it entirely from both the top header navbar and printed customer receipts. Easily update your POS screen branding to match your business identity. Set a custom screen saver image or GIF for idle POS screens, creating a polished, professional in-store experience. Enhance your brand presence at every transaction with the POS Logo & Screen Saver module.

Features:
- Custom POS Header Logo: Replace the default Odoo POS navbar logo with your company logo or a custom uploaded image.
- Hide POS Header Logo: Option to completely hide the logo from your POS top navbar for a clean, distraction-free interface.
- Custom Receipt Logo: Override the printed customer receipt (OrderReceipt ticket) logo with your company logo or a custom high-res image.
- Hide Receipt Logo on Print Ticket: Option to remove the logo from printed customer tickets and receipts for a clean text-only receipt.
- Screen Saver Configuration: Enable custom screen saver background image/GIF, custom timer color, and screen idle timer duration in minutes.

Developed by Engr Waheed
LinkedIn: https://www.linkedin.com/in/waheed-ullah-810082151
WhatsApp: +97430643395
    """,
    'author': 'Engr Waheed',
    'depends': ['point_of_sale'],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'wu_pos_logo/static/src/**/*',
        ],
    },
    'images': [
        'static/description/banner.png',
        'static/description/thumbnail.png',
        'static/description/icon.png',
        'static/description/screenshot_settings_1.png',
        'static/description/screenshot_settings_2.png',
        'static/description/screenshot_register.png',
        'static/description/screenshot_checkout.png',
        'static/description/screenshot_ticket_closeup.png',
        'static/description/screenshot_config.png',
        'static/description/screenshot_saverscreen.png',
        'static/description/screenshot_receipt.png',
        'static/description/screenshot_navbar.png',
    ],
    'price': 5.00,
    'currency': 'USD',
    'license': 'OPL-1',
    'installable': True,
    'application': False,
    'auto_install': False,
}

