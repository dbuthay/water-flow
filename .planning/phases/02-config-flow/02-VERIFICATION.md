---
phase: 02-config-flow
verified: 2026-03-20T00:00:00Z
status: passed
score: 11/11 must-haves verified
re_verification: false
gaps: []
human_verification:
  - test: "Open Settings > Integrations > Add Integration > Irrigation Monitor"
    expected: "Step 1 shows a Flume sensor entity picker (not a free-text field). Choosing a sensor advances to Step 2 showing discovered switches/valves as a multi-select list."
    why_human: "EntitySelector and SelectSelector rendering requires actual HA frontend — cannot verify UI appearance or picker filter behavior programmatically."
  - test: "Open integration options and step through per-zone configuration"
    expected: "BooleanSelector renders as a toggle, NumberSelector renders with min/max/step constraints visually enforced. Zone name appears in description placeholder."
    why_human: "Selector widget rendering is frontend behavior not exercised by pytest."
---

# Phase 2: Config Flow Verification Report

**Phase Goal:** Users can install the integration, select their Flume sensor, pick which valves to monitor, and configure per-zone options — all through the HA UI with no YAML
**Verified:** 2026-03-20
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Config flow Step 1 presents a Flume sensor picker filtered by integration=flume | VERIFIED | `EntityFilterSelectorConfig(integration="flume")` at config_flow.py:63; test `test_step_user_shows_form` passes |
| 2 | Config flow Step 2 presents discovered valve candidates from switch/valve/binary_sensor domains as multi-select | VERIFIED | `SelectSelector(SelectSelectorConfig(options=options, multiple=True))` at line 108; VALVE_DOMAINS filter at line 119; `test_step_valves_shows_discovered_entities` verifies schema |
| 3 | Completing both steps creates a ConfigEntry with flume_entity_id, monitored_zone_entity_ids, and poll_interval in data | VERIFIED | `async_create_entry` at line 87 with all three keys; `test_full_flow_creates_entry` passes |
| 4 | Each valve candidate displays as "Friendly Name (entity_id)" | VERIFIED | `SelectOptionDict(value=eid, label=f"{name} ({eid})")` at line 99 |
| 5 | New ConfigEntry initializes per-zone defaults in options.zones | VERIFIED | `options_zones` dict built at lines 78-86; `test_config_flow_sets_zone_defaults` asserts all four defaults |
| 6 | User can open options flow and change which valves are monitored without losing existing zone configuration | VERIFIED | Critical merge pattern: `existing = dict(self.config_entry.options)` then selective update at lines 221-264; `test_options_flow_merge_preserves_zones` passes (calibrated_flow=3.5 preserved) |
| 7 | User can toggle auto-shutoff on or off for a specific zone | VERIFIED | `CONF_SHUTOFF_ENABLED: BooleanSelector()` in async_step_zones schema; `test_options_per_zone_shutoff` passes |
| 8 | User can toggle anomaly alerts on or off for a specific zone | VERIFIED | `CONF_ALERTS_ENABLED: BooleanSelector()` in async_step_zones schema; `test_options_per_zone_alerts` passes |
| 9 | User can set a custom leak detection threshold multiplier per zone | VERIFIED | `CONF_THRESHOLD_MULTIPLIER: NumberSelector(NumberSelectorConfig(min=1.0, max=5.0, step=0.1))` at lines 283-289; `test_options_per_zone_threshold` passes |
| 10 | Removing a valve from the monitored list clears its zone data entirely | VERIFIED | Removed zones are simply omitted from `updated_zones` dict (not carried into `existing[CONF_ZONES]`); `test_options_flow_remove_valve_clears_data` passes |
| 11 | Adding a new valve gives it default zone settings immediately | VERIFIED | New-zone branch at lines 244-250 applies all four defaults including `CONF_CALIBRATED_FLOW: None`; `test_options_flow_add_new_valve_gets_defaults` passes |

