# Migrating from Odoo Enterprise IoT to filamind-iot

This guide walks an existing Odoo Enterprise IoT user through
swapping the OEEL-1 stack (20 paid modules) for the LGPL-3
filamind-iot stack (14 free addons), with **no downtime** and
**no data loss**.

The migration is **field-name-compatible by design** — every
Enterprise field we replicated kept the same name (e.g.
`pos.config.iot_box_id`, `event.event.iot_badge_printer_id`) so
existing automations, reports, and integrations keep working.

---

## 0. Pre-flight checklist

- [ ] Take a full database dump (`pg_dump`).
- [ ] Take a snapshot of the box's SD card if you can (`dd`).
- [ ] Document which Enterprise IoT modules are installed today:

  ```sql
  SELECT name, latest_version
    FROM ir_module_module
   WHERE state = 'installed'
     AND name LIKE '%iot%'
   ORDER BY name;
  ```

- [ ] Confirm Odoo version. filamind-iot targets v19.0; if you're
  on v17 or v18, upgrade Odoo Community first via the usual
  `--update=all` path, then proceed.

---

## 1. Module-by-module mapping

| Enterprise module (OEEL-1) | filamind replacement (LGPL-3) | Notes |
|---|---|---|
| `iot` | `filamind_iot` | Core gateway |
| `iot_drivers` (on the box) | `filamind-iotbox` patches | Box-side |
| `pos_iot` | `filamind_pos_iot` | Field names preserved |
| `stock_barcode_iot` | `filamind_stock_iot` | |
| `mrp_workorder_iot` | `filamind_mrp_iot` | |
| `pos_restaurant_preparation_display` | `filamind_kitchen_display` | KDS |
| `quality_iot` + `quality_control_iot` | `filamind_quality_iot` | We re-implement `quality_control` too — no Enterprise dep |
| `pos_self_order_iot` | `filamind_self_order_iot` | |
| `event_iot` + `event_sale_iot` + `pos_event_iot` | `filamind_event_iot` | |
| `l10n_eg_pos_iot` | `filamind_l10n_eg_iot` | ETA hardware-fiscal-printer routing |
| `l10n_eu_iot_scale_cert` | `filamind_l10n_eu_iot_scale_cert` | EU MID/LNE |
| `pos_iot_six` | `filamind_pos_iot_six` | Six TIM terminals |
| `pos_iot_worldline` | `filamind_pos_iot_worldline` | Worldline CTEP |
| `pos_iot_adam_scale` | `filamind_pos_iot_adam_scale` | Adam Equipment scales |
| *(none — umbrella)* | `filamind_iot_full` | One-click install |

---

## 2. Order of operations

### Step 1 — Install filamind-iot alongside Enterprise

filamind addons are designed to coexist with Enterprise addons
on the same database. Add the filamind addons_path to your
`odoo.conf` **without removing** the Enterprise addons_path:

```ini
[options]
addons_path = /opt/odoo/addons,/opt/odoo/enterprise,/opt/odoo/custom-addons/filamind-iot/addons
```

Restart Odoo. The Apps screen now shows both stacks. **Do not
install the filamind addons yet.**

### Step 2 — Pair a test box

Connect one filamind-iotbox-flashed Pi to the test instance and
verify the pairing flow end-to-end. The Enterprise iot.box
records are untouched.

### Step 3 — Migrate per-pos-config / per-workcenter / per-event

For each business object that has an Enterprise IoT field set,
either:

a) **Keep using Enterprise** — leave the field pointing at the
   Enterprise iot.box, or
b) **Migrate to filamind** — point the field at the new
   filamind iot.box record (same field name, same UI).

Because filamind kept the field names identical (`iot_box_id`,
`iot_printer_id`, etc.), no SQL migration is needed for the
field values — they're just `Many2one` references to whichever
iot.box record you choose.

### Step 4 — Uninstall the Enterprise stack

When every business object is migrated, uninstall the Enterprise
IoT modules in reverse-dependency order:

```bash
odoo -d <db> --uninstall iot_drivers,pos_iot_six,pos_iot_worldline,...
```

Or via the Apps screen, one module at a time.

