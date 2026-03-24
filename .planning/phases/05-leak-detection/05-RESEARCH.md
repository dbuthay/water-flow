# Phase 5: Leak Detection - Research

**Researched:** 2026-03-23
**Domain:** Home Assistant custom integration — coordinator extension, new entity types, state machine
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Leak detection logic added inside existing `_async_update_data` loop
- Ramp-up: `_ramp_up_counters: dict[zone_id, int]`, reset on OFF→ON transition, skip detection while counter > 0, decrement each poll
- Dedup: `_leak_notified: set[zone_id]`, add on first notification, clear on ON→OFF transition
- Zone state tracking: `_zone_was_on: dict[zone_id, bool]` to detect transitions
- New entities: `ZoneStatusSensor` (idle/running/leak_detected) + `AcknowledgeLeakButtonEntity`
- `ZoneData` may need a `status` field OR separate `_leak_statuses` dict
- `_turn_valve(zone_id, turn_on=False)` already exists for shutoff
- Notification via `hass.services.async_call("persistent_notification", "create", {...})`
- Flume unavailable: already handled by UpdateFailed → no change needed
- Ramp-up polls is a global option (stored in ConfigEntry.options), default 2 polls

### Claude's Discretion
- Whether `ramp_up_polls` is global or per-zone in options (decided: global)
- Exact notification ID format for the leak notification
- Whether `_leak_statuses` is a coordinator dict or stored in ZoneData

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DETECT-01 | Integration monitors flow rate whenever a valve is active and compares it against the zone's calibrated baseline × threshold multiplier | Coordinator loop already computes `flow_rate` and has `calibrated_flow`; threshold comparison is a simple conditional |
| DETECT-02 | Integration skips leak evaluation for a configurable number of polls after a valve turns on (ramp-up period to avoid false positives) | `_ramp_up_counters` dict + `_zone_was_on` dict enable clean OFF→ON detection and per-zone countdown; CONF_RAMP_UP_POLLS goes in options |
| DETECT-03 | When flow exceeds the threshold and auto-shutoff is enabled for that zone, integration turns off the valve via HA service call | `_turn_valve(zone_id, turn_on=False)` already works for both switch and valve domains; safe to await mid-loop |
| DETECT-04 | When a leak is detected and alerts are enabled for that zone, integration fires an HA notification identifying the zone and the measured vs. expected flow | `async_create` pattern from Phase 4 is directly reusable; notification ID format mirrors calibration pattern |
| DETECT-05 | Integration handles Flume sensor being unavailable or returning unknown state without crashing or triggering false leak events | Already handled: `UpdateFailed` in `_async_update_data` stops the loop before leak logic runs; no new code required |
</phase_requirements>

---

## Summary

Phase 5 extends `IrrigationCoordinator._async_update_data` with leak detection logic that slots cleanly into the existing per-zone `for` loop. The coordinator already computes `flow_rate`, holds `calibrated_flow` from options, and owns `_turn_valve()`. Three new coordinator instance variables handle the state machine: `_zone_was_on` (transition detection), `_ramp_up_counters` (skip window), and `_leak_notified` (dedup). A separate `_leak_statuses` dict (coordinator-level, not inside `ZoneData`) tracks the persistent "leak_detected" state that survives valve shutoff and requires explicit user acknowledgment.

Two new entity classes are added in existing platform files: `ZoneStatusSensor` in `sensor.py` and `AcknowledgeLeakButtonEntity` in `button.py`. Neither requires a new platform — `__init__.py` already lists both `["sensor", "button"]`. The status sensor uses no `state_class` (enum-like text values have no numeric aggregation) and no `device_class` (no matching class for status strings). The acknowledge button is simpler than `CalibrateButtonEntity` — its `async_press` is synchronous state update, no background task needed.

**Primary recommendation:** Use a coordinator-level `_leak_statuses: dict[str, str]` dict (not a `ZoneData` field) to hold the persistent leak state, because `ZoneData` is rebuilt every poll from scratch and a field there would be overwritten before `ZoneStatusSensor` can read it. The `ZoneStatusSensor` reads from `coordinator._leak_statuses` directly (not from `coordinator.data`).

