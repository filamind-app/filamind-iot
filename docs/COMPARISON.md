# Enterprise vs Community vs filamind-iot — Detailed Comparison

> Snapshot taken 2026-05-11 against `payout.odoo.com` (Odoo `saas~19.2.1.0`).
> All facts in this document were extracted via JSON-RPC introspection of a
> live Enterprise database with every IoT-adjacent module installed.

---

## 1. Headline finding

The **entire IoT module family is `OEEL-1` (Odoo Enterprise) licensed.**
Odoo Community edition ships **zero** IoT integration — only the legacy
`hw_proxy` modules (deprecated). The only LGPL-3 piece is `iot_drivers`
which lives on the IoT Box itself (the Raspberry Pi), not on the server.

That is the gap **filamind-iot** is built to fill.

---

## 2. Module inventory (20 Enterprise IoT modules)

| Technical name | Display name | License | Purpose |
|---|---|---|---|
| `iot` | Internet of Things | OEEL-1 | Base models + bus channel |
| `iot_drivers` | Hardware Proxy | LGPL-3 | Box-side code (the Pi image) |
| `pos_iot` | IoT for PoS | OEEL-1 | Printer/scale/scanner/display from POS |
| `pos_self_order_iot` | POS Self Order IoT | OEEL-1 | Kiosk → IoT |
| `pos_iot_six` | POS IoT Six | OEEL-1 | Six payment terminal |
| `pos_iot_worldline` | POS IoT Worldline | OEEL-1 | Worldline payment terminal |
| `pos_iot_adam_scale` | POS IoT Adam Scale | OEEL-1 | Adam Equipment scales |
| `pos_restaurant_preparation_display` | KDS — Preparation Display | OEEL-1 | Kitchen Display tablet UI |
| `pos_self_order_preparation_display` | Self-Order → KDS | OEEL-1 | Kiosk orders to KDS |
| `pos_online_payment_self_order_preparation_display` | Online → Kiosk → KDS | OEEL-1 | Online payment + kiosk + KDS link |
| `mrp_iot` | IoT for Manufacturing | OEEL-1 | `iot.trigger` for workcenter actions |
| `quality_iot` | Quality Steps with IoT | OEEL-1 | `quality.point.device_id` |
| `quality_control_iot` | IoT for Quality Control | OEEL-1 | `quality.check` measurement capture |
| `delivery_iot` | IoT for Delivery | OEEL-1 | Stock picking + scale weighing |
| `event_iot` | IoT for Events | OEEL-1 | Event badges + check-in |
| `event_sale_iot` | IoT for Event/Sale | OEEL-1 | Paid event ticket printing |
| `pos_event_iot` | IoT for PoS/Event | OEEL-1 | POS-driven event workflow |
| `l10n_eg_iot` | Egypt - Internet Of Things | OEEL-1 | Egyptian fiscal proxy |
| `l10n_eu_iot_scale_cert` | LNE EU Scale Cert | OEEL-1 | EU legal scale certification |
| `pos_enterprise` | Point of Sale enterprise | OEEL-1 | Holds the KDS reset wizard + report |

---

## 3. Side-by-side feature matrix

