"""IoT badge printer + check-in scanner per event."""
from odoo import fields, models


class EventEvent(models.Model):
    _inherit = 'event.event'

    iot_badge_printer_id = fields.Many2one(
        'iot.device', string='IoT Badge Printer',
        domain="[('type_id.code', 'in', ('label_printer', 'receipt_printer')),"
               " ('active', '=', True)]",
        ondelete='set null',
        help='Printer that issues an attendee badge when a registration '
             'is confirmed.',
    )
    iot_scanner_id = fields.Many2one(
        'iot.device', string='IoT Check-in Scanner',
        domain="[('type_id.code', '=', 'barcode_scanner'),"
               " ('active', '=', True)]",
        ondelete='set null',
        help='Scanner that checks an attendee in by reading their badge '
             'barcode (registration name or barcode field).',
    )
    auto_print_badges = fields.Boolean(
        string='Auto-print Badges', default=True,
        help='When a registration moves to "Confirmed", push a badge to '
             'iot_badge_printer_id automatically.',
    )
