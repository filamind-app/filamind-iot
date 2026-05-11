{
    'name': 'Filamind Event IoT',
    'version': '19.0.1.0.0',
    'category': 'Marketing',
    'summary': 'Event registration with IoT badge printing and barcode '
               'check-in. Community alternative to Enterprise event_iot + '
               'event_sale_iot + pos_event_iot.',
    'description': """
Filamind Event IoT
==================
Bridges the LGPL `event` module with the filamind IoT gateway.
Community alternative to Enterprise `event_iot` + `event_sale_iot` +
`pos_event_iot` (all OEEL-1).

What it adds
------------
* ``event.event.iot_badge_printer_id``  printer that issues attendee
                                          badges.
* ``event.event.iot_scanner_id``        scanner that checks attendees
                                          in by reading their badge
                                          barcode.
* ``event.registration.action_iot_print_badge``  manual reprint button.
* Auto-print badge whenever a registration moves to ``open``
  (confirmed). Disable per event with ``auto_print_badges = False``.
* Optional POS integration (when ``pos_event_iot`` data is needed):
  prints a badge from the POS receipt printer when an event ticket
  is purchased at the till.

Badge template
--------------
Default plain-text layout (name + event + date + barcode placeholder).
Override ``event.registration._render_iot_badge`` for ESC/POS,
ZPL, or branded layouts.
""",
    'author': 'filamind',
    'website': 'https://github.com/filamind-app/filamind-iot',
    'depends': ['filamind_iot', 'event'],
    'data': [
        'views/event_event_views.xml',
        'views/event_registration_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
