"""Sensor platform for the Irrigation Monitor integration."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfVolume, UnitOfVolumeFlowRate
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_MONITORED_ZONES, DOMAIN
from .coordinator import IrrigationCoordinator, ZoneData


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up irrigation_monitor sensors from a config entry."""
    coordinator: IrrigationCoordinator = entry.runtime_data
    monitored: list[str] = entry.data[CONF_MONITORED_ZONES]
    entities: list[SensorEntity] = []
    for zone_id in monitored:
        entities.append(DailyUsageSensor(coordinator, entry, zone_id))
        entities.append(FlowRateSensor(coordinator, entry, zone_id))
        entities.append(ZoneStatusSensor(coordinator, entry, zone_id))
    async_add_entities(entities)


class DailyUsageSensor(CoordinatorEntity[IrrigationCoordinator], SensorEntity):
    """Sensor showing daily water usage (gallons accumulated since midnight) per zone."""

    _attr_device_class = SensorDeviceClass.WATER
    _attr_native_unit_of_measurement = UnitOfVolume.GALLONS
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: IrrigationCoordinator,
        entry: ConfigEntry,
        zone_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._attr_unique_id = f"{entry.entry_id}_{zone_id}_daily_usage"
        # Entity ID: sensor.irrigation_monitor_{zone_id}_daily_usage
        # zone_id contains dots (e.g. "switch.rachio_zone_1") — replace for entity_id safety
        zone_slug = zone_id.replace(".", "_")
        self._attr_name = f"{DOMAIN} {zone_slug} daily_usage"
        self.entity_id = f"sensor.{DOMAIN}_{zone_slug}_daily_usage"

    @property
    def native_value(self) -> float | None:
        """Return accumulated daily usage in gallons."""
        if self.coordinator.data is None:
            return None
        zone: ZoneData | None = self.coordinator.data.get(self._zone_id)
        return round(zone.daily_usage, 2) if zone else None


class FlowRateSensor(CoordinatorEntity[IrrigationCoordinator], SensorEntity):
    """Sensor showing current flow rate (gal/min) per zone; 0 when zone is idle."""

    _attr_device_class = SensorDeviceClass.VOLUME_FLOW_RATE
    _attr_native_unit_of_measurement = UnitOfVolumeFlowRate.GALLONS_PER_MINUTE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: IrrigationCoordinator,
        entry: ConfigEntry,
        zone_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._attr_unique_id = f"{entry.entry_id}_{zone_id}_flow_rate"
        zone_slug = zone_id.replace(".", "_")
        self._attr_name = f"{DOMAIN} {zone_slug} flow_rate"
        self.entity_id = f"sensor.{DOMAIN}_{zone_slug}_flow_rate"

    @property
    def native_value(self) -> float | None:
        """Return current flow rate in gal/min (0 when idle)."""
        if self.coordinator.data is None:
            return None
        zone: ZoneData | None = self.coordinator.data.get(self._zone_id)
        return round(zone.flow_rate, 2) if zone else None


class ZoneStatusSensor(CoordinatorEntity[IrrigationCoordinator], SensorEntity):
    """Sensor showing zone status: idle / running / leak_detected."""

    # CRITICAL: Do NOT set _attr_state_class — text enum values are incompatible
    # with HA statistics. Omitting avoids HA warnings in the recorder.
    # CRITICAL: Do NOT set _attr_device_class — no matching HA device class for
    # status strings. Omitting avoids HA entity registry warnings.
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: IrrigationCoordinator,
        entry: ConfigEntry,
        zone_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._attr_unique_id = f"{entry.entry_id}_{zone_id}_status"
        zone_slug = zone_id.replace(".", "_")
        self._attr_name = f"{DOMAIN} {zone_slug} status"
        self.entity_id = f"sensor.{DOMAIN}_{zone_slug}_status"

    @property
    def native_value(self) -> str:
        """Return zone status string."""
        return self.coordinator._leak_statuses.get(self._zone_id, "idle")
