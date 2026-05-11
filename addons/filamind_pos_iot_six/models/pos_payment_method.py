"""Six (TIM Cloud / TIM Direct) terminal extensions to
pos.payment.method. The actual TIM protocol implementation lives on
the IoT Box itself; this addon is the server-side data + UI layer."""
from odoo import _, fields, models
from odoo.exceptions import UserError


SIX_PROTOCOLS = [
    ('tim_direct', 'TIM Direct (USB / Serial)'),
    ('tim_cloud', 'TIM Cloud (HTTPS)'),
]


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    iot_six_terminal_id = fields.Char(
        string='Six Terminal ID (TID)',
        help='8-character TID assigned by Six when the terminal was '
             'provisioned. Embossed on the back of the device.',
    )
    iot_six_protocol = fields.Selection(
        SIX_PROTOCOLS, string='Six Protocol', default='tim_direct',
        help='TIM Direct = the box drives the terminal over USB/serial. '
             'TIM Cloud = the box hits Six\'s HTTPS API.',
    )
    iot_six_supports_tip = fields.Boolean(
        string='Terminal Prompts for Tip',
        help='If checked, the cashier UI does NOT prompt for tip — '
             'the terminal will handle it.',
    )

    def iot_request_payment(self, amount, currency, reference=None):
        """Override the generic iot_request_payment to inject Six-specific
        TIM payload fields."""
        self.ensure_one()
        if not self.iot_terminal_id:
            return False
        if not self.iot_six_terminal_id:
            raise UserError(_(
                "Set the Six Terminal ID (TID) on payment method '%s' "
                "before processing card payments.") % self.name)
        return self.iot_terminal_id.iot_box_id.send_bus_message(
            method='iot_action',
            payload={
                'action': 'pay',
                'vendor': 'six',
                'amount': amount,
                'currency': currency,
                'reference': reference or '',
                'six': {
                    'terminal_id': self.iot_six_terminal_id,
                    'protocol': self.iot_six_protocol,
                    'transaction_type': 'purchase',
                    'application_label': self.name,
                },
            },
            device=self.iot_terminal_id,
            timeout=180,  # Six TIM Cloud round-trips can take a while
        )
