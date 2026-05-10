from odoo import api, fields, models, _


class IotDevice(models.Model):
    """A physical device attached to an IoT Box — printer, scanner, scale,
    camera, payment terminal, fiscal data module, display, etc."""
    _name = 'iot.device'
    _description = 'IoT Device'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'iot_box_id, sequence, name'
    _check_company_auto = True

    name = fields.Char(
        string='Device Name', required=True, tracking=True,
        help='Human-readable name, e.g. "Epson TM-T20 (Cashier 1)".',
    )
    identifier = fields.Char(
        string='Identifier', index=True, copy=False,
        help='Device identifier reported by the IoT Box '
             '(USB ID, MAC, or serial).',
    )
    iot_box_id = fields.Many2one(
        'iot.box', string='IoT Box', required=True,
        ondelete='cascade', index=True, tracking=True,
        check_company=True,
    )
    company_id = fields.Many2one(
        related='iot_box_id.company_id', store=True, readonly=True,
        index=True,
    )
    type_id = fields.Many2one(
        'iot.device.type', string='Type', required=True, tracking=True,
        ondelete='restrict',
    )
    type_code = fields.Char(related='type_id.code', store=True, readonly=True)
    type_icon = fields.Char(related='type_id.icon', readonly=True)

    connection = fields.Selection([
        ('usb', 'USB'),
        ('serial', 'Serial'),
        ('bluetooth', 'Bluetooth'),
        ('network', 'Network'),
        ('hdmi', 'HDMI / Display'),
        ('gpio', 'GPIO'),
    ], string='Connection', default='usb', tracking=True)

    manufacturer = fields.Char(string='Manufacturer')
    model_name = fields.Char(string='Model')
    subtype = fields.Char(
        string='Subtype',
        help='Free-form qualifier, e.g. "receipt", "label", "shipping".',
    )

    state = fields.Selection([
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('error', 'Error'),
        ('disabled', 'Disabled'),
    ], string='Status', default='offline', tracking=True, readonly=True)

    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Color Index', default=0)

    last_seen = fields.Datetime(string='Last Seen', readonly=True)

    # ── Usage hints ──────────────────────────────────────────────────────
    use_in_pos = fields.Boolean(
        string='Available in POS',
        help='Make this device selectable from Point of Sale configs.',
    )
    use_in_inventory = fields.Boolean(string='Available in Inventory')
    use_in_manufacturing = fields.Boolean(string='Available in Manufacturing')

    # ── Type-specific settings (printers mostly) ─────────────────────────
    paper_width = fields.Integer(
        string='Paper Width (mm)',
        help='Only for receipt / label printers.',
    )
    report_id = fields.Many2one(
        'ir.actions.report', string='Default Report',
        help='Default QWeb report for this printer.',
    )

    # ── Relations ────────────────────────────────────────────────────────
    connection_log_ids = fields.One2many(
        'iot.connection.log', 'device_id', string='Activity Log')
    log_count = fields.Integer(string='Logs', compute='_compute_log_count')

    notes = fields.Html(string='Notes')

    @api.depends('connection_log_ids')
    def _compute_log_count(self):
        for dev in self:
            dev.log_count = len(dev.connection_log_ids)

    # ── Actions ──────────────────────────────────────────────────────────
    def action_enable(self):
        for dev in self:
            dev.write({'state': 'offline', 'active': True})
            dev.message_post(body=_('Device enabled.'))

    def action_disable(self):
        for dev in self:
            dev.write({'state': 'disabled'})
            dev.message_post(body=_('Device disabled.'))

    def action_test(self):
        """Create a log entry simulating a test ping. A real box would POST
        back its response via the HTTP controller."""
        self.ensure_one()
        self.env['iot.connection.log'].create({
            'iot_box_id': self.iot_box_id.id,
            'device_id': self.id,
            'event': 'test',
            'message': _('Test requested by %s') % self.env.user.name,
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Test queued'),
                'message': _('A test command was queued for %s.') % self.name,
                'type': 'success',
                'sticky': False,
            },
        }

    def action_view_logs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Activity Log'),
            'res_model': 'iot.connection.log',
            'view_mode': 'list,form',
            'domain': [('device_id', '=', self.id)],
            'context': {
                'default_device_id': self.id,
                'default_iot_box_id': self.iot_box_id.id,
            },
        }

    def _record_state(self, new_state, message=None):
        """Called from the HTTP controller when the box reports device status."""
        self.ensure_one()
        vals = {'state': new_state, 'last_seen': fields.Datetime.now()}
        self.sudo().write(vals)
        self.env['iot.connection.log'].sudo().create({
            'iot_box_id': self.iot_box_id.id,
            'device_id': self.id,
            'event': new_state,
            'message': message or _('State changed to %s') % new_state,
        })
