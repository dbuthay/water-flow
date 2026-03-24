"""Button platform for the Irrigation Monitor integration."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_MONITORED_ZONES, DOMAIN
from .coordinator import IrrigationCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up calibrate and acknowledge-leak button entities per monitored zone."""
    coordinator: IrrigationCoordinator = entry.runtime_data
    monitored: list[str] = entry.data[CONF_MONITORED_ZONES]
    entities = []
    for zone_id in monitored:
        entities.append(CalibrateButtonEntity(coordinator, entry, zone_id))
        entities.append(AcknowledgeLeakButtonEntity(coordinator, entry, zone_id))
    async_add_entities(entities)


class CalibrateButtonEntity(CoordinatorEntity[IrrigationCoordinator], ButtonEntity):
    """Button that triggers calibration for one zone."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: IrrigationCoordinator,
        entry: ConfigEntry,
        zone_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._entry = entry
        zone_slug = zone_id.replace(".", "_")
        self._attr_unique_id = f"{entry.entry_id}_{zone_id}_calibrate"
        self._attr_name = f"{DOMAIN} {zone_slug} calibrate"
        self.entity_id = f"button.{DOMAIN}_{zone_slug}_calibrate"

    async def async_press(self) -> None:
        """Fire calibration as a background task -- never block async_press."""
        self._entry.async_create_background_task(
            self.hass,
            self.coordinator.async_calibrate_zone(self._zone_id),
            name=f"calibrate_{self._zone_id}",
        )


class AcknowledgeLeakButtonEntity(CoordinatorEntity[IrrigationCoordinator], ButtonEntity):
    """Button that clears leak_detected status for one zone."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: IrrigationCoordinator,
        entry: ConfigEntry,
        zone_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._zone_id = zone_id
        zone_slug = zone_id.replace(".", "_")
        self._attr_unique_id = f"{entry.entry_id}_{zone_id}_acknowledge_leak"
        self._attr_name = f"{DOMAIN} {zone_slug} acknowledge_leak"
        self.entity_id = f"button.{DOMAIN}_{zone_slug}_acknowledge_leak"

    async def async_press(self) -> None:
        """Clear leak_detected status and dedup flag for this zone."""
        self.coordinator._leak_statuses[self._zone_id] = "idle"
        self.coordinator._leak_notified.discard(self._zone_id)
        # CRITICAL: Use async_update_listeners() NOT async_request_refresh()
        # async_update_listeners is a @callback that immediately notifies all
        # CoordinatorEntity listeners to call async_write_ha_state().
        # async_request_refresh would trigger an unnecessary Flume network poll.
        self.coordinator.async_update_listeners()
