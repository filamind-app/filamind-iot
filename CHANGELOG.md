# Changelog

All notable changes to filamind-iot are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/) and
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added — Phase 9: filamind_l10n_eg_iot new addon (v0.1.0)

> Roadmap Phase 9 of 16. Egyptian Tax Authority (ETA) hardware-fiscal
> printer integration on the IoT side. The signing happens **inside
> the device**; this addon dispatches the receipt to it and captures
> the device-issued UUID/QR for downstream e-receipt submission. The
> actual ETA submission API belongs in a localization EDI addon and
> is deliberately out of scope here.

- `pos.config.iot_eg_fiscal_printer_id` — receipt printer (or
  Fiscal Data Module device) that signs receipts. Filtered to
  `type_id.code in ('receipt_printer', 'fiscal_data')`.
- `pos.config.action_iot_eg_test_fiscal()` — round-trip test button
  (sends a small `fiscal_print` action and opens the resulting
  iot.command.queue form).
- `pos.order.iot_eg_fiscal_print_command_id` (m2o → iot.command.queue,
  readonly) — traceability link for the fiscal print job.
- `pos.order.iot_eg_fiscal_uuid` and `iot_eg_fiscal_qr` (readonly)
  — signature data the box reports back from the fiscal printer.
  A downstream `l10n_eg_eta_edi` addon is expected to read these
  fields and submit them to ETA.
- Hook on `pos.order.action_pos_order_paid`: when the order is
  paid on a config with a fiscal printer set, the order body is
  sent via `iot.box.send_bus_message` with `action='fiscal_print'`
  and the command queue id is stored on the order. Failures swallow
  silently so they never block the paid flow — staff retry from
  the order form, or a future ETA-resubmission cron picks up
  unsigned orders.
- `_filamind_render_eg_fiscal_body()` returns the plain-text body —
  override for ESC/POS, ESC/Z, or vendor-specific fiscal protocols.
- `_filamind_apply_eg_fiscal_response(uuid, qr)` — entry point the
  IoT controller / cron calls when the box reports the device's
  signature.

### Added — Phase 8: filamind_event_iot new addon (v0.1.0)

> Roadmap Phase 8 of 16. Bridges the LGPL `event` module with the
> filamind IoT gateway. Community alternative to Enterprise
> `event_iot` + `event_sale_iot` + `pos_event_iot` (all OEEL-1).

- `event.event.iot_badge_printer_id` — printer that issues attendee
  badges (filtered to `subtype=printer`).
- `event.event.iot_scanner_id` — scanner that checks attendees in by
  reading their badge barcode (filtered to `subtype=scanner`).
- `event.event.auto_print_badges` — disable per event (default: on).
- `event.registration.iot_badge_print_command_id` (m2o → iot.command.queue,
  readonly) and `event.registration.iot_badge_printed_date` (datetime,
  readonly) for traceability of which print job produced which badge.
- Auto-print hook on `event.registration.write`: when a registration
  flips to `state=open` (confirmed) and the linked event has
  `auto_print_badges` and a configured `iot_badge_printer_id`, the
  badge prints once via `iot.box.send_bus_message`. Print failures
  do not break confirmation — staff can reprint manually.
- `event.registration.action_iot_print_badge()` — manual reprint
  button on the registration form.
- `event.registration.action_iot_check_in()` — manual check-in button
  alongside the scanner-driven path (the scanner path is wired by the
  `iot.trigger` system from filamind_iot).
- Plain-text badge template (`_render_iot_badge`) — override for
  ESC/POS, ZPL, or branded layouts. Variables exposed: event name,
  attendee name, email, event date, registration ref.

### Added — Phase 7: filamind_self_order_iot new addon (v0.1.0)

> Roadmap Phase 7 of 16. Bridges the LGPL `pos_self_order` kiosk
> module with the filamind IoT gateway. Community alternative to
> Enterprise `pos_self_order_iot` (OEEL-1).

- `pos.config.self_order_iot_box_id` — IoT Box dedicated to the kiosk
  (independent of the cashier-side iot_box_id), filtered by
  `iot.box.can_be_kiosk = True`.
