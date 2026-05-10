from odoo import fields, models


class IotDeviceType(models.Model):
    """Catalog of supported IoT device categories.

    Keeping types in a model (rather than a Selection) lets admins add their
    own categories without code changes.
    """
    _name = 'iot.device.type'
    _description = 'IoT Device Type'
    _order = 'sequence, name'

    name = fields.Char(string='Type', required=True, translate=True)
    code = fields.Char(
        string='Technical Code', required=True,
        help='Technical identifier used by the IoT Box to report device type.',
    )
    icon = fields.Char(
        string='FontAwesome Icon', default='fa-plug',
        help='FontAwesome icon class, e.g. "fa-print", "fa-barcode".',
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    description = fields.Text(translate=True)
    color = fields.Integer(string='Color Index', default=0)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Device type code must be unique.'),
    ]
