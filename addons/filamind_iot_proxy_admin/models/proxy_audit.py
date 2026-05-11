"""Read-only mirror of the proxy's audit log."""
import json

from odoo import api, fields, models


class ProxyAudit(models.Model):
    _name = 'iot.proxy.audit'
    _description = 'Proxy audit log entry (mirror)'
    _order = 'remote_id desc'
    _rec_name = 'event'

    proxy_id = fields.Many2one(
        'iot.proxy.config', string='Proxy', required=True, ondelete='cascade',
    )
    remote_id = fields.Integer(string='Audit Row ID', required=True, index=True)
    ts = fields.Datetime(string='Timestamp')
    actor = fields.Char()
    event = fields.Char()
    box_id = fields.Many2one('iot.proxy.box', string='Box')
    tenant_id = fields.Many2one('iot.proxy.tenant', string='Tenant')
    payload = fields.Text(help='Raw JSON payload from the proxy.')

    _sql_constraints = [
        ('uniq_remote_per_proxy', 'unique(proxy_id, remote_id)',
         'An audit row can only appear once per proxy.'),
    ]

    @api.model
    def _refresh_from(self, proxy, limit=500):
        """Drop the local cache for `proxy` and re-fetch the latest N rows."""
        existing = self.search([('proxy_id', '=', proxy.id)])
        existing.unlink()
        resp = proxy._request('GET', f'/admin/audit?limit={int(limit)}')
        rows = resp.json()
        tenants = self.env['iot.proxy.tenant'].search(
            [('proxy_id', '=', proxy.id)])
        tenant_by_remote = {t.remote_id: t.id for t in tenants}
        boxes = self.env['iot.proxy.box'].search(
            [('proxy_id', '=', proxy.id)])
        box_by_remote = {b.remote_id: b.id for b in boxes}
        return self.create([{
            'proxy_id': proxy.id,
            'remote_id': r['id'],
            'ts': r.get('ts'),
            'actor': r.get('actor'),
            'event': r.get('event'),
            'box_id': box_by_remote.get(r.get('box_id')),
            'tenant_id': tenant_by_remote.get(r.get('tenant_id')),
            'payload': json.dumps(r.get('payload')) if r.get('payload') else False,
        } for r in rows])
