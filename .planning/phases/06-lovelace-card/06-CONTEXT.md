# Phase 6: Lovelace Card - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a custom Lovelace card (`irrigation-monitor-card`) distributed in `www/irrigation-monitor-card.js` that displays all monitored irrigation zones in a responsive grid of tiles. The card auto-discovers zones by scanning HA entity states for the integration's status sensor pattern. Each tile shows zone name, status icon+color, current flow rate, and daily usage. Card is distributed via HACS as a frontend resource.

Requirements: CARD-01, CARD-02, CARD-03

</domain>

<decisions>
## Implementation Decisions

### Layout
- **Grid of zone tiles** — responsive CSS grid, tiles wrap based on available width
- **State dominates each tile** — large icon + color tint communicates state at a glance; zone name and numbers are secondary
- Tile structure (top to bottom):
  1. Icon (large, centered) — communicates state
  2. Zone name — from entity friendly_name
  3. Flow rate — shown when zone is running (hidden or "0 gal/min" when idle)
  4. Daily usage — always shown (e.g., "3.2 gal today")

### Zone State Visuals
- **Icon + color tint combination** per state:
  - `idle`: grey tint + pause/droplet icon (e.g., 💧 or ⏸)
  - `running`: blue/green tint + water flow icon (e.g., 💦 or ▶)
  - `leak_detected`: **red tint + warning icon** (⚠️) — no animation; clear and static
- Icon + color choice is Claude's discretion for exact SVG/emoji/HA icon names

### Card Configuration
- **Auto-discover**: card scans `hass.states` for entities matching `sensor.*_status` where the state is `idle`, `running`, or `leak_detected` (integration-specific values) — no entity list required
- **Optional title**: configurable via card YAML as `title: "My Irrigation"` — defaults to `"Irrigation Monitor"` if not set
- **No other required config** — add the card type and it works

### Card Type Registration
```javascript
window.customCards = window.customCards || [];
window.customCards.push({
  type: "irrigation-monitor-card",
  name: "Irrigation Monitor",
  description: "Zone status, flow rates, and daily usage"
});
customElements.define("irrigation-monitor-card", IrrigationMonitorCard);
```

### Tech Stack
- **Vanilla Web Component** (`class IrrigationMonitorCard extends HTMLElement`) — no Lit/TypeScript/Rollup required for a card this simple; reduces build complexity
- HA calls `set hass(hass)` on every state change — card diffs and re-renders
- HA calls `setConfig(config)` on card setup — reads `config.title`
- Single bundled `.js` file: `custom_components/irrigation_monitor/www/irrigation-monitor-card.js`
- Registered as HA static path in `__init__.py`: `hass.http.register_static_path("/local/irrigation-monitor-card.js", path, True)`
- No build step — single JS file authored directly

### HACS Distribution
- Frontend resources in HACS: card `.js` file placed in `custom_components/irrigation_monitor/www/`
- HA resource registration in `__init__.py` using `homeassistant.components.frontend.async_register_panel` or `hass.http.register_static_path`
- User adds Lovelace resource URL: `/local/irrigation-monitor-card.js`

### Entity Discovery Pattern
```javascript
set hass(hass) {
  this._hass = hass;
  const zones = Object.entries(hass.states)
    .filter(([id, state]) =>
      id.startsWith("sensor.") &&
      id.endsWith("_status") &&
      ["idle", "running", "leak_detected"].includes(state.state)
    )
    .map(([statusId, statusState]) => {
      const prefix = statusId.replace("_status", "");
      return {
        statusId,
        name: statusState.attributes.friendly_name || statusId,
        status: statusState.state,
        flowRate: hass.states[prefix + "_flow_rate"]?.state ?? "0",
        dailyUsage: hass.states[prefix + "_daily_usage"]?.state ?? "0",
      };
    });
  this._render(zones);
}
```

### Claude's Discretion
- Exact icon names/SVG (HA MDI icons or emoji)
- Exact CSS color values for states
- Whether to show flow rate as "0 gal/min" or hide it when idle
- Card CSS responsive breakpoints
- Whether `register_static_path` or `async_register_panel` is the correct HA API for serving the JS file

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project context
- `.planning/REQUIREMENTS.md` — CARD-01, CARD-02, CARD-03
- `.planning/research/STACK.md` — Lovelace card architecture, static path registration, HACS frontend distribution

### Integration entry points (extend)
- `custom_components/irrigation_monitor/__init__.py` — register static path for `www/irrigation-monitor-card.js`
- Entity naming pattern: `sensor.irrigation_monitor_{zone_slug}_status`, `sensor.irrigation_monitor_{zone_slug}_flow_rate`, `sensor.irrigation_monitor_{zone_slug}_daily_usage`

### No external specs — requirements fully captured in decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Entity Naming (from sensor.py)
- `sensor.*_status` — `"idle"` / `"running"` / `"leak_detected"`
- `sensor.*_flow_rate` — float gal/min, unit "gal/min"
- `sensor.*_daily_usage` — float gallons, unit "gal"
- Pattern: all share the same `{entry.entry_id}_{zone_id}` prefix (but entity_id uses zone_slug derived from zone entity_id)

### Integration Points
- `__init__.py: async_setup_entry` — add static path registration here (after coordinator setup)
- `custom_components/irrigation_monitor/www/` — create this directory, place `irrigation-monitor-card.js` here
- No new Python entity platforms needed — card is pure JS

### Established Patterns (from STACK.md research)
- Card type registration: `customElements.define()` + `window.customCards.push()` pattern
- HA calls `set hass(hass)` on every state change — no manual subscription needed
- HA calls `setConfig(config)` once at card setup

</code_context>

<specifics>
## Specific Ideas

- Discovery relies on state values "idle"/"running"/"leak_detected" being unique to this integration — reasonable assumption since these are domain-specific strings not used by other HA entities
- The `prefix + "_flow_rate"` derivation works as long as entity naming is consistent (which it is — all three sensors share the same base)
- For HACS: research whether `hass.http.register_static_path` is the correct API for HA 2026.x or if `HomeAssistantView` pattern is needed

</specifics>

<deferred>
## Deferred Ideas

- History chart / usage trend over time (CARD-04 in v2 requirements)
- None from this discussion

</deferred>

---

*Phase: 06-lovelace-card*
*Context gathered: 2026-03-24*
