---
phase: 02-config-flow
plan: 01
subsystem: config
tags: [homeassistant, config_flow, options_flow, voluptuous, entity_registry, selectors]

requires:
  - phase: 01-scaffold
    provides: integration stub (__init__.py, const.py, manifest.json, conftest.py) and passing smoke test

provides:
  - IrrigationMonitorConfigFlow two-step wizard (user -> valves -> create_entry)
  - EntitySelector with integration=flume filter for Flume sensor picker
  - SelectSelector multi-select for irrigation valve candidates via entity registry scan
  - ConfigEntry.data schema: flume_entity_id, monitored_zone_entity_ids, poll_interval=30
  - ConfigEntry.options schema: zones dict with per-zone defaults (shutoff_enabled, alerts_enabled, calibrated_flow=None, threshold_multiplier=1.5)
  - IrrigationMonitorOptionsFlowHandler stub (Plan 02 implements fully)
  - All CONF_* config keys and defaults in const.py
  - strings.json and translations/en.json for config/options UI strings
  - 5 passing config flow tests covering SETUP-01/02/03

affects:
  - 02-02 options flow (extends IrrigationMonitorOptionsFlowHandler stub)
  - 03-coordinator (reads ConfigEntry.data for flume_entity_id and monitored_zone_entity_ids)
  - 04-calibration (writes ConfigEntry.options["zones"][entity_id]["calibrated_flow"])
  - 05-leak-detection (reads threshold_multiplier and calibrated_flow from options)

tech-stack:
  added:
    - homeassistant.config_entries.ConfigFlow (two-step wizard pattern)
    - homeassistant.config_entries.OptionsFlow (stub for Plan 02)
    - homeassistant.helpers.selector.EntitySelector with EntityFilterSelectorConfig
    - homeassistant.helpers.selector.SelectSelector with SelectSelectorConfig
    - homeassistant.helpers.selector.SelectOptionDict
    - homeassistant.helpers.entity_registry (valve candidate discovery)
  patterns:
    - Two-step config flow: async_step_user -> async_step_valves -> async_create_entry
    - async_get_options_flow registered via @staticmethod @callback
    - ConfigEntry.options initialized at config flow time with per-zone defaults
    - Valve discovery via EntityRegistry.entities.values() filtered by VALVE_DOMAINS

key-files:
  created:
    - custom_components/irrigation_monitor/config_flow.py
    - custom_components/irrigation_monitor/strings.json
    - custom_components/irrigation_monitor/translations/en.json
    - tests/test_config_flow.py
  modified:
    - custom_components/irrigation_monitor/const.py (added CONF_* keys, defaults, VALVE_DOMAINS)
    - custom_components/irrigation_monitor/manifest.json (config_flow: true)
    - tests/conftest.py (added mock_flume_entity and mock_valve_entities fixtures)

key-decisions:
  - "EntitySelector with integration=flume filter for Step 1 (fallback to domain=sensor if Flume not installed not implemented — plan scope)"
  - "SelectSelector (not EntitySelector) for valve Step 2 to support Friendly Name (entity_id) display format per CONTEXT.md"
  - "options.zones initialized at config flow CREATE_ENTRY time (not deferred to options flow)"
  - "calibrated_flow=None in per-zone defaults signals unset — Phase 4 writes the value"
  - "IrrigationMonitorOptionsFlowHandler is a stub (returns existing options) — Plan 02 implements fully"
  - "VALVE_DOMAINS = {switch, valve, binary_sensor} covers all known irrigation controller integrations"

patterns-established:
  - "Config flow step progression: async_step_user stores state in self._field, calls next step"
  - "Per-zone defaults dict structure: {shutoff_enabled, alerts_enabled, calibrated_flow, threshold_multiplier}"
  - "Options merge pattern (CRITICAL for Plan 02): existing = dict(self.config_entry.options); existing[key] = updated; async_create_entry(data=existing)"
  - "Test fixtures: mock_flume_entity sets state + registers entity; mock_valve_entities registers 3 entities across switch/valve domains"

requirements-completed: [SETUP-01, SETUP-02, SETUP-03]

duration: 12min
completed: 2026-03-20
---

# Phase 02 Plan 01: Config Flow Setup Wizard Summary

**Two-step HA config flow wizard with EntitySelector Flume picker and SelectSelector valve multi-select, creating ConfigEntry with per-zone defaults in options.zones**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-20T07:19:34Z
- **Completed:** 2026-03-20T07:31:48Z
- **Tasks:** 2 (Task 1: infra/fixtures, Task 2: TDD implementation)
- **Files modified:** 7

## Accomplishments

- Config flow two-step wizard navigating user -> valves -> create_entry with full data validation
- ConfigEntry created with correct data (flume_entity_id, monitored_zone_entity_ids, poll_interval=30) and options (zones with per-zone defaults)
- All 5 config flow tests pass; full suite of 6 tests green
- Integration manifest config_flow: true enabling Settings > Integrations > Add Integration discovery

## Task Commits

Each task was committed atomically:

1. **Task 1: Add config keys, strings, manifest update, and test fixtures** - `85d3a13` (feat)
2. **Task 2: Implement IrrigationMonitorConfigFlow two-step wizard** - `b482306` (feat)

## Files Created/Modified

- `custom_components/irrigation_monitor/config_flow.py` - IrrigationMonitorConfigFlow (two steps) + IrrigationMonitorOptionsFlowHandler stub
- `custom_components/irrigation_monitor/const.py` - Added all CONF_* keys, defaults, VALVE_DOMAINS
- `custom_components/irrigation_monitor/manifest.json` - Flipped config_flow to true
- `custom_components/irrigation_monitor/strings.json` - UI strings for config and options flow steps
- `custom_components/irrigation_monitor/translations/en.json` - English translations (mirrors strings.json)
- `tests/conftest.py` - Added mock_flume_entity and mock_valve_entities fixtures
- `tests/test_config_flow.py` - 5 tests covering SETUP-01/02/03

## Decisions Made

- Used EntitySelector with integration=flume filter for Step 1 (cleaner than domain=sensor, covers the primary Flume user case)
- Used SelectSelector (not EntitySelector with multiple) for Step 2 to support "Friendly Name (entity_id)" display format per CONTEXT.md decision
- Initialized options.zones at config flow CREATE_ENTRY time with all per-zone defaults — avoids any null-check complexity in Phase 3/4/5
- calibrated_flow=None in defaults signals "not yet calibrated" — Phase 4 writes the actual value; Phase 5 checks for None before running detection

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. All tests passed on first run after implementing config_flow.py.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 02-02 can immediately extend IrrigationMonitorOptionsFlowHandler stub with full options flow
- ConfigEntry.data and options schema is established and stable for Phase 3 coordinator to consume
- Per-zone defaults are in place for Phase 4 calibration to write calibrated_flow values

---
*Phase: 02-config-flow*
*Completed: 2026-03-20*
