# Phase 2: Config Flow - Research

**Researched:** 2026-03-19
**Domain:** Home Assistant ConfigFlow, OptionsFlow, EntitySelector, EntityRegistry discovery
**Confidence:** HIGH (all core APIs verified via HA source; Flume entity format confirmed from source)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Step 1**: Select Flume sensor — show all numeric sensor entities (EntitySelector); user picks their Flume sensor. No auto-detection required — always show a list.
- **Step 2**: Select valves — show discovered valve candidates (or all switches/binary_sensors if none obvious); multi-select. Each entry shown as `"Friendly Name (entity_id)"`.
- Per-zone settings NOT collected at initial setup — deferred to options flow.
- New valves added via options flow also start with defaults immediately.
- **Per-zone defaults**: leak detection disabled until calibrated (threshold = None/0), shutoff_enabled = true, alerts_enabled = true.
- **Options flow scope**: valve management, per-zone settings, Flume sensor, global poll interval.
- **Removing a valve**: clears its calibration data entirely.
- **Merge strategy CRITICAL**: always merge into existing options dict, never replace. `existing = dict(self.config_entry.options); existing["zones"] = updated_zones; return self.async_create_entry(data=existing)`
- Fallback: show all switch + binary_sensor entities if no obvious irrigation valves found.
- No manual text entry — always a picker.

### Claude's Discretion
- Exact HA Selectors used (EntitySelector, SelectSelector, NumberSelector, BooleanSelector)
- ConfigEntry.data vs ConfigEntry.options data split
- Step-by-step flow implementation details
- Error handling for unavailable entities during setup

### Deferred Ideas (OUT OF SCOPE)
- None from discussion.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SETUP-01 | User can select the Flume flow sensor entity from a list of HA entities during initial setup | EntitySelector with integration="flume" filter covers this; fallback to domain="sensor" if no flume entities found |
| SETUP-02 | Integration scans HA entity registry for irrigation valve entities and presents them as candidates | EntityRegistry.async_get() + filtering by domain (switch, valve) and optionally device_class; valve domain now exists in HA |
| SETUP-03 | User selects which valves to monitor (not all discovered valves need to be monitored) | EntitySelector with multiple=true (or SelectSelector with entity list); multi-select confirmed |
| SETUP-04 | User can re-run valve discovery via integration options to add newly available valves without losing existing zone configuration | OptionsFlow with merge strategy: existing = dict(self.config_entry.options); existing["zones"] = updated; async_create_entry(data=existing) |
| SETUP-05 | User can enable or disable auto-shutoff per monitored valve at any time | Per-zone options stored in ConfigEntry.options["zones"][entity_id]["shutoff_enabled"]; editable in options flow |
| SETUP-06 | User can enable or disable anomaly alerts per monitored valve at any time | Per-zone options stored in ConfigEntry.options["zones"][entity_id]["alerts_enabled"]; editable in options flow |
| SETUP-07 | User can configure the leak detection threshold multiplier per zone | Per-zone options stored in ConfigEntry.options["zones"][entity_id]["threshold"]; NumberSelector in options flow |
</phase_requirements>

---

## Summary

Phase 2 builds the full config flow (initial setup wizard) and options flow (post-setup reconfiguration) for the irrigation_monitor integration. The config flow is a two-step wizard: Step 1 picks the Flume sensor, Step 2 multi-selects irrigation valves. Per-zone settings are deferred entirely to the options flow to keep first-run simple.

The most important technical finding for planning: **the Flume `current_interval` sensor has no device_class** (confirmed from HA source). The EntitySelector filter must use `integration: "flume"` (not `device_class: "flow"`). If the user does not have the Flume integration installed, the fallback is `domain: "sensor"` — the user picks from all sensors. This is consistent with the CONTEXT.md decision that "no auto-detection required — always show a list."

The options flow merge pattern is architecturally critical. HA's `OptionsFlow.async_create_entry(data=...)` replaces the entire options dict. Callers MUST read `self.config_entry.options`, copy it, update only the changed keys, and pass the merged dict. Failure destroys calibration data stored in options (Phase 4's data).

