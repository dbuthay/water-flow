# Phase 2: Config Flow - Context

**Gathered:** 2026-03-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the HA config flow (initial setup wizard) and options flow (post-setup reconfiguration) for the irrigation_monitor integration. Users go through Settings → Integrations → Add Integration → Irrigation Monitor to set up; and Settings → Integrations → Irrigation Monitor → Configure to reconfigure. No logic, no coordinator, no entities yet — this phase only stores configuration in ConfigEntry. Phase is complete when all 7 SETUP requirements are satisfied.

</domain>

<decisions>
## Implementation Decisions

### Valve Discovery Display
- Each valve candidate shown as: `"Friendly Name (entity.id)"` — e.g., "Front Yard Drip (switch.rachio_zone_1)"
- No custom rename per zone within this integration — use the HA entity's friendly name throughout
- Discovery falls back to showing ALL switch and binary_sensor entities if no obvious irrigation valves found; user picks manually from the full list

### Config Flow Structure (Initial Setup)
- **Step 1**: Select Flume sensor — show all numeric sensor entities (EntitySelector); user picks their Flume sensor. No auto-detection required — always show a list.
- **Step 2**: Select valves — show discovered valve candidates (or all switches/binary_sensors if none obvious); multi-select. Each entry shows `"Friendly Name (entity_id)"`.
- Per-zone settings (threshold, shutoff toggle, alert toggle) are NOT collected at initial setup — deferred to options flow. Simpler first-run.
- New valves added via options flow also start with defaults immediately — per-zone config edited in a subsequent options visit.

### Per-Zone Defaults
- **Threshold multiplier**: N/A at setup — leak detection is **disabled until calibrated** (Phase 4 sets the baseline; detection only activates after calibration)
- **Shutoff enabled**: `true` by default (user can disable per valve in options)
- **Alerts enabled**: `true` by default (user can disable per valve in options)

### Options Flow Scope (Post-Setup)
All four of these are editable post-setup via Configure:
1. **Valve management** — re-run discovery, add/remove monitored valves
2. **Per-zone settings** — threshold multiplier, shutoff enabled, alerts enabled per zone
3. **Flume sensor** — change which entity is the flow sensor
4. **Global poll interval** — how often coordinator reads Flume (default 30s, configurable)

- **Removing a valve**: clears its calibration data (fresh slate if re-added — no stale baseline)
- **Options flow merge strategy**: CRITICAL — always merge into existing options dict, never replace. New valves get default config; existing zones are untouched.

### Flume Sensor Fallback
- If no Flume-specific entity is found during setup, show all numeric sensor entities — user picks manually from the list
- No manual text entry — always a picker

### Options Flow — No Valves Found
- If discovery finds no obvious irrigation valves, fall back to showing all switch + binary_sensor entities
- User picks from the full list — never blocked by discovery failures

### Claude's Discretion
- Exact HA Selectors used (EntitySelector, SelectSelector, NumberSelector, BooleanSelector)
- ConfigEntry.data vs ConfigEntry.options data split
- Step-by-step flow implementation details
- Error handling for unavailable entities during setup

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project context
- `.planning/PROJECT.md` — Project vision, key decisions (config flow + options flow merge strategy)
- `.planning/REQUIREMENTS.md` — SETUP-01 through SETUP-07 (all Phase 2 requirements)
- `.planning/research/STACK.md` — HA Selectors (EntitySelector, SelectSelector, NumberSelector, BooleanSelector), config flow API
- `.planning/research/ARCHITECTURE.md` — Config flow + options flow interaction, ConfigEntry data split, incremental valve add pattern
- `.planning/research/PITFALLS.md` — P3 (options flow destroying existing zone config — merge strategy CRITICAL), P6 (entity uniqueness after config change)

### Phase 1 scaffold (extend, don't replace)
- `custom_components/irrigation_monitor/__init__.py` — stub to extend with platform registration
- `custom_components/irrigation_monitor/manifest.json` — set `config_flow: true` in this phase
- `custom_components/irrigation_monitor/const.py` — add config keys here

### State decisions
- `.planning/STATE.md` — blocker: Flume sensor entity format and valve pairing pattern need research before implementation

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `custom_components/irrigation_monitor/__init__.py` — async_setup_entry/async_unload_entry stubs; extend, don't replace
- `custom_components/irrigation_monitor/const.py` — DOMAIN constant; add CONF_* keys here
- `tests/conftest.py` — enable_custom_integrations fixture already in place; add MockConfigEntry usage for config flow tests

### Established Patterns
- `PLATFORMS: list[str] = []` in `__init__.py` — will remain empty until Phase 3 adds entity platforms
- `manifest.json` has `"config_flow": false` — this phase must flip it to `true` when config_flow.py is added

### Integration Points
- Phase 2 creates `config_flow.py` — this is what Phase 3 (coordinator) and Phase 4 (calibration) read to know which entities are configured
- ConfigEntry.data stores: flume_entity_id, monitored_zone_entity_ids, poll_interval
- ConfigEntry.options stores: per-zone settings dict (shutoff_enabled, alerts_enabled, threshold — all keyed by zone entity_id)

</code_context>

<specifics>
## Specific Ideas

- "Disabled until calibrated" for leak detection threshold: the threshold field in ConfigEntry.options can be stored as `None` or `0` to signal "not yet calibrated — skip detection". Phase 5 (leak detection) checks for this before evaluating.
- Options flow merge pattern (CRITICAL): `existing = dict(self.config_entry.options); existing["zones"] = updated_zones; return self.async_create_entry(data=existing)` — never `return self.async_create_entry(data={"zones": new_zones})`
- Removing a valve: delete its entry from the options dict entirely (clears calibration + settings). If re-added, starts fresh with defaults.

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-config-flow*
*Context gathered: 2026-03-20*
