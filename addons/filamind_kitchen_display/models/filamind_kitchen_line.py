"""A single line item on a kitchen ticket."""
from odoo import fields, models


class FilamindKitchenLine(models.Model):
    _name = 'filamind.kitchen.line'
    _description = 'Kitchen Display Order Line'
    _order = 'order_id, sequence, id'

    order_id = fields.Many2one(
        'filamind.kitchen.order', string='Order', required=True,
        ondelete='cascade', index=True,
    )
    sequence = fields.Integer(default=10)
    pos_order_line_id = fields.Many2one(
        'pos.order.line', string='POS Line', ondelete='set null',
    )
    product_id = fields.Many2one(
        'product.product', string='Product',
    )
    qty = fields.Float(string='Quantity', default=1.0)
    note = fields.Char(string='Note')
    state = fields.Selection([
        ('pending', 'Pending'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready'),
        ('served', 'Served'),
    ], default='pending', required=True)
