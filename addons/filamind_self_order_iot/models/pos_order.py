"""When a kiosk order is paid, push a ticket to the kiosk's IoT
printer (in addition to whatever pos_self_order's own logic does).
"""
from odoo import models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def action_pos_order_paid(self):
        result = super().action_pos_order_paid() if hasattr(
            super(), 'action_pos_order_paid') else None
        for order in self:
            order._filamind_dispatch_kiosk_ticket()
        return result

    def _filamind_dispatch_kiosk_ticket(self):
        """If this order originated from a self-order kiosk on a config
        with a self_order_iot_printer_id set, push the ticket there."""
        config = self.config_id
        printer = getattr(config, 'self_order_iot_printer_id', False)
        # `is_self_order` is the upstream pos_self_order flag on
        # pos.order; absent on pre-19 builds, so guard with getattr.
        is_self_order = getattr(self, 'is_self_order',
                                 getattr(self, 'self_order', False))
        if not (printer and is_self_order):
            return False
        body = self._render_kiosk_ticket()
        return printer.iot_box_id.send_bus_message(
            method='iot_action',
            payload={
                'action': 'print',
                'document': body,
                'document_format': 'raw',
                'print_id': self.name or str(self.id),
            },
            device=printer,
            timeout=15,
        )

    def _render_kiosk_ticket(self):
        """Plain-text confirmation ticket. Override in customer addons
        for ESC/POS or branded layouts."""
        lines = ''.join(
            "  %2d  %s\n" % (line.qty, line.product_id.display_name[:30])
            for line in self.lines
        )
        return (
            "*** Self-Order Confirmation ***\n"
            "  %s\n"
            "\n"
            "Order: %s\n"
            "Date:  %s\n"
            "\n"
            "%s"
            "------------------------------\n"
            "Total: %s %s\n"
            "\n"
            "Show this ticket at the counter.\n\n\n"
        ) % (self.config_id.name, self.name or '', self.date_order,
             lines, self.amount_total, self.currency_id.name or '')
