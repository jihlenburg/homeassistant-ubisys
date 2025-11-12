# Shared Architecture: J1 Window Covering & D1 Dimmer

## Design Philosophy

This document explains the shared architecture between J1 (window covering) and D1 (dimmer) implementations, focusing on **separation of concerns** and **code reuse**.

---

## Core Principles

### 1. **Single Responsibility Principle**

Each module has ONE clear responsibility:

```
j1_calibration.py     → ONLY window covering calibration (J1-specific)
device_config.py      → Common device configuration utilities (shared)
d1_config.py          → D1-specific configuration logic
const.py              → All constants (shared)
helpers.py            → Shared utilities (cluster access, validation)
```

**Why:** Easy to test, maintain, and extend. Changes to D1 don't affect J1 and vice versa.

---

### 2. **Dependency Inversion**

High-level modules don't depend on low-level modules. Both depend on abstractions.

```python
# BAD: Direct dependency
class UbisysCover:
    def __init__(self):
        self.cluster = get_j1_cluster()  # Tightly coupled to J1

# GOOD: Dependency injection
class UbisysCover:
    def __init__(self, cluster_provider: ClusterProvider):
        self.cluster = cluster_provider.get_cluster()
```

**Why:** Easier testing (mock dependencies), flexible configuration.

---

### 3. **DRY (Don't Repeat Yourself) - But Carefully**

Share code when logic is **truly identical**, not just **similar**.

```python
# SHARED: Truly identical logic
def get_window_covering_cluster(hass, ieee):
    """Get cluster for any device using WindowCovering."""
    # J1 and D1 both use this cluster
    return _get_cluster(hass, ieee, 0x0102)

# SEPARATE: Similar but different
def configure_j1_shade_type(cluster, shade_type):
    """J1-specific: Configure window covering type."""
    # J1-specific attribute 0x1000

def configure_d1_phase_mode(cluster, mode):
    """D1-specific: Configure dimmer phase control."""
    # D1-specific attribute (ballast cluster)
```

**Why:** Premature abstraction is worse than duplication. Only abstract when you have 3+ identical use cases.

---

### 4. **Explicit Over Implicit**

Make intentions clear through naming and structure.

```python
# BAD: Implicit device type detection
def configure_device(hass, entity_id, settings):
    # Mystery: What device? What settings?
    pass

# GOOD: Explicit device-specific functions
def configure_j1_window_covering(hass, entity_id, shade_type):
    """Configure J1 window covering controller."""
    pass

def configure_d1_dimmer(hass, entity_id, phase_mode, ballast_config):
    """Configure D1 universal dimmer."""
    pass
```

**Why:** Code is read 10x more than written. Clarity trumps brevity.

---

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERFACE LAYER                     │
│  (Config Flow, Services, Lovelace Cards)                    │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  PLATFORM LAYER (Entities)                  │
│  ┌──────────────────┐         ┌──────────────────┐        │
│  │  UbisysCover     │         │  UbisysLight     │        │
│  │  (cover.py)      │         │  (light.py)      │        │
│  │                  │         │                  │        │
│  │  - J1 wrapper    │         │  - D1 wrapper    │        │
│  │  - Feature       │         │  - Feature       │        │
│  │    filtering     │         │    filtering     │        │
│  │  - Delegates to  │         │  - Delegates to  │        │
│  │    ZHA entity    │         │    ZHA entity    │        │
│  └──────────────────┘         └──────────────────┘        │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              BUSINESS LOGIC LAYER (Services)                │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │  j1_calibration.py│  │  d1_config.py    │               │
│  │                  │  │                  │               │
│  │  - J1 calibration│  │  - Phase mode    │               │
│  │  - 5-phase seq   │  │  - Ballast config│               │
│  │  - Stall detect  │  │  - Input config  │               │
│  └──────────────────┘  └──────────────────┘               │
│            ▲                      ▲                         │
│            │                      │                         │
│            └──────┬───────────────┘                         │
│                   ▼                                         │
│         ┌──────────────────┐                               │
│         │   helpers.py     │                               │
│         │                  │                               │
│         │  - Cluster access│                               │
│         │  - Device lookup │                               │
│         │  - Validation    │                               │
│         └──────────────────┘                               │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│               DATA ACCESS LAYER (ZHA Interface)             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  ZHA Gateway Access                                  │  │
│  │  - Get device by IEEE                                │  │
│  │  - Get cluster by endpoint + cluster_id              │  │
│  │  - Read/write attributes                             │  │
│  │  - Send commands                                     │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  DEVICE LAYER (Zigbee)                      │
│  ┌──────────────────┐         ┌──────────────────┐        │
│  │  J1 Device       │         │  D1 Device       │        │
│  │  (WindowCovering)│         │  (Dimmer)        │        │
│  └──────────────────┘         └──────────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