**Primary recommendation:** Use `OptionsFlow` (not the legacy `OptionsFlowWithConfigEntry`). Access `self.config_entry` directly — it is injected by the framework automatically. Register with `@staticmethod @callback async_get_options_flow(config_entry) -> OptionsFlowHandler`.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `homeassistant.config_entries.ConfigFlow` | HA built-in | Two-step initial setup wizard | HA standard for UI-based setup |
| `homeassistant.config_entries.OptionsFlow` | HA built-in | Post-setup reconfiguration | Current pattern (OptionsFlowWithConfigEntry is legacy) |
| `homeassistant.helpers.selector.EntitySelector` | HA built-in | Flume sensor picker, valve multi-select | Native HA selector with filtering support |
| `homeassistant.helpers.selector.SelectSelector` | HA built-in | Custom option list (e.g., formatted valve display) | Supports multiple=true, custom labels |
| `homeassistant.helpers.selector.NumberSelector` | HA built-in | Threshold multiplier input | Slider or box input with min/max/step |
| `homeassistant.helpers.selector.BooleanSelector` | HA built-in | Shutoff/alerts per-zone toggles | Toggle switch in UI |
| `homeassistant.helpers.entity_registry` | HA built-in | Discover valve candidates from registry | Access to all registered entities |
| `voluptuous` (`vol`) | HA built-in | Schema validation in flow steps | Required for `async_show_form` data_schema |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `homeassistant.helpers.selector.EntitySelectorConfig` | HA built-in | Typed config for EntitySelector | Always use typed config for IDE support |
| `homeassistant.helpers.selector.SelectSelectorConfig` | HA built-in | Typed config for SelectSelector | When building custom option lists |
| `homeassistant.data_entry_flow.FlowResultType` | HA built-in | Test assertions on flow step results | In tests: FORM, CREATE_ENTRY, ABORT |
| `tests.common.MockConfigEntry` | pytest-ha-custom | Create entries without UI in tests | All config flow tests |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| EntitySelector with integration="flume" | EntitySelector with domain="sensor" | integration filter is cleaner but fails if Flume not installed — use domain="sensor" as fallback |
| SelectSelector with formatted strings | EntitySelector with multiple=true | EntitySelector native is cleaner; SelectSelector allows "Friendly Name (entity_id)" display format (user decision) |
| OptionsFlow (current) | OptionsFlowWithConfigEntry (legacy) | OptionsFlowWithConfigEntry is the old pattern; OptionsFlow with self.config_entry is current — confirmed from Rachio and demo integrations |

**Installation:** No extra packages needed. All APIs are built into HA core.

---

## Architecture Patterns

### Recommended Project Structure
```
custom_components/irrigation_monitor/
├── __init__.py          # async_setup_entry stub (exists — extend, don't replace)
├── manifest.json        # Set config_flow: true in this phase
├── config_flow.py       # IrrigationMonitorConfigFlow + IrrigationMonitorOptionsFlowHandler
├── const.py             # Add CONF_* keys, DOMAIN, default values
├── strings.json         # UI strings (step titles, field labels, error messages)
└── translations/
    └── en.json          # English translations (mirrors strings.json)
```

### ConfigEntry Data Split

```
ConfigEntry.data = {
    "flume_entity_id": "sensor.flume_sensor_current_interval",
    "monitored_zone_entity_ids": ["switch.rachio_zone_1", "switch.rain_bird_sprinkler_1"],
    "poll_interval": 30,
}

ConfigEntry.options = {
    "zones": {
        "switch.rachio_zone_1": {
            "shutoff_enabled": True,
            "alerts_enabled": True,
            "threshold": None,          # None = not yet calibrated, skip detection
            "calibrated_flow": None,    # Written by Phase 4 calibration
        },
        ...
    }
}
```

**Rule:** `data` is set once at config flow time (or reconfigured). `options` is modified incrementally — by the options flow (user settings) and by Phase 4 calibration (programmatic write via `hass.config_entries.async_update_entry`).

### Pattern 1: Two-Step Config Flow

