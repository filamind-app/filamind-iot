"""POS-config switch for capacity-overflow warnings on Adam scales."""
from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    iot_adam_check_capacity = fields.Boolean(
        string='Warn on Adam Scale Overload',
        default=True,
        help='If checked, the POS warns the cashier when the scale '
             'returns a weight greater than its declared capacity. '
             'Useful catching overload errors and misconfigured scales.',
    )
