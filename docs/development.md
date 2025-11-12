# Development Guide

This guide is for developers who want to contribute to or modify the Ubisys Home Assistant integration.

## Table of Contents

- [Development Setup](#development-setup)
- [Architecture Overview](#architecture-overview)
- [Code Style](#code-style)
- [Testing](#testing)
- [Contributing](#contributing)
- [Release Process](#release-process)

## Development Setup

### Prerequisites

- Home Assistant development environment (2024.1.0+)
- Python 3.11 or higher
- Git
- A Ubisys J1 device (for testing) or access to test environment

### Initial Setup

1. **Fork the repository:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/homeassistant-ubisys.git
   cd homeassistant-ubisys
   ```

2. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate  # Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install homeassistant
   pip install -r requirements_dev.txt  # If exists
   ```

4. **Link to Home Assistant:**
   ```bash
   # Create symbolic links for development
   ln -s $(pwd)/custom_components/ubisys ~/.homeassistant/custom_components/ubisys
   ln -s $(pwd)/custom_zha_quirks/ubisys_j1.py ~/.homeassistant/custom_zha_quirks/ubisys_j1.py
   ln -s $(pwd)/python_scripts/ubisys_j1_calibrate.py ~/.homeassistant/python_scripts/ubisys_j1_calibrate.py
   ```

5. **Configure Home Assistant:**
   ```yaml
   # configuration.yaml
   logger:
     default: info
     logs:
       custom_components.ubisys: debug

   zha:
     custom_quirks_path: custom_zha_quirks

   python_script:
   ```

6. **Restart Home Assistant**

### Development Workflow

1. **Make changes** in your local repository
2. **Restart Home Assistant** to load changes
3. **Test** the changes
4. **Commit** with descriptive messages
5. **Push** to your fork
6. **Create pull request**

## Architecture Overview

### Component Structure

```
custom_components/ubisys/
├── __init__.py           # Integration setup, service registration
├── config_flow.py        # UI configuration flow
├── const.py              # Constants and mappings
├── cover.py              # Cover platform entity wrapper
├── manifest.json         # Integration metadata
├── services.yaml         # Service definitions
├── strings.json          # UI strings (English)
└── translations/
    └── en.json           # Localized strings
```

### Data Flow

```
User Command
    ↓
Ubisys Cover Entity (cover.py)
    ↓
Filters based on shade_type
    ↓
ZHA Cover Entity
    ↓
Zigbee Network
    ↓
Ubisys J1 Device
```

### Key Classes

#### UbisysCover (cover.py)

**Purpose:** Wrapper entity that filters features based on shade type

**Key Methods:**
- `__init__`: Initialize with ZHA entity reference and shade type
- `_async_update_from_zha`: Sync state from underlying ZHA entity
- `async_open_cover`: Filtered open command
- `async_set_cover_position`: Filtered position command
- `async_set_cover_tilt_position`: Filtered tilt command (venetian only)

**Key Attributes:**
- `_attr_supported_features`: Dynamically set based on shade type
- `_zha_entity_id`: Reference to underlying ZHA entity
- `_shade_type`: Configured shade type

#### UbisysConfigFlow (config_flow.py)

**Purpose:** Handle UI configuration

**Key Methods:**
- `async_step_user`: Initial configuration step
- `_get_zha_cover_entities`: Query available ZHA covers

#### UbisysOptionsFlow (config_flow.py)

**Purpose:** Handle reconfiguration (shade type changes)

**Key Methods:**
- `async_step_init`: Options flow entry point

#### UbisysWindowCovering (custom_zha_quirks/ubisys_j1.py)

**Purpose:** Extend ZHA WindowCovering cluster with manufacturer attributes

**Key Methods:**
- `read_attributes`: Auto-inject manufacturer code for Ubisys attributes
- `write_attributes`: Auto-inject manufacturer code for Ubisys attributes

**Key Attributes:**
- `manufacturer_attributes`: Ubisys-specific attribute definitions
- `UBISYS_MANUFACTURER_CODE`: 0x10F2

### State Management

The integration uses an event-driven state synchronization model:

1. **ZHA entity state changes**
2. **Event listener in UbisysCover** (`_async_state_changed_listener`)
3. **Update internal state** (`_async_update_from_zha`)
4. **Notify Home Assistant** (`async_write_ha_state`)

### Configuration Flow

```
User initiates setup
    ↓
List available ZHA cover entities
    ↓
User selects entity and shade type
    ↓
Create config entry
    ↓
Setup cover platform
    ↓
Create UbisysCover entity
    ↓
Register state listener
    ↓
Entity available in Home Assistant
```

## Code Style

### Python Style Guide

Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) and Home Assistant's [style guide](https://developers.home-assistant.io/docs/development_guidelines).

**Key points:**
- Use `black` for formatting
- Use `isort` for import sorting
- Use type hints for all function parameters and returns
- Maximum line length: 88 characters (black default)

### Formatting Tools

```bash
# Install tools
pip install black isort flake8 mypy

# Format code
black custom_components/ubisys/
isort custom_components/ubisys/

# Check style
flake8 custom_components/ubisys/
mypy custom_components/ubisys/
```

### Docstrings

Use Google-style docstrings:

```python
def example_function(param1: str, param2: int) -> bool:
    """Brief description of function.

    Longer description if needed.

    Args:
        param1: Description of param1.
        param2: Description of param2.

    Returns:
        Description of return value.

    Raises:
        ValueError: Description of when this is raised.
    """
    return True
```

### Type Hints

Always use type hints:

```python
from __future__ import annotations

from typing import Any

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up from config entry."""
    ...
```

### Constants

All constants go in `const.py`:

```python
from typing import Final

DOMAIN: Final = "ubisys"
CONF_SHADE_TYPE: Final = "shade_type"
```

### Logging

Use appropriate log levels:

```python
import logging

_LOGGER = logging.getLogger(__name__)

_LOGGER.debug("Detailed debug info")
_LOGGER.info("Important information")
_LOGGER.warning("Warning message")
_LOGGER.error("Error occurred: %s", error)
```

## Testing

### Manual Testing

1. **Install in test environment:**
   ```bash
   ./install.sh
   ```

2. **Test config flow:**
   - Add integration via UI
   - Test with different shade types
   - Test reconfiguration

3. **Test entity functionality:**
   - Open/close commands
   - Position commands
   - Tilt commands (venetian)
   - State updates

4. **Test calibration:**
   - Run calibration service
   - Verify step counts
   - Test position accuracy

### Automated Testing

**Note:** Automated tests are planned for future development.

Structure for tests:

```
tests/
├── __init__.py
├── test_config_flow.py
├── test_cover.py
├── test_j1_calibration.py
└── fixtures/
    └── zha_device.py
```

Example test structure:

```python
"""Tests for Ubisys config flow."""
from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from custom_components.ubisys.const import DOMAIN


async def test_config_flow_success(hass: HomeAssistant):
    """Test successful config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    # ... more assertions
```

### Test Checklist

Before submitting PR:

- [ ] Config flow works
- [ ] Cover entity responds to commands
- [ ] Feature filtering works correctly
- [ ] Calibration completes successfully
- [ ] State updates propagate correctly
- [ ] Options flow works
- [ ] Unload/reload works
- [ ] No errors in logs
- [ ] Code passes linting (black, isort, flake8, mypy)
- [ ] Docstrings complete
- [ ] Type hints present

## Contributing

### Branch Strategy

- `main` - Stable releases
- `develop` - Development branch
- `feature/*` - Feature branches
- `bugfix/*` - Bug fix branches
- `hotfix/*` - Urgent fixes for main

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(cover): add support for tilt position

- Implement set_cover_tilt_position
- Add tilt state tracking
- Filter tilt features by shade type

Closes #123
```

```
fix(calibration): handle timeout during close operation

Previously the calibration would fail silently if the
shade took too long to close. Now it properly reports
the timeout error.

Fixes #456
```

### Pull Request Process

1. **Create feature branch:**
   ```bash
   git checkout -b feature/my-new-feature develop
   ```

2. **Make changes and commit:**
   ```bash
   git add .
   git commit -m "feat(scope): description"
   ```

3. **Push to fork:**
   ```bash
   git push origin feature/my-new-feature
   ```

4. **Create pull request:**
   - Base: `develop`
   - Title: Clear description
   - Description:
     - What changed
     - Why it changed
     - How to test
     - Screenshots if UI changes
     - Related issues

5. **Code review:**
   - Address review comments
   - Update PR with requested changes
   - Mark conversations as resolved

6. **Merge:**
   - Maintainer will merge when approved
   - Delete feature branch after merge

### Code Review Checklist

Reviewers should check:

- [ ] Code follows style guide
- [ ] Type hints present
- [ ] Docstrings complete
- [ ] Logging appropriate
- [ ] Error handling robust
- [ ] No breaking changes (or documented)
- [ ] Performance considerations
- [ ] Security considerations
- [ ] Tests passing (when available)

## Release Process

### Versioning

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: New features, backwards compatible
- **PATCH**: Bug fixes, backwards compatible

### Release Steps

1. **Update version:**
   ```bash
   # manifest.json
   "version": "1.1.0"
   ```

2. **Update CHANGELOG.md:**
   ```markdown
   ## [1.1.0] - 2024-02-15

   ### Added
   - New feature X
   - New feature Y

   ### Fixed
   - Bug fix A
   - Bug fix B

   ### Changed
   - Improvement C
   ```

3. **Commit changes:**
   ```bash
   git add manifest.json CHANGELOG.md
   git commit -m "chore: bump version to 1.1.0"
   ```

4. **Create tag:**
   ```bash
   git tag -a v1.1.0 -m "Release version 1.1.0"
   git push origin v1.1.0
   ```

5. **Create GitHub release:**
   - Go to GitHub → Releases → New Release
   - Tag: v1.1.0
   - Title: Version 1.1.0
   - Description: Copy from CHANGELOG.md
   - Attach assets if needed

6. **Update HACS:**
   - HACS should auto-detect new release
   - Verify in HACS after a few hours

## Project Structure Details

### manifest.json

Required fields:
```json
{
  "domain": "ubisys",
  "name": "Ubisys Zigbee Devices",
  "codeowners": ["@jihlenburg"],
  "config_flow": true,
  "dependencies": ["zha"],
  "documentation": "https://github.com/jihlenburg/homeassistant-ubisys",
  "integration_type": "device",
  "iot_class": "local_polling",
  "issue_tracker": "https://github.com/jihlenburg/homeassistant-ubisys/issues",
  "requirements": [],
  "version": "1.0.0"
}
```

### strings.json

Structure:
```json
{
  "config": {
    "step": { /* config flow steps */ },
    "error": { /* error messages */ },
    "abort": { /* abort reasons */ }
  },
  "options": {
    "step": { /* options flow steps */ }
  },
  "services": {
    "calibrate": { /* service definition */ }
  }
}
```

### translations/en.json

Must match strings.json structure exactly.

## Future Development

### Planned Features

- [ ] Support for Ubisys J1-R (roller shutter variant)
- [ ] Support for Ubisys S1/S2 switches
- [ ] Scene support for preset positions
- [ ] Position offset configuration
- [ ] Speed control configuration
- [ ] Web-based calibration wizard
- [ ] Multi-language support (DE, FR, ES)
- [ ] Automated testing framework
- [ ] CI/CD pipeline

### Enhancement Ideas

- Position learning mode
- Custom step size configuration
- Calibration scheduling
- Position drift detection
- Advanced diagnostics panel
- Integration with cover groups

## Resources

### Home Assistant Development

- [Developer Docs](https://developers.home-assistant.io/)
- [Architecture](https://developers.home-assistant.io/docs/architecture_index)
- [Integration Development](https://developers.home-assistant.io/docs/creating_integration_manifest)
- [Config Flow](https://developers.home-assistant.io/docs/config_entries_config_flow_handler)

### Zigbee/ZHA

- [ZHA Documentation](https://www.home-assistant.io/integrations/zha/)
- [Zigpy Documentation](https://github.com/zigpy/zigpy)
- [ZHA Quirks](https://github.com/zigpy/zha-device-handlers)
- [Zigbee Cluster Library](https://zigbeealliance.org/wp-content/uploads/2019/12/07-5123-06-zigbee-cluster-library-specification.pdf)

### Ubisys

- [Ubisys Technical Documentation](https://www.ubisys.de/en/support/)
- [J1 Manual](https://www.ubisys.de/en/products/zigbee-shutter-control-j1/)

## Getting Help

- **Questions:** Open a [GitHub Discussion](https://github.com/jihlenburg/homeassistant-ubisys/discussions)
- **Bugs:** Open a [GitHub Issue](https://github.com/jihlenburg/homeassistant-ubisys/issues)
- **Chat:** Home Assistant [Discord](https://discord.gg/home-assistant) #devs_custom_integrations

## License

This project is licensed under the MIT License - see [LICENSE](../LICENSE) file.
