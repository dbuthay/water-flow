# Phase 4: Calibration - Research

**Researched:** 2026-03-23
**Domain:** Home Assistant ButtonEntity, async background tasks, persistent notifications, ConfigEntry options update
**Confidence:** HIGH

## Summary

Phase 4 adds a `CalibrateButtonEntity` per monitored zone that triggers a long-running async calibration sequence on the `IrrigationCoordinator`. The sequence involves background-flow checking, valve control via HA service calls, variance-based stabilization detection (polling every 5 seconds for up to 60 seconds), sampling, and writing the result to `ConfigEntry.options`. Re-calibration uses a pending-result dict on the coordinator and fires a persistent notification with action buttons; the event type `mobile_app_notification_action` fires when the user taps Save or Cancel.

The biggest implementation risk is firing-and-forgetting the calibration coroutine correctly from `async_press()`. `entry.async_create_background_task()` is the correct HA-native mechanism: it ties task lifecycle to the config entry (auto-cancelled on unload), is transparent to `async_block_till_done` in tests (does NOT block test waits), and is the pattern HA's own docs recommend over raw `asyncio.create_task`. Tests must use `hass.services.async_call("button", "press", {"entity_id": ...}, blocking=True)` then advance `asyncio` manually to exercise the background coroutine.

Persistent notification action buttons fire `mobile_app_notification_action` events (NOT a special persistent_notification event). The action identifier in the event data must exactly match what was sent in the notification's `actions` list. HA's `persistent_notification.async_create` / `async_dismiss` functions in `homeassistant.components.persistent_notification` are the correct programmatic API — do not call the service layer from coordinator code.

**Primary recommendation:** Implement the calibration sequence as `async def async_calibrate_zone(self, zone_id: str)` on `IrrigationCoordinator`; fire it from `CalibrateButtonEntity.async_press()` using `self._entry.async_create_background_task(hass, coro, name="calibrate_zone")`.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- ButtonEntity per zone triggers async calibration sequence on coordinator
- Calibration sequence: background check → already-running guard → turn valve on → variance detection (5s intervals, std_dev < 0.05, 60s timeout) → sample 3 readings over 15s → save/notify
- Re-calibration: store pending result in coordinator memory, fire persistent notification with HA action buttons (Save/Cancel)
- Background threshold: configurable, default 0.1 gal/min, stored as CONF_BACKGROUND_THRESHOLD
- Failure: notification + turn valve off
- Options merge: `existing = dict(entry.options); existing["zones"][zone_id]["calibrated_flow"] = val; async_update_entry(entry, options=existing)`
- PLATFORMS needs "button" added
- New const keys: `CONF_BACKGROUND_THRESHOLD = "background_flow_threshold"`, `DEFAULT_BACKGROUND_THRESHOLD = 0.1`, `CONF_PENDING_CALIBRATION = "pending_calibration"`
- Valve control: switch domain → `switch.turn_on`/`switch.turn_off`; valve domain → `valve.open_valve`/`valve.close_valve`
- Calibration steps: (1) background check, (2) already-running guard, (3) fire "Calibrating..." notification, (4) turn valve on, (5) variance detection loop, (6) sample 3 readings, (7) first vs re-cal branch, (8) turn valve off

### Claude's Discretion
- Exact persistent notification IDs (for dismissal/replacement)
- HA event names for action buttons
- Whether `background_flow_threshold` is added to options flow in this phase or left for a follow-up
- Variance detection threshold value (std_dev < 0.05 recommended by research)

