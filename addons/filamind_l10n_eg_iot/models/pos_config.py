"""Per-POS-config selector for the Egyptian fiscal printer device."""
from odoo import _, fields, models
from odoo.exceptions import UserError


class PosConfig(models.Model):
    _inherit = 'pos.config'

    iot_eg_fiscal_printer_id = fields.Many2one(
        'iot.device', string='ETA Fiscal Printer',
        domain="[('iot_box_id', '=', iot_box_id),"
               " ('type_id.code', 'in', ('receipt_printer', 'fiscal_data')),"
               " ('active', '=', True)]",
        ondelete='set null',
        help='Hardware fiscal printer that signs receipts and returns a '
             'UUID + QR data block compliant with Egyptian Tax Authority '
             '(ETA) requirements. Leave empty to disable hardware fiscal '
             'signing on this POS configuration.',
    )

    def action_iot_eg_test_fiscal(self):
        """Round-trip a small fiscal-print test to verify the device wiring
        and the box reports a signature back."""
        self.ensure_one()
        if not self.iot_eg_fiscal_printer_id:
            raise UserError(_("No ETA fiscal printer configured."))
        printer = self.iot_eg_fiscal_printer_id
        cmd = printer.iot_box_id.send_bus_message(
            method='iot_action',
            payload={
                'action': 'fiscal_print',
                'document_format': 'raw',
                'document': '*** filamind ETA fiscal test ***\n',
                'fiscal': {'kind': 'test'},
            },
            device=printer,
            timeout=20,
        )
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'iot.command.queue',
            'res_id': cmd.id,
            'view_mode': 'form',
            'target': 'new',
        }