- `pos.config.self_order_iot_printer_id` — printer for the kiosk's
  customer-confirmation ticket.
- `pos.config.self_order_iot_terminal_id` — payment terminal exposed
  at the kiosk.
- `pos.config.self_ordering_iot_available_iot_box_ids` (computed o2m)
  — Enterprise-parity helper field for cross-import compatibility.
- Hook on `pos.order.action_pos_order_paid`: if the order is a
  self-order and the config has `self_order_iot_printer_id` set, push
  a confirmation ticket via `iot.box.send_bus_message`. Plain-text
  template; override `_render_kiosk_ticket` for ESC/POS or branded
  layouts.

### Added — Phase 6: filamind_quality_iot new addon (v0.1.0)

> Roadmap Phase 6 of 16. Quality control with IoT-driven
> measurements. Community LGPL-3 alternative to Enterprise's
> `quality_iot` + `quality_control_iot` (which require the OEEL-1
> `quality_control` module). We deliberately reimplement the quality
> models from scratch so the addon works on a vanilla Community Odoo.

**Models**
- `filamind.quality.point` — define a check (Pass/Fail, Measurement,
  or Picture) on a product/operation. Optional `iot_device_id` to
  auto-pull values from a caliper/scale/camera.
- `filamind.quality.check` — one captured measurement. Tracks the
  IoT command queue id so you can trace which device reading produced
  which check. Auto-judges Pass/Fail against the point's
  `tolerance_min/max` for measurement-type checks.
- `filamind.quality.alert` — open quality issue / non-conformance
  ticket with severity, state machine, corrective + preventive
  actions, and chatter.

**IoT integration**
- Taking a check on a point with `iot_device_id` set fires an
  `iot_action` (`read_once` or `picture`) and stores the
  iot.command.queue id on the check.
- Cron `_cron_apply_iot_results` (every minute) walks completed
  iot.command.queue rows and copies `value` / `image` / `weight`
  back into the matching check.

**Sequences + UI**
- `QP/0001` for points, `QC/00001` for checks.
- New top-level "Quality" menu (sequence 92).
- Buttons: Take Check, Re-read from IoT, Pass/Fail, Open Alert.

### Added — Phase 5: filamind_kitchen_display new addon (v0.1.0)

> Roadmap Phase 5 of 16. Tablet-friendly Kitchen Display System for
> restaurants — community alternative to Enterprise's
> `pos_restaurant_preparation_display` family.

**Models**
- `filamind.kitchen.display` — one row per tablet. Has `name`,
  `pos_config_ids` (m2m), `category_ids` (m2m filter),
  `auto_clear` + `clear_after_seconds`, `access_token` (URL auth),
  `public_url` (computed), and stat counters.
- `filamind.kitchen.stage` — workflow columns (default 3 created
  automatically: In Progress / Ready / Served).
- `filamind.kitchen.order` — one ticket per pos.order, links via
  `pos_order_id`, tracks `fired_date` / `completed_date` /
  `completion_seconds`.
- `filamind.kitchen.line` — line items (product, qty, note, state).
- `pos.config.filamind_kitchen_display_ids` (m2m) — bind a POS to
  one or more displays.

**Public route**
- `GET /filamind_kitchen/<id>?access_token=…` — vanilla-JS tablet
  page that polls every 5 s. (Proper OWL frontend in v0.2.0.)
- `GET /filamind_kitchen/<id>/orders?access_token=…` — JSON feed.
- `POST /filamind_kitchen/transition` — stage move with token check.

**Hooks**
- `pos.order.action_pos_order_paid` extended to materialise
  kitchen.order rows on every linked display, filtered by
  category_ids if set, and pushes a `bus.bus` event for the OWL
  frontend.

**Crons**
- `_cron_auto_clear` — drops served orders past `clear_after_seconds`.
- `_cron_auto_advance` — moves orders to next stage if
  `auto_advance_seconds` set.

**UI**
- Backend list/form/search for displays + orders.
- Menu under `POS → Kitchen Displays`.
- "Open Tablet View" + "Rotate Token" + "Clear Served" buttons.
- Inline CSS for the public page (dark theme, kanban columns).

