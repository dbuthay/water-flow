---
phase: 03-coordinator-usage
plan: 01
subsystem: coordinator
tags: [homeassistant, DataUpdateCoordinator, Store, sensor, irrigation, CoordinatorEntity]

# Dependency graph
requires:
  - phase: 02-config-flow
    provides: "ConfigEntry with data (flume_entity_id, monitored_zone_entity_ids, poll_interval) and options.zones per-zone config"
provides:
  - "IrrigationCoordinator: DataUpdateCoordinator subclass polling Flume, attributing flow to zones, accumulating daily usage"
  - "ZoneData dataclass: flow_rate + daily_usage + is_available per zone"
  - "sensor.py: DailyUsageSensor + FlowRateSensor (CoordinatorEntity subclasses), 2 entities per monitored zone"
  - "Store persistence: daily totals survive HA restarts, stale-date reset on startup, midnight reset via async_track_time_change"
  - "7 passing integration tests covering USAGE-01/02/03"
affects:
  - 04-calibration
  - 05-leak-detection
  - 06-dashboard

# Tech tracking
tech-stack:
  added:
    - homeassistant.helpers.update_coordinator.DataUpdateCoordinator
    - homeassistant.helpers.update_coordinator.CoordinatorEntity
    - homeassistant.helpers.update_coordinator.UpdateFailed
    - homeassistant.helpers.storage.Store (async_delay_save + async_save)
    - homeassistant.helpers.event.async_track_time_change
    - homeassistant.components.sensor.SensorDeviceClass.WATER + VOLUME_FLOW_RATE
    - homeassistant.const.UnitOfVolume.GALLONS + UnitOfVolumeFlowRate.GALLONS_PER_MINUTE
    - homeassistant.helpers.entity_platform.AddConfigEntryEntitiesCallback
  patterns:
    - "coordinator.py: DataUpdateCoordinator subclass with _async_setup + _async_update_data override"
    - "sensor.py: CoordinatorEntity + SensorEntity dual-inheritance; native_value from coordinator.data"
    - "__init__.py: coordinator → async_config_entry_first_refresh → runtime_data → async_forward_entry_setups ordering"
    - "Store flush on unload via entry.async_on_unload(_flush_store) for test reliability"
    - "Valve domain uses 'open'/'closed'; switch uses 'on'/'off' — checked via entity_id.split('.')[0]"

key-files:
  created:
    - custom_components/irrigation_monitor/coordinator.py
    - custom_components/irrigation_monitor/sensor.py
    - tests/test_coordinator.py
  modified:
    - custom_components/irrigation_monitor/__init__.py
    - custom_components/irrigation_monitor/const.py
    - tests/conftest.py

key-decisions:
  - "Store flush on entry unload via async_save (not just async_delay_save) so persistence test can reload immediately"
  - "Midnight reset turns zone off before midnight fire in test to avoid new increment from async_refresh() obscuring zero"
  - "entity.entity_id set explicitly on sensor entities using zone_slug (dots replaced with underscores) for predictable test entity IDs"
  - "type IrrigationConfigEntry = ConfigEntry[IrrigationCoordinator] added to __init__.py for type safety"

patterns-established:
  - "IrrigationCoordinator(hass, entry) — explicit config_entry= required (HA 2026.x)"
  - "entry.runtime_data = coordinator before async_forward_entry_setups"
  - "Zone active state: valve domain → state == 'open'; switch/binary_sensor → state == 'on'"
  - "Daily totals: accumulated in _daily_totals dict, written to Store with async_delay_save(fn, SAVE_DELAY)"

requirements-completed: [USAGE-01, USAGE-02, USAGE-03]

# Metrics
duration: 6min
completed: 2026-03-23
---

# Phase 3 Plan 01: Coordinator + Usage Summary

**IrrigationCoordinator (DataUpdateCoordinator) polling Flume every 30s, attributing flow to zones, accumulating daily gallons in Store-persisted totals with midnight reset — plus two CoordinatorEntity sensor entities per zone**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-23T21:17:30Z
- **Completed:** 2026-03-23T21:23:20Z
- **Tasks:** 2 (RED + GREEN TDD)
- **Files modified:** 6

## Accomplishments

- IrrigationCoordinator with Store load-on-setup, midnight reset, multi-zone attribution logic (calibrated vs uncalibrated zones, overlap detection), and explicit flush on entry unload
- DailyUsageSensor + FlowRateSensor per monitored zone, both CoordinatorEntity subclasses — entities go unavailable automatically when Flume raises UpdateFailed
- Full test suite: 7 coordinator tests + 13 existing = 20 passing (zero regressions)

