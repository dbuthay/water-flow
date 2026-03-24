# Requirements: Water Flow Monitor

**Defined:** 2026-03-19
**Core Value:** When a valve is running and water flow spikes beyond the expected rate, the system shuts it off automatically — protecting against burst pipes and unexpected leaks.

## v1 Requirements

### Setup & Discovery (SETUP)

- [x] **SETUP-01**: User can select the Flume flow sensor entity from a list of HA entities during initial setup
- [x] **SETUP-02**: Integration scans HA entity registry for irrigation valve entities and presents them as candidates
- [x] **SETUP-03**: User selects which valves to monitor (not all discovered valves need to be monitored)
- [x] **SETUP-04**: User can re-run valve discovery via integration options to add newly available valves without losing existing zone configuration
- [x] **SETUP-05**: User can enable or disable auto-shutoff per monitored valve at any time (without removing the valve from monitoring)
- [x] **SETUP-06**: User can enable or disable anomaly alerts per monitored valve at any time (to temporarily silence a zone)
- [x] **SETUP-07**: User can configure the leak detection threshold multiplier per zone (e.g., 1.5 = shut off if flow exceeds 150% of calibrated baseline)

### Calibration (CALIB)

- [x] **CALIB-01**: User can trigger calibration for a monitored zone via a button entity in the HA UI
- [x] **CALIB-02**: Integration checks for background water flow before starting calibration and warns the user if flow is detected above a minimum threshold
- [x] **CALIB-03**: Integration aborts calibration if the target zone is already running (active schedule or manual activation)
- [x] **CALIB-04**: Integration turns on the valve, waits for flow to stabilize (configurable delay, default 30s), then samples Flume flow over a window to compute a reliable average
- [x] **CALIB-05**: Calibrated flow rate is stored persistently and survives HA restarts
- [x] **CALIB-06**: Integration turns the valve back off after calibration completes and notifies the user of the recorded flow rate

### Leak Detection (DETECT)

- [x] **DETECT-01**: Integration monitors flow rate whenever a valve is active and compares it against the zone's calibrated baseline × threshold multiplier
- [x] **DETECT-02**: Integration skips leak evaluation for a configurable number of polls after a valve turns on (ramp-up period to avoid false positives)
- [x] **DETECT-03**: When flow exceeds the threshold and auto-shutoff is enabled for that zone, integration turns off the valve via HA service call
- [x] **DETECT-04**: When a leak is detected and alerts are enabled for that zone, integration fires an HA notification identifying the zone and the measured vs. expected flow
- [x] **DETECT-05**: Integration handles Flume sensor being unavailable or returning unknown state without crashing or triggering false leak events

### Usage Tracking (USAGE)

- [x] **USAGE-01**: Integration exposes a sensor entity per monitored zone showing daily water usage (gallons accumulated since midnight)
- [x] **USAGE-02**: Daily usage totals persist across HA restarts and only reset at midnight (not on restart)
- [x] **USAGE-03**: If HA was offline at midnight, daily totals reset correctly on next startup based on stored date comparison

### Lovelace Card (CARD)

- [x] **CARD-01**: Custom Lovelace card displays all monitored zones with their current state (idle / running / leak detected)
- [x] **CARD-02**: Card shows the current flow rate for each active zone
- [x] **CARD-03**: Card shows today's water usage per zone

### Development Infrastructure (INFRA)

- [x] **INFRA-01**: Integration is installable via HACS as a custom repository (valid manifest.json, hacs.json, semver tags)
- [x] **INFRA-02**: pytest test suite with pytest-homeassistant-custom-component covers coordinator logic, calibration sequence, leak detection, and daily usage tracking using mock Flume and valve entities

## v2 Requirements

### Usage Tracking

- **USAGE-04**: User can set a daily water budget per zone; integration fires an alert when the daily budget is exceeded

### Lovelace Card

- **CARD-04**: Card shows historical usage trend over time (requires recorder statistics integration)

### Development Infrastructure

- **INFRA-03**: Local HA dev configuration with template entities for manual UI/config flow testing
- **INFRA-04**: GitHub Actions CI runs pytest on every push

## Out of Scope

| Feature | Reason |
|---------|--------|
| Irrigation scheduling | Out of scope — use Rachio integration or irrigation_unlimited |
| Multiple Flume sensors | Single-sensor assumption for v1; complexity not justified |
| Mobile push notifications | HA's notify platform handles this — no custom work needed |
| Cloud sync / remote access | HA already provides this |
| ML-based anomaly detection | Simple threshold sufficient for v1 |
| Water billing estimates | Utility rates and unit conversion out of scope |
| YAML-based configuration | Config flow UI is the standard and user preference |

## Traceability

Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| SETUP-01 | Phase 2 | Complete |
| SETUP-02 | Phase 2 | Complete |
| SETUP-03 | Phase 2 | Complete |
| SETUP-04 | Phase 2 | Complete |
| SETUP-05 | Phase 2 | Complete |
| SETUP-06 | Phase 2 | Complete |
| SETUP-07 | Phase 2 | Complete |
| CALIB-01 | Phase 4 | Complete |
| CALIB-02 | Phase 4 | Complete |
| CALIB-03 | Phase 4 | Complete |
| CALIB-04 | Phase 4 | Complete |
| CALIB-05 | Phase 4 | Complete |
| CALIB-06 | Phase 4 | Complete |
| DETECT-01 | Phase 5 | Complete |
| DETECT-02 | Phase 5 | Complete |
| DETECT-03 | Phase 5 | Complete |
| DETECT-04 | Phase 5 | Complete |
| DETECT-05 | Phase 5 | Complete |
| USAGE-01 | Phase 3 | Complete |
| USAGE-02 | Phase 3 | Complete |
| USAGE-03 | Phase 3 | Complete |
| CARD-01 | Phase 6 | Complete |
| CARD-02 | Phase 6 | Complete |
| CARD-03 | Phase 6 | Complete |
| INFRA-01 | Phase 1 | Complete |
| INFRA-02 | Phase 1 | Complete |

**Coverage:**
- v1 requirements: 26 total
- Mapped to phases: 26
- Unmapped: 0

---
*Requirements defined: 2026-03-19*
*Last updated: 2026-03-19 after roadmap creation*