### Deferred Ideas (OUT OF SCOPE)
- Adding `background_flow_threshold` to the options flow UI — could be done in this phase or as a follow-up. If deferred, hard-code reading from `ConfigEntry.data` or fall back to `DEFAULT_BACKGROUND_THRESHOLD`.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CALIB-01 | User can trigger calibration for a monitored zone via a button entity in the HA UI | ButtonEntity + async_setup_entry pattern; one entity per zone_id |
| CALIB-02 | Integration checks for background water flow before starting calibration and warns the user if flow is detected above a minimum threshold | Read Flume sensor state before starting; compare to CONF_BACKGROUND_THRESHOLD; fire persistent notification and abort if exceeded |
| CALIB-03 | Integration aborts calibration if the target zone is already running | Reuse existing `coordinator._zone_is_on(zone_id)`; abort with notification if True |
| CALIB-04 | Integration turns on the valve, waits for flow to stabilize (variance detection), then samples Flume flow to compute a reliable average | `hass.services.async_call` for valve control; `asyncio.sleep(5)` in loop; statistics.stdev on last 3 readings; 60s timeout guard |
| CALIB-05 | Calibrated flow rate is stored persistently and survives HA restarts | Options merge pattern via `hass.config_entries.async_update_entry(entry, options=merged)`; stored in `ConfigEntry.options["zones"][zone_id]["calibrated_flow"]` |
| CALIB-06 | Integration turns the valve back off after calibration completes and notifies the user of the recorded flow rate | Always call valve close service in finally block; fire persistent notification for success or failure |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `homeassistant.components.button` | bundled with HA | ButtonEntity base class | Standard HA entity type for triggering one-shot actions |
| `homeassistant.helpers.update_coordinator` | bundled | CoordinatorEntity base | Coordinator pattern established in Phase 3; button follows same pattern |
| `homeassistant.components.persistent_notification` | bundled | In-progress, success, failure, re-cal notifications | Correct programmatic API (not service layer) for integration code |
| `asyncio` stdlib | Python 3.13 | `asyncio.sleep()` for polling delays | HA event loop compatible; avoids blocking |
| `statistics` stdlib | Python 3.13 | `statistics.stdev()` for variance detection | No extra dependency; 3-sample stdev sufficient |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `homeassistant.core.callback` | bundled | Synchronous event listener decorator | Required when registering `hass.bus.async_listen` handlers called from sync context |
| `homeassistant.helpers.event.async_call_later` | bundled | Scheduled future callback | Not needed here — `asyncio.sleep()` inside background task is simpler for sequential delays |

**Installation:** No new dependencies. All APIs are bundled with HA.

---

## Architecture Patterns

### Recommended File Structure
```
custom_components/irrigation_monitor/
├── __init__.py          # PLATFORMS += ["button"] — add "button" here
├── button.py            # NEW: CalibrateButtonEntity + async_setup_entry
├── coordinator.py       # ADD: async_calibrate_zone(), _pending_calibrations dict
├── const.py             # ADD: CONF_BACKGROUND_THRESHOLD, DEFAULT_BACKGROUND_THRESHOLD
├── sensor.py            # unchanged
└── config_flow.py       # unchanged (options merge pattern already correct)
```

### Pattern 1: ButtonEntity + CoordinatorEntity Combination

**What:** `CalibrateButtonEntity` inherits from both `CoordinatorEntity[IrrigationCoordinator]` and `ButtonEntity`. The coordinator reference gives access to `self.coordinator.hass`, `self.coordinator._entry`, and the calibration method.

**When to use:** Standard HA pattern when a button entity needs coordinator data (e.g., to read zone config before pressing).

```python
# Source: HA ButtonEntity base class + CoordinatorEntity pattern from sensor.py
from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

class CalibrateButtonEntity(CoordinatorEntity[IrrigationCoordinator], ButtonEntity):
    """Button that triggers calibration for one zone."""

    _attr_has_entity_name = True
    _attr_should_poll = False  # ButtonEntity default; explicit for clarity

    def __init__(
        self,
        coordinator: IrrigationCoordinator,
        entry: ConfigEntry,
        zone_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._entry = entry
        zone_slug = zone_id.replace(".", "_")
        self._attr_unique_id = f"{entry.entry_id}_{zone_id}_calibrate"
        self._attr_name = f"{DOMAIN} {zone_slug} calibrate"
        self.entity_id = f"button.{DOMAIN}_{zone_slug}_calibrate"

    async def async_press(self) -> None:
        """Fire calibration as a background task — never block async_press."""
        self._entry.async_create_background_task(
            self.hass,
            self.coordinator.async_calibrate_zone(self._zone_id),
            name=f"calibrate_{self._zone_id}",
        )
```

**Critical note:** `async_press()` MUST return immediately. The calibration loop takes up to 90s. Fire it as a background task, never `await` it directly.

### Pattern 2: Background Task from async_press

**What:** Use `entry.async_create_background_task(hass, coro, name)` — NOT `asyncio.create_task()` or `hass.async_create_task()`.

**Why `entry.async_create_background_task` is correct:**
- Task is auto-cancelled when the config entry is unloaded (prevents dangling coroutines on reload)
- Task does NOT block `async_block_till_done()` in tests — required for test controllability
- Task is tracked in `entry._background_tasks` for lifecycle management
- Signature (from installed HA source): `entry.async_create_background_task(hass, target: Coroutine, name: str, eager_start: bool = True) -> asyncio.Task`

