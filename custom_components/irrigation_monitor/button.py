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
    """Set up calibrate button entities per monitored zone."""
    coordinator: IrrigationCoordinator = entry.runtime_data
    monitored: list[str] = entry.data[CONF_MONITORED_ZONES]
    async_add_entities([
        CalibrateButtonEntity(coordinator, entry, zone_id)
        for zone_id in monitored
    ])


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
