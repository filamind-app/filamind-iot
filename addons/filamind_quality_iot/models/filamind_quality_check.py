"""One captured measurement / pass-fail / picture against a quality
point."""
import json

from odoo import _, api, fields, models


class FilamindQualityCheck(models.Model):
    _name = 'filamind.quality.check'
    _description = 'Quality Check'
    _order = 'create_date desc, id desc'
    _inherit = ['mail.thread']

    name = fields.Char(string='Reference', readonly=True, copy=False,
                       default=lambda self: _('New'))
    point_id = fields.Many2one(
        'filamind.quality.point', string='Quality Point', required=True,
        ondelete='cascade', index=True, tracking=True,
    )
    product_id = fields.Many2one(
        'product.product', string='Product', tracking=True,
    )
    user_id = fields.Many2one(
        'res.users', string='Operator',
        default=lambda self: self.env.user, tracking=True,
    )

    # Result -----------------------------------------------------------
    state = fields.Selection([
        ('open', 'To Test'),
        ('pass', 'Passed'),
        ('fail', 'Failed'),
    ], default='open', required=True, tracking=True)
    measure_value = fields.Float(string='Measured Value', tracking=True)
    measure_unit = fields.Char(
        related='point_id.norm_unit', store=False, readonly=True,
    )
    picture = fields.Binary(string='Picture', attachment=True)
    note = fields.Html(string='Note', sanitize=True)

    # IoT trace -------------------------------------------------------
    iot_box_id = fields.Many2one(
        'iot.box', string='IoT Box',
        compute='_compute_iot_box_id', store=True, readonly=True,
    )
    iot_command_id = fields.Many2one(
        'iot.command.queue', string='Source IoT Command',
        readonly=True, ondelete='set null',
        help='The command queue row whose response produced this '
             'measurement (when filled by an IoT device).',
    )

    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company, required=True,
    )

    @api.depends('point_id.iot_device_id')
    def _compute_iot_box_id(self):
        for r in self:
            r.iot_box_id = r.point_id.iot_device_id.iot_box_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code(
                        'filamind.quality.check') or _('New Check'))
        return super().create(vals_list)

    # ── IoT integration ──────────────────────────────────────────────
    def _iot_request_measurement(self):
        """Dispatch an iot_action to the point's device. The result lands
        on iot.command.queue.response_payload; a small post-write hook
        below copies the value back into measure_value (or picture).
        """
        self.ensure_one()
        device = self.point_id.iot_device_id
        if not device:
            return False
        action = ('picture' if self.point_id.test_type == 'picture'
                   else 'read_once')
        cmd = device.iot_box_id.send_bus_message(
            method='iot_action',
            payload={'action': action, 'check_id': self.id},
            device=device,
            timeout=15,
        )
        self.iot_command_id = cmd.id
        return cmd

    @api.model
    def _cron_apply_iot_results(self):
        """Cron: walk completed iot.command.queue rows that we created
        and copy their values into the matching check."""
        Cmd = self.env['iot.command.queue']
        completed = Cmd.search([
            ('state', '=', 'completed'),
            ('id', 'in', self.search([
                ('iot_command_id', '!=', False),
                ('measure_value', '=', 0),
            ]).mapped('iot_command_id.id')),
        ])
        for cmd in completed:
            check = self.search(
                [('iot_command_id', '=', cmd.id)], limit=1)
            if not check:
                continue
            try:
                payload = json.loads(cmd.response_payload or '{}')
            except ValueError:
                continue
            value = payload.get('value') or payload.get('weight') or 0
            picture = payload.get('image') or payload.get('picture')
            vals = {}
            if value:
                vals['measure_value'] = float(value)
                pt = check.point_id
                if pt.test_type == 'measure' and pt.tolerance_min < pt.tolerance_max:
                    vals['state'] = ('pass' if pt.tolerance_min <= float(value)
                                                <= pt.tolerance_max else 'fail')
            if picture:
                vals['picture'] = picture
            if vals:
                check.write(vals)
        return True

    # Manual pass / fail buttons --------------------------------------
    def action_pass(self):
        self.write({'state': 'pass'})

    def action_fail(self):
        self.write({'state': 'fail'})

    def action_create_alert(self):
        self.ensure_one()
        alert = self.env['filamind.quality.alert'].create({
            'name': _('Issue from check %s') % self.name,
            'product_id': self.product_id.id or False,
            'check_id': self.id,
            'severity': 'medium',
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'filamind.quality.alert',
            'res_id': alert.id,
            'view_mode': 'form',
            'target': 'current',
        }
