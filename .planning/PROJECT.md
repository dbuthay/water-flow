# Water Flow Monitor

## What This Is

A Home Assistant custom integration (distributed via HACS) that monitors water usage across irrigation zones by bridging a Flume water flow sensor with an irrigation controller. It detects leaks, tracks daily per-zone usage, and provides a custom Lovelace dashboard card.

## Core Value

When a valve is running and water flow spikes beyond the expected rate, the system shuts it off automatically — protecting against burst pipes and unexpected leaks.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Integration discovers available irrigation valves from HA and presents them as candidates during initial setup
- [ ] User selects which valves to monitor (not all zones need to be monitored)
- [ ] User can re-run valve discovery later (via integration options) to add newly available valves without losing existing valve configuration
- [ ] User can calibrate expected flow for each monitored zone via a button in the HA UI
- [ ] Calibration detects and warns if background water flow exists before starting
- [ ] Integration auto-shuts off a valve if flow exceeds a configurable threshold (per zone)
- [ ] User can disable auto-shutoff per valve at any time (without removing it from monitoring)
- [ ] User can disable alerting per valve at any time (e.g., to silence a known anomaly temporarily)
- [ ] Integration tracks daily water usage per zone as HA sensor entities
- [ ] User can set a daily water budget per zone with alerts when exceeded
- [ ] Custom Lovelace card shows zone status, current flow, and daily usage history
- [ ] Integration is configured entirely through the HA config flow UI (no YAML)
- [ ] Integration is installable via HACS as a custom repository

### Out of Scope

- Mobile app — HA's existing mobile app handles notifications
- YAML-based configuration — config flow UI covers all setup
- Multi-Flume sensor support — single sensor for whole house assumed
- Controlling irrigation schedules — only monitors and reacts, does not schedule

## Context

- **Flume sensor**: Already integrated in HA, exposes a numeric sensor for whole-house flow rate (gallons/min or similar). Since it measures total house flow, calibration must happen when no other water is running. The integration will detect baseline flow before calibration starts and warn if it's non-zero.
- **Irrigation controller**: Already in HA, each zone exposed as a binary sensor (on/off state). During setup the integration discovers all available valve entities and lets the user pick which to monitor. The integration will also need to send turn-off commands, so zones need switch entities or service calls.
- **Calibration flow**: Button-driven — integration turns on the valve, waits for flow to stabilize, reads Flume average, saves as the zone's baseline. Threshold for shutoff is configurable per zone (e.g., "shut off if flow > 150% of baseline").
- **Testing approach**: Development uses pytest + pytest-homeassistant-custom-component for logic tests and a local HA dev instance with fake entities for UI/config flow testing. Real hardware only for final validation.
- **Inspiration**: Rachio irrigation controller — known for smart water monitoring, leak detection, and usage history.

## Constraints

- **Tech stack**: Python, Home Assistant custom integration structure (custom_components/), HACS-compatible
- **HA version**: Must support current HA stable (2024.x+)
- **Flume assumption**: Single Flume sensor; calibration requires exclusive water use during the process
- **Hardware**: Flume flow sensor + irrigation controller both pre-integrated in HA before this integration is installed

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Custom integration (not add-on) | Add-ons are separate Docker containers; an integration runs inside HA and can directly read/write HA entities | — Pending |
| Config flow UI over YAML | User preference; also the modern HA standard for custom integrations | — Pending |
| Per-zone configurable shutoff threshold | Different zones (drip vs. spray) have very different normal flow rates | — Pending |
| Per-valve shutoff/alert toggles | User needs to temporarily silence a zone without removing it from monitoring | — Pending |
| Config flow + options flow | Initial setup via config flow; adding valves later via options flow — incremental, non-destructive | — Pending |
| Mocked dev environment | Allows full iteration without risk to real irrigation system | — Pending |

---
*Last updated: 2026-03-19 after initialization*
