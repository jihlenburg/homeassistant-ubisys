# Repository Guidelines

## Project Structure & Module Organization
- `custom_components/ubisys/`: Integration code — `__init__.py` (setup/services), platforms (`cover.py`, `light.py`, `switch.py`, `button.py`, `sensor.py`), config UI (`config_flow.py`), calibration (`j1_calibration.py`), D1 config (`d1_config.py`), input monitoring (`input_monitor.py`, `input_parser.py`), device triggers (`device_trigger.py`), constants (`const.py`), helpers (`helpers.py`), `services.yaml`, `strings.json`, `translations/`.
- `custom_zha_quirks/`: ZHA quirks for Ubisys devices — shared clusters (`ubisys_common.py`), device-specific (`ubisys_j1.py`, `ubisys_d1.py`, `ubisys_s1.py`).
- `docs/`: Development and architecture docs.
- `tests/`: Pytest suite with fixtures (`conftest.py`), lightweight HA fakes, zigpy/zhaquirks stubs; current coverage ~50%.
- `scripts/`: Development scripts (`run_ci_local.sh`, `create_release.sh`).

## Build, Test, and Development Commands
- Prereqs: Home Assistant 2024.1+ and Python 3.11+; uv recommended for fast dependency install.
- Local CI: `make ci` (creates .venv, installs from `pyproject.toml` [dependency-groups], runs lint/type/tests).
- Quick commands: `make fmt` (auto-fix), `make lint`, `make typecheck`, `make test`.
- Restart HA: `ha core restart` (or UI: Settings → System → Restart).
- Logs: `grep -i ubisys /config/home-assistant.log`.

## Branching Strategy
- **`develop`**: Active development branch, may include WIP, CI must pass.
- **`main`**: Production releases only, each commit = version, HACS tracks this.
- **Feature branches**: Create from develop (`feature/*`, `bugfix/*`, `hotfix/*`).
- **Beta releases**: Tag on develop (e.g., `v1.1.0-beta.1`), create GitHub pre-release.
- **Stable releases**: Squash merge develop → main, tag, create GitHub release.
- **PRs**: Always target `develop`, not `main`.

## Coding Style & Naming Conventions
- PEP 8; 4-space indent; `black` (88 cols) and `isort` required; type hints for public functions; Google-style docstrings.
- Modules: `snake_case`; constants in `const.py` UPPER_SNAKE_CASE; domain `ubisys`.
- Services: `ubisys.<action>`; user-facing strings in `strings.json` and `translations/en.json`.
- Async-first: avoid blocking I/O; use HA helpers; appropriate logging levels.
- Structured logging: use `kv()` and `info_banner()` from helpers.

## Testing Guidelines
- Automated tests: `make test` (or `pytest --cov`) runs the full suite.
- Test fixtures: `tests/conftest.py` provides mock clusters, config entries, ZHA devices.
- Coverage target: 80%+ (current: 50%).
- Manual HA testing: exercise config/option flows, cover/light/switch commands, calibration with real hardware.
- Use `DEBUG` logging during development; avoid `print`.

## Commit & Pull Request Guidelines
- Conventional Commits with optional scope (e.g., `feat(config_flow): ...`).
- PRs target `develop`, not `main`.
- PRs include: what/why/how-to-test, linked issues, updated docs.
- Run `make ci` locally before submitting.

## Release Process
- **Beta**: On develop, tag `vX.Y.Z-beta.N`, push, create pre-release.
- **Stable**: Squash merge develop → main, tag `vX.Y.Z`, push, run `./scripts/create_release.sh vX.Y.Z`.
- Update `manifest.json` version and `CHANGELOG.md` before release.

## Security & Configuration Tips
- Never include secrets, personal paths, or real IEEE addresses in examples.
- Maintain compatibility with supported HA/ZHA versions.
- Handle manufacturer codes and cluster writes cautiously; add safeguards and clear logging.

See `CONTRIBUTING.md` for full development guidelines and `CLAUDE.md` for detailed architecture.
