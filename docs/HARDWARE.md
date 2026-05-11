# Hardware compatibility for filamind-iot

This document tracks which physical devices have been validated
end-to-end. **A row appearing here means a real device of that
exact model has been observed working with filamind-iot ≥ v1.0.0
and filamind-iotbox ≥ v0.5.0** — no guesses, no "probably works"
inferences from datasheets.

To add a row, run the device through the
[mock-then-real workflow](../tests/hil/README.md), then open a PR
with a one-line entry below.

---

## Receipt printers

| Vendor | Model | Connection | Driver | Status | Notes |
|---|---|---|---|---|---|
| Epson | TM-T20 III | USB | upstream ESC/POS | ⏳ untested | should work; standard ESC/POS |
| Epson | TM-T88 V/VI | USB / Ethernet | upstream ESC/POS | ⏳ untested | |
| Star | TSP143III | USB / Ethernet | upstream ESC/POS | ⏳ untested | |
| Bixolon | SRP-330 II | USB | upstream ESC/POS | ⏳ untested | |

---

## Label printers

| Vendor | Model | Connection | Driver | Status | Notes |
|---|---|---|---|---|---|
| Zebra | GK420t | USB | upstream ESC/ZPL | ⏳ untested | |
| Zebra | ZD220 / ZD230 | USB | upstream ESC/ZPL | ⏳ untested | |
| Brother | QL-820NWB | USB / WiFi | upstream Brother | ⏳ untested | |
| Dymo | LabelWriter 450 | USB | upstream Dymo | ⏳ untested | |

---

## Barcode scanners

Any HID-class USB scanner works (the box treats it as a keyboard
emitting rapid keystrokes). No driver needed, just set
`is_scanner=True` on the iot.device.

| Vendor | Model | Notes |
|---|---|---|
| Honeywell | Voyager 1200g / 1450g | ⏳ untested but standard HID |
| Datalogic | QuickScan QD2430 | ⏳ untested but standard HID |
| Zebra | DS2208 | ⏳ untested but standard HID |

For 2D scanners (QR / DataMatrix / PDF417), make sure the
keyboard layout matches the OS layout on the box (US English by
default; configurable per-device via `keyboard_layout`).

---

## Scales

| Vendor | Model | Family | Connection | Driver | Status |
|---|---|---|---|---|---|
| Adam Equipment | CPWplus 6 / 15 / 35 | `cpwplus` | USB-Serial (FTDI) | `filamind_adam_driver` | ⏳ untested |
| Adam Equipment | GFK 75 / 150 | `gfk_gbk` | USB-Serial | `filamind_adam_driver` | ⏳ untested |
| Adam Equipment | GBK 30 / 60 | `gfk_gbk` | USB-Serial | `filamind_adam_driver` | ⏳ untested |
| Mettler Toledo | ARIVA / Ariva-S | OIML  | RS-232 | upstream Mettler | ⏳ untested |
| OHAUS | Ranger 3000 | OIML | USB-Serial | upstream OHAUS | ⏳ untested |

For EU "legal-for-trade" use, the scale **must** carry an EU MID
Module B certificate from a notified body — record the
certificate number on the iot.device via the
`filamind_l10n_eu_iot_scale_cert` addon.

---

## Payment terminals

| Vendor | Model | Protocol | Driver | Status | Notes |
|---|---|---|---|---|---|
| Six (Worldline) | Yomani XR | TIM Direct | `filamind_six_driver` | ⏳ stub | TIM framing TODO |
| Six (Worldline) | Yoximo | TIM Cloud | `filamind_six_driver` | ⏳ stub | HTTPS framing TODO |
| Worldline | Yomani XR | CTEP | `filamind_worldline_driver` | ⏳ stub | CTEP framing TODO |
| Worldline | Move/2500 | CTEP | `filamind_worldline_driver` | ⏳ stub | CTEP framing TODO |
| Adyen | TAP / V400m | TerminalAPI | upstream `pos_adyen` | ⏳ untested | use Adyen's existing addon |
| Stripe | BBPOS WisePOS E | StripeTerminal | upstream `pos_stripe` | ⏳ untested | use Stripe's existing addon |

**Critical**: the full PAN must NEVER be stored. Our drivers
explicitly capture only `card_last4` plus EMV TVR/TSI for
chargeback defense. PCI-DSS scope stays at the terminal.

---

## Egyptian fiscal printers

| Vendor | Model | Driver | Status |
|---|---|---|---|
| Sunmi | V2 fiscal (T2 Mini fiscal variant) | `filamind_eg_fiscal_driver` | ⏳ stub |
| Aures | Yuno fiscal | `filamind_eg_fiscal_driver` | ⏳ stub |
| Bematech | MP-4200 TH-FI | `filamind_eg_fiscal_driver` | ⏳ stub |

The driver speaks ESC/POS with ETA-specific extensions
(`ESC i`, `ESC I`, `ESC ? u`, `ESC ? q`). Vendor-specific
deviations from the canonical sequences are TODO — fork the
driver and override `_query()` for non-Sunmi vendors.

---

## HDMI / customer displays

| Type | Notes |
|---|---|
| Standard HDMI display | Works as a `customer_display` device. Set `display_url` on the iot.device to the page the box should render full-screen. |
| VFD pole displays (USB) | Use the upstream `customer_display` driver — no filamind-specific driver needed. |

---

## Cash drawers

| Connection | Driver | Notes |
|---|---|---|
| Triggered via printer kick (RJ-11) | upstream ESC/POS | Most common. `iot_cash_drawer_id` doesn't need to be set; the printer handles it. |
| Standalone USB cash drawer | upstream `cash_drawer` | Set `iot_cash_drawer_id` on the pos.config. |

---

## Cameras

| Vendor | Model | Connection | Driver | Status |
|---|---|---|---|---|
| Generic UVC USB camera | (any) | USB-UVC | upstream camera | ⏳ untested |
| IP cameras (RTSP) | (any) | Network | upstream camera | ⏳ untested |

Used by `filamind_quality_iot` for `picture` test type.

---

## Status legend

- ✅ **validated** — real device tested, all advertised actions work
- ⏳ **untested** — code path exists but no real device has run through it
- 🚧 **stub** — server data layer + box driver scaffold ship, but the
  vendor wire-format (TIM / CTEP / etc.) is `TODO` until a real
  device pairs
- ❌ **broken** — known not to work, see the linked issue
