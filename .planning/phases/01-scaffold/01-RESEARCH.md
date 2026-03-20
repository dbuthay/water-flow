# Phase 1: Scaffold - Research

**Researched:** 2026-03-19
**Domain:** HACS-installable Home Assistant custom integration skeleton + pytest environment
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **Domain**: `irrigation_monitor` — prefix for all entity IDs. Locked once real users install.
- **HACS display name**: "Irrigation Monitor"
- **Python package folder**: `custom_components/irrigation_monitor/` — matches domain
- Start as a private GitHub repository; add as a HACS custom repository for local testing
- No HACS default catalog submission yet — custom repo approach until ready to go public
- Phase 1 only needs pytest environment wired up and passing — no example tests required
- Success = `pytest` runs without errors (even with zero test files)
- Mock Flume sensor and mock valve entities deferred to Phase 3

### Claude's Discretion

- Exact `manifest.json` field values beyond domain and name (iot_class, version, dependencies)
- `hacs.json` structure
- File layout within `custom_components/irrigation_monitor/`
- GitHub Actions CI setup (deferred to v2)

### Deferred Ideas (OUT OF SCOPE)

- GitHub Actions CI (run pytest on push) — v2 requirement (INFRA-04)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INFRA-01 | Integration is installable via HACS as a custom repository (valid manifest.json, hacs.json, semver tags) | HACS structure requirements, manifest.json fields, hacs.json format — fully documented in Standard Stack and Architecture sections |
| INFRA-02 | pytest test suite with pytest-homeassistant-custom-component covers coordinator logic, calibration sequence, leak detection, and daily usage tracking using mock Flume and valve entities | Phase 1 only wires up the environment; actual test content is Phase 3+. Fixture and conftest.py patterns documented. |
</phase_requirements>

---

## Summary

Phase 1 creates the structural foundation for a HACS-installable custom integration. The deliverables are two things: (1) a valid `custom_components/irrigation_monitor/` package structure with correct `manifest.json` and a stub `__init__.py` that HA can load, and (2) a working pytest environment using `pytest-homeassistant-custom-component` that can run `pytest` with zero errors (even zero tests).

The HACS validation rules for a custom repository (non-default-catalog) are lighter than for default catalog submission. The repo needs a `hacs.json` at root, a valid `manifest.json` with a `version` field, and a semver git tag. Private repos work as custom repositories in HACS when the user supplies a GitHub token — the context decision to start private is fully supported.

The pytest environment requires a `conftest.py` that enables custom integration loading, a `pyproject.toml` (or `requirements_test.txt`) pinning `pytest-homeassistant-custom-component`, and `pytest-asyncio` with `asyncio_mode = "auto"`. The current package version is 0.13.318 (tracking HA 2026.3.x), requiring Python >=3.14.

**Primary recommendation:** Lay down the full file skeleton now so later phases can fill in stubs without restructuring — even if `__init__.py` and `const.py` are nearly empty.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest-homeassistant-custom-component | 0.13.318 | Provides HA test fixtures (hass, MockConfigEntry) | Official pytest plugin for custom component testing; tracks HA core test utilities daily |
| pytest-asyncio | 1.3.0 | async test support | Required for HA async test patterns; built on asyncio |
| pytest | latest compatible | Test runner | Standard Python testing |

**Version verification (as of 2026-03-19):**
- `pytest-homeassistant-custom-component`: 0.13.318 (released 2026-03-17, tracks HA 2026.3.2)
- `pytest-asyncio`: 1.3.0 (released 2025-11-10)

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-cov | latest | Coverage reporting | Add once tests exist (Phase 3+) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pytest-homeassistant-custom-component | homeassistant full install | Full HA install is ~500MB; the plugin extracts only what's needed for testing |
| pyproject.toml | requirements_test.txt | pyproject.toml is the modern standard; both work |

**Installation:**
```bash
pip install pytest-homeassistant-custom-component pytest-asyncio pytest-cov
```

---

## Architecture Patterns

