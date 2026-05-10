from odoo import api, fields, models, _
from odoo.exceptions import UserError


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
        """Round-trip a 'test_connection' message via bus.bus to verify the
        device's box is actually reachable end-to-end."""
        self.ensure_one()
        if self.iot_box_id.state != 'connected':
            raise UserError(_(
                "The box owning this device is not connected (state=%s). "
                "Pair or wake the box first.") % self.iot_box_id.state)
        queue = self.iot_box_id.send_bus_message(
            method='test_connection',
            payload={'device_identifier': self.identifier},
            device=self,
            timeout=10,
        )
        self.env['iot.connection.log'].create({
            'iot_box_id': self.iot_box_id.id,
            'device_id': self.id,
            'event': 'test',
            'message': _('Test command sent (session %s).') % queue.name[:12],
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Command'),
            'res_model': 'iot.command.queue',
            'res_id': queue.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_test_print(self):
        """Send a small test print job to a printer-type device.

        The exact payload is what upstream Odoo's iot_drivers ESC/POS
        printer driver consumes via its action() method. Verification with
        a real printer is part of Phase 2 (hardware-in-the-loop tests).
        """
        self.ensure_one()
        if self.type_id.code not in ('receipt_printer', 'label_printer'):
            raise UserError(_(
                "Test print is only available for receipt or label printers."))
        if self.iot_box_id.state != 'connected':
            raise UserError(_(
                "The box owning this printer is not connected."))
        body = (
            "*** filamind test print ***\n"
            "\n"
            "Box:    %s\n"
            "Device: %s\n"
            "Time:   %s\n"
            "\n"
            "If you can read this on a paper roll, the\n"
            "round-trip Odoo -> box -> printer works.\n"
        ) % (self.iot_box_id.name, self.name, fields.Datetime.now())
        queue = self.iot_box_id.send_bus_message(
            method='iot_action',
            payload={
                'document': body,
                'document_format': 'raw',
                'print_id': fields.Datetime.now().isoformat(),
            },
            device=self,
            timeout=15,
        )
        self.env['iot.connection.log'].create({
            'iot_box_id': self.iot_box_id.id,
            'device_id': self.id,
            'event': 'test',
            'message': _('Test print sent (session %s).') % queue.name[:12],
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Print Command'),
            'res_model': 'iot.command.queue',
            'res_id': queue.id,
            'view_mode': 'form',
            'target': 'new',
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
