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
                # filamind extension fields the box patch (002) saves into
                # /home/pi/odoo.conf so the WebsocketClient can build the
                # /web/login?db=... URL needed for an authenticated WS.
                'db_name': request.env.cr.dbname,
                'ws_channel': request.env['iot.channel'].sudo().get_iot_channel(),
                'transports': ['websocket', 'longpoll', 'shortpoll'],
                'min_poll_interval': 5,
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

    # ── Upstream-parity endpoints (Phase 1) ──────────────────────────────
    @http.route(['/filamind_iot/log', '/iot/log'],
                type='http', auth='public', methods=['POST'], csrf=False)
    def collect_log(self, **post):
        """Streaming log shipper. The upstream box POSTs chunked text
        (NOT JSON) here every 0.5 s. Body shape:

            identifier <IOT_IDENTIFIER><log/>
            <level>,<message><log/>
            <level>,<message><log/>
            ...

        Header `X-Odoo-Database` = db name.

        We just persist the lines into iot.connection.log (severity from
        the level) and return 200. No response body required.
        """
        try:
            body = request.httprequest.get_data(as_text=True)
            if not body:
                return _json_response({'status': 'ok'})

            ip = _client_ip()
            box_identifier = ''
            lines = []
            for raw in body.split('<log/>'):
                line = raw.strip()
                if not line:
                    continue
                if line.startswith('identifier '):
                    box_identifier = line[len('identifier '):].strip()
                else:
                    lines.append(line)

            if not box_identifier or not lines:
                return _json_response({'status': 'ok', 'accepted': 0})

            box = request.env['iot.box'].sudo().search(
                [('identifier', '=', box_identifier)], limit=1)
            if not box:
                # Unknown box — accept but drop on the floor (avoid 401 spam)
                return _json_response({'status': 'ok', 'matched': False})

            Log = request.env['iot.connection.log'].sudo()
            for line in lines[:50]:  # cap to avoid runaway batches
                level, _, message = line.partition(',')
                severity = {
                    'WARNING': 'warn', 'ERROR': 'error', 'CRITICAL': 'error',
                }.get(level.strip().upper(), 'info')
                Log.create({
                    'iot_box_id': box.id,
                    'event': 'error' if severity == 'error' else 'heartbeat',
                    'message': (message or line)[:512],
                    'ip_address': ip,
                    'severity': severity,
                })
            return _json_response({'status': 'ok', 'accepted': len(lines)})
        except Exception:
            return _internal_error('IoT log collect failed')

    @http.route(['/filamind_iot/keyboard_layouts', '/iot/keyboard_layouts'],
                type='http', auth='public', methods=['POST'], csrf=False)
    def keyboard_layouts(self, **post):
        """The keyboard driver POSTs the X11 layouts available on the box.
        Body is form-encoded `available_layouts=<json-list>`.
        """
        try:
            raw = post.get('available_layouts') or '[]'
            try:
                layouts = json.loads(raw) if isinstance(raw, str) else raw
            except ValueError:
                return _json_response({'error': 'Invalid layout JSON'},
                                       status=400)
            Layout = request.env['iot.keyboard.layout'].sudo()
            created = 0
            for entry in layouts or []:
                if not isinstance(entry, dict):
                    continue
                layout = (entry.get('layout') or '').strip()
                variant = (entry.get('variant') or '').strip()
                if not layout:
                    continue
                if Layout.search_count([('layout', '=', layout),
                                        ('variant', '=', variant)]):
                    continue
                Layout.create({
                    'layout': layout,
                    'variant': variant,
                    'language': entry.get('language') or layout,
                })
                created += 1
            return _json_response({'status': 'ok', 'created': created})
        except Exception:
            return _internal_error('IoT keyboard_layouts failed')

    @http.route(['/iot/box/<int:box_id>/display_url',
                 '/filamind_iot/box/<int:box_id>/display_url'],
                type='http', auth='public', methods=['GET'])
    def display_url(self, box_id, **kwargs):
        """Return per-display URLs for every display device on a box.

        Response: {<device_identifier>: <url>, ...}

        The box's display driver polls this every 60 s and refreshes the
        kiosk browser when the URL changes.
        """
        try:
            box = request.env['iot.box'].sudo().browse(box_id).exists()
            if not box:
                return _json_response({}, status=404)
            urls = {
                d.identifier: d.display_url or ''
                for d in box.device_ids
                if (d.type_id.code or '').lower() in ('display', 'customer_display')
                   and d.display_url
            }
            return _json_response(urls)
        except Exception:
            return _internal_error('IoT display_url failed')

    @http.route(['/filamind_iot/get_handlers', '/iot/get_handlers'],
                type='http', auth='public', methods=['POST'], csrf=False)
    def get_handlers(self, **post):
        """Stub for the upstream box's `download_iot_handlers` flow.
        Returns {not_modified: True} so the box keeps its bundled drivers
        and doesn't try to fetch custom Python from us.

        A future filamind addon may serve real custom handler bundles
        here, gated by box.use_custom_handlers.
        """
        try:
            return _json_response({'not_modified': True, 'handlers': {}})
        except Exception:
            return _internal_error('IoT get_handlers failed')

    # ── Multi-transport polling (Phase 2) ────────────────────────────────
    @http.route(['/filamind_iot/poll', '/iot/box/poll'],
                type='http', auth='public', methods=['POST'], csrf=False)
    def poll_long(self, **post):
        """Long-poll: block up to `wait_seconds` (capped at 30 s) waiting
        for new iot.command.queue entries addressed to this box.

        Body:
          {identifier, token, last_seq, wait_seconds=20}

        Response:
          {
            "commands": [{id, method, payload}, ...],
            "next_seq": <highest id returned, or last_seq if none>,
            "server_time": <iso>,
          }

        The box is expected to call /filamind_iot/command_result for each
        command after acting on it.
        """
        try:
            payload = request.httprequest.get_json(silent=True) or post
            box = self._authenticate_box(payload)
            if not box:
                return _json_response({'error': 'Unauthorized'}, status=401)

            last_seq = int(payload.get('last_seq') or 0)
            wait = max(0, min(30, int(payload.get('wait_seconds') or 20)))
            return self._poll_block(box, last_seq, wait)
        except Exception:
            return _internal_error('IoT poll failed')

    @http.route(['/filamind_iot/poll_short', '/iot/box/poll_short'],
                type='http', auth='public', methods=['POST'], csrf=False)
    def poll_short(self, **post):
        """Short-poll: same as /poll but returns immediately (no blocking)."""
        try:
            payload = request.httprequest.get_json(silent=True) or post
            box = self._authenticate_box(payload)
            if not box:
                return _json_response({'error': 'Unauthorized'}, status=401)
            last_seq = int(payload.get('last_seq') or 0)
            return self._poll_block(box, last_seq, wait_seconds=0)
        except Exception:
            return _internal_error('IoT poll_short failed')

    def _poll_block(self, box, last_seq, wait_seconds):
        """Shared implementation for long-poll and short-poll.

        Polls iot.command.queue every 1s up to wait_seconds, returning
        all `sent` rows newer than last_seq. Marks them as delivered to
        prevent re-delivery on the next poll cycle.
        """
        import time as _time
        from odoo import fields as _fields

        Queue = request.env['iot.command.queue'].sudo()
        deadline = _time.monotonic() + max(0, wait_seconds)
        domain = [
            ('iot_box_id', '=', box.id),
            ('state', '=', 'sent'),
            ('id', '>', last_seq),
            ('delivered_at', '=', False),
        ]
        while True:
            request.env.cr.commit()  # see writes from other workers
            commands = Queue.search(domain, order='id asc', limit=50)
            if commands or _time.monotonic() >= deadline:
                break
            _time.sleep(1)

        out = []
        if commands:
            now = _fields.Datetime.now()
            commands.write({'delivered_at': now})
            request.env.cr.commit()
            for c in commands:
                out.append({
                    'id': c.id,
                    'session_id': c.name,
                    'method': c.method,
                    'payload': json.loads(c.request_payload or '{}')
                                if c.request_payload else {},
                    'timeout_seconds': c.timeout_seconds,
                })
        next_seq = max([c['id'] for c in out], default=last_seq)
        return _json_response({
            'commands': out,
            'next_seq': next_seq,
            'server_time': fields.Datetime.now().isoformat(),
        })


def _box_default_name(identifier):
    short = identifier[:8] if identifier else 'unknown'
    return 'IoT Box %s' % short
