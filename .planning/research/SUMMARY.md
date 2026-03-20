# Project Research Summary

**Project:** Water Flow Monitor (Home Assistant Custom Integration)
**Domain:** Smart home / HA custom integration + HACS + Lovelace card
**Researched:** 2026-03-19
**Confidence:** HIGH

## Executive Summary

This project is a Home Assistant custom integration that bridges an existing Flume water flow sensor with irrigation valve entities to provide per-zone flow monitoring, anomaly detection, and automated shutoff. The recommended approach follows modern HA patterns: a `DataUpdateCoordinator` as the single polling hub, `ConfigFlow` + `OptionsFlow` for YAML-free setup, `ConfigEntry.runtime_data` for coordinator storage, and `ConfigEntry.options` for persisting calibration data across restarts. A custom Lovelace card built with Lit 3.x + TypeScript + Rollup rounds out the user experience. All of these patterns are well-documented with HIGH confidence — this is a well-trodden path in the HA custom integration ecosystem.

The feature set has a clear dependency chain: valve discovery enables zone selection, which enables calibration, which enables leak detection, which enables auto-shutoff and alerts. Daily usage tracking is independent and can start at zone selection. This dependency order directly dictates the phase structure. Rachio 3 is the reference bar for UX — targeting per-zone daily totals, calibration-based anomaly detection, and granular per-zone shutoff/alert toggles. Scheduling and multi-sensor support are intentionally out of scope for v1.

The top risks are architectural, not algorithmic: storing calibration data in-memory (lost on restart), the options flow overwriting existing calibration when adding new zones, and the coordinator polling before a valve has physically opened (producing false readings). All three are fully preventable with patterns documented in PITFALLS.md — the key is designing the storage layer and options flow merge strategy correctly in Phase 2 before any calibration or detection logic is written.

---

## Key Findings

### Recommended Stack

The integration uses Python 3.12+ targeting HA 2024.1+. The coordinator pattern (`DataUpdateCoordinator`) is the right choice because all zones share one Flume reading — a single poll pushes state to all entities simultaneously. `ConfigEntry.runtime_data` (available since HA 2024.4) replaces the legacy `hass.data[DOMAIN]` pattern and should be used from day one. For state persistence, calibration config lives in `ConfigEntry.options`, while daily usage totals use `homeassistant.helpers.storage.Store` (separate file, handles frequent writes safely).

The Lovelace card stack is Lit 3.x + TypeScript + Rollup — the same stack used by HA core cards, which means the ecosystem, bundling conventions, and component lifecycle patterns are stable and well-documented. Testing uses `pytest-homeassistant-custom-component` with the `hass` fixture to run integration tests against a real lightweight HA instance.

**Core technologies:**
- Python 3.12+ / HA 2024.1+: Integration runtime — required by current HA stable
- DataUpdateCoordinator: Single poll hub — prevents N×Flume reads, ensures entity consistency
- ConfigFlow + OptionsFlow: UI-based setup — modern HA standard, no YAML required
- ConfigEntry.options: Calibration storage — persists across restarts, editable via options flow
- homeassistant.helpers.storage.Store: Daily usage totals — handles frequent writes, restart-safe
- Lit 3.x + TypeScript + Rollup: Lovelace card — HA ecosystem standard, single-file output
- pytest-homeassistant-custom-component: Integration testing — real HA instance in tests

### Expected Features

The feature dependency chain is the key planning constraint: every layer depends on the one below it. Calibration cannot exist without zone selection; leak detection cannot exist without calibration; auto-shutoff cannot exist without leak detection. The roadmap must respect this order.

**Must have (table stakes):**
- Per-zone current flow display — users need to see what a zone is doing right now
- Daily usage totals per zone — the #1 question after "is my irrigation working?"
- Leak / burst detection + auto-shutoff — core safety feature; Rachio and Flume both provide this
- Zone calibration (expected flow rate) — required before any anomaly detection is meaningful
- Enable/disable shutoff per zone — essential override for non-standard zones
- Notification on leak/anomaly — users can't watch HA all day
- Config flow setup (no YAML) — modern HA standard; users expect it
- Incremental zone add/remove — system grows over time without losing existing calibration

**Should have (differentiators):**
- Background flow detection during calibration — prevents false calibration if other water is running
- Per-zone daily budget alerts — Rachio has this; users value it for conservation
- Custom Lovelace card with usage history — visualizes zone flow trends over time
- Valve discovery from HA entity registry — avoids manual entity_id typing
- Separate per-valve shutoff AND alert toggles — more granular than Rachio
- Flow rate stability detection during calibration — rolling average/variance check before recording

**Defer (v2+):**
- Irrigation scheduling — use Rachio integration or irrigation_unlimited
- Multi-Flume sensor support — complexity not worth it for v1
- Historical anomaly ML — simple threshold is sufficient; over-engineering for v1
- Water meter billing estimates — different units and utility rates, out of scope

### Architecture Approach