---

## Shared vs Device-Specific Code

### Shared Code (helpers.py)

**Purpose:** Utilities used by BOTH J1 and D1

**Functions:**
```python
async def get_cluster(hass, device_ieee, cluster_id, endpoint_id, cluster_name):
    """Get any cluster from any Ubisys device.

    This is the foundational function for all cluster access.
    Both J1 and D1 use this to get their respective clusters.

    Args:
        hass: Home Assistant instance
        device_ieee: Device IEEE address (string)
        cluster_id: Zigbee cluster ID (e.g., 0x0102 for WindowCovering)
        endpoint_id: Endpoint number (e.g., 2 for J1, 4 for D1)
        cluster_name: Human-readable name for error messages

    Returns:
        Cluster object or None if not found

    Why shared:
        The mechanism to access ZHA clusters is identical for all devices.
        Only the cluster_id and endpoint_id differ.
    """

async def validate_entity_ready(hass, entity_id, expected_platform=None):
    """Validate entity exists and is ready for operations.

    Performs common pre-flight checks used by both J1 and D1:
    - Entity exists in state registry
    - Entity is available (not offline)
    - Entity platform matches expected (if specified)

    Args:
        hass: Home Assistant instance
        entity_id: Entity ID to validate
        expected_platform: Expected platform ("ubisys" or None)

    Raises:
        HomeAssistantError: With specific error message

    Why shared:
        Validation logic is identical for covers and lights.
    """

def get_device_model(config_entry):
    """Extract device model from config entry.

    Args:
        config_entry: HA config entry

    Returns:
        Device model string (e.g., "J1", "D1")

    Why shared:
        All devices store model in the same config entry structure.
    """
```

**Why these are shared:**
- Logic is 100% identical
- Used by multiple device types
- Reduces code duplication
- Single source of truth for validation/access patterns

---

### J1-Specific Code (j1_calibration.py)

**Purpose:** Window covering calibration (ONLY used by J1)

**Why separate:**
- D1 doesn't need calibration
- Complex domain-specific logic (motor stall detection, phase sequencing)
- Different Zigbee attributes (configured_mode, total_steps, tilt_steps)

**Functions:**
- `async_calibrate_window_covering()` - Service handler
- `_perform_calibration()` - 5-phase orchestrator
- `_calibration_phase_1_enter_mode()` through `_calibration_phase_5_finalize()`
- `_wait_for_stall()` - Stall detection algorithm

**Dependencies:**
- Uses `helpers.get_cluster()` for cluster access (shared)
- Uses J1-specific constants from `const.py`

---

### D1-Specific Code (d1_config.py)

**Purpose:** Dimmer configuration (ONLY used by D1)

**Why separate:**
- J1 doesn't have phase control or ballast configuration
- Different Zigbee clusters (Ballast, DeviceSetup)
- Different configuration parameters

