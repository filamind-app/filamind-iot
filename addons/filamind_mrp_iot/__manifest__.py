{
    'name': 'Filamind MRP IoT',
    'version': '19.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Connect manufacturing work centers to filamind IoT Boxes — '
               'measurement tools, label printers, drawer relays.',
    'description': """
Filamind MRP IoT
================
* Per-workcenter defaults: ``mrp.workcenter.iot_box_id``,
  ``iot_label_printer_id``, ``iot_caliper_id``, ``iot_scanner_id``.
* ``mrp.workorder.action_iot_capture_measurement`` — request a reading
  from the workcenter's caliper / measuring tool. Result lands on the
  related iot.command.queue entry; downstream modules can react via cron
  or extend ``record_response`` to push the reading into a quality.check.
* ``mrp.workorder.action_print_iot_label`` — print a work-order label.
""",
    'author': 'filamind',
    'website': 'https://github.com/filamind-app/filamind-iot',
    'depends': ['filamind_iot', 'mrp'],
    'data': [
        'views/mrp_workcenter_views.xml',
        'views/mrp_workorder_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