The integration has a clear hub-and-spoke architecture. The `WaterFlowCoordinator` is the hub: it polls the Flume sensor every 10 seconds, evaluates all active zone states, runs leak detection, accumulates daily usage, and triggers shutoff/notifications. All entities are spokes that read from coordinator data and write their state via `async_write_ha_state()`. The Lovelace card sits at the outer layer, reading entity states through the standard `hass` object. The calibration flow is a separate async sequence triggered by a `ButtonEntity`, not part of the polling loop.

**Major components:**
1. WaterFlowCoordinator — polls Flume, evaluates all zone states, runs detection, accumulates usage
2. Entity platforms (sensor, switch, button) — expose coordinator data as HA entities
3. ConfigFlow + OptionsFlow — setup wizard + incremental zone management
4. Store — persists daily usage totals across restarts, handles midnight reset
5. Lovelace card (water-flow-card.js) — zone list, flow rates, daily usage visualization

### Critical Pitfalls

1. **Options flow overwrites existing calibration** — merge into existing options dict instead of replacing it; always do `existing = dict(entry.options); existing["zones"] = new_zones` before returning from options flow. Affects Phase 2.
2. **Coordinator reads before valve physically opens** — add configurable `ZONE_START_DELAY` (default 5s) after zone turns on before reading flow; skip first N polls after zone state changes to ON. Affects Phases 3, 4, and 5.
3. **Calibration data lost on HA restart** — store calibration in `ConfigEntry.options`, never in-memory. Daily totals go in `Store` with a startup date check to handle missed midnight resets. Affects Phases 2, 3, and 4.
4. **Flume sensor unavailable state crashes coordinator** — always guard against `unavailable`/`unknown` state; propagate `UpdateFailed` so HA marks the integration unavailable rather than crashing. Affects Phase 3.
5. **Entity unique_id format changes create duplicates** — set unique_id as `f"{entry.entry_id}_{zone_id}_{type}"` from day one and never change the format. Affects Phase 3.

---

## Implications for Roadmap

Based on research, the architecture file already contains a well-reasoned 7-phase build order that respects feature dependencies. The roadmap should follow this structure closely.

### Phase 1: Project Scaffold + Dev Environment
**Rationale:** Foundation must come first. HACS compliance requirements (manifest.json, hacs.json, semver tags, repo structure) need to be correct from day one — retroactive fixes create churn. Testing infrastructure must be in place before logic is written.
**Delivers:** Installable (but empty) integration structure, pytest environment with mock HA, HACS validation passing
**Addresses:** HA config flow setup requirement (infrastructure for it)
**Avoids:** P7 (HACS submission failures), P1 (establishes async pattern from start)

### Phase 2: Config Flow + Valve Discovery
**Rationale:** The entire feature chain depends on zone selection. Config flow must be built before any entities or logic, because it creates the ConfigEntry that everything else reads. Options flow merge strategy (P3 pitfall) must be designed correctly here — before calibration data exists to be accidentally wiped.
**Delivers:** Working setup UI, valve discovery from EntityRegistry, ConfigEntry with zone list, incremental zone add/remove
**Addresses:** Config flow setup (table stakes), incremental zone add/remove (table stakes), valve discovery (differentiator)
**Avoids:** P3 (options flow destroy), P2 (storage design established here)

### Phase 3: Core Entities + Coordinator
**Rationale:** With zones configured, the coordinator polling loop and entity platforms can be built. Daily usage accumulation and state persistence are included here because they are tightly coupled to coordinator startup — the midnight reset check (P9) and storage initialization happen at coordinator init.
**Delivers:** All entity platforms registered with stable unique_ids, coordinator polling loop, daily usage accumulation, midnight reset with restart recovery, Flume unavailability handling
**Addresses:** Per-zone current flow display (table stakes), daily usage totals (table stakes)
**Avoids:** P1 (async-only), P4 (zone start delay), P5 (Flume unavailable guard), P6 (unique_id stability), P9 (missed midnight reset)

### Phase 4: Calibration
**Rationale:** Calibration is a prerequisite for leak detection. The calibration sequence (turn on valve, wait for stabilization, sample, store) is a distinct async workflow separate from the polling loop, best implemented as its own phase.
**Delivers:** ButtonEntity calibration sequence, background flow detection before calibration starts, flow stabilization wait, calibrated_flow stored in ConfigEntry.options
**Addresses:** Zone calibration (table stakes), background flow detection during calibration (differentiator), flow rate stability detection (differentiator)
**Avoids:** P2 (calibration stored in options), P4 (stabilization delay), P10 (zone already running check)

### Phase 5: Leak Detection + Auto-Shutoff
**Rationale:** Depends on calibrated baseline from Phase 4. This is the core safety feature — threshold comparison, per-zone shutoff/alert toggles as SwitchEntities, and notification dispatch.
**Delivers:** Threshold logic in coordinator, SwitchEntities for shutoff/alert toggles per zone, HA notify integration for anomaly alerts
**Addresses:** Leak/burst detection + auto-shutoff (table stakes), notification on leak (table stakes), enable/disable shutoff per zone (table stakes), separate shutoff AND alert toggles (differentiator)
**Avoids:** P4 (skip first N polls after zone start)