**Why NOT `asyncio.create_task()`:**
- Not tied to entry lifecycle — leaks on entry unload
- No name scoping

```python
# CORRECT — from async_press:
self._entry.async_create_background_task(
    self.hass,
    self.coordinator.async_calibrate_zone(self._zone_id),
    name=f"calibrate_{self._zone_id}",
)

# WRONG — blocks async_press for up to 90s:
await self.coordinator.async_calibrate_zone(self._zone_id)

# WRONG — not tied to entry lifecycle:
asyncio.create_task(self.coordinator.async_calibrate_zone(self._zone_id))
```

### Pattern 3: Calibration Sequence on Coordinator

**What:** `async_calibrate_zone` is an `async def` method on `IrrigationCoordinator`. It has direct access to `self.hass`, `self._entry`, and `self._zone_is_on()`.

```python
# Source: pattern derived from coordinator.py + HA service call conventions
import statistics
import asyncio

async def async_calibrate_zone(self, zone_id: str) -> None:
    """Full calibration sequence for one zone."""
    # --- Guard: already calibrating ---
    if zone_id in self._pending_calibrations:
        return  # silently skip duplicate presses

    # --- CALIB-02: Background flow check ---
    threshold = self._entry.data.get(
        CONF_BACKGROUND_THRESHOLD, DEFAULT_BACKGROUND_THRESHOLD
    )
    flume_id = self._entry.data[CONF_FLUME_ENTITY_ID]
    state = self.hass.states.get(flume_id)
    if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
        async_create(self.hass,
            "Calibration failed: Flume sensor unavailable.",
            title="Irrigation Monitor",
            notification_id=f"calib_{zone_id}_fail",
        )
        return
    current_flow = float(state.state)
    if current_flow > threshold:
        async_create(self.hass,
            f"Background water flow detected ({current_flow:.1f} gal/min). "
            "Stop all other water use before calibrating.",
            title="Irrigation Monitor",
            notification_id=f"calib_{zone_id}_background",
        )
        return

    # --- CALIB-03: Zone already running guard ---
    if self._zone_is_on(zone_id):
        async_create(self.hass,
            f"Zone {zone_id} is already running. Stop it first.",
            title="Irrigation Monitor",
            notification_id=f"calib_{zone_id}_running",
        )
        return

    # --- CALIB-04: Start calibration ---
    async_create(self.hass,
        f"Calibrating {zone_id}… please wait.",
        title="Irrigation Monitor",
        notification_id=f"calib_{zone_id}_progress",
    )
    domain = zone_id.split(".")[0]
    on_service = "turn_on" if domain == "switch" else "open_valve"
    off_service = "turn_off" if domain == "switch" else "close_valve"

    try:
        await self.hass.services.async_call(
            domain, on_service, {"entity_id": zone_id}, blocking=True
        )

        # Variance detection loop (max 60s, poll every 5s)
        readings: list[float] = []
        elapsed = 0
        stable = False
        while elapsed < 60:
            await asyncio.sleep(5)
            elapsed += 5
            s = self.hass.states.get(flume_id)
            if s is None or s.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                raise RuntimeError("Flume went unavailable during calibration")
            readings.append(float(s.state))
            if len(readings) >= 3:
                if statistics.stdev(readings[-3:]) < 0.05:
                    stable = True
                    break

        if not stable:
            raise RuntimeError("Flow did not stabilize within 60 seconds")

        # Sample 3 readings over 15s
        samples: list[float] = []
        for _ in range(3):
            await asyncio.sleep(5)
            s = self.hass.states.get(flume_id)
            if s is None or s.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                raise RuntimeError("Flume went unavailable during sampling")
            samples.append(float(s.state))
        new_flow = sum(samples) / len(samples)

        # CALIB-05: Persist or pending
        zones_cfg = self._entry.options.get(CONF_ZONES, {})
        old_flow = zones_cfg.get(zone_id, {}).get(CONF_CALIBRATED_FLOW)

        if old_flow is not None:
            # Re-calibration: store pending, fire action notification
            self._pending_calibrations[zone_id] = new_flow
            self._register_calibration_action_listener(zone_id, old_flow, new_flow)
            async_dismiss(self.hass, f"calib_{zone_id}_progress")
            async_create(self.hass,
                f"Zone {zone_id} recalibration complete.\n"
                f"Old: {old_flow:.1f} gal/min → New: {new_flow:.1f} gal/min.\n"
                "Save or Cancel?",
                title="Irrigation Monitor",
                notification_id=f"calib_{zone_id}_confirm",
                # actions are set via service — see Pattern 4
            )
        else:
            # First calibration: write immediately
            self._write_calibrated_flow(zone_id, new_flow)
            async_dismiss(self.hass, f"calib_{zone_id}_progress")
            async_create(self.hass,
                f"Zone {zone_id} calibrated: {new_flow:.1f} gal/min",
                title="Irrigation Monitor",
                notification_id=f"calib_{zone_id}_success",
            )

    except Exception as err:
        async_dismiss(self.hass, f"calib_{zone_id}_progress")
        async_create(self.hass,
            f"Calibration failed for {zone_id}: {err}",
            title="Irrigation Monitor",
            notification_id=f"calib_{zone_id}_fail",
        )
        _LOGGER.exception("Calibration error for %s", zone_id)
    finally:
        # CALIB-06: Always turn valve off
        await self.hass.services.async_call(
            domain, off_service, {"entity_id": zone_id}, blocking=True
        )
```

