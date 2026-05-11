"""Read-only mirror of the proxy's tenants."""
from odoo import _, api, fields, models


class ProxyTenant(models.Model):
    _name = 'iot.proxy.tenant'
    _description = 'Proxy tenant (mirror)'
    _order = 'name'
    _rec_name = 'name'

    proxy_id = fields.Many2one(
        'iot.proxy.config', string='Proxy', required=True, ondelete='cascade',
    )
    remote_id = fields.Char(string='Tenant ID', required=True, index=True)
    name = fields.Char(required=True)
    plan = fields.Char()
    box_quota = fields.Integer()
    contact_email = fields.Char()
    license_key = fields.Char()
    license_expires = fields.Datetime()
    remote_created_at = fields.Datetime()

    _sql_constraints = [
        ('uniq_remote_per_proxy', 'unique(proxy_id, remote_id)',
         'A tenant ID can only appear once per proxy.'),
    ]

    # -- Refresh from proxy ------------------------------------------

    @api.model
    def _refresh_from(self, proxy):
        """Drop the local cache for `proxy` and re-fetch from the API."""
        existing = self.search([('proxy_id', '=', proxy.id)])
        existing.unlink()
        resp = proxy._request('GET', '/admin/tenants?limit=500')
        rows = resp.json()
        return self.create([{
            'proxy_id': proxy.id,
            'remote_id': r['id'],
            'name': r.get('name') or '',
            'plan': r.get('plan'),
            'box_quota': r.get('box_quota') or 0,
            'contact_email': r.get('contact_email'),
            'license_key': r.get('license_key'),
            'license_expires': r.get('license_expires'),
            'remote_created_at': r.get('created_at'),
        } for r in rows])

    # -- Actions -----------------------------------------------------

    def action_delete_remote(self):
        for rec in self:
            rec.proxy_id._request(
                'DELETE', f'/admin/tenants/{rec.remote_id}',
            )
        return self.env['iot.proxy.config'].browse(
            self.mapped('proxy_id.id'),
        ).action_refresh_all() if self else True

    def action_open_form(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
            'name': _('Tenant: %s', self.name),
        }