```python
# Source: HA demo config_flow.py + official HA docs pattern
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    EntityFilterSelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
)
import voluptuous as vol
from .const import DOMAIN, CONF_FLUME_ENTITY_ID, CONF_MONITORED_ZONES, CONF_POLL_INTERVAL

class IrrigationMonitorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle config flow for Irrigation Monitor."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 1: Pick Flume sensor."""
        if user_input is not None:
            self._flume_entity_id = user_input[CONF_FLUME_ENTITY_ID]
            return await self.async_step_valves()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_FLUME_ENTITY_ID): EntitySelector(
                    EntitySelectorConfig(
                        filter=EntityFilterSelectorConfig(
                            integration="flume",  # narrows to flume sensors
                        )
                    )
                ),
            }),
        )

    async def async_step_valves(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 2: Pick valves to monitor."""
        if user_input is not None:
            return self.async_create_entry(
                title="Irrigation Monitor",
                data={
                    CONF_FLUME_ENTITY_ID: self._flume_entity_id,
                    CONF_MONITORED_ZONES: user_input[CONF_MONITORED_ZONES],
                    CONF_POLL_INTERVAL: 30,
                },
            )

        valve_candidates = self._discover_valve_entities()
        options = [
            {"value": eid, "label": f"{name} ({eid})"}
            for eid, name in valve_candidates
        ]

        return self.async_show_form(
            step_id="valves",
            data_schema=vol.Schema({
                vol.Required(CONF_MONITORED_ZONES): SelectSelector(
                    SelectSelectorConfig(options=options, multiple=True)
                ),
            }),
        )

    def _discover_valve_entities(self) -> list[tuple[str, str]]:
        """Return list of (entity_id, friendly_name) valve candidates."""
        registry = er.async_get(self.hass)
        candidates = []
        for entry in registry.entities.values():
            if entry.domain in ("switch", "valve", "binary_sensor"):
                # Prefer valve domain (water device class) or switch with no device class
                name = entry.name or entry.original_name or entry.entity_id
                candidates.append((entry.entity_id, name))
        return candidates

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "IrrigationMonitorOptionsFlowHandler":
        """Get the options flow handler."""
        return IrrigationMonitorOptionsFlowHandler()
```

### Pattern 2: Options Flow with Merge Strategy

```python
# Source: Rachio config_flow.py pattern + CONTEXT.md merge requirement
class IrrigationMonitorOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Irrigation Monitor."""

    async def async_step_init(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage options: global settings + valve management."""
        if user_input is not None:
            # CRITICAL: merge, never replace
            existing = dict(self.config_entry.options)
            existing[CONF_POLL_INTERVAL] = user_input[CONF_POLL_INTERVAL]
            existing[CONF_FLUME_ENTITY_ID] = user_input[CONF_FLUME_ENTITY_ID]
            # Store selected zones but preserve existing per-zone config
            self._new_zone_ids = user_input[CONF_MONITORED_ZONES]
            return await self.async_step_zones()

        current_data = self.config_entry.data
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(
                    CONF_FLUME_ENTITY_ID,
                    default=current_data.get(CONF_FLUME_ENTITY_ID),
                ): EntitySelector(...),
                vol.Required(
                    CONF_MONITORED_ZONES,
                    default=current_data.get(CONF_MONITORED_ZONES, []),
                ): SelectSelector(SelectSelectorConfig(options=valve_options, multiple=True)),
                vol.Optional(
                    CONF_POLL_INTERVAL,
                    default=current_data.get(CONF_POLL_INTERVAL, 30),
                ): NumberSelector(NumberSelectorConfig(min=10, max=300, step=5, unit_of_measurement="s")),
            }),
        )

    async def async_step_zones(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        """Per-zone settings step."""
        if user_input is not None:
            existing = dict(self.config_entry.options)
            old_zones = existing.get("zones", {})
            new_zones = {}
            for zone_id in self._new_zone_ids:
                if zone_id in old_zones:
                    # Preserve existing config (including calibration)
                    new_zones[zone_id] = old_zones[zone_id]
                else:
                    # New zone: apply defaults
                    new_zones[zone_id] = {
                        "shutoff_enabled": True,
                        "alerts_enabled": True,
                        "threshold": None,
                        "calibrated_flow": None,
                    }
            existing["zones"] = new_zones
            return self.async_create_entry(data=existing)
        # ... show per-zone form
```

### Pattern 3: Programmatic Options Update (Phase 4 reference)

```python
# Used by calibration in Phase 4 — NOT in config_flow.py, but must be compatible
existing = dict(entry.options)
existing["zones"][zone_entity_id]["calibrated_flow"] = measured_flow
hass.config_entries.async_update_entry(entry, options=existing)
```

### Pattern 4: Config Flow Tests

