"""Per-operation-type IoT scale binding.

Mirrors Enterprise `delivery_iot.stock.picking.type.iot_scale_ids`.
Each `stock.picking.type` (Receipts / Internal Transfers / Outgoing
shipments) can list scales eligible for use during that operation.
The `stock.put.in.pack` wizard then offers them as a dropdown when
weighing a parcel.
"""
from odoo import fields, models


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    iot_scale_ids = fields.Many2many(
        'iot.device', 'stock_picking_type_iot_scale_rel',
        'picking_type_id', 'device_id',
        string='IoT Scales',
        domain="[('type_id.code', '=', 'scale'), ('active', '=', True)]",
        help='Scales available for weighing during this operation type. '
             'Empty = all scales on the warehouse default IoT box are '
             'offered.',
    )
