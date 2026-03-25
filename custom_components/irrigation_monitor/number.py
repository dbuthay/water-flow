"""Number platform for the Irrigation Monitor integration.

Per-zone leak detection threshold multiplier (1.1x – 2.0x). Stored in
ConfigEntry.options and read by the coordinator on every poll.
"""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    CONF_MONITORED_ZONES,
    CONF_THRESHOLD_MULTIPLIER,
    CONF_ZONES,
    DEFAULT_THRESHOLD_MULTIPLIER,
    DOMAIN,
    THRESHOLD_MULTIPLIER_MAX,
    THRESHOLD_MULTIPLIER_MIN,
    THRESHOLD_MULTIPLIER_STEP,
)
from .sensor import _zone_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up threshold multiplier number entity per monitored zone."""
    monitored: list[str] = entry.data[CONF_MONITORED_ZONES]
    entities = []
    for zone_id in monitored:
        device_info = _zone_device_info(hass, entry, zone_id)
        entities.append(ThresholdMultiplierNumber(entry, zone_id, device_info))
    async_add_entities(entities)


class ThresholdMultiplierNumber(RestoreEntity, NumberEntity):
    """Number entity for the per-zone leak detection threshold multiplier.

    e.g. 1.5 means shut off if flow > 1.5 × calibrated baseline.
    Range: 1.1 – 2.0, step 0.1.
    """

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_native_min_value = THRESHOLD_MULTIPLIER_MIN
    _attr_native_max_value = THRESHOLD_MULTIPLIER_MAX
    _attr_native_step = THRESHOLD_MULTIPLIER_STEP
    _attr_native_unit_of_measurement = "×"
    _attr_mode = NumberMode.BOX

    def __init__(self, entry: ConfigEntry, zone_id: str, device_info) -> None:
        self._entry = entry
        self._zone_id = zone_id
        zone_slug = zone_id.replace(".", "_")
        self._attr_unique_id = f"{entry.entry_id}_{zone_id}_threshold_multiplier"
        self._attr_name = f"{DOMAIN} {zone_slug} threshold_multiplier"
        self.entity_id = f"number.{DOMAIN}_{zone_slug}_threshold_multiplier"
        self._attr_device_info = device_info

    @property
    def native_value(self) -> float:
        """Read current threshold from ConfigEntry.options (always live)."""
        return (
            self._entry.options
            .get(CONF_ZONES, {})
            .get(self._zone_id, {})
            .get(CONF_THRESHOLD_MULTIPLIER, DEFAULT_THRESHOLD_MULTIPLIER)
        )

    async def async_set_native_value(self, value: float) -> None:
        """Persist new threshold using the CRITICAL nested merge pattern."""
        existing = dict(self._entry.options)
        zones = dict(existing.get(CONF_ZONES, {}))
        zone_data = dict(zones.get(self._zone_id, {}))
        zone_data[CONF_THRESHOLD_MULTIPLIER] = round(value, 1)
        zones[self._zone_id] = zone_data
        existing[CONF_ZONES] = zones
        # async_update_entry is a @callback — do not await
        self.hass.config_entries.async_update_entry(self._entry, options=existing)
        self.async_write_ha_state()
