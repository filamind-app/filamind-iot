"""POS config extensions for kiosk-side IoT bindings."""
from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    self_order_iot_box_id = fields.Many2one(
        'iot.box', string='Self-Order IoT Box',
        ondelete='set null',
        domain="[('can_be_kiosk', '=', True), ('active', '=', True)]",
        help='IoT Box dedicated to this kiosk. Independent of the '
             'cashier-side iot_box_id.',
    )
    self_order_iot_printer_id = fields.Many2one(
        'iot.device', string='Self-Order Ticket Printer',
        ondelete='set null',
        domain="[('iot_box_id', '=', self_order_iot_box_id),"
               " ('type_id.code', 'in', ('receipt_printer', 'label_printer')),"
               " ('active', '=', True)]",
        help='Printer that issues a confirmation ticket for the customer '
             'after they place a kiosk order.',
    )
    self_order_iot_terminal_id = fields.Many2one(
        'iot.device', string='Self-Order Payment Terminal',
        ondelete='set null',
        domain="[('iot_box_id', '=', self_order_iot_box_id),"
               " ('type_id.code', '=', 'payment_terminal'),"
               " ('active', '=', True)]",
        help='Payment terminal exposed to the customer at the kiosk.',
    )
    self_ordering_iot_available_iot_box_ids = fields.One2many(
        'iot.box', compute='_compute_kiosk_available_boxes',
        string='Kiosk-eligible IoT Boxes',
        help='IoT Boxes flagged can_be_kiosk = True — Enterprise-parity '
             'helper field name; surfaces in the Self-Order admin UI.',
    )

    @api.depends('company_id')
    def _compute_kiosk_available_boxes(self):
        Box = self.env['iot.box']
        for r in self:
            r.self_ordering_iot_available_iot_box_ids = Box.search([
                ('can_be_kiosk', '=', True),
                ('state', '=', 'connected'),
                '|', ('company_id', '=', False),
                     ('company_id', '=', r.company_id.id),
            ])
