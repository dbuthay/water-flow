---
phase: 02-config-flow
plan: 02
subsystem: ui
tags: [homeassistant, config-flow, options-flow, BooleanSelector, NumberSelector, voluptuous]

# Dependency graph
requires:
  - phase: 02-config-flow/02-01
    provides: IrrigationMonitorConfigFlow two-step wizard, const.py with all CONF_ keys, stub IrrigationMonitorOptionsFlowHandler

provides:
  - Full IrrigationMonitorOptionsFlowHandler with async_step_init and async_step_zones
  - Per-zone options editing: shutoff_enabled, alerts_enabled, threshold_multiplier
  - CRITICAL merge pattern preserving calibrated_flow and future Phase 4 calibration data
  - 7 new passing tests covering SETUP-04 through SETUP-07

affects: [03-coordinator, 04-calibration, 05-leak-detection]

# Tech tracking
tech-stack:
  added: [BooleanSelector, NumberSelector, NumberSelectorConfig]
  patterns:
    - "Options flow merge: existing = dict(self.config_entry.options); existing['zones'] = updated; async_create_entry(data=existing)"
    - "Per-zone iterator: _zone_iterator list popped one at a time to show per-zone forms"
    - "New zone defaults initialized before user input merge to ensure calibrated_flow=None is always present"

key-files:
  created: []
  modified:
    - custom_components/irrigation_monitor/config_flow.py
    - tests/test_config_flow.py

key-decisions:
  - "New zones configured via per-zone form get defaults as base before merging user input (ensures calibrated_flow=None is always set)"
  - "Zone iterator pattern: _zone_iterator list is popped per-step until empty, then final merge executes"
  - "ConfigEntry.data updated via async_update_entry before async_create_entry to keep data and options in sync"

patterns-established:
  - "Options merge pattern: never replace — always merge into existing dict to protect Phase 4 calibrated_flow data"
  - "Per-zone defaults must include calibrated_flow=None for all paths (new zone, configured zone) to prevent KeyError in Phase 4"

requirements-completed: [SETUP-04, SETUP-05, SETUP-06, SETUP-07]

# Metrics
duration: 6min
completed: 2026-03-20
---

# Phase 02 Plan 02: Options Flow — Full IrrigationMonitorOptionsFlowHandler Summary

**Two-step HA options flow with per-zone shutoff/alerts/threshold editing and CRITICAL merge pattern preserving Phase 4 calibration data across reconfiguration**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-20T07:39:46Z
- **Completed:** 2026-03-20T07:46:28Z
- **Tasks:** 2 (1 test stub, 1 implementation)
- **Files modified:** 2

## Accomplishments

- Options flow Step 1 (init): users can change Flume sensor, valve list, and poll interval
- Options flow Step 2 (zones): iterates per-zone for shutoff_enabled, alerts_enabled, and threshold_multiplier
- CRITICAL merge pattern implemented: calibrated_flow=3.5 survives full options flow round-trip (confirmed by test)
- New valves added via options flow get default settings including calibrated_flow=None
- Removing a valve clears its zone data entirely from options.zones
- All 12 tests pass (5 config flow from Plan 01 + 7 options flow tests)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add options flow test stubs (RED phase)** - `8a60871` (test)
2. **Task 2: Implement full IrrigationMonitorOptionsFlowHandler** - `a34bdcb` (feat)

## Files Created/Modified

- `custom_components/irrigation_monitor/config_flow.py` - Replaced stub with full IrrigationMonitorOptionsFlowHandler; added BooleanSelector and NumberSelector imports
- `tests/test_config_flow.py` - Added MockConfigEntry import, mock_config_entry fixture, and 7 options flow tests

## Decisions Made

- New zones get their full defaults dict (incl. calibrated_flow=None) as the base before user input is merged. This ensures calibrated_flow is always present regardless of code path, preventing KeyError in Phase 4 calibration reads.
- Zone iterator: _zone_iterator is a copy of _new_zone_ids that is popped one entry per async_step_zones call. When empty, the final merge and async_create_entry execute.
- ConfigEntry.data (flume_entity_id, monitored_zone_entity_ids, poll_interval) is updated via async_update_entry immediately before async_create_entry so Phase 3 coordinator can always read current values from .data.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] New zone configured via per-zone form was missing calibrated_flow key**
- **Found during:** Task 2 (test_options_flow_add_new_valve_gets_defaults failed with KeyError)
- **Issue:** When a new zone had user-provided settings, the merge path did `base = dict(old_zones.get(zone_id, {}))` which produced an empty dict — user settings were merged in, but calibrated_flow was never set
- **Fix:** When zone_id is not in old_zones, initialize base with full defaults dict (including calibrated_flow=None) before merging user input
- **Files modified:** custom_components/irrigation_monitor/config_flow.py
- **Verification:** test_options_flow_add_new_valve_gets_defaults passes; all 12 tests green
- **Committed in:** a34bdcb (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Fix essential for correctness. Without it, Phase 4 calibration reads would KeyError on newly-added valves.

## Issues Encountered

None beyond the auto-fixed bug above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Full config + options flow complete: both initial setup and post-setup reconfiguration work
- ConfigEntry.data schema: flume_entity_id, monitored_zone_entity_ids, poll_interval
- ConfigEntry.options schema: zones dict keyed by entity_id, each with shutoff_enabled, alerts_enabled, calibrated_flow, threshold_multiplier
- Phase 3 coordinator reads from ConfigEntry.data for which entities to poll
- Phase 4 calibration writes calibrated_flow to ConfigEntry.options["zones"][zone_id] via async_update_entry — merge pattern guarantees this survives subsequent options flow visits

---
*Phase: 02-config-flow*
*Completed: 2026-03-20*