**Functions:**
```python
async def async_configure_phase_mode(hass, call):
    """Configure D1 phase control mode.

    D1-specific because:
    - Only D1 has phase control (forward/reverse/automatic)
    - Uses ballast cluster with manufacturer-specific attributes
    - J1 has completely different configuration (shade type)
    """

async def async_configure_ballast(hass, call):
    """Configure D1 ballast minimum/maximum levels.

    D1-specific because:
    - Ballast cluster only relevant to dimmers
    - Controls dimming behavior, not applicable to J1
    """

async def async_configure_inputs(hass, call):
    """Configure D1 physical input behavior.

    D1-specific because:
    - Different input requirements than J1
    - Uses DeviceSetup cluster (0xFC00) differently
    """
```

**Dependencies:**
- Uses `helpers.get_cluster()` for cluster access (shared)
- Uses D1-specific constants from `const.py`

---

## Module Responsibilities

### const.py - Central Constants Repository

**Responsibility:** Define ALL constants used across the integration

**Structure:**
```python
# ============================================================================
# GENERAL INTEGRATION CONSTANTS
# ============================================================================
DOMAIN = "ubisys"
MANUFACTURER = "ubisys"
UBISYS_MANUFACTURER_CODE = 0x10F2

# ============================================================================
# DEVICE MODEL CATEGORIZATION
# ============================================================================
WINDOW_COVERING_MODELS = ["J1", "J1-R"]
DIMMER_MODELS = ["D1", "D1-R"]
SWITCH_MODELS = ["S1", "S1-R", "S2", "S2-R"]  # Future

SUPPORTED_MODELS = (
    WINDOW_COVERING_MODELS
    + DIMMER_MODELS
    # + SWITCH_MODELS  # Uncomment when implementing
)

# ============================================================================
# J1 WINDOW COVERING CONSTANTS
# ============================================================================

# Shade types
SHADE_TYPE_ROLLER = "roller"
SHADE_TYPE_CELLULAR = "cellular"
# ... etc

# J1-specific attributes
UBISYS_ATTR_CONFIGURED_MODE = 0x1000  # Window covering type
UBISYS_ATTR_TOTAL_STEPS = 0x1002      # Total motor steps
UBISYS_ATTR_LIFT_TO_TILT_TRANSITION_STEPS = 0x1001

# Calibration constants
CALIBRATION_MODE_ATTR = 0x0017
CALIBRATION_MODE_ENTER = 0x02
CALIBRATION_MODE_EXIT = 0x00

# ============================================================================
# D1 DIMMER CONSTANTS
# ============================================================================

# Phase control modes
PHASE_MODE_AUTOMATIC = 0
PHASE_MODE_FORWARD = 1
PHASE_MODE_REVERSE = 2

PHASE_MODES = {
    "automatic": PHASE_MODE_AUTOMATIC,
    "forward": PHASE_MODE_FORWARD,
    "reverse": PHASE_MODE_REVERSE,
}

# Ballast cluster attributes (standard ZCL)
BALLAST_MIN_LEVEL_ATTR = 0x0011
BALLAST_MAX_LEVEL_ATTR = 0x0012

# D1-specific manufacturer attributes (if any)
# UBISYS_ATTR_PHASE_CONTROL_MODE = 0x0000  # In ballast cluster

# DeviceSetup cluster (shared between J1 and D1, but used differently)
DEVICE_SETUP_CLUSTER_ID = 0xFC00
DEVICE_SETUP_ATTR_INPUT_CONFIGS = 0x0000
DEVICE_SETUP_ATTR_INPUT_ACTIONS = 0x0001

# ============================================================================
# SERVICE NAMES
# ============================================================================

# Window covering services
SERVICE_CALIBRATE_COVER = "calibrate_cover"
SERVICE_CALIBRATE_J1 = "calibrate_j1"  # Deprecated alias

# Dimmer services
SERVICE_CONFIGURE_D1_PHASE_MODE = "configure_d1_phase_mode"
SERVICE_CONFIGURE_D1_BALLAST = "configure_d1_ballast"
SERVICE_CONFIGURE_D1_INPUTS = "configure_d1_inputs"

# ============================================================================
# CLUSTER IDS (Standard Zigbee)
# ============================================================================
CLUSTER_WINDOW_COVERING = 0x0102
CLUSTER_ON_OFF = 0x0006
CLUSTER_LEVEL_CONTROL = 0x0008
CLUSTER_BALLAST = 0x0301
CLUSTER_METERING = 0x0702
CLUSTER_ELECTRICAL_MEASUREMENT = 0x0B04

# ============================================================================
# ENDPOINT IDS
# ============================================================================
J1_WINDOW_COVERING_ENDPOINT = 2
D1_DIMMER_ENDPOINT = 4
D1_METERING_ENDPOINT = 5
```

