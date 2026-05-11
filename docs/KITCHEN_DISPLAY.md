# `filamind_kitchen_display` — Design

> Replacement for the Enterprise `pos_restaurant_preparation_display`
> family of modules. Tablet-first web view that shows kitchen tickets
> in real time. **No IoT box required for the display itself**, but it
> can optionally drive an IoT-attached kitchen printer.

---

## 1. What we're modelling (mirrors Enterprise)

| Our model | Enterprise equivalent | Purpose |
|---|---|---|
| `filamind.kitchen.display` | `pos.prep.display` | One row per kitchen-station tablet |
| `filamind.kitchen.order` | `pos.prep.order` | An order shown on a display |
| `filamind.kitchen.line` | `pos.prep.line` | Line item (product, qty, notes) |
| `filamind.kitchen.stage` | `pos.prep.stage` | Workflow stage (in-progress / ready / served) |
| `filamind.kitchen.course` | `restaurant.order.course` | Multi-course meal grouping |

A `pos.config` can be linked to N displays via
`pos.config.filamind_kitchen_display_ids` (m2m).

---

## 2. Data shape

### `filamind.kitchen.display`

```
name (char, required)              "Kitchen #1", "Bar"
pos_config_ids (m2m → pos.config)
category_ids (m2m → pos.category)  filter — only show items from these
stage_ids (one2many → filamind.kitchen.stage)
auto_clear (boolean, default True)
clear_after_seconds (integer, default 300)
average_time (integer, computed)
order_count (integer, computed)
access_token (char, indexed, copy=False)  used in public URL
company_id (m2o → res.company)
```

### `filamind.kitchen.stage`

```
display_id (m2o → filamind.kitchen.display, required)
name (char)                        "In Progress", "Ready", "Served"
sequence (integer)
color (integer)                    kanban color
auto_advance_seconds (integer)     auto-advance after N s (optional)
```

### `filamind.kitchen.order`

```
display_id (m2o → filamind.kitchen.display, required)
pos_order_id (m2o → pos.order, required)
stage_id (m2o → filamind.kitchen.stage, required)
fired_date (datetime)
completed_date (datetime)
completion_seconds (integer, computed)
course_id (m2o → filamind.kitchen.course)
table_number (integer, related → pos.order.table_id.table_number)
internal_note (text)
customer_note (text)
line_ids (one2many → filamind.kitchen.line)
```

### `filamind.kitchen.line`

```
order_id (m2o → filamind.kitchen.order, required)
pos_order_line_id (m2o → pos.order.line)
product_id (m2o → product.product)
qty (float)
note (char)                        "no salt", "well done"
modifier_ids (m2m → product.product) toppings/options
state (selection: pending/preparing/ready/served)
```

### `filamind.kitchen.course`

Pure structural grouping for multi-course meals. Same fields as
`restaurant.order.course`.

---

## 3. URL routes

### Public (no login)

```
GET  /filamind_kitchen/<int:display_id>?access_token=<tok>
     → OWL single-page app, periodic bus.bus subscribe
```

The display tablet bookmarks this URL. `access_token` is a 32-char
random string stored on the display record. Rotating the token
immediately revokes access.

### Internal (auth=user)

```
POST /filamind_kitchen/regenerate_token/<int:display_id>
     → admin button to rotate the token (and invalidate any active tablet)

POST /filamind_kitchen/orders/transition
     → from the tablet UI: move an order from one stage to the next
     body: {order_id, target_stage_id, access_token}
```

---

## 4. Data flow

```
Cashier validates a POS order
        │
        ▼
   pos.order.action_paid()      (existing Odoo behavior)
        │
        ▼
   filamind.kitchen.display._on_pos_order_paid(order)
        │   for each display where pos_config matches:
        │   - filter lines by category_ids
        │   - create filamind.kitchen.order + lines
        │   - if pos.printer.iot_device_id is set, also push print job
        │
        ▼
   bus.bus._sendone(
       f'kitchen_display_{display.id}',
       'new_order',
       {order_id, order_data})
        │
        ▼
   tablet's OWL component subscribed to that channel adds the order to
   the "in progress" column

Cook drags order to "ready":
        │
        ▼
   POST /filamind_kitchen/orders/transition
        │
        ▼
   bus.bus._sendone(...)        ← all other tablets subscribed to the
                                   same display see the move
```

---

## 5. UI components (frontend)

OWL components in `addons/filamind_kitchen_display/static/src/`:

```
src/
├── kitchen_display.js        root component, subscribes to bus channel
├── kitchen_display.xml       template: header + columns + footer
├── kitchen_display.scss
├── stage_column.js           one column per stage, kanban-style
├── stage_column.xml
├── order_card.js             single order with lines
├── order_card.xml
└── order_card.scss
```

The tablet should work offline (after first load) and resync when
connection returns. Use `localforage` or similar for queue.

---

## 6. Admin views

`addons/filamind_kitchen_display/views/`:

```
filamind_kitchen_display_views.xml       list/form/kanban for displays
filamind_kitchen_stage_views.xml         editable stages on form
filamind_kitchen_order_views.xml         search-only (read-only data)
filamind_kitchen_menus.xml               under "POS → Kitchen Displays"
```

Display form has a "Open Display" button that opens the public URL in a
new tab — handy for setup.

---

## 7. Integration with `pos_iot` printer

If `pos.config.iot_printer_id` (or our new `pos.printer.iot_device_id`)
is set on a config that's wired to a kitchen display, the
`_on_pos_order_paid` hook should ALSO send a `iot_action` to that
printer with a kitchen-ticket-formatted body (different layout from the
customer receipt — bigger fonts, no totals).

---

## 8. Things to deliberately keep simple (vs Enterprise)

| Enterprise | Us |
|---|---|
| Per-stage colour pickers | We pick 3 sensible colours in CSS |
| Course timing analytics | Phase 2 |
| Per-table summary view | Phase 2 |
| Floor-plan overlay | Out of scope |
| Multi-language menu translation | Out of scope (uses POS product translations) |

---

## 9. Acceptance test plan

1. Create a POS config "Test POS" + one display "Kitchen #1"
2. Link them via `filamind_kitchen_display_ids`
3. Open the public URL on a second browser tab
4. Validate an order from the POS UI
5. Within 1 second, the order appears in the "In Progress" column
6. Drag to "Ready" — the order moves on a third browser too (3-way real-time)
7. After `clear_after_seconds`, served orders are auto-cleared
8. Rotate the access token — all open tablets are evicted on next bus heartbeat

---

## 10. Effort estimate

| Sub-task | Hours |
|---|---|
| Models + access control | 2 |
| `_on_pos_order_paid` hook + tests | 2 |
| Backend views + menus | 2 |
| OWL frontend (display + columns + cards) | 4 |
| Public route + access_token plumbing | 2 |
| Bus subscription + live updates | 2 |
| Optional kitchen printer ticket format | 1 |
| Documentation + screenshots | 1 |

**Total: ~16 hours**.
