---
phase: 04-calibration
plan: 01
subsystem: integration
tags: [homeassistant, button, coordinator, calibration, pytest]

# Dependency graph
requires:
  - phase: 03-coordinator-usage
    provides: IrrigationCoordinator with _zone_is_on, DataUpdateCoordinator pattern, sensor entity pattern
provides:
  - CalibrateButtonEntity per zone with async_press firing background task via async_create_background_task
  - 12 xfail test stubs for CALIB-01 through CALIB-06 collected by pytest
  - 7 calibration constants in const.py (CONF_BACKGROUND_THRESHOLD, DEFAULT_BACKGROUND_THRESHOLD, VARIANCE_THRESHOLD, STABILIZATION_TIMEOUT, STABILIZATION_POLL_INTERVAL, SAMPLE_COUNT, SAMPLE_INTERVAL)
  - coordinator._pending_calibrations dict and _calibrating set for Plan 04-02 guard logic
  - coordinator.async_calibrate_zone stub (raises NotImplementedError; Plan 04-02 implements it)
affects: [04-02-calibration-sequence, 05-leak-detection]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - ButtonEntity with CoordinatorEntity double-inheritance (same as sensor pattern)
    - async_create_background_task for fire-and-forget calibration from async_press
    - xfail test stubs (Wave 0) — collected by pytest, all marked not implemented

key-files:
  created:
    - custom_components/irrigation_monitor/button.py
    - tests/test_button.py
  modified:
    - custom_components/irrigation_monitor/const.py
    - custom_components/irrigation_monitor/__init__.py
    - custom_components/irrigation_monitor/coordinator.py

key-decisions:
  - "async_press uses entry.async_create_background_task (not asyncio.create_task) — returns immediately, background task runs the ~60-90s calibration sequence"
  - "async_calibrate_zone stub raises NotImplementedError — Plan 04-02 replaces this with full implementation"
  - "Wave 0 test stubs use @pytest.mark.xfail(reason=not implemented) so they are collected but do not fail the suite"

patterns-established:
  - "Button platform: CalibrateButtonEntity(CoordinatorEntity[IrrigationCoordinator], ButtonEntity) mirrors sensor entity pattern"
  - "Background task pattern: entry.async_create_background_task(hass, coro, name=...) for long-running async work from button press"

requirements-completed: [CALIB-01]

# Metrics
duration: 3min
completed: 2026-03-24
---

# Phase 4 Plan 01: Calibration Scaffold Summary

**CalibrateButtonEntity per zone firing background calibration task via async_create_background_task, with 12 xfail test stubs and coordinator guard structures for Plan 04-02**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-24T05:07:01Z
- **Completed:** 2026-03-24T05:10:08Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Created button.py with CalibrateButtonEntity that fires calibration as a background task on async_press
- Added 12 xfail test stubs to tests/test_button.py covering CALIB-01 through CALIB-06, all collected by pytest
- Extended coordinator with _pending_calibrations dict, _calibrating set, and async_calibrate_zone stub

## Task Commits

Each task was committed atomically:

1. **Task 1: Wave 0 test stubs + constants** - `ee9bc32` (test)
2. **Task 2: CalibrateButtonEntity + coordinator calibration stub** - `4e36ae2` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `custom_components/irrigation_monitor/button.py` - CalibrateButtonEntity with async_press using async_create_background_task
- `tests/test_button.py` - 12 xfail stubs for CALIB-01 through CALIB-06
- `custom_components/irrigation_monitor/const.py` - 7 calibration constants added
- `custom_components/irrigation_monitor/__init__.py` - PLATFORMS extended to include "button"
- `custom_components/irrigation_monitor/coordinator.py` - _pending_calibrations, _calibrating, async_calibrate_zone stub; asyncio/statistics/persistent_notification imports added

## Decisions Made

- `entry.async_create_background_task` chosen over `asyncio.create_task` per HA best practices — ties task lifecycle to config entry, not raw event loop
- Stub pattern (`raise NotImplementedError`) used for `async_calibrate_zone` so button.py can import and reference it without import errors before Plan 04-02

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 04-02 can now implement `async_calibrate_zone` with the full calibration sequence
- Guard structures (`_pending_calibrations`, `_calibrating`) are in place
- All existing tests remain green (20 passed, 12 xfailed)
- Phase 5 (leak detection) reads `calibrated_flow` from ConfigEntry.options — write path established in this scaffold

---
*Phase: 04-calibration*
*Completed: 2026-03-24*

## Self-Check: PASSED

- `custom_components/irrigation_monitor/button.py` - FOUND
- `tests/test_button.py` - FOUND
- `custom_components/irrigation_monitor/const.py` contains CONF_BACKGROUND_THRESHOLD - FOUND
- `custom_components/irrigation_monitor/__init__.py` contains "button" - FOUND
- `custom_components/irrigation_monitor/coordinator.py` contains _pending_calibrations - FOUND
- Commit `ee9bc32` - FOUND
- Commit `4e36ae2` - FOUND