---

## Standard Stack

### Core (already in project — no new installs)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `homeassistant.helpers.update_coordinator` | HA 2026.x | `DataUpdateCoordinator`, `CoordinatorEntity` | Established in Phase 3 |
| `homeassistant.components.sensor` | HA 2026.x | `SensorEntity`, `SensorStateClass` | Established in Phase 3 |
| `homeassistant.components.button` | HA 2026.x | `ButtonEntity` | Established in Phase 4 |
| `homeassistant.components.persistent_notification` | HA 2026.x | `async_create`, `async_dismiss` | Established in Phase 4 |

### New constants (to add to `const.py`)
```python
CONF_RAMP_UP_POLLS = "ramp_up_polls"
DEFAULT_RAMP_UP_POLLS = 2
```

**No new pip packages.** This phase is pure coordinator logic and entity additions.

---

## Architecture Patterns

### Recommended Project Structure (additions only)
```
custom_components/irrigation_monitor/
├── const.py          # add CONF_RAMP_UP_POLLS, DEFAULT_RAMP_UP_POLLS
├── coordinator.py    # add 3 instance vars + _fire_leak_notification + leak logic in loop
├── sensor.py         # add ZoneStatusSensor + wire in async_setup_entry
└── button.py         # add AcknowledgeLeakButtonEntity + wire in async_setup_entry
tests/
├── conftest.py       # add mock_calibrated_config_entry fixture (zone with calibrated_flow set)
└── test_leak.py      # new test file for DETECT-01 through DETECT-05
```

---

### Pattern 1: Coordinator instance variable initialization

**What:** Three new dicts/sets initialize in `__init__` alongside `_pending_calibrations` and `_calibrating`.

**When to use:** Always initialize mutable state in `__init__`, never lazily in `_async_update_data`.

```python
# In IrrigationCoordinator.__init__ (after existing vars):
self._zone_was_on: dict[str, bool] = {}
self._ramp_up_counters: dict[str, int] = {}
self._leak_notified: set[str] = set()
self._leak_statuses: dict[str, str] = {}  # "idle" | "running" | "leak_detected"
```

**Why not lazy:** If `_zone_was_on` is absent on first poll, the `dict.get(zone_id, False)` default handles the cold-start case correctly (treat as "was off"). But initializing in `__init__` makes the type contract explicit and avoids AttributeError if anything accesses these before `_async_update_data` runs.

---

### Pattern 2: Transition detection in the per-zone loop

**What:** Read previous state, compute current state, detect edges, update tracking at end of iteration.

```python
# Inside for zone_id in monitored: loop, before leak detection:
was_on = self._zone_was_on.get(zone_id, False)
is_on = self._zone_is_on(zone_id)  # already computed above in existing code

# OFF → ON transition: reset ramp-up counter
if not was_on and is_on:
    ramp_up_polls = self._entry.options.get(CONF_RAMP_UP_POLLS, DEFAULT_RAMP_UP_POLLS)
    self._ramp_up_counters[zone_id] = ramp_up_polls

# ON → OFF transition: clear dedup, reset status if not leak_detected
if was_on and not is_on:
    self._leak_notified.discard(zone_id)
    # Note: _leak_statuses["leak_detected"] persists across OFF transitions
    # Only AcknowledgeLeakButtonEntity clears it

# Decrement ramp-up counter while zone is running
if is_on and self._ramp_up_counters.get(zone_id, 0) > 0:
    self._ramp_up_counters[zone_id] -= 1

# Update tracking for next poll — MUST be at END of loop body
self._zone_was_on[zone_id] = is_on
```

**Critical ordering:** `_zone_was_on[zone_id] = is_on` must come after all transition checks. If it's placed first, was_on and is_on are identical and edges are never detected.

---

### Pattern 3: Leak detection conditional

**What:** Placed after `flow_rate` and `usage_increment` are computed in the existing loop.

