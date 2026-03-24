# Phase 6: Lovelace Card - Research

**Researched:** 2026-03-23
**Domain:** Home Assistant custom Lovelace card (vanilla Web Component, static path registration)
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Grid of zone tiles** — responsive CSS grid, tiles wrap based on available width
- **State dominates each tile** — large icon + color tint; zone name and numbers are secondary
- Tile structure (top to bottom): icon, zone name, flow rate (running only), daily usage (always)
- **State visuals:** idle = grey + pause/droplet icon; running = blue/green + flow icon; leak_detected = red + warning icon (no animation)
- **Auto-discover** zones by scanning `hass.states` for `sensor.*_status` with values `idle`/`running`/`leak_detected`
- **Optional title** via card YAML `title:` — defaults to `"Irrigation Monitor"`
- **Vanilla Web Component** (`class IrrigationMonitorCard extends HTMLElement`) — no Lit/TypeScript/Rollup
- Single JS file: `custom_components/irrigation_monitor/www/irrigation-monitor-card.js`
- Static path registered in `__init__.py`: `hass.http.register_static_path("/local/irrigation-monitor-card.js", path, True)`
- Card type registration: `window.customCards.push({...})` + `customElements.define("irrigation-monitor-card", ...)`
- Discovery pattern: iterate `hass.states`, filter by `sensor.*_status` with valid state values, derive `_flow_rate` and `_daily_usage` sibling entities by replacing `_status` suffix

### Claude's Discretion
- Exact icon names/SVG (HA MDI icons or emoji)
- Exact CSS color values for states
- Whether to show flow rate as "0 gal/min" or hide it when idle
- Card CSS responsive breakpoints
- Whether `register_static_path` or `async_register_panel` is the correct HA API for serving the JS file (researched below — answer: `async_register_static_paths` with `StaticPathConfig`)

### Deferred Ideas (OUT OF SCOPE)
- History chart / usage trend over time (CARD-04 v2 requirement)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CARD-01 | Custom Lovelace card displays all monitored zones with their current state (idle / running / leak detected) | Vanilla Web Component lifecycle confirmed; entity discovery pattern from CONTEXT.md validated against sensor.py entity naming |
| CARD-02 | Card shows the current flow rate for each active zone | `sensor.irrigation_monitor_{zone_slug}_flow_rate` exists and is accessible via `hass.states`; sibling entity derivation pattern confirmed |
| CARD-03 | Card shows today's water usage per zone | `sensor.irrigation_monitor_{zone_slug}_daily_usage` exists; same derivation pattern |
</phase_requirements>

---

## Summary

This phase builds a single vanilla JavaScript file that registers as a custom Lovelace card element. No build toolchain is needed — the file is authored directly. Home Assistant's `hass.http.async_register_static_paths` (with `StaticPathConfig`) serves the file from `custom_components/irrigation_monitor/www/` at the URL path `/local/irrigation-monitor-card.js`. Users manually add that URL as a Lovelace resource (type: `module`), or HACS can do it via its resource management.

The card lifecycle is straightforward: HA calls `setConfig(config)` once at card insertion and `set hass(hass)` on every state update. The card re-renders on every `hass` update by replacing `innerHTML` of its shadow root. CSS Grid in the shadow DOM works identically to normal CSS Grid — shadow DOM does not restrict CSS layout. The `window.customCards` registration makes the card visible in the "Add Card" dialog; it runs immediately after `customElements.define`.

**Primary recommendation:** Use `hass.http.async_register_static_paths([StaticPathConfig("/local/irrigation-monitor-card.js", path, True)])` in `async_setup_entry`. No Python changes to `async_unload_entry` are needed — static paths are request-routing additions that persist for the HA session.

---

## Standard Stack

### Core
| Library / API | Version | Purpose | Why Standard |
|---------------|---------|---------|--------------|
| Web Components (HTMLElement) | Native browser | Card base class | No dependency, no build step, official HA docs show this pattern |
| `hass.http.async_register_static_paths` | HA 2024.7+ | Serve JS file over HTTP | Current async API replacing legacy `register_static_path` (sync) |
| `homeassistant.components.http.StaticPathConfig` | HA 2024.7+ | Typed config for static path registration | Required parameter type for `async_register_static_paths` |
| CSS Grid | Native browser | Responsive tile layout | No dependencies; works in shadow DOM |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `window.customCards` array | HA convention | Card picker registration | Always — makes card visible in "Add Card" dialog |
| `customElements.define()` | Web standard | Register custom element | Always — required before HA can instantiate the card |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Vanilla HTMLElement | LitElement | Lit adds reactive property system and template rendering, but requires build step — overkill for this card's complexity |
| `async_register_static_paths` | `HomeAssistantView` subclass | View gives more control (auth, routing) but is designed for REST endpoints, not static file serving |
| CSS Grid | CSS Flexbox | Flexbox is fine for single-axis layouts; CSS Grid gives better 2D wrapping tile control |

