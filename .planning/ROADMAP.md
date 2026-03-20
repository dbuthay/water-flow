# Roadmap: Water Flow Monitor

## Overview

This integration is built in dependency order: the scaffold establishes the HACS-compliant structure and test harness before any logic exists; the config flow creates the ConfigEntry that all other components read; the coordinator and entities bring zones to life with real-time flow data and daily usage tracking; calibration establishes per-zone baselines; leak detection uses those baselines to protect against burst pipes; and the Lovelace card surfaces everything visually. Each phase delivers a coherent, independently verifiable capability.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Scaffold** - HACS-compliant integration skeleton with working pytest infrastructure (completed 2026-03-20)
- [ ] **Phase 2: Config Flow** - Setup UI discovers irrigation valves; user selects zones and configures per-zone options
- [ ] **Phase 3: Coordinator + Usage** - DataUpdateCoordinator polls Flume; per-zone daily usage sensors track and persist across restarts
- [ ] **Phase 4: Calibration** - Button-driven calibration workflow records per-zone baseline flow and stores it persistently
- [ ] **Phase 5: Leak Detection** - Coordinator detects flow anomalies, auto-shuts off valves, and fires HA notifications
- [ ] **Phase 6: Lovelace Card** - Custom dashboard card shows zone status, active flow rates, and daily usage

## Phase Details

### Phase 1: Scaffold
**Goal**: A HACS-installable integration skeleton that passes HACS validation and has a working pytest environment with mock HA entities
**Depends on**: Nothing (first phase)
**Requirements**: INFRA-01, INFRA-02
**Success Criteria** (what must be TRUE):
  1. Integration can be added as a custom HACS repository without validation errors
  2. Running `pytest` against the test suite completes without errors (even with no tests yet — environment is functional)
  3. Integration loads in a local HA instance without errors (empty config flow, no entities registered yet)
**Plans:** 1/1 plans complete
Plans:
- [ ] 01-01-PLAN.md — Integration skeleton, HACS metadata, and pytest infrastructure

### Phase 2: Config Flow
**Goal**: Users can install the integration, select their Flume sensor, pick which valves to monitor, and configure per-zone options — all through the HA UI with no YAML
**Depends on**: Phase 1
**Requirements**: SETUP-01, SETUP-02, SETUP-03, SETUP-04, SETUP-05, SETUP-06, SETUP-07
**Success Criteria** (what must be TRUE):
  1. User can complete initial setup by selecting the Flume sensor entity and choosing which discovered valve entities to monitor
  2. User can re-open integration options and add a newly available valve without any existing zone configuration being lost
  3. User can toggle auto-shutoff on or off for a specific zone from the options UI without removing that zone from monitoring
  4. User can toggle anomaly alerts on or off for a specific zone from the options UI independently of the auto-shutoff toggle
  5. User can set a custom leak detection threshold multiplier per zone (e.g., 1.5×) from the options UI
**Plans**: TBD

### Phase 3: Coordinator + Usage
**Goal**: The integration actively polls the Flume sensor and exposes per-zone daily water usage as HA sensor entities that persist correctly across restarts and midnight boundaries
**Depends on**: Phase 2
**Requirements**: USAGE-01, USAGE-02, USAGE-03
**Success Criteria** (what must be TRUE):
  1. A daily usage sensor entity appears in HA for each monitored zone, showing gallons accumulated since midnight
  2. After restarting HA mid-day, each zone's daily usage sensor resumes from the pre-restart total (not reset to zero)
  3. If HA was offline at midnight, daily usage totals reset correctly on next startup based on stored date — they do not retain yesterday's values
  4. When the Flume sensor reports unavailable or unknown, the integration marks itself unavailable rather than crashing or firing false events
**Plans**: TBD

### Phase 4: Calibration
**Goal**: Users can calibrate the expected flow rate for each monitored zone through a button in the HA UI, with the result stored persistently and surviving HA restarts
**Depends on**: Phase 3
**Requirements**: CALIB-01, CALIB-02, CALIB-03, CALIB-04, CALIB-05, CALIB-06
**Success Criteria** (what must be TRUE):
  1. A calibrate button entity appears in HA for each monitored zone; pressing it starts the calibration sequence
  2. If background water flow is detected before calibration starts, the user receives a warning and calibration does not proceed
  3. If the target zone is already running when calibration is triggered, calibration aborts without turning anything on or off
  4. After a successful calibration run, the recorded baseline flow rate is displayed to the user via an HA notification
  5. After an HA restart, the previously calibrated flow rate is still present and the zone does not require re-calibration
**Plans**: TBD

### Phase 5: Leak Detection
**Goal**: The integration continuously monitors active zones against their calibrated baselines and automatically shuts off valves and fires alerts when anomalous flow is detected
**Depends on**: Phase 4
**Requirements**: DETECT-01, DETECT-02, DETECT-03, DETECT-04, DETECT-05
**Success Criteria** (what must be TRUE):
  1. When a running zone's flow exceeds its calibrated baseline × threshold and auto-shutoff is enabled, the integration turns the valve off via HA service call
  2. When a running zone's flow exceeds the threshold and alerts are enabled, the user receives an HA notification identifying the zone and showing measured vs. expected flow
  3. Immediately after a valve turns on, the integration does not evaluate for leaks during the configurable ramp-up window (no false positives at zone start)
  4. When the Flume sensor becomes unavailable while a zone is active, no shutoff or alert is triggered — the integration handles the missing data gracefully
**Plans**: TBD

### Phase 6: Lovelace Card
**Goal**: A custom Lovelace card gives users a single-glance view of all monitored zones with their current state, active flow rate, and daily usage
**Depends on**: Phase 5
**Requirements**: CARD-01, CARD-02, CARD-03
**Success Criteria** (what must be TRUE):
  1. The Lovelace card can be added to a dashboard and displays all monitored zones with their current state (idle / running / leak detected)
  2. For any zone currently running, the card shows the current flow rate in real time
  3. The card shows today's water usage total for each zone
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Scaffold | 1/1 | Complete    | 2026-03-20 |
| 2. Config Flow | 0/? | Not started | - |
| 3. Coordinator + Usage | 0/? | Not started | - |
| 4. Calibration | 0/? | Not started | - |
| 5. Leak Detection | 0/? | Not started | - |
| 6. Lovelace Card | 0/? | Not started | - |
