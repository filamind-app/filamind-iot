"""A kitchen ticket on a display, mirroring a pos.order."""
from odoo import api, fields, models


class FilamindKitchenOrder(models.Model):
    _name = 'filamind.kitchen.order'
    _description = 'Kitchen Display Order'
    _order = 'create_date desc, id desc'

    display_id = fields.Many2one(
        'filamind.kitchen.display', string='Display', required=True,
        ondelete='cascade', index=True,
    )
    pos_order_id = fields.Many2one(
        'pos.order', string='POS Order', required=True,
        ondelete='cascade', index=True,
    )
    stage_id = fields.Many2one(
        'filamind.kitchen.stage', string='Stage', required=True,
        ondelete='restrict',
        domain="[('display_id', '=', display_id)]",
    )
    line_ids = fields.One2many(
        'filamind.kitchen.line', 'order_id', string='Lines',
    )

    table_number = fields.Integer(
        string='Table',
        compute='_compute_table_number', store=True,
    )
    customer_note = fields.Text(string='Customer Note')
    internal_note = fields.Text(string='Kitchen Note')

    fired_date = fields.Datetime(
        string='Fired At',
        help='When the order entered its initial stage.',
        default=fields.Datetime.now,
    )
    completed_date = fields.Datetime(
        string='Completed At',
        help='When the order moved into a final stage.',
    )
    completion_seconds = fields.Integer(
        string='Completion (s)', compute='_compute_completion', store=True,
    )

    company_id = fields.Many2one(
        related='display_id.company_id', store=True, readonly=True,
    )

    # ── Computed ────────────────────────────────────────────────────────
    @api.depends('pos_order_id')
    def _compute_table_number(self):
        for r in self:
            table = getattr(r.pos_order_id, 'table_id', False)
            r.table_number = (table.table_number if table else 0) or 0

    @api.depends('fired_date', 'completed_date')
    def _compute_completion(self):
        for r in self:
            if r.fired_date and r.completed_date:
                r.completion_seconds = int(
                    (r.completed_date - r.fired_date).total_seconds())
            else:
                r.completion_seconds = 0

    # ── Stage transitions ──────────────────────────────────────────────
    def transition(self, target_stage_id):
        """Move this order to `target_stage_id` (must belong to the same
        display). Sets completed_date when entering a final stage; clears
        it when leaving one."""
        Stage = self.env['filamind.kitchen.stage'].sudo()
        for r in self:
            target = Stage.browse(int(target_stage_id))
            if target.display_id != r.display_id:
                raise ValueError("stage does not belong to this display")
            vals = {'stage_id': target.id}
            if target.is_final and not r.completed_date:
                vals['completed_date'] = fields.Datetime.now()
            elif not target.is_final and r.completed_date:
                vals['completed_date'] = False
            r.write(vals)
        return True

    @api.model
    def _cron_auto_advance(self):
        """Cron: auto-move orders past their stage's auto_advance_seconds."""
        from datetime import timedelta
        now = fields.Datetime.now()
        Stage = self.env['filamind.kitchen.stage'].sudo()
        for stage in Stage.search([('auto_advance_seconds', '>', 0)]):
            cutoff = now - timedelta(seconds=stage.auto_advance_seconds)
            stuck = self.sudo().search([
                ('display_id', '=', stage.display_id.id),
                ('stage_id', '=', stage.id),
                ('fired_date', '<', cutoff),
            ])
            next_stage = Stage.search(
                [('display_id', '=', stage.display_id.id),
                 ('sequence', '>', stage.sequence)],
                order='sequence asc', limit=1)
            if next_stage:
                stuck.transition(next_stage.id)
        return True
