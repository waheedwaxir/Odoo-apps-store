{
    'name': 'Real Time Stock Inventory Valuation Dashboard',
    'version': '19.0.1.1.4',
    'summary': 'Advanced Stock Valuation, Financial Summaries, & Multilingual Inventory Dashboard',
    'description': """
Real-Time Stock Inventory Valuation Dashboard
===========================================

Provides a comprehensive, real-time dashboard for inventory management.

Key Features:
-------------
* **Financial & Valuation Summaries:** Instantly view Beginning Balance, Inventory Adjustments, Exact COGS, Gross Profit, and Sales Revenue.
* **Interactive Drill-Downs:** Click on any summary card (e.g., Inventory Adjustments, COGS, Stock Alerts) to jump directly into the exact underlying stock moves and product records.
* **Multilingual Support:** Fully compatible with Odoo's translation system (includes comprehensive Arabic translation).
* **Odoo 19 Ready:** Modernized valuation drill-downs leveraging Odoo 19's updated `stock.move` valuation structure.
* **Colorful & Formatted PDF Reports:** Generate clean, easy-to-read PDF reports for Product Stock Summaries directly from the dashboard.
* **Actionable Stock Alerts:** Immediate visibility into Low Stock, Overstock, and Negative Stock with one-click "View All" functionality.
    """,
    'category': 'Inventory/Inventory',
    'author': 'Engr Waheed',
    'depends': ['stock', 'stock_account', 'sale_management', 'purchase', 'account', 'web'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/dashboard_views.xml',
        'reports/product_report.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'wu_stock_valuation_dashboard/static/src/components/**/*.js',
            'wu_stock_valuation_dashboard/static/src/components/**/*.xml',
            'wu_stock_valuation_dashboard/static/src/components/**/*.scss',
        ],
    },
        'images': ['static/description/banner.png'],
    'price': 49.00,
    'currency': 'USD',
    'support': 'waheedwazir566@gmail.com',
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
