---
phase: 04-calibration
plan: 02
subsystem: coordinator
tags: [homeassistant, calibration, button, persistent-notification, asyncio, statistics]

requires:
  - phase: 04-01
    provides: ButtonEntity scaffold with xfail test stubs, _calibrating and _pending_calibrations on coordinator

provides:
  - Full async_calibrate_zone implementation on IrrigationCoordinator
  - _turn_valve helper: routes switch.turn_on/off vs valve.open_valve/close_valve by entity domain
  - _write_calibrated_flow helper: safe nested MappingProxyType copy for ConfigEntry.options update
  - 10 GREEN tests for CALIB-01 through CALIB-06 first-calibration paths

affects:
  - 04-03 (re-calibration action buttons read from _pending_calibrations populated here)
  - 05-leak-detection (reads calibrated_flow written by _write_calibrated_flow)

tech-stack:
  added: []
  patterns:
    - Two-level try/finally for calibration: outer removes _calibrating set, inner ensures valve always off
    - Safe nested copy for MappingProxyType: dict() each level before mutating
    - asyncio.sleep patching in tests to control timing without real waits
    - side_effect on mock_sleep to simulate Flume state changes mid-calibration

key-files:
  created: []
  modified:
    - custom_components/irrigation_monitor/coordinator.py
    - tests/test_button.py

key-decisions:
  - "Two-level try/finally: outer finally removes _calibrating, inner finally turns valve off — early returns (background check, already-running) exit before valve on, so skip valve-off"
  - "Stabilization timeout test uses alternating Flume values (1.0/5.0) so stdev never drops below 0.05 threshold"
  - "Tests patch coordinator.asyncio.sleep with side_effect to update Flume state mid-loop without real sleeps"
  - "Re-calibration tests (test_recalibration_pending_flow, test_recalibration_save_action) remain xfail for Plan 04-03"

patterns-established:
  - "Calibration guard: _calibrating set added at entry, discarded in outer finally — prevents duplicate concurrent runs"
  - "Valve domain dispatch: zone_id.split('.')[0] determines switch vs valve domain for service calls"
  - "Nested options copy: dict(entry.options) -> dict(zones) -> dict(zone_cfg) -> mutate -> reassemble"

requirements-completed: [CALIB-02, CALIB-03, CALIB-04, CALIB-05, CALIB-06]

duration: 2min
completed: 2026-03-23
---

# Phase 4 Plan 02: Calibration Sequence Implementation Summary

**Full async_calibrate_zone with variance detection, 3-sample averaging, MappingProxyType-safe options write, and 10 GREEN first-calibration tests covering CALIB-01 through CALIB-06**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-23T20:12:11Z
- **Completed:** 2026-03-23T20:14:28Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Replaced `async_calibrate_zone` stub with full 150-line implementation: background flow check, already-running guard, variance detection loop using `statistics.stdev`, 3-sample averaging, first-calibration options write, failure handling
- Added `_turn_valve` helper that dispatches `switch.turn_on/off` vs `valve.open_valve/close_valve` based on entity domain prefix
- Added `_write_calibrated_flow` helper using safe 3-level nested copy pattern to avoid MappingProxyType mutation errors
- Replaced 10 xfail test stubs with working implementations — all 10 pass, 2 re-calibration stubs remain xfail for Plan 04-03

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement async_calibrate_zone core sequence** - `b4ccde0` (feat)
2. **Task 2: GREEN tests for first-calibration path** - `c14627d` (feat)

## Files Created/Modified

- `custom_components/irrigation_monitor/coordinator.py` - Added `_turn_valve`, `_write_calibrated_flow`, and full `async_calibrate_zone` replacing NotImplementedError stub
- `tests/test_button.py` - Replaced 10 xfail stubs with working test implementations; 2 re-calibration tests remain xfail

## Decisions Made

- Two-level try/finally: the outer try removes `_calibrating` (always); the inner try ensures valve off (only reached after valve on). Early returns for background flow and already-running bypass the inner try entirely — correct behavior since valve was never opened.
- Tests use `side_effect` on the patched `asyncio.sleep` to update Flume state between poll iterations, simulating realistic state transitions without real delays.
- Stabilization timeout test uses alternating 1.0/5.0 values so `statistics.stdev` always exceeds 0.05 threshold across 12 iterations (60s / 5s).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `async_calibrate_zone` fully implements the first-calibration path; Plan 04-03 adds re-calibration action buttons (Save/Cancel) using `_pending_calibrations` populated here
- `_write_calibrated_flow` writes `calibrated_flow` to `ConfigEntry.options` — Phase 5 leak detection reads this field to detect flow anomalies
- 2 xfail tests (`test_recalibration_pending_flow`, `test_recalibration_save_action`) are scaffolded and waiting for Plan 04-03 implementation

---
*Phase: 04-calibration*
*Completed: 2026-03-23*