**Installation (Python side — no npm packages):**
```bash
# No new Python dependencies. StaticPathConfig is part of homeassistant.components.http.
# The www/ directory must exist before HA loads the entry:
mkdir -p custom_components/irrigation_monitor/www
```

---

## Architecture Patterns

### Recommended Project Structure
```
custom_components/irrigation_monitor/
├── __init__.py          # ADD: import StaticPathConfig, call async_register_static_paths
├── www/
│   └── irrigation-monitor-card.js   # NEW: entire card implementation
└── (existing files unchanged)
```

### Pattern 1: Static Path Registration in async_setup_entry

**What:** Register the `www/` directory (or the single `.js` file) as a static HTTP path so HA serves it at `/local/irrigation-monitor-card.js`.

**When to use:** Once, inside `async_setup_entry`, after the coordinator is set up.

**Correct API for HA 2024.7+:**
```python
# Source: WebRTC integration utils.py + HA core http/__init__.py
from pathlib import Path
from homeassistant.components.http import StaticPathConfig

async def async_setup_entry(hass: HomeAssistant, entry: IrrigationConfigEntry) -> bool:
    coordinator = IrrigationCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register www/ JS file as a static resource
    www_path = str(Path(__file__).parent / "www" / "irrigation-monitor-card.js")
    await hass.http.async_register_static_paths(
        [StaticPathConfig("/local/irrigation-monitor-card.js", www_path, True)]
    )
    return True
```

**Note on the third `True` argument:** The boolean is `cache_headers`. Set to `True` in production (browser caches the file). During development, set to `False` to avoid stale-cache issues while iterating.

**Note on double-registration:** If the integration is loaded more than once (e.g., multiple config entries), calling `async_register_static_paths` for the same URL path a second time raises an error. Guard with a module-level flag or register in `async_setup` (the domain-level setup called once) rather than `async_setup_entry` (called per config entry). Since irrigation_monitor only ever has one config entry, this is not a practical concern here — but it is a known pitfall.

### Pattern 2: Vanilla Web Component Card Skeleton

**What:** Minimal HTMLElement subclass satisfying HA's Lovelace card contract.

**Required methods:** `setConfig(config)` (REQUIRED), `set hass(hass)` (REQUIRED), `getCardSize()` (strongly recommended — defaults to 1 if absent).

**Optional methods:** `getConfigElement()` (visual editor), `getStubConfig()` (default config for card picker), `getGridOptions()` (sections view layout hints).

**Example skeleton:**
```javascript
// Source: HA developer docs (developers.home-assistant.io/docs/frontend/custom-ui/custom-card/)
class IrrigationMonitorCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = null;
  }

  setConfig(config) {
    // Called once when card is added/edited. Validate here.
    this._config = { title: "Irrigation Monitor", ...config };
    this._render([]);  // render empty state immediately
  }

  set hass(hass) {
    // Called on every HA state change. Keep cheap.
    this._hass = hass;
    const zones = this._discoverZones(hass);
    this._render(zones);
  }

  getCardSize() {
    // 1 unit ≈ 50px. A 2-row tile grid is roughly 4 units.
    return 4;
  }

  _discoverZones(hass) {
    return Object.entries(hass.states)
      .filter(([id, state]) =>
        id.startsWith("sensor.") &&
        id.endsWith("_status") &&
        ["idle", "running", "leak_detected"].includes(state.state)
      )
      .map(([statusId, statusState]) => {
        const prefix = statusId.replace(/_status$/, "");
        return {
          name: statusState.attributes.friendly_name || statusId,
          status: statusState.state,
          flowRate: hass.states[prefix + "_flow_rate"]?.state ?? "0",
          flowUnit: hass.states[prefix + "_flow_rate"]?.attributes?.unit_of_measurement ?? "gal/min",
          dailyUsage: hass.states[prefix + "_daily_usage"]?.state ?? "0",
          dailyUnit: hass.states[prefix + "_daily_usage"]?.attributes?.unit_of_measurement ?? "gal",
        };
      });
  }

  _render(zones) {
    // Replace shadow root content on every call — simple and correct for this card's size
    this.shadowRoot.innerHTML = `
      <style>${this._styles()}</style>
      <ha-card header="${this._config.title}">
        <div class="grid">
          ${zones.map(z => this._renderTile(z)).join("")}
          ${zones.length === 0 ? '<p class="empty">No irrigation zones found.</p>' : ""}
        </div>
      </ha-card>
    `;
  }

  _renderTile(zone) { /* ... */ }
  _styles() { return `/* CSS here */`; }
}

// Registration — window.customCards BEFORE customElements.define is fine;
// order within the same script execution context does not matter.
window.customCards = window.customCards || [];
window.customCards.push({
  type: "irrigation-monitor-card",
  name: "Irrigation Monitor",
  description: "Zone status, flow rates, and daily usage",
});
customElements.define("irrigation-monitor-card", IrrigationMonitorCard);
```

