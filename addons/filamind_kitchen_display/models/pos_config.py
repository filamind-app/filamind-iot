"""Bind one or more kitchen displays to a POS configuration."""
from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    filamind_kitchen_display_ids = fields.Many2many(
        'filamind.kitchen.display',
        'pos_config_kitchen_display_rel',
        'config_id', 'display_id',
        string='Kitchen Displays (filamind)',
        help='New POS orders from this configuration are sent to every '
             'display listed here. Filtered further by each display\'s '
             'category_ids if set.',
    )
