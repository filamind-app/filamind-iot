{
    'name': 'Filamind POS IoT',
    'version': '19.0.2.0.0',
    'category': 'Point of Sale',
    'summary': 'Connect Odoo POS to filamind IoT Boxes (printer, scale, '
               'scanner(s), customer display, payment terminal, kitchen printer).',
    'description': """
Filamind POS IoT
================
Bridges Odoo's Point of Sale module with the filamind-iot IoT gateway.

What it adds (v0.2.0)
---------------------
* Per pos.config:
  ``iot_box_id``, ``iot_printer_id``, ``iot_scale_id``,
  ``iot_scanner_ids`` (m2m — multiple scanners), ``iot_scanner_id``
  (deprecated m2o), ``use_iot_box`` (boolean toggle),
  ``iot_customer_display_id``, ``iot_cash_drawer_id``.
* Per pos.printer (kitchen / bar): ``iot_device_id`` + ``iot_use_lna``
  so order tickets dispatch via the IoT Box rather than over IPP.
* Per pos.payment.method: ``iot_terminal_id`` (deprecated alias,
  use iot_device_id from Phase 12+).
* ``pos.session.action_print_receipt(order_id)`` and
  ``pos.session.update_iot_customer_display(payload)`` server methods.
""",
    'author': 'filamind',
    'website': 'https://github.com/filamind-app/filamind-iot',
    'depends': ['filamind_iot', 'point_of_sale', 'pos_restaurant'],
    'data': [
        'views/pos_config_views.xml',
        'views/pos_payment_method_views.xml',
        'views/pos_printer_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