### Recommended Project Structure
```
water-flow/                          # repo root
├── custom_components/
│   └── irrigation_monitor/
│       ├── __init__.py              # async_setup_entry, async_unload_entry (stubs in Phase 1)
│       ├── manifest.json            # HACS/HA metadata
│       └── const.py                 # DOMAIN constant
├── tests/
│   ├── __init__.py                  # empty, makes tests a package
│   └── conftest.py                  # enable_custom_integrations fixture
├── hacs.json                        # at repo root
├── pyproject.toml                   # pytest config + test deps
└── README.md                        # required for HACS display
```

Files added in later phases (not Phase 1):
- `config_flow.py`, `coordinator.py`, `sensor.py`, `switch.py`, `button.py` — Phase 2+
- `strings.json`, `translations/en.json` — Phase 2

### Pattern 1: Minimal __init__.py Stub
**What:** Phase 1 only needs HA to be able to import the integration without error. Provide stub `async_setup_entry` and `async_unload_entry`.
**When to use:** Scaffold phase — no logic yet.
**Example:**
```python
# custom_components/irrigation_monitor/__init__.py
from __future__ import annotations
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

PLATFORMS: list[str] = []

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
```

### Pattern 2: conftest.py for pytest-homeassistant-custom-component
**What:** Required fixture `enable_custom_integrations` must be active; otherwise HA refuses to load custom components during tests.
**When to use:** Every project using pytest-homeassistant-custom-component.
**Example:**
```python
# tests/conftest.py
from pytest_homeassistant_custom_component.common import MockConfigEntry
import pytest

pytest_plugins = "pytest_homeassistant_custom_component"

@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests in this project."""
    yield
```

Note: The `enable_custom_integrations` fixture was introduced in HA 2021.6.0b0. Without it, HA's test infrastructure silently skips loading custom components and tests pass vacuously.

### Pattern 3: manifest.json for Custom Repository (Non-Default-Catalog)
**What:** The minimum valid manifest.json for a HACS custom repository.
**When to use:** Phase 1 scaffold.
**Example:**
```json
{
  "domain": "irrigation_monitor",
  "name": "Irrigation Monitor",
  "version": "0.1.0",
  "documentation": "https://github.com/OWNER/REPO",
  "issue_tracker": "https://github.com/OWNER/REPO/issues",
  "codeowners": ["@GITHUB_USERNAME"],
  "dependencies": [],
  "requirements": [],
  "iot_class": "local_polling",
  "config_flow": false
}
```

Notes:
- `config_flow: false` in Phase 1 — set to `true` in Phase 2 when config_flow.py is added
- `version` field is required for HACS (not required for HA core integrations, but required for custom ones)
- `iot_class: "local_polling"` — correct for this integration (reads local HA entities via polling)
- `integration_type` defaults to `"hub"` when omitted — acceptable for Phase 1

### Pattern 4: hacs.json at Repo Root
**What:** Minimum valid hacs.json.
**Example:**
```json
{
  "name": "Irrigation Monitor",
  "content_in_root": false
}
```

`content_in_root: false` signals that `custom_components/` is a subdirectory (not the root itself).

