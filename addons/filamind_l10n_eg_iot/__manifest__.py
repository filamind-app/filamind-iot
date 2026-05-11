{
    'name': 'Filamind Egypt Fiscal IoT',
    'version': '19.0.1.0.0',
    'category': 'Localization/Egypt',
    'summary': 'Route POS receipts through an ETA-signed fiscal device '
               'on the IoT Box, and capture the device-issued signature '
               'for later e-receipt submission.',
    'description': """
Filamind Egypt Fiscal IoT
=========================
Egypt's Tax Authority (ETA) requires retail receipts (B2C) to carry a
device-issued cryptographic signature. The signing can happen either
in cloud software (e-receipts API) or in a hardware "fiscal printer"
that signs each ticket locally and hands back a UUID + QR data block.

This addon does the IoT-side wiring for the **hardware path**:

* Adds ``pos.config.iot_eg_fiscal_printer_id`` — the receipt printer
  device to route fiscal receipts through (filtered to subtype
  containing "fiscal" or to the dedicated Fiscal Data Module type).
* Hooks ``pos.order.action_pos_order_paid``: when the order is paid
  on a config with a fiscal printer set, the order body is sent via
  ``iot.box.send_bus_message`` with ``action=fiscal_print`` and the
  command queue id is stored on the order.
* Adds ``pos.order.iot_eg_fiscal_uuid`` and ``iot_eg_fiscal_qr`` to
  hold the signature data once the box reports back. A downstream
  l10n_eg_eta_edi addon (out of scope here) is expected to read
  these fields and submit them to ETA.

Out of scope (deliberately)
---------------------------
* The actual ETA submission API — that belongs in a localization
  EDI addon, not in IoT plumbing.
* Server-side signing — this addon assumes a hardware fiscal printer.
  For software signing, integrate with l10n_eg_eta_edi directly.
""",
    'author': 'filamind',
    'website': 'https://github.com/filamind-app/filamind-iot',
    'depends': ['filamind_pos_iot', 'l10n_eg'],
    'data': [
        'views/pos_config_views.xml',
        'views/pos_order_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
