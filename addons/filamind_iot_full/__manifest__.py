{
    'name': 'Filamind IoT — Full Suite',
    'version': '19.0.1.0.0',
    'category': 'Internet of Things (IoT)',
    'summary': 'Umbrella meta-addon: install every filamind IoT addon '
               'in one click. Community LGPL-3 alternative to the full '
               '20-module Odoo Enterprise IoT stack.',
    'description': """
Filamind IoT — Full Suite
=========================
This is an umbrella addon — it ships **no models, no views, and
no code of its own**. Installing it installs every filamind IoT
addon at once, which is what most production deployments want.

Contents (every dependency is its own LGPL-3 addon)
---------------------------------------------------
* `filamind_iot` — core gateway (boxes, devices, channel, pairing,
  three transports).
* `filamind_pos_iot` — POS device wiring (printer, scale, scanner,
  customer display, cash drawer, payment terminal).
* `filamind_stock_iot` — Inventory (barcode scanners + scales on
  picking types).
* `filamind_mrp_iot` — Manufacturing (workcenter triggers + IoT
  measuring tools on quality steps).
* `filamind_kitchen_display` — KDS (LGPL replacement for
  Enterprise pos_kitchen_display).
* `filamind_quality_iot` — quality control with IoT-driven
  measurements (Community-only — Enterprise quality_control is
  re-implemented from scratch here).
* `filamind_self_order_iot` — kiosk-side IoT (printer + payment
  terminal at the kiosk).
* `filamind_event_iot` — attendee badge printing + barcode
  check-in for events.
* `filamind_l10n_eg_iot` — Egyptian Tax Authority (ETA) hardware
  fiscal printer routing.
* `filamind_pos_iot_six` — Six (TIM Cloud / TIM Direct) payment
  terminals.
* `filamind_pos_iot_worldline` — Worldline CTEP / Sips-Sherlocks
  payment terminals.
* `filamind_pos_iot_adam_scale` — Adam Equipment scales (CPWplus,
  GFK, GBK, GFC, GBC).
* `filamind_l10n_eu_iot_scale_cert` — EU MID / LNE certification
  metadata + audit log for legal-for-trade scales.

Out of scope
------------
* Vendor-specific drivers that ship on the IoT Box image — those
  live in `filamind-iotbox` and update independently.

License
-------
LGPL-3, like every filamind addon. The Enterprise stack equivalent
is OEEL-1 (proprietary) and bundled with the Enterprise edition.
""",
    'author': 'filamind',
    'website': 'https://github.com/filamind-app/filamind-iot',
    'depends': [
        'filamind_iot',
        'filamind_pos_iot',
        'filamind_stock_iot',
        'filamind_mrp_iot',
        'filamind_kitchen_display',
        'filamind_quality_iot',
        'filamind_self_order_iot',
        'filamind_event_iot',
        'filamind_l10n_eg_iot',
        'filamind_pos_iot_six',
        'filamind_pos_iot_worldline',
        'filamind_pos_iot_adam_scale',
        'filamind_l10n_eu_iot_scale_cert',
    ],
    'data': [],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}
