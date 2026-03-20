# Feature Landscape: Irrigation Water Monitoring

**Domain:** Smart irrigation water monitoring (Home Assistant custom integration)
**Reference systems:** Rachio 3, Flume 2, RainBird, HA irrigation_unlimited

---

## Reference Systems

| System | Relevance |
|--------|-----------|
| **Rachio 3** | Gold standard UX for smart irrigation — leak detection, usage history, zone calibration |
| **Flume 2** | Whole-house flow sensor; already in HA. Reference for flow-based leak detection approach |
| **RainBird ESP-Me** | Traditional controller — shows what features matter at the hardware layer |
| **HA Rachio integration** | Shows what HA users expect from a polished irrigation integration |
| **HA irrigation_unlimited** | Popular HACS integration — shows what HA users tolerate in config complexity |

---

## Table Stakes

Features users expect. Missing these makes the integration feel incomplete.

| Feature | Why Expected | Complexity | Dependency |
|---------|--------------|------------|------------|
| Per-zone current flow display | Users need to see what a zone is actually doing right now | Low | Flume sensor + active zone detection |
| Daily usage totals per zone | The #1 question after "is my irrigation working?" | Medium | Persistent storage across restarts |
| Leak / burst detection + auto-shutoff | Core safety feature — Rachio and Flume both do this | Medium | Calibrated baseline per zone |
| Zone calibration (expected flow rate) | Required before any anomaly detection is meaningful | Medium | Valve control + Flume reading |
| Enable/disable shutoff per zone | Users need override capability — essential for non-standard zones | Low | Per-zone config storage |
| Notification on leak/anomaly | Users can't watch HA all day | Low | HA notify service |
| HA config flow setup (no YAML) | Modern HA standard; users expect it | Medium | Config flow + options flow |
| Incremental zone add/remove | System grows over time; can't lose existing calibration | Medium | Options flow |

---

## Differentiators

Features that would make this stand out compared to manual HA automations.

| Feature | Value | Complexity | Notes |
|---------|-------|------------|-------|
| Background flow detection during calibration | Prevents false calibration if other water is running | Low-Medium | Check Flume baseline before turning on valve |
| Per-zone daily budget alerts | Rachio has this; users love it for conservation | Low | Threshold stored per zone in config |
| Custom Lovelace card with history | Visualization of zone flow trends over time | High | Requires Lit card + statistics integration |
| Valve discovery from HA entity registry | Avoids manual entity_id typing — much better UX | Medium | EntitySelector or registry scan |
| Per-valve shutoff AND alert toggles independently | More granular than Rachio (shutoff-only or alerts-only) | Low | Two boolean flags per zone |
| Flow rate stability detection in calibration | Wait for flow to stabilize before recording baseline | Medium | Rolling average / variance check |

---

## Anti-Features

Things deliberately NOT building.

| Feature | Why Excluded |
|---------|-------------|
| Irrigation scheduling | Out of scope — use Rachio integration or irrigation_unlimited |
| Multi-Flume sensor support | Complexity not worth it for v1; single sensor assumed |
| Mobile push notifications | HA's existing notify platform handles this |
| Cloud sync / remote access | HA already handles this |
| Historical anomaly ML | Over-engineering for v1; simple threshold is sufficient |
| Water meter billing estimates | Different units, utility rates — out of scope |

---

## Feature Dependencies

```
Valve discovery
    └── Zone selection (can't select what isn't discovered)
            └── Calibration (can't calibrate unselected zones)
                    └── Leak detection (needs calibrated baseline)
                            └── Auto-shutoff (needs leak detection)
                            └── Anomaly alerts (needs leak detection)

Daily usage tracking (independent of calibration — starts at zone selection)
    └── Daily budget alerts (needs usage tracking)

Custom Lovelace card (depends on all entities being registered)
```

---

## Rachio-Specific Insights

- **Calibration approach**: Rachio uses "catch cup" physical calibration for precipitation rate. Our approach (flow sensor timing) is actually more accurate for flow-rate anomaly detection.
- **Leak detection**: Rachio Smart Hose Timer detects flow when no zone is scheduled. Our approach is flow-rate anomaly during active zone — different but complementary.
- **Usage history**: Rachio shows gallons per zone per run and per month. Target parity for daily totals.
- **Zone skip**: Rachio lets you skip a zone without removing it. Our per-valve shutoff toggle serves this purpose.
