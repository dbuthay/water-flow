---
phase: 03-coordinator-usage
plan: 02
subsystem: sensor
tags: [home-assistant, coordinator-entity, sensor, daily-usage, flow-rate, tdd]

# Dependency graph
requires:
  - phase: 03-01
    provides: IrrigationCoordinator with ZoneData, Store persistence, midnight reset, and sensor.py stubs
provides:
  - "DailyUsageSensor CoordinatorEntity subclass — gallons accumulated since midnight per zone"
  - "FlowRateSensor CoordinatorEntity subclass — gal/min current flow (0 when idle) per zone"
  - "All 7 coordinator/sensor tests passing GREEN (USAGE-01, USAGE-02, USAGE-03)"
  - "Full test suite (20 tests) passing GREEN"
affects: [04-calibration, 05-leak-detection]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "CoordinatorEntity[IrrigationCoordinator] double-inheritance for auto-update wiring without manual listener registration"
    - "Explicit entity_id via zone_slug (dots->underscores) for predictable test and UI entity IDs"
    - "AddConfigEntryEntitiesCallback (HA 2024.x+) in async_setup_entry signature"
    - "No custom available property — CoordinatorEntity.available returns coordinator.last_update_success automatically"

key-files:
  created: []
  modified:
    - "custom_components/irrigation_monitor/sensor.py"
    - "tests/test_coordinator.py"

key-decisions:
  - "Both sensor classes use CoordinatorEntity[IrrigationCoordinator] + SensorEntity double-inheritance — auto-wires coordinator updates to HA state machine without manual async_write_ha_state calls"
  - "entity_id set explicitly using zone_slug (dots->underscores) pattern for predictable test assertions"
  - "No custom available property override — CoordinatorEntity.available delegates to coordinator.last_update_success, which UpdateFailed sets to False automatically"
  - "DailyUsageSensor: SensorStateClass.TOTAL_INCREASING + SensorDeviceClass.WATER + UnitOfVolume.GALLONS"
  - "FlowRateSensor: SensorStateClass.MEASUREMENT + SensorDeviceClass.VOLUME_FLOW_RATE + UnitOfVolumeFlowRate.GALLONS_PER_MINUTE"

patterns-established:
  - "Pattern 1: CoordinatorEntity double-inheritance — use CoordinatorEntity[CoordinatorType] + SensorEntity MRO for all sensor platforms"
  - "Pattern 2: Zone slug entity IDs — replace dots with underscores in entity_ids derived from zone entity_ids"
  - "Pattern 3: native_value guard pattern — if coordinator.data is None: return None; then .get() zone and return None if missing"

requirements-completed: [USAGE-01, USAGE-02, USAGE-03]

# Metrics
duration: 5min
completed: 2026-03-24
---

# Phase 3 Plan 02: Sensor Entities Summary

**DailyUsageSensor and FlowRateSensor as CoordinatorEntity subclasses delivering per-zone gallons-since-midnight and gal/min flow to HA UI, with all 7 coordinator tests GREEN**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-24T04:28:09Z
- **Completed:** 2026-03-24T04:33:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- `sensor.py` with `DailyUsageSensor` and `FlowRateSensor` as `CoordinatorEntity[IrrigationCoordinator]` subclasses
- All 7 coordinator/sensor tests pass GREEN (entities created, flow rate zero when idle, daily usage accumulates, Flume unavailable propagates, persistence across restart, midnight reset, stale date reset)
- Full test suite of 20 tests passes GREEN (coordinator + config_flow tests)

## Task Commits

Both tasks were already complete from Plan 03-01's implementation commit:

1. **Task 1: Create sensor.py with DailyUsageSensor and FlowRateSensor** - `e85d0e0` (feat(03-01): implement IrrigationCoordinator with Store persistence and sensor entities)
2. **Task 2: Make all 7 tests GREEN** - `e85d0e0` (same commit — all tests passed GREEN immediately)

**Plan metadata:** (docs commit — this SUMMARY)

_Note: Both tasks were completed in Plan 03-01's implementation phase. Plan 03-02 verified all acceptance criteria met and produces this SUMMARY._

## Files Created/Modified

- `custom_components/irrigation_monitor/sensor.py` — DailyUsageSensor and FlowRateSensor CoordinatorEntity subclasses with correct device_class, units, state_class, unique_id format, and explicit entity_id slugs
- `tests/test_coordinator.py` — 7 tests covering all USAGE-01/02/03 scenarios

## Decisions Made

- Sensor entity_id set explicitly using `zone_slug = zone_id.replace(".", "_")` pattern for predictable test assertions (e.g., `sensor.irrigation_monitor_switch_rachio_zone_1_daily_usage`)
- No custom `available` property — `CoordinatorEntity.available` returns `coordinator.last_update_success` automatically; when `UpdateFailed` is raised, HA sets all entities to unavailable state
- `SensorStateClass.TOTAL_INCREASING` on `DailyUsageSensor` only; `SensorStateClass.MEASUREMENT` on `FlowRateSensor` only
- `AddConfigEntryEntitiesCallback` (HA 2024.x+) used in `async_setup_entry` signature

## Deviations from Plan

None — plan executed exactly as written. Both tasks were verified complete from 03-01's implementation; all acceptance criteria met without modification.

## Issues Encountered

None. The implementation from Plan 03-01 satisfied all 03-02 acceptance criteria:
- `sensor.py` has 94 lines (min_lines: 50 requirement met)
- Both classes inherit `CoordinatorEntity[IrrigationCoordinator]`
- No `def available` override present
- Unique ID format `{entry.entry_id}_{zone_id}_daily_usage` / `_flow_rate` confirmed
- All 7 tests pass; full 20-test suite passes

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Phase 3 data pipeline is complete: Flume poll → coordinator attribution → ZoneData → sensor entities
- `DailyUsageSensor` and `FlowRateSensor` entities visible in HA UI per zone
- `calibrated_flow` field in `ConfigEntry.options.zones` is `None` until Phase 4 sets it
- `IrrigationCoordinator._async_update_data` designed for Phase 5 extension (threshold comparison)
- No blockers for Phase 4 (Calibration)

---
*Phase: 03-coordinator-usage*
*Completed: 2026-03-24*
