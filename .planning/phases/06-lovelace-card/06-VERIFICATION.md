---
phase: 06-lovelace-card
verified: 2026-03-24T07:30:00Z
status: passed
score: 7/7 must-haves verified
re_verification: false
human_verification:
  - test: "Visual card rendering in running HA"
    expected: "Zones appear in responsive grid tiles; idle=grey, running=blue, leak=red; flow rate and daily usage displayed"
    why_human: "Browser DOM / Web Component rendering cannot be verified programmatically; user confirmed working in real HA instance"
---

# Phase 6: Lovelace Card Verification Report

**Phase Goal:** A custom Lovelace card gives users a single-glance view of all monitored zones with their current state, active flow rate, and daily usage
**Verified:** 2026-03-24T07:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## URL Deviation Note (Plan vs. Implementation)

The PLAN frontmatter states the static path should be `/local/irrigation-monitor-card.js`. The actual implementation registers `/irrigation_monitor/irrigation-monitor-card.js` instead. This is an intentional and correct deviation: HA's `/local/` path is reserved for the config `www/` directory and would return 404 for integration-bundled assets. The `/irrigation_monitor/` prefix avoids this conflict. The test asserts the actual URL, the README documents it correctly, and the user confirmed the card works in a real HA instance. All truths below are evaluated against the actual implementation.

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | JS card file exists at `www/irrigation-monitor-card.js` | VERIFIED | File present, 222 lines |
| 2 | Static path registration serves the JS file at runtime | VERIFIED | `async_setup` calls `async_register_static_paths` with `StaticPathConfig("/irrigation_monitor/irrigation-monitor-card.js", ...)` |
| 3 | Card auto-discovers zones by scanning `hass.states` for `sensor.*_status` entities | VERIFIED | `_discoverZones` filters by `startsWith("sensor.")`, `endsWith("_status")`, state in `["idle","running","leak_detected"]` |
| 4 | Each zone tile shows name, state icon+color, flow rate, and daily usage | VERIFIED | `_renderTile` emits `.name`, `.icon`, `.flow`, `.usage` divs; state class drives CSS color |
| 5 | Card registers itself in `window.customCards` for the HA card picker | VERIFIED | `window.customCards.push({type:"irrigation-monitor-card",...})` present before `customElements.define` |
| 6 | README documents the manual Lovelace resource registration step | VERIFIED | README section 4 documents URL `/irrigation_monitor/irrigation-monitor-card.js` as JavaScript Module |
| 7 | All 45 tests pass with no regressions | VERIFIED | `pytest tests/ -q` → 45 passed |

**Score:** 7/7 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `custom_components/irrigation_monitor/www/irrigation-monitor-card.js` | Complete Lovelace card implementation | VERIFIED | 222 lines; contains `customElements.define`, `_discoverZones`, `window.customCards`, `setConfig`, `set hass`, `getCardSize` |
| `custom_components/irrigation_monitor/__init__.py` | Static path registration via `async_register_static_paths` + `StaticPathConfig` | VERIFIED | `async_setup` registers `/irrigation_monitor/irrigation-monitor-card.js`; `async_setup_entry` clean (no double-registration) |
| `tests/test_card_setup.py` | Tests for file existence and static path registration | VERIFIED | `test_www_file_exists` and `test_static_path_registered` both pass; test asserts actual URL path |
| `README.md` | Installation instructions including Lovelace resource step | VERIFIED | Contains resource URL, JavaScript Module type, card YAML example, troubleshooting note on `/irrigation_monitor/` vs `/local/` |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `__init__.py` `async_setup` | `www/irrigation-monitor-card.js` | `async_register_static_paths([StaticPathConfig("/irrigation_monitor/irrigation-monitor-card.js", www_path, True)])` | WIRED | `Path(__file__).parent / "www" / "irrigation-monitor-card.js"` resolves to the actual file |
| `irrigation-monitor-card.js` `set hass` | `hass.states` | `_discoverZones(hass)` filters and maps state objects | WIRED | Filter logic reads state values; derives `_flow_rate` and `_daily_usage` sibling entities by prefix substitution |
| `_renderTile` | Zone data (name, flow, usage) | Template literal with `_escapeHtml`, `toFixed(1)` | WIRED | All four data points rendered; flow display conditionally shows `running` live rate vs. idle `0 gal/min` |
| README | `/irrigation_monitor/irrigation-monitor-card.js` | User follows documented resource registration steps | WIRED (docs) | Correct URL documented; troubleshooting section explicitly warns against using `/local/` |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| CARD-01 | 06-01, 06-02 | Custom Lovelace card displays all monitored zones with idle/running/leak_detected state | SATISFIED | Card discovers zones via `hass.states` scan; state class drives visual indicator per tile |
| CARD-02 | 06-01, 06-02 | Card shows current flow rate for each active zone | SATISFIED | `_renderTile` shows live `flowRate.toFixed(1) flowUnit` for `running` zones; `0 gal/min` for idle/leak |
| CARD-03 | 06-01, 06-02 | Card shows today's water usage per zone | SATISFIED | `_renderTile` always shows `dailyUsage.toFixed(1) dailyUnit today` for every zone tile |

No orphaned requirements: CARD-01, CARD-02, CARD-03 are the only Phase 6 requirements in REQUIREMENTS.md, and both plans claim all three.

---

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| None | — | — | — |

Scan results:
- No `TODO`, `FIXME`, `PLACEHOLDER` comments in card JS or `__init__.py`
- No `return null` / `return {}` / `return []` stub returns in the JS card logic
- `setConfig` calls `_render([])` with empty array — this is a correct initialization guard (no data before `set hass` fires), not a stub; `set hass` immediately overwrites with live zone data
- `_config = {}` initial value in constructor is correct initialization, overwritten by `setConfig`
- No hardcoded data flowing to user-visible output without being populated by live `hass.states`

---

### Human Verification Required

#### 1. Visual card rendering

**Test:** In a running HA instance, add `/irrigation_monitor/irrigation-monitor-card.js` as a JavaScript Module resource, then add `custom:irrigation-monitor-card` to a dashboard.
**Expected:** Grid of zone tiles appears; each tile shows zone name, state icon with correct color (grey/blue/red), current flow rate, and today's usage. Card picker shows "Irrigation Monitor" entry.
**Why human:** Web Component rendering, Shadow DOM styles, and `<ha-icon>` resolution are browser-runtime behaviors that cannot be verified by static code inspection or pytest.

**Note:** The user has confirmed this is working in a real HA instance per task context.

---

### Gaps Summary

No gaps. All automated verifiable truths pass. The single human-verification item (visual rendering) has been confirmed working by the user in a real HA instance.

**URL deviation from PLAN is not a gap:** The plan front-matter specified `/local/` which is architecturally incorrect for integration-bundled assets. The implementation correctly uses `/irrigation_monitor/`. The test, README, and user confirmation all align with the actual URL. The PLAN's stated truth is outdated documentation, not a codebase failure.

---

_Verified: 2026-03-24T07:30:00Z_
_Verifier: Claude (gsd-verifier)_
