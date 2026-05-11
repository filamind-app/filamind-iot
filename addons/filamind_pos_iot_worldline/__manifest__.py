{
    'name': 'Filamind POS IoT — Worldline Payment Terminals',
    'version': '19.0.1.0.0',
    'category': 'Sales/Point of Sale',
    'summary': 'Worldline (CTEP / Sips Sherlocks) payment terminal '
               'support for filamind_pos_iot. Community alternative to '
               'Enterprise pos_iot_worldline.',
    'description': """
Filamind POS IoT — Worldline Payment Terminals
==============================================
Adds Worldline CTEP / Sips-Sherlocks payment terminal support
to filamind_pos_iot. Worldline is a Six-owned acquirer/PSP whose
terminals speak the CTEP (Card Terminal Exchange Protocol) family.

Community alternative to Enterprise `pos_iot_worldline` (OEEL-1).

What it adds
------------
* Vendor selector on `pos.payment.method` — when set to ``worldline``,
  the IoT request payload includes Worldline-specific fields:
    - ``terminal_address`` (TID + IP-or-USB-path).
    - ``transaction_type`` (``purchase`` | ``refund`` | ``cancel``
      | ``preauth`` | ``capture``).
    - ``language`` for cardholder prompts.
    - ``manual_entry_allowed`` for keyed PAN fallback.
* Per-payment-method config:
    - ``iot_worldline_terminal_id`` — TID assigned by Worldline.
    - ``iot_worldline_protocol`` — ``ctep`` (USB/serial) or
      ``cless_evo`` (network).
    - ``iot_worldline_currency_code`` — ISO-4217 numeric (e.g.
      ``978`` for EUR) baked into the terminal's config; the addon
      exposes it for cross-checking with the POS journal.
* Capture from terminal response on ``pos.payment``:
    - ``iot_worldline_authorization_code`` — issuer auth code.
    - ``iot_worldline_card_brand``.
    - ``iot_worldline_card_last4``.
    - ``iot_worldline_emv_aid``.
    - ``iot_worldline_emv_tvr`` — Terminal Verification Results.
    - ``iot_worldline_emv_tsi`` — Transaction Status Information.
    - ``iot_worldline_signature_required``.

Out of scope (deliberately)
---------------------------
* The CTEP protocol implementation lives on the IoT Box itself
  (the box's Worldline driver speaks CTEP to the terminal).
  This addon is the server-side data layer + UI only.
""",
    'author': 'filamind',
    'website': 'https://github.com/filamind-app/filamind-iot',
    'depends': ['filamind_pos_iot'],
    'data': [
        'views/pos_payment_method_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
