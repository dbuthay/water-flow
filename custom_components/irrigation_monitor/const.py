"""Constants for the Irrigation Monitor integration."""

DOMAIN = "irrigation_monitor"

# Config flow keys (stored in ConfigEntry.data)
CONF_FLUME_ENTITY_ID = "flume_entity_id"
CONF_MONITORED_ZONES = "monitored_zone_entity_ids"
CONF_POLL_INTERVAL = "poll_interval"

# Options flow keys (stored in ConfigEntry.options)
CONF_ZONES = "zones"
CONF_SHUTOFF_ENABLED = "shutoff_enabled"
CONF_ALERTS_ENABLED = "alerts_enabled"
CONF_CALIBRATED_FLOW = "calibrated_flow"
CONF_THRESHOLD_MULTIPLIER = "threshold_multiplier"

# Defaults
DEFAULT_POLL_INTERVAL = 30
DEFAULT_SHUTOFF_ENABLED = True
DEFAULT_ALERTS_ENABLED = True
DEFAULT_THRESHOLD_MULTIPLIER = 1.5

# Valve discovery domains
VALVE_DOMAINS = {"switch", "valve", "binary_sensor"}
