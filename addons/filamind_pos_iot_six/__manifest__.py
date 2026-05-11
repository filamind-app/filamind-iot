{
    'name': 'Filamind POS IoT — Six Payment Terminals',
    'version': '19.0.1.0.0',
    'category': 'Sales/Point of Sale',
    'summary': 'Six (TIM Cloud / TIM Direct) payment terminal support '
               'for filamind_pos_iot. Community alternative to '
               'Enterprise pos_iot_six.',
    'description': """
Filamind POS IoT — Six Payment Terminals
========================================
Adds Six (Worldline-AG-owned, formerly SIX Payment Services)
TIM-protocol payment terminal support to filamind_pos_iot.

Community alternative to Enterprise `pos_iot_six` (OEEL-1).

What it adds
------------
* Vendor selector on `pos.payment.method` — when set to ``six``,
  the IoT request payload includes Six's TIM-specific fields:
    - ``terminal_id`` (TID, 8-char alphanumeric)
    - ``transaction_type`` (``purchase`` | ``refund`` | ``cancel``)
    - ``application_label`` for receipt printing
* Per-payment-method config:
    - ``iot_six_terminal_id`` — the TID assigned by Six.
    - ``iot_six_protocol`` — ``tim_direct`` (USB/serial) or
      ``tim_cloud`` (HTTPS).
    - ``iot_six_supports_tip`` — terminal-side tip prompting.
* Capture from terminal response on ``pos.payment``:
    - ``iot_six_transaction_id`` — Six's unique txn UUID.
    - ``iot_six_authorization_code`` — issuer auth code.
    - ``iot_six_card_brand`` — Visa / Mastercard / Maestro / etc.
    - ``iot_six_card_last4`` — last four digits (never the full PAN).
    - ``iot_six_emv_aid`` — EMV Application Identifier.
    - ``iot_six_signature_required`` — boolean for the cashier UX.

Out of scope (deliberately)
---------------------------
* The actual TIM protocol implementation — that lives on the IoT
  Box itself (the box's Six driver speaks TIM to the terminal).
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
