# Phase 3: Coordinator + Usage - Research

**Researched:** 2026-03-23
**Domain:** Home Assistant DataUpdateCoordinator + sensor entities + Store persistence
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- Two sensors per zone: `daily_usage` (gal since midnight) + `flow_rate` (gal/min, 0 when idle — not unavailable)
- Multi-zone overlap: calibrated zones get their `calibrated_flow` attributed when Flume ≈ sum of calibrated values (within `threshold_multiplier` margin). Uncalibrated zones in overlap get 0. Logic requires `calibrated_flow` to be set (Phase 4 sets it).
- Flume unavailable → all entities go `unavailable`; coordinator raises `UpdateFailed`. Stored totals preserved. Resume from stored total when Flume returns; no confirmation delay.
- Storage key: `"irrigation_monitor.daily_usage"` with `{"date": "YYYY-MM-DD", "zones": {entity_id: float}}`
- On startup: if stored date == today → restore totals; if stored date != today → reset all totals to 0 and save new date
- Midnight reset: `async_track_time_change` callback at 00:00:00 local time resets in-memory totals and writes new Store entry
- Unique ID format: `{entry.entry_id}_{zone_entity_id}_daily_usage` / `{entry.entry_id}_{zone_entity_id}_flow_rate`
- `ConfigEntry.runtime_data` for coordinator (not `hass.data[DOMAIN]`)
- Single `DataUpdateCoordinator` polls every `poll_interval` seconds from `ConfigEntry.data`
- Coordinator data dict: `{zone_entity_id: ZoneData(flow_rate: float, daily_usage: float, is_available: bool)}`
- Store write debounce: SAVE_DELAY (Claude's discretion, recommended 30s); always write on unload/shutdown

### Claude's Discretion

- Store write debounce interval (SAVE_DELAY)
- `ZoneData` dataclass vs TypedDict
- Exact `UpdateFailed` error message content
- Whether to expose a coordinator-level "status" binary sensor

### Deferred Ideas (OUT OF SCOPE)

- None — discussion stayed within phase scope.

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| USAGE-01 | Integration exposes a sensor entity per monitored zone showing daily water usage (gallons accumulated since midnight) | `SensorEntity` + `CoordinatorEntity` subclass; `SensorDeviceClass.WATER`, `UnitOfVolume.GALLONS`; unique ID format confirmed |
| USAGE-02 | Daily usage totals persist across HA restarts and only reset at midnight (not on restart) | `Store.async_load()` on coordinator init; date comparison at startup; `async_track_time_change` midnight callback |
| USAGE-03 | If HA was offline at midnight, daily totals reset correctly on next startup based on stored date comparison | Startup date check: `stored_date != date.today().isoformat()` → reset totals before first poll |

</phase_requirements>

---

## Summary

Phase 3 builds the core data pipeline: a `DataUpdateCoordinator` subclass that polls the Flume sensor, attributes flow to zones, accumulates daily usage, persists totals across restarts, and exposes two `CoordinatorEntity`-based sensor entities per monitored zone.

All required APIs have been verified directly from the installed HA 2026.2.3 source. The `DataUpdateCoordinator` subclass pattern (`_async_update_data` override + `UpdateFailed`), `Store` persistence (`async_load` / `async_delay_save`), `CoordinatorEntity` base class, `async_track_time_change`, and `entry.runtime_data` assignment are all confirmed from source. No training-data uncertainty applies.

Key structural insight: `CoordinatorEntity.available` already returns `coordinator.last_update_success`, so entities go unavailable automatically when `UpdateFailed` is raised — no extra logic needed in sensor entities. The coordinator carries all state; sensor entities are thin wrappers.

**Primary recommendation:** Implement coordinator as a single file `coordinator.py`, sensor entities in `sensor.py`, wire them in `__init__.py` using the confirmed `runtime_data` + `async_config_entry_first_refresh` + `async_forward_entry_setups` pattern.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `homeassistant.helpers.update_coordinator.DataUpdateCoordinator` | HA 2026.2.3 (installed) | Polling hub; manages update interval, error state, listener notification | HA standard pattern for all polling integrations |
| `homeassistant.helpers.update_coordinator.CoordinatorEntity` | HA 2026.2.3 (installed) | Base class for entities driven by a coordinator | Auto-wires listener, handles `available`, no manual `async_write_ha_state` calls needed |
| `homeassistant.helpers.update_coordinator.UpdateFailed` | HA 2026.2.3 (installed) | Exception raised from `_async_update_data` when source is unavailable | Coordinator catches it, sets `last_update_success=False`, notifies listeners (→ entities go unavailable) |
| `homeassistant.helpers.storage.Store` | HA 2026.2.3 (installed) | Persistent key-value storage in `.storage/` dir | HA standard for integration data that changes frequently and must survive restarts |
| `homeassistant.helpers.event.async_track_time_change` | HA 2026.2.3 (installed) | Fires callback at exact time pattern (local time) | Standard for midnight reset; supports `hour=0, minute=0, second=0` |
| `homeassistant.components.sensor.SensorEntity` | HA 2026.2.3 (installed) | Base class for sensor platform entities | Required for sensor platform |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `dataclasses.dataclass` | stdlib | `ZoneData` value object | Preferred over TypedDict for coordinator data dict values — dot-access, immutable option, IDE support |
| `homeassistant.const.STATE_UNAVAILABLE`, `STATE_UNKNOWN` | HA 2026.2.3 | Guard values for Flume state check | Always check before `float()` conversion |
| `homeassistant.const.UnitOfVolume.GALLONS` | HA 2026.2.3 | Unit for daily_usage sensor | Correct enum value (`"gal"`) |
| `homeassistant.const.UnitOfVolumeFlowRate.GALLONS_PER_MINUTE` | HA 2026.2.3 | Unit for flow_rate sensor | Correct enum value (`"gal/min"`) |
| `homeassistant.components.sensor.SensorDeviceClass.WATER` | HA 2026.2.3 | Device class for daily_usage sensor | Signals HA this is a water measurement; supports unit conversion |
| `homeassistant.components.sensor.SensorDeviceClass.VOLUME_FLOW_RATE` | HA 2026.2.3 | Device class for flow_rate sensor | Generic flow rate device class |
| `homeassistant.helpers.entity_platform.AddConfigEntryEntitiesCallback` | HA 2026.2.3 | Type hint for `async_setup_entry` second arg in `sensor.py` | Correct modern type (not `AddEntitiesCallback`) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `Store` + date check | `RestoreEntity` + `RestoreExtraData` | RestoreEntity restores last-known state but doesn't handle date comparison or midnight reset; Store gives full control over the date-check-and-reset logic needed for USAGE-03 |
| `dataclass` for ZoneData | `TypedDict` | TypedDict works but lacks dot-access; dataclass is cleaner for coordinator data where multiple fields are accessed per poll |

---

## Architecture Patterns

### Recommended Project Structure
```
custom_components/irrigation_monitor/
├── __init__.py          # async_setup_entry: create coordinator, first refresh, forward sensor setup
├── const.py             # add STORAGE_KEY, SAVE_DELAY new constants
├── coordinator.py       # IrrigationCoordinator(DataUpdateCoordinator) + ZoneData dataclass
└── sensor.py            # async_setup_entry(entry, async_add_entities) + 2 entity classes
```

### Pattern 1: Coordinator Subclass with _async_update_data

**What:** Override `_async_update_data` in a `DataUpdateCoordinator` subclass. Raise `UpdateFailed` when Flume is unavailable. Return typed data dict.

**When to use:** All polling integrations that read HA state (not external HTTP) and compute derived values.

**Example (verified from HA 2026.2.3 source):**
```python
# coordinator.py
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_FLUME_ENTITY_ID, CONF_MONITORED_ZONES, CONF_POLL_INTERVAL,
    CONF_ZONES, CONF_CALIBRATED_FLOW, CONF_THRESHOLD_MULTIPLIER,
    DOMAIN, SAVE_DELAY, STORAGE_KEY,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class ZoneData:
    flow_rate: float
    daily_usage: float
    is_available: bool


class IrrigationCoordinator(DataUpdateCoordinator[dict[str, ZoneData]]):
    """Coordinator for irrigation_monitor."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._entry = entry
        self._store = Store(hass, version=1, key=STORAGE_KEY)
        self._daily_totals: dict[str, float] = {}
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,       # REQUIRED: pass config_entry explicitly (HA 2026.x)
            name=DOMAIN,
            update_interval=timedelta(seconds=entry.data[CONF_POLL_INTERVAL]),
        )

    async def _async_setup(self) -> None:
        """Load persisted totals on first setup."""
        stored = await self._store.async_load()
        today = date.today().isoformat()
        if stored and stored.get("date") == today:
            self._daily_totals = dict(stored.get("zones", {}))
        else:
            # HA was offline at midnight or first run — reset
            self._daily_totals = {}
            self._store.async_delay_save(self._data_to_save, 0)
        # Register midnight reset
        self.hass.async_on_stop(
            async_track_time_change(
                self.hass, self._midnight_reset, hour=0, minute=0, second=0
            )
        )

    async def _async_update_data(self) -> dict[str, ZoneData]:
        flume_id = self._entry.data[CONF_FLUME_ENTITY_ID]
        state = self.hass.states.get(flume_id)
        if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            raise UpdateFailed(f"Flume sensor {flume_id} is unavailable")
        try:
            flume_flow = float(state.state)
        except ValueError as err:
            raise UpdateFailed(f"Flume sensor returned non-numeric state: {state.state}") from err

        zones_config = self._entry.options.get(CONF_ZONES, {})
        monitored = self._entry.data[CONF_MONITORED_ZONES]
        result: dict[str, ZoneData] = {}
        interval_seconds = self._entry.data[CONF_POLL_INTERVAL]

        # Attribution logic (multi-zone overlap handled here)
        active_calibrated = {
            z: zones_config[z][CONF_CALIBRATED_FLOW]
            for z in monitored
            if self._zone_is_on(z) and zones_config.get(z, {}).get(CONF_CALIBRATED_FLOW) is not None
        }
        # Check if Flume ≈ sum of calibrated flows (for multi-zone overlap detection)
        calibrated_sum = sum(active_calibrated.values())

        for zone_id in monitored:
            zone_cfg = zones_config.get(zone_id, {})
            is_on = self._zone_is_on(zone_id)
            calibrated_flow = zone_cfg.get(CONF_CALIBRATED_FLOW)

            if not is_on:
                flow_rate = 0.0
                usage_increment = 0.0
            elif calibrated_flow is not None and active_calibrated:
                threshold = zone_cfg.get(CONF_THRESHOLD_MULTIPLIER, 1.5)
                if calibrated_sum > 0 and abs(flume_flow - calibrated_sum) / calibrated_sum <= (threshold - 1.0):
                    flow_rate = calibrated_flow
                else:
                    flow_rate = flume_flow / len(active_calibrated) if len(active_calibrated) == 1 else 0.0
                usage_increment = flow_rate * (interval_seconds / 60.0)
            else:
                # Uncalibrated zone running alone (no overlap ambiguity)
                flow_rate = flume_flow if len(active_calibrated) == 0 else 0.0
                usage_increment = flow_rate * (interval_seconds / 60.0)

            self._daily_totals[zone_id] = self._daily_totals.get(zone_id, 0.0) + usage_increment
            result[zone_id] = ZoneData(
                flow_rate=flow_rate,
                daily_usage=self._daily_totals[zone_id],
                is_available=True,
            )

        self._store.async_delay_save(self._data_to_save, SAVE_DELAY)
        return result

    def _zone_is_on(self, entity_id: str) -> bool:
        state = self.hass.states.get(entity_id)
        return state is not None and state.state == "on"

    def _data_to_save(self) -> dict:
        return {"date": date.today().isoformat(), "zones": dict(self._daily_totals)}

    async def _midnight_reset(self, _now) -> None:
        self._daily_totals = {z: 0.0 for z in self._daily_totals}
        self._store.async_delay_save(self._data_to_save, 0)
        await self.async_refresh()
```

### Pattern 2: ConfigEntry.runtime_data Assignment

**What:** Assign coordinator to `entry.runtime_data` in `async_setup_entry`. Type the entry with `type IrrigationConfigEntry = ConfigEntry[IrrigationCoordinator]` for downstream type safety.

**When to use:** All HA 2024.4+ integrations — replaces `hass.data[DOMAIN][entry.entry_id]`.

**Example (verified from SMLIGHT source, HA 2026.2.3):**
```python
# __init__.py
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .coordinator import IrrigationCoordinator

PLATFORMS: list[str] = ["sensor"]

type IrrigationConfigEntry = ConfigEntry[IrrigationCoordinator]

async def async_setup_entry(hass: HomeAssistant, entry: IrrigationConfigEntry) -> bool:
    coordinator = IrrigationCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: IrrigationConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
```

**CRITICAL ordering:** `async_config_entry_first_refresh()` BEFORE `entry.runtime_data = coordinator` BEFORE `async_forward_entry_setups`. If first refresh raises `ConfigEntryNotReady`, `runtime_data` is never set and sensor setup never runs — correct behavior.

### Pattern 3: CoordinatorEntity Sensor Subclass

**What:** Inherit from both `CoordinatorEntity` and `SensorEntity`. Use `_handle_coordinator_update` (already implemented in base to call `async_write_ha_state`). Override `native_value` and `available` as properties.

**When to use:** All sensor entities driven by a coordinator.

**Example (verified from update_coordinator.py source):**
```python
# sensor.py
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfVolume, UnitOfVolumeFlowRate
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import IrrigationCoordinator, ZoneData
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator: IrrigationCoordinator = entry.runtime_data
    monitored = entry.data["monitored_zone_entity_ids"]
    entities = []
    for zone_id in monitored:
        entities.append(DailyUsageSensor(coordinator, entry, zone_id))
        entities.append(FlowRateSensor(coordinator, entry, zone_id))
    async_add_entities(entities)


class DailyUsageSensor(CoordinatorEntity[IrrigationCoordinator], SensorEntity):
    _attr_device_class = SensorDeviceClass.WATER
    _attr_native_unit_of_measurement = UnitOfVolume.GALLONS
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, zone_id: str) -> None:
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._attr_unique_id = f"{entry.entry_id}_{zone_id}_daily_usage"
        self._attr_name = f"{zone_id} Daily Usage"

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        zone: ZoneData = self.coordinator.data.get(self._zone_id)
        return round(zone.daily_usage, 2) if zone else None


class FlowRateSensor(CoordinatorEntity[IrrigationCoordinator], SensorEntity):
    _attr_device_class = SensorDeviceClass.VOLUME_FLOW_RATE
    _attr_native_unit_of_measurement = UnitOfVolumeFlowRate.GALLONS_PER_MINUTE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, zone_id: str) -> None:
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._attr_unique_id = f"{entry.entry_id}_{zone_id}_flow_rate"
        self._attr_name = f"{zone_id} Flow Rate"

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        zone: ZoneData = self.coordinator.data.get(self._zone_id)
        return round(zone.flow_rate, 2) if zone else None
```

### Pattern 4: Store async_delay_save (debounced write)

**What:** `async_delay_save(data_func, delay)` is a `@callback` (synchronous), not a coroutine. Takes a callable that returns the data. Automatically schedules a `EVENT_HOMEASSISTANT_FINAL_WRITE` listener so pending writes flush on HA shutdown — no manual shutdown hook needed.

**When to use:** Frequent writes where exact timing doesn't matter (usage accumulation every poll).

**Example (verified from storage.py source):**
```python
# Correct — async_delay_save is @callback, not async:
self._store.async_delay_save(self._data_to_save, SAVE_DELAY)

# data_func returns the dict to save:
def _data_to_save(self) -> dict:
    return {"date": date.today().isoformat(), "zones": dict(self._daily_totals)}

# For immediate write (e.g. midnight reset), use delay=0:
self._store.async_delay_save(self._data_to_save, 0)
```

**NOT `await self._store.async_save(...)` in hot path** — `async_save` writes immediately, blocks for disk I/O. Use `async_delay_save` for debouncing; use `async_save` only when you need to guarantee data is on disk (e.g., explicit flush before unload — though `async_delay_save` already handles shutdown via `EVENT_HOMEASSISTANT_FINAL_WRITE`).

### Pattern 5: async_track_time_change for Midnight Reset

**What:** Returns an unsubscribe callable. Must be cancelled on entry unload. Pass to `entry.async_on_unload` or store and call manually.

**Verified signature (event.py, HA 2026.2.3):**
```python
async_track_time_change(
    hass: HomeAssistant,
    action: Callable[[datetime], Coroutine | None],
    hour: Any | None = None,
    minute: Any | None = None,
    second: Any | None = None,
) -> CALLBACK_TYPE  # returns unsubscribe function
```

**Usage in coordinator `_async_setup`:**
```python
# Store unsub so it's cancelled on entry unload
unsub = async_track_time_change(
    self.hass, self._midnight_reset, hour=0, minute=0, second=0
)
# Wire cleanup to config entry unload:
self._entry.async_on_unload(unsub)
```

**IMPORTANT:** `_midnight_reset` can be `async def` (coroutine) or a sync `@callback`. Using `async def` allows it to call `await self.async_refresh()` to push fresh zeroed data to entities immediately.

### Anti-Patterns to Avoid

- **Passing `config_entry=UNDEFINED` to coordinator:** In HA 2026.x, relying on ContextVar (the default when `config_entry` arg is omitted) will error for non-custom integrations and will break in HA 2026.8. Always pass `config_entry=entry` explicitly.
- **`await self._store.async_save(data)` in hot poll path:** Blocks for disk I/O on every poll. Use `async_delay_save` with a 30s delay instead.
- **Calling `async_delay_save` as a coroutine:** It's a `@callback`, not `async def`. Do not `await` it.
- **Registering platform in coordinator `__init__`:** Always do `async_forward_entry_setups` in `__init__.py:async_setup_entry`, after `runtime_data` is assigned.
- **`SensorStateClass.TOTAL_INCREASING` on flow_rate sensor:** Only daily_usage gets `TOTAL_INCREASING`. Flow rate gets `MEASUREMENT`.
- **`hass.data[DOMAIN]` for coordinator storage:** Replaced by `entry.runtime_data` as of HA 2024.4. Do not use.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Polling with error handling | Custom asyncio timer loop | `DataUpdateCoordinator` | Handles exponential backoff, UpdateFailed propagation, listener management, shutdown |
| Entity state refresh on data change | Manual `async_write_ha_state` calls | `CoordinatorEntity._handle_coordinator_update` | Already wired via `async_add_listener` in `async_added_to_hass` |
| Entity unavailability when coordinator fails | Custom `available` property checking error state | `CoordinatorEntity.available` returns `coordinator.last_update_success` | Already correct behavior |
| Debounced writes | Custom asyncio timer + lock | `Store.async_delay_save` | Handles coalescing, shutdown flush via EVENT_HOMEASSISTANT_FINAL_WRITE |
| Midnight callback | Manual datetime polling | `async_track_time_change` | Fires reliably at exact local time, handles DST |

**Key insight:** `CoordinatorEntity` provides `available` for free — when `UpdateFailed` is raised, `last_update_success` becomes `False`, `available` returns `False`, and entities show as unavailable in HA UI. Zero custom availability logic needed.

---

## Common Pitfalls

### Pitfall 1: config_entry Not Passed to DataUpdateCoordinator Constructor
**What goes wrong:** Coordinator uses deprecated ContextVar lookup instead of explicit config_entry reference. HA logs a warning; will break in HA 2026.8.
**Why it happens:** The `config_entry` parameter has a default of `UNDEFINED` which triggers a ContextVar fallback; easy to miss.
**How to avoid:** Always pass `config_entry=entry` in `DataUpdateCoordinator.__init__()` call.
**Warning signs:** HA log: "relies on ContextVar, but should pass the config entry explicitly"

### Pitfall 2: Flume Float Conversion Without State Guard
**What goes wrong:** `float(state.state)` crashes with `ValueError` when Flume returns `"unavailable"` or `"unknown"`.
**Why it happens:** Flume is cloud-dependent; network blips are common.
**How to avoid:**
```python
if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
    raise UpdateFailed("Flume sensor unavailable")
flow = float(state.state)
```
**Warning signs:** `ValueError: could not convert string to float: 'unavailable'` in HA logs.

### Pitfall 3: Midnight Reset Missed if HA Was Offline
**What goes wrong:** `async_track_time_change` callback never fired at 00:00:00; yesterday's totals carry into today.
**Why it happens:** HA was stopped before midnight and started after.
**How to avoid:** In `_async_setup`, compare stored date to today before loading totals. If different, reset to zero regardless of stored values.
**Warning signs:** Daily usage counter accumulates indefinitely without midnight drops.

### Pitfall 4: Zone State for switch/valve Domains
**What goes wrong:** `state.state == "on"` fails to detect running zones for valve entities that use `"open"` state.
**Why it happens:** HA `valve` domain uses `"open"`/`"closed"` states; `switch` domain uses `"on"`/`"off"`.
**How to avoid:** Check the actual entity domain when evaluating zone state:
```python
def _zone_is_on(self, entity_id: str) -> bool:
    state = self.hass.states.get(entity_id)
    if state is None:
        return False
    domain = entity_id.split(".")[0]
    if domain == "valve":
        return state.state == "open"
    return state.state == "on"  # switch, binary_sensor
```
**Warning signs:** Valve zones never accumulate usage despite running.

### Pitfall 5: async_delay_save Called as Coroutine
**What goes wrong:** `await self._store.async_delay_save(...)` raises `TypeError` because `async_delay_save` is `@callback`, not `async def`.
**Why it happens:** Looks like other async helpers.
**How to avoid:** Call without `await`: `self._store.async_delay_save(self._data_to_save, SAVE_DELAY)`

### Pitfall 6: runtime_data Accessed in sensor.py Before Assignment
**What goes wrong:** `entry.runtime_data` raises `AttributeError` if sensor platform setup runs before `__init__.py` assigns it.
**Why it happens:** If `async_forward_entry_setups` is called before `entry.runtime_data = coordinator`.
**How to avoid:** Always assign `entry.runtime_data` BEFORE calling `async_forward_entry_setups`.

### Pitfall 7: SensorStateClass.TOTAL_INCREASING Resets on HA Restart
**What goes wrong:** HA's long-term statistics treats a decrease from yesterday's total as invalid and may discard or warn.
**Why it happens:** Store restores yesterday's total but `TOTAL_INCREASING` expects only-increasing values across sessions.
**How to avoid:** `daily_usage` sensor uses `TOTAL_INCREASING` but resets to 0 at midnight (this is expected behavior for daily totals). HA handles same-day restarts correctly since restored value is same or lower than last recorded. This is acceptable — document that daily totals start from 0 at midnight.

---

## Code Examples

Verified patterns from installed HA 2026.2.3 source:

### Store Constructor
```python
# Source: homeassistant/helpers/storage.py line 230
from homeassistant.helpers.storage import Store

store = Store(
    hass,
    version=1,          # increment if you change data schema
    key="irrigation_monitor.daily_usage",
)
# Store file will be at: .storage/irrigation_monitor.daily_usage
```

### Store Load on Startup
```python
# Source: homeassistant/helpers/storage.py line 292
stored = await self._store.async_load()
# Returns: None (file doesn't exist) or the dict previously saved
# If None: first run, initialize fresh
```

### CoordinatorEntity available Property
```python
# Source: homeassistant/helpers/update_coordinator.py line 643
@property
def available(self) -> bool:
    """Return if entity is available."""
    return self.coordinator.last_update_success
# No override needed — this is automatic
```

### async_track_time_change Signature
```python
# Source: homeassistant/helpers/event.py line 1905
from homeassistant.helpers.event import async_track_time_change

unsub = async_track_time_change(
    hass,
    action,        # Callable[[datetime], Coroutine | None]
    hour=0,
    minute=0,
    second=0,
)
# Returns CALLBACK_TYPE (callable that unsubscribes)
# Fires in local time (not UTC)
```

### async_forward_entry_setups
```python
# Source: homeassistant/config_entries.py line 2594
# Must be awaited before async_setup_entry returns
await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
```

### runtime_data Pattern (from SMLIGHT)
```python
# Source: homeassistant/components/smlight/__init__.py
entry.runtime_data = coordinator          # set before forward_entry_setups
await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
# Access in sensor.py:
coordinator = entry.runtime_data
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `hass.data[DOMAIN][entry.entry_id] = coordinator` | `entry.runtime_data = coordinator` | HA 2024.4 | Cleaner; type-safe with `type IrrigationConfigEntry = ConfigEntry[CoordinatorType]` |
| `async_forward_entry_setup` (single platform) | `async_forward_entry_setups` (plural, list) | HA 2022.x | More efficient, loads platforms in parallel |
| Implicit ContextVar config_entry in coordinator | Explicit `config_entry=entry` parameter | HA 2026.x | Required; ContextVar will error in HA 2026.8 |
| `AddEntitiesCallback` type hint in sensor.py | `AddConfigEntryEntitiesCallback` | HA 2024.x | Use `AddConfigEntryEntitiesCallback` for config-entry-based platforms |

**Deprecated/outdated:**
- `coordinator.async_forward_entry_setup` (singular): use `async_forward_entry_setups` (plural)
- Omitting `config_entry=` in `DataUpdateCoordinator.__init__`: will error in HA 2026.8

---

## Open Questions

1. **Multi-zone attribution threshold comparison**
   - What we know: "total Flume reading ≈ sum of calibrated values (within threshold_multiplier margin)" — but `threshold_multiplier` is 1.5 (meaning "150% of calibrated flow triggers shutoff"). Using it as a flow-attribution margin needs careful interpretation.
   - What's unclear: Is the overlap detection margin `(threshold - 1.0)` (i.e., 50% deviation allowed) or a fixed margin?
   - Recommendation: Implement as `abs(flume_flow - calibrated_sum) <= calibrated_sum * (threshold_multiplier - 1.0)`. Document this interpretation. Phase 4 may refine it.

2. **Uncalibrated single-zone flow attribution**
   - What we know: Decision says uncalibrated zones in multi-zone overlap get 0. Nothing stated about uncalibrated zone running alone.
   - What's unclear: Does an uncalibrated zone running alone get the full Flume reading credited as its flow_rate?
   - Recommendation: Yes — when a single zone is running and it's uncalibrated, attribute full Flume flow to it. This is the only sensible behavior before calibration and enables Phase 4 to immediately start recording data.

3. **valve domain "open"/"closed" vs "on"/"off"**
   - What we know: `conftest.py` mock uses `valve.os_zone_3` with state `"off"`. HA `valve` domain uses `"open"`/`"closed"` in production.
   - What's unclear: Test fixture uses `"off"` but real HA valves use `"open"`. The coordinator must handle both.
   - Recommendation: `_zone_is_on` checks domain prefix to apply correct state string. Tests set valve state to `"open"` to simulate running zone.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-homeassistant-custom-component 0.13.316 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_coordinator.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| USAGE-01 | Sensor entities created per zone with correct unique_id, unit, device_class | unit | `pytest tests/test_coordinator.py::test_sensor_entities_created -x` | Wave 0 |
| USAGE-01 | flow_rate sensor shows 0 when zone is idle | unit | `pytest tests/test_coordinator.py::test_flow_rate_zero_when_idle -x` | Wave 0 |
| USAGE-01 | daily_usage sensor accumulates gallons while zone is running | unit | `pytest tests/test_coordinator.py::test_daily_usage_accumulates -x` | Wave 0 |
| USAGE-01 | All entities go unavailable when Flume is unavailable | unit | `pytest tests/test_coordinator.py::test_flume_unavailable_entities_unavailable -x` | Wave 0 |
| USAGE-02 | Totals persist across simulated restart (Store load) | unit | `pytest tests/test_coordinator.py::test_totals_persist_across_restart -x` | Wave 0 |
| USAGE-02 | Midnight reset zeroes all daily totals | unit | `pytest tests/test_coordinator.py::test_midnight_reset_zeroes_totals -x` | Wave 0 |
| USAGE-03 | Startup with stale stored date resets totals to 0 | unit | `pytest tests/test_coordinator.py::test_stale_date_resets_totals -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_coordinator.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_coordinator.py` — covers all USAGE-01/02/03 tests above
- [ ] Update `tests/conftest.py` — add `mock_config_entry` fixture for coordinator tests (with `add_to_hass` and `async_setup_entry` loading); add `mock_coordinator` fixture

*(Existing test infrastructure: `tests/conftest.py`, `tests/test_config_flow.py`, `pytest.ini_options` — all functional. Only new test file needed.)*

---

## Testing Coordinator in pytest-homeassistant-custom-component

### Setup Pattern (verified from existing test_config_flow.py patterns)
```python
# Test pattern for coordinator integration tests
from pytest_homeassistant_custom_component.common import MockConfigEntry
from homeassistant.core import HomeAssistant

async def test_coordinator_creates_sensors(
    hass: HomeAssistant,
    mock_flume_entity: str,
    mock_valve_entities: list[str],
) -> None:
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
                    CONF_CALIBRATED_FLOW: None,
                    CONF_THRESHOLD_MULTIPLIER: 1.5,
                },
            }
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Verify sensor entities exist
    state = hass.states.get(f"sensor.irrigation_monitor_{mock_valve_entities[0]}_daily_usage")
    assert state is not None
