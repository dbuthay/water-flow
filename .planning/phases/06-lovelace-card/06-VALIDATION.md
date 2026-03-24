---
phase: 6
slug: lovelace-card
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-24
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest-homeassistant-custom-component 0.13.316 |
| **Config file** | `pyproject.toml` (exists from Phase 1) |
| **Quick run command** | `.venv/bin/pytest tests/test_card_setup.py -x -q` |
| **Full suite command** | `.venv/bin/pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** `.venv/bin/pytest tests/test_card_setup.py -x -q`
- **After every plan wave:** `.venv/bin/pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green (43 existing + 2 new)
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 6-W0 | 06-01 | 0 | CARD-01 | stubs | `.venv/bin/pytest tests/test_card_setup.py --collect-only -q` | ❌ W0 | ⬜ pending |
| 6-01-01 | 06-01 | 1 | CARD-01 | integration | `.venv/bin/pytest tests/test_card_setup.py::test_www_file_exists -x` | ❌ W0 | ⬜ pending |
| 6-01-02 | 06-01 | 1 | CARD-01 | integration | `.venv/bin/pytest tests/test_card_setup.py::test_static_path_registered -x` | ❌ W0 | ⬜ pending |
| 6-02-01 | 06-02 | 2 | CARD-01,02,03 | smoke | `.venv/bin/pytest tests/ -x -q` (full suite green) | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_card_setup.py` — 2 test stubs: `test_www_file_exists`, `test_static_path_registered`
- [ ] No new fixtures needed — existing `mock_config_entry` covers static path registration test

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Card shows all zones in grid layout | CARD-01 | Requires running HA + browser | Add card to dashboard, verify grid appears |
| Running zone shows current flow rate | CARD-02 | Requires running zone entity state | Set zone to "on", verify flow rate displays in tile |
| Daily usage shows today's total | CARD-03 | Requires sensor state > 0 | Check tile shows non-zero usage for zones that have run |
| Leak detected tile shows red + warning icon | CARD-01 | Requires leak_detected state | Set status sensor to leak_detected, verify red tint |
| Card auto-discovers zones without config | CARD-01 | Requires running HA | Add card with only `type:` field, verify zones appear |

**Note:** CARD-02 and CARD-03 have no automated Python tests — JS discovery logic is verified manually. The Python tests only cover the static path registration (CARD-01 infra).

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