### Pattern 3: CSS Grid in Shadow DOM

**What:** Standard CSS Grid works identically inside a shadow root. There is no restriction.

**Responsive tile grid (auto-fill, min tile width ~180px):**
```css
/* Source: standard CSS Grid — no HA-specific behavior */
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
  padding: 12px;
}

.tile {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px 12px;
  border-radius: 8px;
  text-align: center;
  transition: background-color 0.2s;
}

/* State-based color tints */
.tile.idle    { background: rgba(128, 128, 128, 0.15); }
.tile.running { background: rgba(33, 150, 243, 0.15); }
.tile.leak_detected { background: rgba(244, 67, 54, 0.15); }

.tile .icon { font-size: 2.5rem; margin-bottom: 8px; }
.tile .name { font-weight: 500; font-size: 0.9rem; margin-bottom: 4px; }
.tile .flow { font-size: 0.8rem; color: var(--secondary-text-color); }
.tile .usage { font-size: 0.8rem; color: var(--secondary-text-color); }
```

**HA CSS custom properties available inside shadow DOM** (inherited from host):
- `--primary-text-color`
- `--secondary-text-color`
- `--card-background-color`
- `--primary-color`
- `--error-color` (maps well to leak state)

CSS custom properties (variables) **do pierce shadow DOM** by design — they are the approved mechanism for theming web components.

### Pattern 4: window.customCards Registration

**What:** Pushes card metadata into a global array that HA's card picker reads at dashboard-open time.

**When:** This code runs at script load (top level), immediately after the card class is defined. The `customElements.define` call is what actually registers the element with the browser; `window.customCards` just provides display metadata to HA.

**Order:** Push to `window.customCards` either before or after `customElements.define` — both work because the card picker reads the array lazily when the dashboard opens, not at script load.

```javascript
// Source: HA developer docs
window.customCards = window.customCards || [];
window.customCards.push({
  type: "irrigation-monitor-card",  // must match string passed to customElements.define
  name: "Irrigation Monitor",
  description: "Zone status, flow rates, and daily usage",
});
customElements.define("irrigation-monitor-card", IrrigationMonitorCard);
```

### Anti-Patterns to Avoid

- **Calling `async_register_static_paths` per config entry without a guard:** If somehow two config entries exist, the second registration crashes. Use `async_setup` (domain level) or a module-level flag.
- **Registering the `www/` directory instead of the specific file:** Serving the whole directory as `/local/` conflicts with HA's own `/local/` path (which serves `<config>/www/`). Register the specific file path to `/local/irrigation-monitor-card.js`.
- **Using `innerHTML` with unsanitized entity data in the tile render:** The `friendly_name` attribute from HA comes from the entity registry — it's user-controlled and could contain HTML. Use `textContent` assignment or escape it.
- **Calling expensive JS in every `set hass` invocation:** HA fires `set hass` on _every_ state change in the system. Keep `_discoverZones` and `_render` cheap. Full `innerHTML` replacement is acceptable for a small grid (< 20 zones); for larger grids, diff the DOM.
- **`getConfigElement()` is NOT required.** HA renders a raw YAML editor as fallback. Implementing it adds significant complexity; skip for v1.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Serving a static JS file | Custom HTTP view subclass | `hass.http.async_register_static_paths` + `StaticPathConfig` | Built-in; handles caching headers, path collision detection |
| CSS grid responsive layout | JavaScript resize observer + column calculator | `grid-template-columns: repeat(auto-fill, minmax(180px, 1fr))` | One CSS line; browser handles all resize math |
| Card picker registration | Custom HA event or hook | `window.customCards.push()` | Official HA convention; anything else won't work |
| Card editing UI | Custom form elements | Skip (raw YAML fallback) or `getConfigForm()` schema | `getConfigElement()` requires building a second custom element; not needed for a simple `title` config |
| HA CSS theming | Hardcoded hex colors | `var(--primary-color)`, `var(--error-color)`, `var(--secondary-text-color)` | Automatically adapts to HA themes; CSS vars pierce shadow DOM |

