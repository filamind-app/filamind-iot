# Hardware-in-the-loop (HIL) test scripts

This directory ships **mock devices** so you can exercise the
filamind-iot stack end-to-end without owning real hardware. Each
mock is a small standalone Python script (no Odoo dependency)
that opens a virtual serial port (Linux pty) or HTTP listener
and answers to the same protocols the real device does.

| Mock | Pairs with on-server addon | Pairs with on-box driver |
|---|---|---|
| `mock_adam_scale.py` | `filamind_pos_iot_adam_scale` | `filamind_adam_driver.py` |
| `mock_payment_terminal.py --vendor six` | `filamind_pos_iot_six` | `filamind_six_driver.py` |
| `mock_payment_terminal.py --vendor worldline` | `filamind_pos_iot_worldline` | `filamind_worldline_driver.py` |
| `mock_eg_fiscal_printer.py` | `filamind_l10n_eg_iot` | `filamind_eg_fiscal_driver.py` |

## Workflow

1. Start the mock on a Linux machine — it prints the slave pty path
   (or HTTP URL) on stdout:

   ```bash
   $ python3 tests/hil/mock_adam_scale.py --weight 1.234 --unit kg
   /dev/pts/7
   [mock_adam] received '...'
   ```

2. On the box (or a dev machine running the iot_drivers code), edit
   the iot.device record so its serial path points at the mock's
   slave pty (or HTTP endpoint).

3. From the Odoo backend, click the test button on the device
   (`Test Connection` for scales / `Test Print` for printers /
   `Test Fiscal Printer` for the EG addon) — the call flows:

   ```
   Odoo backend
     │
     ▼ iot.box.send_bus_message(method='iot_action', ...)
   bus.bus channel
     │
     ▼ box's transport client (WebSocket / longpoll / shortpoll)
   on-box vendor driver (e.g. filamind_adam_driver)
     │
     ▼ writes to /dev/pts/7
   mock_adam_scale.py
     │
     ▼ writes reply back to /dev/pts/7
   on-box driver parses reply
     │
     ▼ send_to_controller
   Odoo backend  (iot.command.queue.record_response)
   ```

4. Look at `iot.command.queue` to confirm the round-trip succeeded
   — `state` should flip from `sent` → `completed` and `result`
   should hold the parsed weight / authorization / fiscal UUID.

## Running mocks on Windows / macOS

The `pty` module requires a Unix-like OS. On Windows, run the
mocks from inside WSL2:

```powershell
wsl bash -c "python3 /mnt/c/.../tests/hil/mock_adam_scale.py"
```

Then expose the WSL pty to the box over `socat` /
`socket-tcp-bridge` if the box is not on the same machine.

## What the mocks do NOT prove

These mocks accept any well-formed framing and return canned
responses. They do **not** validate:

* CRC / LRC checksums (TIM, AGN with checksum frames, etc.).
* Vendor-specific timing rules (e.g., Adam's "wait for stable
  reading" delay, Six's "card removal grace period").
* PCI-DSS-relevant edge cases (PIN-out-of-band, fall-back to mag,
  cardholder-not-present scenarios).

Real hardware-in-the-loop tests against actual terminals/scales
must be run against the v1.0 release before claiming production
readiness for any specific vendor.
