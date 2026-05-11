{
    'name': 'Filamind Quality IoT',
    'version': '19.0.1.0.0',
    'category': 'Quality',
    'summary': 'Quality control with IoT-driven measurements (caliper, scale, '
               'camera). Community alternative to Enterprise quality_iot + '
               'quality_control_iot.',
    'description': """
Filamind Quality IoT
====================
Quality control with IoT-driven measurements. The community LGPL-3
alternative to Odoo Enterprise's `quality_iot` + `quality_control_iot`
which are OEEL-1 and require the Enterprise `quality_control` module.

Built-in models (no Enterprise dependency):

* ``filamind.quality.point``  define a quality check point on a product
                              or operation. Test type = pass/fail,
                              measurement, or picture. Optional
                              ``iot_device_id`` to auto-pull the
                              measurement from a caliper / scale / camera.
* ``filamind.quality.check``  one captured measurement. Stores the
                              IoT command queue id so the user can
                              trace which device reading produced
                              which check.
* ``filamind.quality.alert``  open quality issue (defective product,
                              process problem). Tracks chatter +
                              activities.

Optional MRP integration: when ``mrp`` is installed, work orders gain
an ``Open Quality Checks`` button that lists the relevant
filamind.quality.point rows. Picture/measurement is auto-pulled from
the workcenter's iot.device when set.
""",
    'author': 'filamind',
    'website': 'https://github.com/filamind-app/filamind-iot',
    'depends': ['filamind_iot', 'product', 'mrp'],
    'data': [
        'security/ir.model.access.csv',
        'data/filamind_quality_data.xml',
        'views/filamind_quality_point_views.xml',
        'views/filamind_quality_check_views.xml',
        'views/filamind_quality_alert_views.xml',
        'views/filamind_quality_menus.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}
