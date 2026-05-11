"""Hook pos.order to send a fiscal print on payment and capture the
ETA-compliant signature returned by the device."""
from odoo import fields, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    iot_eg_fiscal_print_command_id = fields.Many2one(
        'iot.command.queue', string='Fiscal Print Command',
        readonly=True, ondelete='set null',
        help='IoT command queue entry that carried this order to the '
             'fiscal printer; track its state to know whether the box '
             'has reported a signature back.',
    )
    iot_eg_fiscal_uuid = fields.Char(
        string='ETA Fiscal UUID', readonly=True, copy=False,
        help='Unique signature ID returned by the fiscal printer. '
             'A downstream l10n_eg_eta_edi addon submits this to ETA.',
    )
    iot_eg_fiscal_qr = fields.Char(
        string='ETA Fiscal QR Data', readonly=True, copy=False,
        help='Base32 / base64 QR payload returned by the fiscal printer. '
             'Render this on the customer receipt to satisfy ETA Stage-2.',
    )

    def action_pos_order_paid(self):
        result = super().action_pos_order_paid() if hasattr(
            super(), 'action_pos_order_paid') else None
        for order in self:
            order._filamind_dispatch_to_eg_fiscal()
        return result

    def _filamind_dispatch_to_eg_fiscal(self):
        """If the POS config has a fiscal printer set, send the receipt
        body via the IoT box and store the command queue id."""
        for order in self:
            printer = order.config_id.iot_eg_fiscal_printer_id \
                if hasattr(order.config_id, 'iot_eg_fiscal_printer_id') \
                else False
            if not printer:
                continue
            try:
                body = order._filamind_render_eg_fiscal_body()
                cmd = printer.iot_box_id.send_bus_message(
                    method='iot_action',
                    payload={
                        'action': 'fiscal_print',
                        'document_format': 'raw',
                        'document': body,
                        'fiscal': {
                            'kind': 'sale',
                            'order_ref': order.pos_reference or order.name,
                            'amount_total': order.amount_total,
                            'amount_tax': order.amount_tax,
                            'currency': order.currency_id.name,
                            'company_tax_id': order.company_id.vat or '',
                        },
                    },
                    device=printer,
                    timeout=30,
                )
                order.write({
                    'iot_eg_fiscal_print_command_id': cmd.id,
                })
            except Exception:
                # Don't block the paid flow if the device is offline —
                # the cashier can retry from the order form, and an
                # ETA-resubmission cron can pick up unsigned orders.
                pass

    def _filamind_render_eg_fiscal_body(self):
        """Plain-text receipt body sent to the fiscal printer. Override
        for ESC/POS, ESC/Z, or vendor-specific protocols."""
        self.ensure_one()
        lines = [
            '================================',
            '  %s' % (self.company_id.name or '')[:30],
            '  VAT: %s' % (self.company_id.vat or '')[:24],
            '================================',
            '  Order: %s' % (self.pos_reference or self.name or ''),
            '',
        ]
        for line in self.lines:
            lines.append('  %s x%s' % (
                (line.product_id.display_name or '')[:24],
                line.qty,
            ))
            lines.append('       %.2f %s' % (
                line.price_subtotal_incl,
                self.currency_id.name or '',
            ))
        lines.append('--------------------------------')
        lines.append('  TOTAL: %.2f %s' % (
            self.amount_total, self.currency_id.name or ''))
        lines.append('  TAX:   %.2f' % self.amount_tax)
        lines.append('')
        return '\n'.join(lines)

    def _filamind_apply_eg_fiscal_response(self, uuid, qr):
        """Called by the IoT controller / cron when the box reports the
        device's signature for this order."""
        for order in self:
            order.sudo().write({
                'iot_eg_fiscal_uuid': uuid or False,
                'iot_eg_fiscal_qr': qr or False,
            })
