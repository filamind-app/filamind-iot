# filamind-iot Roadmap to Enterprise Parity

> Phased plan to bring filamind-iot to ~95 % feature-equivalence with the
> 20-module Odoo Enterprise IoT stack.
>
> Reference: see [COMPARISON.md](COMPARISON.md) for the gap analysis and
> [ENTERPRISE_REFERENCE.md](ENTERPRISE_REFERENCE.md) for the protocol details
> every phase below depends on.

---

## Versioning convention

- `filamind-iot` v0.x = pre-parity (current).
- `filamind-iot` v1.0 = full parity for the 5 in-scope sub-modules
  (POS, KDS, Stock, MRP, Quality). Sub-modules out of scope (Six,
  Worldline, Adam, EU LNE) explicitly listed as *not planned*.
- `filamind-iotbox` v0.x = pre-parity image. v1.0 = ships with the
  multi-transport client + self-diagnose.

---

## Phase 0 — Production Hotfix (live customer fix, ~30 min)

**Trigger:** filamind-iot already deployed at `deltafabs.com`, currently
broken because OpenLiteSpeed appends `Connection: Keep-Alive` to the WS
upgrade response.

**Steps:**
1. Add a Caddy sidecar to the customer's `docker-compose.yml`:
   ```yaml
   ws_proxy:
     image: caddy:2
     command: caddy reverse-proxy --from :80 --to odoo-web:8072 --change-host-header
     ports: ["8082:80"]
   ```
2. In CyberPanel vhost.conf, swap `/websocket` handler from
   `odoo_longpolling` (broken) to a new `odoo_ws_caddy` extprocessor
   pointing at `127.0.0.1:8082`.
3. `systemctl restart lsws`.

**Acceptance:** the existing `Test Connection` button on `iot.box`
returns `completed`, not `timeout`.

---

## Phase 1 — Upstream protocol compatibility (filamind_iot v0.3.0, ~6 h)

**Goal:** an unmodified upstream Odoo IoT Box image can talk to filamind-iot.

| Task | File |
|---|---|
| Add `iot.channel` singleton model with `get_iot_channel()` | `addons/filamind_iot/models/iot_channel.py` |
| Store the channel name in `ir.config_parameter['iot.ws_channel']` | same |
| `/iot/setup` must return `result: <ws_channel>` (string, not dict) | `controllers/iot_controller.py` |
| Add `POST /iot/log` (streaming text receiver, identifier+token auth) | new |
| Add `POST /iot/keyboard_layouts` (form-encoded layouts upload) + `iot.keyboard.layout` model | new |
| Add `GET /iot/box/<id>/display_url` returning `{device_identifier: url}` | new |
| Add `POST /iot/get_handlers` stub returning `{not_modified: true}` | new |
| Add `db_name` to `/filamind_iot/pair` response so the box can fetch a session cookie | existing |
| Add `iot.device.iot_ip`, `iot.device.report_ids` (m2m → ir.actions.report), `iot.device.is_scanner`, `iot.device.keyboard_layout` (m2o) | extend model |
| Add `iot.box.use_custom_handlers`, `iot.box.must_install_fdm_module`, `iot.box.use_lna`, `iot.box.can_be_kiosk`, `iot.box.ssl_certificate_end_date` | extend model |
| Add `iot.box.associated_pos_config_ids` (m2m → pos.config, computed from devices) | extend |

**Acceptance:** install `filamind_iot` next to upstream's bundled iot.box
image (no patches), pair, push a `test_protocol` from server, see the
box log it.

---

## Phase 2 — Multi-transport (filamind_iot v0.4.0 + filamind-iotbox v0.2.0, ~12 h)

**Goal:** survive any reverse proxy. The box auto-falls-back from
WebSocket → LongPoll → ShortPoll.

**Server side:**
| Task | File |
|---|---|
| `POST /filamind_iot/poll` long-poll endpoint, blocks up to 30 s for new commands per `(box_token, last_seq)` | new |
| `POST /filamind_iot/poll_short` short-poll endpoint, returns immediately | new |
| Reuse `iot.command.queue` as the source of truth for both poll endpoints | existing |

**Box side (image patch 5):**
| Task | File |
|---|---|
| `tools/transport.py` — abstract `Transport` with `WebSocketTransport`, `LongPollTransport`, `ShortPollTransport` | new |
| `Transport.create(server_url, channel)` probes WS, falls back gracefully | new |
| `main.py` — replace `WebsocketClient(channel)` with `Transport.create(...)` | patch |
| `tools/communication.py` — accept `'longpoll'` and `'shortpoll'` as `communication_type` strings | patch |
| Persist chosen transport in odoo.conf for next boot (skip the probe) | patch |

