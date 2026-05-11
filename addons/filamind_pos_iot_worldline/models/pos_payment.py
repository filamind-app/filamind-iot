"""Capture the Worldline terminal's CTEP response on the matching
pos.payment row. Includes EMV-spec TVR + TSI for downstream chargeback
defense workflows."""
from odoo import fields, models


class PosPayment(models.Model):
    _inherit = 'pos.payment'

    iot_worldline_authorization_code = fields.Char(
        string='Authorization Code', readonly=True, copy=False,
        help='Issuer authorization code (typically 6 digits).',
    )
    iot_worldline_card_brand = fields.Char(
        string='Card Brand', readonly=True, copy=False,
    )
    iot_worldline_card_last4 = fields.Char(
        string='Card Last 4', readonly=True, copy=False,
        help='Last four digits of the PAN. The full PAN MUST NOT be '
             'stored — PCI-DSS forbids it outside of certified vaults.',
    )
    iot_worldline_emv_aid = fields.Char(
        string='EMV AID', readonly=True, copy=False,
        help='EMV Application Identifier.',
    )
    iot_worldline_emv_tvr = fields.Char(
        string='Terminal Verification Results (TVR)',
        readonly=True, copy=False,
        help='Five-byte hex TVR from the EMV transaction. Required '
             'evidence in chargeback defense.',
    )
    iot_worldline_emv_tsi = fields.Char(
        string='Transaction Status Information (TSI)',
        readonly=True, copy=False,
        help='Two-byte hex TSI from the EMV transaction.',
    )
    iot_worldline_signature_required = fields.Boolean(
        string='Signature Required', readonly=True,
    )

    def _filamind_apply_worldline_response(self, response):
        """Called by the IoT controller / cron when the box reports
        the terminal's CTEP response. ``response`` keys mirror the
        field names above (without the ``iot_worldline_`` prefix)."""
        for payment in self:
            payment.sudo().write({
                'iot_worldline_authorization_code':
                    response.get('authorization_code') or False,
                'iot_worldline_card_brand':
                    response.get('card_brand') or False,
                'iot_worldline_card_last4':
                    response.get('card_last4') or False,
                'iot_worldline_emv_aid':
                    response.get('emv_aid') or False,
                'iot_worldline_emv_tvr':
                    response.get('emv_tvr') or False,
                'iot_worldline_emv_tsi':
                    response.get('emv_tsi') or False,
                'iot_worldline_signature_required':
                    bool(response.get('signature_required')),
            })
