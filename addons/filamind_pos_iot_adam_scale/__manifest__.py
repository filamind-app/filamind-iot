{
    'name': 'Filamind POS IoT — Adam Equipment Scales',
    'version': '19.0.1.0.0',
    'category': 'Sales/Point of Sale',
    'summary': 'Adam Equipment scale (CPWplus / GFK / GBK series) '
               'support for filamind_pos_iot. Community alternative '
               'to Enterprise pos_iot_adam_scale.',
    'description': """
Filamind POS IoT — Adam Equipment Scales
========================================
Adds Adam Equipment scale support to filamind_pos_iot — covers the
CPWplus, GFK, GBK, GFC, and GBC series. Adam scales speak a small
ASCII serial protocol (the "AGN" command set) at 9600/8/N/1 by
default; the IoT Box's serial driver translates between that and
the iot.box bus.

Community alternative to Enterprise `pos_iot_adam_scale` (OEEL-1).

What it adds
------------
* Per-device config on `iot.device` (only meaningful on devices of
  type `scale`):
    - ``adam_model_family`` — ``cpwplus`` | ``gfk_gbk`` | ``gfc_gbc``.
    - ``adam_serial_baud`` — 9600 (default), 4800, 19200, 38400.
    - ``adam_unit_default`` — ``g`` | ``kg`` | ``lb`` | ``oz``.
    - ``adam_capacity_kg`` — for sanity-checking weights returned
      by the scale.
    - ``adam_supports_tare`` — gate the Tare button in the UI.
* `iot.device.action_iot_adam_zero()` — issue an AGN ``Z`` command
  (zero) to the configured scale.
* `iot.device.action_iot_adam_tare()` — issue an AGN ``T`` command
  (tare) on scales whose ``adam_supports_tare`` is set.
* `pos.config.iot_adam_check_capacity` — when set, the POS warns
  the cashier if a returned weight exceeds the scale's capacity
  (typically a sign of an overload or a misconfigured scale).

Out of scope (deliberately)
---------------------------
* The actual AGN serial command implementation lives on the IoT
  Box itself; this addon is the server-side data + UI layer only.
""",
    'author': 'filamind',
    'website': 'https://github.com/filamind-app/filamind-iot',
    'depends': ['filamind_pos_iot'],
    'data': [
        'views/iot_device_views.xml',
        'views/pos_config_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