**Acceptance:** with LiteSpeed deliberately mis-configured, the box still
receives commands within 5 s via long-poll, with the diagnose endpoint
reporting `transport=longpoll`.

---

## Phase 3 — Self-diagnose + Re-sync (filamind-iotbox v0.3.0, ~4 h)

**Goal:** make the IoT Box's settings page tell the user exactly what's
wrong with their setup.

**Box side (image patch 6):**
| Task |
|---|
| `GET /iot_drivers/diagnose` — runs DNS, HTTP/HTTPS, TLS chain, WS upgrade, returns JSON report (incl. detection of OpenLiteSpeed `Keep-Alive` bug) |
| Settings page: add "Diagnose Connection" button — opens diagnose result in a modal with copy-to-clipboard |
| Settings page: add "Re-sync Devices" button — forces `_send_all_devices()` with empty `previous_*` dicts (fixes the "only first device sent" bug) |
| Show transport choice (WS/LongPoll/Short) in the box homepage header |

**Acceptance:** clicking Diagnose on a misconfigured server reports
`status: connection_ok / websocket_failed / longpoll_ok` with a
human-readable hint linking to `docs/REVERSE_PROXY.md` for the
detected proxy product.

---

## Phase 4 — Missing extensions on existing addons (filamind_pos_iot v0.2.0, filamind_mrp_iot v0.2.0, filamind_stock_iot v0.2.0, ~6 h)

| Addon | Change |
|---|---|
| `filamind_pos_iot` | Convert `iot_scanner_id` (m2o) → `iot_scanner_ids` (m2m). Add `iot_display_id` (m2o). Add `use_iot_box` (boolean) toggle. Add `pos.printer.iot_device_id` for kitchen/bar printers. |
| `filamind_pos_iot` | Add `pos.payment.method.iot_device_id` (renaming our `iot_terminal_id`, with deprecation warning). |
| `filamind_mrp_iot` | Add `iot.trigger` model (`device_id`, `workcenter_id`, `key`, `sequence`, `action`) with full 19-action selection. |
| `filamind_mrp_iot` | Add `mrp.workcenter.trigger_ids` (o2m). UI: trigger editor on workcenter form. |
| `filamind_stock_iot` | Add `stock.picking.type.iot_scale_ids` (m2m). |
| `filamind_stock_iot` | Add `stock.put.in.pack.iot_device_id` + `iot_id` + `available_scale_ids`. |
| All | Add `ir.actions.report.device_ids` (m2m → iot.device) so admins can pin a default IoT printer per report. |

**Acceptance:** importing a `pos.config` exported from Enterprise loads
without missing-field errors.

---

## Phase 5 — `filamind_kitchen_display` new addon (~16 h)

**Goal:** Kitchen Display System for restaurants — tablet web view,
no IoT box needed.

See [KITCHEN_DISPLAY.md](KITCHEN_DISPLAY.md) for the full design.

| Task |
|---|
| Models: `filamind.kitchen.display`, `filamind.kitchen.order`, `filamind.kitchen.line`, `filamind.kitchen.stage` |
| Public route `/filamind_kitchen/<id>?access_token=...` (no login, OWL UI) |
| `pos.config.filamind_kitchen_display_ids` (m2m) so a POS sends new orders to one or more displays |
| `bus.bus` push when a `pos.order` is paid → all matching displays update live |
| Stage transitions (in-progress → ready → served) drive a status column |
| Auto-clear after N seconds (configurable) |
| Optional: print a kitchen ticket on a `pos.printer.iot_device_id` printer too |

**Acceptance:** a tablet at `https://odoo.example.com/filamind_kitchen/3?access_token=…`
shows orders from two POS configs in real time, drag-and-drop between
stages.

---

## Phase 6 — `filamind_quality_iot` new addon (~10 h)

| Task |
|---|
| Extend `quality.point` with `iot_device_id` (m2o → iot.device) — auto-pull a measurement from a caliper/scale at check time |
| Extend `quality.check` with `iot_box_id` (m2o → iot.box) and `iot_measure` (float) |
| Extend `quality.check.wizard` with the same + `iot_picture` (binary, from camera) |
| Wizard sends `iot_action` `measure` / `picture` and waits up to 10 s for response |

**Acceptance:** a quality check with a Mitutoyo caliper auto-fills the
measurement field on opening the check wizard.

---

## Phase 7 — `filamind_self_order_iot` new addon (~8 h)

| Task |
|---|
| Extend `pos.config` with `self_order_iot_box_id` and `self_order_iot_printer_id` |
| Wire kiosk's "send to kitchen" button to the IoT printer + KDS |
| Optional: payment terminal on kiosk side |

