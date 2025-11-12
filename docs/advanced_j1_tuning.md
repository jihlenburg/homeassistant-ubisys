# Advanced J1 Tuning

This guide explains how to tune advanced manufacturer-specific attributes on Ubisys J1/J1‑R using the integration’s service and options flow.

What you can set

- Turnaround Guard Time (0x1000): Delay between reversing direction, in 50ms units (e.g., 10 = 500ms).
- Inactive Power Threshold (0x1006): Motor inactive threshold in milliwatts (e.g., 4096 ≈ 4.1W).
- Startup Steps (0x1007): Number of AC waves to run on startup.
- Additional Steps (0x1005): Overtravel percentage (0–100) to improve limit contact.

How to apply

- Options Flow: Settings → Devices & Services → Ubisys → [Your J1] → Configure → “J1 Advanced”
- Service: `ubisys.tune_j1_advanced` with fields `entity_id`, and any of `turnaround_guard_time`, `inactive_power_threshold`, `startup_steps`, `additional_steps`.

Verification

- Writes are verified by reading back the attributes; a mismatch raises an error.
- Values persist across reboots.

Tips

- Make small, incremental changes and test in between.
- Avoid setting guard time too low for safety and mechanical longevity.
