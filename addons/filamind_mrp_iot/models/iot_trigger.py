"""IoT trigger — bind a key/scan from a device to an action on an MRP
work centre.

Mirrors Enterprise's `mrp_iot.iot.trigger` model. Use case: a foot-pedal
or barcode scanner attached to the IoT Box on a workcenter triggers
"VALIdate", "PAUSe", "NEXT", "Take MEASURE", etc. on the active work
order — no clicking required.

The 19 action codes match Enterprise's selection so that triggers
exported from Enterprise can be imported into filamind 1:1.
"""
from odoo import fields, models


class IotTrigger(models.Model):
    _name = 'iot.trigger'
    _description = 'IoT Trigger'
    _order = 'workcenter_id, sequence, id'

    sequence = fields.Integer(default=10)
    workcenter_id = fields.Many2one(
        'mrp.workcenter', string='Work Center', required=True,
        ondelete='cascade', index=True,
    )
    device_id = fields.Many2one(
        'iot.device', string='Device', ondelete='set null',
        domain="[('type_id.code', 'in', ('barcode_scanner', 'keyboard',"
               " 'measuring_tool', 'gpio')), ('active', '=', True)]",
        help='The device whose key/scan/measure event fires this trigger.',
    )
    key = fields.Char(
        string='Key',
        help='The exact value the device must emit (barcode contents, '
             'key sequence, GPIO pin name) for this trigger to match.',
    )
    action = fields.Selection([
        # Workcenter operations
        ('NEXT', 'Next'),
        ('PREV', 'Previous'),
        ('SKIP', 'Skip'),
        ('PAUS', 'Pause'),
        ('VALI', 'Validate'),
        ('CLMO', 'Close MO'),
        ('CLWO', 'Close WO'),
        ('FINI', 'Finish'),
        ('RECO', 'Record Production'),
        ('CANC', 'Cancel'),
        ('PACK', 'Pack'),
        ('SCRA', 'Scrap'),
        # Printing
        ('PROP', 'Print Operation'),
        ('PRSL', 'Print Delivery Slip'),
        ('PRNT', 'Print Labels'),
        # Quality / measurement
        ('picture', 'Take Picture'),
        ('measure', 'Take Measure'),
        ('pass', 'Pass'),
        ('fail', 'Fail'),
    ], string='Action', required=True, default='VALI',
       help='What happens when the device fires this trigger. Codes match '
            'Enterprise mrp_iot for cross-import compatibility.')
