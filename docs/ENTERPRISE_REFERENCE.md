# Enterprise IoT — Protocol & Schema Reference

> Canonical record of how Odoo Enterprise's IoT modules talk to the IoT Box,
> extracted from a live `saas~19.2` instance + the LGPL-licensed `iot_drivers`
> code shipped on the box image.
>
> Use this as the source of truth when building filamind-iot endpoints — every
> rule below is what the unmodified upstream IoT Box actually expects to see.

---

## 1. Connection lifecycle

```
   Box boots
      │
      ▼
   tools/system.IOT_IDENTIFIER  (read /sys/firmware/devicetree/base/serial-number)
      │
      ▼
   manager._send_all_devices()                   (main.py:75)
      │
      │  POST  {server}/iot/setup
      │       JSON-RPC envelope:
      │       { "params": {
      │           "iot_box": { identifier, mac, ip, token, version,
      │                        name=hostname, l10n_eg_proxy_token },
      │           "devices": { "<dev_identifier>": {name,type,
      │                          manufacturer,connection,
      │                          subtype-only-for-printer}, ... } } }
      │       Server returns:
      │       { "result": "<bus_channel_name>" }       ← single string
      │
      ▼
   self.ws_channel = result                      (main.py:116)
      │
      ▼
   helpers.download_iot_handlers()               (main.py:152)
      │
      ▼
   WebsocketClient(self.ws_channel).start()      (main.py:161)
      │
      │  GET   {server}/web/login?db=<db>          (anonymous, fetch session_id)
      │  WS    wss://<server>/websocket
      │  send  { "event_name": "subscribe",
      │          "data": { "channels": [ws_channel],
      │                    "iot_token": ..., "mac_address": ...,
      │                    "identifier": IOT_IDENTIFIER } }
      │
      ▼
   3-second loop:
     if _get_changes_to_send(): _send_all_devices()
     wifi.reconnect() if RPi
     schedule.run_pending()                      ← daily cert renew, weekly upgrade
```

### Push direction (server → box)

Server-side handler (any module):

```python
channel = self.env['iot.channel'].get_iot_channel()    # one string per DB
self.env['bus.bus']._sendone(channel, 'iot_action', {
    'iot_identifier': box.identifier,                  # box filters on this
    'session_id'   : str(request.session.uid),         # for response routing
    'device_identifier': device.identifier,
    'data'         : <action-specific body>,
})
```

The box's `WebsocketClient.on_message` receives every message on the channel,
filters via `payload.iot_identifier == IOT_IDENTIFIER`, then dispatches:

```python
result = communication.handle_message(message_type, 'ws', **payload)
if result:
    send_to_controller(result)              # POST {server}/iot/box/send_websocket
```

