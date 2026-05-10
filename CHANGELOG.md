# Changelog

All notable changes to filamind-iot are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/) and
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Initial release of the **Filamind IoT** Odoo 19 addon, forked and
  hardened from an internal `iot_custom` baseline.
- 5 models: `iot.box`, `iot.device`, `iot.device.type`,
  `iot.connection.log`, `iot.pairing.wizard`.
- HTTP endpoints under `/filamind_iot/*` plus `/iot/box/*` aliases for
  drop-in compatibility with the [filamind-iotbox](https://github.com/filamind-app/filamind-iotbox) image and the upstream Odoo IoT Box.
- Dual pairing wizard: server-code or box-token.
- 12 preloaded device types covering printers, scales, scanners, cameras,
  payment terminals, fiscal modules, customer displays, etc.
- Multi-company `ir.rule` on `iot.box`, `iot.device`,
  `iot.connection.log`.
- `_check_company_auto = True` on `iot.device` to enforce same-company
  device → box linking.
- `pairing_ttl` system parameter wired into `action_generate_pairing_code`
  (was hardcoded at 15 minutes).
- HTTP error responses no longer echo internal exception messages
  (information-disclosure hardening).
- CI workflow: ruff + py_compile + XML well-formedness +
  manifest-references-exist sanity.

### Notes
- Addon technical name: `filamind_iot` (Python module).
- Repo name on GitHub: `filamind-iot` (URL-friendly).