```python
# After computing flow_rate, inside "if is_on and calibrated_flow is not None:" block:
ramp_active = self._ramp_up_counters.get(zone_id, 0) > 0
threshold = zone_cfg.get(CONF_THRESHOLD_MULTIPLIER, DEFAULT_THRESHOLD_MULTIPLIER)

if not ramp_active and flow_rate > calibrated_flow * threshold:
    # Leak detected
    self._leak_statuses[zone_id] = "leak_detected"
    if zone_cfg.get(CONF_SHUTOFF_ENABLED, True):
        await self._turn_valve(zone_id, turn_on=False)
    if zone_cfg.get(CONF_ALERTS_ENABLED, True) and zone_id not in self._leak_notified:
        await self._fire_leak_notification(zone_id, flow_rate, calibrated_flow)
        self._leak_notified.add(zone_id)
elif is_on:
    # Running without anomaly
    if self._leak_statuses.get(zone_id) != "leak_detected":
        self._leak_statuses[zone_id] = "running"
else:
    # Zone is off — set idle only if not in persistent leak_detected state
    if self._leak_statuses.get(zone_id) != "leak_detected":
        self._leak_statuses[zone_id] = "idle"
```

**Key insight on status persistence:** `"leak_detected"` must NOT be overwritten by the idle/running branches on subsequent polls. The `!= "leak_detected"` guard preserves the alert state until the user presses acknowledge.

---

### Pattern 4: `_fire_leak_notification` helper method

**What:** Extracted into a private async method to keep `_async_update_data` readable and to make it mockable in tests.

```python
async def _fire_leak_notification(
    self, zone_id: str, flow_rate: float, calibrated_flow: float
) -> None:
    """Fire a persistent notification for a detected leak."""
    zone_cfg = self._entry.options.get(CONF_ZONES, {}).get(zone_id, {})
    shutoff_enabled = zone_cfg.get(CONF_SHUTOFF_ENABLED, True)
    shutoff_msg = "Valve has been shut off." if shutoff_enabled else "Valve shutoff is disabled."
    zone_slug = zone_id.replace(".", "_")
    async_create(
        self.hass,
        (
            f"Leak detected on {zone_id}. "
            f"Flow: {flow_rate:.1f} gal/min (expected: {calibrated_flow:.1f} gal/min). "
            f"{shutoff_msg}"
        ),
        title="Irrigation Monitor — Leak Alert",
        notification_id=f"leak_{zone_slug}",
    )
```

**Notification ID format:** `leak_{zone_slug}` — mirrors the `calib_{zone_id}_*` pattern from Phase 4. Using `zone_slug` (dots replaced with underscores) keeps it valid as an HA notification_id string.

---

### Pattern 5: `await self._turn_valve()` inside `_async_update_data`

**What:** `_turn_valve` is `async def` and uses `await self.hass.services.async_call(..., blocking=True)`. It is safe to call with `await` mid-loop inside `_async_update_data` because the HA event loop is single-threaded and `async_call` with `blocking=True` suspends until the service call completes.

**Concern:** Does calling `_turn_valve` mid-loop cause state to shift under the loop? No — the coordinator loop reads `_zone_is_on()` at the top of each zone's iteration. Calling `_turn_valve` for zone 1 mid-loop does not retroactively affect zone 1's `is_on` for this poll (already read). It will affect zone 1 on the NEXT poll, which is correct behavior.

**Confirmed safe** (HIGH confidence): Phase 4's calibration code already awaits `_turn_valve` inside `async_calibrate_zone`, which is also an async context. Same pattern, same safety guarantees.

---

### Pattern 6: ZoneStatusSensor — reads coordinator dict, not ZoneData

**What:** `ZoneStatusSensor` reads from `coordinator._leak_statuses` directly rather than from `coordinator.data` (the `ZoneData` dict). This is the correct architectural choice because `"leak_detected"` must persist across multiple polls and survives valve shutoff.

**Why NOT ZoneData:** `ZoneData` is reconstructed from scratch every poll in `_async_update_data`. Adding a `status` field would require setting it correctly every poll, including preserving "leak_detected" from the previous poll — effectively duplicating `_leak_statuses` into `ZoneData`. Simpler to read `_leak_statuses` directly.