## Task Commits

1. **Task 1 (RED): Test stubs and conftest fixtures** - `d814975` (test)
2. **Task 2 (GREEN): coordinator.py + sensor.py + __init__.py + const.py** - `e85d0e0` (feat)

## Files Created/Modified

- `custom_components/irrigation_monitor/coordinator.py` — IrrigationCoordinator + ZoneData dataclass
- `custom_components/irrigation_monitor/sensor.py` — DailyUsageSensor + FlowRateSensor
- `custom_components/irrigation_monitor/__init__.py` — PLATFORMS=["sensor"], coordinator wiring, IrrigationConfigEntry type alias
- `custom_components/irrigation_monitor/const.py` — STORAGE_KEY, STORAGE_VERSION, SAVE_DELAY added
- `tests/test_coordinator.py` — 7 integration tests (USAGE-01/02/03)
- `tests/conftest.py` — mock_config_entry fixture

## Decisions Made

- **Store flush on unload:** `async_delay_save` with SAVE_DELAY=30 won't flush during test entry reload. Added explicit `async_save` in `entry.async_on_unload` callback so persistence test (unload + reload) works correctly without mocking. This also benefits production: totals are guaranteed on disk before entry goes down.
- **Midnight test zone state:** `_midnight_reset` calls `async_refresh()` which re-runs `_async_update_data`, adding a new usage increment. Test turns zone off before firing midnight event to avoid non-zero result obscuring the reset check. Correct production behavior — at midnight, zone was running; new day starts counting fresh.
- **Explicit entity_id on sensors:** Used `self.entity_id = f"sensor.{DOMAIN}_{zone_slug}_daily_usage"` to make entity IDs predictable for tests (dot in `switch.rachio_zone_1` → underscore in entity_id slug).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Added explicit Store flush on entry unload**
- **Found during:** Task 2 (GREEN — test_totals_persist_across_restart failure)
- **Issue:** `async_delay_save(fn, 30)` schedules write for 30s; entry unload happens before that fires. `EVENT_HOMEASSISTANT_FINAL_WRITE` doesn't trigger on entry unload — only on HA stop. Persistence test reloaded entry immediately after unload; Store had no data.
- **Fix:** Added `_flush_store` coroutine in `_async_setup` wired via `entry.async_on_unload(_flush_store)` — calls `await self._store.async_save(self._data_to_save())`
- **Files modified:** `custom_components/irrigation_monitor/coordinator.py`
- **Committed in:** `e85d0e0` (Task 2 feat commit)

**2. [Rule 1 - Bug] Fixed midnight reset test to not leave zone running**
- **Found during:** Task 2 (GREEN — test_midnight_reset_zeroes_totals failure)
- **Issue:** `_midnight_reset` zeroes totals then calls `async_refresh()`. Zone 1 was still "on" in test, so `_async_update_data` immediately added a new interval's usage, making state non-zero.
- **Fix:** Added `hass.states.async_set(mock_valve_entities[0], "off")` before firing midnight event
- **Files modified:** `tests/test_coordinator.py`
- **Committed in:** `e85d0e0` (Task 2 feat commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — bugs found during GREEN phase)
**Impact on plan:** Both fixes necessary for test correctness. The Store flush also improves production reliability. No scope creep.

## Issues Encountered

- `SensorDeviceClass.VOLUME_FLOW_RATE` required for flow_rate sensor (not `SensorDeviceClass.FLOW_RATE`) — confirmed from RESEARCH.md and used correctly.
- `async_fire_time_changed` import from `pytest_homeassistant_custom_component.common` works as expected in 0.13.316.

## Next Phase Readiness

- Coordinator data pipeline fully operational: Phases 4 (calibration) and 5 (leak detection) can import `IrrigationCoordinator` and `ZoneData`
- `coordinator.data[zone_id].flow_rate` and `.daily_usage` available per zone
- Phase 4 will write `calibrated_flow` to `ConfigEntry.options.zones[entity_id]["calibrated_flow"]` — coordinator already reads this field (currently `None` for all zones)
- No blockers

## Known Stubs

None — all sensor data is wired from coordinator. Zone entities may show 0.0 flow_rate until a zone runs (expected behavior, not a stub).

---
*Phase: 03-coordinator-usage*
*Completed: 2026-03-23*