### Pattern 5: pyproject.toml pytest configuration
**Example:**
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[project.optional-dependencies]
test = [
    "pytest-homeassistant-custom-component==0.13.318",
    "pytest-asyncio>=1.3.0",
    "pytest-cov",
]
```

### Anti-Patterns to Avoid
- **Missing `custom_components/__init__.py`**: The `custom_components/` directory does NOT need an `__init__.py` (it is not a Python package in HA's custom component loading model). Do NOT add one at the `custom_components/` level — only add it at `irrigation_monitor/` level.
- **Nested custom_components**: HACS requires `custom_components/` at the repo root. Placing it under `src/` or a subdirectory fails HACS validation.
- **config_flow: true without config_flow.py**: If `manifest.json` sets `config_flow: true` but no `config_flow.py` exists, HA will log errors during tests.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HA test fixtures | Custom HA instance setup | `pytest-homeassistant-custom-component` | Extracting HA fixtures manually requires cloning the entire core repo; the plugin does it cleanly |
| HACS validation | Manual checklist | `hacs-validate` CLI or `hacs/action@main` GitHub Action | The validator catches non-obvious failures (missing semver tags, wrong file placement) |
| Async test setup | `asyncio.run()` wrapper | `pytest-asyncio` with `asyncio_mode = "auto"` | Manual async runner causes event loop conflicts with HA's test infrastructure |

**Key insight:** The HA test ecosystem is tightly coupled — using fixtures from outside the ecosystem or rolling custom async harnesses breaks in subtle ways. Always use the plugin.

---

## Common Pitfalls

### Pitfall 1: enable_custom_integrations Not Active (P7 variant)
**What goes wrong:** Tests run without error but the integration is never actually loaded by HA. Tests pass vacuously, giving false confidence.
**Why it happens:** HA's test infrastructure disables custom component loading by default for safety.
**How to avoid:** Add `autouse=True` fixture in `conftest.py` that depends on `enable_custom_integrations`. Verify by adding a dummy test that asserts the integration domain is registered.
**Warning signs:** No import errors even when `__init__.py` has a syntax error.

### Pitfall 2: Version Mismatch Between manifest.json and Git Tag (P7)
**What goes wrong:** HACS custom repository shows "Update available" loop or fails to install.
**Why it happens:** HACS checks that the semver git tag matches the `version` field in `manifest.json`.
**How to avoid:** When creating the initial git tag `v0.1.0`, ensure `manifest.json` contains `"version": "0.1.0"` (no `v` prefix in the JSON value).
**Warning signs:** HACS shows an update immediately after fresh install.

### Pitfall 3: pytest-homeassistant-custom-component Version Drift
**What goes wrong:** Tests break unexpectedly after `pip install --upgrade` because the plugin tracks HA beta releases daily.
**Why it happens:** Package increments version with every HA beta/stable release — unpinned installs can jump to a version requiring Python 3.14+ or new HA APIs.
**How to avoid:** Pin the exact version in `pyproject.toml` or `requirements_test.txt`. Upgrade deliberately, not automatically.
**Warning signs:** `ImportError` or `AttributeError` on fixtures after upgrade.

### Pitfall 4: custom_components/__init__.py Present
**What goes wrong:** Python import system treats `custom_components/` as a regular package, causing namespace conflicts with HA's custom component loader.
**Why it happens:** Common Python convention to add `__init__.py` to all directories. HA's loader expects the directory to NOT be a Python package at that level.
**How to avoid:** Only `irrigation_monitor/__init__.py` should exist. The `custom_components/` dir itself should have no `__init__.py`.
**Warning signs:** `ModuleNotFoundError` or duplicate domain registration errors during tests.

### Pitfall 5: Python Version Incompatibility
**What goes wrong:** `pytest-homeassistant-custom-component` 0.13.x requires Python >=3.14. Running under Python 3.12 fails at install.
**Why it happens:** HA 2026.x has moved to Python 3.14 as the minimum.
**How to avoid:** Verify local Python version with `python --version`. Install Python 3.14 if not present. Note: Python 3.14 is stable (released October 2025).
**Warning signs:** `pip install` fails with "requires Python >=3.14".

---

## Code Examples

### Minimal async_setup_entry / async_unload_entry
```python
# Source: HA developer docs — integration lifecycle
from __future__ import annotations
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN

