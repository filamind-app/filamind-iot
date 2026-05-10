from datetime import timedelta
from odoo import api, fields, models


class IotConnectionLog(models.Model):
    """Audit trail of IoT events: box heartbeats, device discovery, device
    state changes, test commands, errors."""
    _name = 'iot.connection.log'
    _description = 'IoT Connection Log'
    _order = 'create_date desc, id desc'
    _rec_name = 'event'

    iot_box_id = fields.Many2one(
        'iot.box', string='IoT Box', required=True,
        ondelete='cascade', index=True,
    )
    device_id = fields.Many2one(
        'iot.device', string='Device',
        ondelete='cascade', index=True,
    )
    event = fields.Selection([
        ('heartbeat', 'Heartbeat'),
        ('pairing', 'Pairing'),
        ('paired', 'Paired'),
        ('connected', 'Connected'),
        ('disconnected', 'Disconnected'),
        ('discovered', 'Device Discovered'),
        ('online', 'Device Online'),
        ('offline', 'Device Offline'),
        ('error', 'Error'),
        ('test', 'Test Command'),
        ('firmware', 'Firmware Update'),
        ('blocked', 'Blocked'),
    ], string='Event', required=True, default='heartbeat', index=True)

    message = fields.Char(string='Message')
    payload = fields.Text(
        string='Raw Payload',
        help='JSON payload sent by the IoT Box (truncated).',
    )
    ip_address = fields.Char(string='Source IP')
    severity = fields.Selection([
        ('info', 'Info'),
        ('warn', 'Warning'),
        ('error', 'Error'),
    ], default='info', string='Severity', index=True)

    company_id = fields.Many2one(
        related='iot_box_id.company_id', store=True, readonly=True)

    @api.model
    def _cron_purge_old_logs(self):
        """Delete log entries older than the retention window."""
        days = int(self.env['ir.config_parameter'].sudo().get_param(
            'filamind_iot.log_retention_days', 90))
        if days <= 0:
            return 0
        cutoff = fields.Datetime.now() - timedelta(days=days)
        old = self.sudo().search([('create_date', '<', cutoff)])
        count = len(old)
        old.unlink()
        return count
