# Architecture: Water Flow Monitor HA Integration

**Domain:** Home Assistant custom integration
**Pattern:** DataUpdateCoordinator + Config/Options flow + Lit Lovelace card

---

## Component Map

```
┌─────────────────────────────────────────────────────────┐
│                   Home Assistant Core                    │
│                                                         │
│  ┌──────────────┐    ┌─────────────────────────────┐   │
│  │ Flume sensor │    │ Irrigation controller       │   │
│  │ (pre-existing│    │ binary_sensor.zone_N (on/off)│   │
│  │  integration)│    │ switch.zone_N (control)      │   │
│  └──────┬───────┘    └──────────────┬──────────────┘   │
│         │                           │                   │
│  ┌──────▼───────────────────────────▼──────────────┐   │
│  │         WaterFlowCoordinator                     │   │
│  │  - Polls Flume sensor every N seconds            │   │
│  │  - Reads active zone states                      │   │
│  │  - Runs leak detection logic                     │   │
│  │  - Accumulates daily usage per zone              │   │
│  │  - Triggers shutoff if threshold exceeded        │   │
│  └──────┬───────────────────────────────────────────┘   │
│         │ pushes state to                               │
│  ┌──────▼───────────────────────────────────────────┐   │
│  │  Entity Platforms                                 │   │
│  │  sensor.wfm_zone_N_daily_usage   (gallons/day)   │   │
│  │  sensor.wfm_zone_N_flow_rate     (gal/min)       │   │
│  │  sensor.wfm_zone_N_status        (normal/leak/…) │   │
│  │  switch.wfm_zone_N_shutoff_enabled               │   │
│  │  switch.wfm_zone_N_alerts_enabled                │   │
│  │  button.wfm_zone_N_calibrate                     │   │
│  └──────┬───────────────────────────────────────────┘   │
│         │                                               │
│  ┌──────▼────────────────────────────────────────────┐  │
│  │  Custom Lovelace Card (water-flow-card.js)        │  │
│  │  Reads entity states via hass object              │  │
│  │  Shows: zone list, flow rates, daily usage chart  │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## Data Flow

### Normal Operation (polling loop)
```
Every 10s:
  Coordinator.async_refresh()
    → read hass.states["sensor.flume_flow"].state  (current flow rate)
    → for each monitored zone:
        read hass.states["binary_sensor.zone_N"].state  (on/off)
        if zone is ON:
            accumulate flow into zone.daily_usage
            if flow > zone.calibrated_flow * zone.threshold_multiplier:
                if zone.shutoff_enabled:
                    call hass.services.async_call("switch", "turn_off", zone.switch_entity)
                if zone.alerts_enabled:
                    call hass.services.async_call("notify", ...)
    → push updated data to all entities via async_write_ha_state()
```

### Calibration Flow
```
User presses button.wfm_zone_N_calibrate
    → ButtonEntity.async_press()
        1. Read current Flume flow (baseline check)
           if baseline > BACKGROUND_FLOW_THRESHOLD (e.g., 0.1 gal/min):
               fire persistent_notification "Other water detected — stop other water use first"
               abort
        2. Call hass.services.async_call("switch", "turn_on", zone.switch_entity)
        3. Wait STABILIZATION_DELAY (e.g., 30s) for flow to stabilize
        4. Sample Flume flow for SAMPLE_WINDOW (e.g., 10s), compute rolling average
        5. Store calibrated_flow in ConfigEntry.options[zone_id]["calibrated_flow"]
        6. Call hass.services.async_call("switch", "turn_off", zone.switch_entity)
        7. Fire persistent_notification "Zone N calibrated: X.X gal/min"
```

### Valve Discovery (Config Flow + Options Flow)
```
Initial setup (ConfigFlow):
    Step 1: User picks Flume sensor entity (EntitySelector, device_class=flow)
    Step 2: Integration scans EntityRegistry for binary_sensor entities
            that look like irrigation valves (user selects from list)
    Step 3: For each selected valve, find paired switch entity (for control)
    Result: ConfigEntry created with selected zones list

Adding valves later (OptionsFlow):
    Step 1: Re-scan EntityRegistry for binary_sensor entities
    Step 2: Show ALL found valves; pre-check already-monitored ones (read-only)
    Step 3: User checks new valves to add
    Result: ConfigEntry.options updated; existing zone calibration preserved
```

---

## State Persistence

### What needs to survive HA restarts
| Data | Storage | Why |
|------|---------|-----|
| Monitored zone list | `ConfigEntry.data` | Set at config flow time |
| Calibrated flow per zone | `ConfigEntry.options` | Updated by calibration button |
| Per-zone thresholds | `ConfigEntry.options` | Set in options flow |
| Per-zone shutoff/alert toggles | Entity state via `RestoreEntity` | User-controlled switches |
| Daily usage totals | `homeassistant.helpers.storage.Store` | Must survive restarts; resets at midnight |

### Daily reset
```python
# In coordinator __init__:
async_track_time_change(hass, self._midnight_reset, hour=0, minute=0, second=0)

async def _midnight_reset(self, now):
    for zone in self.zones:
        zone.daily_usage = 0.0
    self._store.async_delay_save(self._data_to_save, SAVE_DELAY)
```

---

## Build Order (Phase Dependencies)

```
Phase 1: Project scaffold + dev environment
    → custom_components/ structure, manifest.json, hacs.json
    → pytest setup with mock hass, fake Flume + valve entities
    → Basic coordinator skeleton (no logic yet)

Phase 2: Config flow + valve discovery
    → ConfigFlow: pick Flume sensor, discover + select valves
    → OptionsFlow: incremental valve add
    → ConfigEntry created; zones stored

Phase 3: Core entities + coordinator
    → All entity platforms registered
    → Coordinator polling loop
    → Daily usage accumulation + midnight reset
    → State persistence via Store

Phase 4: Calibration
    → ButtonEntity.async_press() calibration sequence
    → Background flow detection
    → Calibrated flow stored in options

Phase 5: Leak detection + auto-shutoff
    → Threshold logic in coordinator
    → Per-zone shutoff/alert toggles (SwitchEntity)
    → Alert notifications via HA notify service

Phase 6: Daily budget alerts
    → Threshold stored per zone
    → Alert fired when daily_usage > budget

Phase 7: Lovelace card
    → Lit 3.x + TypeScript + Rollup
    → Zone list with flow + daily usage
    → History chart (uses recorder statistics)
```

---

## Key Architectural Decisions

| Decision | Rationale |
|----------|-----------|
| Single DataUpdateCoordinator | All zones share one Flume reading; coordinator ensures consistency |
| ConfigEntry.options for calibration data | Survives restarts; editable via options flow without resetting the entry |
| Store for daily totals | Survives restarts; separate from options (changes frequently) |
| SwitchEntity for shutoff/alert toggles | Proper HA entity ownership; user can toggle from any HA UI |
| ButtonEntity for calibration | Standard HA pattern for triggering actions; visible in entity list |
