"""Switch platform for the Irrigation Monitor integration.

Per-zone toggles for auto-shutoff and anomaly alerts. State is persisted
in ConfigEntry.options so it survives HA restarts. Changes take effect
on the coordinator's next poll — no integration reload required.
"""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    CONF_ALERTS_ENABLED,
    CONF_MONITORED_ZONES,
    CONF_SHUTOFF_ENABLED,
    CONF_ZONES,
    DEFAULT_ALERTS_ENABLED,
    DEFAULT_SHUTOFF_ENABLED,
    DOMAIN,
)
from .sensor import _zone_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up shutoff and alerts toggle switches per monitored zone."""
    monitored: list[str] = entry.data[CONF_MONITORED_ZONES]
    entities = []
    for zone_id in monitored:
        device_info = _zone_device_info(hass, entry, zone_id)
        entities.append(ShutoffEnabledSwitch(entry, zone_id, device_info))
        entities.append(AlertsEnabledSwitch(entry, zone_id, device_info))
    async_add_entities(entities)


class _ZoneOptionSwitch(RestoreEntity, SwitchEntity):
    """Base class for per-zone option switches backed by ConfigEntry.options."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _options_key: str
    _default_value: bool

    def __init__(self, entry: ConfigEntry, zone_id: str, device_info) -> None:
        self._entry = entry
        self._zone_id = zone_id
        self._attr_device_info = device_info

    @property
    def is_on(self) -> bool:
        """Read current value directly from ConfigEntry.options (always live)."""
        return (
            self._entry.options
            .get(CONF_ZONES, {})
            .get(self._zone_id, {})
            .get(self._options_key, self._default_value)
        )

    async def async_turn_on(self, **kwargs) -> None:
        await self._set_option(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._set_option(False)

    async def _set_option(self, value: bool) -> None:
        """Write new value into ConfigEntry.options using the CRITICAL nested merge pattern."""
        existing = dict(self._entry.options)
        zones = dict(existing.get(CONF_ZONES, {}))
        zone_data = dict(zones.get(self._zone_id, {}))
        zone_data[self._options_key] = value
        zones[self._zone_id] = zone_data
        existing[CONF_ZONES] = zones
        # async_update_entry is a @callback — do not await
        self.hass.config_entries.async_update_entry(self._entry, options=existing)
        self.async_write_ha_state()


class ShutoffEnabledSwitch(_ZoneOptionSwitch):
    """Toggle that enables/disables auto-shutoff for a zone."""

    _options_key = CONF_SHUTOFF_ENABLED
    _default_value = DEFAULT_SHUTOFF_ENABLED

    def __init__(self, entry: ConfigEntry, zone_id: str, device_info) -> None:
        super().__init__(entry, zone_id, device_info)
        zone_slug = zone_id.replace(".", "_")
        self._attr_unique_id = f"{entry.entry_id}_{zone_id}_shutoff_enabled"
        self._attr_name = f"{DOMAIN} {zone_slug} shutoff_enabled"
        self.entity_id = f"switch.{DOMAIN}_{zone_slug}_shutoff_enabled"


class AlertsEnabledSwitch(_ZoneOptionSwitch):
    """Toggle that enables/disables anomaly alerts for a zone."""

    _options_key = CONF_ALERTS_ENABLED
    _default_value = DEFAULT_ALERTS_ENABLED

    def __init__(self, entry: ConfigEntry, zone_id: str, device_info) -> None:
        super().__init__(entry, zone_id, device_info)
        zone_slug = zone_id.replace(".", "_")
        self._attr_unique_id = f"{entry.entry_id}_{zone_id}_alerts_enabled"
        self._attr_name = f"{DOMAIN} {zone_slug} alerts_enabled"
        self.entity_id = f"switch.{DOMAIN}_{zone_slug}_alerts_enabled"
