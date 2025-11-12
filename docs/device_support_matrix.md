# Device Support Matrix

Compatibility: Home Assistant 2024.1+ (Python 3.11+)

This matrix summarizes supported devices, features, and key endpoints/clusters.

| Model  | Platform | Status            | Position | Tilt | Calibration | Phase/Ballast | Inputs (Controller EPs) | Notable Endpoints |
|--------|----------|-------------------|----------|------|-------------|---------------|-------------------------|-------------------|
| J1     | cover    | Fully supported   | ✅        | ✅    | ✅           | N/A           | EP2                     | EP1/EP2: 0x0102   |
| J1‑R   | cover    | Fully supported   | ✅        | ✅    | ✅           | N/A           | EP2                     | EP1/EP2: 0x0102   |
| D1     | light    | Supported         | N/A      | N/A  | N/A         | ✅             | EP2, EP3                | EP1: 0x0301, EP4  |
| D1‑R   | light    | Supported         | N/A      | N/A  | N/A         | ✅             | EP2, EP3                | EP1: 0x0301, EP4  |
| S1     | switch   | Evolving support  | N/A      | N/A  | N/A         | N/A           | EP2                     | EP3 (metering)    |
| S1‑R   | switch   | Evolving support  | N/A      | N/A  | N/A         | N/A           | EP2, EP3                | EP4 (metering)    |

Notes
- J1 WindowCovering cluster may appear on EP1 or EP2 depending on firmware; the integration probes both.
- D1 phase/ballast configuration exposed via services and Options; outputs must be OFF before changing mode.
- S1/S1‑R: Input presets via Options; advanced features and quirks continue to evolve.

