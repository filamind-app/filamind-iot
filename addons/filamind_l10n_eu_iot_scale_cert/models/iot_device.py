"""LNE / EU MID certification metadata on iot.device. Only meaningful
on devices whose type is `scale`."""
from datetime import timedelta

from odoo import _, api, fields, models


NOTIFIED_BODIES = [
    ('lne', 'LNE (France)'),
    ('ptb', 'PTB (Germany)'),
    ('accreditar', 'AccreditAR (Italy)'),
    ('inmetro_eu', 'INMETRO-EU (Portugal)'),
    ('npl', 'NPL (UK — pre-Brexit certs only)'),
    ('aenor', 'AENOR (Spain)'),
    ('cmi', 'ČMI (Czech Republic)'),
    ('other', 'Other Notified Body'),
]


class IotDevice(models.Model):
    _inherit = 'iot.device'

    lne_certificate_number = fields.Char(
        string='Certificate Number',
        help='EU Module B type-examination certificate number, e.g. '
             '17-FR-0123-NB-0071. Required for legal-for-trade use.',
    )
    lne_notified_body = fields.Selection(
        NOTIFIED_BODIES, string='Notified Body',
        help='The EU notified body that issued the certificate.',
    )
    lne_certificate_expiry = fields.Date(
        string='Certificate Expiry',
        help='Date after which the certificate is no longer valid. '
             'A daily cron warns the responsible user 30 days before.',
    )
    lne_max_weight_g = fields.Float(
        string='Max Weight (g)',
        help='Capacity (Max) from the M-mark plate on the device.',
    )
    lne_min_weight_g = fields.Float(
        string='Min Weight (g)',
        help='Minimum legal-for-trade weight (typically 20 e).',
    )
    lne_division_g = fields.Float(
        string='Verification Scale Interval e (g)',
        help='Smallest division of mass certified for legal-for-trade '
             'use. Weights below 20 e MUST NOT be used for pricing.',
    )
    lne_responsible_user_id = fields.Many2one(
        'res.users', string='Metrology Responsible',
        help='Receives the expiry warnings.',
    )
    lne_certificate_status = fields.Selection(
        [('ok', 'Valid'),
         ('expiring', 'Expiring Soon'),
         ('expired', 'Expired'),
         ('not_certified', 'Not Certified')],
        string='Certification Status', compute='_compute_lne_status',
        store=True, default='not_certified',
    )

    @api.depends('lne_certificate_number', 'lne_certificate_expiry')
    def _compute_lne_status(self):
        today = fields.Date.context_today(self)
        for d in self:
            if not d.lne_certificate_number or not d.lne_certificate_expiry:
                d.lne_certificate_status = 'not_certified'
            elif d.lne_certificate_expiry < today:
                d.lne_certificate_status = 'expired'
            elif d.lne_certificate_expiry <= today + timedelta(days=30):
                d.lne_certificate_status = 'expiring'
            else:
                d.lne_certificate_status = 'ok'

    @api.model
    def _cron_check_lne_expiry(self):
        """Notify the metrology responsible 30 days before expiry."""
        today = fields.Date.context_today(self)
        soon = today + timedelta(days=30)
        devices = self.search([
            ('type_id.code', '=', 'scale'),
            ('lne_certificate_expiry', '<=', soon),
            ('lne_certificate_expiry', '>=', today),
            ('lne_responsible_user_id', '!=', False),
        ])
        for d in devices:
            d.message_post(
                body=_(
                    "Certificate %s expires on %s. Renew with the "
                    "notified body before that date or stop using "
                    "this scale for legal-for-trade weighing."
                ) % (d.lne_certificate_number, d.lne_certificate_expiry),
                partner_ids=d.lne_responsible_user_id.partner_id.ids,
            )
