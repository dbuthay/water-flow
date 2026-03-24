---
phase: 04-calibration
verified: 2026-03-23T00:00:00Z
status: passed
score: 13/13 must-haves verified
re_verification: false
---

# Phase 4: Calibration Verification Report

**Phase Goal:** Users can calibrate the expected flow rate for each monitored zone through a button in the HA UI, with the result stored persistently and surviving HA restarts
**Verified:** 2026-03-23
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

All truths are drawn from the three plan `must_haves` blocks (04-01, 04-02, 04-03).

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | A calibrate button entity exists in HA for each monitored zone | VERIFIED | `button.py` creates one `CalibrateButtonEntity` per `CONF_MONITORED_ZONES` entry; `test_button_entities_created` asserts two entities in state machine |
| 2  | Pressing the calibrate button fires a background task (returns immediately) | VERIFIED | `async_press` calls `self._entry.async_create_background_task(...)` — never `await` |
| 3  | Background flow above threshold aborts calibration with notification | VERIFIED | `async_calibrate_zone` checks `current_flow > threshold` and fires `calib_{zone_id}_background` notification; `test_calibrate_aborts_on_background_flow` passes |
| 4  | Already-running zone aborts calibration with notification | VERIFIED | `_zone_is_on` guard fires `calib_{zone_id}_running` notification; `test_calibrate_aborts_when_zone_running` passes |
| 5  | Valve turns on, flow stabilizes via variance detection, 3 samples averaged | VERIFIED | `statistics.stdev(readings[-3:]) < VARIANCE_THRESHOLD` loop present; 3-sample averaging in coordinator; `test_calibration_full_sequence` and `test_calibration_stabilization_timeout` pass |
| 6  | First calibration writes calibrated_flow to ConfigEntry.options immediately | VERIFIED | `_write_calibrated_flow` uses nested dict copy + `async_update_entry`; `test_calibration_saves_to_options` asserts value in `entry.options` |
| 7  | Valve always turns off after calibration (success or failure) | VERIFIED | Inner `finally` block calls `await self._turn_valve(zone_id, turn_on=False)`; `test_calibration_turns_valve_off_on_success` and `test_calibration_turns_valve_off_on_failure` pass |
| 8  | Success notification shows the measured flow rate | VERIFIED | `f"Zone {zone_id} calibrated: {new_flow:.1f} gal/min"` fired; `test_calibration_success_notification` asserts "2.0 gal/min" in message |
| 9  | Stabilization timeout fires failure notification | VERIFIED | `raise RuntimeError("Flow did not stabilize within 60 seconds")` caught and notification fired; `test_calibration_stabilization_timeout` passes |
| 10 | Re-calibration stores pending result in coordinator memory (not persisted) | VERIFIED | `self._pending_calibrations[zone_id] = new_flow` in re-cal branch; old `calibrated_flow` unchanged; `test_recalibration_pending_flow` passes |
| 11 | Re-calibration fires notification with old vs new values and Save/Cancel actions | VERIFIED | `hass.services.async_call("persistent_notification", "create", {..., "actions": [...]})` with both action entries; `test_recalibration_pending_flow` passes |
| 12 | Save action writes new calibrated_flow to ConfigEntry.options | VERIFIED | `_handle_action` calls `_write_calibrated_flow` on save; `test_recalibration_save_action` asserts new value written |
| 13 | Event listener is cleaned up on entry unload | VERIFIED | `self._entry.async_on_unload(unsub)` registered in `_register_calibration_action_listener` (coordinator.py line 245) |

