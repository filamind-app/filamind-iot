{
    'name': 'Filamind POS IoT',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Connect Odoo POS to filamind IoT Boxes (printer, scale, scanner, '
               'customer display, payment terminal).',
    'description': """
Filamind POS IoT
================
Bridges Odoo's Point of Sale module with the filamind-iot IoT gateway.

What it adds
------------
* Per pos.config M2O fields:
  ``iot_box_id``, ``iot_printer_id``, ``iot_scale_id``, ``iot_scanner_id``,
  ``iot_customer_display_id``, ``iot_payment_terminal_id``.
* Test buttons on pos.config form: print receipt, weigh on scale,
  test connection.
* ``pos.session.action_print_receipt(order_id)`` server method that pushes
  a rendered receipt to the configured IoT printer via the bus channel.
* ``pos.payment.method.iot_terminal_id`` to bind a payment method to a
  specific IoT-attached terminal.

What it deliberately does NOT add (yet)
---------------------------------------
* Frontend OWL components (live POS UI). These need browser-side hardware
  testing and are part of Phase 3b.
""",
    'author': 'filamind',
    'website': 'https://github.com/filamind-app/filamind-iot',
    'depends': ['filamind_iot', 'point_of_sale'],
    'data': [
        'views/pos_config_views.xml',
        'views/pos_payment_method_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
