from odoo import _, fields, models
from odoo.exceptions import UserError


class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'

    iot_box_id = fields.Many2one(
        'iot.box', string='IoT Box',
        ondelete='set null',
        help='Default IoT gateway used by this work center.',
    )
    iot_label_printer_id = fields.Many2one(
        'iot.device', string='Label Printer',
        domain="[('iot_box_id', '=', iot_box_id),"
               " ('type_id.code', 'in', ('label_printer', 'receipt_printer')),"
               " ('active', '=', True)]",
        ondelete='set null',
    )
    iot_caliper_id = fields.Many2one(
        'iot.device', string='Caliper / Measuring Tool',
        domain="[('iot_box_id', '=', iot_box_id),"
               " ('type_id.code', '=', 'measuring_tool'),"
               " ('active', '=', True)]",
        ondelete='set null',
        help='Used by quality checks to capture dimensional measurements.',
    )
    iot_scanner_id = fields.Many2one(
        'iot.device', string='Barcode Scanner',
        domain="[('iot_box_id', '=', iot_box_id),"
               " ('type_id.code', '=', 'barcode_scanner'),"
               " ('active', '=', True)]",
        ondelete='set null',
    )

    def action_iot_test_caliper(self):
        self.ensure_one()
        if not self.iot_caliper_id:
            raise UserError(_("No caliper configured."))
        queue = self.iot_caliper_id.iot_box_id.send_bus_message(
            method='iot_action',
            payload={'action': 'read'},
            device=self.iot_caliper_id,
            timeout=10,
        )
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'iot.command.queue',
            'res_id': queue.id,
            'view_mode': 'form',
            'target': 'new',
        }
