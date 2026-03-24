"""Global test fixtures for irrigation_monitor."""
import pytest

pytest_plugins = "pytest_homeassistant_custom_component"

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.irrigation_monitor.const import (
    DOMAIN,
    CONF_FLUME_ENTITY_ID,
    CONF_MONITORED_ZONES,
    CONF_POLL_INTERVAL,
    CONF_ZONES,
    CONF_SHUTOFF_ENABLED,
    CONF_ALERTS_ENABLED,
    CONF_CALIBRATED_FLOW,
    CONF_THRESHOLD_MULTIPLIER,
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests."""
    yield


@pytest.fixture
def mock_flume_entity(hass: HomeAssistant) -> str:
    """Register a mock Flume sensor entity in the entity registry."""
    entity_id = "sensor.flume_current_interval"
    registry = er.async_get(hass)
    registry.async_get_or_create(
        domain="sensor",
        platform="flume",
        unique_id="flume_current_interval_001",
        suggested_object_id="flume_current_interval",
    )
    hass.states.async_set(
        entity_id, "1.5",
        attributes={"unit_of_measurement": "gal/min"},
    )
    return entity_id


@pytest.fixture
def mock_valve_entities(hass: HomeAssistant) -> list[str]:
    """Register mock valve/switch entities in the entity registry."""
    registry = er.async_get(hass)
    entities = []
    for domain, platform, obj_id, name in [
        ("switch", "rachio", "rachio_zone_1", "Front Yard Drip"),
        ("switch", "rachio", "rachio_zone_2", "Back Yard Sprinkler"),
        ("valve", "opensprinkler", "os_zone_3", "Side Garden"),
    ]:
        entity_id = f"{domain}.{obj_id}"
        registry.async_get_or_create(
            domain=domain,
            platform=platform,
            unique_id=f"{platform}_{obj_id}",
            suggested_object_id=obj_id,
            original_name=name,
        )
        hass.states.async_set(entity_id, "off")
        entities.append(entity_id)
    return entities


@pytest.fixture
def mock_config_entry(
    hass: HomeAssistant,
    mock_flume_entity: str,
    mock_valve_entities: list[str],
) -> MockConfigEntry:
    """Create a MockConfigEntry for coordinator tests."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_FLUME_ENTITY_ID: mock_flume_entity,
            CONF_MONITORED_ZONES: mock_valve_entities[:2],  # 2 zones
            CONF_POLL_INTERVAL: 30,
        },
        options={
            CONF_ZONES: {
                mock_valve_entities[0]: {
                    CONF_SHUTOFF_ENABLED: True,
                    CONF_ALERTS_ENABLED: True,
                    CONF_CALIBRATED_FLOW: None,
                    CONF_THRESHOLD_MULTIPLIER: 1.5,
                },
                mock_valve_entities[1]: {
                    CONF_SHUTOFF_ENABLED: True,
                    CONF_ALERTS_ENABLED: True,
                    CONF_CALIBRATED_FLOW: None,
                    CONF_THRESHOLD_MULTIPLIER: 1.5,
                },
            }
        },
    )
    entry.add_to_hass(hass)
    return entry