**CoordinatorEntity update behavior:** `CoordinatorEntity` calls `async_write_ha_state()` automatically after every coordinator refresh via `_handle_coordinator_update`. The `ZoneStatusSensor.native_value` property will be called at that point and will read the freshly-updated `_leak_statuses`.

```python
class ZoneStatusSensor(CoordinatorEntity[IrrigationCoordinator], SensorEntity):
    """Sensor showing zone status: idle / running / leak_detected."""

    _attr_has_entity_name = True
    # No state_class — text enum, not numeric
    # No device_class — no matching HA device class for status strings

    def __init__(self, coordinator, entry, zone_id):
        super().__init__(coordinator)
        self._zone_id = zone_id
        zone_slug = zone_id.replace(".", "_")
        self._attr_unique_id = f"{entry.entry_id}_{zone_id}_status"
        self._attr_name = f"{DOMAIN} {zone_slug} status"
        self.entity_id = f"sensor.{DOMAIN}_{zone_slug}_status"

    @property
    def native_value(self) -> str:
        """Return zone status string."""
        return self.coordinator._leak_statuses.get(self._zone_id, "idle")
```

---

### Pattern 7: AcknowledgeLeakButtonEntity — synchronous press, no background task

**What:** Unlike `CalibrateButtonEntity`, the acknowledge action is instant state mutation. No I/O, no async service calls. `async_press` can call `coordinator` methods directly and call `async_write_ha_state()` on relevant sensors.

```python
class AcknowledgeLeakButtonEntity(CoordinatorEntity[IrrigationCoordinator], ButtonEntity):
    """Button that clears leak_detected status for one zone."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinator, entry, zone_id):
        super().__init__(coordinator)
        self._zone_id = zone_id
        zone_slug = zone_id.replace(".", "_")
        self._attr_unique_id = f"{entry.entry_id}_{zone_id}_acknowledge_leak"
        self._attr_name = f"{DOMAIN} {zone_slug} acknowledge_leak"
        self.entity_id = f"button.{DOMAIN}_{zone_slug}_acknowledge_leak"

    async def async_press(self) -> None:
        """Clear leak_detected status and dedup flag for this zone."""
        self.coordinator._leak_statuses[self._zone_id] = "idle"
        self.coordinator._leak_notified.discard(self._zone_id)
        # Trigger entity updates so ZoneStatusSensor reflects the change immediately
        await self.coordinator.async_request_refresh()
```

**Alternative to `async_request_refresh`:** Call `self.coordinator.async_update_listeners()` (a `@callback`, not async). This immediately calls `async_write_ha_state()` on all registered `CoordinatorEntity` listeners without triggering a new Flume poll. Prefer this for acknowledge — it's lighter weight and avoids an unnecessary network read.

```python
    async def async_press(self) -> None:
        self.coordinator._leak_statuses[self._zone_id] = "idle"
        self.coordinator._leak_notified.discard(self._zone_id)
        self.coordinator.async_update_listeners()  # @callback — no await needed
```

---

### Pattern 8: Wiring new entities in `async_setup_entry`

**sensor.py** — extend the existing loop:
```python
for zone_id in monitored:
    entities.append(DailyUsageSensor(coordinator, entry, zone_id))
    entities.append(FlowRateSensor(coordinator, entry, zone_id))
    entities.append(ZoneStatusSensor(coordinator, entry, zone_id))  # NEW
async_add_entities(entities)
```

**button.py** — extend the list comprehension (or convert to explicit loop):
```python
entities = []
for zone_id in monitored:
    entities.append(CalibrateButtonEntity(coordinator, entry, zone_id))
    entities.append(AcknowledgeLeakButtonEntity(coordinator, entry, zone_id))  # NEW
async_add_entities(entities)
```

---

### Pattern 9: mock_calibrated_config_entry fixture for leak tests

The existing `mock_config_entry` fixture has `CONF_CALIBRATED_FLOW: None` for both zones. Leak detection requires a calibrated zone. Add a new fixture to `conftest.py`:

```python
@pytest.fixture
def mock_calibrated_config_entry(
    hass: HomeAssistant,
    mock_flume_entity: str,
    mock_valve_entities: list[str],
) -> MockConfigEntry:
    """ConfigEntry with zone 1 calibrated at 2.0 gal/min."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_FLUME_ENTITY_ID: mock_flume_entity,
            CONF_MONITORED_ZONES: mock_valve_entities[:2],
            CONF_POLL_INTERVAL: 30,
        },
        options={
            CONF_ZONES: {
                mock_valve_entities[0]: {
                    CONF_SHUTOFF_ENABLED: True,
                    CONF_ALERTS_ENABLED: True,
                    CONF_CALIBRATED_FLOW: 2.0,  # calibrated
                    CONF_THRESHOLD_MULTIPLIER: 1.5,
                },
                mock_valve_entities[1]: {
                    CONF_SHUTOFF_ENABLED: True,
                    CONF_ALERTS_ENABLED: True,
                    CONF_CALIBRATED_FLOW: None,
                    CONF_THRESHOLD_MULTIPLIER: 1.5,
                },
            },
            CONF_RAMP_UP_POLLS: 0,  # disable ramp-up for most leak tests
        },
    )
    entry.add_to_hass(hass)
    return entry
```

**Key:** Set `CONF_RAMP_UP_POLLS: 0` in leak tests by default so tests don't need to simulate N pre-polls to get through the ramp-up window. Dedicated ramp-up tests use a non-zero value.

---

### Anti-Patterns to Avoid

- **Setting `_zone_was_on` before transition checks:** The update must come last in the loop body, after all edge detection.
- **Overwriting `"leak_detected"` in the idle/running branches:** Always guard with `!= "leak_detected"` before setting idle/running.
- **Adding a `status` field to `ZoneData`:** The dataclass is reconstructed each poll. Use `_leak_statuses` dict on the coordinator.
- **Using `async_request_refresh()` in `async_press`:** Triggers an unnecessary Flume poll. Use `async_update_listeners()` instead.
- **Calling `await self._turn_valve()` outside the `is_on and calibrated_flow is not None` guard:** Could issue spurious shutoffs when zone is off.
- **Calling `async_create` (from `homeassistant.components.persistent_notification`) when the intent is the service call pattern:** The existing Phase 4 code uses BOTH import styles. For leak notifications, match the Phase 4 calibration pattern — use the `async_create` helper directly (already imported in `coordinator.py`).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Persistent state across polls | ZoneData field updated each poll | `_leak_statuses` dict on coordinator | ZoneData is rebuilt from scratch; coordinator dict persists |
| Entity state propagation after acknowledge | Manual `async_write_ha_state()` on each entity | `coordinator.async_update_listeners()` | Single call notifies all registered CoordinatorEntity listeners |
| Valve shutoff | Custom service call | `self._turn_valve(zone_id, turn_on=False)` | Already handles switch vs valve domain branching |
| Notification | `hass.services.async_call("persistent_notification", "create", ...)` | `async_create(self.hass, ...)` | Direct helper already imported; avoids service dispatch overhead |

---

## Common Pitfalls

### Pitfall 1: `_zone_was_on` update ordering
**What goes wrong:** If `_zone_was_on[zone_id] = is_on` is placed BEFORE transition logic, `was_on == is_on` always, and no transitions are ever detected. Ramp-up counter never resets; `_leak_notified` never clears.
**Why it happens:** Natural to update the tracker at the top of the loop iteration.
**How to avoid:** Place `_zone_was_on[zone_id] = is_on` as the LAST statement in the zone's loop body.
**Warning signs:** Tests show leak notification fires on every poll (dedup not working); ramp-up never activates.

### Pitfall 2: `"leak_detected"` overwritten on next poll
**What goes wrong:** After shutoff, the valve state becomes "off", so `is_on = False`. The status branch sets `_leak_statuses[zone_id] = "idle"`, erasing the alert.
**Why it happens:** Forgetting that `"leak_detected"` is a user-acknowledged state, not a transient condition.
**How to avoid:** Guard idle/running status assignments: `if self._leak_statuses.get(zone_id) != "leak_detected": ...`
**Warning signs:** `ZoneStatusSensor` flips back to "idle" immediately after shutoff without user pressing acknowledge.