```python
# Source: pytest-homeassistant-custom-component pattern + pyscript test conventions
from homeassistant.data_entry_flow import FlowResultType
from tests.common import MockConfigEntry

async def test_config_flow_creates_entry(hass):
    """Test full config flow produces a valid ConfigEntry."""
    # Simulate Flume sensor in state machine
    hass.states.async_set("sensor.flume_current_interval", "1.5",
                          attributes={"unit_of_measurement": "gal/min"})

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"flume_entity_id": "sensor.flume_current_interval"},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "valves"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"monitored_zone_entity_ids": ["switch.rachio_zone_1"]},
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["flume_entity_id"] == "sensor.flume_current_interval"
    assert "switch.rachio_zone_1" in result["data"]["monitored_zone_entity_ids"]

async def test_options_flow_merges_not_replaces(hass, config_entry):
    """Test that options flow merge strategy preserves existing zone data."""
    # Pre-seed options with calibration data
    hass.config_entries.async_update_entry(
        config_entry,
        options={"zones": {"switch.zone_1": {"calibrated_flow": 3.5, "shutoff_enabled": True}}}
    )
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    # ... configure flow ...
    # Assert calibrated_flow is preserved after options flow completes
    assert config_entry.options["zones"]["switch.zone_1"]["calibrated_flow"] == 3.5
```

### Anti-Patterns to Avoid

- **Replace instead of merge in options flow**: `async_create_entry(data={"zones": new_zones})` wipes calibration data. Always merge.
- **Using OptionsFlowWithConfigEntry**: Legacy pattern. Use `OptionsFlow` — `self.config_entry` is injected automatically.
- **Filtering Flume by device_class="flow"**: Flume's current_interval sensor has NO device_class. Filter by `integration="flume"` or `domain="sensor"` + `unit_of_measurement="gal/min"`.
- **Assuming all valves are switches**: HA has a `valve` domain (ValveDeviceClass.WATER) that some controllers use. Discover from `domain in ("switch", "valve")`.
- **Setting `config_flow: true` in manifest.json without config_flow.py**: HA will reject the integration. Both must be added together.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Entity picker UI | Custom input field | EntitySelector with filter | Built-in HA UI component; filter by integration, domain, device_class |
| Multi-select entity list | Custom HTML select | SelectSelector with multiple=true | Native HA multi-select; supports value/label pairs |
| Options persistence | Custom JSON file | ConfigEntry.options via async_update_entry | Persisted automatically to .storage/core.config_entries |
| Options merge | Custom dict merge utility | Manual merge pattern (copy, update, pass) | No utility exists — must be explicit |
| Form validation | Custom validator | vol.Schema with vol.Required/Optional | Voluptuous is the HA standard |
| Entity discovery scan | Custom state iteration | EntityRegistry.async_get(hass).entities.values() | Proper registry access; includes disabled entities too |

**Key insight:** The entire config/options flow UI is declarative — define vol.Schema with Selectors, HA renders the form. No custom frontend code in Phase 2.

---

## Common Pitfalls

### Pitfall 1: Options Flow Destroys Calibration Data (P3 from PITFALLS.md)
**What goes wrong:** `return self.async_create_entry(data={"zones": new_zones})` replaces ALL options, erasing `calibrated_flow` from Phase 4.
**Why it happens:** async_create_entry replaces the entire options dict.
**How to avoid:** Always: `existing = dict(self.config_entry.options); existing["zones"] = new_zones; return self.async_create_entry(data=existing)`
**Warning signs:** After running options flow, calibration disappears from stored options.

### Pitfall 2: Flume EntitySelector Filter Fails Silently
**What goes wrong:** Using `device_class: "flow"` as EntitySelector filter returns empty list — Flume `current_interval` has no device_class.
**Why it happens:** Flume sensor uses no SensorDeviceClass for flow rate (confirmed from source). Unit is `"gal/m"` not a device_class.
**How to avoid:** Filter by `integration: "flume"`. Fallback: show all `domain: "sensor"` entities if no Flume entities found.
**Warning signs:** Config flow Step 1 shows an empty dropdown.