**Score:** 11/11 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `custom_components/irrigation_monitor/config_flow.py` | Two-step config flow wizard + full options flow handler | VERIFIED | 294 lines; both `IrrigationMonitorConfigFlow` and `IrrigationMonitorOptionsFlowHandler` fully implemented — no stubs |
| `custom_components/irrigation_monitor/const.py` | All CONF_* config keys and default values | VERIFIED | Contains CONF_FLUME_ENTITY_ID, CONF_MONITORED_ZONES, CONF_POLL_INTERVAL, CONF_ZONES, CONF_SHUTOFF_ENABLED, CONF_ALERTS_ENABLED, CONF_CALIBRATED_FLOW, CONF_THRESHOLD_MULTIPLIER, all DEFAULT_* values, VALVE_DOMAINS |
| `custom_components/irrigation_monitor/strings.json` | UI strings for config and options flow steps | VERIFIED | Contains config.step.user, config.step.valves, options.step.init, options.step.zones |
| `custom_components/irrigation_monitor/translations/en.json` | Mirror of strings.json | VERIFIED | Identical content to strings.json |
| `custom_components/irrigation_monitor/manifest.json` | config_flow: true | VERIFIED | `"config_flow": true` confirmed at line 12 |
| `tests/conftest.py` | mock_flume_entity and mock_valve_entities fixtures | VERIFIED | Both fixtures present; mock_valve_entities registers switch.rachio_zone_1, switch.rachio_zone_2, valve.os_zone_3 |
| `tests/test_config_flow.py` | 12 tests covering SETUP-01 through SETUP-07 | VERIFIED | 449 lines; 12 tests (5 config flow + 7 options flow); all pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| config_flow.py | const.py | `from .const import` | VERIFIED | All CONF_* and DEFAULT_* constants imported at lines 22-37 |
| config_flow.py | homeassistant.helpers.entity_registry | `er.async_get(self.hass)` | VERIFIED | Called at config_flow.py:116 and :196 in both discover methods |
| tests/test_config_flow.py | config_flow.py | `hass.config_entries.flow.async_init(DOMAIN)` | VERIFIED | Used in all 5 config flow tests; `hass.config_entries.options.async_init` used in all 7 options flow tests |
| IrrigationMonitorOptionsFlowHandler | self.config_entry.options | merge pattern `existing = dict(self.config_entry.options)` | VERIFIED | Line 221; then `existing[CONF_ZONES] = updated_zones; return self.async_create_entry(data=existing)` at lines 252-264 |
| async_step_zones | self.async_create_entry(data=existing) | merged options dict | VERIFIED | Line 264; `existing` contains updated zones dict |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| SETUP-01 | 02-01 | User selects Flume sensor from entity list during initial setup | SATISFIED | `EntitySelector(EntitySelectorConfig(filter=EntityFilterSelectorConfig(integration="flume")))` in async_step_user; test_step_user_shows_form passes |
| SETUP-02 | 02-01 | Integration scans entity registry for valve candidates | SATISFIED | `_discover_valve_entities()` iterates `registry.entities.values()` filtering by VALVE_DOMAINS; test_step_valves_shows_discovered_entities verifies schema |
| SETUP-03 | 02-01 | User selects which valves to monitor (not all discovered) | SATISFIED | `SelectSelector(multiple=True)` allows arbitrary subset selection; test_full_flow_creates_entry verifies selected subset stored in data |
| SETUP-04 | 02-02 | User can re-run valve discovery via options without losing existing zone config | SATISFIED | Critical merge pattern preserves calibrated_flow=3.5 through round-trip; test_options_flow_merge_preserves_zones, test_options_flow_add_new_valve_gets_defaults, test_options_flow_remove_valve_clears_data all pass |
| SETUP-05 | 02-02 | User can enable/disable auto-shutoff per valve without removing from monitoring | SATISFIED | CONF_SHUTOFF_ENABLED BooleanSelector in per-zone step; test_options_per_zone_shutoff verifies False toggle persists |
| SETUP-06 | 02-02 | User can enable/disable anomaly alerts per valve independently | SATISFIED | CONF_ALERTS_ENABLED BooleanSelector separate from shutoff field; test_options_per_zone_alerts verifies independent toggle |
| SETUP-07 | 02-02 | User can configure leak detection threshold multiplier per zone | SATISFIED | CONF_THRESHOLD_MULTIPLIER NumberSelector(min=1.0, max=5.0, step=0.1); test_options_per_zone_threshold verifies 2.5 value persists |

No orphaned requirements. All 7 SETUP requirements claimed by plans 02-01 and 02-02 are accounted for and verified.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| config_flow.py | 406 | `IrrigationMonitorOptionsFlowHandler` stub from Plan 01 comment in Plan 02-01 | INFO | Not present — the stub was fully replaced. No anti-patterns detected. |

No TODOs, FIXMEs, placeholder returns, or empty implementations found in any phase 2 files.

### Human Verification Required

#### 1. Config Flow UI — EntitySelector and SelectSelector Rendering

**Test:** In a local HA instance with the Flume integration installed, go to Settings > Integrations > Add Integration > Irrigation Monitor.
**Expected:** Step 1 shows a dropdown/picker that only lists Flume integration entities (not all sensors). Selecting a Flume sensor and clicking Next shows Step 2 with discovered switches and valves in a multi-select list labeled "Friendly Name (entity_id)".
**Why human:** EntitySelector's `integration="flume"` filter and SelectSelector's multi-select rendering are frontend behaviors not exercised by pytest mocks.

#### 2. Options Flow — Per-Zone Step Iteration and Placeholder Rendering

**Test:** After setup, go to Settings > Integrations > Irrigation Monitor > Configure. Submit the init form. Verify that the zones step appears once per selected valve, with the zone's entity_id shown in the step description.
**Expected:** If two valves are selected, the zones step appears twice — once for each valve. The description shows the correct zone identifier. BooleanSelectors render as toggles. NumberSelector for threshold shows min/max constraints.
**Why human:** Step iteration count and description_placeholders rendering require real flow execution in HA frontend.

### Gaps Summary

No gaps. All must-haves from both plans verified. All 12 automated tests pass. All 7 SETUP requirements are satisfied with implementation evidence.

---

_Verified: 2026-03-20_
_Verifier: Claude (gsd-verifier)_
