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
        for box in self:
            box.device_count = len(box.device_ids)
            box.log_count = len(box.connection_log_ids)

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
