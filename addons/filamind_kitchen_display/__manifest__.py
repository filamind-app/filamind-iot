{
    'name': 'Filamind Kitchen Display',
    'version': '19.0.2.0.0',
    'category': 'Point of Sale',
    'summary': 'Tablet-friendly Kitchen Display System (KDS) for restaurants — '
               'community alternative to Enterprise pos_restaurant_preparation_display.',
    'description': """
Filamind Kitchen Display (KDS)
==============================
A tablet-first web view that shows pending kitchen tickets in real time.
Mirror of Odoo Enterprise's pos_restaurant_preparation_display family
of modules, released under LGPL-3 with no Enterprise subscription
needed.

Models
------
* filamind.kitchen.display    — one row per kitchen station tablet.
                                Has access_token for password-less URL.
* filamind.kitchen.stage      — workflow columns (in-progress / ready /
                                served).
* filamind.kitchen.order      — orders shown on a display, linked to
                                pos.order.
* filamind.kitchen.line       — order line items (product + qty + note).

URLs
----
* /filamind_kitchen/<int:display_id>?access_token=<tok>   public URL
  the tablet bookmarks. No login.
* /filamind_kitchen/transition                            move an order
  between stages (called by the OWL frontend).

Integration
-----------
* pos.config.filamind_kitchen_display_ids   m2m of displays a POS
                                            sends new orders to.
* pos.order paid -> auto-creates kitchen.order(s) on matching displays.
* Optional: also push a print job to pos.printer.iot_device_id (from
  filamind_pos_iot v0.2.0+) for paper kitchen tickets.

Notes
-----
* The OWL frontend single-page app is intentionally minimal in v0.1.0
  (auto-refreshing list grouped by stage). Drag-and-drop + bus.bus
  live updates are scheduled for v0.2.0.
* Multi-course meals (restaurant.order.course) are stub-supported via
  filamind.kitchen.course.
""",
    'author': 'filamind',
    'website': 'https://github.com/filamind-app/filamind-iot',
    'depends': [
        'point_of_sale',
        'pos_restaurant',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/filamind_kitchen_data.xml',
        'views/filamind_kitchen_display_views.xml',
        'views/filamind_kitchen_order_views.xml',
        'views/pos_config_views.xml',
        'views/filamind_kitchen_menus.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'filamind_kitchen_display/static/src/css/kitchen.css',
            'filamind_kitchen_display/static/src/js/kitchen.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