---

## Phase 8 — `filamind_event_iot` new addon (~6 h)

| Task |
|---|
| Extend `event.event` with `iot_badge_printer_id` |
| On `event.registration.action_set_done`, push a print job |
| Optional: barcode scanner triggers `action_set_done` automatically |

---

## Phase 9 — `filamind_l10n_eg_iot` new addon (~6 h)

| Task |
|---|
| Egyptian fiscal proxy token (`l10n_eg_proxy_token`) sent in `/iot/setup` |
| Wire to the existing `l10n_eg_driver` already shipping in iot_drivers |
| `account.move` → push to fiscal device on validation |

---

## Phase 10 — Documentation per reverse-proxy + per panel (~10 h)

`docs/REVERSE_PROXY.md` with tested snippets for each of the categories
identified during the discovery phase:

**Open-source panels:** aaPanel, CyberPanel, HestiaCP, VestaCP,
ISPConfig 3, Webmin/Virtualmin, CloudPanel, EasyPanel, Coolify,
CapRover, Dokku, Yunohost, Cloudron, Froxlor.

**Commercial panels:** cPanel/WHM, Plesk, DirectAdmin, InterWorx,
ISPmanager, CWP.

**Container / PaaS:** Docker Compose + Traefik, Kubernetes
(ingress-nginx, Traefik, Contour, HAProxy ingress), Docker Swarm.

**Edge / CDN:** Cloudflare, AWS ALB, AWS API Gateway WS, GCP LB,
Azure App Gateway, Fastly.

**Tunnels:** Cloudflare Tunnel, Tailscale Funnel, ngrok, Netbird,
ZeroTier.

**Reverse-proxies standalone:** nginx, Apache 2.4+, Caddy, Traefik,
HAProxy, Envoy, LiteSpeed/OLS, IIS.

Per category: a copy-pasteable snippet, a 30-second test command,
expected behaviour, and links to the diagnose endpoint output for
when it doesn't work.

---

## Phase 11 — CI matrix (~16 h)

GitHub Actions matrix that brings up Odoo + each major reverse proxy in
docker-compose, runs the box-mock against it, asserts the chosen
transport is correct.

| reverse-proxy | expected transport |
|---|---|
| nginx | websocket |
| Caddy | websocket |
| Traefik | websocket |
| Apache | websocket |
| openlitespeed (broken) | longpoll |
| no proxy / direct | websocket |
| Cloudflare | websocket |

---

## Phase 12 — Out-of-scope (will not build)

| Module | Why not |
|---|---|
| `pos_iot_six` | Six payment terminal SDK is proprietary, NDA-bound. Customers using Six remain on Enterprise. |
| `pos_iot_worldline` | Same — Worldline TIM SDK is proprietary. |
| `pos_iot_adam_scale` | Adam Equipment-specific. Generic scale support already covers most cases. |
| `l10n_eu_iot_scale_cert` | EU LNE certification is a legal/lab process, not a code problem. |

---

## Effort summary

| Phase | Hours | Cumulative |
|---|---|---|
| 0 (hotfix) | 0.5 | 0.5 |
| 1 (protocol parity) | 6 | 6.5 |
| 2 (multi-transport) | 12 | 18.5 |
| 3 (self-diagnose) | 4 | 22.5 |
| 4 (missing extensions) | 6 | 28.5 |
| 5 (kitchen display) | 16 | 44.5 |
| 6 (quality) | 10 | 54.5 |
| 7 (self-order kiosk) | 8 | 62.5 |
| 8 (events) | 6 | 68.5 |
| 9 (Egypt fiscal) | 6 | 74.5 |
| 10 (proxy docs) | 10 | 84.5 |
| 11 (CI matrix) | 16 | 100.5 |

**~100 hours of focused work for full Enterprise-parity** (excluding the
4 vendor-locked modules). At a single-developer pace with test cycles,
plan for ~3 weeks calendar time.

---

## Suggested release cadence

```
v0.3.0 — Phase 1 (protocol parity)              week 1, days 1-2
v0.4.0 — Phase 2 (multi-transport)              week 1, days 3-5
v0.5.0 — Phase 3 + 4                            week 2, days 1-2
v0.6.0 — Phase 5 (KDS) major release            week 2, days 3-5 + week 3 day 1
v0.7.0 — Phase 6 (Quality)                      week 3, days 2-3
v0.8.0 — Phase 7 (Self-Order)                   week 3, day 4
v0.9.0 — Phase 8 + 9 + 10 + 11                  week 3 day 5
v1.0.0 — full parity, polished docs             week 4
```

Every release MUST land with a green CI matrix and an updated
`CHANGELOG.md`.