### Added — Phase 4: Missing field extensions on existing addons

> Roadmap Phase 4 of 16. Brings the three existing business addons in
> line with what upstream `pos_iot`, `mrp_iot`, `delivery_iot` ship.

**filamind_pos_iot v0.2.0**
- `pos.config.iot_scanner_ids` (m2m) — multiple scanners per POS.
  `pos.config.iot_scanner_id` (m2o) kept as a deprecated alias until
  v1.0.
- `pos.config.use_iot_box` (boolean) toggle.
- New file `models/pos_printer.py`: `pos.printer.iot_device_id` (m2o)
  + `pos.printer.iot_use_lna` (boolean) — kitchen / bar tickets
  dispatch through the IoT Box.
- `views/pos_printer_views.xml` to expose the new fields on the printer
  form.
- `pos_restaurant` added to module depends.

**filamind_mrp_iot v0.2.0**
- New model `iot.trigger` (mirrors Enterprise `mrp_iot.iot.trigger`):
  `device_id`, `workcenter_id`, `key`, `sequence`, plus an `action`
  selection with **all 19 Enterprise codes** for cross-import
  compatibility (`VALI`, `PAUS`, `NEXT`, `PREV`, `SKIP`, `CLMO`,
  `CLWO`, `FINI`, `RECO`, `CANC`, `PACK`, `SCRA`, `PROP`, `PRSL`,
  `PRNT`, `picture`, `measure`, `pass`, `fail`).
- `mrp.workcenter.trigger_ids` (o2m → iot.trigger).
- `security/ir.model.access.csv` + `views/iot_trigger_views.xml`.

**filamind_stock_iot v0.2.0**
- New file `models/stock_picking_type.py`:
  `stock.picking.type.iot_scale_ids` (m2m → iot.device) — mirrors
  Enterprise `delivery_iot`.
- `views/stock_picking_type_views.xml` to surface the field on the
  operation-type form.

### Added — Phase 2: Multi-transport server endpoints (filamind_iot v19.0.4.0.0)

> Roadmap Phase 2 of 16. Server side of the WebSocket → LongPoll →
> ShortPoll graceful-degradation chain. The matching box-side patch
> (transport.py) ships in filamind-iotbox v0.2.0.

- New endpoints (each with `/iot/box/...` alias for symmetry):
  * `POST /filamind_iot/poll` — long-poll. Blocks up to 30 s waiting
    for new `iot.command.queue` rows in state `sent` with id greater
    than the box's `last_seq`. Returns up to 50 commands at once.
  * `POST /filamind_iot/poll_short` — short-poll. Same behaviour but
    returns immediately. For environments where long-polling is
    actively blocked (some hardened LBs).
- `iot.command.queue.delivered_at` (datetime) — set when a poll
  endpoint hands a command to the box, so the next poll cycle won't
  re-deliver. Stays NULL for boxes still on WebSocket transport.
- Both endpoints reuse the existing token-based `_authenticate_box`
  and require the same JSON envelope as our other authenticated routes.

### Added — Phase 1: Upstream protocol parity (filamind_iot v19.0.3.0.0)

> Roadmap Phase 1 of 16. After this release, an unmodified upstream
> Odoo IoT Box image can pair with filamind-iot and ship logs / keyboard
> layouts / display URLs without code changes on the box.

- New model `iot.channel` (singleton) — `get_iot_channel()` returns the
  shared `bus.bus` channel name from
  `ir.config_parameter['iot.ws_channel']`. Generated lazily on first
  call. Lets upstream `pos_iot` / `mrp_iot` extension code coexist
  with our per-box channel design.
- New model `iot.keyboard.layout` — populated by the box's keyboard
  driver POSTing to `/iot/keyboard_layouts`. Used as the dropdown for
  per-device layouts on `iot.device`.
