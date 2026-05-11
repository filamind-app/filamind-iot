{
    'name': 'Filamind MRP IoT',
    'version': '19.0.2.0.0',
    'category': 'Manufacturing',
    'summary': 'Connect manufacturing work centers to filamind IoT Boxes — '
               'measurement tools, label printers, key/scan triggers.',
    'description': """
Filamind MRP IoT v0.2.0
=======================
* Per-workcenter defaults: ``mrp.workcenter.iot_box_id``,
  ``iot_label_printer_id``, ``iot_caliper_id``, ``iot_scanner_id``,
  ``trigger_ids`` (NEW — IoT triggers).
* ``iot.trigger`` model (NEW) — bind a key/scan/measure event to one
  of 19 work-order actions. Action codes match Enterprise mrp_iot for
  cross-import compatibility.
* ``mrp.workorder.action_iot_capture_measurement`` — request a reading
  from the workcenter's caliper / measuring tool.
* ``mrp.workorder.action_print_iot_label`` — print a work-order label.
""",
    'author': 'filamind',
    'website': 'https://github.com/filamind-app/filamind-iot',
    'depends': ['filamind_iot', 'mrp'],
    'data': [
        'security/ir.model.access.csv',
        'views/mrp_workcenter_views.xml',
        'views/iot_trigger_views.xml',
        'views/mrp_workorder_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
