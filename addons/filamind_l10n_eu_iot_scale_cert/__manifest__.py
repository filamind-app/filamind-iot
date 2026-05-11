{
    'name': 'Filamind EU Legal-for-Trade Scale Certification (LNE)',
    'version': '19.0.1.0.0',
    'category': 'Localization',
    'summary': 'EU MID + LNE certification metadata and weight-event '
               'logging for legal-for-trade IoT scales.',
    'description': """
Filamind EU Legal-for-Trade Scale Certification (LNE)
=====================================================
EU member states require scales used for direct-to-consumer
commerce ("legal-for-trade", "metrologically controlled", or
"non-automatic weighing instruments" / NAWI) to:

* Carry a Module B EU type-examination certificate (issued by a
  notified body — in France that's LNE, in Germany the PTB, in
  Italy AccreditAR, etc.).
* Display the M-mark + green CE sticker on the device housing.
* Log every weight-for-pricing event so an inspector can audit
  cashier behaviour for at least the period mandated locally
  (typically 1 year).

Community alternative to Enterprise `l10n_eu_iot_scale_cert` (OEEL-1).

What it adds
------------
* `iot.device.lne_certificate_number` — the type-examination
  certificate number (e.g. ``17-FR-0123-NB-0071``).
* `iot.device.lne_notified_body` — selection: ``lne`` (FR),
  ``ptb`` (DE), ``accreditar`` (IT), ``inmetro_eu`` (PT), etc.
* `iot.device.lne_certificate_expiry` — date after which the
  certificate is no longer valid; the cron flags the device.
* `iot.device.lne_max_weight_g` — Maximum capacity from the
  certificate (must match the physical M-mark).
* `iot.device.lne_min_weight_g` — Minimum legal-for-trade weight
  (typically 20 e for retail scales).
* `iot.device.lne_division_g` — verification scale interval (e),
  in grams.
* New `filamind.scale.weighing.event` model — captures every
  weight returned from a certified scale that was used for
  pricing (i.e. flowed into a pos.order.line).
* Cron `_cron_check_lne_expiry` (daily): emails configured
  responsible users when a certificate is < 30 days from expiry.
* Cron `_cron_purge_old_weighing_events` (monthly): respects
  ``filamind.scale.weighing.event.retention_days`` (default 400
  to cover the EU Member-State minimum of 1 year + buffer).

Out of scope (deliberately)
---------------------------
* The actual EU Module B certificate issuance — that's the job of
  the notified body.
* The legal weight-or-count check on the box itself — that's
  built into the scale firmware (the M-mark certifies it).
* PTB / OIML self-test commands — added per-vendor in companion
  addons (e.g. filamind_pos_iot_adam_scale for Adam-specific).
""",
    'author': 'filamind',
    'website': 'https://github.com/filamind-app/filamind-iot',
    'depends': ['filamind_pos_iot'],
    'data': [
        'security/ir.model.access.csv',
        'data/cron_data.xml',
        'views/iot_device_views.xml',
        'views/scale_weighing_event_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