### Pattern 4: Persistent Notification Action Buttons (Re-calibration)

**What:** HA's persistent notification service supports an `actions` list (introduced HA 2023.4). When the user taps an action button, HA fires a `mobile_app_notification_action` event on the event bus.

**Event type:** `"mobile_app_notification_action"` (confirmed from companion.home-assistant.io docs)

**Event data structure:**
```python
{
    "action": "ACTION_IDENTIFIER",   # string — matches what was sent in actions list
    "reply_text": "...",             # only present for text-reply actions
    "tag": "...",                    # Android: notification tag
    "action_data": {...},            # iOS: additional custom data
}
```

**Sending the notification with actions via service call:**
```python
# NOTE: The programmatic async_create() API does NOT support actions.
# Must use the service layer with actions parameter.
await self.hass.services.async_call(
    "persistent_notification",
    "create",
    {
        "message": f"Zone {zone_id} recalibration complete.\n"
                   f"Old: {old_flow:.1f} → New: {new_flow:.1f} gal/min.\nSave or Cancel?",
        "title": "Irrigation Monitor",
        "notification_id": f"calib_{zone_id}_confirm",
        "actions": [
            {
                "action": f"irrigation_monitor_confirm_calibration_{zone_id_slug}",
                "title": "Save",
            },
            {
                "action": f"irrigation_monitor_cancel_calibration_{zone_id_slug}",
                "title": "Cancel",
            },
        ],
    },
)
```

**Listening for action response:**
```python
def _register_calibration_action_listener(
    self, zone_id: str, old_flow: float, new_flow: float
) -> None:
    """Register a one-time event listener for Save/Cancel action buttons."""
    zone_slug = zone_id.replace(".", "_")
    save_action = f"irrigation_monitor_confirm_calibration_{zone_slug}"
    cancel_action = f"irrigation_monitor_cancel_calibration_{zone_slug}"

    @callback
    def _handle_action(event: Event) -> None:
        action = event.data.get("action")
        if action == save_action:
            self._write_calibrated_flow(zone_id, new_flow)
            async_dismiss(self.hass, f"calib_{zone_id}_confirm")
            async_create(self.hass,
                f"Zone {zone_id} calibration saved: {new_flow:.1f} gal/min",
                title="Irrigation Monitor",
                notification_id=f"calib_{zone_id}_saved",
            )
        elif action == cancel_action:
            self._pending_calibrations.pop(zone_id, None)
            async_dismiss(self.hass, f"calib_{zone_id}_confirm")
        else:
            return  # Not our action — do not unsubscribe
        unsub()  # One-shot: remove listener after handling

    unsub = self.hass.bus.async_listen(
        "mobile_app_notification_action", _handle_action
    )
    # Ensure listener is cleaned up if entry is unloaded before user responds
    self._entry.async_on_unload(unsub)
```

**CAUTION:** The `actions` list in persistent notifications requires HA Companion app (iOS or Android). In a desktop browser or HA frontend, action buttons are NOT rendered — the notification appears without buttons. This is a known HA limitation. The in-memory pending state will be discarded on HA restart if the user never responds.

### Pattern 5: ConfigEntry Options Write

**What:** Write `calibrated_flow` to `ConfigEntry.options` using the established merge pattern.

