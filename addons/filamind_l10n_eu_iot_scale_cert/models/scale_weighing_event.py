"""Audit log for every weight-for-pricing event from a certified
scale. Used by EU inspectors to verify cashier conduct."""
from datetime import timedelta

from odoo import _, api, fields, models


class ScaleWeighingEvent(models.Model):
    """One row per weight that flowed into a sale.

    Inspectors can inspect this list to confirm that no weights
    below ``min_weight_g`` were used for pricing.
    """
    _name = 'filamind.scale.weighing.event'
    _description = 'Legal-for-Trade Weighing Event'
    _order = 'create_date desc'

    device_id = fields.Many2one(
        'iot.device', string='Scale', required=True,
        ondelete='restrict', index=True,
    )
    pos_order_id = fields.Many2one(
        'pos.order', string='POS Order', ondelete='set null', index=True,
    )
    pos_order_line_id = fields.Many2one(
        'pos.order.line', string='POS Line',
        ondelete='set null', index=True,
    )
    weight_g = fields.Float(string='Weight (g)', required=True)
    unit = fields.Char(string='Unit', default='g')
    cashier_id = fields.Many2one('res.users', string='Cashier')
    legal = fields.Boolean(
        string='Legal for Trade?',
        help='False when the weight was below the certified Min, or '
             'when the device had no certificate at the time.',
    )
    note = fields.Char()

    retention_days = fields.Integer(
        string='Retention (days)', default=400,
        help='Used by the purge cron. EU member states require at '
             'least 1 year — 400 days gives a small buffer.',
        compute=False, store=False,  # company-level setting, not row-level
    )

    @api.model
    def _record(self, device, weight_g, **kw):
        """Helper called by the IoT controller / pos.order.create_from_ui."""
        legal = True
        if device.lne_certificate_status not in ('ok', 'expiring'):
            legal = False
        if device.lne_min_weight_g and weight_g < device.lne_min_weight_g:
            legal = False
        return self.sudo().create({
            'device_id': device.id,
            'weight_g': weight_g,
            'unit': kw.get('unit') or 'g',
            'pos_order_id': kw.get('pos_order_id'),
            'pos_order_line_id': kw.get('pos_order_line_id'),
            'cashier_id': kw.get('cashier_id') or self.env.uid,
            'legal': legal,
            'note': kw.get('note') or '',
        })

    @api.model
    def _cron_purge_old_weighing_events(self):
        """Drop events older than the configured retention window."""
        retention = int(self.env['ir.config_parameter'].sudo().get_param(
            'filamind_l10n_eu_iot_scale_cert.retention_days', '400'))
        cutoff = fields.Datetime.now() - timedelta(days=retention)
        old = self.sudo().search([('create_date', '<', cutoff)])
        n = len(old)
        old.unlink()
        if n:
            self.env['ir.logging'].sudo().create({
                'name': __name__,
                'type': 'server',
                'level': 'INFO',
                'dbname': self.env.cr.dbname,
                'message': _(
                    'filamind_l10n_eu_iot_scale_cert: purged %d weighing '
                    'events older than %d days.') % (n, retention),
                'path': 'filamind_l10n_eu_iot_scale_cert',
                'func': '_cron_purge_old_weighing_events',
                'line': 0,
            })