**Why this structure:**
- One place for all constants (easy to find)
- Grouped by device type (easy to navigate)
- Clear comments explaining purpose
- Version control-friendly (see what changed)

---

### helpers.py - Shared Utilities

**Responsibility:** Provide common utilities for cluster access, validation, device lookup

**Key Functions:**

```python
async def get_cluster(
    hass: HomeAssistant,
    device_ieee: str,
    cluster_id: int,
    endpoint_id: int,
    cluster_name: str = "Unknown"
) -> Cluster | None:
    """Get a Zigbee cluster from a device.

    This is the core function for accessing Zigbee clusters. Used by both
    J1 and D1 implementations to get their respective clusters.

    How it works:
        1. Convert IEEE string → EUI64 object
        2. Access ZHA gateway
        3. Look up device in gateway's device registry
        4. Find endpoint
        5. Find cluster within endpoint
        6. Return cluster object

    Args:
        hass: Home Assistant instance
        device_ieee: IEEE address string (e.g., "00:12:4b:00:...")
        cluster_id: Zigbee cluster ID (e.g., 0x0102 for WindowCovering)
        endpoint_id: Endpoint number (e.g., 2 for J1, 4 for D1)
        cluster_name: Human-readable name for error messages

    Returns:
        Cluster object for direct Zigbee access, or None if not found

    Raises:
        HomeAssistantError: If IEEE address is invalid

    Example:
        # J1: Get WindowCovering cluster
        cluster = await get_cluster(
            hass, ieee, 0x0102, 2, "WindowCovering"
        )

        # D1: Get Ballast cluster
        cluster = await get_cluster(
            hass, ieee, 0x0301, 4, "Ballast"
        )

    Why shared:
        The mechanism to access ZHA clusters is identical regardless
        of device type. Only the cluster_id and endpoint_id differ.
    """

async def get_entity_device_info(
    hass: HomeAssistant,
    entity_id: str
) -> tuple[str, str, str]:
    """Get device information from entity ID.

    Looks up device_id, device_ieee, and model from an entity.

    Args:
        hass: Home Assistant instance
        entity_id: Entity ID (e.g., "cover.bedroom_j1")

    Returns:
        Tuple of (device_id, device_ieee, model)

    Raises:
        HomeAssistantError: If entity not found or missing data

    Why shared:
        Both J1 and D1 entities need to look up their parent device.
    """

async def validate_ubisys_entity(
    hass: HomeAssistant,
    entity_id: str,
    expected_platform: str | None = None
) -> None:
    """Validate entity is Ubisys entity and ready for operations.

    Checks:
        - Entity exists in registry
        - Entity platform is "ubisys" (if expected_platform specified)
        - Entity is available (not offline)

    Args:
        hass: Home Assistant instance
        entity_id: Entity to validate
        expected_platform: Expected platform ("ubisys" or None to skip check)

    Raises:
        HomeAssistantError: With specific error message

    Why shared:
        Validation logic is identical for covers, lights, switches.
    """

def get_device_type(model: str) -> str:
    """Get device type category from model string.

    Args:
        model: Device model (e.g., "J1", "D1", "S1")

    Returns:
        Device type: "window_covering", "dimmer", "switch", or "unknown"

    Why shared:
        Multiple modules need to categorize devices.
    """

def supports_calibration(model: str) -> bool:
    """Check if device model supports calibration.

    Args:
        model: Device model string

    Returns:
        True if device supports calibration (window covering devices)

    Why shared:
        Used by button.py to conditionally create calibration button,
        and by config flow to show/hide calibration-related options.
    """
```

