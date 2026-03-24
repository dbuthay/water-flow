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

# Storage
STORAGE_KEY = "irrigation_monitor.daily_usage"
STORAGE_VERSION = 1
SAVE_DELAY = 30  # seconds — debounce Store writes

# Leak detection
CONF_RAMP_UP_POLLS = "ramp_up_polls"
DEFAULT_RAMP_UP_POLLS = 2

# Calibration
CONF_BACKGROUND_THRESHOLD = "background_flow_threshold"
DEFAULT_BACKGROUND_THRESHOLD = 0.1  # gal/min
VARIANCE_THRESHOLD = 0.05  # std_dev threshold for stabilization
STABILIZATION_TIMEOUT = 60  # seconds max wait for flow to stabilize
STABILIZATION_POLL_INTERVAL = 5  # seconds between readings
SAMPLE_COUNT = 3  # number of readings to average
SAMPLE_INTERVAL = 5  # seconds between sample readings
