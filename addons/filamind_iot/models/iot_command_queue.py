"""Outgoing IoT commands and their round-trip results.

Each command sent to a box via bus.bus is tagged with a unique
session_id. When the box reports the result back via /iot/box/send_websocket
(or /filamind_iot/command_result), we look up the matching queue entry
and mark it complete.
"""
import json
import secrets

from odoo import api, fields, models


class IotCommandQueue(models.Model):
    _name = 'iot.command.queue'
    _description = 'IoT Command Queue'
    _order = 'create_date desc, id desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Session ID', required=True, copy=False, index=True,
        help='Unique correlation token sent in the bus message and echoed '
             'back by the box.',
    )
    iot_box_id = fields.Many2one(
        'iot.box', string='IoT Box', required=True,
        ondelete='cascade', index=True, check_company=True,
    )
    device_id = fields.Many2one(
        'iot.device', string='Device',
        ondelete='set null', index=True, check_company=True,
    )
    method = fields.Char(
        string='Bus Message Type', required=True, default='iot_action',
        help='Value of "type" in the bus message envelope. The IoT Box '
             'dispatches based on this value (iot_action, test_protocol, '
             'restart_odoo, server_clear, server_update, remote_debug, '
             'reset_password, test_connection).',
    )
    request_payload = fields.Text(
        string='Request', readonly=True,
        help='JSON payload sent to the box.',
    )
    response_payload = fields.Text(
        string='Response', readonly=True,
        help='JSON the box returned via send_websocket.',
    )
    state = fields.Selection([
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('timeout', 'Timed Out'),
    ], default='pending', required=True, index=True, tracking=False)
    error = fields.Char(string='Error')
    sent_at = fields.Datetime(string='Sent At', readonly=True)
    completed_at = fields.Datetime(string='Completed At', readonly=True)
    timeout_seconds = fields.Integer(
        string='Timeout (s)', default=15,
        help='Reap as timeout if no response after this many seconds.',
    )

    company_id = fields.Many2one(
        related='iot_box_id.company_id', store=True, readonly=True, index=True,
    )

    @api.model
    def _new_session_id(self):
        """Generate a 32-char hex correlation id."""
        return secrets.token_hex(16)

    def record_response(self, payload):
        """Called by the controller when the box POSTs a result back.

        :param payload: dict already parsed from the box's request body.
        """
        self.ensure_one()
        if self.state in ('completed', 'failed', 'timeout'):
            return  # idempotent
        is_error = (payload.get('status') in ('disconnected', 'error', 'failure')
                    or 'error' in payload)
        self.write({
            'state': 'failed' if is_error else 'completed',
            'response_payload': json.dumps(payload, default=str)[:32000],
            'completed_at': fields.Datetime.now(),
            'error': payload.get('error') or (
                payload.get('status') if is_error else False),
        })

    @api.model
    def _cron_reap_stale(self):
        """Mark old in-flight commands as timed out."""
        from datetime import timedelta
        now = fields.Datetime.now()
        stale = self.search([
            ('state', 'in', ('pending', 'sent')),
            ('sent_at', '!=', False),
        ])
        for cmd in stale:
            deadline = cmd.sent_at + timedelta(seconds=cmd.timeout_seconds or 15)
            if deadline < now:
                cmd.write({'state': 'timeout', 'completed_at': now,
                           'error': 'No response received before deadline.'})
        return True
