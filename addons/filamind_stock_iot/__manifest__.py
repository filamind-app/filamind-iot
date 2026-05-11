{
    'name': 'Filamind Stock IoT',
    'version': '19.0.2.0.0',
    'category': 'Inventory',
    'summary': 'Warehouse-side IoT hooks: barcode scanners, label printers, '
               'and scales attached to filamind IoT Boxes.',
    'description': """
Filamind Stock IoT
==================
* Per-warehouse defaults: ``stock.warehouse.iot_box_id``,
  ``iot_label_printer_id``, ``iot_scale_id``, ``iot_barcode_scanner_id``.
* ``stock.picking.action_print_iot_label`` — push the picking's label
  template to the IoT label printer (cab Squix, Zebra, Brother, …).
* ``stock.picking.action_iot_weigh_package`` — capture a weight reading
  from the warehouse scale into ``stock.move.line`` ``shipping_weight``.
* ``stock.picking.type.iot_scale_ids`` (NEW v0.2.0) — m2m of scales
  available for a given operation type (mirrors Enterprise
  delivery_iot).
* Generic helpers any other inventory flow can call.
""",
    'author': 'filamind',
    'website': 'https://github.com/filamind-app/filamind-iot',
    'depends': ['filamind_iot', 'stock'],
    'data': [
        'views/stock_warehouse_views.xml',
        'views/stock_picking_views.xml',
        'views/stock_picking_type_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
