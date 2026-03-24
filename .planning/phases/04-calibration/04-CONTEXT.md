# Phase 4: Calibration - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the calibration system: a ButtonEntity per monitored zone that triggers an async calibration sequence. The sequence checks for background flow, turns the valve on, waits for flow to stabilize using variance detection (max 60s), samples the Flume average over 3 readings, and saves the baseline to ConfigEntry.options. Also handles re-calibration with a persistent HA notification offering "Save" / "Cancel" action buttons so the user can compare old vs. new values before committing. No leak detection logic in this phase — calibration just writes the `calibrated_flow` value that Phase 5 will use.

</domain>

<decisions>
## Implementation Decisions

### Calibration Progress Feedback
- **In-progress**: fire a persistent HA notification — `"Calibrating Zone N… please wait"` — when calibration starts
- **Success (first calibration)**: replace in-progress notification with `"Zone N calibrated: X.X gal/min"`
- **Failure**: fire a failure notification explaining what went wrong (Flume offline, valve wouldn't open, stabilization timeout, etc.) AND turn the valve off (always leave system in known state)
- **No calibration status sensor** — notifications only, no extra entity

### Re-Calibration Flow (zone already has calibrated_flow set)
- Run the full calibration sequence to get the new baseline value
- At completion: fire a persistent HA notification with **HA action buttons**: `"Zone N recalibration complete. Old: Y.Y gal/min → New: X.X gal/min. Save or Cancel?"`
  - Action button: `irrigation_monitor_confirm_calibration_{zone_id}` → save new value to ConfigEntry.options
  - Action button: `irrigation_monitor_cancel_calibration_{zone_id}` → discard new value, keep old
- Pending result stored in coordinator memory (not persisted) until user confirms or cancels
- If user ignores: pending result expires on next HA restart (not auto-saved)

### Stabilization Detection
- **Method**: variance detection — take readings every 5s; when variance across last 3 consecutive readings drops below a threshold (e.g., std_dev < 0.05 gal/min), declare stable
- **Timeout**: 60 seconds max; if not stable by then, fail with notification + turn valve off
- **After stabilization**: sample Flume 3 times over 15s (readings spaced 5s apart), average them as the baseline

### Background Flow Check (CALIB-02)
- Before starting calibration, read current Flume state
- If `flume_flow > background_flow_threshold` → abort with notification: `"Background water flow detected (X.X gal/min). Stop all other water use before calibrating."`
- **Threshold**: configurable per integration (global, not per zone), default `0.1 gal/min`
- New config key: `CONF_BACKGROUND_THRESHOLD` — stored in `ConfigEntry.data` (set during config flow setup, editable in options flow)
- **Note**: This constant needs to be added to options flow UI in Phase 2 retroactively OR added as a new options field in this phase

### Already-Running Guard (CALIB-03)
- Before starting calibration, check if the target zone is already ON
- If already running → abort with notification: `"Zone N is already running. Stop it first before calibrating."`
- Do NOT turn it off; leave it as-is

### Calibration Persistence (CALIB-05)
- Write `calibrated_flow` directly to `ConfigEntry.options.zones[zone_id]["calibrated_flow"]` via `hass.config_entries.async_update_entry(entry, options=updated_options)`
- The coordinator already reads this field — it becomes active on the next poll after options update
- **Merge pattern** (same as Phase 2 options flow): `existing = dict(entry.options); existing["zones"][zone_id]["calibrated_flow"] = new_value; async_update_entry(entry, options=existing)`

### Calibration Sequence (CALIB-04 full flow)
```
1. Check background flow > threshold → abort if yes
2. Check zone is NOT already running → abort if yes
3. Fire "Calibrating Zone N..." persistent notification
4. Call hass.services.async_call("homeassistant", "turn_on", {"entity_id": valve_entity})
   — or appropriate domain (switch.turn_on / valve.open_valve depending on entity domain)
5. Wait for variance detection to stabilize (poll every 5s, max 60s)
   — if Flume goes unavailable during wait → fail
   — if timeout → fail
6. Sample 3 readings spaced 5s apart, compute average
7. If this is a re-calibration (calibrated_flow is not None):
   a. Store pending result in coordinator memory
   b. Fire persistent notification with HA action buttons (Save / Cancel)
   c. Register event listener for action button events
   Else (first calibration):
   a. Write new calibrated_flow to ConfigEntry.options immediately
   b. Fire success notification
8. Call hass.services.async_call to turn valve OFF (always, regardless of success/failure)
```

### New Const Keys
- `CONF_BACKGROUND_THRESHOLD = "background_flow_threshold"`
- `DEFAULT_BACKGROUND_THRESHOLD = 0.1`
- `CONF_PENDING_CALIBRATION = "pending_calibration"` (in-memory only, not stored)

### Claude's Discretion
- Exact persistent notification IDs (for dismissal/replacement)
- HA event names for action buttons
- Whether background_flow_threshold is added to options flow in this phase or left for a follow-up
- Variance detection threshold value (std_dev < 0.05 recommended by research)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 3 artifacts (extend)
- `custom_components/irrigation_monitor/coordinator.py` — IrrigationCoordinator; calibration sequence runs as a method on this class or as a standalone async function called by the button
- `custom_components/irrigation_monitor/const.py` — add CONF_BACKGROUND_THRESHOLD, DEFAULT_BACKGROUND_THRESHOLD here
- `custom_components/irrigation_monitor/__init__.py` — add "button" to PLATFORMS list

### Phase 2 artifacts (options merge pattern)
- `custom_components/irrigation_monitor/config_flow.py` — options merge pattern; same pattern applies when writing calibrated_flow

### Requirements
- `.planning/REQUIREMENTS.md` — CALIB-01 through CALIB-06

### Research references
- `.planning/research/ARCHITECTURE.md` — ButtonEntity pattern, ConfigEntry options update
- `.planning/research/PITFALLS.md` — P3 (options merge — critical), P10 (calibration while zone already running)

### Tests
- `tests/conftest.py` — `mock_flume_entity`, `mock_valve_entities` fixtures available

No external specs — requirements fully captured in decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `coordinator.py: _zone_is_on(entity_id)` — already handles switch/valve domain state differences; reuse in CALIB-03 already-running check
- `coordinator.py: IrrigationCoordinator` — calibration method can be an async method on this class; has access to `self._entry`, `self.hass`, `self._store`
- `tests/conftest.py: mock_flume_entity` — returns `"sensor.flume_current_interval"`; can update its state mid-test with `hass.states.async_set(...)` to simulate flow changes
- `tests/conftest.py: mock_valve_entities` — includes switch and valve domain entities

### Established Patterns
- Options merge: `existing = dict(entry.options); existing["zones"][zone_id]["calibrated_flow"] = val; hass.config_entries.async_update_entry(entry, options=existing)` — CRITICAL, same as Phase 2
- Turn on/off valve: `hass.services.async_call(domain, service, {"entity_id": entity_id})` where domain="switch" → service="turn_on"/"turn_off"; domain="valve" → service="open_valve"/"close_valve"
- `PLATFORMS = ["sensor"]` in `__init__.py` → Phase 4 adds "button" → `PLATFORMS = ["sensor", "button"]`

### Integration Points
- `coordinator.py` → Phase 5 (Leak Detection) reads `calibrated_flow` from `entry.options` — write path here must be correct
- New `button.py` platform → one `CalibrateButtonEntity` per monitored zone
- ButtonEntity presses trigger `async_press()` → calls coordinator calibration method

</code_context>

<specifics>
## Specific Ideas

- HA persistent notification action buttons: fired via `hass.bus.async_fire("mobile_app_notification_action", {...})` listener or via HA's `persistent_notification.create` with `actions` list (HA 2023.4+). Research needed to confirm exact API.
- The "pending calibration" approach for re-calibration is pure in-memory: `coordinator._pending_calibrations: dict[zone_id, float]`. When action button event fires, either writes to options (save) or pops from dict (cancel).
- Valve turn-on service: `switch.turn_on` for switch domain, `valve.open_valve` for valve domain.

</specifics>

<deferred>
## Deferred Ideas

- Adding `background_flow_threshold` to the options flow UI — could be done in this phase or as a follow-up. If deferred, hard-code reading from ConfigEntry.data or fall back to DEFAULT_BACKGROUND_THRESHOLD.

</deferred>

---

*Phase: 04-calibration*
*Context gathered: 2026-03-24*
