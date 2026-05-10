"""HTTP endpoints used by IoT Boxes to pair, heartbeat, and report devices.

All endpoints are auth='public' because IoT Boxes don't carry Odoo user
credentials — they authenticate with a per-box token issued at pairing time.

Each route is registered under TWO paths:
  * /filamind_iot/<action>   — canonical filamind path
  * /iot/box/<action>        — alias matching the path scheme used by the
                               filamind-iotbox image and by the upstream
                               Odoo IoT Box when sending results back via
                               send_to_controller(method=...).

Production deployments must NOT echo internal exception messages back to
the box (information disclosure). On error we log the traceback server-side
and return a generic message.
"""
import json
import logging

from odoo import fields, http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


def _json_response(data, status=200):
    return Response(
        json.dumps(data),
        status=status,
        mimetype='application/json',
    )


def _client_ip():
    return request.httprequest.remote_addr or ''


def _internal_error(prefix):
    """Common error envelope. Logs the real traceback, hides it from the box."""
    _logger.exception('%s', prefix)
    return _json_response({'error': 'Internal error'}, status=500)


class IotController(http.Controller):

    # ── Pairing ──────────────────────────────────────────────────────────
    @http.route(['/filamind_iot/pair', '/iot/box/pair'],
                type='http', auth='public', methods=['POST'], csrf=False)
    def pair(self, **post):
        """The box posts {'code': '<pairing_code>', 'identifier': '<mac>'}
        and receives back {'token': '<auth_token>', 'box_id': <id>} on
        success. This binds that identifier to the matching iot.box record."""
        try:
            payload = request.httprequest.get_json(silent=True) or post
            code = (payload.get('code') or '').strip().upper()
            identifier = (payload.get('identifier') or '').strip()
            ip_address = payload.get('ip_address') or _client_ip()

            if not code or not identifier:
                return _json_response(
                    {'error': 'Missing code or identifier'}, status=400)

            Box = request.env['iot.box'].sudo()
            box = Box.search([
                ('pairing_code', '=', code),
                ('state', '=', 'pairing'),
            ], limit=1)

            if not box:
                return _json_response(
                    {'error': 'Invalid or expired pairing code'}, status=404)

            now = fields.Datetime.now()
            if box.pairing_expiry and box.pairing_expiry < now:
                return _json_response(
                    {'error': 'Pairing code expired'}, status=410)

            box.write({
                'identifier': identifier,
                'ip_address': ip_address,
                'state': 'connected',
                'last_heartbeat': now,
                'pairing_code': False,
                'pairing_expiry': False,
                'version': payload.get('version') or box.version,
                'mac_address': payload.get('mac_address') or box.mac_address,
                'hostname': payload.get('hostname') or box.hostname,
            })
            box.message_post(body='IoT Box paired via API from %s.' % ip_address)
            request.env['iot.connection.log'].sudo().create({
                'iot_box_id': box.id,
                'event': 'paired',
                'ip_address': ip_address,
                'message': 'Paired via API',
                'payload': json.dumps(payload)[:2000],
            })
            return _json_response({
                'status': 'ok',
                'box_id': box.id,
                'name': box.name,
                'token': box.sudo().token,
            })

        except Exception:
            return _internal_error('IoT pairing failed')

    # ── Auth helper ──────────────────────────────────────────────────────
    def _authenticate_box(self, payload):
        """Return the iot.box matched by (identifier, token) or None."""
        identifier = (payload.get('identifier') or '').strip()
        token = (payload.get('token') or '').strip()
        if not identifier or not token:
            return None
        box = request.env['iot.box'].sudo().search([
            ('identifier', '=', identifier),
        ], limit=1)
        if not box or box.sudo().token != token:
            return None
        if box.state == 'blocked':
            return None
        return box

    # ── Heartbeat ────────────────────────────────────────────────────────
    @http.route(['/filamind_iot/heartbeat', '/iot/box/heartbeat'],
                type='http', auth='public', methods=['POST'], csrf=False)
    def heartbeat(self, **post):
        try:
            payload = request.httprequest.get_json(silent=True) or post
            box = self._authenticate_box(payload)
            if not box:
                return _json_response({'error': 'Unauthorized'}, status=401)

            box._record_heartbeat(payload)
            request.env['iot.connection.log'].sudo().create({
                'iot_box_id': box.id,
                'event': 'heartbeat',
                'ip_address': _client_ip(),
                'payload': json.dumps(payload)[:2000],
            })
            return _json_response({
                'status': 'ok',
                'server_time': fields.Datetime.now().isoformat(),
            })
        except Exception:
            return _internal_error('IoT heartbeat failed')

    # ── Device reporting ─────────────────────────────────────────────────
    @http.route(['/filamind_iot/devices',
                 '/iot/box/devices',
                 '/iot/box/send_devices'],
                type='http', auth='public', methods=['POST'], csrf=False)
    def report_devices(self, **post):
        """The box reports its current list of devices.
        Payload: {'identifier':..., 'token':..., 'devices': [
            {'identifier': 'usb-1', 'name': 'Epson TM-T20',
             'type': 'receipt_printer', 'connection': 'usb',
             'manufacturer': 'Epson', 'state': 'online'}, ...
        ]}
        """
        try:
            payload = request.httprequest.get_json(silent=True) or {}
            box = self._authenticate_box(payload)
            if not box:
                return _json_response({'error': 'Unauthorized'}, status=401)

            devices_payload = payload.get('devices') or []
            auto_discover = request.env['ir.config_parameter'].sudo().get_param(
                'filamind_iot.auto_discover', 'True').lower() not in ('false', '0')

            Device = request.env['iot.device'].sudo()
            Type = request.env['iot.device.type'].sudo()
            results = []

            for d in devices_payload:
                ident = (d.get('identifier') or '').strip()
                if not ident:
                    continue

                existing = Device.search([
                    ('iot_box_id', '=', box.id),
                    ('identifier', '=', ident),
                ], limit=1)

                type_code = d.get('type') or 'generic'
                dtype = Type.search([('code', '=', type_code)], limit=1)
                if not dtype:
                    dtype = Type.search([('code', '=', 'generic')], limit=1)

                vals = {
                    'name': d.get('name') or ident,
                    'iot_box_id': box.id,
                    'identifier': ident,
                    'type_id': dtype.id if dtype else False,
                    'connection': d.get('connection') or 'usb',
                    'manufacturer': d.get('manufacturer'),
                    'model_name': d.get('model'),
                    'subtype': d.get('subtype'),
                    'state': d.get('state') or 'online',
                    'last_seen': fields.Datetime.now(),
                }

                if existing:
                    existing.write(vals)
                    results.append({'identifier': ident, 'action': 'updated',
                                    'id': existing.id})
                elif auto_discover:
                    new_dev = Device.create(vals)
                    request.env['iot.connection.log'].sudo().create({
                        'iot_box_id': box.id,
                        'device_id': new_dev.id,
                        'event': 'discovered',
                        'message': 'Device auto-discovered: %s' % new_dev.name,
                    })
                    results.append({'identifier': ident, 'action': 'created',
                                    'id': new_dev.id})
                else:
                    results.append({'identifier': ident,
                                    'action': 'ignored (auto_discover off)'})

            return _json_response({'status': 'ok', 'devices': results})

        except Exception:
            return _internal_error('IoT device reporting failed')

    # ── Device status update ─────────────────────────────────────────────
    @http.route(['/filamind_iot/device_status',
                 '/iot/box/device_status',
                 '/iot/box/send_websocket'],
                type='http', auth='public', methods=['POST'], csrf=False)
    def device_status(self, **post):
        """Update a single device state.
        Payload: {'identifier':..., 'token':..., 'device': '<device_ident>',
                  'state': 'online|offline|error', 'message': '...'}

        The /iot/box/send_websocket alias matches the default `method` used
        by the upstream Odoo IoT Box's send_to_controller helper, allowing
        the box to push device-state updates without code changes.
        """
        try:
            payload = request.httprequest.get_json(silent=True) or post
            box = self._authenticate_box(payload)
            if not box:
                return _json_response({'error': 'Unauthorized'}, status=401)

            dev_ident = (payload.get('device') or '').strip()
            new_state = payload.get('state') or 'offline'
            if new_state not in ('online', 'offline', 'error', 'disabled'):
                return _json_response({'error': 'Bad state'}, status=400)

            device = request.env['iot.device'].sudo().search([
                ('iot_box_id', '=', box.id),
                ('identifier', '=', dev_ident),
            ], limit=1)
            if not device:
                return _json_response({'error': 'Device not found'}, status=404)

            device._record_state(new_state, payload.get('message'))
            return _json_response({'status': 'ok'})

        except Exception:
            return _internal_error('IoT device status failed')
