"""Wizard: claim a pairing code on behalf of a target Odoo DB.

Usually this is done by the customer's Odoo over its own pairing UI;
the operator wizard exists for manual pairing or rescue scenarios.
"""
from odoo import _, fields, models


class FinalizePairingWizard(models.TransientModel):
    _name = 'iot.proxy.finalize.wizard'
    _description = 'Finalize a proxy pairing code'

    code = fields.Char(required=True, help='8-char pairing code shown by the box.')
    db_uuid = fields.Char(required=True, help='Target Odoo db_uuid.')
    server_url = fields.Char(
        required=True, help='Customer Odoo URL the box should phone to.')

    def action_finalize(self):
        self.ensure_one()
        proxy = self.env['iot.proxy.config'].get_active()
        proxy._request(
            'POST', '/iot/finalize',
            json={
                'code': self.code.strip().upper(),
                'db_uuid': self.db_uuid.strip(),
                'server_url': self.server_url.strip(),
            },
        )
        proxy.action_refresh_all()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Pairing finalized'),
                'message': _(
                    'Code %s claimed for %s.', self.code, self.server_url),
                'type': 'success',
            },
        }
