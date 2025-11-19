# Contributing to Ubisys Zigbee Devices Integration

Thank you for your interest in contributing! This document provides guidelines and information for developers.

## 🏗️ Development Setup

### Project Structure

```
homeassistant-ubisys/
├── custom_components/ubisys/     # Main integration
│   ├── __init__.py              # Setup, discovery, and service registration
│   ├── button.py                # Calibration button platform
│   ├── cover.py                 # Wrapper cover platform
│   ├── light.py                 # Wrapper light platform
│   ├── switch.py                # Wrapper switch platform
│   ├── sensor.py                # Last input event sensor
│   ├── j1_calibration.py        # J1 calibration module
│   ├── d1_config.py             # D1 configuration module
│   ├── config_flow.py           # Configuration UI with auto-discovery
│   ├── const.py                 # Constants and mappings
│   ├── helpers.py               # Shared utility functions
│   ├── input_config.py          # Input configuration presets
│   ├── input_monitor.py         # Physical input event monitoring
│   ├── input_parser.py          # InputActions micro-code parser
│   ├── device_trigger.py        # Device automation triggers
│   ├── diagnostics.py           # Diagnostics platform
│   ├── logbook.py               # Logbook integration
│   ├── repairs.py               # Repairs platform
│   ├── manifest.json            # Integration metadata
│   ├── services.yaml            # Service definitions
│   ├── strings.json             # UI strings
│   └── translations/            # Localization files
│       ├── en.json
│       ├── de.json
│       ├── fr.json
│       └── es.json
├── custom_zha_quirks/           # ZHA device quirks
│   ├── ubisys_common.py         # Shared clusters and constants
│   ├── ubisys_j1.py             # J1/J1-R quirk
│   ├── ubisys_d1.py             # D1/D1-R quirk
│   └── ubisys_s1.py             # S1/S1-R quirk
├── tests/                       # Test suite
│   ├── conftest.py              # Shared fixtures
│   ├── test_integration_bootstrap.py
│   ├── test_input_monitor.py
│   ├── test_platform_wrappers.py
│   ├── test_zha_quirks.py
│   └── test_device_trigger.py
├── docs/                        # Documentation
├── scripts/                     # Development scripts
│   ├── run_ci_local.sh         # Local CI runner
│   └── create_release.sh        # Release automation
├── Makefile                     # Development commands
└── pyproject.toml               # Project configuration
```

## 🧪 Testing & Local CI

### Quick Start

Use our local CI runner (automatically creates `.venv`, installs dependencies, runs all checks):

```bash
# Full local CI suite
make ci

# Auto-fix formatting issues
make fmt

# After initial bootstrap
make lint        # Run linters (black, isort, flake8)
make typecheck   # Run mypy type checking
make test        # Run pytest suite
```

### Manual Testing

```bash
# Activate virtual environment (created by make ci)
source .venv/bin/activate

# Run specific test file
pytest tests/test_input_monitor.py -v

# Run with coverage report
pytest --cov=custom_components.ubisys --cov=custom_zha_quirks --cov-report=term-missing

# Run specific test function
pytest tests/test_device_trigger.py::test_async_get_triggers -v
```

### Test Coverage

Current coverage: ~58% with these targeted suites:

- `test_integration_bootstrap.py` - Verifies `async_setup`, `async_setup_entry`, `async_unload_entry` wire services and discovery correctly
- `test_input_monitor.py` - Tests InputActions parsing, zha_event correlation, and monitor lifecycle
- `test_platform_wrappers.py` - Tests cover/light/switch wrappers and last input event sensor
- `test_zha_quirks.py` - Validates quirk cluster definitions and manufacturer code injection
- `test_device_trigger.py` - Tests device automation trigger mapping

## 📝 Code Quality Standards

### Function Complexity Limits

- **Maximum function size**: 100 lines (target: <60 lines)
- **Maximum complexity**: Keep functions focused on single responsibility
- **Nesting limit**: Maximum 2-3 levels of indentation

### Documentation Requirements

All functions must have docstrings that include:

1. One-line summary
2. Detailed explanation of **WHY** (not just WHAT)
3. Args with types, valid values, and constraints
4. Returns with typical values and units
5. Raises with conditions and user actions
6. Examples for complex functions
7. Design decisions and tradeoffs