**Key insight:** The entire non-trivial complexity of this phase lives in one JS file. There is no Python complexity beyond a two-line static path registration. Do not over-engineer the Python side.

---

## Common Pitfalls

### Pitfall 1: `register_static_path` (singular, synchronous) is the OLD API

**What goes wrong:** Calling `hass.http.register_static_path(url, path)` (singular, no `await`) works in HA < 2024.7 but is deprecated and removed in later versions. Using it causes a `TypeError` or `AttributeError` on current HA.

**Why it happens:** The CONTEXT.md and STACK.md both reference `hass.http.register_static_path` — this is the legacy form. The current API (HA 2024.7+) is `await hass.http.async_register_static_paths([StaticPathConfig(...)])`.

**How to avoid:** Import `StaticPathConfig` from `homeassistant.components.http` and use `async_register_static_paths` (plural, async). This is confirmed by WebRTC integration's version-gated utility.

**Confidence:** HIGH — confirmed via HA core source at `homeassistant/components/http/__init__.py`

### Pitfall 2: Lovelace resource must be manually added by the user (or HACS)

**What goes wrong:** Registering a static path makes the file _servable_ — it does NOT make HA _load_ it. The user must also add a Lovelace resource entry pointing to the URL. Without this, the browser never fetches the JS and the card type is unknown.

**Why it happens:** Lovelace resource management and HTTP static path registration are two separate HA systems. `async_register_static_paths` only tells aiohttp to serve the file; Lovelace resources tell the frontend to `<script type="module">` load it.

**How to avoid:** Document clearly in the integration README that the user must add:
- URL: `/local/irrigation-monitor-card.js`
- Type: `JavaScript Module`

HACS performs this step automatically for repositories that declare the resource in `hacs.json` under the `frontend` category. For a `custom_components` integration (not a standalone frontend card repo), the user adds it manually.

**Alternative (programmatic):** It is possible to programmatically register a Lovelace resource using the `lovelace` HA integration's storage API, but this is undocumented, fragile, and not recommended. Do not implement this.

**Confidence:** HIGH — confirmed via HA developer docs (registering resources page)

### Pitfall 3: Entity ID collision in zone discovery (false positives from other integrations)

**What goes wrong:** The discovery filter `id.startsWith("sensor.") && id.endsWith("_status") && ["idle","running","leak_detected"].includes(state.state)` could theoretically match a `sensor.*_status` entity from another integration that happens to use the same state string values.

**Why it happens:** `idle`, `running`, and `leak_detected` are not globally reserved. Another integration could produce them.

**How to avoid:** The CONTEXT.md accepted this risk as reasonable — these are domain-specific strings unlikely to collide in practice. No action needed. The risk is noted for documentation.

**Confidence:** MEDIUM — reasoning, not tested

### Pitfall 4: `innerHTML` XSS from entity friendly_name

**What goes wrong:** Setting `innerHTML` with `${zone.name}` where `zone.name` comes from `statusState.attributes.friendly_name` allows a user who controls entity names to inject HTML/JS into the card's shadow DOM.

**Why it happens:** `innerHTML` interprets the string as HTML markup.

**How to avoid:** Use `element.textContent = zone.name` for the zone name text node, or escape `<`, `>`, `&` before inserting into innerHTML template. The simplest fix in a template literal is to create elements and set `textContent` directly rather than using a template string for user-supplied values.

**Confidence:** HIGH — standard web security

### Pitfall 5: `set hass` called before `setConfig`

**What goes wrong:** HA _should_ always call `setConfig` before `set hass`, but defensive coding is required. If `this._config` is `undefined` when `set hass` fires, any `this._config.title` access throws.

**Why it happens:** Race conditions in HA card initialization, or card being instantiated and added to the DOM before the config is applied.

**How to avoid:** Initialize `this._config = {}` in the constructor. Guard in `set hass`: `if (!this._config) return;`

**Confidence:** HIGH — standard Web Component defense

### Pitfall 6: www/ directory must exist before HA loads the entry