### Pitfall 3: Missing valve Domain in Discovery
**What goes wrong:** Discovery only scans `switch.*` entities, misses `valve.*` entities from newer controller integrations.
**Why it happens:** HA added a dedicated `valve` domain with `ValveDeviceClass.WATER/GAS`. Some newer integrations use it.
**How to avoid:** Scan `entry.domain in ("switch", "valve", "binary_sensor")` in `_discover_valve_entities()`.
**Warning signs:** OpenSprinkler or similar valve-domain controllers not appearing in Step 2.

### Pitfall 4: manifest.json config_flow: false
**What goes wrong:** Integration installed but Settings → Integrations → Add Integration doesn't show "Irrigation Monitor".
**Why it happens:** `config_flow.py` must exist AND `manifest.json` must have `"config_flow": true`. Currently set to `false`.
**How to avoid:** Both changes must happen in the same task: write config_flow.py + flip manifest.json.
**Warning signs:** Integration not discoverable through HA UI.

### Pitfall 5: OptionsFlow Step Naming Conflicts
**What goes wrong:** If options flow step_id matches config flow step_id (e.g., both use "user"), strings.json translations collide.
**Why it happens:** HA's strings.json has separate namespaces for `config` and `options` steps.
**How to avoid:** Use distinct step_ids: config flow uses `"user"` and `"valves"`; options flow uses `"init"` and `"zones"`.

### Pitfall 6: Removing a Valve Leaves Stale Unique IDs
**What goes wrong:** Phase 3 entities for removed valves remain in the entity registry as orphans.
**Why it happens:** Phase 2 removes zone_id from options but Phase 3 entity cleanup depends on reading the updated zones list.
**How to avoid:** Phase 2 design: when options flow removes a valve, delete its entire entry from `options["zones"]` (the CONTEXT.md decision). Phase 3 reads `entry.options["zones"].keys()` to know which entities to register.

---

## Code Examples

Verified patterns from official sources:

### EntitySelector with integration filter (Flume)
```python
# Source: homeassistant/helpers/selector.py EntityFilterSelectorConfig
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    EntityFilterSelectorConfig,
)

EntitySelector(
    EntitySelectorConfig(
        filter=EntityFilterSelectorConfig(integration="flume"),
    )
)
```

### EntitySelector with domain + unit fallback
```python
# Fallback when filtering by integration: show all numeric sensors
EntitySelector(
    EntitySelectorConfig(
        filter=EntityFilterSelectorConfig(
            domain="sensor",
            unit_of_measurement="gal/m",  # matches Flume's unit
        )
    )
)
```

### SelectSelector for valve list (with "Friendly Name (entity_id)" format)
```python
# Source: homeassistant/helpers/selector.py SelectSelectorConfig
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectOptionDict,
)

options = [
    SelectOptionDict(value=eid, label=f"{name} ({eid})")
    for eid, name in valve_candidates
]

SelectSelector(SelectSelectorConfig(options=options, multiple=True))
```

### EntityRegistry scan for valve candidates
```python
# Source: homeassistant/helpers/entity_registry.py
from homeassistant.helpers import entity_registry as er

def _discover_valve_entities(self) -> list[tuple[str, str]]:
    registry = er.async_get(self.hass)
    VALVE_DOMAINS = {"switch", "valve", "binary_sensor"}
    candidates = []
    for entry in registry.entities.values():
        if entry.domain not in VALVE_DOMAINS:
            continue
        # Prefer valve domain with water device_class
        # For fallback: include all switch/binary_sensor
        name = entry.name or entry.original_name or entry.entity_id
        candidates.append((entry.entity_id, name))
    return sorted(candidates, key=lambda x: x[1])  # sort by friendly name
```

### Options flow registration on ConfigFlow
```python
# Source: Rachio config_flow.py + demo config_flow.py (HA core)
from homeassistant.core import callback

class IrrigationMonitorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "IrrigationMonitorOptionsFlowHandler":
        """Return the options flow handler."""
        return IrrigationMonitorOptionsFlowHandler()
```

### OptionsFlow class (current pattern — NOT OptionsFlowWithConfigEntry)
```python
# Source: Rachio + demo integrations (HA core dev branch)
class IrrigationMonitorOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow handler — self.config_entry is injected by HA framework."""

    async def async_step_init(self, user_input=None):
        # Access via self.config_entry (no __init__ needed for basic case)
        current = self.config_entry.data
        options = self.config_entry.options
        ...
```

