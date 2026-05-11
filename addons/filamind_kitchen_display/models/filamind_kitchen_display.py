"""Kitchen Display — one row per kitchen-station tablet.

Customers bookmark `/filamind_kitchen/<id>?access_token=<tok>` on a
tablet and the page auto-refreshes with new orders. The token is the
sole authentication: rotating it via `action_rotate_token` immediately
revokes any open tablet.
"""
import secrets

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class FilamindKitchenDisplay(models.Model):
    _name = 'filamind.kitchen.display'
    _description = 'Kitchen Display'
    _order = 'sequence, name'

    name = fields.Char(string='Display Name', required=True,
                       help='Shown on the tablet header. e.g. "Hot Kitchen #1".')
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one('res.company', required=True,
                                  default=lambda self: self.env.company)
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Colour Index', default=0)

    # Sources of new orders
    pos_config_ids = fields.Many2many(
        'pos.config', 'kitchen_display_pos_config_rel',
        'display_id', 'config_id',
        string='POS Configurations',
        help='New orders from these POS configurations appear on this '
             'display.',
    )
    category_ids = fields.Many2many(
        'pos.category', 'kitchen_display_pos_category_rel',
        'display_id', 'category_id',
        string='Product Categories',
        help='If set, only order lines whose product belongs to one of '
             'these categories are sent here. Leave empty to receive all.',
    )

    # Workflow
    stage_ids = fields.One2many(
        'filamind.kitchen.stage', 'display_id', string='Stages',
        help='Workflow columns on the tablet. Default = In Progress / '
             'Ready / Served.',
    )
    auto_clear = fields.Boolean(
        string='Auto-clear Served Orders', default=True,
    )
    clear_after_seconds = fields.Integer(
        string='Auto-clear After (s)', default=300,
        help='Served orders disappear from the tablet this many seconds '
             'after entering the final stage.',
    )

    # Public access
    access_token = fields.Char(
        string='Access Token', copy=False, readonly=True,
        index=True, default=lambda self: secrets.token_urlsafe(24),
        help='Rotating this revokes every open tablet immediately.',
    )
    public_url = fields.Char(
        string='Public URL', compute='_compute_public_url',
    )

    # Stats
    order_count = fields.Integer(string='Orders Today',
                                  compute='_compute_stats')
    average_time_seconds = fields.Integer(string='Avg Prep Time (s)',
                                           compute='_compute_stats')

    # ── Computed ────────────────────────────────────────────────────────
    @api.depends('access_token')
    def _compute_public_url(self):
        base = self.env['ir.config_parameter'].sudo().get_param(
            'web.base.url', '')
        for r in self:
            r.public_url = '%s/filamind_kitchen/%s?access_token=%s' % (
                base, r.id, r.access_token or '')

    def _compute_stats(self):
        Order = self.env['filamind.kitchen.order'].sudo()
        for r in self:
            today_orders = Order.search([
                ('display_id', '=', r.id),
                ('create_date', '>=', fields.Date.today()),
            ])
            r.order_count = len(today_orders)
            done = today_orders.filtered(lambda o: o.completion_seconds)
            r.average_time_seconds = (
                sum(done.mapped('completion_seconds')) // len(done)
                if done else 0)

    # ── Actions ─────────────────────────────────────────────────────────
    def action_rotate_token(self):
        """Generate a new access_token. Any currently-open tablet stops
        receiving updates and must be re-bookmarked with the new URL."""
        for r in self:
            r.access_token = secrets.token_urlsafe(24)
        return True

    def action_open_public(self):
        self.ensure_one()
        if not self.public_url:
            raise UserError(_("Display has no access_token yet."))
        return {
            'type': 'ir.actions.act_url',
            'url': self.public_url,
            'target': 'new',
        }

    def action_clear_served(self):
        """Manual cleanup: remove all served orders from the display."""
        Order = self.env['filamind.kitchen.order']
        for r in self:
            served_stage = r.stage_ids.filtered(lambda s: s.is_final)
            if not served_stage:
                continue
            Order.search([
                ('display_id', '=', r.id),
                ('stage_id', 'in', served_stage.ids),
            ]).unlink()
        return True

    # ── ORM ─────────────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        # Ship default 3 stages so the tablet works out of the box
        Stage = self.env['filamind.kitchen.stage']
        for r in records:
            if not r.stage_ids:
                Stage.create([
                    {'display_id': r.id, 'sequence': 10,
                     'name': 'In Progress', 'color': 1, 'is_initial': True},
                    {'display_id': r.id, 'sequence': 20,
                     'name': 'Ready', 'color': 5},
                    {'display_id': r.id, 'sequence': 30,
                     'name': 'Served', 'color': 10, 'is_final': True},
                ])
        return records

    @api.model
    def _cron_auto_clear(self):
        """Cron: drop served orders past `clear_after_seconds`."""
        from datetime import timedelta
        Order = self.env['filamind.kitchen.order'].sudo()
        now = fields.Datetime.now()
        for d in self.search([('auto_clear', '=', True),
                               ('clear_after_seconds', '>', 0)]):
            cutoff = now - timedelta(seconds=d.clear_after_seconds)
            Order.search([
                ('display_id', '=', d.id),
                ('stage_id.is_final', '=', True),
                ('completed_date', '!=', False),
                ('completed_date', '<', cutoff),
            ]).unlink()
        return True
