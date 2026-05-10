from odoo import _, fields, models
from odoo.exceptions import UserError


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    iot_box_id = fields.Many2one(
        related='workcenter_id.iot_box_id', store=False, readonly=True,
    )
    iot_label_printer_id = fields.Many2one(
        related='workcenter_id.iot_label_printer_id', store=False, readonly=True,
    )
    iot_caliper_id = fields.Many2one(
        related='workcenter_id.iot_caliper_id', store=False, readonly=True,
    )

    def action_iot_capture_measurement(self):
        """Ask the workcenter's caliper for a reading. The reading lands on
        the iot.command.queue's response_payload — downstream modules can
        wire it to a quality.check or a custom field by overriding
        ``iot.command.queue.record_response``.
        """
        self.ensure_one()
        caliper = self.iot_caliper_id
        if not caliper:
            raise UserError(_(
                "No caliper configured on workcenter '%s'.")
                % (self.workcenter_id.name or _('(unknown)')))
        queue = caliper.iot_box_id.send_bus_message(
            method='iot_action',
            payload={
                'action': 'read',
                'workorder_id': self.id,
                'product_id': self.product_id.id if self.product_id else False,
            },
            device=caliper,
            timeout=15,
        )
        self.message_post(body=_(
            "Measurement requested (session %s).") % queue.name[:12])
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'iot.command.queue',
            'res_id': queue.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_print_iot_label(self):
        """Print a work-order label on the configured printer."""
        self.ensure_one()
        printer = self.iot_label_printer_id
        if not printer:
            raise UserError(_(
                "No label printer configured on workcenter '%s'.")
                % (self.workcenter_id.name or _('(unknown)')))
        body = (
            "%-30s\n"
            "WO: %s\n"
            "Product: %s\n"
            "Qty: %s\n"
            "Workcenter: %s\n"
        ) % ((self.production_id.name or '')[:30],
             (self.name or '')[:30],
             (self.product_id.display_name or '')[:30],
             self.qty_production,
             (self.workcenter_id.name or '')[:30])
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
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'iot.command.queue',
            'res_id': queue.id,
            'view_mode': 'form',
            'target': 'new',
        }