```python
def _write_calibrated_flow(self, zone_id: str, flow: float) -> None:
    """Persist calibrated flow to ConfigEntry.options using safe merge pattern."""
    existing = dict(self._entry.options)
    # Shallow-copy the zones dict to avoid mutating MappingProxyType in-place
    zones = dict(existing.get(CONF_ZONES, {}))
    zone_cfg = dict(zones.get(zone_id, {}))
    zone_cfg[CONF_CALIBRATED_FLOW] = flow
    zones[zone_id] = zone_cfg
    existing[CONF_ZONES] = zones
    self.hass.config_entries.async_update_entry(self._entry, options=existing)
```

**Key:** `ConfigEntry.options` is a `MappingProxyType` (immutable). `dict(entry.options)` creates a shallow copy that is mutable, but nested dicts are still shared references. Must explicitly copy each nested level before mutating.

**`async_update_entry` signature** (from installed HA source):
```python
hass.config_entries.async_update_entry(
    entry: ConfigEntry,
    *,
    data: Mapping | UNDEFINED = UNDEFINED,
    options: Mapping | UNDEFINED = UNDEFINED,
    # ... other fields: title, unique_id, version, etc.
) -> bool  # True if entry actually changed
```

Passing only `options=...` leaves `data` unchanged.

### Pattern 6: async_setup_entry for button.py

```python
# Source: sensor.py async_setup_entry pattern adapted for buttons
async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up calibrate button entities per monitored zone."""
    coordinator: IrrigationCoordinator = entry.runtime_data
    monitored: list[str] = entry.data[CONF_MONITORED_ZONES]
    async_add_entities([
        CalibrateButtonEntity(coordinator, entry, zone_id)
        for zone_id in monitored
    ])
```

### Anti-Patterns to Avoid

- **`await self.coordinator.async_calibrate_zone(...)` directly in `async_press()`**: Blocks the HA event loop for 75-90 seconds. Use `entry.async_create_background_task()`.
- **`asyncio.create_task()` instead of `entry.async_create_background_task()`**: Task not cancelled on entry unload; leaks after integration reload.
- **Calling `persistent_notification.create` service to pass `actions`**: Correct for action buttons. However, `async_create()` from the module API does NOT support `actions` — the programmatic function signature has no `actions` param. Must go through service call layer for action buttons.
- **Mutating `entry.options` in-place**: It is a `MappingProxyType`. Always `dict(entry.options)` then copy nested levels before mutation.
- **Using `time.sleep()` in the polling loop**: Blocks the event loop. Always `await asyncio.sleep(5)`.
- **Forgetting to close the valve in the failure path**: The `finally:` block ensures valve is always turned off regardless of success or failure.
- **Setting zone_id (contains dots) directly in entity_id string**: `entity_id` and notification IDs must be slug-safe. Replace `.` with `_` for entity IDs. For notification IDs and event action names, also replace `.` with `_`.
- **Listening for `persistent_notification_action` or `notification_action`**: Wrong. The correct event type is `"mobile_app_notification_action"`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Variance calculation | Custom rolling stdev | `statistics.stdev(readings[-3:])` | stdlib; 3-element list is fast |
| Background task lifecycle | Manual task dict + cleanup | `entry.async_create_background_task()` | Auto-cancelled on unload; HA managed |
| Event listener cleanup | Manual unsub tracking | `entry.async_on_unload(unsub)` | Guarantees cleanup on entry unload |
| Options persistence | Custom JSON/Store | `hass.config_entries.async_update_entry(entry, options=...)` | Persists to `.storage/core.config_entries` automatically |
| Notification creation | `hass.services.async_call("persistent_notification", "create", ...)` for non-action notifications | `from homeassistant.components.persistent_notification import async_create, async_dismiss` | Cleaner, no service overhead for simple notifications |

**Key insight:** Re-calibration state is pure in-memory. `coordinator._pending_calibrations: dict[str, float]` is the entire state store. It intentionally expires on HA restart — no persistence needed.

---

## Common Pitfalls

### Pitfall 1: Blocking async_press with the 90-second calibration coroutine

**What goes wrong:** If `async_press()` `await`s the calibration coroutine directly, it holds the HA event loop for the full calibration duration. All other HA tasks (polling, automations, UI updates) freeze. HA may log `Detected blocking call` or timeout the service call.

**Why it happens:** `async_press()` is called by HA's button press service handler. HA awaits it. If it takes 90 seconds, the service call blocks.

**How to avoid:** Always fire the coroutine as a background task from `async_press()`:
```python
async def async_press(self) -> None:
    self._entry.async_create_background_task(
        self.hass,
        self.coordinator.async_calibrate_zone(self._zone_id),
        name=f"calibrate_{self._zone_id}",
    )
    # returns immediately
```

