{
    'name': 'Filamind IoT',
    'version': '19.0.4.0.0',
    'category': 'Productivity/IoT',
    'summary': 'Self-hosted IoT gateway for Odoo — pairs with the filamind-iotbox image',
    'description': """
Filamind IoT
============
A self-hosted Internet-of-Things gateway for Odoo 19, designed to pair with
the filamind-iotbox Raspberry Pi image
(https://github.com/filamind-app/filamind-iotbox). Inspired by — but
independent of — Odoo's stock IoT app.

Key Features
------------
* IoT Box management — register and monitor gateways
* Supported devices: receipt printers, label printers, barcode scanners,
  electronic scales, digital cameras, customer displays, payment terminals,
  fiscal data modules, measuring tools, and generic USB/HID devices
* Dual pairing workflow — short code from server OR token displayed on box
* Auto-discovery of devices attached to a box
* Per-device status, heartbeat and activity log
* Usage across POS, Sales, Inventory and Manufacturing
* REST-style endpoints (/filamind_iot/*) plus /iot/box/* aliases for
  drop-in compatibility with the filamind-iotbox image
* Dedicated configuration / settings page
* Full chatter audit trail on every box and device
    """,
    'author': 'filamind',
    'website': 'https://github.com/filamind-app/filamind-iot',
    'depends': ['base', 'mail', 'web', 'bus'],
    'data': [
        'security/iot_security.xml',
        'security/ir.model.access.csv',
        'data/iot_sequence.xml',
        'data/iot_device_type_data.xml',
        'data/iot_cron.xml',
        'views/iot_device_type_views.xml',
        'wizard/iot_pairing_wizard_views.xml',
        'views/iot_box_views.xml',
        'views/iot_device_views.xml',
        'views/iot_connection_log_views.xml',
        'views/iot_command_queue_views.xml',
        'views/iot_config_settings_views.xml',
        'views/iot_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'filamind_iot/static/src/css/iot_backend.css',
        ],
    },
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'images': ['static/description/banner.png'],
}
