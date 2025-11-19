# Repository Guidelines

## Project Structure & Module Organization
- `custom_components/ubisys/`: Integration code — `__init__.py` (setup/services), platforms (`cover.py`, `light.py`, `button.py`), config UI (`config_flow.py`), constants (`const.py`), `services.yaml`, `strings.json`, `translations/`.
- `custom_zha_quirks/`: ZHA quirks for Ubisys devices (manufacturer attributes, model mapping).
- `docs/`: Development and architecture docs (see `docs/development.md`).
- `install.sh`: One‑line installer for HA environments.
- `tests/`: Pytest suite with reusable fixtures (`conftest.py`), lightweight HA fakes, zigpy/zhaquirks stubs, and integration bootstrap/input-monitor/device-trigger suites; current repo-wide coverage ~58%.

## Build, Test, and Development Commands
- Prereqs: Home Assistant 2024.1.0+ and Python 3.11+; uv recommended for fast dependency install.
- Local install: `./install.sh` (creates folders, copies files, validates config).
- Dev links: `ln -s $(pwd)/custom_components/ubisys /config/custom_components/ubisys` and `ln -s $(pwd)/custom_zha_quirks /config/custom_zha_quirks`.
- Restart HA: `ha core restart` (or UI: Settings → System → Restart).
- Validate config: `hass --script check_config -c /config`; logs: `grep -i ubisys /config/home-assistant.log`.
- CI/Testing: `make ci` (creates .venv, installs from `pyproject.toml` [dependency-groups], runs lint/type/tests).
- Quick commands: `make fmt` (auto-fix), `make lint`, `make typecheck`, `make test`.

## Coding Style & Naming Conventions
- PEP 8; 4‑space indent; `black` (88 cols) and `isort` required; type hints for public functions; Google‑style docstrings.
- Modules: `snake_case`; constants in `const.py` UPPER_SNAKE_CASE; domain `ubisys`.
- Services: `ubisys.<action>`; user‑facing strings in `strings.json` and `translations/en.json`.
- Async‑first: avoid blocking I/O; use HA helpers; appropriate logging levels.

## Testing Guidelines
- Automated tests: `make test` (or `pytest --cov=custom_components.ubisys --cov=custom_zha_quirks`) runs the full suite; see `tests/README.md` for fixture guidance.
- Test fixtures: `tests/conftest.py` provides mock clusters, config entries, ZHA devices, and helper functions.
- Coverage target: 80%+ (current: 58% overall); remaining gaps are mainly legacy sensor/switch platforms, advanced input monitoring edge cases, and `custom_components/ubisys/__init__.py` service helpers.
- Manual HA testing: exercise config/option flows, cover/light commands, state updates, calibration with real hardware.
- Prefer real hardware for quirks, calibration, and input monitoring validation.
- Use `DEBUG` logging during development; avoid `print`; leverage structured logging (`kv()`, `info_banner()`).

## Commit & Pull Request Guidelines
- Conventional Commits with optional scope (e.g., `feat(config_flow): ...`).
- Branching: base PRs on `develop`; use `feature/*`, `bugfix/*`, `hotfix/*` branches.
- PRs include: what/why/how‑to‑test, linked issues, screenshots/logs if relevant, and updated docs (`docs/`, `README.md`).
- Versioning: bump `manifest.json` for user‑visible changes; update `CHANGELOG.md` and tag releases (e.g., `v1.2.0`).

## Security & Configuration Tips
- Never include secrets, personal paths, or real IEEE addresses in examples.
- Maintain compatibility with supported HA/ZHA versions where possible.
- Handle manufacturer codes and cluster writes cautiously; add safeguards and clear logging.

See `docs/development.md` for in‑depth guidance and rationale.
