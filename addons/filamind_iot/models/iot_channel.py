"""Singleton model exposing the bus.bus channel name used by IoT boxes.

Upstream Odoo Enterprise uses a single shared channel per database
(stored in ir.config_parameter['iot.ws_channel']) — every IoT box
subscribes to it, every server-side command is broadcast on it, and
each box filters by `iot_identifier` in the message payload.

filamind-iot keeps its own per-box channels (`iot_<token>`) for
isolation and lower per-box wake-ups, BUT we also expose the upstream
shared-channel API here so that:

  * an unmodified upstream IoT Box image can talk to filamind-iot
    without any patches;
  * upstream extension modules (pos_iot, mrp_iot, etc.) that call
    `self.env['iot.channel'].get_iot_channel()` keep working.
"""
import secrets

from odoo import api, models


CONFIG_KEY = 'iot.ws_channel'


class IotChannel(models.Model):
    _name = 'iot.channel'
    _description = 'The Websocket IoT Channel'

    @api.model
    def get_iot_channel(self) -> str:
        """Return the canonical bus.bus channel name for IoT boxes.

        Generated lazily on first call and persisted in
        ir.config_parameter so it survives across all sessions.
        """
        ICP = self.env['ir.config_parameter'].sudo()
        channel = ICP.get_param(CONFIG_KEY)
        if not channel:
            channel = 'iot_channel-%s' % secrets.token_hex(16)
            ICP.set_param(CONFIG_KEY, channel)
        return channel
