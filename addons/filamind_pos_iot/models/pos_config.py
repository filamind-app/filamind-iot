from odoo import _, fields, models
from odoo.exceptions import UserError


class PosConfig(models.Model):
    _inherit = 'pos.config'

    iot_box_id = fields.Many2one(
        'iot.box', string='IoT Box',
        ondelete='set null',
        help='Default IoT gateway used by this POS configuration.',
    )
    iot_printer_id = fields.Many2one(
        'iot.device', string='Receipt Printer',
        domain="[('iot_box_id', '=', iot_box_id),"
               " ('type_id.code', 'in', ('receipt_printer', 'label_printer')),"
               " ('active', '=', True)]",
        ondelete='set null',
    )
    iot_scale_id = fields.Many2one(
        'iot.device', string='Electronic Scale',
        domain="[('iot_box_id', '=', iot_box_id),"
               " ('type_id.code', '=', 'scale'), ('active', '=', True)]",
        ondelete='set null',
    )
    iot_scanner_id = fields.Many2one(
        'iot.device', string='Barcode Scanner',
        domain="[('iot_box_id', '=', iot_box_id),"
               " ('type_id.code', '=', 'barcode_scanner'),"
               " ('active', '=', True)]",
        ondelete='set null',
    )
    iot_customer_display_id = fields.Many2one(
        'iot.device', string='Customer Display',
        domain="[('iot_box_id', '=', iot_box_id),"
               " ('type_id.code', '=', 'customer_display'),"
               " ('active', '=', True)]",
        ondelete='set null',
    )
    iot_cash_drawer_id = fields.Many2one(
        'iot.device', string='Cash Drawer',
        domain="[('iot_box_id', '=', iot_box_id),"
               " ('type_id.code', '=', 'cash_drawer'), ('active', '=', True)]",
        ondelete='set null',
        help='Cash drawer is usually opened via the receipt printer kick code; '
             'set this only if you have a standalone drawer device.',
    )

    # ── Test actions ─────────────────────────────────────────────────────
    def action_iot_test_connection(self):
        self.ensure_one()
        if not self.iot_box_id:
            raise UserError(_("No IoT Box configured for this POS."))
        return self.iot_box_id.action_test_connection()

    def action_iot_test_print(self):
        self.ensure_one()
        if not self.iot_printer_id:
            raise UserError(_("No receipt printer configured for this POS."))
        return self.iot_printer_id.action_test_print()

    def action_iot_test_weigh(self):
        self.ensure_one()
        if not self.iot_scale_id:
            raise UserError(_("No scale configured for this POS."))
        return self.iot_scale_id.iot_box_id.send_bus_message(
            method='iot_action',
            payload={'action': 'read_weight'},
            device=self.iot_scale_id,
            timeout=10,
        ) and self._open_command_form_for_device(self.iot_scale_id)

    def action_iot_open_drawer(self):
        """Send the ESC/POS kick code to the configured printer (or drawer)."""
        self.ensure_one()
        target = self.iot_cash_drawer_id or self.iot_printer_id
        if not target:
            raise UserError(_("Configure a printer or cash drawer first."))
        target.iot_box_id.send_bus_message(
            method='iot_action',
            payload={'action': 'cashbox', 'document_format': 'raw'},
            device=target,
            timeout=10,
        )
        return self._open_command_form_for_device(target)

    def action_iot_open_devices(self):
        self.ensure_one()
        if not self.iot_box_id:
            raise UserError(_("No IoT Box configured."))
        return self.iot_box_id.action_view_devices()

    # ── Helpers ──────────────────────────────────────────────────────────
    def _open_command_form_for_device(self, device):
        cmd = self.env['iot.command.queue'].search(
            [('device_id', '=', device.id)], limit=1, order='id desc')
        if not cmd:
            return True
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'iot.command.queue',
            'res_id': cmd.id,
            'view_mode': 'form',
            'target': 'new',
        }
