"""Wizard: create a tenant on the proxy via REST."""
from odoo import _, fields, models


class TenantCreateWizard(models.TransientModel):
    _name = 'iot.proxy.tenant.create.wizard'
    _description = 'Create proxy tenant'

    name = fields.Char(required=True)
    plan = fields.Char(default='free')
    box_quota = fields.Integer(default=5)
    contact_email = fields.Char()
    license_key = fields.Char()
    license_expires = fields.Datetime()

    def action_create(self):
        self.ensure_one()
        proxy = self.env['iot.proxy.config'].get_active()
        body = {
            'name': self.name,
            'plan': self.plan or 'free',
            'box_quota': self.box_quota or 5,
            'contact_email': self.contact_email or None,
            'license_key': self.license_key or None,
            'license_expires': (
                self.license_expires.isoformat()
                if self.license_expires else None),
        }
        proxy._request('POST', '/admin/tenants', json=body)
        proxy.action_refresh_all()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Tenant created'),
                'message': _('Tenant "%s" was created on the proxy.', self.name),
                'type': 'success',
            },
        }
