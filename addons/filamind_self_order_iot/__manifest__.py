{
    'name': 'Filamind Self-Order IoT',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Self-Order kiosk + IoT printer / payment terminal — '
               'community alternative to Enterprise pos_self_order_iot.',
    'description': """
Filamind Self-Order IoT
=======================
Bridges the LGPL `pos_self_order` kiosk module with the filamind IoT
gateway. The community equivalent of Enterprise `pos_self_order_iot`
(OEEL-1).

What it adds
------------
* ``pos.config.self_order_iot_box_id``  the IoT Box dedicated to the
                                         kiosk (independent from the
                                         cashier-side iot_box_id).
* ``pos.config.self_order_iot_printer_id``  printer for the kiosk's
                                             confirmation ticket.
* ``pos.config.self_order_iot_terminal_id``  payment terminal exposed
                                              to the customer at the
                                              kiosk.
* ``pos.config.self_ordering_iot_available_iot_box_ids`` (o2m)
   compute-helper listing IoT boxes flagged ``can_be_kiosk`` —
   matches the field name used by upstream pos_self_order_iot for
   cross-import compatibility.
* On every paid kiosk order, push:
   1. a ticket to the kiosk's IoT printer (so the customer takes it
      to the counter / collection point);
   2. (already handled by filamind_kitchen_display) a ticket to any
      KDS linked to this POS.

Configuration
-------------
1. Install ``filamind_iot``, ``filamind_pos_iot``, and either
   ``pos_self_order`` (free) or both ``pos_self_order`` and
   ``pos_restaurant`` (also free) for restaurant kiosks.
2. Mark the relevant ``iot.box`` records with ``can_be_kiosk = True``.
3. On the kiosk's ``pos.config``, set ``self_order_iot_box_id`` and
   the printer / terminal pointers.
""",
    'author': 'filamind',
    'website': 'https://github.com/filamind-app/filamind-iot',
    'depends': [
        'filamind_iot',
        'filamind_pos_iot',
        'pos_self_order',
    ],
    'data': [
        'views/pos_config_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