**Warning signs:** Tests hang at `await hass.async_block_till_done()`. HA logs show blocking operations.

### Pitfall 2: MappingProxyType shallow copy trap

**What goes wrong:** `existing = dict(entry.options)` copies the top-level dict, but `existing["zones"]` is still the same `MappingProxyType` object. Doing `existing["zones"][zone_id]["calibrated_flow"] = val` raises `TypeError: 'mappingproxy' object does not support item assignment`.

**Why it happens:** `ConfigEntry.options` is a `MappingProxyType`. `dict()` only creates a shallow copy. Nested values are still proxy objects.

**How to avoid:**
```python
existing = dict(self._entry.options)
zones = dict(existing.get(CONF_ZONES, {}))       # copy zones level
zone_cfg = dict(zones.get(zone_id, {}))           # copy individual zone
zone_cfg[CONF_CALIBRATED_FLOW] = flow
zones[zone_id] = zone_cfg
existing[CONF_ZONES] = zones
hass.config_entries.async_update_entry(self._entry, options=existing)
```

**Warning signs:** `TypeError: 'mappingproxy' object does not support item assignment` at runtime.

### Pitfall 3: action buttons not visible in HA frontend

**What goes wrong:** The re-calibration notification appears without Save/Cancel buttons in the HA web frontend. Users cannot save or cancel.

**Why it happens:** Persistent notification `actions` are a mobile app feature. They render only in iOS/Android Companion apps, not in the HA web UI.

**How to avoid (research finding):** This is a known HA limitation. Mitigations:
1. Document in UI that re-calibration confirmation requires HA Companion app, OR
2. Provide an alternative: a separate "confirm last calibration" button entity per zone that reads from `_pending_calibrations`, OR
3. Accept it — the pending result expires harmlessly on restart.

**Decision for planner:** The CONTEXT.md locks the notification-with-action approach. Flag this limitation in the implementation notes. Recommend Option 2 (confirm button) as a follow-up.

**Warning signs:** Users report notification appears but no buttons to tap.

### Pitfall 4: Duplicate calibration runs

**What goes wrong:** User presses the calibrate button twice quickly. Two concurrent calibration coroutines run for the same zone, interfering with each other.

**How to avoid:** Check `zone_id in self._pending_calibrations` at the start of `async_calibrate_zone` and early-return. Alternatively, use a separate `_calibrating: set[str]` guard set that is added to at start and removed in `finally`.

**Warning signs:** Two concurrent notifications for the same zone.

### Pitfall 5: zone_id contains dots — must slug for entity IDs and notification IDs

**What goes wrong:** zone_id values are HA entity IDs like `switch.rachio_zone_1`. Using them directly in `f"button.{zone_id}_calibrate"` creates `button.switch.rachio_zone_1_calibrate` which HA rejects (double-dot in domain position).

**How to avoid:** Always `zone_slug = zone_id.replace(".", "_")` for entity_id, notification_id, and event action name construction. The `unique_id` field does not have this restriction.

**Warning signs:** HA logs `Invalid entity ID: button.switch.rachio_zone_1_calibrate`.

### Pitfall 6: `async_update_entry` must be called from the event loop thread

**What goes wrong:** If called from a thread-pool executor or from outside the event loop, HA raises a thread-safety error.

**How to avoid:** The calibration coroutine is already in the event loop. `async_update_entry` is a `@callback` (synchronous but must be called from the loop thread). Calling it from within an `async def` function is correct — no `await` needed.

```python
# Correct — synchronous callback called from async context
self.hass.config_entries.async_update_entry(self._entry, options=existing)

# Wrong — DO NOT await it
await self.hass.config_entries.async_update_entry(...)  # TypeError
```

---

## Code Examples

### Persistent Notification Imports

```python
# Source: homeassistant/components/persistent_notification/__init__.py
from homeassistant.components.persistent_notification import (
    async_create,
    async_dismiss,
)

# Usage:
async_create(hass, message="...", title="...", notification_id="my_notif_id")
async_dismiss(hass, notification_id="my_notif_id")
```

### Event Bus Listener Registration

```python
# Source: HA event bus pattern + companion docs event type
from homeassistant.core import Event, callback

@callback
def _handle_action(event: Event) -> None:
    action = event.data.get("action")
    if action == "my_action_id":
        # handle it
        unsub()  # one-shot

unsub = self.hass.bus.async_listen("mobile_app_notification_action", _handle_action)
self._entry.async_on_unload(unsub)  # cleanup if entry unloaded before user responds
```

