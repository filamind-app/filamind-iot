"""Auto-print attendee badge on registration confirmation; expose a
manual reprint action button for staff."""
from odoo import _, fields, models
from odoo.exceptions import UserError


class EventRegistration(models.Model):
    _inherit = 'event.registration'

    iot_badge_print_command_id = fields.Many2one(
        'iot.command.queue', string='Last Badge Print',
        readonly=True, ondelete='set null',
    )
    iot_badge_printed_date = fields.Datetime(
        string='Badge Printed At', readonly=True,
    )

    # ── Hooks ──────────────────────────────────────────────────────────
    def write(self, vals):
        result = super().write(vals)
        if vals.get('state') == 'open':
            for r in self:
                if (r.event_id.auto_print_badges
                        and r.event_id.iot_badge_printer_id
                        and not r.iot_badge_printed_date):
                    try:
                        r.action_iot_print_badge()
                    except Exception:
                        # Don't break confirmation if printing fails
                        # — admin can reprint manually.
                        pass
        return result

    # ── Actions ────────────────────────────────────────────────────────
    def action_iot_print_badge(self):
        self.ensure_one()
        printer = self.event_id.iot_badge_printer_id
        if not printer:
            raise UserError(_("This event has no IoT badge printer."))
        body = self._render_iot_badge()
        cmd = printer.iot_box_id.send_bus_message(
            method='iot_action',
            payload={
                'action': 'print',
                'document': body,
                'document_format': 'raw',
                'print_id': 'badge-%s' % self.id,
            },
            device=printer,
            timeout=15,
        )
        self.write({
            'iot_badge_print_command_id': cmd.id,
            'iot_badge_printed_date': fields.Datetime.now(),
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'iot.command.queue',
            'res_id': cmd.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_iot_check_in(self):
        """Manual check-in (button on the registration form). The
        scanner-driven path is wired up by the iot.trigger system if the
        site uses it."""
        self.ensure_one()
        if hasattr(self, 'action_set_done'):
            self.action_set_done()
        else:
            self.write({'state': 'done'})
        return True

    # ── Badge rendering ────────────────────────────────────────────────
    def _render_iot_badge(self):
        """Plain-text badge body. Override for ESC/POS, ZPL, or branded
        layouts. Variables available: self.name, partner_id, event_id."""
        return (
            "================================\n"
            "      %s\n"
            "================================\n"
            "  Attendee: %s\n"
            "  Email:    %s\n"
            "  Date:     %s\n"
            "  Ref:      %s\n"
            "\n"
            "  >>> Show at the door <<<\n\n\n"
        ) % ((self.event_id.name or '')[:30],
             (self.name or self.partner_id.name or '')[:30],
             (self.email or '')[:30],
             self.event_id.date_begin or '',
             self.id)
