---
phase: 5
slug: leak-detection
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-24
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest-homeassistant-custom-component 0.13.316 |
| **Config file** | `pyproject.toml` (exists from Phase 1) |
| **Quick run command** | `.venv/bin/pytest tests/test_leak.py -x -q` |
| **Full suite command** | `.venv/bin/pytest tests/ -x -q` |
| **Estimated runtime** | ~20 seconds |

---

## Sampling Rate

- **After every task commit:** `.venv/bin/pytest tests/test_leak.py -x -q`
- **After every plan wave:** `.venv/bin/pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green (all 32 existing + new)
- **Max feedback latency:** ~20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 5-W0 | 05-01 | 0 | DETECT-01–04 | stubs | `.venv/bin/pytest tests/test_leak.py --collect-only -q` | ❌ W0 | ⬜ pending |
| 5-01-01 | 05-01 | 1 | DETECT-01,02 | unit | `.venv/bin/pytest tests/test_leak.py::test_leak_detection_fires tests/test_leak.py::test_ramp_up_skips_detection -x` | ❌ W0 | ⬜ pending |
| 5-01-02 | 05-01 | 1 | DETECT-03,04 | unit | `.venv/bin/pytest tests/test_leak.py::test_leak_triggers_shutoff tests/test_leak.py::test_leak_notification_fires -x` | ❌ W0 | ⬜ pending |
| 5-02-01 | 05-02 | 2 | DETECT-04 | unit | `.venv/bin/pytest tests/test_leak.py::test_leak_notification_dedup tests/test_leak.py::test_leak_notification_clears_on_restart -x` | ❌ W0 | ⬜ pending |
| 5-02-02 | 05-02 | 2 | DETECT-01,04 | unit | `.venv/bin/pytest tests/test_leak.py::test_zone_status_sensor tests/test_leak.py::test_acknowledge_clears_status -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**DETECT-05 note:** Already covered by `tests/test_coordinator.py::test_flume_unavailable_entities_unavailable` (existing green test). No new test needed.

---

## Wave 0 Requirements

- [ ] `tests/test_leak.py` — 10 new test stubs covering DETECT-01 through DETECT-04
- [ ] `tests/conftest.py` — add `mock_calibrated_config_entry` fixture (with `CONF_RAMP_UP_POLLS: 0` so tests don't need multiple pre-polls)

*Note: `_zone_was_on` update MUST be last statement in per-zone loop — placing it earlier kills all transition detection.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Zone status sensor visible in HA states panel | DETECT-01 | Requires running HA | Check Developer Tools → States for `sensor.irrigation_monitor_*_status` |
| Acknowledge leak button visible in HA entity list | DETECT-01 | Requires running HA | Check `button.irrigation_monitor_*_acknowledge_leak` entities |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
