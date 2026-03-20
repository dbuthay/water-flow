---
phase: 1
slug: scaffold
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-19
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-homeassistant-custom-component 0.13.318 |
| **Config file** | `pyproject.toml` — Wave 0 creates it |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v --cov=custom_components/irrigation_monitor` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 0 | INFRA-02 | smoke | `pytest tests/ -x -q` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 0 | INFRA-01 | smoke | `python -c "import json; json.load(open('custom_components/irrigation_monitor/manifest.json'))"` | ❌ W0 | ⬜ pending |
| 1-01-03 | 01 | 0 | INFRA-01 | smoke | `python -c "import json; json.load(open('hacs.json'))"` | ❌ W0 | ⬜ pending |
| 1-01-04 | 01 | 1 | INFRA-02 | unit | `pytest tests/test_init.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/__init__.py` — empty, makes tests a Python package
- [ ] `tests/conftest.py` — `enable_custom_integrations` autouse fixture (CRITICAL — without this, HA silently skips loading custom components)
- [ ] `tests/test_init.py` — smoke test: import DOMAIN constant, assert it equals "irrigation_monitor"
- [ ] `pyproject.toml` — pytest config (`asyncio_mode = "auto"`, `testpaths = ["tests"]`) + pinned test deps
- [ ] Framework install: `pip install pytest-homeassistant-custom-component==0.13.318 pytest-asyncio>=1.3.0 pytest-cov`

*Note: Python 3.14 required by pytest-homeassistant-custom-component 0.13.318. Verify with `python --version` before Wave 0.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Integration loads in HA without errors | INFRA-01 | Requires a running HA instance | Start local HA with `hass -c config/`, check logs for `[irrigation_monitor]` errors |
| HACS custom repository install works | INFRA-01 | Requires HACS + GitHub token | HACS → ⋮ → Custom Repositories → add repo URL → verify it appears without validation errors |
| Private repo accessible via HACS | INFRA-01 | LOW confidence from research — needs empirical test | Attempt HACS custom repo add with private repo; if rejected, make public early |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
