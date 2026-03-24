# Phase 5: Leak Detection - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Extend `_async_update_data` in `IrrigationCoordinator` to detect flow anomalies on active zones and respond: auto-shutoff the valve (if enabled) and fire an HA notification (if enabled). Add a ramp-up skip window, notification deduplication, a zone status sensor (idle/running/leak_detected), and an acknowledge button entity per zone. Phase is complete when all DETECT-01 through DETECT-05 requirements are satisfied.

</domain>

<decisions>
## Implementation Decisions

### Ramp-up Period (DETECT-02)
- **Skip window**: configurable poll count, default **2 polls** — at 30s interval = 60s skip after valve turns ON
- New config key: `CONF_RAMP_UP_POLLS = "ramp_up_polls"`, `DEFAULT_RAMP_UP_POLLS = 2`
- Stored in `ConfigEntry.options` (global, not per-zone — Claude's discretion whether global or per-zone)
- **Tracking**: `coordinator._ramp_up_counters: dict[zone_id, int]` — decremented each poll while > 0
- **Reset**: every time a zone transitions from OFF → ON, counter is reset to `DEFAULT_RAMP_UP_POLLS` (or configured value)
- Multiple starts in same day: always reset on each new ON transition

### Notification Deduplication
- **Fire once per leak event** — one notification when the anomaly is first detected on a zone
- Tracking: `coordinator._leak_notified: set[zone_id]` — zone added when notification fires
- **Reset**: zone removed from `_leak_notified` when it transitions from ON → OFF
- Next run: if zone starts again and exceeds threshold, notify again

### Zone Status Sensor (new entity)
- New sensor per monitored zone: `sensor.irrigation_monitor_{zone_id}_status`
- States: `"idle"` / `"running"` / `"leak_detected"`
- `"leak_detected"` persists even after valve is shut off / zone turns off
- Cleared **only** by user pressing the "Acknowledge leak" button entity
- Exposed to HA dashboards, automations, and the Phase 6 Lovelace card

### Acknowledge Leak Button (new entity)
- New button per monitored zone: `button.irrigation_monitor_{zone_id}_acknowledge_leak`
- Only meaningful when zone status is `"leak_detected"` — pressing it at any time is safe (idempotent)
- On press: sets zone status back to `"idle"`, clears `_leak_notified` for that zone
- No background task needed — synchronous state update

### Leak Detection Logic (in `_async_update_data`)
After computing `flow_rate` per zone:
```python
if is_on and calibrated_flow is not None and zone_id not in self._ramp_up_counters_active(zone_id):
    if flow_rate > calibrated_flow * threshold_multiplier:
        # Leak detected
        self._leak_statuses[zone_id] = "leak_detected"
        if zone_cfg.get(CONF_SHUTOFF_ENABLED, True):
            await self._turn_valve(zone_id, turn_on=False)
        if zone_cfg.get(CONF_ALERTS_ENABLED, True) and zone_id not in self._leak_notified:
            await self._fire_leak_notification(zone_id, flow_rate, calibrated_flow)
            self._leak_notified.add(zone_id)
```

### Zone State Tracking
- `coordinator._zone_was_on: dict[zone_id, bool]` — tracks previous poll state to detect ON→OFF and OFF→ON transitions
- ON→OFF transition: remove zone from `_leak_notified` (reset dedup)
- OFF→ON transition: set/reset `_ramp_up_counters[zone_id] = ramp_up_polls_setting`
- Ramp-up active: `_ramp_up_counters.get(zone_id, 0) > 0`; decrement each poll while zone is ON

### Leak Notification Content (DETECT-04)
`"Leak detected on Zone N. Flow: X.X gal/min (expected: Y.Y gal/min). Valve has been shut off."` (or "Valve shutoff is disabled." if shutoff_enabled=False)

### Uncalibrated Zone Behavior
No leak detection on uncalibrated zones (`calibrated_flow is None`). Silent skip — zone status stays `"running"`. Consistent with Phase 3 behavior.

### Flume Unavailability (DETECT-05)
Already handled by `UpdateFailed` → `last_update_success=False` → all entities go unavailable. No shutoff or alert fires when Flume is unavailable.

### New Entities Summary
- `sensor.irrigation_monitor_{zone_id}_status` — zone status sensor ("idle"/"running"/"leak_detected")
- `button.irrigation_monitor_{zone_id}_acknowledge_leak` — acknowledge button (clears leak_detected)

### Claude's Discretion
- Whether `ramp_up_polls` is global or per-zone in options
- Exact notification ID format for the leak notification
- Whether `_leak_statuses` is a coordinator dict or stored in ZoneData

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing coordinator (extend, don't replace)
- `custom_components/irrigation_monitor/coordinator.py` — `_async_update_data`, `ZoneData`, `_turn_valve`, `_zone_is_on`, `_zone_was_on` tracking needed; leak detection slots into the existing per-zone loop
- `custom_components/irrigation_monitor/const.py` — add `CONF_RAMP_UP_POLLS`, `DEFAULT_RAMP_UP_POLLS`
- `custom_components/irrigation_monitor/__init__.py` — PLATFORMS already `["sensor", "button"]`; no change needed unless new platform type required

### Existing entities (extend)
- `custom_components/irrigation_monitor/sensor.py` — add `ZoneStatusSensor` here
- `custom_components/irrigation_monitor/button.py` — add `AcknowledgeLeakButtonEntity` here

### Requirements
- `.planning/REQUIREMENTS.md` — DETECT-01 through DETECT-05

### Research references
- `.planning/research/ARCHITECTURE.md` — coordinator entity update pattern
- `.planning/research/PITFALLS.md` — P4 (race condition: coordinator reads before zone state settles), P5 (Flume unavailable)

### Tests
- `tests/conftest.py` — existing fixtures; extend with leak scenario helpers
- `tests/test_coordinator.py` — existing coordinator tests (must stay green)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `coordinator._turn_valve(zone_id, turn_on)` — already domain-aware; reuse directly for shutoff
- `coordinator._zone_is_on(entity_id)` — reuse for ramp-up transition detection
- `coordinator.ZoneData(flow_rate, daily_usage, is_available)` — extend with `status: str` field OR use a separate `_leak_statuses` dict (Claude's discretion)
- `tests/conftest.py: mock_valve_entities` — returns switch + valve domain entities; set state to "on"/"open" to simulate running zones
- Phase 4's `_calibrating` set pattern — mirrors the `_leak_notified` set pattern needed here

### Established Patterns
- `coordinator._pending_calibrations` / `_calibrating` sets — same pattern for `_leak_notified` and `_ramp_up_counters`
- Notification via `hass.services.async_call("persistent_notification", "create", {...})` — established in Phase 4
- State transition tracking (`_zone_was_on`) — new pattern needed; track previous poll state to detect ON→OFF / OFF→ON

### Integration Points
- `ZoneData` feeds `sensor.py` (DailyUsageSensor, FlowRateSensor) and the new `ZoneStatusSensor`
- `button.py` gets `AcknowledgeLeakButtonEntity` alongside existing `CalibrateButtonEntity`
- Phase 6 (Lovelace card) reads `sensor.*.status` to show idle/running/leak_detected per zone

</code_context>

<specifics>
## Specific Ideas

- The `_zone_was_on` dict enables clean transition detection: `was_on = self._zone_was_on.get(zone_id, False)`; `is_on = self._zone_is_on(zone_id)`; then `if was_on and not is_on: # OFF transition` and `if not was_on and is_on: # ON transition`; update `_zone_was_on[zone_id] = is_on` at end of each zone's loop iteration.

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope.

</deferred>

---

*Phase: 05-leak-detection*
*Context gathered: 2026-03-24*
