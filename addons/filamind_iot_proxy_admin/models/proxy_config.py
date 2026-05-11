"""Connection settings for a filamind-iot-proxy deployment.

Single record per Odoo DB (the singleton convention used by
``ir.config_parameter``-style models in stock Odoo). The first record
is "the active config"; we only ever read by ``get_active()``.
"""
import logging

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ProxyConfig(models.Model):
    _name = 'iot.proxy.config'
    _description = 'filamind-iot-proxy connection settings'
    _rec_name = 'proxy_url'

    proxy_url = fields.Char(
        string='Proxy URL',
        required=True,
        help='Base URL of the filamind-iot-proxy, '
             'e.g. https://iot-proxy.filamind.app',
    )
    admin_token = fields.Char(
        string='Admin Bearer Token',
        required=True,
        help='Long random string set as ADMIN_TOKEN in the proxy '
             "container's environment.",
    )
    timeout = fields.Integer(
        string='HTTP Timeout (s)', default=15, required=True,
    )
    last_health = fields.Char(string='Last Health-check', readonly=True)
    last_health_at = fields.Datetime(string='Checked At', readonly=True)
    active = fields.Boolean(default=True)

    @api.model
    def get_active(self):
        """Return the singleton active config or raise."""
        rec = self.search([('active', '=', True)], limit=1)
        if not rec:
            raise UserError(_(
                'No active filamind-iot-proxy config. '
                'Create one in IoT Proxy → Configuration first.'))
        return rec

    # -- HTTP helpers (instance methods, called by other models) -----

    def _headers(self):
        self.ensure_one()
        return {'Authorization': f'Bearer {self.admin_token}',
                'Accept': 'application/json'}

    def _url(self, path):
        self.ensure_one()
        return self.proxy_url.rstrip('/') + path

    def _request(self, method, path, **kwargs):
        self.ensure_one()
        kwargs.setdefault('headers', {}).update(self._headers())
        kwargs.setdefault('timeout', self.timeout)
        try:
            resp = requests.request(method, self._url(path), **kwargs)
        except requests.RequestException as exc:
            _logger.warning('proxy %s %s failed: %s', method, path, exc)
            raise UserError(_(
                'Could not reach proxy at %(url)s: %(err)s',
                url=self.proxy_url, err=exc)) from exc
        if resp.status_code == 401:
            raise UserError(_('Proxy rejected the bearer token (401).'))
        if resp.status_code == 403:
            raise UserError(_('Proxy says token is invalid (403).'))
        if resp.status_code == 503:
            raise UserError(_(
                'Proxy returned 503 — admin_token is unset on the '
                'server side.'))
        if resp.status_code >= 400:
            try:
                detail = resp.json().get('detail', resp.text)
            except ValueError:
                detail = resp.text
            raise UserError(_(
                'Proxy %(method)s %(path)s -> %(code)s: %(detail)s',
                method=method, path=path,
                code=resp.status_code, detail=detail))
        return resp

    # -- Actions (buttons in the form view) --------------------------

    def action_check_health(self):
        for rec in self:
            try:
                resp = requests.get(
                    rec._url('/healthz'), timeout=rec.timeout,
                )
                body = resp.json()
                rec.last_health = (
                    f"{body.get('status')} (db={body.get('db')}, "
                    f"redis={body.get('redis')})"
                )
            except (requests.RequestException, ValueError) as exc:
                rec.last_health = f'ERROR: {exc}'
            rec.last_health_at = fields.Datetime.now()
        return True

    def action_refresh_all(self):
        """Pull tenants + boxes + audit from the proxy."""
        for rec in self:
            self.env['iot.proxy.tenant']._refresh_from(rec)
            self.env['iot.proxy.box']._refresh_from(rec)
            self.env['iot.proxy.audit']._refresh_from(rec)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Refresh complete'),
                'message': _('Tenants, boxes, and audit log are up to date.'),
                'type': 'success',
                'sticky': False,
            },
        }
