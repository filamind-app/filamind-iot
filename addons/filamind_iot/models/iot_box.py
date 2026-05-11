import json
import uuid
from datetime import timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class IotBox(models.Model):
    """A physical IoT gateway that bridges devices (USB/serial/Bluetooth/LAN)
    to the Odoo backend over HTTPS."""
    _name = 'iot.box'
    _description = 'IoT Box'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'
    _rec_name = 'name'

    name = fields.Char(
        string='Name', required=True, tracking=True,
        default=lambda self: _('New'),
        help='Friendly name of this IoT Box.',
    )
    identifier = fields.Char(
        string='Identifier', index=True, copy=False, tracking=True,
        help='Unique hardware identifier (MAC address or serial number).',
    )
    ip_address = fields.Char(
        string='LAN IP', tracking=True,
        help='Local network address of the IoT Box, e.g. 192.168.1.50',
    )
    ip_url = fields.Char(
        string='Homepage URL', compute='_compute_ip_url',
        help='Clickable URL to the IoT Box homepage.',
    )
    mac_address = fields.Char(string='MAC Address')
    version = fields.Char(string='Firmware Version', tracking=True)
    pairing_code = fields.Char(
        string='Pairing Code', copy=False, readonly=True, tracking=True,
        help='One-time code the IoT Box uses to register with this Odoo instance.',
    )
    pairing_expiry = fields.Datetime(
        string='Pairing Code Expiry', readonly=True, copy=False)
    box_pairing_token = fields.Char(
        string='Box-Displayed Token', copy=False, index=True, tracking=True,
        help='Token shown on the IoT Box screen (HDMI) at boot. '
             'Use it to register the box from the Odoo side.',
    )
    token = fields.Char(
        string='Auth Token', copy=False, readonly=True, groups='base.group_system',
        default=lambda self: uuid.uuid4().hex,
        help='Secret token used by the IoT Box to authenticate API calls.',
    )
    ws_channel = fields.Char(
        string='WebSocket Channel', copy=False, readonly=True, index=True,
        help='bus.bus channel this box subscribes to. Filled in at first '
             '/iot/setup call. Server-side commands target this channel.',
    )

    # ── Upstream-Enterprise-parity fields (Phase 1) ──────────────────────
    use_custom_handlers = fields.Boolean(
        string='Use Custom Handlers',
        help='Opt-in to fetch custom drivers via /iot/get_handlers.',
    )
    must_install_fdm_module = fields.Boolean(
        string='Requires Fiscal Data Module',
        help='True when this box must run a country-specific fiscal '
             'data module (Belgium, Sweden, etc.).',
    )
    use_lna = fields.Boolean(
        string='LNA Logging',
        help='Enable EU LNE Logging-Network-Activity for trade scales.',
    )
    can_be_kiosk = fields.Boolean(
        string='Can be Kiosk',
        help='Allow this box to host a self-order kiosk display.',
    )
    ssl_certificate_end_date = fields.Datetime(
        string='SSL Cert Expiry', readonly=True,
        help='When the box-side TLS certificate expires.',
    )
    version_commit_url = fields.Html(
        string='Image Commit URL', readonly=True,
        help='Hyperlink to the Git commit the running image was built from.',
    )
    associated_pos_config_ids = fields.Many2many(
        'pos.config', string='POS Configurations',
        compute='_compute_associated_pos_config_ids', store=False,
        help='POS configurations whose iot_*_id fields point to a device '
             'on this box. Computed from filamind_pos_iot if installed; '
             'otherwise empty.',
    )

    state = fields.Selection([
        ('new', 'Not Paired'),
        ('pairing', 'Pairing'),
        ('connected', 'Connected'),
        ('disconnected', 'Disconnected'),
        ('blocked', 'Blocked'),
    ], string='Status', default='new', tracking=True, readonly=True)

    last_heartbeat = fields.Datetime(
        string='Last Seen', readonly=True, tracking=False)
    heartbeat_interval = fields.Integer(
        string='Heartbeat Interval (s)', default=60,
        help='Expected seconds between heartbeat pings from the box.',
    )
    is_online = fields.Boolean(
        string='Online', compute='_compute_is_online', store=False)

    # ── Network / security ───────────────────────────────────────────────
    wifi_ssid = fields.Char(string='Wi-Fi SSID')
    hostname = fields.Char(string='Hostname')
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company,
        required=True,
    )
    user_id = fields.Many2one(
        'res.users', string='Responsible',
        default=lambda self: self.env.user, tracking=True,
    )

    # ── Relations ────────────────────────────────────────────────────────
    device_ids = fields.One2many(
        'iot.device', 'iot_box_id', string='Devices')
    connection_log_ids = fields.One2many(
        'iot.connection.log', 'iot_box_id', string='Activity Log')

    device_count = fields.Integer(
        string='Devices', compute='_compute_counts')
    log_count = fields.Integer(
        string='Log Entries', compute='_compute_counts')
    command_count = fields.Integer(
        string='Commands', compute='_compute_counts')

    notes = fields.Html(string='Internal Notes')
    color = fields.Integer(string='Color Index', default=0)

    # ── Computed ─────────────────────────────────────────────────────────
    @api.depends('ip_address')
    def _compute_ip_url(self):
        for box in self:
            if box.ip_address:
                ip = box.ip_address.strip()
                if not ip.startswith('http'):
                    ip = 'http://' + ip
                box.ip_url = ip
            else:
                box.ip_url = False

    @api.depends('last_heartbeat', 'heartbeat_interval', 'state')
    def _compute_is_online(self):
        now = fields.Datetime.now()
        for box in self:
            if box.state != 'connected' or not box.last_heartbeat:
                box.is_online = False
                continue
            threshold = timedelta(seconds=(box.heartbeat_interval or 60) * 3)
            box.is_online = (now - box.last_heartbeat) < threshold

    @api.depends('device_ids', 'connection_log_ids')
    def _compute_counts(self):
        Cmd = self.env['iot.command.queue']
        for box in self:
            box.device_count = len(box.device_ids)
            box.log_count = len(box.connection_log_ids)
            box.command_count = Cmd.search_count(
                [('iot_box_id', '=', box.id)])

    def _compute_associated_pos_config_ids(self):
        """Best-effort: list pos.config records that pin a device on this box.
        Returns empty when point_of_sale isn't installed."""
        PosConfig = self.env.get('pos.config')
        if PosConfig is None:
            for box in self:
                box.associated_pos_config_ids = False
            return
        # Read every iot.device on each box, then find pos.config rows
        # whose iot_*_id fields reference any of those devices.
        for box in self:
            device_ids = box.device_ids.ids
            if not device_ids:
                box.associated_pos_config_ids = False
                continue
            domain = [
                '|', '|', '|',
                ('iot_device_ids', 'in', device_ids),
                ('iot_printer_id', 'in', device_ids),
                ('iot_scale_id', 'in', device_ids),
                ('iot_scanner_id', 'in', device_ids),
            ]
            try:
                box.associated_pos_config_ids = PosConfig.sudo().search(domain)
            except Exception:
                # filamind_pos_iot not installed: those fields don't exist yet
                box.associated_pos_config_ids = False

    # ── ORM ──────────────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'iot.box') or _('New Box')
            if not vals.get('token'):
                vals['token'] = uuid.uuid4().hex
        return super().create(vals_list)

    # ── Actions ──────────────────────────────────────────────────────────
    def action_generate_pairing_code(self):
        """Create an 8-char pairing code valid for the configured TTL
        (filamind_iot.pairing_ttl, default 15 minutes)."""
        self.ensure_one()
        ttl_minutes = int(self.env['ir.config_parameter'].sudo().get_param(
            'filamind_iot.pairing_ttl', 15) or 15)
        code = uuid.uuid4().hex[:8].upper()
        self.write({
            'pairing_code': code,
            'pairing_expiry': fields.Datetime.now() + timedelta(minutes=ttl_minutes),
            'state': 'pairing',
        })
        self.message_post(
            body=_('Pairing code generated: <b>%(code)s</b> (valid %(ttl)s minutes).',
                   code=code, ttl=ttl_minutes),
        )
        return {
            'type': 'ir.actions.act_window',
            'name': _('Pair IoT Box'),
            'res_model': 'iot.pairing.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_iot_box_id': self.id,
                'default_pairing_code': code,
            },
        }

    def action_mark_connected(self):
        self.ensure_one()
        self.write({
            'state': 'connected',
            'last_heartbeat': fields.Datetime.now(),
            'pairing_code': False,
            'pairing_expiry': False,
        })
        self.message_post(body=_('Box marked as connected.'))

    def action_disconnect(self):
        for box in self:
            box.state = 'disconnected'
            box.message_post(body=_('Box manually disconnected.'))

    def action_block(self):
        for box in self:
            box.state = 'blocked'
            box.message_post(body=_('Box has been blocked. It cannot reconnect.'))

    def action_unblock(self):
        for box in self:
            box.state = 'disconnected'
            box.message_post(body=_('Box unblocked — it may reconnect.'))

    def action_reset_token(self):
        self.ensure_one()
        self.sudo().token = uuid.uuid4().hex
        self.message_post(body=_('Authentication token regenerated.'))

    def action_view_devices(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Devices'),
            'res_model': 'iot.device',
            'view_mode': 'list,form,kanban',
            'domain': [('iot_box_id', '=', self.id)],
            'context': {'default_iot_box_id': self.id},
        }

    def action_view_logs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Activity Log'),
            'res_model': 'iot.connection.log',
            'view_mode': 'list,form',
            'domain': [('iot_box_id', '=', self.id)],
            'context': {'default_iot_box_id': self.id},
        }

    def action_view_commands(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Commands'),
            'res_model': 'iot.command.queue',
            'view_mode': 'list,form',
            'domain': [('iot_box_id', '=', self.id)],
            'context': {'default_iot_box_id': self.id},
        }

    # ── WebSocket / Bus ──────────────────────────────────────────────────
    def _ensure_ws_channel(self):
        """Allocate a WebSocket channel name on first /iot/setup call."""
        self.ensure_one()
        if not self.ws_channel:
            # Token-derived channel: unguessable, ties subscriptions to the box.
            self.sudo().ws_channel = 'iot_%s' % self.sudo().token
        return self.ws_channel

    def send_bus_message(self, method='iot_action', payload=None,
                         device=None, timeout=15):
        """Push a command to this box via bus.bus and create a queue entry.

        :param method: The 'type' field in the bus envelope. Mapped to
                       message_type by the box's communication.handle_message.
                       Use 'iot_action' for device commands.
        :param payload: Extra dict merged into the message payload.
        :param device: Optional iot.device for tracking on the queue.
        :param timeout: Seconds before the cron marks this command as
                        timed out.
        :return: The created iot.command.queue record.
        """
        self.ensure_one()
        channel = self.ws_channel
        if not channel:
            raise UserError(_(
                "This box hasn't subscribed to a WebSocket channel yet — "
                "wait for it to call /iot/setup or restart the box's Odoo "
                "service."))
        if self.state != 'connected':
            raise UserError(_(
                "Box %s is not connected (state=%s).") % (self.name, self.state))

        Queue = self.env['iot.command.queue'].sudo()
        session_id = Queue._new_session_id()

        message = {
            'iot_identifier': self.identifier,
            'session_id': session_id,
            **(payload or {}),
        }
        if device:
            message['device_identifier'] = device.identifier

        queue = Queue.create({
            'name': session_id,
            'iot_box_id': self.id,
            'device_id': device.id if device else False,
            'method': method,
            'request_payload': json.dumps(message, default=str)[:32000],
            'timeout_seconds': timeout,
            'state': 'sent',
            'sent_at': fields.Datetime.now(),
        })

        # bus.bus dispatch happens after the current transaction commits;
        # the queue row will be visible to /iot/box/send_websocket by then.
        self.env['bus.bus']._sendone(channel, method, message)
        return queue

    def action_test_connection(self):
        """Round-trip a 'test_connection' message via the bus."""
        self.ensure_one()
        queue = self.send_bus_message(method='test_connection', timeout=10)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Test sent'),
                'message': _(
                    'Test message dispatched to %(box)s. Watch the queue '
                    'entry %(qid)s for the result.') % {
                        'box': self.name, 'qid': queue.name[:12] + '…'},
                'type': 'info',
                'sticky': False,
            },
        }

    def action_open_homepage(self):
        self.ensure_one()
        if not self.ip_url:
            raise UserError(_('Set the LAN IP of this box first.'))
        return {
            'type': 'ir.actions.act_url',
            'url': self.ip_url,
            'target': 'new',
        }

    # ── Heartbeat / API ──────────────────────────────────────────────────
    def _record_heartbeat(self, payload=None):
        """Called by the HTTP controller when the box pings in."""
        self.ensure_one()
        self.sudo().write({
            'last_heartbeat': fields.Datetime.now(),
            'state': 'connected' if self.state != 'blocked' else 'blocked',
        })
        if payload and isinstance(payload, dict):
            self.sudo().write({
                k: v for k, v in payload.items()
                if k in ('version', 'wifi_ssid', 'hostname', 'ip_address', 'mac_address')
                and v is not None
            })

    @api.model
    def _cron_check_stale_boxes(self):
        """Mark boxes as disconnected when their heartbeat is overdue."""
        now = fields.Datetime.now()
        boxes = self.search([('state', '=', 'connected')])
        for box in boxes:
            if not box.last_heartbeat:
                continue
            if (now - box.last_heartbeat) > timedelta(
                    seconds=(box.heartbeat_interval or 60) * 3):
                box.state = 'disconnected'
                box.message_post(
                    body=_('No heartbeat received — marked as disconnected.'))
        return True
