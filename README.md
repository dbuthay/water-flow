# Irrigation Monitor

Home Assistant custom integration for irrigation water flow monitoring and automatic leak detection.

## Installation

Add this repository as a custom repository in HACS.

## Dashboard Card

After installing the integration, you must register the Lovelace card JS file as a resource in Home Assistant. **This step is required** — the integration makes the file available at the URL, but HA does not auto-load it into the Lovelace frontend. Without this step, the card type will show as "unknown" when you try to add it.

### Step 1: Register the Lovelace Resource

1. Go to **Settings > Dashboards**
2. Click the three-dots menu (top right) and select **Resources**
3. Click **Add Resource**
4. Set the URL to: `/local/irrigation-monitor-card.js`
5. Set the resource type to: **JavaScript Module**
6. Click **Create**

### Step 2: Add the Card to a Dashboard

1. Edit a dashboard and click **Add Card**
2. Search for **"Irrigation Monitor"** in the card picker
3. Select the card and click **Add to Dashboard**

Or add it manually with YAML configuration:

```yaml
type: custom:irrigation-monitor-card
title: "My Irrigation"  # optional, defaults to "Irrigation Monitor"
```

### What the Card Shows

- All monitored irrigation zones — auto-discovered, no entity configuration needed
- Zone tiles with a state indicator:
  - **Idle** — grey tint, water-off icon
  - **Running** — blue tint, water icon, current flow rate
  - **Leak detected** — red tint, warning icon
- Current flow rate for active zones (gal/min)
- Today's water usage per zone (gal)

## Status

Under development.
