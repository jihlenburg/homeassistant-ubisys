# Work Log

A chronological log of meaningful changes performed during development sessions. This complements the human-readable CHANGELOG.

## 2025-11-12

- Logging & Verbosity
  - Added Options Flow toggles: `verbose_info_logging`, `verbose_input_logging`.
  - Reduced INFO noise across modules; gated lifecycle, setup, and per-event logs.
  - Optimized `kv()` to avoid formatting cost when level disabled.
- Calibration
  - Gated phase banners; added persistent notifications (start/success/failure).
  - Recorded last calibration results in `hass.data[DOMAIN]['calibration_history']`.
  - Wrapped cluster commands via `async_zcl_command` (timeouts + retries).
- Diagnostics & Logbook
  - Added `diagnostics.py`: redacted config/options, ZHA endpoints, last calibration.
  - Added `logbook.py`: friendly entries for input events and calibration completion.
  - Created Repairs issues for missing DeviceSetup or WindowCovering clusters.
- UX & Options Flow
  - Added “About” menu step with links to docs/issues.
  - Fixed `button.py` oddities; clear async_press behavior.
- Reliability
  - `async_write_and_verify_attrs` now uses timeouts and a limited retry; kept rollback on mismatch.
- CI & Tooling
  - Added `.github/workflows/ci.yml` (hassfest/HACS, lint/type/tests against HA 2024.1.*).
  - Added `scripts/run_ci_local.sh` and Makefile targets (`ci`, `fmt`, `lint`, `typecheck`, `test`).
- Documentation
  - README refreshed (features, testing, logging controls, diagnostics/logbook, About).
  - Added docs: `logging.md`, `device_triggers_examples.md`, `getting_started.md`.
  - Updated `CLAUDE.md` with logging policy, diagnostics/logbook/repairs, CI/tests overview.

