# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-19)

**Core value:** When a valve is running and water flow spikes beyond the expected rate, the system shuts it off automatically — protecting against burst pipes and unexpected leaks.
**Current focus:** Phase 1 — Scaffold

## Current Position

Phase: 1 of 6 (Scaffold)
Plan: 0 of ? in current phase
Status: Ready to plan
Last activity: 2026-03-19 — Roadmap created; 26/26 v1 requirements mapped across 6 phases

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

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Custom integration (not add-on): runs inside HA, directly reads/writes entities
- Config flow + options flow: initial setup via config flow; adding valves later via options flow (merge strategy critical — never replace, always merge into existing options dict)
- DataUpdateCoordinator: single poll hub; calibration data in ConfigEntry.options; daily totals in Store
- Per-zone unique_id format: `{entry.entry_id}_{zone_id}_{type}` — set once, never change

### Pending Todos

None yet.

### Blockers/Concerns

- [Pre-Phase 2] EntityRegistry discovery pairing pattern depends on upstream irrigation controller integration naming — validate against target controller before writing EntitySelector filter
- [Pre-Phase 2] Flume sensor entity_id/device_class — confirm against current Flume HA integration before config flow EntitySelector filter
- [Pre-Phase 3] Statistics/recorder API shape for daily totals — use Store (high confidence), verify recorder API only if history chart becomes needed in Phase 6

## Session Continuity

Last session: 2026-03-19
Stopped at: Roadmap created; ready to plan Phase 1
Resume file: None
