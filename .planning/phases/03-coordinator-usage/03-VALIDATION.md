---
phase: 3
slug: coordinator-usage
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-20
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest-homeassistant-custom-component 0.13.316 |
| **Config file** | `pyproject.toml` (exists from Phase 1) |
| **Quick run command** | `.venv/bin/pytest tests/test_coordinator.py -x -q` |
| **Full suite command** | `.venv/bin/pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** `.venv/bin/pytest tests/test_coordinator.py -x -q`
- **After every plan wave:** `.venv/bin/pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 3-W0 | 03-01 | 0 | USAGE-01–03 | stubs | `.venv/bin/pytest tests/test_coordinator.py -x -q` | ❌ W0 | ⬜ pending |
| 3-01-01 | 03-01 | 1 | USAGE-01 | unit | `.venv/bin/pytest tests/test_coordinator.py::test_sensor_entities_created -x` | ❌ W0 | ⬜ pending |
| 3-01-02 | 03-01 | 1 | USAGE-01 | unit | `.venv/bin/pytest tests/test_coordinator.py::test_daily_usage_accumulates -x` | ❌ W0 | ⬜ pending |
| 3-01-03 | 03-01 | 1 | USAGE-01 | unit | `.venv/bin/pytest tests/test_coordinator.py::test_flume_unavailable_entities_unavailable -x` | ❌ W0 | ⬜ pending |
| 3-02-01 | 03-02 | 2 | USAGE-02 | unit | `.venv/bin/pytest tests/test_coordinator.py::test_totals_persist_across_restart -x` | ❌ W0 | ⬜ pending |
| 3-02-02 | 03-02 | 2 | USAGE-02 | unit | `.venv/bin/pytest tests/test_coordinator.py::test_midnight_reset_zeroes_totals -x` | ❌ W0 | ⬜ pending |
| 3-02-03 | 03-02 | 2 | USAGE-03 | unit | `.venv/bin/pytest tests/test_coordinator.py::test_stale_date_resets_totals -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_coordinator.py` — 7 RED test stubs covering USAGE-01, USAGE-02, USAGE-03
- [ ] Extended `tests/conftest.py` — add `mock_config_entry` and `mock_coordinator` fixtures

*Note: `valve` domain state is `"open"`/`"closed"`, not `"on"`/`"off"` — test fixtures must set correct state strings per domain.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Sensor entities visible in HA Developer Tools | USAGE-01 | Requires running HA instance | Start HA with `hass -c config/`, check States tab for `sensor.irrigation_monitor_*` entities |
| Daily usage resets at midnight | USAGE-02 | Time-dependent | Observe sensor value before/after midnight or use time-freeze in HA dev instance |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
