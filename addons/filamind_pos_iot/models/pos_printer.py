"""Bind a pos.printer (kitchen / bar / order printer) to an iot.device.

`pos.printer` is the upstream model used by `pos_restaurant` to send
order tickets to a printer in the back-of-house. Without IoT, those
tickets go to a network printer over IPP. With IoT, the ticket is sent
to the iot.box which forwards to the locally-attached printer.

Requires `pos_restaurant` to be installed (which is LGPL community —
no Enterprise dependency).
"""
from odoo import _, fields, models
from odoo.exceptions import UserError


class PosPrinter(models.Model):
    _inherit = 'pos.printer'

    iot_device_id = fields.Many2one(
        'iot.device', string='IoT Printer Device',
        domain="[('type_id.code', 'in', ('receipt_printer', 'label_printer', 'office_printer')),"
               " ('active', '=', True)]",
        ondelete='set null',
        help='When set, kitchen tickets for this printer are dispatched '
             'via the IoT Box rather than over the network.',
    )
    iot_use_lna = fields.Boolean(
        string='LNA Logging',
        help='Append the EU LNE Logging-Network-Activity reference to '
             'every ticket printed on this device. Requires '
             'filamind_l10n_eu_iot_scale_cert (Phase 15).',
    )

    def action_iot_test_print(self):
        self.ensure_one()
        if not self.iot_device_id:
            raise UserError(_(
                "This printer is not bound to an IoT device."))
        return self.iot_device_id.action_test_print()