**Example:**

```python
async def _wait_for_stall(
    hass: HomeAssistant,
    entity_id: str,
    phase_description: str,
    timeout: int = PER_MOVE_TIMEOUT,
) -> int:
    """Wait for motor stall via position monitoring.

    The J1 motor doesn't signal when it reaches a limit. We detect
    stall by monitoring the position attribute - if unchanged for
    STALL_DETECTION_TIME seconds, the motor has stalled.

    Why 3 seconds?
    - <2s: False positives (motor may pause briefly)
    - >5s: Poor UX (user perceives lag)
    - 3s: Balanced (proven by deCONZ implementation)

    Args:
        hass: Home Assistant instance for state access
        entity_id: ZHA cover entity to monitor
        phase_description: Description for logging (e.g., "finding top")
        timeout: Max seconds to wait before raising timeout error

    Returns:
        Final position when motor stalled (e.g., 100 for fully open)

    Raises:
        HomeAssistantError: If motor doesn't stall within timeout.
            Usually indicates jammed motor or disconnected device.
    """
```

### Security Patterns

**Service Parameter Validation:**

```python
# ALWAYS validate service parameters
entity_id = call.data.get("entity_id")

# Check type
if not isinstance(entity_id, str):
    raise HomeAssistantError(f"entity_id must be string, got {type(entity_id).__name__}")

# Verify entity exists
entity_entry = entity_registry.async_get(entity_id)
if not entity_entry:
    raise HomeAssistantError(f"Entity {entity_id} not found")

# Verify platform ownership
if entity_entry.platform != DOMAIN:
    raise HomeAssistantError(
        f"Entity {entity_id} is not a Ubisys entity (platform: {entity_entry.platform})"
    )
```

**Concurrency Control:**

```python
# Use asyncio.Lock, NOT set-based tracking
# Set-based has TOCTOU race condition

# Get or create lock for device
if "calibration_locks" not in hass.data.setdefault(DOMAIN, {}):
    hass.data[DOMAIN]["calibration_locks"] = {}

locks = hass.data[DOMAIN]["calibration_locks"]
if device_ieee not in locks:
    locks[device_ieee] = asyncio.Lock()

device_lock = locks[device_ieee]

# Non-blocking check
if device_lock.locked():
    raise HomeAssistantError("Calibration already in progress")

# Atomic acquire
async with device_lock:
    await perform_operation()
    # Lock automatically released
```

## 🎨 Logging Policy

### Structured Logging

Use the `kv()` helper for structured, sorted key-value logging:

```python
from .helpers import kv

kv(_LOGGER, logging.INFO, "Device discovered",
   ieee="00:1f:ee:00:00:00:68:a5",
   model="J1",
   shade_type="roller")
```

### Verbosity Levels

- **DEBUG**: Technical details, always on for developers
- **INFO**: Lifecycle events, gated by `verbose_info_logging` option
- **WARNING**: Recoverable issues
- **ERROR**: Failures requiring user action

### Banner Logs

Use `info_banner()` for major milestones:

```python
from .helpers import info_banner

info_banner(_LOGGER, "Calibration Complete",
            total_steps=12543,
            duration_seconds=87,
            shade_type="venetian")
```

## 🔧 Architecture Principles

### DRY (Don't Repeat Yourself)

Extract shared functionality to common modules:

- `helpers.py` - Shared utility functions
- `ubisys_common.py` - Shared ZHA quirk clusters

### Separation of Concerns

- Device-specific logic in dedicated modules (`j1_calibration.py`, `d1_config.py`)
- Shared functionality in common modules
- Platform wrappers delegate to ZHA (never talk to Zigbee directly)

### Wrapper Entity Pattern

Entities are **wrappers**, not replacements:

```
User → Ubisys Entity → ZHA Entity → Zigbee Device
```

Critical: Always delegate commands to underlying ZHA entity. Never access Zigbee clusters directly from wrapper entities.

## 📋 Pull Request Guidelines

### Before Submitting

