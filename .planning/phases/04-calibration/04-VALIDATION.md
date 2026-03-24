---
phase: 4
slug: calibration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-24
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest-homeassistant-custom-component 0.13.316 |
| **Config file** | `pyproject.toml` (exists from Phase 1) |
| **Quick run command** | `.venv/bin/pytest tests/test_button.py -x -q` |
| **Full suite command** | `.venv/bin/pytest tests/ -x -q` |
| **Estimated runtime** | ~20 seconds |

---

## Sampling Rate

- **After every task commit:** `.venv/bin/pytest tests/test_button.py -x -q`
- **After every plan wave:** `.venv/bin/pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 4-W0 | 04-01 | 0 | CALIB-01–06 | stubs | `.venv/bin/pytest tests/test_button.py --collect-only -q` | ❌ W0 | ⬜ pending |
| 4-01-01 | 04-01 | 1 | CALIB-01,02,03 | unit | `.venv/bin/pytest tests/test_button.py::test_button_entities_created tests/test_button.py::test_calibrate_aborts_on_background_flow tests/test_button.py::test_calibrate_aborts_when_zone_running -x` | ❌ W0 | ⬜ pending |
| 4-01-02 | 04-01 | 1 | CALIB-04,05,06 | unit | `.venv/bin/pytest tests/test_button.py::test_calibration_full_sequence tests/test_button.py::test_calibration_saves_to_options tests/test_button.py::test_calibration_turns_valve_off_on_success -x` | ❌ W0 | ⬜ pending |
| 4-02-01 | 04-02 | 2 | CALIB-04,05 | unit | `.venv/bin/pytest tests/test_button.py::test_calibration_stabilization_timeout tests/test_button.py::test_recalibration_pending_flow tests/test_button.py::test_recalibration_save_action -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_button.py` — 12 test stubs for CALIB-01 through CALIB-06
- [ ] No new conftest fixtures needed — existing `mock_config_entry`, `mock_flume_entity`, `mock_valve_entities` cover all scenarios

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Notification action buttons (Save/Cancel) appear in Companion app | CALIB-05 | Requires iOS/Android Companion app — NOT visible in HA web frontend | Press calibrate on previously calibrated zone; verify notification appears in Companion app with Save/Cancel buttons |
| Calibrate button appears in HA entity list | CALIB-01 | Requires running HA instance | Check Developer Tools → States for `button.irrigation_monitor_*_calibrate` entities |

**Note:** Re-calibration Save/Cancel action buttons are only visible in the Home Assistant Companion mobile app (iOS/Android). They do not appear as clickable buttons in the HA web frontend. Web users see the notification text only.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
