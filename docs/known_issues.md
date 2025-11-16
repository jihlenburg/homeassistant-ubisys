# Known Issues & Limitations

Current limitations, device support gaps, and planned features for the Ubisys integration.

> [!NOTE]
> This page documents known limitations and roadmap items. For bugs and issues, see [GitHub Issues](https://github.com/jihlenburg/homeassistant-ubisys/issues).

---

## 🚧 Device Support Gaps

###  S1/S1-R Power Switch

| Component | Status | Notes |
|-----------|--------|-------|
| Platform Wrapper | ✅ Implemented | Basic switch functionality |
| Input Configuration | ✅ Implemented | Options Flow presets |
| ZHA Quirk | ✅ Implemented | DeviceSetup cluster |
| Power Metering | ⚠️ Via ZHA | Standard sensors (no wrapper needed) |
| Advanced Features | 🔄 Evolving | Quirks and platform still being refined |

**Current limitations:**
- Input configuration presets are basic
- Advanced power metering features not fully exposed
- Needs more real-hardware testing

### S2/S2-R Dual Power Switch

| Status | ❌ Not Implemented |
|--------|-------------------|

**Required work:**
- Add `S2`, `S2-R` to `SWITCH_MODELS` constant
- Create platform support for dual endpoints
- Implement ZHA quirk with proper endpoint mapping
- Test with real hardware

**Blocker:** No S2 hardware available for testing

---

## 🔬 Hardware Validation Needed

The following features exist but **require real hardware testing** for validation:

### D1 Input Configuration

**Status:** ⚠️ Not Implemented

**Reason:** Requires understanding DeviceSetup cluster format with real hardware

**Workaround:** Default input configuration works for most users

**Status:** Phase 3 feature blocked pending hardware access

### D1 Phase Mode Configuration

**Status:** ⚠️ Implemented, needs validation

**Service:** `ubisys.configure_d1_phase_mode`

**Validation needed:**
- Behavior with different LED types
- Behavior with incandescent loads
- Behavior with halogen loads
- Phase mode persistence across power cycles

### J1 Calibration

**Status:** ✅ Mostly validated

**Known issues:**
- Very large shades (>3m) may timeout
- Needs testing across more shade types
- Edge cases with unusual motor behavior

---

## 📋 Planned Features (Roadmap)

See also: [Roadmap](roadmap.md)

<details>
<summary><strong>Input Monitoring Enhancements</strong></summary>

**Event Entities** (Phase 4)
- Show last button press in dashboard
- Display press history
- Timestamp of last event

**Binary Sensors** (Phase 5)
- For stationary rocker switches
- Show current state (on/off)
- Track state history

**Scene-Only Mode** (Phase 6)
- Buttons trigger automations only
- Disable local device control
- Useful for scene controllers
</details>

<details>
<summary><strong>J1 Window Covering Enhancements</strong></summary>

**Scene Support**
- Save preset positions
- Recall specific positions
- Name preset scenes

**Position Offset Configuration**
- Adjust reporting to match physical reality
- Useful when limits don't align with 0%/100%

**Speed Control**
- Configure motor speed
- Slow/medium/fast presets

**Web-Based Calibration Wizard**
- Interactive step-by-step guide
- Visual feedback during calibration
- Diagnostics and troubleshooting
</details>

<details>
<summary><strong>Energy Monitoring</strong></summary>

**Energy Dashboard Integration**
- Leverage S1/D1 0.5% accuracy power monitoring
- Energy metering dashboard
- Historical usage tracking
- Cost calculations

**Status:** Depends on S1 platform completion
</details>

<details>
<summary><strong>Developer Experience</strong></summary>

**Test Coverage** (Current: ~58%)
- Unit test suite expansion
- Integration test suite
- End-to-end testing framework
- Target: 80%+ coverage

**Documentation**
- Manual testing procedures (`docs/testing.md`)
- Contributor guidelines enhancement
- Architecture deep-dives
</details>

<details>
<summary><strong>Localization</strong></summary>

**Multi-Language Support**
- Currently: English, German, French, Spanish (partial)
- Target: Complete translations for all languages
- Community contributions welcome
</details>

---

## 📝 Documentation Gaps

### Missing Guides

- **S2/S2-R Configuration** - Blocked until device support implemented
- **Manual Testing Procedures** - No structured checklist for contributors
- **Translation Guide** - How to add new languages

### Incomplete Documentation

- **S1 Advanced Features** - Power metering integration with Energy dashboard
- **Performance Tuning** - Optimizing for large installations
- **Network Troubleshooting** - Zigbee mesh optimization

---

## 💡 Architectural Notes

### J1 Unused Attributes

Technical reference documents these manufacturer attributes:
- `0x1003` (LiftToTiltTransitionSteps2)
- `0x1004` (TotalSteps2)

**Status:** Not currently used by integration

**Reason:** Existing calibration approach works well without them

**Future:** May be useful for advanced scenarios

### Button→Service Pattern

Calibration button delegates to service for flexibility:
- ✅ UI access via button
- ✅ Automation access via service
- ✅ Single implementation (DRY)

**Tradeoff:** Slightly more complex than direct button action

### Wrapper Entity Architecture

Entities delegate to ZHA rather than talking directly to Zigbee:
- ✅ Leverages ZHA's excellent communication layer
- ✅ No need to reimplement Zigbee protocol
- ✅ Easier maintenance

**Tradeoff:** Dependency on ZHA entity existence

---

## 🔧 How You Can Help

### High Priority Contributions

<details>
<summary><strong>Hardware Testing</strong></summary>

**D1/D1-R Validation:**
- Test phase mode with various load types
- Validate ballast configuration
- Document LED compatibility

**J1 Calibration:**
- Test with more shade types
- Validate on large shades (>2m)
- Edge case discovery

**S1/S1-R:**
- Test input configuration presets
- Validate power metering accuracy
- Document real-world usage

</details>

<details>
<summary><strong>S2 Implementation</strong></summary>

**Requirements:**
- Access to S2 or S2-R hardware
- Python development experience
- Understanding of ZHA quirks

**Tasks:**
1. Add model constants
2. Implement dual-endpoint platform
3. Create ZHA quirk
4. Write tests
5. Document usage

</details>

<details>
<summary><strong>Test Suite Expansion</strong></summary>

**Current coverage:** ~58%
**Target:** 80%+

**Focus areas:**
- Input monitoring correlation
- Diagnostics content validation
- Calibration flow testing
- Config flow edge cases

</details>

<details>
<summary><strong>Documentation</strong></summary>

**Needed:**
- Translation to additional languages
- More automation examples
- Troubleshooting guides
- Video tutorials

</details>

---

## 📞 Reporting Issues

### Before Reporting

1. Check [Existing Issues](https://github.com/jihlenburg/homeassistant-ubisys/issues)
2. Review [Troubleshooting Guide](troubleshooting.md)
3. Enable debug logging
4. Gather diagnostics

### Issue Template

```markdown
**Home Assistant Version:** 2025.x.x
**Integration Version:** x.y.z
**Device Model:** J1 / D1 / S1 / etc.

**Expected Behavior:**
[What you expected to happen]

**Actual Behavior:**
[What actually happened]

**Steps to Reproduce:**
1. ...
2. ...

**Logs:**
```
[Paste relevant logs here]
```

**Diagnostics:**
[Attach diagnostics file if applicable]
```

### Where to Report

- **Bugs:** [GitHub Issues](https://github.com/jihlenburg/homeassistant-ubisys/issues)
- **Feature Requests:** [GitHub Discussions](https://github.com/jihlenburg/homeassistant-ubisys/discussions)
- **Questions:** [Home Assistant Forum](https://community.home-assistant.io/)

---

##  🔗 Related Documentation

- [Roadmap](roadmap.md) - Detailed future plans
- [Troubleshooting](troubleshooting.md) - Common problems and solutions
- [Contributing](../CONTRIBUTING.md) - Development guide
- [Architecture](architecture_overview.md) - Technical deep-dive