### PLATFORMS Extension in __init__.py

```python
# BEFORE (Phase 3):
PLATFORMS: list[str] = ["sensor"]

# AFTER (Phase 4):
PLATFORMS: list[str] = ["sensor", "button"]
```

### Testing Button Press (pytest-homeassistant-custom-component)

```python
# Source: HA test conventions for ButtonEntity
# Option A: Direct entity method call
button_entity = ...  # get from platform
await button_entity.async_press()
# Then advance event loop to let background task start:
await hass.async_block_till_done()

# Option B: Via service call (more realistic)
await hass.services.async_call(
    "button",
    "press",
    {"entity_id": "button.irrigation_monitor_switch_rachio_zone_1_calibrate"},
    blocking=True,
)
await hass.async_block_till_done()
```

**Note on testing background tasks:** `entry.async_create_background_task()` creates tasks that do NOT block `async_block_till_done()`. To test the calibration sequence, you must advance the event loop manually after each `asyncio.sleep()` call inside the coroutine. Use `async_fire_time_changed` or patch `asyncio.sleep` to avoid real waits in tests.

Recommended test strategy:
```python
with patch("asyncio.sleep", return_value=None):
    # Now asyncio.sleep() returns instantly, calibration runs to completion
    # Must also mock Flume state changes between sleep calls
    pass
```

### Calibration In-Progress Guard (coordinator __init__ extension)

```python
# Add to IrrigationCoordinator.__init__:
self._pending_calibrations: dict[str, float] = {}
# key = zone_id, value = pending new flow rate (awaiting user confirm)

self._calibrating: set[str] = set()
# zones currently running the calibration loop
```

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-homeassistant-custom-component |
| Config file | `pytest.ini` or `pyproject.toml` (detect at project root) |
| Quick run command | `.venv/bin/pytest tests/test_button.py -x` |
| Full suite command | `.venv/bin/pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CALIB-01 | Button entities created per monitored zone | unit | `.venv/bin/pytest tests/test_button.py::test_button_entities_created -x` | ❌ Wave 0 |
| CALIB-02 | Background flow check aborts and notifies when flow > threshold | unit | `.venv/bin/pytest tests/test_button.py::test_calibrate_aborts_on_background_flow -x` | ❌ Wave 0 |
| CALIB-03 | Already-running guard aborts and notifies | unit | `.venv/bin/pytest tests/test_button.py::test_calibrate_aborts_when_zone_running -x` | ❌ Wave 0 |
| CALIB-04 | Full calibration sequence: valve on, stabilize, sample, compute average | unit | `.venv/bin/pytest tests/test_button.py::test_calibration_full_sequence -x` | ❌ Wave 0 |
| CALIB-04 | Stabilization timeout fires failure notification | unit | `.venv/bin/pytest tests/test_button.py::test_calibration_stabilization_timeout -x` | ❌ Wave 0 |
| CALIB-04 | Flume going unavailable mid-calibration fires failure | unit | `.venv/bin/pytest tests/test_button.py::test_calibration_flume_unavailable_mid_run -x` | ❌ Wave 0 |
| CALIB-05 | calibrated_flow saved to ConfigEntry.options on first calibration | unit | `.venv/bin/pytest tests/test_button.py::test_calibration_saves_to_options -x` | ❌ Wave 0 |
| CALIB-05 | Re-calibration stores pending and fires confirm notification | unit | `.venv/bin/pytest tests/test_button.py::test_recalibration_pending_flow -x` | ❌ Wave 0 |
| CALIB-05 | Save action writes new calibrated_flow, Cancel discards | unit | `.venv/bin/pytest tests/test_button.py::test_recalibration_save_action -x` | ❌ Wave 0 |
| CALIB-06 | Valve always turned off after success | unit | `.venv/bin/pytest tests/test_button.py::test_calibration_turns_valve_off_on_success -x` | ❌ Wave 0 |
| CALIB-06 | Valve always turned off after failure | unit | `.venv/bin/pytest tests/test_button.py::test_calibration_turns_valve_off_on_failure -x` | ❌ Wave 0 |
| CALIB-06 | Success notification fired after first calibration | unit | `.venv/bin/pytest tests/test_button.py::test_calibration_success_notification -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `.venv/bin/pytest tests/test_button.py -x`
- **Per wave merge:** `.venv/bin/pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_button.py` — all CALIB-01 through CALIB-06 test stubs
- [ ] No new conftest fixtures required — existing `mock_config_entry`, `mock_flume_entity`, `mock_valve_entities` cover all needed state
- [ ] No framework install needed — pytest-homeassistant-custom-component already installed

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `hass.async_create_task()` for integration background work | `entry.async_create_background_task()` | HA ~2023.x | Tasks tied to entry lifecycle; auto-cancelled on unload |
| `OptionsFlowWithConfigEntry` | `OptionsFlow` (config_entry injected automatically) | HA 2024.x | Simpler class; `self.config_entry` available without inheritance |
| `async_add_entities` type hint as `AddEntitiesCallback` | `AddConfigEntryEntitiesCallback` | HA 2024.x | Stronger type; already used in sensor.py |