### Options flow merge (CRITICAL pattern)
```python
# Source: PITFALLS.md P3 + CONTEXT.md specifics
# WRONG:
return self.async_create_entry(data={"zones": new_zones})

# RIGHT:
existing = dict(self.config_entry.options)
existing["zones"] = new_zones  # preserve other keys (future-proof)
return self.async_create_entry(data=existing)
```

### Config flow test pattern
```python
# Source: pyscript test_config_flow.py + pytest-homeassistant-custom-component docs
from homeassistant.data_entry_flow import FlowResultType

async def test_step_user_shows_form(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

async def test_options_flow(hass, config_entry):
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={...}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `OptionsFlowWithConfigEntry` | `OptionsFlow` with `self.config_entry` | ~2024.x | OptionsFlowWithConfigEntry is legacy — base OptionsFlow now exposes config_entry directly |
| `hass.data[DOMAIN]` for coordinator | `ConfigEntry.runtime_data` | 2024.4 | Type-safe, no domain key collisions |
| `vol.Schema` with bare type validators | `vol.Schema` with Selector objects | 2022+ | Selectors render native HA UI components |
| switch.* only for irrigation valves | switch.* AND valve.* domains | ~2023-2024 | HA added dedicated valve domain with ValveDeviceClass.WATER |

**Deprecated/outdated:**
- `OptionsFlowWithConfigEntry`: Still functional but not the pattern used in current HA core integrations. Use plain `OptionsFlow`.
- `cv.multi_select()` (as a vol validator): Still works but SelectSelector is the modern equivalent with proper UI rendering.

---

## Open Questions

1. **Flume integration filter fallback UX**
   - What we know: `integration="flume"` filter returns empty if Flume not installed
   - What's unclear: Does EntitySelector show an empty disabled state or error? Is there a way to conditionally switch filter strategies within the flow?
   - Recommendation: In `async_step_user`, scan EntityRegistry first. If no entities with `platform == "flume"` found, fall back to showing `domain="sensor"` with a description hint. Alternatively use SelectSelector (custom list) for Step 1 too, building the options list from EntityRegistry.

2. **Valve discovery — how to identify irrigation-specific valves vs generic switches**
   - What we know: No `device_class` distinguishes irrigation switches from other switches in Rachio/RainBird. `valve` domain uses `ValveDeviceClass.WATER` which is specific. Switch platform_origin (Rachio) could be used but is fragile.
   - What's unclear: Is there any standard attribute (e.g., entity_category, platform name) that reliably identifies an irrigation valve switch vs a light switch?
   - Recommendation: Scan for `domain == "valve"` first (highest signal). For `domain == "switch"`, filter by `entry.platform in ("rachio", "rainbird", "opensprinkler", "irrigation_unlimited")` as a best-effort heuristic. Fall back to all switches if no heuristic matches. User always makes final selection.

3. **OptionsFlow accessing ConfigEntry.data vs ConfigEntry.options for current zone list**
   - What we know: CONTEXT.md says `monitored_zone_entity_ids` is in `ConfigEntry.data`, per-zone settings in `ConfigEntry.options`.
   - What's unclear: When options flow re-runs valve discovery, should the current monitored list come from `self.config_entry.data["monitored_zone_entity_ids"]` or from `self.config_entry.options["zones"].keys()`? These should be the same but could drift.
   - Recommendation: Use `options["zones"].keys()` as the source of truth for currently monitored zones in options flow (since options flow is also responsible for updating the zone list). Update `ConfigEntry.data` as well via `async_update_entry` if needed for coordinator in Phase 3.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest-homeassistant-custom-component 0.13.316 |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `python -m pytest tests/test_config_flow.py -x -q` |
| Full suite command | `python -m pytest tests/ -x -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SETUP-01 | Config flow Step 1 shows Flume entity picker | unit | `pytest tests/test_config_flow.py::test_step_user_shows_form -x` | Wave 0 |
| SETUP-01 | Submitting valid Flume entity advances to Step 2 | unit | `pytest tests/test_config_flow.py::test_step_user_advances -x` | Wave 0 |
| SETUP-02 | Step 2 shows discovered valve candidates | unit | `pytest tests/test_config_flow.py::test_step_valves_discovery -x` | Wave 0 |
| SETUP-02 | Fallback shows all switches if no obvious valves | unit | `pytest tests/test_config_flow.py::test_step_valves_fallback -x` | Wave 0 |
| SETUP-03 | User can multi-select valves; entry is created | unit | `pytest tests/test_config_flow.py::test_full_flow_creates_entry -x` | Wave 0 |
| SETUP-04 | Options flow re-runs discovery without losing zone data | unit | `pytest tests/test_config_flow.py::test_options_flow_merge_preserves_zones -x` | Wave 0 |
| SETUP-05 | Options flow saves shutoff_enabled per zone | unit | `pytest tests/test_config_flow.py::test_options_per_zone_shutoff -x` | Wave 0 |
| SETUP-06 | Options flow saves alerts_enabled per zone | unit | `pytest tests/test_config_flow.py::test_options_per_zone_alerts -x` | Wave 0 |
| SETUP-07 | Options flow saves threshold multiplier per zone | unit | `pytest tests/test_config_flow.py::test_options_per_zone_threshold -x` | Wave 0 |
| MERGE CRITICAL | Options flow never replaces, always merges options | unit | `pytest tests/test_config_flow.py::test_options_merge_not_replace -x` | Wave 0 |
| REMOVE VALVE | Removing a valve clears its zone data entirely | unit | `pytest tests/test_config_flow.py::test_options_remove_valve_clears_data -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_config_flow.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_config_flow.py` — covers all SETUP-01 through SETUP-07 requirements listed above
- [ ] Entity state fixtures in `tests/conftest.py` — mock Flume sensor + valve switch states for config flow tests

