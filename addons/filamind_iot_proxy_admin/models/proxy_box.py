"""Read-only mirror of the proxy's boxes."""
from odoo import api, fields, models


class ProxyBox(models.Model):
    _name = 'iot.proxy.box'
    _description = 'Proxy box (mirror)'
    _order = 'remote_created_at desc'
    _rec_name = 'serial_number'

    proxy_id = fields.Many2one(
        'iot.proxy.config', string='Proxy', required=True, ondelete='cascade',
    )
    remote_id = fields.Char(string='Box ID', required=True, index=True)
    tenant_id = fields.Many2one('iot.proxy.tenant', string='Tenant')
    serial_number = fields.Char(required=True, index=True)
    paired_db_uuid = fields.Char(string='Paired DB UUID')
    paired_server_url = fields.Char(string='Paired Server URL')
    paired_at = fields.Datetime()
    last_seen = fields.Datetime()
    state = fields.Selection(
        [('pending', 'Pending'),
         ('paired', 'Paired'),
         ('revoked', 'Revoked')],
        string='Status', default='pending',
    )
    remote_created_at = fields.Datetime()

    _sql_constraints = [
        ('uniq_remote_per_proxy', 'unique(proxy_id, remote_id)',
         'A box ID can only appear once per proxy.'),
    ]

    # -- Refresh from proxy ------------------------------------------

    @api.model
    def _refresh_from(self, proxy):
        """Drop the local cache for `proxy` and re-fetch from the API."""
        existing = self.search([('proxy_id', '=', proxy.id)])
        existing.unlink()
        resp = proxy._request('GET', '/admin/boxes?limit=500')
        rows = resp.json()
        # Tenant id resolution -- assumes tenants are already refreshed.
        tenants = self.env['iot.proxy.tenant'].search(
            [('proxy_id', '=', proxy.id)])
        tenant_by_remote = {t.remote_id: t.id for t in tenants}
        return self.create([{
            'proxy_id': proxy.id,
            'remote_id': r['id'],
            'tenant_id': tenant_by_remote.get(r.get('tenant_id')),
            'serial_number': r['serial_number'],
            'paired_db_uuid': r.get('paired_db_uuid'),
            'paired_server_url': r.get('paired_server_url'),
            'paired_at': r.get('paired_at'),
            'last_seen': r.get('last_seen'),
            'state': r.get('status') if r.get('status') in (
                'pending', 'paired', 'revoked') else 'pending',
            'remote_created_at': r.get('created_at'),
        } for r in rows])

    # -- Actions -----------------------------------------------------

    def action_unpair(self):
        for rec in self:
            rec.proxy_id._request(
                'POST', f'/admin/boxes/{rec.remote_id}/unpair',
            )
        if self:
            return self.proxy_id[:1].action_refresh_all()
        return True
