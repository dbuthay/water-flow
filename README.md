# Irrigation Monitor

Home Assistant custom integration for irrigation water flow monitoring and automatic leak detection.

## Requirements

Before installing, ensure these are already set up in Home Assistant:
- **Flume water sensor** integration (exposes a flow rate sensor entity)
- **Irrigation controller** integration (exposes valve entities as switches or binary sensors)

## Installation

### 1. Install via HACS

Add this repository as a custom repository in HACS (category: Integration), then install "Irrigation Monitor".

### 2. Restart Home Assistant

Required after installation so HA loads the integration code.

### 3. Add the Integration

Go to **Settings > Devices & Services > Integrations tab** and click **+ Add Integration** (bottom right). Search for **"Irrigation Monitor"** and complete the setup wizard:

- **Step 1:** Select your Flume flow sensor entity from the dropdown
- **Step 2:** Select which valve entities to monitor

The integration will not appear in the Integrations list until this step is done. HACS installs the files; this step activates the integration.

### 4. Register the Lovelace Card Resource

The dashboard card requires a one-time resource registration. Go to **Settings > Dashboards**, click the three-dots menu (top right), select **Resources**, then **Add Resource**:

- **URL:** `/irrigation_monitor/irrigation-monitor-card.js`
- **Resource type:** JavaScript Module

Click **Create**, then hard-refresh your browser (Ctrl+Shift+R / Cmd+Shift+R).

> **Note:** The resource URL uses the `/irrigation_monitor/` prefix, not `/local/`. Using `/local/` will result in a 404 because that path is reserved by HA for the config `www` directory.

### 5. Add the Card to a Dashboard

Edit a dashboard, click **Add Card**, and search for **"Irrigation Monitor"**. Select it and click **Add to Dashboard**.

Or add it manually with YAML:

```yaml
type: custom:irrigation-monitor-card
title: "My Irrigation"  # optional, defaults to "Irrigation Monitor"
```

The card auto-discovers all monitored zones — no entity configuration needed.

## Dashboard Card

Each zone is shown as a tile in a responsive grid:

| State | Appearance |
|-------|-----------|
| Idle | Grey tint, water-off icon |
| Running | Blue tint, water icon, current flow rate |
| Leak detected | Red tint, warning icon |

Each tile shows: zone name, current flow rate (gal/min), and today's water usage (gal).

## Features

- **Zone monitoring** — tracks flow rate and daily usage per zone
- **Calibration** — press the calibrate button per zone to record its expected flow rate
- **Leak detection** — auto-shuts off a valve and fires a notification if flow exceeds the calibrated baseline by a configurable multiplier
- **Re-calibration** — shows old vs. new value with Save/Cancel action buttons (requires Home Assistant Companion app on iOS/Android to see action buttons)
- **Per-zone toggles** — enable/disable auto-shutoff and alerts independently per zone via integration options

## Troubleshooting

**Card not appearing in the card picker:**
1. Verify the resource URL is exactly `/irrigation_monitor/irrigation-monitor-card.js` (not `/local/...`)
2. Confirm the integration is set up (Settings > Devices & Services > Integrations — "Irrigation Monitor" should be listed)
3. Hard-refresh the browser after adding the resource

**404 on the resource URL:**
The integration must be set up (step 3) before the file is served. If it is set up, check Settings > System > Logs and filter for `irrigation_monitor` to see registration errors.

**Calibration action buttons not appearing:**
Save/Cancel buttons on re-calibration notifications are only visible in the Home Assistant Companion mobile app (iOS/Android). They do not appear in the HA web frontend.