### Phase 6: Daily Budget Alerts
**Rationale:** Depends on daily usage tracking from Phase 3. Lightweight addition — per-zone budget threshold stored in options, alert fired when daily_usage exceeds budget.
**Delivers:** Per-zone budget thresholds in options flow, alert notification when budget exceeded
**Addresses:** Per-zone daily budget alerts (differentiator)

### Phase 7: Lovelace Card
**Rationale:** Final layer. Depends on all entities being registered and stable. Card reads entity states; building it last means the entity surface area won't change underneath it. Cache-busting strategy (P8) must be addressed at build time.
**Delivers:** Lit 3.x + TypeScript + Rollup card bundled as single JS, zone list with flow rates and daily usage, history chart using recorder statistics, HACS resource management
**Addresses:** Custom Lovelace card with history (differentiator)
**Avoids:** P8 (card caching — version query param in resource URL)

### Phase Ordering Rationale

- Phases 1-2 establish the structural foundation (file layout, config entries, storage design) before any logic exists — mistakes here are expensive to fix later
- Phase 3 builds the coordinator before calibration because the coordinator's startup behavior (storage init, date check) is a prerequisite for reliable calibration storage
- Phases 4-5 respect the hard dependency: calibration must exist before leak detection
- Phase 6 is a thin addition on top of Phase 3's daily tracking infrastructure
- Phase 7 is last because it is purely presentational and depends on all entity IDs being stable

### Research Flags

Phases with standard, well-documented patterns (skip research-phase):
- **Phase 1:** HA integration file structure is stable and extensively documented
- **Phase 2:** ConfigFlow/OptionsFlow patterns are well-documented in HA developer docs
- **Phase 3:** DataUpdateCoordinator pattern is the HA standard; coordinator docs are thorough
- **Phase 5:** SwitchEntity and notify service integration are standard HA patterns
- **Phase 7:** Lit 3.x + Rollup card development is well-documented in HA frontend examples

Phases that may benefit from deeper research during planning:
- **Phase 3 (statistics/recorder API):** The `StatisticsHelper` / `recorder` API for persisting daily totals has MEDIUM confidence — current API shape should be verified before implementation
- **Phase 2 (EntityRegistry discovery):** Discovery patterns for pairing binary_sensor + switch entities may vary by irrigation controller integration — worth a targeted research pass

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All core patterns (Coordinator, ConfigEntry.runtime_data, Lit+Rollup) verified against HA stable APIs and ecosystem standards |
| Features | HIGH | Benchmarked against Rachio 3, Flume 2, HA Rachio integration, irrigation_unlimited — feature expectations are well-established |
| Architecture | HIGH | Component boundaries and data flow follow standard HA patterns; build order validated against feature dependencies |
| Pitfalls | HIGH | 10 specific, actionable pitfalls with prevention code — drawn from HA custom integration common failure modes |

**Overall confidence:** HIGH

### Gaps to Address

- **Statistics/recorder API for daily totals:** MEDIUM confidence — the `homeassistant.helpers.storage.Store` approach is high-confidence, but if recorder statistics are needed for the history chart in Phase 7, the current recorder API shape should be verified against HA 2024.x docs before that phase begins.
- **EntityRegistry discovery pairing (binary_sensor + switch):** The pattern for finding a switch entity that pairs with a binary_sensor for the same valve depends on how the upstream irrigation controller integration names its entities. This is integration-specific and should be validated against the actual target controller (e.g., Rachio, OpenSprinkler) during Phase 2.
- **Flume sensor entity_id format:** The exact entity_id and device_class of the Flume flow sensor should be confirmed against the current Flume HA integration before the config flow EntitySelector filter is written.

---

## Sources

### Primary (HIGH confidence)
- Home Assistant Developer Documentation — ConfigFlow, OptionsFlow, DataUpdateCoordinator, ConfigEntry.runtime_data, entity platforms, SwitchEntity, ButtonEntity
- Home Assistant HACS documentation — manifest.json requirements, hacs.json, HACS validation rules
- Lit 3.x documentation — LitElement, reactive properties, shadow DOM, web component lifecycle
- pytest-homeassistant-custom-component — test fixtures, hass instance, config entry testing

### Secondary (MEDIUM confidence)
- Home Assistant community forums / HACS default integrations — options flow merge pattern, entity unique_id stability conventions
- Rachio 3 product documentation — calibration UX, usage history, zone management reference
- HA irrigation_unlimited HACS integration — complexity tolerance reference for HA users

### Tertiary (LOW confidence)
- StatisticsHelper / recorder API — needs verification against current HA 2024.x API shape before Phase 3/7 implementation

---
*Research completed: 2026-03-19*
*Ready for roadmap: yes*
