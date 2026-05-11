"""Capture the Six terminal's response (transaction id, auth code,
card brand, etc.) on the matching pos.payment row."""
from odoo import fields, models


class PosPayment(models.Model):
    _inherit = 'pos.payment'

    iot_six_transaction_id = fields.Char(
        string='Six Transaction UUID', readonly=True, copy=False,
        help='Unique transaction identifier returned by the Six '
             'terminal — store for reconciliation with Six reports.',
    )
    iot_six_authorization_code = fields.Char(
        string='Authorization Code', readonly=True, copy=False,
        help='Issuer authorization code (typically 6 digits).',
    )
    iot_six_card_brand = fields.Char(
        string='Card Brand', readonly=True, copy=False,
        help='Visa / Mastercard / Maestro / AmEx / etc.',
    )
    iot_six_card_last4 = fields.Char(
        string='Card Last 4', readonly=True, copy=False,
        help='Last four digits of the PAN. The full PAN MUST NOT be '
             'stored — PCI-DSS forbids it outside of certified vaults.',
    )
    iot_six_emv_aid = fields.Char(
        string='EMV AID', readonly=True, copy=False,
        help='EMV Application Identifier (e.g. A0000000031010 for Visa).',
    )
    iot_six_signature_required = fields.Boolean(
        string='Signature Required', readonly=True,
        help='Set by the terminal when the issuer requires a paper '
             'signature on the merchant copy of the receipt.',
    )

    def _filamind_apply_six_response(self, response):
        """Called by the IoT controller / cron when the box reports the
        terminal's response. ``response`` is a dict with keys matching
        the field names above (without the ``iot_six_`` prefix)."""
        for payment in self:
            payment.sudo().write({
                'iot_six_transaction_id':
                    response.get('transaction_id') or False,
                'iot_six_authorization_code':
                    response.get('authorization_code') or False,
                'iot_six_card_brand':
                    response.get('card_brand') or False,
                'iot_six_card_last4':
                    response.get('card_last4') or False,
                'iot_six_emv_aid':
                    response.get('emv_aid') or False,
                'iot_six_signature_required':
                    bool(response.get('signature_required')),
            })
