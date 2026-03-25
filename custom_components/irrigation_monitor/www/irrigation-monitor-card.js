/**
 * Irrigation Monitor Card
 * Custom Lovelace card for Home Assistant
 * Displays zone status, flow rates, and daily usage in a responsive grid.
 */
class IrrigationMonitorCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = null;
  }

  setConfig(config) {
    this._config = { title: "Irrigation Monitor", ...config };
    if (!this.shadowRoot) return;
    this._render([]);
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._config) return;
    const zones = this._discoverZones(hass);
    this._render(zones);
  }

  getCardSize() {
    return 4;
  }

  _discoverZones(hass) {
    return Object.entries(hass.states)
      .filter(
        ([id, stateObj]) =>
          id.startsWith("sensor.") &&
          id.endsWith("_status") &&
          ["idle", "running", "leak_detected"].includes(stateObj.state)
      )
      .map(([statusId, statusState]) => {
        const prefix = statusId.replace(/_status$/, "");
        const flowState = hass.states[prefix + "_flow_rate"];
        const usageState = hass.states[prefix + "_daily_usage"];

        // Use the original valve entity (exposed as zone_entity_id attribute)
        // to get the real friendly name and entity picture.
        const zoneEntityId = statusState.attributes.zone_entity_id;
        const valveState = zoneEntityId ? hass.states[zoneEntityId] : null;
        const name = valveState?.attributes?.friendly_name
          || statusState.attributes.friendly_name
          || statusId;
        const picture = valveState?.attributes?.entity_picture || null;

        return {
          name: this._cleanZoneName(name),
          status: statusState.state,
          flowRate: flowState ? parseFloat(flowState.state) || 0 : 0,
          flowUnit: flowState?.attributes?.unit_of_measurement ?? "gal/min",
          dailyUsage: usageState ? parseFloat(usageState.state) || 0 : 0,
          dailyUnit: usageState?.attributes?.unit_of_measurement ?? "gal",
          picture: picture,
        };
      });
  }

  _cleanZoneName(name) {
    if (!name) return "Zone";
    // Strip leading domain word (switch, valve, binary_sensor) if present,
    // then strip trailing "status" if present, then humanize underscores.
    // Mirrors the entity registry friendly name resolution in the config wizard.
    return name
      .replace(/^(switch|valve|binary_sensor|sensor)\s+/i, "")
      .replace(/\s*status$/i, "")
      .replace(/_/g, " ")
      .trim() || "Zone";
  }

  _escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  _render(zones) {
    if (!this.shadowRoot) return;

    const title = this._escapeHtml(this._config.title);

    this.shadowRoot.innerHTML = `
      <style>${this._styles()}</style>
      <ha-card header="${title}">
        <div class="grid">
          ${
            zones.length === 0
              ? '<p class="empty">No irrigation zones found.</p>'
              : zones.map((z) => this._renderTile(z)).join("")
          }
        </div>
      </ha-card>
    `;
  }

  _renderTile(zone) {
    const icon = this._stateIcon(zone.status);
    const name = this._escapeHtml(zone.name);
    const statusClass = zone.status.replace(/\s+/g, "_");

    const flowDisplay =
      zone.status === "running"
        ? `<div class="flow">${zone.flowRate.toFixed(1)} ${this._escapeHtml(zone.flowUnit)}</div>`
        : '<div class="flow idle-flow">0 gal/min</div>';

    // When an entity picture is available, use it as background with a
    // state-coloured overlay. Fall back to solid colour tint (no background-image).
    const bgStyle = zone.picture
      ? `style="background-image: url('${this._escapeHtml(zone.picture)}');"`
      : "";
    const hasImage = zone.picture ? " has-image" : "";

    return `
      <div class="tile ${statusClass}${hasImage}" ${bgStyle}>
        <div class="overlay"></div>
        <div class="content">
          <div class="icon">${icon}</div>
          <div class="name">${name}</div>
          ${flowDisplay}
          <div class="usage">${zone.dailyUsage.toFixed(1)} ${this._escapeHtml(zone.dailyUnit)} today</div>
        </div>
      </div>
    `;
  }

  _stateIcon(status) {
    switch (status) {
      case "idle":
        return '<ha-icon icon="mdi:water-off"></ha-icon>';
      case "running":
        return '<ha-icon icon="mdi:water"></ha-icon>';
      case "leak_detected":
        return '<ha-icon icon="mdi:alert-circle"></ha-icon>';
      default:
        return '<ha-icon icon="mdi:help-circle"></ha-icon>';
    }
  }

  _styles() {
    return `
      :host {
        --overlay-idle: rgba(80, 80, 80, 0.65);
        --overlay-running: rgba(33, 150, 243, 0.55);
        --overlay-leak: rgba(244, 67, 54, 0.65);
        --tile-idle-bg: rgba(128, 128, 128, 0.15);
        --tile-running-bg: rgba(33, 150, 243, 0.15);
        --tile-leak-bg: rgba(244, 67, 54, 0.15);
      }

      .grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
        gap: 12px;
        padding: 0 16px 16px;
      }

      /* ── Tile base ── */
      .tile {
        position: relative;
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 0;
        border-radius: 12px;
        overflow: hidden;
        text-align: center;
        background-size: cover;
        background-position: center;
      }

      /* ── Colour overlay (sits between background image and content) ── */
      .tile .overlay {
        position: absolute;
        inset: 0;
        border-radius: inherit;
      }

      /* Solid tint when no image */
      .tile.idle:not(.has-image)     { background: var(--tile-idle-bg); }
      .tile.running:not(.has-image)  { background: var(--tile-running-bg); }
      .tile.leak_detected:not(.has-image) { background: var(--tile-leak-bg); }

      /* Colour overlay when image is present */
      .tile.has-image.idle     .overlay { background: var(--overlay-idle); }
      .tile.has-image.running  .overlay { background: var(--overlay-running); }
      .tile.has-image.leak_detected .overlay { background: var(--overlay-leak); }

      /* ── Content layer (above overlay) ── */
      .tile .content {
        position: relative;
        z-index: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 16px 12px;
        width: 100%;
      }

      /* Icon colours */
      .tile.idle ha-icon          { color: var(--secondary-text-color, #888); }
      .tile.running ha-icon       { color: var(--info-color, #2196F3); }
      .tile.leak_detected ha-icon { color: var(--error-color, #f44336); }

      /* When image present, icons always white to show on coloured overlay */
      .tile.has-image ha-icon { color: #fff; }

      .tile .icon { margin-bottom: 8px; }
      .tile .icon ha-icon {
        --mdc-icon-size: 36px;
        width: 36px;
        height: 36px;
      }

      .tile .name {
        font-weight: 500;
        font-size: 0.95rem;
        color: var(--primary-text-color);
        margin-bottom: 4px;
        word-break: break-word;
      }
      .tile.has-image .name { color: #fff; text-shadow: 0 1px 3px rgba(0,0,0,0.5); }

      .tile .flow {
        font-size: 0.85rem;
        color: var(--primary-text-color);
        margin-bottom: 2px;
      }
      .tile .flow.idle-flow { color: var(--secondary-text-color, #888); }
      .tile.has-image .flow { color: rgba(255,255,255,0.9); }

      .tile .usage {
        font-size: 0.8rem;
        color: var(--secondary-text-color, #888);
      }
      .tile.has-image .usage { color: rgba(255,255,255,0.75); }

      .empty {
        padding: 16px;
        text-align: center;
        color: var(--secondary-text-color, #888);
        font-style: italic;
      }
    `;
  }
}

// Card picker registration -- BEFORE customElements.define per HA convention
window.customCards = window.customCards || [];
window.customCards.push({
  type: "irrigation-monitor-card",
  name: "Irrigation Monitor",
  description: "Zone status, flow rates, and daily usage",
});

customElements.define("irrigation-monitor-card", IrrigationMonitorCard);
