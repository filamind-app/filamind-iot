# Security model for filamind-iot

This document describes the threat model, secret/token handling,
PCI-DSS scope, and recommended hardening for production
deployments.

---

## 1. Threat model in scope

filamind-iot is designed to defend against:

1. **A malicious user on the same LAN as the box** trying to
   issue commands directly to the box's IoT endpoints.
2. **A malicious user on the public Internet** scanning for
   pairing endpoints to register a rogue box against the
   server.
3. **Eavesdropping on the box ↔ server channel** (cleartext
   credentials, replayable bus messages).
4. **A compromised box** sending fabricated IoT commands or
   measurement data to the server.

Defenses below address each.

### Out of scope

- A compromised Odoo server. If the server is owned, the boxes
  it controls are too — full stop.
- Physical tampering with the box's SD card.
- Side-channel attacks against the WebSocket TLS layer.
- Vendor-specific PIN-on-glass attacks (responsibility of the
  payment terminal vendor, not filamind).

---

## 2. Token + pairing flow

### How tokens are issued

1. Admin clicks **Connect a Box** in Odoo. The server generates
   an 8-character pairing code (random, base32) valid for
   `filamind_iot.pairing_ttl` minutes (default 15).
2. The admin enters the code on the box's setup page along with
   the server URL.
3. The box `POST`s `{code, identifier, ip_address, mac_address,
   hostname}` to `/filamind_iot/pair`.
4. The server validates the code, generates a per-box token
   (`secrets.token_urlsafe(32)`), stores it, and returns it.
5. The box persists the token under `/home/pi/odoo.conf`
   (filesystem-restricted to user `odoo`).

### How tokens are used

Every subsequent box → server request carries `identifier` +
`token` in the JSON body. The server validates both as a unit:
no fall-back to identifier-only, no plaintext password.

```python
# filamind_iot/controllers/iot_controller.py
box = env['iot.box'].sudo().search([
    ('identifier', '=', identifier),
    ('token', '=', token),    # equality match, no LIKE / regex
], limit=1)
if not box:
    return Response('forbidden', status=403)
```

### Rotation

Re-pair a box to rotate its token (delete the old one from the
box, click **Connect a Box** again). No automatic rotation —
boxes are infrastructure, not user accounts.

---

## 3. Transport security

### TLS

The server URL **must** be `https://` for production. The box's
`tools/transport.py` rejects plaintext `http://` URLs by default
(`SECURITY_REJECT_PLAINTEXT = True`); flip it to `False` only
for closed-network development.

Cipher suite is whatever the reverse proxy negotiates. The
recipes in
[REVERSE_PROXY_PLATFORMS.md](REVERSE_PROXY_PLATFORMS.md) all
configure modern TLS — letsencrypt + nginx/Caddy default to
TLS 1.2+ with PFS.

### WebSocket vs HTTP

The box's transport client tries WebSocket first, then long-poll,
then short-poll. All three carry `identifier` + `token` for
auth. WebSocket is preferred for latency, not for security —
the security properties are identical.

### CSRF

Every public HTTP endpoint that accepts POST is `csrf=False`
because the IoT box is not a browser session. Auth is via the
identifier + token in the body, which serves as a CSRF token
substitute (an attacker without the token can't forge a
request).

---

## 4. PCI-DSS scope

### Where the PAN lives

filamind-iot **never** stores the full PAN. The
`filamind_pos_iot_six` and `filamind_pos_iot_worldline` addons
explicitly capture only:

- `card_last4` — last four digits, harmless under PCI-DSS.
- `card_brand` — Visa / Mastercard / etc.
- `emv_aid`, `emv_tvr`, `emv_tsi` — chargeback-defence evidence.
- `authorization_code` — issuer auth code, NOT card data.
- `signature_required` — boolean.

The full PAN exists transiently inside the payment terminal
(certified by the vendor) and is never sent to the IoT box or
the server. **Do not** override
`pos.payment._filamind_apply_six_response` to store more — your
PCI-DSS scope expands the moment you do.

### What the box sees

The box's vendor driver receives the terminal's response frame.
For Six TIM, this frame typically contains last4 + EMV fields
but not the PAN. For Worldline CTEP, the response frame
**may** include a maskedPAN field (e.g., `4242 ** ** 1234`)
which is also PCI-DSS-safe per requirement 3.3.

If the driver ever sees a 16-digit PAN in the response frame,
either the terminal is misconfigured (file a support ticket)
or the PAN is masked already. Either way, the driver is hard-
coded to log only the last 4 — it never persists the rest.

### Audit trail

`pos.payment` rows are write-once after creation; PostgreSQL
ACLs enforce this via the standard Odoo ORM (no DELETE on
`pos_payment`). For full audit compliance, enable PostgreSQL
WAL archiving and ship logs to a tamper-evident store.

---

## 5. Recommended hardening

### Server

- Run Odoo as a non-root user (`odoo`, never `root`).
- Set `admin_passwd` in `odoo.conf` to a long random string —
  this is the database-management password, not a user
  password. Compromise = remote DB drop.
- Enable `proxy_mode = True` in `odoo.conf` so Odoo trusts
  `X-Forwarded-Proto`/`X-Real-IP` from the reverse proxy.
- Front Odoo with a reverse proxy (nginx / Caddy / etc. — see
  REVERSE_PROXY_PLATFORMS.md). Never expose port 8069 or 8072
  directly to the Internet.
- Restrict the box's pairing endpoint to your boxes' source IPs
  via the proxy's `allow`/`deny` rules if your boxes have
  static IPs.

### Box

- Change the `pi` user's password from the Raspberry Pi default.
- Disable SSH password login; use SSH keys only.
- Keep the box on a VLAN segregated from end-user networks.
- Run `filamind-status` periodically as a health check (e.g.
  via cron + remote pull).

### Database

- Enable `sslmode=require` between Odoo and Postgres.
- Restrict the `odoo` PG role to its own database; revoke
  PUBLIC schema access to other DBs.
- Back up daily; test restore monthly.

---

## 6. Reporting a vulnerability

Send PGP-encrypted email to
[security@filamind-app](mailto:security@filamind-app.example).
We aim to acknowledge within 72 hours and ship a patch within
30 days for high-severity issues.

Do **not** open public GitHub issues for security
vulnerabilities — file a private security advisory on GitHub
instead.
