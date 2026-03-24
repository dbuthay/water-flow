---
phase: 05-leak-detection
plan: "01"
subsystem: coordinator
tags: [leak-detection, state-machine, tdd, coordinator, notifications]
dependency_graph:
  requires: []
  provides: [leak-detection-engine, test-infrastructure, calibrated-fixture]
  affects: [coordinator, conftest, tests]
tech_stack:
  added: []
  patterns: [transition-detection, ramp-up-counter, dedup-set, persistent-notification]
key_files:
  created:
    - tests/test_leak.py
  modified:
    - custom_components/irrigation_monitor/const.py
    - custom_components/irrigation_monitor/coordinator.py
    - tests/conftest.py
decisions:
  - "ramp_up_polls stored globally in ConfigEntry.options (not per-zone) — simpler for single-setting use case"
  - "leak_statuses kept as coordinator dict (not ZoneData field) — avoids ZoneData dataclass churn, Plan 02 wires sensors to it"
  - "notification_id format: leak_{zone_slug} — zone_slug uses dot->underscore replacement for valid HA notification IDs"
  - "DEFAULT_THRESHOLD_MULTIPLIER reused from const.py rather than hardcoding 1.5 in detection branch"
metrics:
  duration_minutes: 3
  completed_date: "2026-03-23"
  tasks_completed: 2
  files_modified: 4
---

# Phase 5 Plan 01: Leak Detection Engine and Test Infrastructure Summary

Coordinator leak detection state machine with OFF->ON/ON->OFF transition tracking, configurable ramp-up skip window, threshold comparison, auto-shutoff, and deduped persistent notifications — plus 10 xfail test stubs and calibrated fixture for Plan 02.

## What Was Built

### Task 0: Wave 0 Test Infrastructure
- **`const.py`**: Added `CONF_RAMP_UP_POLLS = "ramp_up_polls"` and `DEFAULT_RAMP_UP_POLLS = 2`
- **`tests/conftest.py`**: Added `mock_calibrated_config_entry` fixture — zone 1 calibrated at 2.0 gal/min, zone 2 uncalibrated, `CONF_RAMP_UP_POLLS: 0` (disables ramp-up delay in tests)
- **`tests/test_leak.py`**: 10 `xfail(strict=True)` stubs covering DETECT-01 through DETECT-04; collected by pytest without failing the suite

### Task 1: Coordinator Leak Detection Engine
- **New imports**: `CONF_ALERTS_ENABLED`, `CONF_RAMP_UP_POLLS`, `CONF_SHUTOFF_ENABLED`, `DEFAULT_RAMP_UP_POLLS`, `DEFAULT_THRESHOLD_MULTIPLIER`
- **4 new instance variables in `__init__`**: `_zone_was_on`, `_ramp_up_counters`, `_leak_notified`, `_leak_statuses`
- **`_fire_leak_notification` method**: fires `async_create` with zone_id, flow rate, calibrated flow, and shutoff status in the message body
- **`_async_update_data` leak detection block**: inserted after `result[zone_id] = ZoneData(...)`, with `_zone_was_on[zone_id] = is_on` as the final statement in the per-zone loop

### State Machine Logic
```
OFF -> ON:  _ramp_up_counters[zone_id] = ramp_up_polls  (reset counter)
ON -> OFF:  _leak_notified.discard(zone_id)              (reset dedup)
            _leak_statuses stays "leak_detected" if set  (persists until ack)

Per poll when ON + calibrated:
  ramp > 0:  decrement counter, status = "running"
  ramp == 0 + flow > calibrated * threshold:
             status = "leak_detected"
             shutoff_enabled -> _turn_valve(zone_id, turn_on=False)
             alerts_enabled + not deduped -> _fire_leak_notification(...)
             _leak_notified.add(zone_id)
  ramp == 0 + flow <= threshold: status = "running"

When ON + uncalibrated: status = "running" (silent skip)
When OFF + not leak_detected: status = "idle"
```

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 0 | 95f1222 | test(05-01): add Wave 0 leak detection test stubs and calibrated fixture |
| 1 | c26ec5b | feat(05-01): implement coordinator leak detection engine |

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None - coordinator leak detection is fully implemented. Test stubs are intentionally xfail (Wave 0 pattern) — they will be wired GREEN in Plan 05-02 when ZoneStatusSensor and AcknowledgeLeakButton entities are added.

## Self-Check: PASSED

- tests/test_leak.py: FOUND
- coordinator.py: FOUND
- commit 95f1222: FOUND
- commit c26ec5b: FOUND