### Pitfall 3: Ramp-up counter race on rapid ON/OFF/ON cycles
**What goes wrong:** Zone toggles OFF then ON within one poll interval. The OFF→ON transition sets counter to N, but `was_on` was already updated to True, so the transition is missed.
**Why it happens:** See Pitfall 1 (update ordering). If ordering is correct, this resolves itself.
**How to avoid:** Correct update ordering (Pitfall 1 fix). Ramp-up correctly resets on each ON transition.
**Warning signs:** Leak fires immediately after valve restart.

### Pitfall 4: `CONF_RAMP_UP_POLLS` absent from options in existing config entries
**What goes wrong:** Users who configured the integration before Phase 5 don't have `CONF_RAMP_UP_POLLS` in their options. Code that calls `self._entry.options[CONF_RAMP_UP_POLLS]` (without `.get()`) raises `KeyError`.
**Why it happens:** Options flow wasn't updated to write the new key.
**How to avoid:** Always use `.get(CONF_RAMP_UP_POLLS, DEFAULT_RAMP_UP_POLLS)` when reading this option. The key is optional and defaults gracefully.
**Warning signs:** Integration crashes on first poll after Phase 5 upgrade for existing installs.

### Pitfall 5: Notification dedup across valve restart
**What goes wrong:** `_leak_notified` is cleared ON→OFF (correct). But if the coordinator tracks `_zone_was_on` only for zones that are currently in `monitored`, a zone removed and re-added might not clear the set.
**Why it happens:** Unlikely in this integration (monitored zones are fixed at config time), but worth noting.
**How to avoid:** `_leak_notified.discard(zone_id)` (not `remove`) on every ON→OFF transition. No risk of KeyError.
**Warning signs:** Leak notification never fires on second run after a leak on first run.

### Pitfall 6: Existing test fixture misconfiguration breaks DETECT-01 tests
**What goes wrong:** The default `mock_config_entry` fixture has `CONF_CALIBRATED_FLOW: None`. A test using it expects leak detection to fire, but the `if calibrated_flow is not None:` guard silently skips detection.
**Why it happens:** Reusing the uncalibrated fixture for leak tests.
**How to avoid:** Use the new `mock_calibrated_config_entry` fixture for all DETECT tests.
**Warning signs:** Leak tests pass vacuously (no shutoff, no notification) without assertion errors.

---

## Code Examples

### Verified: coordinator update flow (from reading coordinator.py)
```python
# _async_update_data returns dict[str, ZoneData]
# CoordinatorEntity._handle_coordinator_update calls async_write_ha_state()
# Therefore: every coordinator poll triggers entity state refresh automatically
# ZoneStatusSensor.native_value is called at that point
```

### Verified: transition detection idiom (from CONTEXT.md specifics)
```python
was_on = self._zone_was_on.get(zone_id, False)
is_on = self._zone_is_on(zone_id)
if not was_on and is_on:  # OFF → ON
    ...
if was_on and not is_on:  # ON → OFF
    ...
self._zone_was_on[zone_id] = is_on  # MUST be last
```

### Verified: `_turn_valve` domain routing (from coordinator.py line 182-191)
```python
async def _turn_valve(self, zone_id: str, turn_on: bool) -> None:
    domain = zone_id.split(".")[0]
    service = "turn_off" if domain == "switch" else "close_valve"
    await self.hass.services.async_call(
        domain, service, {"entity_id": zone_id}, blocking=True
    )
```
Call site: `await self._turn_valve(zone_id, turn_on=False)` — no additional args needed.

### Verified: `async_create` import (from coordinator.py line 10)
```python
from homeassistant.components.persistent_notification import async_create, async_dismiss
```
Already imported. Use `async_create(self.hass, message, title=..., notification_id=...)` — not the service call pattern.