---

## Open Questions

1. **Persistent notification action buttons in HA frontend**
   - What we know: `actions` list renders in iOS/Android Companion app only
   - What's unclear: Whether HA 2024/2025 added frontend support for notification action buttons
   - Recommendation: Implement as specified in CONTEXT.md. Add a comment in button.py noting the Companion-app limitation. Consider adding a `ConfirmCalibrationButtonEntity` as a follow-up (Phase 4.5 or add to discretion items).

2. **`background_flow_threshold` options flow placement**
   - What we know: CONTEXT.md marks this as discretion — either add to options flow in this phase or fall back to DEFAULT
   - What's unclear: Whether users will find the default (0.1 gal/min) adequate
   - Recommendation: Defer options flow UI to a follow-up (Phase 2 retroactive or standalone). This phase reads from `entry.data.get(CONF_BACKGROUND_THRESHOLD, DEFAULT_BACKGROUND_THRESHOLD)`. The constant is added to `const.py` now.

3. **Duplicate press guard mechanism**
   - What we know: Two quick presses would launch two concurrent calibrations per zone
   - What's unclear: Whether to use `_pending_calibrations` dict as the guard or a separate `_calibrating: set[str]`
   - Recommendation: Use `_calibrating: set[str]` as the active guard (add at loop start, remove in finally). `_pending_calibrations` is for the re-calibration pending-save state. Keeps semantics clean.

---

## Sources

### Primary (HIGH confidence)
- Installed HA source at `.venv/lib/python3.13/site-packages/homeassistant/` — `core.py` lines 755-830 (async_create_task, async_create_background_task), `config_entries.py` lines 1315-1365 (ConfigEntry.async_create_background_task), `config_entries.py` lines 2357-2407 (ConfigEntries.async_update_entry signature)
- `custom_components/irrigation_monitor/coordinator.py` — `_zone_is_on()`, coordinator init patterns, entry unload registration
- `custom_components/irrigation_monitor/sensor.py` — CoordinatorEntity + SensorEntity combination pattern; entity_id slug construction
- `custom_components/irrigation_monitor/config_flow.py` lines 220-264 — options merge pattern with MappingProxyType copy
- `tests/conftest.py` — available fixtures: `mock_flume_entity`, `mock_valve_entities`, `mock_config_entry`

### Secondary (MEDIUM confidence)
- companion.home-assistant.io notification actions docs — event type `"mobile_app_notification_action"`, event data structure `{"action": "ACTION_ID", "reply_text": ..., "tag": ..., "action_data": ...}`
- HA GitHub `components/button/__init__.py` fetched response — `_attr_should_poll = False`, `async_press()` signature, `ButtonDeviceClass` values
- HA GitHub `components/persistent_notification/__init__.py` fetched response — `async_create(hass, message, title, notification_id)` and `async_dismiss(hass, notification_id)` signatures

### Tertiary (LOW confidence — flag for validation)
- Claim that `persistent_notification` programmatic `async_create()` does NOT support `actions` parameter — inferred from fetched source showing no `actions` param in `Notification` dataclass; use service call for action buttons. Validate before implementing.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are bundled HA; verified from installed source
- ButtonEntity API: HIGH — verified from installed HA source + demo pattern
- Background task pattern: HIGH — verified from installed `config_entries.py` + `core.py`
- Options merge pattern: HIGH — already working in Phase 2 `config_flow.py`
- Persistent notification actions event type: MEDIUM — from companion docs; cannot verify `actions` param support in programmatic API without reading full source
- Test patterns: HIGH — established patterns from existing tests in `tests/test_coordinator.py`

**Research date:** 2026-03-23
**Valid until:** 2026-09-23 (stable HA APIs; re-verify ButtonEntity if HA version changes significantly)
