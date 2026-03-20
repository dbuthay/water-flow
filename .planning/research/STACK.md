# Stack Research: Water Flow Monitor (Home Assistant Custom Integration)

## Summary

Standard 2025 stack for a Home Assistant custom integration with config flow, options flow, HACS distribution, and a custom Lovelace card.

---

## Core Integration Stack

### Language & Runtime
- **Python 3.12+** — Required by current HA stable (2024.x+). Use type hints throughout.
- **Home Assistant Core** — Target 2024.1+ minimum. Integration lives in `custom_components/water_flow_monitor/`.

### Integration Structure
```
custom_components/water_flow_monitor/
├── __init__.py          # async_setup_entry, async_unload_entry
├── manifest.json        # HACS/HA metadata
├── config_flow.py       # ConfigFlow + OptionsFlow
├── coordinator.py       # DataUpdateCoordinator subclass
├── sensor.py            # SensorEntity platforms (daily usage, flow rate)
├── switch.py            # Switch entities (shutoff enable/disable per valve)
├── button.py            # ButtonEntity (calibrate per zone)
├── binary_sensor.py     # Optional status entities
├── const.py             # Domain, config keys, defaults
├── strings.json         # UI strings
└── translations/
    └── en.json          # English translations for config flow UI
```

### Key HA APIs
- **`ConfigFlow`** — Initial setup wizard. Discovers Flume sensor entity + valve entities. [HIGH confidence]
- **`OptionsFlowWithConfigEntry`** — Post-setup reconfiguration. Incremental valve add/remove without losing calibration data. [HIGH confidence]
- **`DataUpdateCoordinator`** — Centralized polling hub. Reads Flume sensor state, evaluates leak conditions, updates all entities. Preferred over per-entity polling. [HIGH confidence]
- **`ConfigEntry.runtime_data`** — Store coordinator instance on the config entry (replaces legacy `hass.data[DOMAIN]` pattern). Available since HA 2024.4. [HIGH confidence]
- **`EntityRegistry`** — Used during discovery to find candidate valve entities by device class or entity_id pattern.
- **`StatisticsHelper` / `recorder`** — For persisting daily usage totals across HA restarts. [MEDIUM confidence — verify current API]

### Selectors (Config Flow UI)
- **`EntitySelector`** — Pick Flume sensor entity from HA entity list
- **`SelectSelector`** — Multi-select valve candidates
- **`NumberSelector`** — Leak threshold multiplier per zone (e.g., 1.5 = 150%)
- **`BooleanSelector`** — Per-valve shutoff enable/disable toggles

---

## Testing Stack

### pytest-homeassistant-custom-component
- **Package**: `pytest-homeassistant-custom-component` — must match target HA version
- **Key fixture**: `hass` — provides a real (lightweight) HA instance
- **Key fixture**: `mock_config_entry` — create config entries without UI flow
- **Mocking entities**: Use `hass.states.async_set("sensor.flume_flow", "2.5")` to simulate Flume readings
- **Mocking valve state**: `hass.states.async_set("binary_sensor.zone_1", "on")`
- **Config flow testing**: `hass.config_entries.flow.async_init()` + `async_configure()`

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"

[project.optional-dependencies]
test = [
    "pytest-homeassistant-custom-component",
    "pytest-asyncio",
    "pytest-cov",
]
```

### Local HA Dev Instance
- Run `hass -c config/` with a `configuration.yaml` that defines fake Flume + valve entities using `template:` or `input_number:` / `input_boolean:`
- Test config flow UI manually

---

## HACS Distribution

### manifest.json
```json
{
  "domain": "water_flow_monitor",
  "name": "Water Flow Monitor",
  "version": "1.0.0",
  "documentation": "https://github.com/...",
  "issue_tracker": "https://github.com/.../issues",
  "dependencies": [],
  "codeowners": ["@yourusername"],
  "iot_class": "local_polling",
  "config_flow": true
}
```

### hacs.json
```json
{
  "name": "Water Flow Monitor",
  "content_in_root": false
}
```

### HACS Requirements
- Public GitHub repository
- `custom_components/` at repo root
- Semver git tags (e.g., `v1.0.0`) for releases
- `hacs.json` at repo root
- `manifest.json` with `version` field

---

## Custom Lovelace Card

### Recommended Stack
- **Lit 3.x** — Web components library used by HA core cards. Reactive properties, shadow DOM. [HIGH confidence]
- **TypeScript** — Type safety, better IDE support
- **Rollup** — Bundler (produces single `.js` file). HA uses Rollup, not Webpack.
- **`@web/dev-server`** — Local dev server for card iteration

### Card Structure
```
src/
├── water-flow-card.ts   # Main LitElement class
├── types.ts             # TypeScript interfaces
└── styles.ts            # CSS template literal
dist/
└── water-flow-card.js   # Bundled output (referenced by Lovelace)
```

### Card Registration
```typescript
customElements.define("water-flow-card", WaterFlowCard);
window.customCards = window.customCards || [];
window.customCards.push({
  type: "water-flow-card",
  name: "Water Flow Monitor",
  description: "Zone status, flow rate, and daily usage"
});
```

### HACS Frontend Distribution
Cards go in `www/` at the root of the HACS repo. HA loads them as local resources.

---

## What NOT To Use

| Avoid | Instead | Why |
|-------|---------|-----|
| `hass.data[DOMAIN]` | `ConfigEntry.runtime_data` | Legacy pattern, not type-safe |
| YAML `configuration.yaml` setup | Config flow UI | User preference + modern HA standard |
| Synchronous I/O in entities | `async_update` + coordinator | Blocks HA event loop |
| `input_boolean` for valve toggles | `SwitchEntity` in integration | Proper entity ownership |
| Webpack | Rollup | HA ecosystem standard |
| Per-entity polling | `DataUpdateCoordinator` | Single poll, shared state |
| Storing calibration in `hass.data` | `ConfigEntry.options` or `Store` | Persists across restarts |

---

## Confidence Levels

| Area | Confidence | Notes |
|------|------------|-------|
| Integration file structure | HIGH | Stable HA API |
| Config flow / options flow | HIGH | Well-documented |
| DataUpdateCoordinator | HIGH | Standard pattern |
| ConfigEntry.runtime_data | HIGH | Available since 2024.4 |
| Lit + Rollup for card | HIGH | HA ecosystem standard |
| pytest-homeassistant-custom-component | HIGH | Active project |
| Statistics/recorder API for daily totals | MEDIUM | Verify current API shape |
| EntityRegistry discovery pattern | MEDIUM | May vary by controller integration |
