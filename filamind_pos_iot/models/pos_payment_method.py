from odoo import _, fields, models
from odoo.exceptions import UserError


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    iot_terminal_id = fields.Many2one(
        'iot.device', string='IoT Payment Terminal',
        domain="[('type_id.code', '=', 'payment_terminal'),"
               " ('active', '=', True)]",
        ondelete='set null',
        help='Bind this payment method to a specific IoT-attached terminal '
             '(Worldline CTEP, Six TIM, etc.). When the cashier validates '
             'the payment, an iot_action is dispatched to that terminal.',
    )

    def action_iot_terminal_test(self):
        self.ensure_one()
        if not self.iot_terminal_id:
            raise UserError(_("No IoT terminal bound to this payment method."))
        return self.iot_terminal_id.action_test()

    def iot_request_payment(self, amount, currency, reference=None):
        """Server-side helper: ask the terminal to process a card payment.

        Returns the iot.command.queue record. The caller polls its state.
        Frontend integration (POS payment screen) is part of Phase 3b.
        """
        self.ensure_one()
        if not self.iot_terminal_id:
            return False
        return self.iot_terminal_id.iot_box_id.send_bus_message(
            method='iot_action',
            payload={
                'action': 'pay',
                'amount': amount,
                'currency': currency,
                'reference': reference or '',
            },
            device=self.iot_terminal_id,
            timeout=120,  # card transactions can take a while
        )
