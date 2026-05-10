"""IoT actions on stock.picking — print labels and weigh packages."""
from odoo import _, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    iot_box_id = fields.Many2one(
        related='picking_type_id.warehouse_id.iot_box_id',
        store=False, readonly=True,
    )
    iot_label_printer_id = fields.Many2one(
        related='picking_type_id.warehouse_id.iot_label_printer_id',
        store=False, readonly=True,
    )
    iot_scale_id = fields.Many2one(
        related='picking_type_id.warehouse_id.iot_scale_id',
        store=False, readonly=True,
    )

    def action_print_iot_label(self):
        """Push the picking name + reference to the warehouse label printer.

        For real shipping labels (carrier-specific ZPL/EPL), customers
        should override this method or call
        ``picking.iot_label_printer_id.iot_box_id.send_bus_message(...)``
        with their pre-rendered payload.
        """
        self.ensure_one()
        printer = self.iot_label_printer_id
        if not printer:
            raise UserError(_(
                "No label printer configured on warehouse '%s'.")
                % (self.picking_type_id.warehouse_id.name or _('(unknown)')))

        body = self._render_iot_label_body()
        queue = printer.iot_box_id.send_bus_message(
            method='iot_action',
            payload={
                'document': body,
                'document_format': 'raw',
                'print_id': fields.Datetime.now().isoformat(),
            },
            device=printer,
            timeout=15,
        )
        self.message_post(body=_(
            "Label print dispatched (session %s).") % queue.name[:12])
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'iot.command.queue',
            'res_id': queue.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_iot_weigh(self):
        """Read the warehouse scale and store the value on the first move
        line of this picking (``shipping_weight`` if present, otherwise
        as a chatter note).
        """
        self.ensure_one()
        scale = self.iot_scale_id
        if not scale:
            raise UserError(_(
                "No scale configured on warehouse '%s'.")
                % (self.picking_type_id.warehouse_id.name or _('(unknown)')))

        queue = scale.iot_box_id.send_bus_message(
            method='iot_action',
            payload={'action': 'read_weight', 'picking_id': self.id},
            device=scale,
            timeout=10,
        )
        self.message_post(body=_(
            "Weight reading requested (session %s). "
            "Result will be applied when the box reports back.")
            % queue.name[:12])
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'iot.command.queue',
            'res_id': queue.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _render_iot_label_body(self):
        """Plain-text label body. Override in customer addons for ZPL/EPL."""
        return (
            "%-30s\n"
            "%-30s\n"
            "Origin: %s\n"
            "Partner: %s\n"
            "Lines: %d\n"
        ) % (self.name or '',
             (self.picking_type_id.name or '')[:30],
             (self.origin or '-')[:30],
             (self.partner_id.name or '-')[:30],
             len(self.move_ids))