**What goes wrong:** If `www/irrigation-monitor-card.js` does not exist when `async_setup_entry` calls `async_register_static_paths`, the call may succeed (path validation is lazy in aiohttp) but requests to the URL will 404.

**Why it happens:** `StaticPathConfig` accepts a path string without immediately verifying the file exists on disk.

**How to avoid:** Create the `www/` directory and the JS file as part of this phase. Check that the file exists in the path string before registering. HA's `async_register_static_paths` works equally well with a file path or a directory path — using the specific file path is safer.

**Confidence:** MEDIUM — inferred from aiohttp static resource behavior

---

## Code Examples

Verified patterns from official sources:

### Static path registration (current HA 2024.7+ API)
```python
# Source: HA core homeassistant/components/http/__init__.py + WebRTC utils.py
from pathlib import Path
from homeassistant.components.http import StaticPathConfig

www_path = str(Path(__file__).parent / "www" / "irrigation-monitor-card.js")
await hass.http.async_register_static_paths(
    [StaticPathConfig("/local/irrigation-monitor-card.js", www_path, True)]
)
```

### Complete card registration block
```javascript
// Source: HA developer docs (developers.home-assistant.io/docs/frontend/custom-ui/custom-card/)
window.customCards = window.customCards || [];
window.customCards.push({
  type: "irrigation-monitor-card",
  name: "Irrigation Monitor",
  description: "Zone status, flow rates, and daily usage",
});
customElements.define("irrigation-monitor-card", IrrigationMonitorCard);
```

### Zone discovery from hass.states
```javascript
// Source: CONTEXT.md decision, validated against sensor.py entity_id pattern
// Entity IDs: sensor.irrigation_monitor_{zone_slug}_status
//             sensor.irrigation_monitor_{zone_slug}_flow_rate
//             sensor.irrigation_monitor_{zone_slug}_daily_usage
_discoverZones(hass) {
  return Object.entries(hass.states)
    .filter(([id, state]) =>
      id.startsWith("sensor.") &&
      id.endsWith("_status") &&
      ["idle", "running", "leak_detected"].includes(state.state)
    )
    .map(([statusId, statusState]) => {
      const prefix = statusId.replace(/_status$/, "");
      return {
        name: statusState.attributes.friendly_name || statusId,
        status: statusState.state,
        flowRate: hass.states[prefix + "_flow_rate"]?.state ?? "0",
        flowUnit: hass.states[prefix + "_flow_rate"]?.attributes?.unit_of_measurement ?? "gal/min",
        dailyUsage: hass.states[prefix + "_daily_usage"]?.state ?? "0",
        dailyUnit: hass.states[prefix + "_daily_usage"]?.attributes?.unit_of_measurement ?? "gal",
      };
    });
}
```

### CSS custom property icon map (suggested)
```javascript
// Icon choice at Claude's discretion — emoji work in all browsers with no dependencies
const STATE_ICON = {
  idle:          "💧",
  running:       "💦",
  leak_detected: "⚠️",
};
const STATE_COLOR_CLASS = {
  idle:          "idle",
  running:       "running",
  leak_detected: "leak_detected",
};
```

### HA CSS variables inside shadow DOM
```css
/* Source: HA theming system — CSS custom properties pierce shadow DOM by spec */
.tile { color: var(--primary-text-color); }
.tile .flow { color: var(--secondary-text-color); }
.tile.leak_detected { background: color-mix(in srgb, var(--error-color) 20%, transparent); }
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `hass.http.register_static_path(url, path)` (sync) | `await hass.http.async_register_static_paths([StaticPathConfig(...)])` | HA 2024.7 | Must use async plural form; singular sync is removed |
| `www/` at repo root (for standalone HACS frontend cards) | `custom_components/{domain}/www/` (for integration-bundled cards) | HACS convention | Integration cards live inside `custom_components/`, not at repo root |
| LitElement required | Plain HTMLElement works fine | Always supported; Lit just adds DX | No build step needed for simple cards |
| Registering resources via `lovelace.yaml` | UI-based resource registration or HACS automatic | HA 2023+ | Users prefer UI; document the `/local/` URL they need to add |

**Deprecated/outdated:**
- `hass.http.register_static_path` (singular, sync): removed in HA 2024.7+
- STACK.md recommendation to use Lit + TypeScript + Rollup: correct for complex cards but unnecessary here — locked decision is vanilla HTMLElement

---

## Validation Architecture

> `nyquist_validation: true` in `.planning/config.json` — section included.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-homeassistant-custom-component 0.13.316 |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `pytest tests/test_init.py -x -q` |
| Full suite command | `pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CARD-01 | `async_setup_entry` registers static path without error | integration (Python) | `pytest tests/test_card_setup.py::test_static_path_registered -x` | ❌ Wave 0 |
| CARD-01 | JS file exists at expected path | smoke (filesystem) | `pytest tests/test_card_setup.py::test_www_file_exists -x` | ❌ Wave 0 |
| CARD-02 | `_discoverZones` returns flow rate from sibling entity | unit (JS logic — not automatable via pytest) | Manual / browser console | N/A — manual |
| CARD-03 | `_discoverZones` returns daily usage from sibling entity | unit (JS logic — not automatable via pytest) | Manual / browser console | N/A — manual |