**Why these are shared:**
- Pure utility functions with no device-specific logic
- Prevent code duplication
- Single source of truth
- Easier to test

---

### j1_calibration.py - J1 Calibration Logic

**Responsibility:** Window covering calibration (J1-specific)

**NOT shared because:**
- D1 doesn't need calibration
- Complex domain-specific algorithm
- Uses J1-specific Zigbee attributes

**Dependencies:**
```python
from .helpers import (
    get_cluster,
    get_entity_device_info,
    validate_ubisys_entity,
)
from .const import (
    CALIBRATION_MODE_ATTR,
    UBISYS_ATTR_TOTAL_STEPS,
    # ... other J1 constants
)
```

---

### d1_config.py - D1 Configuration Logic

**Responsibility:** Dimmer-specific configuration (D1-specific)

**NOT shared because:**
- J1 doesn't have phase control or ballast config
- Uses D1-specific Zigbee attributes
- Different parameter validation

**Dependencies:**
```python
from .helpers import (
    get_cluster,
    get_entity_device_info,
    validate_ubisys_entity,
)
from .const import (
    PHASE_MODES,
    BALLAST_MIN_LEVEL_ATTR,
    CLUSTER_BALLAST,
    # ... other D1 constants
)
```

---

## Data Flow Examples

### J1 Calibration Flow

```
User clicks calibration button
    │
    ▼
UbisysCalibrationButton.async_press()
    │
    ▼
hass.services.async_call("ubisys", "calibrate_cover")
    │
    ▼
calibration.async_calibrate_window_covering(hass, call)
    │
    ├─→ helpers.validate_ubisys_entity(entity_id)  [SHARED]
    ├─→ helpers.get_entity_device_info(entity_id)  [SHARED]
    ├─→ helpers.get_cluster(ieee, 0x0102, 2)       [SHARED]
    │
    ▼
calibration._perform_calibration()
    │
    ├─→ _calibration_phase_1_enter_mode()          [J1-SPECIFIC]
    ├─→ _calibration_phase_2_find_top()            [J1-SPECIFIC]
    ├─→ _calibration_phase_3_find_bottom()         [J1-SPECIFIC]
    ├─→ _calibration_phase_4_verify()              [J1-SPECIFIC]
    └─→ _calibration_phase_5_finalize()            [J1-SPECIFIC]
```

**Separation of concerns:**
- `helpers` handles cluster access (shared pattern)
- `calibration` handles domain logic (J1-specific)

---

### D1 Phase Mode Configuration Flow

```
User calls service
    │
    ▼
service: ubisys.configure_d1_phase_mode
data:
  entity_id: light.bedroom_dimmer
  mode: forward
    │
    ▼
d1_config.async_configure_phase_mode(hass, call)
    │
    ├─→ helpers.validate_ubisys_entity(entity_id)  [SHARED]
    ├─→ helpers.get_entity_device_info(entity_id)  [SHARED]
    ├─→ helpers.get_cluster(ieee, 0x0301, 4)       [SHARED]
    │
    ▼
d1_config._write_phase_mode(cluster, mode_value)   [D1-SPECIFIC]
    │
    └─→ cluster.write_attributes({...})
```

**Separation of concerns:**
- `helpers` handles validation and cluster access (shared)
- `d1_config` handles dimmer-specific logic (D1-specific)

---

## Testing Strategy

### Unit Tests

**Shared code (helpers.py):**
```python
# tests/test_helpers.py
async def test_get_cluster_success():
    """Test successful cluster retrieval."""

async def test_get_cluster_invalid_ieee():
    """Test error handling for invalid IEEE."""

async def test_validate_entity_not_found():
    """Test validation fails for missing entity."""
```

