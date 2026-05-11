"""Quality control point definition.

A point describes WHAT to check, WHERE (which product / operation),
and HOW (test type + optional IoT device that pulls the measurement
automatically). One point can produce many `filamind.quality.check`
records over time.

Mirror of Enterprise `quality.point`. We deliberately reimplement
rather than depend on Enterprise `quality_control` so the addon works
on a vanilla Community Odoo.
"""
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class FilamindQualityPoint(models.Model):
    _name = 'filamind.quality.point'
    _description = 'Quality Point'
    _order = 'sequence, name'
    _inherit = ['mail.thread']

    name = fields.Char(string='Name', required=True, tracking=True,
                       default=lambda self: _('New'))
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    # Scope ------------------------------------------------------------
    product_id = fields.Many2one(
        'product.product', string='Product',
        help='If set, the point applies only to this product.',
    )
    product_template_id = fields.Many2one(
        'product.template', string='Product Template',
        help='If set (and no product_id), applies to all variants of '
             'this template.',
    )
    workcenter_id = fields.Many2one(
        'mrp.workcenter', string='Work Centre',
        help='Optional: tie this point to a specific MRP work centre.',
    )

    measure_on = fields.Selection([
        ('product', 'Per Product'),
        ('operation', 'Per Operation'),
        ('lot', 'Per Lot'),
    ], default='operation', required=True)

    test_type = fields.Selection([
        ('passfail', 'Pass / Fail'),
        ('measure', 'Take Measurement'),
        ('picture', 'Take Picture'),
    ], default='passfail', required=True)

    # Measurement bounds (test_type='measure') -------------------------
    norm_unit = fields.Char(
        string='Unit', help='e.g. "mm", "g", "°C". Free-form.',
    )
    target_value = fields.Float(string='Target Value')
    tolerance_min = fields.Float(string='Tolerance Min')
    tolerance_max = fields.Float(string='Tolerance Max')

    # IoT device ------------------------------------------------------
    iot_device_id = fields.Many2one(
        'iot.device', string='IoT Device',
        domain="[('type_id.code', 'in', ('measuring_tool', 'scale', 'camera')),"
               " ('active', '=', True)]",
        help='When set, taking a check auto-pulls the value from this '
             'device via the iot.command.queue.',
    )

    note = fields.Html(string='Note', sanitize=True)

    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company, required=True,
    )

    check_count = fields.Integer(
        string='Checks', compute='_compute_check_count',
    )

    @api.depends()
    def _compute_check_count(self):
        Check = self.env['filamind.quality.check']
        for r in self:
            r.check_count = Check.search_count(
                [('point_id', '=', r.id)])

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code(
                        'filamind.quality.point') or _('New Point'))
        return super().create(vals_list)

    # Action: trigger a check now -------------------------------------
    def action_create_check(self):
        self.ensure_one()
        check = self.env['filamind.quality.check'].create({
            'point_id': self.id,
            'product_id': self.product_id.id or False,
        })
        # If point has an IoT device, dispatch a measurement command
        if self.iot_device_id and self.test_type in ('measure', 'picture'):
            try:
                check._iot_request_measurement()
            except Exception as exc:
                raise UserError(_(
                    "Could not contact the IoT device: %s") % exc) from exc
        return {
            'type': 'ir.actions.act_window',
            'name': _('Quality Check'),
            'res_model': 'filamind.quality.check',
            'res_id': check.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_checks(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Checks for %s') % self.name,
            'res_model': 'filamind.quality.check',
            'view_mode': 'list,form',
            'domain': [('point_id', '=', self.id)],
            'context': {'default_point_id': self.id},
        }
