"""Adam Equipment scale extensions to iot.device. Only meaningful
on devices whose type is `scale` — the form view hides the group on
other device types."""
from odoo import _, fields, models
from odoo.exceptions import UserError


ADAM_FAMILIES = [
    ('cpwplus', 'CPWplus / CPW Series'),
    ('gfk_gbk', 'GFK / GBK Series (Industrial)'),
    ('gfc_gbc', 'GFC / GBC Series (Counting)'),
]
ADAM_UNITS = [
    ('g', 'Grams'),
    ('kg', 'Kilograms'),
    ('lb', 'Pounds'),
    ('oz', 'Ounces'),
]
ADAM_BAUDS = [
    ('4800', '4800'),
    ('9600', '9600 (default)'),
    ('19200', '19200'),
    ('38400', '38400'),
]


class IotDevice(models.Model):
    _inherit = 'iot.device'

    adam_model_family = fields.Selection(
        ADAM_FAMILIES, string='Adam Model Family',
        help='Picks which subset of AGN commands the IoT Box driver '
             'will emit. Wrong value = scale ignores commands.',
    )
    adam_serial_baud = fields.Selection(
        ADAM_BAUDS, string='Serial Baud Rate', default='9600',
    )
    adam_unit_default = fields.Selection(
        ADAM_UNITS, string='Default Unit', default='g',
    )
    adam_capacity_kg = fields.Float(
        string='Capacity (kg)', default=0.0,
        help='Maximum stable weight the scale supports. Used by the '
             'POS to flag suspicious overloads.',
    )
    adam_supports_tare = fields.Boolean(
        string='Supports Tare', default=True,
    )

    def action_iot_adam_zero(self):
        """Send AGN `Z` (zero) to the configured Adam scale."""
        self.ensure_one()
        if self.type_id.code != 'scale' or not self.adam_model_family:
            raise UserError(_(
                "This device is not configured as an Adam scale."))
        return self.iot_box_id.send_bus_message(
            method='iot_action',
            payload={
                'action': 'adam_zero',
                'family': self.adam_model_family,
                'baud': self.adam_serial_baud,
            },
            device=self,
            timeout=5,
        )

    def action_iot_adam_tare(self):
        """Send AGN `T` (tare) to the configured Adam scale."""
        self.ensure_one()
        if self.type_id.code != 'scale' or not self.adam_model_family:
            raise UserError(_(
                "This device is not configured as an Adam scale."))
        if not self.adam_supports_tare:
            raise UserError(_(
                "Tare is disabled on this scale."))
        return self.iot_box_id.send_bus_message(
            method='iot_action',
            payload={
                'action': 'adam_tare',
                'family': self.adam_model_family,
                'baud': self.adam_serial_baud,
            },
            device=self,
            timeout=5,
        )
