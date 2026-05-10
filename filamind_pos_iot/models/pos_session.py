"""POS session helpers for receipt printing and customer-display updates.

Frontend OWL components are out of scope here — this layer exposes
server-side methods that a future point_of_sale.assets bundle will call
via RPC.
"""
import json

from odoo import _, fields, models
from odoo.exceptions import UserError


class PosSession(models.Model):
    _inherit = 'pos.session'

    def action_print_iot_receipt(self, order_id, html=None):
        """Push a receipt to the IoT printer configured on this session's
        pos.config. Returns the iot.command.queue record so the caller can
        watch its state.

        :param order_id: optional pos.order id (used to render a default
                         receipt when ``html`` is not provided).
        :param html: optional pre-rendered receipt HTML.
        """
        self.ensure_one()
        printer = self.config_id.iot_printer_id
        if not printer:
            raise UserError(_(
                "No IoT receipt printer configured for POS '%s'.") %
                self.config_id.name)
        if not html:
            order = self.env['pos.order'].browse(order_id) if order_id else None
            html = self._render_iot_receipt(order)
        return printer.iot_box_id.send_bus_message(
            method='iot_action',
            payload={
                'document': html,
                'document_format': 'qweb',
                'print_id': fields.Datetime.now().isoformat(),
            },
            device=printer,
            timeout=20,
        )

    def update_iot_customer_display(self, payload):
        """Push the current order summary to the customer-display device.

        :param payload: dict with at least ``lines`` (list of {name, qty,
                        price}) and ``total``. Free-form — the box's display
                        driver decides what to render.
        """
        self.ensure_one()
        display = self.config_id.iot_customer_display_id
        if not display:
            return False
        return display.iot_box_id.send_bus_message(
            method='iot_action',
            payload={'action': 'render', 'data': json.dumps(payload)},
            device=display,
            timeout=5,
        )

    # ── Default receipt rendering ────────────────────────────────────────
    def _render_iot_receipt(self, order):
        """Return a minimal receipt body. Customers can override this to
        match their stationery — or pass pre-rendered HTML to
        ``action_print_iot_receipt(order_id, html=...)``.
        """
        if not order:
            body = "*** filamind POS test ***\n"
        else:
            lines = ''.join(
                "%-20s %4d  %8.2f\n" % (line.product_id.display_name[:20],
                                        line.qty, line.price_subtotal_incl)
                for line in order.lines
            )
            body = (
                "%s\n%s\n\n"
                "Order: %s\nDate:  %s\n\n"
                "%s\n"
                "------------------------------\n"
                "Total: %12.2f %s\n"
            ) % (self.config_id.name, '=' * 30,
                 order.name, order.date_order,
                 lines,
                 order.amount_total, order.currency_id.name or '')
        return body