**Score:** 13/13 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `custom_components/irrigation_monitor/button.py` | CalibrateButtonEntity with async_press firing background task | VERIFIED | 55 lines; exports `async_setup_entry` and `CalibrateButtonEntity`; `async_create_background_task` on line 50 |
| `custom_components/irrigation_monitor/coordinator.py` | Full `async_calibrate_zone`, `_write_calibrated_flow`, `_turn_valve`, `_register_calibration_action_listener` | VERIFIED | All four methods present and substantive; `_pending_calibrations` and `_calibrating` on lines 57–58 |
| `custom_components/irrigation_monitor/const.py` | `CONF_BACKGROUND_THRESHOLD`, `DEFAULT_BACKGROUND_THRESHOLD`, `VARIANCE_THRESHOLD`, `STABILIZATION_TIMEOUT`, `STABILIZATION_POLL_INTERVAL`, `SAMPLE_COUNT`, `SAMPLE_INTERVAL` | VERIFIED | All 7 constants present on lines 32–38 |
| `custom_components/irrigation_monitor/__init__.py` | PLATFORMS includes "button" | VERIFIED | Line 10: `PLATFORMS: list[str] = ["sensor", "button"]` |
| `tests/test_button.py` | 12 passing tests for CALIB-01 through CALIB-06 | VERIFIED | 12 tests, 0 xfail, all GREEN; `test_recalibration_pending_flow` and `test_recalibration_save_action` both implemented |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `button.py async_press` | `coordinator.async_calibrate_zone` | `entry.async_create_background_task` | WIRED | `async_create_background_task` confirmed on button.py line 50 |
| `__init__.py` | `button.py` | PLATFORMS list includes "button" | WIRED | `PLATFORMS = ["sensor", "button"]` on __init__.py line 10; `async_forward_entry_setups` iterates PLATFORMS on line 20 |
| `coordinator.async_calibrate_zone` | `hass.services.async_call` | valve turn_on/off by domain | WIRED | `_turn_valve` dispatches `switch.turn_on/off` vs `valve.open_valve/close_valve`; tested with service call capture |
| `coordinator._write_calibrated_flow` | `hass.config_entries.async_update_entry` | nested dict copy for MappingProxyType safety | WIRED | 3-level nested copy pattern confirmed on coordinator.py lines 200–206 |
| `coordinator.async_calibrate_zone` | `statistics.stdev` | variance detection loop with 5s polling | WIRED | `statistics.stdev(readings[-3:])` on coordinator.py line 314 |
| `coordinator.async_calibrate_zone` | `persistent_notification.async_create` | progress, success, failure notifications | WIRED | Multiple `async_create(...)` calls throughout method |
| `coordinator._register_calibration_action_listener` | `hass.bus.async_listen` | mobile_app_notification_action event listener | WIRED | `hass.bus.async_listen("mobile_app_notification_action", _handle_action)` on coordinator.py line 241–242 |
| `coordinator._register_calibration_action_listener` | `coordinator._write_calibrated_flow` | Save action triggers options write | WIRED | `self._write_calibrated_flow(zone_id, new_flow)` on save branch line 225 |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| CALIB-01 | 04-01 | Button entity in HA UI per zone | SATISFIED | `CalibrateButtonEntity` created per zone in `async_setup_entry`; entities confirmed in state machine by test |
| CALIB-02 | 04-02 | Background flow check before calibration | SATISFIED | `current_flow > threshold` guard with notification; test passes |
| CALIB-03 | 04-02 | Abort if zone already running | SATISFIED | `_zone_is_on` guard with notification; test passes |
| CALIB-04 | 04-02, 04-03 | Valve on, stabilize, sample, average | SATISFIED | Full variance-detection loop + 3-sample averaging; stabilization timeout and mid-run Flume-unavailable cases tested |
| CALIB-05 | 04-02, 04-03 | Calibrated flow stored persistently, survives restarts | SATISFIED | Written to `ConfigEntry.options` via `async_update_entry`; re-calibration Save/Cancel flow complete; options survive HA restarts by HA design |
| CALIB-06 | 04-02, 04-03 | Valve turned off after calibration; user notified of flow rate | SATISFIED | `finally: await self._turn_valve(zone_id, turn_on=False)` guarantees valve off; success notification includes measured flow rate |

All 6 phase-4 requirements are SATISFIED.

---

### Anti-Patterns Found

None. Scan results:

- No `TODO`, `FIXME`, `XXX`, `HACK`, or `PLACEHOLDER` comments in any phase-4 file
- No `raise NotImplementedError` remaining in coordinator.py (stub replaced)
- No `return []` or `return {}` empty stubs in implementation files
- No `xfail` markers remaining in `tests/test_button.py`
- No console.log-only handlers

---

### Human Verification Required

The following items cannot be verified programmatically:

#### 1. Action Button Rendering (Companion App)

**Test:** On a device with the Home Assistant Companion App (iOS or Android), trigger a re-calibration on a zone that already has a calibrated_flow value. Look at the persistent notification.
**Expected:** Notification shows "Save" and "Cancel" action buttons that are tappable.
**Why human:** The `actions` list is included in the service call payload, but whether HA renders them as tappable buttons depends on Companion App support. The HA web frontend does NOT render action buttons — this is a known HA limitation documented in 04-03-SUMMARY.md. Unit tests verify the service call payload contains the correct action strings, but actual rendering requires a device.

#### 2. Persistence Across HA Restart

**Test:** Complete a calibration on a real HA instance (not test). Restart HA. Re-open the integration options or re-press the calibrate button.
**Expected:** The previously-measured calibrated_flow value is retained in `ConfigEntry.options`; re-pressing calibrate takes the re-calibration (pending) path, not the first-calibration path.
**Why human:** `ConfigEntry.options` persistence is guaranteed by HA core, but the actual write-reload-read cycle in production is distinct from the in-memory MockConfigEntry used in tests.

---

### Gaps Summary

No gaps. All must-haves from all three plans are satisfied by the actual codebase.

---

## Test Results

```
tests/test_button.py — 12 passed, 0 xfailed (0.20s)
Full suite (tests/) — 32 passed (0.32s)
```

---

_Verified: 2026-03-23_
_Verifier: Claude (gsd-verifier)_
