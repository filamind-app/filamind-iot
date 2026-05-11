"""Worldline (CTEP / Sips-Sherlocks) terminal extensions to
pos.payment.method. The actual CTEP protocol implementation lives
on the IoT Box itself; this addon is the server-side data + UI
layer."""
from odoo import _, fields, models
from odoo.exceptions import UserError


WORLDLINE_PROTOCOLS = [
    ('ctep', 'CTEP (USB / Serial)'),
    ('cless_evo', 'Contactless Evo (Network)'),
]


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    iot_worldline_terminal_id = fields.Char(
        string='Worldline Terminal ID (TID)',
        help='TID assigned by Worldline when the terminal was '
             'provisioned. Visible from the terminal\'s admin menu.',
    )
    iot_worldline_protocol = fields.Selection(
        WORLDLINE_PROTOCOLS, string='Worldline Protocol', default='ctep',
    )
    iot_worldline_currency_code = fields.Char(
        string='Currency (ISO-4217 numeric)',
        help='Three-digit numeric code baked into the terminal\'s '
             'config (e.g. 978 = EUR, 840 = USD). Cross-check with '
             'the POS journal currency to catch misconfigurations.',
    )
    iot_worldline_manual_entry_allowed = fields.Boolean(
        string='Allow Manual PAN Entry',
        help='Some Worldline terminals can fall back to keyed PAN '
             'entry. PCI-DSS treats this as a higher-risk path.',
    )
    iot_worldline_language = fields.Char(
        string='Cardholder Prompt Language',
        default='en',
        help='ISO 639-1 two-letter code forwarded to the terminal '
             'for cardholder-facing prompts.',
    )

    def iot_request_payment(self, amount, currency, reference=None):
        """Override the generic iot_request_payment to inject
        Worldline-specific CTEP payload fields."""
        self.ensure_one()
        if not self.iot_terminal_id:
            return False
        if not self.iot_worldline_terminal_id:
            raise UserError(_(
                "Set the Worldline Terminal ID (TID) on payment "
                "method '%s' before processing card payments.") % self.name)
        return self.iot_terminal_id.iot_box_id.send_bus_message(
            method='iot_action',
            payload={
                'action': 'pay',
                'vendor': 'worldline',
                'amount': amount,
                'currency': currency,
                'reference': reference or '',
                'worldline': {
                    'terminal_id': self.iot_worldline_terminal_id,
                    'protocol': self.iot_worldline_protocol,
                    'transaction_type': 'purchase',
                    'language': self.iot_worldline_language or 'en',
                    'manual_entry_allowed':
                        bool(self.iot_worldline_manual_entry_allowed),
                    'currency_code': self.iot_worldline_currency_code or '',
                },
            },
            device=self.iot_terminal_id,
            timeout=180,
        )
