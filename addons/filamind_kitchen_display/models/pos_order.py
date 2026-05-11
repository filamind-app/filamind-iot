"""Hook into pos.order so each new paid order materialises as kitchen
tickets on every linked display.
"""
from odoo import api, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def action_pos_order_paid(self):
        """Override extension point — push the order to kitchen displays
        right after payment is recorded. Falls through to super for the
        regular paid-flow side effects."""
        result = super().action_pos_order_paid() if hasattr(
            super(), 'action_pos_order_paid') else None
        for order in self:
            order._filamind_dispatch_to_kitchen()
        return result

    @api.model
    def _filamind_dispatch_displays_for(self, config):
        """Resolve which displays a given pos.config sends orders to."""
        return config.filamind_kitchen_display_ids if hasattr(
            config, 'filamind_kitchen_display_ids') else self.env[
                'filamind.kitchen.display']

    def _filamind_dispatch_to_kitchen(self):
        """For every linked display, materialise this order as a
        filamind.kitchen.order (filtered by category if set)."""
        Order = self.env['filamind.kitchen.order'].sudo()
        Stage = self.env['filamind.kitchen.stage'].sudo()
        for o in self:
            displays = o._filamind_dispatch_displays_for(o.config_id)
            if not displays:
                continue
            for display in displays:
                # Filter lines by category_ids if set
                lines = o.lines
                if display.category_ids:
                    cats = display.category_ids
                    lines = lines.filtered(
                        lambda line, _cats=cats: line.product_id.pos_categ_ids
                        and (line.product_id.pos_categ_ids & _cats))
                if not lines:
                    continue
                initial = Stage.search(
                    [('display_id', '=', display.id),
                     ('is_initial', '=', True)],
                    limit=1) or display.stage_ids[:1]
                if not initial:
                    continue
                ko = Order.create({
                    'display_id': display.id,
                    'pos_order_id': o.id,
                    'stage_id': initial.id,
                    'customer_note': getattr(o, 'note', '') or '',
                })
                ko.line_ids = [(0, 0, {
                    'pos_order_line_id': line.id,
                    'product_id': line.product_id.id,
                    'qty': line.qty,
                    'note': getattr(line, 'note', '') or '',
                }) for line in lines]
                # Push a bus.bus event the public OWL frontend listens to
                self.env['bus.bus']._sendone(
                    'filamind_kitchen_%s' % display.id,
                    'kitchen.order.new',
                    {'order_id': ko.id})
