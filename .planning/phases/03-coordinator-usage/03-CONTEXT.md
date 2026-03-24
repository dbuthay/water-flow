# Phase 3: Coordinator + Usage - Context

**Gathered:** 2026-03-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the DataUpdateCoordinator that polls the Flume sensor and exposes per-zone sensor entities: a daily usage sensor (gallons accumulated since midnight) and a current flow rate sensor (gal/min while running, 0 when idle). Daily usage totals must persist across HA restarts and reset correctly at midnight even if HA was offline. No leak detection, no calibration logic yet — this phase establishes the data pipeline that Phases 4 and 5 build on.

</domain>

<decisions>
## Implementation Decisions

### Multi-Zone Overlap Attribution
When multiple zones are ON simultaneously (total flow from Flume is ambiguous):
- **Calibrated zones**: If total Flume reading ≈ sum of calibrated values (within threshold_multiplier margin), attribute each calibrated zone its known calibrated_flow value
- **Uncalibrated zones in overlap**: Skip them — only credit zones that have been calibrated. Do not attempt to estimate uncalibrated zones' contribution.
- **Example**: Zones calibrated at 3, 4, 5 gpm all running; Flume reads 12.4 gpm (within margin) → attribute 3, 4, 5 gpm respectively. Any uncalibrated zone in the same group gets 0 credited.
- This logic requires calibrated_flow to be set (Phase 4 sets it). Until calibrated, zones in multi-zone overlap simply don't accumulate.

### Sensor Entities Per Zone
Phase 3 creates TWO sensor entities per monitored zone:
1. **Daily usage sensor**: `sensor.irrigation_monitor_{zone_id}_daily_usage` — gallons accumulated since midnight. Shows 0 at start of day; accumulates while zone runs.
2. **Current flow rate sensor**: `sensor.irrigation_monitor_{zone_id}_flow_rate` — gal/min from Flume while zone is active, **0** when zone is idle (not unavailable — clean zero distinguishes idle from offline).

### Flume Unavailability Behavior
- When Flume sensor state is `unavailable` or `unknown`: all irrigation_monitor entities switch to **unavailable** state. Coordinator raises `UpdateFailed`.
- Accumulated daily totals are preserved in Store (written to storage before going unavailable).
- When Flume comes back: coordinator immediately resumes accumulation from stored total. No confirmation delay.
- Usage during the outage window is lost (no Flume data to accumulate from) — this is acceptable.

### Coordinator Data Pipeline
- Single `DataUpdateCoordinator` polls Flume every `poll_interval` seconds (from ConfigEntry.data)
- Per poll: reads Flume state, reads all monitored zone states, applies attribution logic, accumulates usage into in-memory totals, writes totals to HA Store (debounced)
- Coordinator data dict: `{zone_entity_id: ZoneData(flow_rate: float, daily_usage: float, is_available: bool)}`
- All sensor entities are `CoordinatorEntity` subclasses — no manual listener wiring

### State Persistence
- Storage key: `"irrigation_monitor.daily_usage"` via `homeassistant.helpers.storage.Store`
- Stored: `{"date": "YYYY-MM-DD", "zones": {entity_id: gallons_float}}`
- On startup: if stored date == today, restore totals; if stored date != today (HA was offline at midnight), reset all totals to 0 and save new date
- Midnight reset: `async_track_time_change` callback at 00:00:00 local time resets in-memory totals and writes new Store entry

### Unique ID Format
Per STATE.md decision: `{entry.entry_id}_{zone_entity_id}_daily_usage` and `{entry.entry_id}_{zone_entity_id}_flow_rate` — set once, never change.

### Claude's Discretion
- Store write debounce interval
- ZoneData dataclass vs TypedDict
- Exact `UpdateFailed` error message content
- Whether to expose a coordinator-level "status" binary sensor

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 2 artifacts (extend, don't replace)
- `custom_components/irrigation_monitor/__init__.py` — async_setup_entry stub to extend with coordinator setup and PLATFORMS registration
- `custom_components/irrigation_monitor/const.py` — all CONF_* keys and defaults already defined; add any new constants here
- `custom_components/irrigation_monitor/config_flow.py` — ConfigEntry.data shape: `{flume_entity_id, monitored_zone_entity_ids, poll_interval}`; ConfigEntry.options.zones shape: `{entity_id: {shutoff_enabled, alerts_enabled, calibrated_flow, threshold_multiplier}}`

### Test infrastructure
- `tests/conftest.py` — `mock_flume_entity` and `mock_valve_entities` fixtures already available; extend for coordinator tests

### Research references
- `.planning/research/ARCHITECTURE.md` — coordinator pattern, Store usage, midnight reset pattern, `ConfigEntry.runtime_data` for coordinator storage
- `.planning/research/PITFALLS.md` — P1 (blocking event loop), P2 (calibration data lost on restart), P5 (Flume sensor unavailable), P9 (midnight reset missed if HA offline)
- `.planning/STATE.md` — per-zone unique_id format decision

No external specs — requirements fully captured in decisions above and research files.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tests/conftest.py: mock_flume_entity` — sets `sensor.flume_current_interval` state to "1.5" with unit "gal/min"; reuse in coordinator tests by calling `hass.states.async_set("sensor.flume_current_interval", "X.X")` to simulate different readings
- `tests/conftest.py: mock_valve_entities` — returns `["switch.rachio_zone_1", "switch.rachio_zone_2", "valve.os_zone_3"]`; use to simulate zone on/off states in coordinator tests

### Established Patterns
- All CONF_* constants are in `const.py` — add new ones there, never inline strings
- `ConfigEntry.runtime_data` pattern (HA 2024.4+): store coordinator on `entry.runtime_data` in `async_setup_entry`, not in `hass.data[DOMAIN]`
- `PLATFORMS: list[str] = []` in `__init__.py` — Phase 3 updates this to `["sensor"]`

### Integration Points
- `__init__.py: async_setup_entry` — wire coordinator creation, first refresh, and `async_forward_entry_setups` for "sensor" platform
- `__init__.py: async_unload_entry` — update PLATFORMS to `["sensor"]` so unload works correctly
- Phase 4 (Calibration) will store `calibrated_flow` into `ConfigEntry.options.zones[entity_id]["calibrated_flow"]` — coordinator reads this field; it will be `None` until calibrated
- Phase 5 (Leak Detection) extends coordinator `_async_update_data` to add threshold comparison — design coordinator with extension in mind

</code_context>

<specifics>
## Specific Ideas

- Multi-zone attribution with calibrated values: the logic is "sum of calibrated flows for active+calibrated zones should approximately equal Flume reading (within margin defined by threshold_multiplier)". If it does, each calibrated zone gets its calibrated_flow credited per poll interval. This is the same threshold_multiplier the user configured per zone.
- Store write: debounce writes (e.g., SAVE_DELAY = 30s) to avoid hammering storage every 30s poll. But always write on coordinator shutdown/unload.

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope.

</deferred>

---

*Phase: 03-coordinator-usage*
*Context gathered: 2026-03-20*
