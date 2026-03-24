---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: completed
stopped_at: "Checkpoint 06-lovelace-card 06-02-PLAN.md Task 2: awaiting human visual verification"
last_updated: "2026-03-24T06:54:41.624Z"
last_activity: 2026-03-24
progress:
  total_phases: 6
  completed_phases: 6
  total_plans: 12
  completed_plans: 12
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-19)

**Core value:** When a valve is running and water flow spikes beyond the expected rate, the system shuts it off automatically — protecting against burst pipes and unexpected leaks.
**Current focus:** Phase 2 — Config Flow

## Current Position

Phase: 6 of 6 (lovelace card)
Plan: Not started
Status: Phase complete — ready for Phase 3
Last activity: 2026-03-24

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: —
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

*Updated after each plan completion*
| Phase 01-scaffold P01 | 5 | 2 tasks | 10 files |
| Phase 02-config-flow P02-01 | 12 | 2 tasks | 7 files |
| Phase 02-config-flow P02-02 | 6 | 2 tasks | 2 files |
| Phase 03-coordinator-usage P01 | 6 | 2 tasks | 6 files |
| Phase 03-coordinator-usage P02 | 5 | 2 tasks | 2 files |
| Phase 04-calibration P01 | 3 | 2 tasks | 5 files |
| Phase 04-calibration P02 | 2 | 2 tasks | 2 files |
| Phase 04-calibration P03 | 8 | 2 tasks | 2 files |
| Phase 05 P01 | 3 | 2 tasks | 4 files |
| Phase 05-leak-detection P02 | 11 | 2 tasks | 3 files |
| Phase 06-lovelace-card P01 | 2 | 2 tasks | 3 files |
| Phase 06-lovelace-card P02 | 2 | 1 tasks | 1 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Custom integration (not add-on): runs inside HA, directly reads/writes entities
- Config flow + options flow: initial setup via config flow; adding valves later via options flow (merge strategy critical — never replace, always merge into existing options dict)
- DataUpdateCoordinator: single poll hub; calibration data in ConfigEntry.options; daily totals in Store
- Per-zone unique_id format: `{entry.entry_id}_{zone_id}_{type}` — set once, never change
- [Phase 01-scaffold]: Used Python 3.13 + pytest-homeassistant-custom-component==0.13.316 (plan specified 0.13.318 requiring Python 3.14 not yet installed)
- [Phase 01-scaffold]: config_flow=false in manifest.json until Phase 2 adds config_flow.py
- [Phase 01-scaffold]: No custom_components/__init__.py - HA loader expects custom_components/ to NOT be a Python package
- [Phase 02-config-flow]: EntitySelector with integration=flume filter for Step 1; SelectSelector for Step 2 to support Friendly Name display format
- [Phase 02-config-flow]: options.zones initialized at config flow CREATE_ENTRY time with all per-zone defaults including calibrated_flow=None
- [Phase 02-config-flow]: IrrigationMonitorOptionsFlowHandler stub (returns existing options unchanged) — Plan 02-02 implements full options flow
- [Phase 02-config-flow 02-02]: New zones initialized with full defaults dict (incl. calibrated_flow=None) before merging user input — prevents KeyError in Phase 4 calibration reads
- [Phase 02-config-flow 02-02]: Zone iterator pattern (_zone_iterator popped per step) drives per-zone forms; final merge executes when iterator is empty
- [Phase 02-config-flow 02-02]: ConfigEntry.data updated via async_update_entry before async_create_entry to keep data and options in sync for Phase 3 coordinator
- [Phase 03-coordinator-usage]: Store flush on entry unload via async_save (not just async_delay_save) ensures persistence test and production reliability
- [Phase 03-coordinator-usage]: Sensor entity_id set explicitly using zone_slug (dots->underscores) for predictable test entity IDs
- [Phase 03-coordinator-usage]: type IrrigationConfigEntry = ConfigEntry[IrrigationCoordinator] for type-safe entry access across platforms
- [Phase 03-coordinator-usage]: CoordinatorEntity double-inheritance: CoordinatorEntity[IrrigationCoordinator] + SensorEntity for auto-wired HA state updates without manual async_write_ha_state calls
- [Phase 03-coordinator-usage]: Sensor entity_id set explicitly using zone_slug (dots->underscores) for predictable test assertions
- [Phase 03-coordinator-usage]: No custom available property override on sensors — CoordinatorEntity.available delegates to coordinator.last_update_success automatically
- [Phase 04-calibration]: async_press uses entry.async_create_background_task for fire-and-forget calibration (not asyncio.create_task)
- [Phase 04-calibration]: Wave 0 xfail test stubs collected by pytest without failing the suite; Plan 04-02 will implement full sequence
- [Phase 04-calibration]: Two-level try/finally for calibration: outer removes _calibrating, inner ensures valve always off after turn_on
- [Phase 04-calibration]: _write_calibrated_flow uses 3-level nested dict copy to safely mutate MappingProxyType ConfigEntry.options
- [Phase 04-calibration]: Service call layer required for action-button notifications — async_create() has no actions param
- [Phase 04-calibration]: One-shot event listener: unsub inside handler + entry.async_on_unload for leak-safe cleanup on entry unload
- [Phase 05-01]: ramp_up_polls stored globally in ConfigEntry.options (not per-zone)
- [Phase 05-01]: leak_statuses kept as coordinator dict (not ZoneData field) — Plan 02 wires sensors to it
- [Phase 05-02]: ZoneStatusSensor omits state_class and device_class — text enum values incompatible with HA statistics recorder
- [Phase 05-02]: AcknowledgeLeakButtonEntity uses async_update_listeners() (no await) not async_request_refresh() to avoid unnecessary Flume poll on acknowledge
- [Phase 05-02]: Tests mock coordinator._turn_valve with AsyncMock to avoid ServiceNotFound — switch/valve services not registered in pytest-homeassistant test harness
- [Phase 06-lovelace-card]: Use async_register_static_paths (plural, async) with StaticPathConfig -- NOT deprecated register_static_path (singular, sync) removed in HA 2024.7+
- [Phase 06-lovelace-card]: Vanilla HTMLElement Web Component (no Lit/TypeScript/build step) per locked decision; XSS protection via _escapeHtml() for innerHTML template literals

### Pending Todos

None yet.

### Blockers/Concerns

- [Pre-Phase 2] EntityRegistry discovery pairing pattern depends on upstream irrigation controller integration naming — validate against target controller before writing EntitySelector filter
- [Pre-Phase 2] Flume sensor entity_id/device_class — confirm against current Flume HA integration before config flow EntitySelector filter
- [Pre-Phase 3] Statistics/recorder API shape for daily totals — use Store (high confidence), verify recorder API only if history chart becomes needed in Phase 6

## Session Continuity

Last session: 2026-03-24T06:54:41.619Z
Stopped at: Checkpoint 06-lovelace-card 06-02-PLAN.md Task 2: awaiting human visual verification
Resume file: None
