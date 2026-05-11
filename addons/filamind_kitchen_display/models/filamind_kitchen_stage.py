"""Stage / column on a kitchen display (In Progress / Ready / Served)."""
from odoo import fields, models


class FilamindKitchenStage(models.Model):
    _name = 'filamind.kitchen.stage'
    _description = 'Kitchen Display Stage'
    _order = 'display_id, sequence, id'

    display_id = fields.Many2one(
        'filamind.kitchen.display', string='Display', required=True,
        ondelete='cascade', index=True,
    )
    name = fields.Char(string='Stage', required=True, translate=True)
    sequence = fields.Integer(default=10)
    color = fields.Integer(string='Colour', default=0)

    is_initial = fields.Boolean(
        string='Initial Stage',
        help='New orders land in this stage. Exactly one stage per '
             'display should be marked initial.',
    )
    is_final = fields.Boolean(
        string='Final Stage',
        help='Auto-clear (if enabled on the display) considers orders '
             'in this stage eligible for removal.',
    )
    auto_advance_seconds = fields.Integer(
        string='Auto-advance After (s)',
        help='If > 0, orders auto-move to the next stage after this '
             'many seconds. Useful for "Ready" → "Served" transitions.',
    )
