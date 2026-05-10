from odoo import _, fields, models
from odoo.exceptions import UserError


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    iot_box_id = fields.Many2one(
        'iot.box', string='IoT Box',
        ondelete='set null',
        help='Default IoT gateway used by this warehouse.',
    )
    iot_label_printer_id = fields.Many2one(
        'iot.device', string='Label Printer',
        domain="[('iot_box_id', '=', iot_box_id),"
               " ('type_id.code', '=', 'label_printer'), ('active', '=', True)]",
        ondelete='set null',
        help='Used to print shipping/product labels from pickings.',
    )
    iot_receipt_printer_id = fields.Many2one(
        'iot.device', string='Receipt/Slip Printer',
        domain="[('iot_box_id', '=', iot_box_id),"
               " ('type_id.code', '=', 'receipt_printer'), ('active', '=', True)]",
        ondelete='set null',
        help='Used for picking slips, transfer documents, etc.',
    )
    iot_scale_id = fields.Many2one(
        'iot.device', string='Warehouse Scale',
        domain="[('iot_box_id', '=', iot_box_id),"
               " ('type_id.code', '=', 'scale'), ('active', '=', True)]",
        ondelete='set null',
        help='Capture package weights at packing/shipping time.',
    )
    iot_barcode_scanner_id = fields.Many2one(
        'iot.device', string='Barcode Scanner',
        domain="[('iot_box_id', '=', iot_box_id),"
               " ('type_id.code', '=', 'barcode_scanner'),"
               " ('active', '=', True)]",
        ondelete='set null',
    )

    def action_iot_test_label(self):
        self.ensure_one()
        if not self.iot_label_printer_id:
            raise UserError(_("No label printer configured."))
        return self.iot_label_printer_id.action_test_print()

    def action_iot_test_scale(self):
        self.ensure_one()
        if not self.iot_scale_id:
            raise UserError(_("No warehouse scale configured."))
        queue = self.iot_scale_id.iot_box_id.send_bus_message(
            method='iot_action',
            payload={'action': 'read_weight'},
            device=self.iot_scale_id,
            timeout=10,
        )
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'iot.command.queue',
            'res_id': queue.id,
            'view_mode': 'form',
            'target': 'new',
        }