*(Existing `conftest.py` has `enable_custom_integrations` fixture — sufficient base; add entity state helpers)*

---

## Sources

### Primary (HIGH confidence)
- `homeassistant/helpers/selector.py` (raw GitHub, dev branch) — EntitySelectorConfig, EntityFilterSelectorConfig, SelectSelectorConfig exact field definitions
- `homeassistant/config_entries.py` (raw GitHub, dev branch) — async_update_entry signature, ConfigEntry.options as MappingProxyType, post-update listener dispatch
- `homeassistant/components/flume/sensor.py` (raw GitHub, dev branch) — confirmed current_interval has NO device_class, unit is `gal/m`
- `homeassistant/components/rachio/config_flow.py` (raw GitHub, dev branch) — OptionsFlow (not OptionsFlowWithConfigEntry), self.config_entry pattern
- `homeassistant/components/demo/config_flow.py` (raw GitHub, dev branch) — async_get_options_flow @staticmethod @callback registration, cv.multi_select
- `homeassistant/components/valve/__init__.py` (raw GitHub, dev branch) — valve domain exists, ValveDeviceClass.WATER/GAS confirmed
- `homeassistant/components/switch/__init__.py` (raw GitHub, dev branch) — SwitchDeviceClass only has OUTLET and SWITCH; no irrigation/valve class

### Secondary (MEDIUM confidence)
- Home Assistant blueprints selector docs (www.home-assistant.io/docs/blueprint/selectors/) — EntitySelector filter YAML examples, SelectSelector multiple=true, NumberSelector config
- RainBird integration docs — zones exposed as switch.rain_bird_sprinkler_N pattern confirmed
- Rachio integration docs — zones exposed as switch entities, no per-zone binary_sensors

### Tertiary (LOW confidence)
- OpenSprinkler valve entity domain — could not verify from docs whether it uses switch or valve domain; assumed to follow valve domain pattern given ValveDeviceClass.WATER exists

---

## Metadata

**Confidence breakdown:**
- Config/Options flow API: HIGH — verified from HA core source (rachio, demo integrations)
- EntitySelector filter API: HIGH — verified from selector.py source (EntityFilterSelectorConfig TypedDict)
- Flume sensor entity format: HIGH — verified from flume/sensor.py source (no device_class, unit=gal/m)
- Valve entity domain: HIGH — verified from valve/__init__.py source
- Rachio/RainBird zone format: MEDIUM — confirmed switch domain from docs, no source verification of attributes
- Options merge pattern: HIGH — verified from config_entries.py async_update_entry + CONTEXT.md decision
- Test patterns: HIGH — verified from pyscript tests + pytest-homeassistant-custom-component

**Research date:** 2026-03-19
**Valid until:** 2026-06-19 (stable HA APIs; re-verify if HA 2025.x changes config_entries API)
