"""filamind_pos_iot extension to iot.box: a computed `pos.config`
back-reference. Lives here (not in filamind_iot) because the field
references `pos.config` which only exists when point_of_sale is
installed — a hard dependency of this addon."""
from odoo import fields, models


class IotBox(models.Model):
    _inherit = 'iot.box'

    associated_pos_config_ids = fields.Many2many(
        'pos.config', string='POS Configurations',
        compute='_compute_associated_pos_config_ids', store=False,
        help='POS configurations whose iot_*_id fields point to a '
             'device on this box. Read-only summary.',
    )

    def _compute_associated_pos_config_ids(self):
        PosConfig = self.env['pos.config']
        for box in self:
            device_ids = box.device_ids.ids
            if not device_ids:
                box.associated_pos_config_ids = False
                continue
            domain = [
                '|', '|', '|',
                ('iot_printer_id', 'in', device_ids),
                ('iot_scale_id', 'in', device_ids),
                ('iot_scanner_ids', 'in', device_ids),
                ('iot_customer_display_id', 'in', device_ids),
            ]
            box.associated_pos_config_ids = PosConfig.sudo().search(domain)
