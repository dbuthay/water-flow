---
phase: 06-lovelace-card
plan: 01
subsystem: ui
tags: [lovelace, web-component, javascript, static-path, home-assistant]

# Dependency graph
requires:
  - phase: 05-leak-detection
    provides: ZoneStatusSensor with idle/running/leak_detected states that the card discovers
  - phase: 03-coordinator-usage
    provides: sensor entity naming pattern (sensor.irrigation_monitor_{zone_slug}_{type})
provides:
  - Lovelace card JS file at custom_components/irrigation_monitor/www/irrigation-monitor-card.js
  - Static path registration in async_setup_entry serving the card at /local/irrigation-monitor-card.js
  - Pytest coverage confirming static path registration (StaticPathConfig + async_register_static_paths)
affects: []

# Tech tracking
tech-stack:
  added:
    - homeassistant.components.http.StaticPathConfig (HA 2024.7+ static path API)
    - Vanilla HTMLElement Web Component (no Lit/TypeScript/Rollup)
  patterns:
    - Static path registration in async_setup_entry with try/except double-registration guard
    - TDD: test stubs written RED first, then GREEN implementation
    - XSS protection via _escapeHtml() helper for innerHTML template literals

key-files:
  created:
    - custom_components/irrigation_monitor/www/irrigation-monitor-card.js
    - tests/test_card_setup.py
  modified:
    - custom_components/irrigation_monitor/__init__.py

key-decisions:
  - "Use async_register_static_paths (plural, async) with StaticPathConfig -- NOT deprecated register_static_path (singular, sync) removed in HA 2024.7+"
  - "Try/except guards double-registration when integration is reloaded with same entry"
  - "Vanilla HTMLElement (no Lit/TypeScript/build step) per CONTEXT.md locked decision"
  - "Zone auto-discovery scans hass.states for sensor.*_status with state in idle/running/leak_detected"
  - "XSS protection: _escapeHtml() prevents injection from entity friendly_name in innerHTML"

patterns-established:
  - "Static path registration pattern: Path(__file__).parent / www / filename.js + StaticPathConfig"
  - "Card zone discovery: filter hass.states by _status suffix + valid state values, derive siblings by prefix"

requirements-completed: [CARD-01, CARD-02, CARD-03]

# Metrics
duration: 2min
completed: 2026-03-24
---

# Phase 6 Plan 01: Lovelace Card Summary

**Vanilla HTMLElement Lovelace card auto-discovering irrigation zones from hass.states, served via StaticPathConfig at /local/irrigation-monitor-card.js**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-24T06:47:20Z
- **Completed:** 2026-03-24T06:50:06Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Static path registration in `async_setup_entry` using `StaticPathConfig` + `async_register_static_paths` (current HA 2024.7+ API)
- Complete 222-line vanilla Web Component card with zone discovery, state-colored tiles, flow rate, and daily usage display
- 45 tests passing (43 existing + 2 new card tests): `test_www_file_exists` and `test_static_path_registered`

## Task Commits

Each task was committed atomically:

1. **Task 1: Wave 0 test stubs + static path registration in __init__.py** - `a716cd9` (feat)
2. **Task 2: Complete Lovelace card JS implementation** - `ded556c` (feat)

**Plan metadata:** (docs commit follows)

_Note: Task 1 used TDD -- test stubs written first (RED), then implementation (GREEN)_

## Files Created/Modified

- `custom_components/irrigation_monitor/__init__.py` - Added `StaticPathConfig` import and `async_register_static_paths` call in `async_setup_entry`
- `custom_components/irrigation_monitor/www/irrigation-monitor-card.js` - Complete Lovelace card (222 lines): `IrrigationMonitorCard` class with zone discovery, tile rendering, CSS grid layout, state icons/colors, XSS protection
- `tests/test_card_setup.py` - Two tests: `test_www_file_exists` (file existence) and `test_static_path_registered` (mocked HTTP call assertion)

## Decisions Made

- Used `async_register_static_paths` (plural, async) with `StaticPathConfig` per RESEARCH.md recommendation -- the legacy `register_static_path` (singular, sync) is removed in HA 2024.7+
- Try/except in `async_setup_entry` guards against double-registration if the integration is reloaded
- `_escapeHtml()` method prevents XSS from entity `friendly_name` attributes being interpolated into `innerHTML` template literals
- Card uses `<ha-icon>` elements with MDI icon names rather than emoji -- integrates with HA theming system
- Window.customCards push placed before `customElements.define` per HA convention for card picker visibility

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

After installing the integration, users must manually add a Lovelace resource:
- URL: `/local/irrigation-monitor-card.js`
- Type: `JavaScript Module`

This step makes the browser load the card JS. The static path registration only makes the file *servable* -- Lovelace resources tell the frontend to `<script type="module">` load it. HACS can automate this for standalone frontend card repos; for integration-bundled cards, manual setup is required.

## Known Stubs

None - the card JS and Python registration are fully wired. Zone discovery works from live `hass.states`. No placeholder data.

## Next Phase Readiness

Phase 6 Plan 01 is the final plan of the final phase. The integration is complete:
- Config flow, options flow, coordinator, sensors, buttons, calibration, leak detection, and Lovelace card are all implemented and tested
- 45 tests pass with no regressions
- The card is ready for use once the user adds the Lovelace resource URL

---
*Phase: 06-lovelace-card*
*Completed: 2026-03-24*
