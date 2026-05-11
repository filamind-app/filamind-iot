"""Catalogue of X11 keyboard layouts the IoT box has detected.

Populated by the box's keyboard driver, which POSTs the available
layouts to /iot/keyboard_layouts on first boot per scanner / keyboard.
Used by the iot.device form to offer a layout dropdown per device.
"""
from odoo import fields, models


class IotKeyboardLayout(models.Model):
    _name = 'iot.keyboard.layout'
    _description = 'Keyboard Layout'
    _order = 'language, layout'
    _rec_name = 'display_name'

    layout = fields.Char(
        string='Layout', required=True, index=True,
        help='X11 layout code, e.g. "us", "fr", "ar".',
    )
    variant = fields.Char(
        string='Variant',
        help='Layout variant (e.g. "dvorak", "azerty"). May be empty.',
    )
    language = fields.Char(
        string='Language',
        help='Human-readable language name.',
    )
    display_name = fields.Char(compute='_compute_display_name', store=True)

    _sql_constraints = [
        ('layout_variant_uniq',
         'unique(layout, variant)',
         'A keyboard layout/variant pair must be unique.'),
    ]

    def _compute_display_name(self):
        for r in self:
            r.display_name = '%s (%s)' % (r.language or r.layout, r.variant or 'default')
