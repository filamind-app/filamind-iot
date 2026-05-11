# Installation guide for filamind-iot

This guide covers installing **filamind-iot** (the server-side
addons) on a fresh or existing Odoo deployment, plus the matching
[filamind-iotbox](https://github.com/filamind-app/filamind-iotbox)
patches on a Raspberry Pi.

For per-platform reverse-proxy setup, see
[REVERSE_PROXY_PLATFORMS.md](REVERSE_PROXY_PLATFORMS.md).

---

## 1. Server-side install (Odoo)

### Requirements

- Odoo 19.0 (or `saas-19.x`) — Community Edition is enough; no
  Enterprise subscription needed.
- PostgreSQL 13 or newer.
- Python 3.11+.
- A reverse proxy in front of Odoo (nginx / Caddy / Apache /
  Traefik / HAProxy) — see REVERSE_PROXY_PLATFORMS.md.

### Drop-in addon path — choose either method

**Method A — release zip (recommended for production):**

```bash
# Pick the latest version from
#   https://github.com/filamind-app/filamind-iot/releases
curl -fsSLO https://github.com/filamind-app/filamind-iot/releases/download/v1.1.0/filamind-iot-v1.1.0.zip
curl -fsSLO https://github.com/filamind-app/filamind-iot/releases/download/v1.1.0/filamind-iot-v1.1.0.zip.sha256
sha256sum -c filamind-iot-v1.1.0.zip.sha256
mkdir -p /opt/odoo/custom-addons/filamind-iot/addons
unzip filamind-iot-v1.1.0.zip -d /opt/odoo/custom-addons/filamind-iot/addons/
```

**Method B — git clone (for tracking main / dev work):**

```bash
git clone https://github.com/filamind-app/filamind-iot \
    /opt/odoo/custom-addons/filamind-iot
```

Either way, in `odoo.conf` point the `addons_path` at the
`addons/` directory:

```ini
[options]
addons_path = /opt/odoo/addons,/opt/odoo/custom-addons/filamind-iot/addons
proxy_mode  = True
gevent_port = 8072
```

`proxy_mode` and `gevent_port` are required for WebSocket to work
behind any reverse proxy. Restart Odoo:

```bash
sudo systemctl restart odoo
```

### Install the umbrella from the Apps screen

1. Log in as admin → **Apps**.
2. Remove the default `Apps` filter, search for `filamind`.
3. Click **Install** on **Filamind IoT — Full Suite**
   (`filamind_iot_full`). This pulls every dependent addon
   automatically.

To install only a subset (e.g. POS without the kitchen display):

| Goal | Install | Pulls in |
|---|---|---|
| Just the gateway | `filamind_iot` | base, mail, web, bus |
| POS device wiring | `filamind_pos_iot` | + point_of_sale, pos_restaurant |
| Inventory IoT | `filamind_stock_iot` | + stock |
| Manufacturing IoT | `filamind_mrp_iot` | + mrp |
| Restaurant KDS | `filamind_kitchen_display` | + point_of_sale, pos_restaurant |
| Quality control | `filamind_quality_iot` | + product, mrp |
| Self-order kiosks | `filamind_self_order_iot` | + pos_self_order |
| Event badges | `filamind_event_iot` | + event |
| Egyptian fiscal | `filamind_l10n_eg_iot` | + l10n_eg |
| EU MID/LNE | `filamind_l10n_eu_iot_scale_cert` | (no extra) |
| Six terminals | `filamind_pos_iot_six` | (no extra) |
| Worldline terminals | `filamind_pos_iot_worldline` | (no extra) |
| Adam scales | `filamind_pos_iot_adam_scale` | (no extra) |

### Per-platform notes

- **CyberPanel / OpenLiteSpeed**: requires the Caddy sidecar
  workaround for WebSocket — see
  [REVERSE_PROXY_PLATFORMS.md](REVERSE_PROXY_PLATFORMS.md#openlitespeed--cyberpanel--known-broken-use-caddy-sidecar).
- **aaPanel**: works with the vanilla nginx recipe.
- **Plesk / cPanel**: enable `mod_proxy_wstunnel` (Apache) or paste
  the nginx snippet (nginx mode).
- **Containers**: works with any Odoo 19 image (official
  `odoo:19`, OCA images, custom builds) as long as the
  container exposes port 8072 and `odoo.conf` has
  `proxy_mode = True` + `gevent_port = 8072`. Mount the
  unzipped `addons/` directory into the container's
  `addons_path`.

---

## 2. Box-side install (Raspberry Pi)

### Option A — flash a pre-built image (recommended)

The
[filamind-iotbox releases page](https://github.com/filamind-app/filamind-iotbox/releases)
hosts pre-built `.img` files for Raspberry Pi 3B/3B+/4. Flash
with **Raspberry Pi Imager**, **Etcher**, or `dd`:

```bash
# Linux / macOS / WSL2
xzcat iotbox-filamind-2026.05.10.img.xz \
    | sudo dd of=/dev/sdX bs=4M status=progress conv=fsync
```

Boot the Pi, wait for HDMI to show the box's IP. Then visit
`https://<box-ip>` in a browser, click **Configure server**,
enter the URL of your Odoo server, and pair.

### Option B — patch a running upstream IoT Box (no re-flash)

If the box already runs a stock Odoo IoT Box image and you don't
want to re-flash:

```bash
git clone https://github.com/filamind-app/filamind-iotbox
cd filamind-iotbox
./scripts/flash-patches.sh pi@<box-ip>
```

The script SSHes into the box, backs up every file it modifies
(`.filamind-backup`), applies the patches, and restarts Odoo.
Roll back by restoring the `.filamind-backup` files.

### Option C — build your own image

```bash
sudo ./scripts/build-image.sh                # downloads latest upstream
# OR
sudo ./scripts/build-image.sh /path/to/upstream-iotbox.img
sudo ./scripts/verify-image.sh build/iotbox-filamind-*.img
```

Output is in `build/`. Flash as in option A.

---

## 3. First-boot pairing

Once both server and box are up:

1. **Server**: log in as admin → **IoT** → **Connect a Box**.
   Note the 8-character pairing code.
2. **Box**: open `https://<box-ip>` in a browser, go to the
   **Server URL** tab, paste the Odoo URL and the pairing code,
   click **Connect**.
3. The box opens a WebSocket back to the server (or falls back
   to long-poll / short-poll automatically), the server marks
   the box `connected`, and the device list in the IoT app
   populates within ~30 s.

If anything fails, hit
`https://<box-ip>/iot_drivers/diagnose.html` for the 5-step
self-diagnose page (red/green badges per transport check).

---

## 4. Verifying the install

```bash
# Server-side: confirm every filamind module is installed
psql -U odoo filamind_db -c \
    "SELECT name, state FROM ir_module_module WHERE name LIKE 'filamind%';"

# Box-side: dump the full status report
ssh pi@<box-ip> filamind-status
```

Both commands are safe to paste output from into a support
ticket — they don't leak credentials, secrets, or PAN data.