| Capability | Community | Enterprise | filamind-iot today | filamind-iot target |
|---|---|---|---|---|
| `iot.box` / `iot.device` models | ❌ | ✅ | ✅ (own schema) | ✅ + Enterprise-shape compatibility layer |
| `iot.channel` singleton (shared bus channel) | ❌ | ✅ | ❌ | ✅ (so upstream `pos_iot` can run alongside) |
| `iot.discovered.box` + `add.iot.box` wizard | ❌ | ✅ | partial | ✅ (multi-stage + offline token) |
| `iot.keyboard.layout` model | ❌ | ✅ | ❌ | ✅ |
| `iot.trigger` (19 workcenter actions) | ❌ | ✅ | ❌ | ✅ |
| `pos.config.iot_*` fields | ❌ | ✅ (7 fields) | ✅ (5 fields, `iot_scanner_id` is m2o not m2m) | ✅ + `iot_scanner_ids` m2m + `use_iot_box` + `iot_display_id` |
| `pos.printer.iot_device_id` (kitchen printers) | ❌ | ✅ | ❌ | ✅ |
| `pos.payment.method.iot_device_id` | ❌ | ✅ | ✅ (via `iot_terminal_id`) | rename to match upstream |
| `mrp.workcenter.trigger_ids` | ❌ | ✅ | ❌ | ✅ |
| `quality.point.device_id` + `quality.check.iot_box_id` | ❌ | ✅ | ❌ | ✅ |
| `stock.picking.type.iot_scale_ids` | ❌ | ✅ | ❌ | ✅ |
| `stock.put.in.pack.iot_device_id` | ❌ | ✅ | ❌ | ✅ |
| `ir.actions.report.device_ids` (default printer per report) | ❌ | ✅ | ❌ | ✅ |
| `pos.prep.display` Kitchen Display | ❌ | ✅ | ❌ | ✅ (new `filamind_kitchen_display` addon) |
| `iot.box.state` + `last_heartbeat` + `is_online` | n/a | ❌ (timeout-based) | ✅ (improvement) | keep |
| `iot.command.queue` audit trail | n/a | ❌ (fire-and-forget pub/sub) | ✅ (improvement) | keep + add pub/sub |
| HTTP `/iot/setup` | ❌ | ✅ | ✅ | ✅ |
| HTTP `/iot/log` | ❌ | ✅ | ❌ | ✅ |
| HTTP `/iot/keyboard_layouts` | ❌ | ✅ | ❌ | ✅ |
| HTTP `/iot/box/<id>/display_url` | ❌ | ✅ | ❌ | ✅ |
| HTTP `/iot/box/send_websocket` | ❌ | ✅ | ✅ (alias) | ✅ |
| HTTP `/iot/get_handlers` | ❌ | ✅ | ❌ | ✅ stub |
| WebSocket transport | ❌ | ✅ (only) | ✅ (only) | ✅ + LongPoll + ShortPoll graceful degradation |
| Self-diagnose endpoint on box | n/a | ❌ | ❌ | ✅ |
| Multi-company `ir.rule` on `iot.device`/`iot.connection.log` | n/a | ❌ | ✅ | keep |
| CI on the addon | n/a | proprietary | ✅ ruff + py_compile + XML + manifest | keep |

---

## 4. Hardware-adjacent modules that are NOT IoT

These modules use hardware (scanners, webcams, signature pads) but talk
directly to the browser via HID/WebUSB/MediaStream — **they don't need the
IoT Box at all**. They're not part of the IoT comparison surface.

| Module | License | Mechanism |
|---|---|---|
| `barcodes` | LGPL-3 | Browser barcode parsing (HID keyboard wedge) |
| `barcodes_gs1_nomenclature` | LGPL-3 | GS1-128 barcode parsing |
| `stock_barcode` + family | OEEL-1 | Browser scanner UI (webcam or HID) |
| `pos_barcodelookup` / `product_barcodelookup` | OEEL-1 | UPC database web service |
| `pos_pine_labs` / `pos_self_order_pine_labs` | LGPL-3 | Payment SDK in browser |
| `pos_self_order_qfpay` / `pos_self_order_razorpay` | LGPL-3 | Payment SDK in browser |
| `hr_attendance` | LGPL-3 | Webcam for facial check-in |

→ **Out of scope** for filamind-iot — they ship in Community and don't need us.

---

## 5. Selection-list reference (we should match these in our addons)

### `iot.device.type` (10)
`printer` · `camera` · `keyboard` · `scanner` · `device` · `payment` ·
`scale` · `display` · `fiscal_data_module` · `unsupported`

### `iot.device.connection` (5)
`network` · `direct` (USB) · `bluetooth` · `serial` · `hdmi`

