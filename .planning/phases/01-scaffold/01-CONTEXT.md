# Phase 1: Scaffold - Context

**Gathered:** 2026-03-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Create a HACS-installable Home Assistant custom integration skeleton (`custom_components/irrigation_monitor/`) with a working pytest environment. No logic, no entities, no config flow yet — just the structural foundation that all subsequent phases build on. Phase is complete when HACS validation passes and `pytest` runs without errors.

</domain>

<decisions>
## Implementation Decisions

### Integration Identity
- **Domain**: `irrigation_monitor` — this becomes the prefix for all entity IDs (e.g., `sensor.irrigation_monitor_zone_1_daily_usage`). Locked once real users install.
- **HACS display name**: "Irrigation Monitor" — what appears in the HACS browser catalog
- **Python package folder**: `custom_components/irrigation_monitor/` — matches domain

### Repository & Distribution
- Start as a private GitHub repository; add as a HACS custom repository for local testing
- No HACS default catalog submission yet — custom repo approach until ready to go public
- Domain can be freely changed while only the developer is using it; becomes a breaking change once public users install

### Test Infrastructure
- Phase 1 only needs the pytest environment wired up and passing — no example tests required
- Success = `pytest` runs without errors (even with zero test files)
- Mock Flume sensor and mock valve entities will be added in Phase 3 when the coordinator needs them

### Claude's Discretion
- Exact `manifest.json` field values beyond domain and name (iot_class, version, dependencies)
- `hacs.json` structure
- File layout within `custom_components/irrigation_monitor/`
- GitHub Actions CI setup (deferred to v2)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project context
- `.planning/PROJECT.md` — Project vision, constraints, and key decisions
- `.planning/REQUIREMENTS.md` — INFRA-01, INFRA-02 (the two requirements this phase covers)
- `.planning/research/STACK.md` — HACS manifest.json requirements, hacs.json format, HACS distribution requirements
- `.planning/research/PITFALLS.md` — P7 (HACS submission failures and validation requirements)

No external specs — requirements fully captured in decisions above and research files.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project, no existing code

### Established Patterns
- None yet — this phase establishes the patterns all subsequent phases follow

### Integration Points
- This phase creates the `custom_components/irrigation_monitor/` structure that Phase 2 (Config Flow) extends
- `manifest.json` domain must match the folder name exactly

</code_context>

<specifics>
## Specific Ideas

- HACS custom repository workflow: HACS → ⋮ → Custom Repositories → paste GitHub URL → Integration category. Works with private repos via GitHub token.
- Domain change policy: freely changeable during development (only developer uses it); treat as locked once submitted to HACS default catalog.

</specifics>

<deferred>
## Deferred Ideas

- GitHub Actions CI (run pytest on push) — v2 requirement (INFRA-04)

</deferred>

---

*Phase: 01-scaffold*
*Context gathered: 2026-03-19*