PLATFORMS: list[str] = []

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up irrigation_monitor from a config entry."""
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
```

### Minimal const.py
```python
# custom_components/irrigation_monitor/const.py
DOMAIN = "irrigation_monitor"
```

### Smoke test to verify environment loads
```python
# tests/test_init.py — optional smoke test for Phase 1 validation
from custom_components.irrigation_monitor.const import DOMAIN

def test_domain_constant():
    assert DOMAIN == "irrigation_monitor"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `hass.data[DOMAIN]` for coordinator storage | `ConfigEntry.runtime_data` | HA 2024.4 | Type-safe, no dict key collisions |
| `pytest.ini` for asyncio config | `pyproject.toml` with `asyncio_mode = "auto"` | 2023+ | Single config file, no asyncio decorator needed |
| `OptionsFlowWithConfigEntry` base class | `OptionsFlow` (entry passed differently) | HA 2024.x | Check current HA version for correct base class |
| Separate `requirements.txt` for tests | `pyproject.toml` optional-dependencies | PEP 621 standard | Modern packaging standard |

**Deprecated/outdated:**
- `hass.data[DOMAIN]` dict pattern: replaced by `ConfigEntry.runtime_data` (HA 2024.4+)
- `@pytest.mark.asyncio` decorator: replaced by `asyncio_mode = "auto"` in config — no per-test decoration needed

---

## Open Questions

1. **Python 3.14 availability in local dev environment**
   - What we know: `pytest-homeassistant-custom-component` 0.13.318 requires Python >=3.14 (tracks HA 2026.3.x)
   - What's unclear: Developer's local Python version
   - Recommendation: Check with `python --version` before installing; install Python 3.14 if needed (pyenv or system installer)

2. **Private repo + HACS custom repository compatibility**
   - What we know: HACS official docs state repos must be public for the default catalog; the custom repository FAQ suggests private repos can work with a GitHub token
   - What's unclear: The exact HACS version behavior for private repos
   - Recommendation: Start with a private repo and test the HACS custom repository workflow before committing to public. If HACS rejects the private repo, make it public early — this is a Phase 1 test.

3. **integration_type field**
   - What we know: HA docs say `integration_type` defaults to `"hub"` when omitted; it is required for core integrations
   - What's unclear: Whether HACS validation requires it for custom integrations
   - Recommendation: Include `"integration_type": "hub"` explicitly to avoid any HACS linting surprise.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-homeassistant-custom-component 0.13.318 |
| Config file | `pyproject.toml` — Wave 0 creates it |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v --cov=custom_components/irrigation_monitor` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-01 | manifest.json is valid JSON with required fields | smoke | `python -c "import json; json.load(open('custom_components/irrigation_monitor/manifest.json'))"` | Wave 0 creates file |
| INFRA-01 | hacs.json is valid JSON at repo root | smoke | `python -c "import json; json.load(open('hacs.json'))"` | Wave 0 creates file |
| INFRA-02 | pytest runs without errors | smoke | `pytest tests/ -x -q` | Wave 0 creates conftest.py |
| INFRA-02 | DOMAIN constant importable from package | unit | `pytest tests/test_init.py -x` | Wave 0 creates test |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/__init__.py` — empty, makes tests a package
- [ ] `tests/conftest.py` — `enable_custom_integrations` autouse fixture
- [ ] `tests/test_init.py` — smoke test: import DOMAIN constant
- [ ] `pyproject.toml` — pytest config + test dependencies
- [ ] Framework install: `pip install pytest-homeassistant-custom-component pytest-asyncio pytest-cov`

---

## Sources

### Primary (HIGH confidence)
- https://github.com/MatthewFlamm/pytest-homeassistant-custom-component — package README, conftest patterns
- https://pypi.org/project/pytest-homeassistant-custom-component/ — version 0.13.318, Python >=3.14 requirement
- https://developers.home-assistant.io/docs/creating_integration_manifest/ — manifest.json required fields
- https://hacs.xyz/docs/publish/start — public repo requirement, hacs.json placement
- .planning/research/STACK.md — project HACS manifest template, testing stack (HIGH confidence, project-authored)
- .planning/research/PITFALLS.md — P7 HACS submission failures (HIGH confidence, project-authored)

### Secondary (MEDIUM confidence)
- https://hacs.xyz/docs/faq/custom_repositories — custom repo workflow (content was sparse; HACS docs confirmed basic add flow)
- https://hacs.xyz/docs/publish/include — validation check list (confirmed hacs.json at root, name field required)

### Tertiary (LOW confidence)
- Private repo + HACS custom repository: implied by HACS FAQ structure but not explicitly confirmed from the fetched page content — flag for manual validation in Phase 1.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions verified against PyPI registry (2026-03-19)
- Architecture: HIGH — file structure derived from official HA docs + project STACK.md
- Pitfalls: HIGH — P7 from project PITFALLS.md + verified HACS validation requirements
- Private repo behavior: LOW — not explicitly confirmed from docs; needs manual test

**Research date:** 2026-03-19
**Valid until:** 2026-04-19 (30 days — pytest-homeassistant-custom-component updates daily but breaking changes are rare within a minor series)