**J1-specific (j1_calibration.py):**
```python
# tests/test_j1_calibration.py
async def test_calibration_phase_1():
    """Test entering calibration mode."""

async def test_stall_detection():
    """Test motor stall detection algorithm."""
```

**D1-specific (d1_config.py):**
```python
# tests/test_d1_config.py
async def test_configure_phase_mode_forward():
    """Test setting phase mode to forward."""

async def test_ballast_min_level_validation():
    """Test validation of ballast minimum level."""
```

---

## Summary of Separation Patterns

| Code | J1 | D1 | Shared | Rationale |
|------|----|----|--------|-----------|
| **Cluster access** | ❌ | ❌ | ✅ | Mechanism identical |
| **Entity validation** | ❌ | ❌ | ✅ | Logic identical |
| **Device type helpers** | ❌ | ❌ | ✅ | Used by multiple modules |
| **Calibration logic** | ✅ | ❌ | ❌ | J1-specific algorithm |
| **Phase mode config** | ❌ | ✅ | ❌ | D1-specific feature |
| **Ballast config** | ❌ | ✅ | ❌ | D1-specific feature |
| **Constants** | ✅ | ✅ | ✅ | All in one place |

**Key Insight:** Share infrastructure (cluster access, validation), separate domain logic (calibration, dimmer config).

---

## Benefits of This Architecture

### 1. **Maintainability**
- Each module has clear, focused responsibility
- Changes to J1 don't affect D1 and vice versa
- Shared code prevents duplication bugs

### 2. **Testability**
- Small, focused functions are easier to test
- Mock dependencies (cluster access) are centralized
- Domain logic can be tested independently

### 3. **Extensibility**
- Adding S1 switch support: Create `s1_config.py`, reuse `helpers.py`
- Adding new J1 features: Modify only `j1_calibration.py`
- Adding new shared utility: Add to `helpers.py`, all devices benefit

### 4. **Readability**
- Clear file names indicate purpose
- Explicit function names reduce cognitive load
- Comments explain "why" not "what"

### 5. **Performance**
- No unnecessary abstractions (no performance overhead)
- Direct cluster access (no intermediate layers)
- Validation happens once at service entry point

---

## Anti-Patterns Avoided

### ❌ **God Object**
We DON'T have a single `UbisysDevice` class that tries to handle everything:
```python
# BAD
class UbisysDevice:
    def calibrate(self):
        if self.model == "J1":
            # J1 calibration
        elif self.model == "D1":
            # D1 doesn't calibrate, error?
        # This becomes unmaintainable

    def configure(self, settings):
        if self.model == "J1":
            # Configure shade type
        elif self.model == "D1":
            # Configure phase mode
        # Logic becomes spaghetti
```

**Why bad:** Changes affect all device types, testing is complex, hard to reason about.

### ❌ **Premature Abstraction**
We DON'T create abstract base classes before we need them:
```python
# BAD
class AbstractUbisysDevice(ABC):
    @abstractmethod
    async def configure(self):
        pass

    @abstractmethod
    async def validate(self):
        pass
```

**Why bad:** We only have 2 device types. Abstraction adds complexity without benefit.

### ❌ **Circular Dependencies**
We DON'T let modules import each other:
```python
# BAD
# j1_calibration.py imports d1_config.py
# d1_config.py imports j1_calibration.py
```

**Why bad:** Circular imports cause loading issues, tight coupling.

**Our solution:** Both import from `helpers.py`, which imports nothing (leaf module).

---

## Conclusion

This architecture balances:
- **Code reuse** (shared utilities)
- **Separation** (device-specific logic isolated)
- **Simplicity** (no unnecessary abstractions)
- **Clarity** (explicit naming, focused modules)

**Result:** Easy to maintain, test, and extend.