### Verified: `CoordinatorEntity` listener notification (HA pattern)
```python
# async_update_listeners() is a @callback on DataUpdateCoordinator
# Calls async_write_ha_state() on all registered CoordinatorEntity instances
# Does NOT trigger a new poll
self.coordinator.async_update_listeners()  # call from async_press, no await
```

### Test pattern: verify shutoff fires on leak
```python
async def test_leak_triggers_shutoff(
    hass: HomeAssistant,
    mock_calibrated_config_entry: MockConfigEntry,
    mock_valve_entities: list[str],
) -> None:
    """DETECT-03: valve shutoff called when flow exceeds threshold."""
    await hass.config_entries.async_setup(mock_calibrated_config_entry.entry_id)
    await hass.async_block_till_done()

    # Zone 1 calibrated at 2.0; threshold 1.5x = shutoff at > 3.0 gal/min
    hass.states.async_set(mock_valve_entities[0], "on")
    hass.states.async_set("sensor.flume_current_interval", "4.0")  # > 3.0

    with patch.object(
        mock_calibrated_config_entry.runtime_data,
        "_turn_valve",
        wraps=mock_calibrated_config_entry.runtime_data._turn_valve,
    ) as mock_shutoff:
        coordinator = mock_calibrated_config_entry.runtime_data
        await coordinator.async_refresh()
        await hass.async_block_till_done()
        mock_shutoff.assert_awaited_once_with(mock_valve_entities[0], turn_on=False)

    # Status sensor should show leak_detected
    state = hass.states.get(
        f"sensor.irrigation_monitor_switch_rachio_zone_1_status"
    )
    assert state.state == "leak_detected"
```

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-homeassistant-custom-component |
| Config file | `pytest.ini` or `pyproject.toml` (check project root) |
| Quick run command | `pytest tests/test_leak.py -x -q` |
| Full suite command | `pytest tests/ -x -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DETECT-01 | flow > calibrated × threshold detected | unit | `pytest tests/test_leak.py::test_leak_detection_fires -x` | Wave 0 |
| DETECT-01 | uncalibrated zone skips detection silently | unit | `pytest tests/test_leak.py::test_uncalibrated_zone_no_leak -x` | Wave 0 |
| DETECT-02 | ramp-up skips detection for N polls | unit | `pytest tests/test_leak.py::test_ramp_up_skips_detection -x` | Wave 0 |
| DETECT-02 | OFF→ON resets ramp-up counter | unit | `pytest tests/test_leak.py::test_ramp_up_resets_on_restart -x` | Wave 0 |
| DETECT-03 | shutoff called when shutoff_enabled=True | unit | `pytest tests/test_leak.py::test_leak_triggers_shutoff -x` | Wave 0 |
| DETECT-03 | no shutoff when shutoff_enabled=False | unit | `pytest tests/test_leak.py::test_leak_no_shutoff_when_disabled -x` | Wave 0 |
| DETECT-04 | notification fires on first leak detection | unit | `pytest tests/test_leak.py::test_leak_notification_fires -x` | Wave 0 |
| DETECT-04 | notification fires only once per event (dedup) | unit | `pytest tests/test_leak.py::test_leak_notification_dedup -x` | Wave 0 |
| DETECT-04 | notification clears on OFF→ON, re-fires next event | unit | `pytest tests/test_leak.py::test_leak_notification_clears_on_restart -x` | Wave 0 |
| DETECT-04 | notification content includes zone, flow, expected | unit | `pytest tests/test_leak.py::test_leak_notification_content -x` | Wave 0 |
| DETECT-05 | Flume unavailable → UpdateFailed, no shutoff | unit | (covered by existing `test_flume_unavailable_entities_unavailable`) | ✅ |

### Sampling Rate
- **Per task commit:** `pytest tests/test_leak.py -x -q` (new tests only — fast)
- **Per wave merge:** `pytest tests/ -x -q` (full suite — must stay green)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_leak.py` — 10 new tests covering DETECT-01 through DETECT-04
- [ ] `tests/conftest.py` — add `mock_calibrated_config_entry` fixture

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `SensorStateClass.MEASUREMENT` on text sensors | No `state_class` on text/enum sensors | HA 2022.x | Text sensors must omit `state_class` to avoid statistics errors |
| `async_request_refresh()` for UI updates | `async_update_listeners()` for non-polling state push | HA 2023.x | Avoid unnecessary Flume polls on acknowledge |

