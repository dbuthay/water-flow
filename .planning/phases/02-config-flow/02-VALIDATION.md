---
phase: 2
slug: config-flow
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-20
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest-homeassistant-custom-component 0.13.316 |
| **Config file** | `pyproject.toml` (already exists from Phase 1) |
| **Quick run command** | `.venv/bin/pytest tests/test_config_flow.py -x -q` |
| **Full suite command** | `.venv/bin/pytest tests/ -x -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/pytest tests/test_config_flow.py -x -q`
- **After every plan wave:** Run `.venv/bin/pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 2-W0 | 02-01 | 0 | SETUP-01–07 | unit stubs | `.venv/bin/pytest tests/test_config_flow.py -x -q` | ❌ W0 | ⬜ pending |
| 2-01-01 | 02-01 | 1 | SETUP-01,02,03 | unit | `.venv/bin/pytest tests/test_config_flow.py::test_full_flow_creates_entry -x` | ❌ W0 | ⬜ pending |
| 2-01-02 | 02-01 | 1 | SETUP-04 | unit | `.venv/bin/pytest tests/test_config_flow.py::test_options_flow_merge_preserves_zones -x` | ❌ W0 | ⬜ pending |
| 2-01-03 | 02-01 | 1 | SETUP-05,06,07 | unit | `.venv/bin/pytest tests/test_config_flow.py::test_options_per_zone_shutoff -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_config_flow.py` — test stubs for all SETUP-01 through SETUP-07 behaviors (listed in RESEARCH.md Validation Architecture)
- [ ] Entity state helpers in `tests/conftest.py` — mock Flume sensor + valve switch/valve entities for config flow tests

*Note: Existing `conftest.py` has `enable_custom_integrations` fixture — sufficient base; extend with entity state helpers.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Config flow appears in HA UI integrations list | SETUP-01 | Requires running HA instance | Add integration in HA UI, verify "Irrigation Monitor" appears |
| Options flow accessible via Configure button | SETUP-04 | Requires running HA instance | Go to integration settings, click Configure, verify options form shows |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
