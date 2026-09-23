# -*- coding: utf-8 -*-
{
    'name': 'POS Single Line Categories',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Display POS product categories in a compact, single-line horizontal scrollable bar',
    'description': """
POS Single-Line Categories
==========================
Transforms the default multi-line category grid in Odoo 19 Point of Sale into an ultra-clean, single-line horizontal scrollable bar:
- Maximizes product grid screen space.
- Smooth horizontal scrolling with left/right navigation arrows.
- Touch swipe, mouse click-and-drag, and mouse wheel horizontal scrolling support.
- 12 soft pastel color badges for instant category distinction.
- Responsive quick-jump overflow dropdown menu.
- Configurable per POS in Point of Sale Settings.
- 100% Free & Open Source under LGPL-3.
    """,
    'author': 'Engr Waheed',
    'license': 'LGPL-3',
    'price': 0.0,
    'currency': 'EUR',
    'images': [
        'static/description/banner_cat.png',
        'static/description/pos_main_screen.png',
        'static/description/setting_pos.png',
        'static/description/thumbnails.png',
    ],
    'depends': ['point_of_sale'],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'wu_pos_categories/static/src/**/*',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
