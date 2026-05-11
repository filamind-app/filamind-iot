# Changelog

All notable changes to filamind-iot are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/) and
[Semantic Versioning](https://semver.org/).

## [Unreleased]

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
