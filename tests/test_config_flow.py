"""Tests for the Irrigation Monitor config flow."""
import pytest

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.irrigation_monitor.const import (
    CONF_ALERTS_ENABLED,
    CONF_CALIBRATED_FLOW,
    CONF_FLUME_ENTITY_ID,
    CONF_MONITORED_ZONES,
    CONF_POLL_INTERVAL,
    CONF_SHUTOFF_ENABLED,
    CONF_THRESHOLD_MULTIPLIER,
    CONF_ZONES,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_SHUTOFF_ENABLED,
    DEFAULT_ALERTS_ENABLED,
    DEFAULT_THRESHOLD_MULTIPLIER,
    DOMAIN,
)


async def test_step_user_shows_form(hass: HomeAssistant, mock_flume_entity: str) -> None:
    """Test that initiating config flow shows Step 1 (Flume sensor picker)."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_step_user_advances_to_valves(
    hass: HomeAssistant,
    mock_flume_entity: str,
    mock_valve_entities: list[str],
) -> None:
    """Test that submitting Flume entity in Step 1 advances to Step 2 (valves)."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_FLUME_ENTITY_ID: mock_flume_entity},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "valves"


async def test_step_valves_shows_discovered_entities(
    hass: HomeAssistant,
    mock_flume_entity: str,
    mock_valve_entities: list[str],
) -> None:
    """Test that Step 2 form is shown after completing Step 1."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_FLUME_ENTITY_ID: mock_flume_entity},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "valves"
    # Verify the schema has the monitored zones field
    assert CONF_MONITORED_ZONES in result["data_schema"].schema


async def test_full_flow_creates_entry(
    hass: HomeAssistant,
    mock_flume_entity: str,
    mock_valve_entities: list[str],
) -> None:
    """Test completing both steps creates a ConfigEntry with correct data."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_FLUME_ENTITY_ID: mock_flume_entity},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "valves"

    selected_valves = [mock_valve_entities[0], mock_valve_entities[1]]
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_MONITORED_ZONES: selected_valves},
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_FLUME_ENTITY_ID] == mock_flume_entity
    assert result["data"][CONF_MONITORED_ZONES] == selected_valves
    assert result["data"][CONF_POLL_INTERVAL] == DEFAULT_POLL_INTERVAL


async def test_config_flow_sets_zone_defaults(
    hass: HomeAssistant,
    mock_flume_entity: str,
    mock_valve_entities: list[str],
) -> None:
    """Test that completing the config flow initializes per-zone defaults in options."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_FLUME_ENTITY_ID: mock_flume_entity},
    )
    selected_valves = mock_valve_entities  # select all 3
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_MONITORED_ZONES: selected_valves},
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY

    # Verify options.zones has per-zone defaults for each selected valve
    options = result["options"]
    assert CONF_ZONES in options
    zones = options[CONF_ZONES]

    for entity_id in selected_valves:
        assert entity_id in zones, f"Zone {entity_id} missing from options.zones"
        zone = zones[entity_id]
        assert zone[CONF_SHUTOFF_ENABLED] is DEFAULT_SHUTOFF_ENABLED
        assert zone[CONF_ALERTS_ENABLED] is DEFAULT_ALERTS_ENABLED
        assert zone[CONF_CALIBRATED_FLOW] is None
        assert zone[CONF_THRESHOLD_MULTIPLIER] == DEFAULT_THRESHOLD_MULTIPLIER
