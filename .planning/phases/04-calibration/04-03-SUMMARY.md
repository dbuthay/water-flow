---
phase: 04-calibration
plan: "03"
subsystem: calibration
tags: [homeassistant, coordinator, persistent-notification, event-bus, mobile-app-action]

# Dependency graph
requires:
  - phase: 04-calibration-02
    provides: async_calibrate_zone with re-calibration branch stub and _write_calibrated_flow
provides:
  - _register_calibration_action_listener method handling Save/Cancel via mobile_app_notification_action events
  - Re-calibration notification fires via service call with actions list
  - Event listener cleanup via entry.async_on_unload
  - GREEN tests for re-calibration pending and save/cancel flows (12/12 tests passing)
affects: [05-leak-detection, phase-gate]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "One-shot event listener: register with hass.bus.async_listen, unsubscribe inside handler after first matching action, register unsub with entry.async_on_unload for cleanup if entry unloads first"
    - "Action-button notification: use hass.services.async_call('persistent_notification', 'create', {...}) with actions list — NOT async_create() which has no actions param"

key-files:
  created: []
  modified:
    - custom_components/irrigation_monitor/coordinator.py
    - tests/test_button.py

key-decisions:
  - "Service call layer (hass.services.async_call) required for action-button notifications — programmatic async_create() has no actions parameter"
  - "One-shot listener pattern: return without unsubscribing for irrelevant actions; call unsub() only on matching save or cancel action"
  - "entry.async_on_unload(unsub) guarantees listener cleanup if user never responds before HA restart"

patterns-established:
  - "One-shot event listener: unsub inside handler + entry.async_on_unload for leak-safe cleanup"

requirements-completed: [CALIB-04, CALIB-05, CALIB-06]

# Metrics
duration: 8min
completed: 2026-03-24
---

# Phase 04 Plan 03: Re-calibration Action-Button Flow Summary

**Re-calibration Save/Cancel with mobile_app_notification_action event listener and service-call action-button notification**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-24T05:10:00Z
- **Completed:** 2026-03-24T05:18:25Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Added `_register_calibration_action_listener` method: registers one-shot event listener for `mobile_app_notification_action` bus events; Save writes new flow to ConfigEntry.options and clears pending; Cancel discards pending and dismisses notification
- Updated re-calibration branch to use `hass.services.async_call("persistent_notification", "create", ...)` with `actions` list instead of `async_create()` (which has no actions param)
- Replaced 2 xfail stubs with real tests covering pending storage, Save path (options written), and Cancel path (options unchanged, pending cleared)
- Full suite: 32 passed, 0 xfailed

## Task Commits

Each task was committed atomically:

1. **Task 1: Add _register_calibration_action_listener and update re-cal notification** - `3a0c531` (feat)
2. **Task 2: GREEN tests for re-calibration path** - `2c74f27` (feat)

**Plan metadata:** (docs commit below)

## Files Created/Modified
- `custom_components/irrigation_monitor/coordinator.py` - Added Event/callback imports, _register_calibration_action_listener method, updated re-calibration branch to service call with actions
- `tests/test_button.py` - Replaced 2 xfail stubs with full test_recalibration_pending_flow and test_recalibration_save_action implementations

## Decisions Made
- Service call layer required for action buttons — `async_create()` programmatic API has no `actions` parameter (confirmed from research and HA source)
- One-shot listener design: irrelevant actions return immediately without unsubscribing; matching action calls `unsub()` after handling — prevents listener accumulation across zones
- `entry.async_on_unload(unsub)` registered alongside the listener so it is cleaned up if the config entry is unloaded before the user taps Save or Cancel

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required. Action buttons require HA Companion app (iOS/Android); they are not rendered in the HA web frontend (known HA limitation documented in research).

## Next Phase Readiness
- Phase 4 calibration feature complete: all 12 button tests GREEN, full suite 32 passed
- `calibrated_flow` is correctly stored in ConfigEntry.options and survives HA restarts
- Phase 5 (Leak Detection) can read `calibrated_flow` from `entry.options["zones"][zone_id]["calibrated_flow"]` — write path is correct

---
*Phase: 04-calibration*
*Completed: 2026-03-24*