### `iot.device.subtype` (printers only)
`receipt_printer` · `label_printer` · `office_printer`

### `iot.trigger.action` (19 — drives MRP workcenter from a device key)
`picture` (Take Picture) · `measure` (Take Measure) · `SKIP` · `PAUS`
(Pause) · `PREV` · `NEXT` · `VALI` (Validate) · `CLMO` (Close MO) ·
`CLWO` (Close WO) · `FINI` (Finish) · `RECO` (Record Production) ·
`CANC` (Cancel) · `PROP` (Print Operation) · `PRSL` (Print Delivery
Slip) · `PRNT` (Print Labels) · `PACK` · `SCRA` (Scrap) · `pass` · `fail`

---

## 6. Bus channel design — Enterprise vs ours

**Enterprise:** one shared channel per database, stored in
`ir.config_parameter['iot.ws_channel']` (e.g.
`iot_channel-3da0159b0ca1a14cf66552ddd500f750`). Every box subscribes
to this single channel. Each `bus.bus` message carries `iot_identifier`
which the receiving box uses to filter for its own commands.

**filamind-iot today:** one channel per box (`iot_<token>`). The box
only receives messages addressed to it.

**Trade-offs:**

| Approach | Pro | Con |
|---|---|---|
| Shared (Enterprise) | Simpler routing (1 channel for the DB) | Every box wakes up for every command |
| Per-box (us) | Lower wake-ups; better isolation | Need a small server-side router |

**Decision:** keep our per-box channel for filamind-native deployments,
but **also** expose `iot.channel.get_iot_channel()` returning a shared
fallback channel name so an unmodified Enterprise IoT Box image can
coexist with us if a customer mixes the two.

---

## 7. Endpoints we are missing right now

Routes confirmed by direct HTTP probing of `payout.odoo.com`:

| Route | Method | Status against payout | Required for parity? |
|---|---|---|---|
| `/iot/setup` | POST | 200 | ✅ have it |
| `/iot/log` | POST | 401 (auth) | ❌ **add** |
| `/iot/keyboard_layouts` | POST | 500 (empty body) → exists | ❌ **add** |
| `/iot/box/<id>/display_url` | GET | 400 (missing args) → exists | ❌ **add** |
| `/iot/box/send_websocket` | POST | 200 | ✅ have it (as alias) |
| `/iot/get_handlers` | POST | 500 (empty body) → exists | ❌ **add stub** |
| `/iot/connect` | — | 404 | n/a (Enterprise doesn't have it either) |
| `/iot/discover` | — | 404 | n/a (discovery is client-side) |

---

## 8. Summary verdict

For 100 % feature parity with Enterprise IoT, filamind-iot needs:

1. **5 new addons:** `filamind_kitchen_display`, `filamind_quality_iot`,
   `filamind_self_order_iot`, `filamind_event_iot`, `filamind_l10n_eg_iot`.
2. **10 missing fields** added to existing models (see § 3).
3. **4 missing HTTP endpoints** wired in.
4. **2 missing models** added (`iot.channel` singleton, `iot.keyboard.layout`).
5. **Multi-transport** (WS + LongPoll + ShortPoll) for proxy-portability.
6. **Self-diagnose** on the box.

What we will **not** build (vendor-locked or niche):

- `pos_iot_six` / `pos_iot_worldline` / `pos_iot_adam_scale` — proprietary
  payment terminals & specific scale brand. Customers using these stay on
  Enterprise.
- `l10n_eu_iot_scale_cert` — EU legal certification process is not a
  software problem we can replicate.

A detailed implementation plan lives in [ROADMAP.md](ROADMAP.md).
A protocol-level reference of how the box talks to the server lives in
[ENTERPRISE_REFERENCE.md](ENTERPRISE_REFERENCE.md).
The new Kitchen Display addon design lives in [KITCHEN_DISPLAY.md](KITCHEN_DISPLAY.md).
