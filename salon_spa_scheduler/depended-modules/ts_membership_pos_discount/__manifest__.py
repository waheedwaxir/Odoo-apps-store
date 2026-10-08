{
    'name': 'Membership Plans & POS Discount',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Membership plans with a spend threshold: members get a discount line in the POS once their services reach it.',
    'description': """
Membership Plans & POS Discount
===============================
* Membership plans (name, tier, duration, price, discount %, minimum spend per session).
* Customer memberships (members) with start/end date and Active / Expired / Cancelled state,
  a Memberships tab on the customer and a Members list.
* In the POS, when the customer has an active membership and the *services* of the order
  reach the plan's minimum spend, a separate discount line named after the plan is added
  (products are never discounted by it). The line is recomputed on every order change.
* The POS order list is grouped into Services / Products (/ Tips) sections.
* POS setting "Discount Button on Services Only": the global Discount button
  (pos_discount) can be limited to services.

A product counts as a *service* when its Product Type is "Service".
    """,
    'author': 'Techman',
    'website': 'https://www.techman.qa',
    'license': 'LGPL-3',
    'depends': ['point_of_sale', 'pos_discount'],
    'data': [
        'security/ts_membership_security.xml',
        'security/ir.model.access.csv',
        'data/ts_membership_data.xml',
        'views/ts_membership_views.xml',
        'views/res_partner_views.xml',
        'views/res_config_settings_views.xml',
        'views/menu_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'ts_membership_pos_discount/static/src/js/pos_membership.js',
            'ts_membership_pos_discount/static/src/xml/pos_sections.xml',
        ],
    },
    'installable': True,
    'application': False,
}