**Note on JS testing:** The card is a single JS file with no build step and no Node.js test runner configured. JS unit tests (e.g., with Jest or Deno) are out of scope — the CONTEXT.md specifies no build step. The discovery logic is simple enough that a manual smoke test in a running HA instance suffices. Python tests cover the only automatable assertion: that `async_setup_entry` succeeds and registers the static path.

### Sampling Rate
- **Per task commit:** `pytest tests/test_card_setup.py -x -q`
- **Per wave merge:** `pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_card_setup.py` — covers CARD-01 (static path registration, file existence)
- [ ] No new fixtures needed — existing `mock_config_entry` from `conftest.py` is sufficient

---

## Open Questions

1. **Double-registration guard for static path**
   - What we know: `async_register_static_paths` raises if the same URL is registered twice (confirmed by aiohttp behavior)
   - What's unclear: Whether HA 2026.x added idempotent registration (some HA internals do deduplicate)
   - Recommendation: Add a guard — check if already registered, or move registration to `async_setup` (runs once per domain, not per entry). Since this integration has exactly one config entry in practice, this is low priority but worth a try/except.

2. **`ha-card` element vs plain `div` as card root**
   - What we know: HA core cards use `<ha-card>` custom element as their outermost element; it provides the card chrome (shadow, elevation, header styling)
   - What's unclear: Whether `<ha-card>` is importable/available from the global scope in the Lovelace frontend context without explicit import
   - Recommendation: Use `<ha-card>` — it is always available in the Lovelace runtime global scope (loaded by HA frontend before custom cards execute). If rendering breaks, fall back to a plain `<div class="card-content">`.

3. **Lovelace resource registration: manual vs programmatic**
   - What we know: The user must add `/local/irrigation-monitor-card.js` as a resource manually, or HACS does it
   - What's unclear: Whether `hacs.json` needs a `frontend_version` or `lovelace_resources` key to enable HACS automatic resource registration for an integration-bundled card (vs a standalone frontend repo)
   - Recommendation: Document the manual step. Do not attempt programmatic resource registration via HA storage API.

---

## Sources

### Primary (HIGH confidence)
- HA core source `homeassistant/components/http/__init__.py` — `StaticPathConfig` dataclass, `async_register_static_paths` signature
- HA developer docs `developers.home-assistant.io/docs/frontend/custom-ui/custom-card/` — lifecycle methods, `window.customCards`, vanilla HTMLElement pattern
- Project `custom_components/irrigation_monitor/sensor.py` — confirmed entity ID patterns: `sensor.irrigation_monitor_{zone_slug}_status`, `_flow_rate`, `_daily_usage`

### Secondary (MEDIUM confidence)
- WebRTC integration `custom_components/webrtc/utils.py` — version-gated `async_register_static_paths` usage pattern with `StaticPathConfig` (live repo, current)
- HACS integration `custom_components/hacs/frontend.py` — `async_register_static_path` call site demonstrating production usage
- HA developer docs (registering resources page) — confirms static path != Lovelace resource; user must add resource manually

### Tertiary (LOW confidence)
- `double-registration` behavior for `async_register_static_paths`: inferred from aiohttp static resource semantics, not tested directly

---

## Metadata

**Confidence breakdown:**
- Static path API: HIGH — confirmed via HA core source and two production integrations
- Card lifecycle (setConfig, set hass, getCardSize): HIGH — confirmed via official HA developer docs
- CSS Grid in shadow DOM: HIGH — CSS specification (custom properties pierce shadow DOM by design)
- window.customCards pattern: HIGH — confirmed via official HA developer docs
- HACS automatic resource registration for integration-bundled cards: LOW — not verified; recommend manual documentation

**Research date:** 2026-03-23
**Valid until:** 2026-09-23 (stable HA APIs; Lovelace card contract has been stable for 3+ years)