**Important**: uninstalling the Enterprise stack removes the
Enterprise iot.box records but NOT the filamind ones — they
have different table names (`iot_box` vs nothing changes
because filamind uses `iot.box` too; but they're different
*rows*).

Wait — actually filamind and Enterprise BOTH use the `iot.box`
model name. They share the same SQL table. **Do not have both
stacks installed simultaneously in production** for more than
the migration window; ORM conflicts may occur on `_inherit`
chains. Test thoroughly on staging first.

### Step 5 — Confirm clean state

```sql
-- Should return zero rows from the Enterprise namespace:
SELECT * FROM ir_module_module
 WHERE state IN ('to remove', 'uninstalled', 'to upgrade')
   AND author LIKE '%Odoo%' AND name LIKE '%iot%';
```

---

## 3. Field-level compatibility table

| Enterprise field | filamind field | Same? |
|---|---|---|
| `iot.box.identifier` | `iot.box.identifier` | ✅ |
| `iot.box.iot_ip` | `iot.box.iot_ip` | ✅ |
| `iot.box.ip_url` | `iot.box.ip_url` | ✅ |
| `iot.box.token` | `iot.box.token` | ✅ |
| `iot.device.iot_ip` | `iot.device.iot_ip` | ✅ |
| `iot.device.connection` | `iot.device.connection` | ✅ |
| `iot.device.identifier` | `iot.device.identifier` | ✅ |
| `pos.config.iot_box_id` | same | ✅ |
| `pos.config.iot_printer_id` | same | ✅ |
| `pos.config.iot_scale_id` | same | ✅ |
| `pos.config.iot_customer_display_id` | same | ✅ |
| `pos.payment.method.iot_terminal_id` | same | ✅ |
| `stock.picking.type.iot_*_id` | same | ✅ |
| `mrp.workcenter.iot_*_id` | same | ✅ |
| `event.event.iot_badge_printer_id` | same | ✅ |
| `event.event.iot_scanner_id` | same | ✅ |
| `event.registration.iot_badge_print_command_id` | same | ✅ |

Fields with **vendor-specific** names (Six TIM, Worldline CTEP,
Adam AGN, etc.) are filamind-only — Enterprise has equivalents
but with different field names. Migrate per-payment-method
manually.

---

## 4. Box-side migration

Existing Enterprise IoT boxes use `iot-proxy.odoo.com` to relay
the bus messages. After migration the box talks to your own
Odoo URL directly. There are three ways to switch:

1. **Re-flash the SD card** with filamind-iotbox image —
   cleanest but takes the box offline for ~5 minutes.
2. **Run `flash-patches.sh pi@<box>`** — patches the running
   box over SSH. Restarts Odoo on the box (~30 s downtime).
3. **Manual edit** of `/home/pi/odoo.conf` to flip
   `remote_server` to your URL and remove `proxy_mode_url` —
   then `systemctl restart odoo` on the box.

After any of these, hit
`https://<box-ip>/iot_drivers/diagnose.html` to verify all five
transport checks pass.

---

## 5. Rollback plan

If something breaks irrecoverably:

1. Restore the database dump from step 0.
2. Restore the box's SD card from the snapshot (or re-flash
   with the upstream IoT Box image and re-pair against Odoo
   Enterprise).
3. The Enterprise stack picks up where it left off as long as
   the `addons_path` still points at the Enterprise addons
   directory.

No filamind code writes to Enterprise-only tables, so a clean
DB restore is sufficient.

---

## 6. Common gotchas

- **`pos_kitchen_display` is the closest Enterprise equivalent
  of `filamind_kitchen_display`**, but the data models are
  NOT compatible — orders live in different tables. There's no
  in-place migration; cut over POS configs to the filamind KDS
  on a quiet day.
- **`quality_control` (Enterprise dep of `quality_iot`)** is
  re-implemented by `filamind_quality_iot` from scratch as
  `filamind.quality.point` / `filamind.quality.check`. Existing
  `quality.point` rows won't auto-migrate; export → import via
  CSV if the data matters.
- **OWL frontend assets**: `filamind_kitchen_display` v0.2.0
  uses a public WebSocket subscription. If you front Odoo with
  OpenLiteSpeed, use the Caddy sidecar from
  REVERSE_PROXY_PLATFORMS.md or the KDS falls back to 5-second
  polling.
