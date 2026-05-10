# Changelog

All notable changes to filamind-iot are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/) and
[Semantic Versioning](https://semver.org/).

## [Unreleased]

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