**Deprecated/outdated:**
- Do not use `SensorStateClass` on `ZoneStatusSensor` — the values "idle"/"running"/"leak_detected" are not numeric and HA statistics will reject them with a warning.
- Do not use `SensorDeviceClass` on `ZoneStatusSensor` — no HA device class maps to zone status strings.

---

## Open Questions

1. **Does `async_update_listeners()` exist on `DataUpdateCoordinator` in the HA version used by this project?**
   - What we know: It is a standard method on `DataUpdateCoordinator` in HA 2023.x+; the project targets HA 2026.x
   - What's unclear: Exact method signature / availability in test harness
   - Recommendation: Verify by checking `DataUpdateCoordinator` source or using `coordinator.async_request_refresh()` as a safe fallback (slightly heavier but always correct)

2. **Should `_leak_statuses` survive HA restart?**
   - What we know: CONTEXT.md does not mention persistence for leak status; `"leak_detected"` is cleared by user acknowledge
   - What's unclear: If HA restarts while a zone is in "leak_detected" state, should the status restore?
   - Recommendation: Do NOT persist — on restart, all zones start at "idle". This is safe because the physical valve was already shut off (the shutoff is the durable safety action). The user can press acknowledge on next login if needed. Keeping it in-memory avoids Store complexity.

3. **Options flow: does Phase 5 need to add `CONF_RAMP_UP_POLLS` to the options flow UI?**
   - What we know: CONTEXT.md says it's stored in `ConfigEntry.options`; the options flow was implemented in Phase 2
   - What's unclear: Whether Phase 5 should update the options flow to expose a UI field, or just read with `.get()` and default
   - Recommendation: Use `.get(CONF_RAMP_UP_POLLS, DEFAULT_RAMP_UP_POLLS)` without options flow UI in Phase 5. The options flow UI change is a Phase 2.5 concern. Test with the key injected directly into options.

---

## Sources

### Primary (HIGH confidence)
- `coordinator.py` (read directly) — `_async_update_data`, `_turn_valve`, `_calibrating`/`_pending_calibrations` patterns, `async_create` import
- `sensor.py` (read directly) — `CoordinatorEntity` inheritance pattern, `native_value` property, entity ID / unique_id conventions
- `button.py` (read directly) — `async_press` pattern, background task vs synchronous press
- `const.py` (read directly) — all existing constants; namespace for new constants
- `tests/conftest.py` (read directly) — fixture patterns, `MockConfigEntry` structure
- `tests/test_coordinator.py` (read directly) — existing test patterns, how to set zone state and trigger refresh
- `.planning/phases/05-leak-detection/05-CONTEXT.md` (read directly) — locked decisions, code sketch

### Secondary (MEDIUM confidence)
- `.planning/research/PITFALLS.md` — P4 (race condition / ramp-up) and P5 (Flume unavailable) directly applicable
- `.planning/research/ARCHITECTURE.md` — coordinator entity update flow, confirmed `async_write_ha_state` is automatic via CoordinatorEntity

### Tertiary (LOW confidence — from training data, HA 2026.x assumed)
- `DataUpdateCoordinator.async_update_listeners()` availability — training data confirms this method; not verified against HA 2026.x source

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in project, no new installs
- Architecture (coordinator extension): HIGH — read actual source code, patterns mirror Phase 4
- Architecture (ZoneStatusSensor): HIGH — follows DailyUsageSensor/FlowRateSensor pattern exactly
- Architecture (AcknowledgeLeakButtonEntity): HIGH — follows CalibrateButtonEntity pattern
- Pitfalls: HIGH — derived from direct code analysis plus established PITFALLS.md entries
- `async_update_listeners()` method: MEDIUM — well-known HA pattern, confirm against actual HA version

**Research date:** 2026-03-23
**Valid until:** 2026-04-22 (HA 2026.x stable; no fast-moving dependencies)