`message_type` is one of (from box's `tools/communication.py`):

| Type | Action | Payload |
|---|---|---|
| `iot_action` | dispatch to `main.iot_devices[device_identifier].action(kwargs)` | device-specific |
| `server_clear` | `helpers.disconnect_from_server()` | none |
| `server_update` | rewrite `remote_server` config | `server_url` |
| `restart_odoo` | `helpers.odoo_restart(2)` | none |
| `remote_debug` | `system.toggle_remote_debug(token)` | `token`, `status` |
| `reset_password` | `system.generate_password()` | none |
| `test_protocol` | echo back | none |
| `test_connection` | run mtr / network checks | none |

### Response direction (box → server)

The box `POST`s its result to `{server}/iot/box/<method>`. Methods seen:

- `send_websocket` (default) — generic action result fan-in.
- `print_status` — printer driver status.
- `keyboard_layouts` — keyboard discovered new layouts.
- `<custom>` — drivers can pick any method name.

Body shape: `{"params": {<communication.handle_message return>}}` where
the inner dict always carries `session_id`, `iot_box_identifier`,
`device_identifier`, `time`, plus driver-specific fields (e.g.
`print_id`, `value`, `image`, `weight`).

Server-side handler should look up `session_id` and forward the result
back to the originating user via another `bus.bus._sendone()` call on
that user's session channel.

---

## 2. HTTP endpoints the box requires

| Route | Method | When called | Body | Response |
|---|---|---|---|---|
| `/iot/setup` | POST | first boot + on every device-list change | `{params:{iot_box, devices}}` | `{result: ws_channel_str}` |
| `/iot/log` | POST | every 0.5s if there are pending log lines | streaming text (NOT JSON) — `b"identifier <id><log/>\n<level>,<msg><log/>\n..."` | 200 OK |
| `/iot/keyboard_layouts` | POST | once per boot per scanner/keyboard | form-encoded `available_layouts=<json>` | 200 OK |
| `/iot/box/<id>/display_url` | GET | every 60s while a display device is alive | URL params | `{display_identifier: url, ...}` |
| `/iot/box/send_websocket` | POST | after every action | `{params: {result}}` | 200 OK |
| `/iot/get_handlers` | POST | when `download_iot_handlers()` runs | `{params: {handlers_etag}}` | binary tar OR `{not_modified: true}` |

---

## 3. Models created by Enterprise IoT

### `iot.box` (model, OEEL-1)

```
identifier (char, indexed, unique-ish)
ip (char)
name (char, required)
token (char) — server-issued, used for HTTP auth
version (char)
device_ids (one2many → iot.device)
device_count (integer compute)
ssl_certificate_end_date (datetime)
version_commit_url (html — links to the box's Git commit page)
use_custom_handlers (boolean — opt-in to /iot/get_handlers)
use_lna (boolean — LNA logging for EU)
must_install_fdm_module (boolean — Belgian fiscal data module)
can_be_kiosk (boolean)
company_id (many2one → res.company)
pos_id (many2one → pos.config) ← legacy, prefer associated_pos_config_ids
associated_pos_config_ids (many2many → pos.config) ← from pos_iot
```

**No `state`, no `last_heartbeat`, no `pairing_code`** — Enterprise infers
liveness from action timeouts.

### `iot.device` (model, OEEL-1)

```
name (char)
identifier (char, indexed)
iot_id (many2one → iot.box, required)
type (selection: printer/camera/keyboard/scanner/device/payment/scale/display/fiscal_data_module/unsupported)
connection (selection: network/direct/bluetooth/serial/hdmi)
subtype (selection: receipt_printer/label_printer/office_printer)
connected_status (selection: connected/disconnected)
manufacturer (char)
iot_ip (char) — separate IP for network devices (cameras, IP printers)
display_orientation (selection)
display_url (char)
is_scanner (boolean)
keyboard_layout (many2one → iot.keyboard.layout)
report_ids (many2many → ir.actions.report)        ← bind a printer to default reports!
trigger_ids (one2many → iot.trigger)              ← from mrp_iot
associated_pos_config_ids (many2many → pos.config) ← from pos_iot
```

### `iot.channel` (model, singleton, admin-only)

```python
@api.model
def get_iot_channel(self) -> str:
    """Returns ir.config_parameter['iot.ws_channel'].
    All boxes subscribe here; messages carry iot_identifier for routing."""
```

### `iot.discovered.box` (TransientModel)

```
name (char)
serial_number (char)
pairing_code (char)
add_iot_box_wizard_id (many2one → add.iot.box)
```

Created when the box phones home during `_call_iot_proxy`. The admin
"claims" one via the `add.iot.box` wizard.

### `add.iot.box` (TransientModel — pairing wizard)

```
stage (selection: probably 'select' / 'pair' / 'done')
discovered_box_ids (one2many → iot.discovered.box)
iot_box_to_connect (many2one → iot.discovered.box)
pairing_code (char)
serial_number (char)
token (char)
offline_pairing_token (char) ← KEY: lets you pre-pair a box that has no internet yet
```

### `iot.keyboard.layout` (model)

Stores X11 layouts so the box's keyboard driver UI can offer them as a
dropdown for each detected keyboard / scanner.

### `iot.trigger` (model, from `mrp_iot`)

```
device_id (many2one → iot.device)
workcenter_id (many2one → mrp.workcenter)
key (char) — barcode or button code
sequence (integer)
action (selection — one of 19, see below)
```

Action selection values (drives the workcenter from a physical button or scanner):
`picture` Take Picture · `measure` Take Measure · `SKIP` · `PAUS` Pause ·
`PREV` · `NEXT` · `VALI` Validate · `CLMO` Close MO · `CLWO` Close WO ·
`FINI` Finish · `RECO` Record Production · `CANC` Cancel · `PROP` Print Op ·
`PRSL` Print Delivery Slip · `PRNT` Print Labels · `PACK` · `SCRA` Scrap ·
`pass` · `fail`.

---

## 4. Field extensions on upstream models

| Upstream model | Field | Type | Source module | Purpose |
|---|---|---|---|---|
| `pos.config` | `iot_device_ids` | m2m → iot.device | pos_iot | catch-all device list |
| `pos.config` | `iot_printer_id` | m2o → iot.device | pos_iot | receipt printer |
| `pos.config` | `iot_scale_id` | m2o → iot.device | pos_iot | scale |
| `pos.config` | `iot_display_id` | m2o → iot.device | pos_iot | customer display |
| `pos.config` | `iot_scanner_ids` | **m2m** → iot.device | pos_iot | multiple scanners |
| `pos.config` | `use_iot_box` | boolean | pos_iot | feature toggle |
| `pos.config` | `self_ordering_iot_available_iot_box_ids` | o2m → iot.box | pos_self_order_iot | kiosk-eligible boxes |
| `pos.payment.method` | `iot_device_id` | m2o → iot.device | pos_iot | bind to a payment terminal |
| `pos.printer` | `iot_device_id` | m2o → iot.device | pos_iot | kitchen/bar printer |
| `pos.printer` | `iot_use_lna` | boolean | l10n_eu_iot_scale_cert | LNA logging |
| `mrp.workcenter` | `trigger_ids` | o2m → iot.trigger | mrp_iot | physical button triggers |
| `quality.point` | `device_id` | m2o → iot.device | quality_iot | which device measures |
| `quality.check` | `iot_box_id` | m2o → iot.box | quality_iot | which box ran the check |
| `quality.check.wizard` | `iot_box_id` + `measure` + `picture` + 22 more | various | quality_control_iot | live measurement capture |
| `stock.picking.type` | `iot_scale_ids` | m2m → iot.device | delivery_iot | scales available per operation type |
| `stock.put.in.pack` | `iot_device_id` + `iot_id` + `available_scale_ids` | m2o, m2o, m2m | delivery_iot | weigh-in-pack workflow |
| `ir.actions.report` | `device_ids` | m2m → iot.device | iot | bind a report to default printers |
| `res.config.settings` | `pos_iot_*` (mirror) + `module_pos_iot_six` + `module_pos_iot_worldline` | various | pos_iot | settings UI + install toggles |

---

## 5. Kitchen Display System (KDS) models

KDS is **not an IoT integration** — it's a standalone tablet web view.
But it lives next to IoT and shares some UX patterns:

| Model | Purpose |
|---|---|
| `pos.prep.display` | One row per kitchen-station tablet. Has `name`, `pos_config_ids` (m2m), `category_ids` (m2m), `stage_ids` (o2m), `auto_clear`, `clear_time_interval`, `average_time`, `access_token` (URL-based auth, no login) |
| `pos.prep.order` | Orders that appear on the display |
| `pos.prep.line` | Order lines |
| `pos.prep.stage` | Stages: in-progress / ready / served |
| `restaurant.order.course` | Multi-course meals |
| `restaurant.table` | Tables (from `pos_restaurant`) |
| `pos.preparation.display.reset.wizard` | Admin reset (from `pos_enterprise`) |
| `preparation.time.report` | Avg prep time analytics |

The KDS tablet hits `/pos-preparation-display/<id>?access_token=...` — no
session, no login. This URL pattern is what we need to replicate.

---

## 6. Discovery + UI flow

| Action | Mechanism |
|---|---|
| Box pairing UX | `ir.actions.client` `discover_iot_boxes` (JS-driven, runs on the user's browser, scans the LAN) |
| Bulk-clear linked devices | `ir.actions.client` `iot_delete_linked_devices_action` |
| Download box image | `ir.actions.act_url` → `https://nightly.odoo.com/master/iotbox/iotbox-latest.zip` |
| Download Windows IoT (virtual) | `ir.actions.act_url` → `https://nightly.odoo.com/19.0/nightly/iot/odoo_19.0.latest.exe` |

---

## 7. Notes for filamind-iot implementers

1. The box's `WebsocketClient` starts a session-cookie request with
   `/web/login?db=<db>` **only if `db_name` is set in odoo.conf**. Our
   pair endpoint must therefore return `db_name` so the box can save it
   (we currently don't — bug to fix).
2. When the box has no `db_name`, it skips the cookie and still tries
   the WebSocket. This works for purely-public bus channels but not for
   anything authenticated.
3. Returning the channel string from `/iot/setup` is the **only** route
   the box trusts to learn its WS channel — there is no second mechanism.
4. The box's `_get_changes_to_send` only fires on the **second** loop
   tick after a device is detected (it diffs against `previous_*` dicts
   that are set by itself). So expect a 3-6 s latency between physical
   plug-in and the device appearing in `iot.device`.
5. USB device identifiers can shift across reboots
   (`usb_VID:PID_<counter>` — counter resets). For stable PKs prefer MAC
   or serial. We already do this with `IOT_IDENTIFIER` for boxes; we
   need the same for devices (use vendor serial when present).