- `iot.box` extended with Enterprise-parity fields:
  `use_custom_handlers`, `must_install_fdm_module`, `use_lna`,
  `can_be_kiosk`, `ssl_certificate_end_date`, `version_commit_url`,
  `associated_pos_config_ids` (computed; safe when POS isn't installed).
- `iot.device` extended with: `iot_ip` (LAN IP for network devices),
  `is_scanner`, `keyboard_layout` (m2o → iot.keyboard.layout),
  `report_ids` (m2m → ir.actions.report — bind a printer to default
  reports), `display_orientation`, `display_url`.
- New HTTP endpoints (registered with both `/filamind_iot/...` and
  `/iot/...` aliases for upstream compatibility):
  * `POST /iot/log` — streaming text log shipper, persists into
    `iot.connection.log` with severity inferred from log level.
  * `POST /iot/keyboard_layouts` — form-encoded JSON list of X11
    layouts; deduplicates against existing `iot.keyboard.layout` rows.
  * `GET /iot/box/<box_id>/display_url` — returns
    `{device_identifier: url}` for every display device on the box.
  * `POST /iot/get_handlers` — stub returning `{not_modified: True}`
    so the upstream box's handler-download loop is satisfied.
- `/filamind_iot/pair` response now also returns `db_name`,
  `ws_channel` (the shared one), `transports`, and
  `min_poll_interval` so the box's WebsocketClient can build its
  `/web/login?db=...` URL and so future multi-transport probing
  (Phase 2) has hints from the server.
- ACL added for the two new models.
- CI route-aliases check broadened: any `/iot/*` path now counts as a
  valid upstream alias (was previously only `/iot/box/*` or
  `/iot/setup`).

### Changed — roadmap scope expanded to 100 % parity (v0.3.3 docs)
- Reclassified the four modules previously marked "out-of-scope":
  * `pos_iot_six` — buildable, the LGPL Six driver already ships on
    the IoT Box image.
  * `pos_iot_worldline` — buildable, Worldline driver on the box +
    CTEP runtime ZIP is a public download.
  * `pos_iot_adam_scale` — buildable, ~3 hour parser branch on top of
    the existing serial scale driver.
  * `l10n_eu_iot_scale_cert` — the *software* (audit logs, hash-chain,
    LNA logging) is buildable. The legal LNE certificate stays the
    customer's regulatory journey.
- ROADMAP.md gained Phases 12-15 covering the four addons. Total
  effort estimate revised from ~100 h to ~130 h. Calendar from
  ~3 weeks to ~4 weeks.
- COMPARISON.md updated: the "What we will not build" section is
  removed. New target = full coverage of all 20 Enterprise IoT
  modules.

### Added — comprehensive documentation (v0.3.2)
- `docs/COMPARISON.md` — feature matrix vs Odoo Enterprise IoT (20
  modules) and Community Edition. Compiled by introspecting a live
  Enterprise SaaS via JSON-RPC.
- `docs/ENTERPRISE_REFERENCE.md` — full protocol + schema reference:
  every model, field, HTTP route, bus channel, and selection list the
  upstream IoT Box expects. Includes the connection lifecycle diagram
  and message-type dispatch table.
- `docs/ROADMAP.md` — 12-phase plan toward Enterprise parity. Covers
  hotfix → protocol parity → multi-transport → self-diagnose → 5 new
  business addons (KDS, Quality, Self-Order, Events, Egypt fiscal) →
  per-platform reverse-proxy docs → CI matrix. Calls out 4
  vendor-locked modules we will *not* build.
- `docs/KITCHEN_DISPLAY.md` — design doc for the upcoming
  `filamind_kitchen_display` addon (replaces the Enterprise
  `pos_restaurant_preparation_display` family).
- README updated with prominent links to the four docs.

### Changed — repo layout (v0.3.1)
- All four addons now live under a top-level `addons/` directory
  (matches Odoo core's bundled-addons convention).
  **Migration:** in your `odoo.conf`, point `addons_path` at
  `/path/to/filamind-iot/addons` instead of `/path/to/filamind-iot`.
- CI workflow paths updated; `pyproject.toml` is unchanged because
  ruff's `per-file-ignores` are matched by filename, not path.
- Module names, Python imports, model names, and HTTP routes are all
  unchanged — this is a pure folder-level reorganisation.

### Added — business-domain addons (v0.3.0)
- **`filamind_pos_iot`** — extends `pos.config` with M2O fields for printer,
  scale, scanner, customer display, and cash drawer. Adds test buttons in
  the POS configuration form. Adds `pos.session.action_print_iot_receipt`
  and `pos.session.update_iot_customer_display` server methods. Binds
  `pos.payment.method` to a specific IoT terminal via `iot_terminal_id`.
- **`filamind_stock_iot`** — extends `stock.warehouse` with label-printer,
  receipt-printer, scale, and scanner defaults. Adds `Print IoT Label` +
  `Read Scale` buttons on `stock.picking`. Picking inherits the
  warehouse's IoT defaults via `related` fields.
- **`filamind_mrp_iot`** — extends `mrp.workcenter` with label-printer,
  caliper, scanner defaults. Adds `Read Caliper` + `Print Label` buttons
  on `mrp.workorder`. Default work-order label template included; override
  for custom ZPL/EPL.
- **CI updated** to scan all four addons (ruff, py_compile, XML
  well-formedness, manifest references, no-iot_custom-leftover, route
  aliases, installable check).

### Added — WebSocket bidirectional command flow (v0.2.0)
- **`bus.bus` integration**: each box gets a private channel `iot_<token>`,
  allocated on first `/iot/setup` call. The box's `WebsocketClient`
  subscribes to it via Odoo's stock `/websocket` endpoint — no upstream
  Odoo bus changes needed.
- **`/iot/setup`** controller (and `/filamind_iot/setup` alias) — receives
  the box's start-up POST and returns the channel name. Auto-creates
  unknown boxes in `pairing` state.
- **`/iot/box/send_websocket`** controller (and `/filamind_iot/command_result`
  alias) — collects results that the box POSTs back after running a
  command. Correlates by `session_id` to the originating queue entry.
- **`iot.command.queue`** model + form/list views + Commands menu.
  Tracks every outgoing command and its result with state machine
  (`pending` → `sent` → `completed` / `failed` / `timeout`). Cron reaps
  in-flight commands past their deadline.
- **`iot.box.send_bus_message(method, payload, device, timeout)`** —
  programmatic API for sending commands. Adds a queue entry and dispatches
  via `bus.bus._sendone`.
- **`iot.box.action_test_connection`** button on the box form — round-trips
  a `test_connection` bus message to verify end-to-end reachability.
- **`iot.device.action_test_print`** button on printer-type device forms —
  sends a small ESC/POS test page (final hardware verification = Phase 2).
- **`iot.device.action_test`** rewritten to use the bus instead of
  creating a no-op log entry.

### Added — initial release (v0.1.0)
- 5 models: `iot.box`, `iot.device`, `iot.device.type`,
  `iot.connection.log`, `iot.pairing.wizard`.
- HTTP endpoints under `/filamind_iot/*` plus `/iot/box/*` aliases for
  drop-in compatibility with the [filamind-iotbox](https://github.com/filamind-app/filamind-iotbox) image and the upstream Odoo IoT Box.
- Dual pairing wizard: server-code or box-token.
- 12 preloaded device types covering printers, scales, scanners, cameras,
  payment terminals, fiscal modules, customer displays, etc.
- Multi-company `ir.rule` on `iot.box`, `iot.device`, `iot.connection.log`,
  `iot.command.queue`.
- `_check_company_auto = True` on `iot.device` to enforce same-company
  device → box linking.
- `pairing_ttl` system parameter wired into `action_generate_pairing_code`
  (was hardcoded at 15 minutes).
- HTTP error responses no longer echo internal exception messages
  (information-disclosure hardening).
- CI workflow: ruff + py_compile + XML well-formedness +
  manifest-references-exist sanity + route-alias presence.

### Roadmap
- **Phase 2** — hardware-in-the-loop verification with a real ESC/POS
  printer, a Mettler scale and a Worldline payment terminal.
- **Phase 3** — POS/Inventory/Manufacturing integration glue, mirroring
  upstream `pos_iot` / `delivery_iot` etc.

### Notes
- Addon technical name: `filamind_iot` (Python module).
- Repo name on GitHub: `filamind-iot` (URL-friendly).
