# filamind-iot

Self-hosted **IoT gateway suite for Odoo 19**, designed to pair with the
[**filamind-iotbox**](https://github.com/filamind-app/filamind-iotbox)
Raspberry Pi image. An independent alternative to Odoo Enterprise's stock
`iot`, `pos_iot`, etc. — no `iot-proxy.odoo.com` involved.

> Built on top of, but independent of, Odoo. Released under LGPL-3 to match
> upstream Odoo's license.

---

## The four addons

This monorepo ships four sibling Odoo addons. Install only what you need.

| Addon | Depends on | Purpose |
|---|---|---|
| **`filamind_iot`** | base, mail, web, bus | Core: box+device+command models, `/iot/setup`, `/iot/box/*` HTTP endpoints, bus-based bidirectional flow, pairing wizard |
| **`filamind_pos_iot`** | filamind_iot, point_of_sale | Per-pos.config IoT device fields (printer, scale, scanner, customer display, cash drawer), payment-terminal binding, server-side receipt printing |
| **`filamind_stock_iot`** | filamind_iot, stock | Per-warehouse defaults (label printer, scale, scanner), `print_iot_label` and `iot_weigh` actions on stock.picking |
| **`filamind_mrp_iot`** | filamind_iot, mrp | Per-workcenter defaults (label printer, caliper, scanner), capture measurement + print label actions on mrp.workorder |

```
            ┌─────────────────────────┐
            │     filamind_iot        │  ← core (box, device, bus, queue)
            └────────────┬────────────┘
                         │ extended by
            ┌────────────┼────────────┐
            ▼            ▼            ▼
   filamind_pos_iot  filamind_stock_iot  filamind_mrp_iot
        (POS)          (Inventory)       (Manufacturing)
```

Every business addon adds Many2one fields to its core record (`pos.config`,
`stock.warehouse`, `mrp.workcenter`) and exposes test buttons that call into
`iot.box.send_bus_message(method, payload, device, timeout)` from the
`filamind_iot` core.

---

## What's inside `filamind_iot`

| Component | Purpose |
|---|---|
| `iot.box` | The gateway record (pairing code, token, heartbeat, state, **WS channel**) |
| `iot.device` | A peripheral attached to a box (printer, scale, scanner, …) |
| `iot.device.type` | Catalog of device categories (12 preloaded) |
| `iot.connection.log` | Audit trail of pairing, heartbeats, device events |
| `iot.command.queue` | **Outgoing commands** sent via bus, plus round-trip results |
| `iot.pairing.wizard` | Dual-mode pairing wizard |

### Bidirectional command flow

```
  Server (Odoo)                            Box (filamind-iotbox)
  ─────────────                            ─────────────────────
  /iot/setup       ◄── POST {iot_box, devices} ── _send_all_devices()
  ws_channel  ── return string ──────────────────►  stores ws_channel
                                                       │
                                                       ▼
                                                 opens wss://<host>/websocket
                                                 subscribes to ws_channel
                                                       │
  iot.box.send_bus_message()                           ▼
       │                                         on_message →
       ▼                                           communication.handle_message
  bus.bus._sendone(channel, type, payload) ─►      dispatches to driver
                                                       │
                                                       ▼ (action result)
  /iot/box/send_websocket ◄── POST {result} ── send_to_controller()
       │
       ▼
  iot.command.queue.record_response()
  state: sent → completed / failed
```

The public API is `iot.box.send_bus_message(method, payload, device, timeout)`.
The **Test Connection** button (on the box form) and **Test Print** button
(on printer-type device forms) are reference implementations.

### HTTP endpoints

Every endpoint is registered under **two paths** — the canonical
`/filamind_iot/<action>` and an `/iot/box/<action>` alias that matches the
path scheme used by the **filamind-iotbox** image (and by the upstream Odoo
IoT Box's `send_to_controller` helper). Both work; pick whichever your client
prefers.

| Action | Method | Authentication |
|---|---|---|
| `/filamind_iot/pair` , `/iot/box/pair` | POST | pairing code (one-time) |
| `/filamind_iot/heartbeat` , `/iot/box/heartbeat` | POST | identifier + token |
| `/filamind_iot/devices` , `/iot/box/devices` , `/iot/box/send_devices` | POST | identifier + token |
| `/filamind_iot/device_status` , `/iot/box/device_status` , `/iot/box/send_websocket` | POST | identifier + token |

`auth='public'` because IoT boxes don't carry user credentials. Every endpoint
authenticates via per-box token issued at pairing time.

### Pairing flows

The wizard supports two complementary flows:

1. **Server-code mode** *(matches the filamind-iotbox v0.2.0+ Server URL tab)*
   - Admin clicks **Connect IoT Box** in Odoo
   - Odoo generates an 8-char code, valid for `filamind_iot.pairing_ttl`
     minutes (default 15)
   - User enters the code on the box's **Server URL** tab along with the URL
   - Box `POST`s `{code, identifier, ip_address, mac_address, hostname}` to
     `/filamind_iot/pair` and gets back a permanent token
2. **Box-token mode**
   - Box displays a token on its HDMI output at boot
   - User types it into Odoo's wizard
   - Odoo creates the box record and marks it connected immediately
   - Box later authenticates with the same token

---

## Installation

### Requirements

- Odoo 19 (or `saas-19.x`)
- PostgreSQL 13+
- Python 3.11+

### Drop-in addon path

```bash
git clone https://github.com/filamind-app/filamind-iot \
    /opt/odoo/custom-addons/filamind-iot
```

Then in `odoo.conf`:

```ini
addons_path = /opt/odoo/addons,/opt/odoo/custom-addons/filamind-iot
```

Restart Odoo, install the **Filamind IoT** app from the apps screen.

### Configuration

Open **IoT → Configuration → Settings** and adjust:

| Setting | Default | Effect |
|---|---|---|
| Pairing code validity | 15 min | TTL for the one-time pairing code |
| Heartbeat interval | 60 s | Expected ping interval from a box |
| Require HTTPS | True | Reject pairing over plain HTTP (advisory only — enforce at your reverse proxy) |
| Auto-discover devices | True | Auto-create `iot.device` records when a box reports a new device |
| Log retention | 90 days | Daily cron purges older `iot.connection.log` rows |
| Allow remote control | True | Reserved for future bidirectional command flow |
| Notify on disconnect | True | Reserved for future activity flow |

---

## Compatibility with the filamind-iotbox image

| filamind-iotbox version | This addon |
|---|---|
| ≤ v0.1.0 (URL-only) | URL is saved; box can't fully authenticate without a token. Use **Box-token mode** in the wizard or re-flash with v0.2.0+. |
| **v0.2.0+ (URL + Pairing Code)** | Full flow: enter URL + pairing-code on the box, server issues token, heartbeat begins. |

The `/iot/box/<action>` aliases mean an unmodified IoT Box that calls the
upstream paths still works at the heartbeat/device-reporting level, but
without the WebSocket-based bidirectional command flow that upstream Odoo
implements. Bidirectional flow (sending print jobs, scale reads, etc. *from*
Odoo *to* the box) is on the roadmap.

---

## Repo layout

```
filamind-iot/
├── filamind_iot/                  # core addon
│   ├── controllers/iot_controller.py
│   ├── data/                      # cron + sequences + 12 device types
│   ├── models/                    # box, device, type, log, queue, settings
│   ├── security/                  # ACLs + multi-company rules
│   ├── static/                    # banner, icon, CSS
│   ├── views/                     # kanban+list+form+search+menus
│   └── wizard/                    # iot.pairing.wizard (dual-mode)
├── filamind_pos_iot/              # POS integration
│   ├── models/                    # pos.config, pos.session, pos.payment.method
│   └── views/
├── filamind_stock_iot/            # Inventory integration
│   ├── models/                    # stock.warehouse, stock.picking
│   └── views/
├── filamind_mrp_iot/              # Manufacturing integration
│   ├── models/                    # mrp.workcenter, mrp.workorder
│   └── views/
├── .github/workflows/ci.yml       # ruff + py_compile + XML + manifest
├── CHANGELOG.md
├── LICENSE                        # LGPL-3.0
└── README.md
```

---

## Development

### Run lint locally

```bash
pip install ruff
ruff check filamind_iot/
python -m py_compile $(find filamind_iot -name '*.py')
```

### Validate XML

```bash
for f in filamind_iot/**/*.xml; do
    python -c "import xml.etree.ElementTree as ET; ET.parse('$f')"
done
```

### Run inside a fresh Odoo

```bash
docker run -p 8069:8069 -v $(pwd)/filamind_iot:/mnt/extra-addons/filamind_iot \
    odoo:19 -- -d filamind_test -i filamind_iot --stop-after-init
```

---

## License

LGPL-3.0-or-later — same as upstream Odoo.
