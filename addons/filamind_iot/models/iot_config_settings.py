from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    iot_pairing_code_ttl = fields.Integer(
        string='Pairing Code Validity (minutes)',
        config_parameter='filamind_iot.pairing_ttl',
        default=15,
    )
    iot_heartbeat_interval = fields.Integer(
        string='Default Heartbeat Interval (seconds)',
        config_parameter='filamind_iot.heartbeat_interval',
        default=60,
    )
    iot_require_tls = fields.Boolean(
        string='Require HTTPS for IoT Box Connections',
        config_parameter='filamind_iot.require_tls',
        default=True,
    )
    iot_auto_discover = fields.Boolean(
        string='Auto-register Newly Reported Devices',
        config_parameter='filamind_iot.auto_discover',
        default=True,
    )
    iot_log_retention_days = fields.Integer(
        string='Log Retention (days)',
        config_parameter='filamind_iot.log_retention_days',
        default=90,
        help='Connection log entries older than this are deleted by the daily cron.',
    )
    iot_allow_remote_control = fields.Boolean(
        string='Allow Remote Device Control',
        config_parameter='filamind_iot.allow_remote_control',
        default=True,
        help='Let Odoo send commands (print, open drawer, weigh) to devices.',
    )
    iot_notify_on_disconnect = fields.Boolean(
        string='Notify Responsible on Disconnect',
        config_parameter='filamind_iot.notify_on_disconnect',
        default=True,
    )
