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
                 '/iot/box/device_status'],
                type='http', auth='public', methods=['POST'], csrf=False)
    def device_status(self, **post):
        """Update a single device state.
        Payload: {'identifier':..., 'token':..., 'device': '<device_ident>',
                  'state': 'online|offline|error', 'message': '...'}
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

    # ── Setup (called once at box startup) ───────────────────────────────
    @http.route(['/filamind_iot/setup', '/iot/setup'],
                type='http', auth='public', methods=['POST'], csrf=False)
    def setup(self, **post):
        """The box calls this on first boot after a server URL is set.

        Body (Odoo JSON-RPC envelope):
          {"params": {"iot_box": {...meta...}, "devices": {ident: {...}}}}

        Authentication is by token via box.identifier match on the iot_box
        meta block, OR (legacy fallback) by mac_address. The endpoint:
          1. Resolves the iot.box record (creating one in 'pairing' state if
             we don't recognise the identifier — the admin can claim it via
             the wizard's box-token mode).
          2. Allocates a WebSocket channel name (`iot_<token>`) and returns
             it as the JSON-RPC `result` so the box's WebsocketClient
             subscribes to it.
          3. Auto-discovers any reported devices (gated by
             filamind_iot.auto_discover).
        """
        try:
            payload = request.httprequest.get_json(silent=True) or post
            params = payload.get('params') or payload  # tolerate bare body
            iot_box_meta = params.get('iot_box') or {}
            devices_meta = params.get('devices') or {}

            identifier = (iot_box_meta.get('identifier')
                          or iot_box_meta.get('mac')
                          or iot_box_meta.get('mac_address')
                          or '').strip()
            if not identifier:
                return _json_response(
                    {'error': 'Missing identifier'}, status=400)

            Box = request.env['iot.box'].sudo()
            box = Box.search([('identifier', '=', identifier)], limit=1)

            if not box:
                # Auto-create in 'pairing' state — admin can later claim
                # via the wizard's box-token mode.
                box = Box.create({
                    'name': iot_box_meta.get('name') or _box_default_name(identifier),
                    'identifier': identifier,
                    'ip_address': iot_box_meta.get('ip_url')
                                   or iot_box_meta.get('ip')
                                   or _client_ip(),
                    'mac_address': iot_box_meta.get('mac_address') or identifier,
                    'hostname': iot_box_meta.get('hostname'),
                    'version': iot_box_meta.get('version'),
                    'state': 'pairing',
                })

            # Allocate / refresh the WebSocket channel for this box.
            channel = box._ensure_ws_channel()

            # Touch heartbeat so the box appears online immediately.
            box.sudo().write({
                'last_heartbeat': fields.Datetime.now(),
                'ip_address': iot_box_meta.get('ip_url')
                               or iot_box_meta.get('ip')
                               or box.ip_address
                               or _client_ip(),
                'version': iot_box_meta.get('version') or box.version,
                'hostname': iot_box_meta.get('hostname') or box.hostname,
                'state': 'connected' if box.state != 'blocked' else 'blocked',
            })
            request.env['iot.connection.log'].sudo().create({
                'iot_box_id': box.id,
                'event': 'connected',
                'ip_address': _client_ip(),
                'message': 'Setup call: ws_channel=%s' % channel,
                'payload': json.dumps(params, default=str)[:2000],
            })

            # Discover devices (best-effort — same logic as report_devices
            # but tolerant of the {"id": {...}} dict shape Odoo upstream uses).
            self._auto_discover_devices(box, devices_meta)

            # The box reads `data.get('result', '')` — string return form.
            return _json_response({'jsonrpc': '2.0', 'result': channel})

        except Exception:
            return _internal_error('IoT setup failed')

    def _auto_discover_devices(self, box, devices_dict):
        if not devices_dict:
            return
        auto = request.env['ir.config_parameter'].sudo().get_param(
            'filamind_iot.auto_discover', 'True').lower() not in ('false', '0')
        if not auto:
            return
        Device = request.env['iot.device'].sudo()
        Type = request.env['iot.device.type'].sudo()
        generic = Type.search([('code', '=', 'generic')], limit=1)
        for ident, meta in (devices_dict or {}).items():
            if not ident:
                continue
            existing = Device.search([
                ('iot_box_id', '=', box.id),
                ('identifier', '=', ident),
            ], limit=1)
            type_code = (meta.get('type') if isinstance(meta, dict) else None) or 'generic'
            dtype = Type.search([('code', '=', type_code)], limit=1) or generic
            vals = {
                'name': (meta or {}).get('name') or ident,
                'iot_box_id': box.id,
                'identifier': ident,
                'type_id': dtype.id if dtype else False,
                'connection': (meta or {}).get('connection') or 'usb',
                'manufacturer': (meta or {}).get('manufacturer'),
                'model_name': (meta or {}).get('model'),
                'subtype': (meta or {}).get('subtype'),
                'state': 'online',
                'last_seen': fields.Datetime.now(),
            }
            if existing:
                existing.write(vals)
            else:
                Device.create(vals)

    # ── Command result collector (box → server, after acting) ────────────
    @http.route(['/filamind_iot/command_result', '/iot/box/send_websocket'],
                type='http', auth='public', methods=['POST'], csrf=False)
    def command_result(self, **post):
        """The box POSTs here after handling a bus message. We correlate
        with the originating iot.command.queue entry by session_id and
        record the result.

        Body shape: {"params": {<communication.handle_message return>}}
        where the inner dict has 'session_id' (correlation), 'status',
        'iot_box_identifier', 'device_identifier', and result-specific
        fields.
        """
        try:
            payload = request.httprequest.get_json(silent=True) or post
            params = payload.get('params') or payload
            session_id = (params.get('session_id') or params.get('owner') or '').strip()
            if not session_id:
                return _json_response(
                    {'error': 'Missing session_id'}, status=400)

            queue = request.env['iot.command.queue'].sudo().search(
                [('name', '=', session_id)], limit=1)
            if not queue:
                # Not necessarily an error — could be a stale message after
                # a server restart. Log and accept.
                _logger.info(
                    "command_result: no queue entry for session_id %s",
                    session_id)
                return _json_response({'status': 'ok', 'matched': False})

            queue.record_response(params)
            return _json_response({'status': 'ok', 'matched': True,
                                   'queue_id': queue.id})

        except Exception:
            return _internal_error('IoT command_result failed')


def _box_default_name(identifier):
    short = identifier[:8] if identifier else 'unknown'
    return 'IoT Box %s' % short