- [ ] Run `make ci` locally (all checks must pass)
- [ ] Add tests for new functionality
- [ ] Update documentation (`docs/` and docstrings)
- [ ] Add CHANGELOG entry under `[Unreleased]`
- [ ] Follow commit message conventions (see below)

### Commit Message Format

Use Conventional Commits:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `refactor`: Code restructuring
- `test`: Adding/updating tests
- `chore`: Maintenance tasks
- `ci`: CI/CD changes

**Examples:**

```
feat(j1): add position offset configuration

Allow users to adjust position reporting to match physical reality.
Useful when shade limits don't align with 0%/100% expectations.

Closes #42
```

```
fix(services): use vol.Schema instead of cv.make_entity_service_schema

The previous implementation used entity service schemas which expect
a different handler signature. Changed to regular schemas with explicit
entity_id field.

Fixes #67
```

## 🐛 Testing with Real Hardware

### Required for Validation

- **D1 Phase Mode** - Needs testing with real dimmer and various load types
- **J1 Calibration** - Needs real-world validation across shade types
- **Input Monitoring** - Needs testing with physical button presses

### Manual Testing Checklist

1. **J1 Calibration**
   - [ ] Test with roller shade (position only)
   - [ ] Test with venetian blind (position + tilt)
   - [ ] Test calibration from various starting positions
   - [ ] Verify accurate position reporting after calibration
   - [ ] Test recalibration (should work multiple times)

2. **D1 Configuration**
   - [ ] Test phase mode with LED loads
   - [ ] Test phase mode with incandescent loads
   - [ ] Test ballast min/max level configuration
   - [ ] Verify settings persist after power cycle

3. **Input Monitoring**
   - [ ] Test button press events fire correctly
   - [ ] Test device triggers in automations
   - [ ] Verify last input event sensor updates

## 🌐 Localization

### Adding a New Language

1. Copy `custom_components/ubisys/translations/en.json` to `<language_code>.json`
2. Translate all string values (keep keys unchanged)
3. Add language to `strings.json` if needed
4. Test with Home Assistant language setting

### Translation Keys

Do not modify these - they must match `strings.json`:

- `config.step.*` - Configuration flow steps
- `options.step.*` - Options flow steps
- `selector.*` - Dropdown options
- `services.*` - Service descriptions

## 🔍 Debugging Tips

### Enable Debug Logging

```yaml
# configuration.yaml
logger:
  logs:
    custom_components.ubisys: debug
    custom_zha_quirks.ubisys_j1: debug
    custom_zha_quirks.ubisys_d1: debug
    custom_zha_quirks.ubisys_s1: debug
```

### View Integration Logs

```bash
grep -i ubisys /config/home-assistant.log | tail -100
```

### Inspect ZHA Quirk Loading

Check Home Assistant logs for:
```
Successfully imported custom quirk ubisys_j1
```

### Verify Entity Registration

```bash
# Check entities in Developer Tools → States
# Filter for: ubisys
```

## 🌿 Branching Strategy

### Overview

```
feature/xxx ──┬──► develop ──────────────► main
feature/yyy ──┤      │                      │
feature/zzz ──┘      │                      │
                     │                      │
                [Dev Testing]          [Releases]
                [CI on every push]     [Tags: vX.Y.Z]
                [Beta tags]            [HACS tracks]
```

### Branches

| Branch | Purpose | Who Uses It |
|--------|---------|-------------|
| **`develop`** | Active development, may include WIP | Developers, testers |
| **`main`** | Production releases only | End users via HACS |

### Development Workflow

#### 1. Create Feature Branch

```bash
git checkout develop
git pull origin develop
git checkout -b feature/new-calibration-ui
```

#### 2. Work and Commit

```bash
# Make changes...
git add -A && git commit -m "feat: add calibration progress UI"
git push -u origin feature/new-calibration-ui
```

#### 3. Create Pull Request

```bash
gh pr create --base develop --title "feat: calibration progress UI"
```

#### 4. After CI Passes

Merge to develop via GitHub UI or CLI.

#### 5. Test on Real Hardware

Point your HA development instance to the develop branch and test with real devices.

### Beta Releases

Create pre-release tags on develop for testers:

```bash
# Ensure develop is stable
git checkout develop
git pull origin develop

# Create beta tag
git tag -a v1.1.0-beta.1 -m "Beta 1 for v1.1.0

New Features:
- Calibration progress UI
- Improved error messages

Known Issues:
- None reported yet"

# Push tag
git push origin v1.1.0-beta.1

# Create GitHub pre-release
gh release create v1.1.0-beta.1 --prerelease --title "v1.1.0 Beta 1" --notes "Testing release for v1.1.0 features"
```

**Beta Version Naming:**
- `v1.1.0-beta.1` - First beta
- `v1.1.0-beta.2` - Second beta (after fixes)
- `v1.1.0-rc.1` - Release candidate (feature complete)

### Stable Releases

Promote tested code from develop to main:

```bash
# 1. Ensure develop is stable and tested
git checkout develop
git pull origin develop
make ci  # All checks must pass

# 2. Switch to main and merge
git checkout main
git pull origin main
git merge --squash develop

# 3. Commit as release
git commit -m "$(cat <<'EOF'
Release v1.1.0

## New Features
- Calibration progress UI
- Improved error messages

## Bug Fixes
- Fixed D1 phase mode edge case

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"

# 4. Tag and push
git tag -a v1.1.0 -m "Version 1.1.0"
git push origin main --tags

# 5. Create GitHub Release
./scripts/create_release.sh v1.1.0

# 6. Sync develop with main
git checkout develop
git merge main
git push origin develop
```

### Installing Beta Versions

#### For Testers

**Option 1: HACS (Recommended)**

1. Open HACS → Integrations → Ubisys
2. Click ⋮ → Redownload
3. Enable "Show beta versions"
4. Select the beta version
5. Restart Home Assistant

**Option 2: Manual Installation**

```bash
cd ~/.homeassistant/custom_components
rm -rf ubisys
git clone -b develop https://github.com/jihlenburg/homeassistant-ubisys.git ubisys-temp
mv ubisys-temp/custom_components/ubisys .
rm -rf ubisys-temp
```

Then restart Home Assistant.

#### Reporting Beta Issues

When testing beta releases:

1. Include version number: `v1.1.0-beta.1`
2. Provide relevant logs
3. Describe steps to reproduce
4. Tag issue with `beta-feedback`

### Branch Protection (Maintainers)

Configure in GitHub Settings → Branches:

**`main` branch:**
- Require pull request before merging
- Require status checks to pass
- No force push
- No deletions

**`develop` branch:**
- Require status checks to pass
- Allow squash merge

## 📦 Release Process

### Creating a Stable Release

See [Stable Releases](#stable-releases) above for the complete workflow.

### Creating a Beta Release

See [Beta Releases](#beta-releases) above for the complete workflow.

### Versioning

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes (API changes, removed features)
- **MINOR**: New features (backward-compatible)
- **PATCH**: Bug fixes (backward-compatible)

**Pre-release Suffixes:**
- `-beta.N` - Beta releases (feature testing)
- `-rc.N` - Release candidates (final testing)
- `-alpha.N` - Alpha releases (early development)

## 💡 How You Can Help

### High Priority

- **Hardware Testing**: Validate D1 phase modes and J1 calibration with real devices
- **Test Coverage**: Increase from 58% to 80%+
- **Documentation**: Add more examples and troubleshooting guides
- **Translations**: Add non-English language support

### Feature Development

- **S2/S2-R Support**: Implement dual power switch platform
- **Event Entities**: Show last button press in dashboard
- **Scene Support**: Save/recall preset positions for J1
- **Energy Dashboard**: Integrate S1/D1 power monitoring

### Bug Reports

File issues at: https://github.com/jihlenburg/homeassistant-ubisys/issues

Include:
- Home Assistant version
- Integration version
- Device model
- Relevant logs
- Steps to reproduce

## 📞 Getting Help

- **Discussions**: [GitHub Discussions](https://github.com/jihlenburg/homeassistant-ubisys/discussions)
- **Issues**: [GitHub Issues](https://github.com/jihlenburg/homeassistant-ubisys/issues)
- **Community**: [Home Assistant Forum](https://community.home-assistant.io/)

## 📝 License

By contributing, you agree that your contributions will be licensed under the MIT License.
