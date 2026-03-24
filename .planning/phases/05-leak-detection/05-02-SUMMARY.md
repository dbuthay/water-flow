---
phase: 05-leak-detection
plan: 02
subsystem: sensor, button, testing
tags: [home-assistant, coordinator, leak-detection, zone-status, acknowledge-button, pytest]

requires:
  - phase: 05-01
    provides: coordinator leak detection engine (_leak_statuses, _ramp_up_counters, _leak_notified, _zone_was_on)
  - phase: 04-calibration
    provides: CalibrateButtonEntity pattern, async_create notification pattern

provides:
  - ZoneStatusSensor per zone reading coordinator._leak_statuses (idle/running/leak_detected)
  - AcknowledgeLeakButtonEntity per zone resetting leak status via async_update_listeners
  - 11 passing leak detection tests covering DETECT-01 through DETECT-04 + acknowledge flow

affects: [06-lovelace-card, future-phases-reading-zone-status]

tech-stack:
  added: []
  patterns:
    - "ZoneStatusSensor reads coordinator dict directly (not ZoneData) for persistent state"
    - "AcknowledgeLeakButtonEntity uses async_update_listeners() not async_request_refresh() to avoid Flume poll"
    - "Test pattern: patch.object coordinator._turn_valve with AsyncMock to avoid ServiceNotFound in test harness"

key-files:
  created:
    - tests/test_leak.py
  modified:
    - custom_components/irrigation_monitor/sensor.py
    - custom_components/irrigation_monitor/button.py

key-decisions:
  - "ZoneStatusSensor omits _attr_state_class and _attr_device_class — text enum values incompatible with HA statistics recorder"
  - "AcknowledgeLeakButtonEntity.async_press calls async_update_listeners() as a @callback (no await) to push state to all CoordinatorEntity listeners without triggering Flume network poll"
  - "Tests mock coordinator._turn_valve via patch.object(AsyncMock) to avoid ServiceNotFound — switch/valve services not registered in pytest-homeassistant test harness"

patterns-established:
  - "Pattern: mock _turn_valve in tests that trigger leak detection to avoid ServiceNotFound from test harness"
  - "Pattern: ZoneStatusSensor.native_value reads coordinator._leak_statuses.get(zone_id, 'idle') directly"

requirements-completed: [DETECT-01, DETECT-02, DETECT-03, DETECT-04, DETECT-05]

duration: 11min
completed: 2026-03-24
---

# Phase 5 Plan 02: Leak Detection Entities and Green Tests Summary

**ZoneStatusSensor (idle/running/leak_detected) and AcknowledgeLeakButtonEntity wired per zone, with 11 passing leak detection tests covering DETECT-01 through DETECT-04 plus acknowledge button flow**

## Performance

- **Duration:** 11 min
- **Started:** 2026-03-24T05:59:55Z
- **Completed:** 2026-03-24T06:11:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added ZoneStatusSensor to sensor.py: reads coordinator._leak_statuses, no state_class, no device_class, wired per zone in async_setup_entry
- Added AcknowledgeLeakButtonEntity to button.py: async_press resets status to idle and calls async_update_listeners() (not async_request_refresh), wired per zone in async_setup_entry
- Replaced all 10 xfail stubs in test_leak.py with passing implementations, plus added 11th test for acknowledge button; full suite 43 tests green

## Task Commits

Each task was committed atomically:

1. **Task 1: Add ZoneStatusSensor and AcknowledgeLeakButtonEntity** - `57ee068` (feat)
2. **Task 2: Turn all 11 leak tests GREEN** - `4280d6c` (test)

## Files Created/Modified

- `custom_components/irrigation_monitor/sensor.py` - Added ZoneStatusSensor class and wired in async_setup_entry loop
- `custom_components/irrigation_monitor/button.py` - Added AcknowledgeLeakButtonEntity class and converted list comprehension to loop in async_setup_entry
- `tests/test_leak.py` - Replaced all xfail stubs with 11 full test implementations

## Decisions Made

- ZoneStatusSensor omits `_attr_state_class` and `_attr_device_class` — text enum values "idle"/"running"/"leak_detected" have no matching HA device class and are incompatible with HA statistics recorder
- AcknowledgeLeakButtonEntity uses `async_update_listeners()` (a `@callback`, no await needed) rather than `async_request_refresh()` — avoids triggering an unnecessary Flume network poll on acknowledge
- Tests mock `_turn_valve` via `patch.object(coordinator, "_turn_valve", new_callable=AsyncMock)` — the `switch` and `valve` domain services are not registered in the pytest-homeassistant test harness, causing ServiceNotFound. This is the correct pattern for tests that exercise leak detection but are not specifically testing shutoff behavior.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Mocked _turn_valve in tests to fix ServiceNotFound in test harness**
- **Found during:** Task 2 (test_leak_detection_fires, first run)
- **Issue:** coordinator._turn_valve calls `hass.services.async_call("switch", "turn_off", ...)` with `blocking=True`. The pytest-homeassistant test harness does not register switch/valve services, so the call raises `ServiceNotFound`, causing the coordinator refresh to fail with status "unavailable".
- **Fix:** Added `patch.object(coordinator, "_turn_valve", new_callable=AsyncMock)` to all tests that trigger leak detection but are not specifically testing the shutoff mechanism. Tests that ARE testing shutoff (test_leak_triggers_shutoff, test_leak_no_shutoff_when_disabled) use the same mock but with assertions.
- **Files modified:** tests/test_leak.py
- **Verification:** All 11 tests pass; full suite 43 tests green
- **Committed in:** 4280d6c (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug in test setup)
**Impact on plan:** Fix is necessary for tests to run correctly in the test harness. The production coordinator code is unchanged — _turn_valve works correctly in real HA. This is a test infrastructure pattern, not a production code change.

## Issues Encountered

- None beyond the _turn_valve ServiceNotFound issue documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 6 (Lovelace card) can read `sensor.irrigation_monitor_{zone_id}_status` to display idle/running/leak_detected per zone
- All DETECT-01 through DETECT-05 requirements satisfied
- Full test suite green (43 tests)

## Self-Check: PASSED

- FOUND: custom_components/irrigation_monitor/sensor.py
- FOUND: custom_components/irrigation_monitor/button.py
- FOUND: tests/test_leak.py
- FOUND: .planning/phases/05-leak-detection/05-02-SUMMARY.md
- FOUND commit 57ee068 (feat(05-02): add ZoneStatusSensor and AcknowledgeLeakButtonEntity)
- FOUND commit 4280d6c (test(05-02): implement 11 leak detection tests GREEN)
- Tests: 43 passed

---
*Phase: 05-leak-detection*
*Completed: 2026-03-24*
