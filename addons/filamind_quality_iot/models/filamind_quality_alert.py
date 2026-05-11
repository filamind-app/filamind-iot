"""Open quality issue / non-conformance ticket."""
from odoo import fields, models


class FilamindQualityAlert(models.Model):
    _name = 'filamind.quality.alert'
    _description = 'Quality Alert'
    _order = 'create_date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Title', required=True, tracking=True)
    description = fields.Html(string='Description', sanitize=True)
    severity = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], default='medium', required=True, tracking=True)
    state = fields.Selection([
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('cancelled', 'Cancelled'),
    ], default='open', required=True, tracking=True)

    product_id = fields.Many2one(
        'product.product', string='Product', tracking=True,
    )
    check_id = fields.Many2one(
        'filamind.quality.check', string='Triggering Check',
        ondelete='set null',
    )
    user_id = fields.Many2one(
        'res.users', string='Assigned To',
        default=lambda self: self.env.user, tracking=True,
    )

    action_corrective = fields.Html(string='Corrective Action', sanitize=True)
    action_preventive = fields.Html(string='Preventive Action', sanitize=True)
    date_resolved = fields.Datetime(string='Resolved On', readonly=True)

    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company, required=True,
    )

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_resolve(self):
        self.write({'state': 'resolved',
                    'date_resolved': fields.Datetime.now()})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reopen(self):
        self.write({'state': 'open', 'date_resolved': False})