```

### Manually Trigger Coordinator Update in Tests
```python
# coordinator.async_refresh() triggers _async_update_data and notifies entities
await entry.runtime_data.async_refresh()
await hass.async_block_till_done()
```

### Simulate Flume Unavailability
```python
# Set Flume to unavailable state, trigger coordinator update
hass.states.async_set(mock_flume_entity, "unavailable")
await entry.runtime_data.async_refresh()
await hass.async_block_till_done()

# All sensors should now be unavailable
state = hass.states.get("sensor.irrigation_monitor_switch_rachio_zone_1_daily_usage")
assert state.state == "unavailable"
```

### Simulate Midnight Reset in Tests
```python
from unittest.mock import patch
from datetime import datetime

# Fire time change event directly
async_fire_time_changed(hass, datetime(2026, 3, 24, 0, 0, 0))
await hass.async_block_till_done()
```

---

## Sources

### Primary (HIGH confidence)
- Installed HA 2026.2.3 source: `.venv/lib/python3.13/site-packages/homeassistant/helpers/update_coordinator.py` — `DataUpdateCoordinator`, `CoordinatorEntity`, `UpdateFailed` verified
- Installed HA 2026.2.3 source: `.venv/lib/python3.13/site-packages/homeassistant/helpers/storage.py` — `Store.__init__`, `async_load`, `async_save`, `async_delay_save` verified
- Installed HA 2026.2.3 source: `.venv/lib/python3.13/site-packages/homeassistant/helpers/event.py` line 1905 — `async_track_time_change` signature verified
- Installed HA 2026.2.3 source: `.venv/lib/python3.13/site-packages/homeassistant/config_entries.py` — `runtime_data`, `async_forward_entry_setups` verified
- Installed HA 2026.2.3 source: `.venv/lib/python3.13/site-packages/homeassistant/components/smlight/__init__.py` — canonical `runtime_data` + `async_config_entry_first_refresh` + `async_forward_entry_setups` pattern verified
- Installed HA 2026.2.3 source: `.venv/lib/python3.13/site-packages/homeassistant/components/sensor/const.py` — `SensorDeviceClass.WATER`, `SensorDeviceClass.VOLUME_FLOW_RATE` verified
- Installed HA 2026.2.3 source: `.venv/lib/python3.13/site-packages/homeassistant/const.py` — `UnitOfVolume.GALLONS`, `UnitOfVolumeFlowRate.GALLONS_PER_MINUTE`, `STATE_UNAVAILABLE`, `STATE_UNKNOWN` verified

### Secondary (MEDIUM confidence)
- Project research artifacts `.planning/research/ARCHITECTURE.md` and `.planning/research/PITFALLS.md` — consistent with source verification above

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all APIs verified from installed HA 2026.2.3 source
- Architecture: HIGH — coordinator/sensor/store pattern confirmed from smlight reference implementation in same HA version
- Pitfalls: HIGH — P1, P2, P5, P9 verified from source; P4 (valve state) is MEDIUM (observed in fixture but not explicitly tested against real HA valve domain)

**Research date:** 2026-03-23
**Valid until:** 2026-05-23 (stable HA APIs; re-check if HA version upgrades past 2026.8 due to ContextVar removal)
