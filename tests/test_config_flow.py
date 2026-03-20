"""Tests for the Irrigation Monitor config flow."""
import pytest

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

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


# ---------------------------------------------------------------------------
# Options flow tests (Plan 02-02) — SETUP-04/05/06/07
# ---------------------------------------------------------------------------


@pytest.fixture
async def mock_config_entry(
    hass: HomeAssistant,
    mock_flume_entity: str,
    mock_valve_entities: list[str],
) -> MockConfigEntry:
    """Create a mock config entry for options flow tests with pre-seeded calibration data."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_FLUME_ENTITY_ID: "sensor.flume_current_interval",
            CONF_MONITORED_ZONES: ["switch.rachio_zone_1", "switch.rachio_zone_2"],
            CONF_POLL_INTERVAL: DEFAULT_POLL_INTERVAL,
        },
        options={
            CONF_ZONES: {
                "switch.rachio_zone_1": {
                    CONF_SHUTOFF_ENABLED: True,
                    CONF_ALERTS_ENABLED: True,
                    CONF_CALIBRATED_FLOW: 3.5,
                    CONF_THRESHOLD_MULTIPLIER: DEFAULT_THRESHOLD_MULTIPLIER,
                },
                "switch.rachio_zone_2": {
                    CONF_SHUTOFF_ENABLED: False,
                    CONF_ALERTS_ENABLED: True,
                    CONF_CALIBRATED_FLOW: None,
                    CONF_THRESHOLD_MULTIPLIER: 2.0,
                },
            }
        },
    )
    entry.add_to_hass(hass)
    return entry


async def test_options_flow_init_shows_form(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_flume_entity: str,
    mock_valve_entities: list[str],
) -> None:
    """Test that initiating options flow shows the init form (SETUP-04)."""
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"


async def test_options_flow_merge_preserves_zones(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_flume_entity: str,
    mock_valve_entities: list[str],
) -> None:
    """Test that running options flow preserves existing calibration data (CRITICAL merge test)."""
    # Pre-seeded: zone_1 has calibrated_flow=3.5 (from fixture)
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"

    # Submit init step with same valves (no change)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_FLUME_ENTITY_ID: "sensor.flume_current_interval",
            CONF_MONITORED_ZONES: ["switch.rachio_zone_1", "switch.rachio_zone_2"],
            CONF_POLL_INTERVAL: DEFAULT_POLL_INTERVAL,
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "zones"

    # Configure zone_1 (keeping defaults)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_SHUTOFF_ENABLED: True,
            CONF_ALERTS_ENABLED: True,
            CONF_THRESHOLD_MULTIPLIER: DEFAULT_THRESHOLD_MULTIPLIER,
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "zones"

    # Configure zone_2 (keeping defaults)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_SHUTOFF_ENABLED: False,
            CONF_ALERTS_ENABLED: True,
            CONF_THRESHOLD_MULTIPLIER: 2.0,
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY

    # CRITICAL: calibrated_flow=3.5 must be preserved from the original options
    assert mock_config_entry.options[CONF_ZONES]["switch.rachio_zone_1"][CONF_CALIBRATED_FLOW] == 3.5


async def test_options_flow_add_new_valve_gets_defaults(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_flume_entity: str,
    mock_valve_entities: list[str],
) -> None:
    """Test that a newly added valve gets default zone settings (SETUP-04)."""
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] == FlowResultType.FORM

    # Add valve.os_zone_3 (new valve) alongside the existing two
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_FLUME_ENTITY_ID: "sensor.flume_current_interval",
            CONF_MONITORED_ZONES: [
                "switch.rachio_zone_1",
                "switch.rachio_zone_2",
                "valve.os_zone_3",
            ],
            CONF_POLL_INTERVAL: DEFAULT_POLL_INTERVAL,
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "zones"

    # Configure zone_1
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_SHUTOFF_ENABLED: True,
            CONF_ALERTS_ENABLED: True,
            CONF_THRESHOLD_MULTIPLIER: DEFAULT_THRESHOLD_MULTIPLIER,
        },
    )
    # Configure zone_2
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_SHUTOFF_ENABLED: False,
            CONF_ALERTS_ENABLED: True,
            CONF_THRESHOLD_MULTIPLIER: 2.0,
        },
    )
    # Configure valve.os_zone_3 (new)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_SHUTOFF_ENABLED: True,
            CONF_ALERTS_ENABLED: True,
            CONF_THRESHOLD_MULTIPLIER: DEFAULT_THRESHOLD_MULTIPLIER,
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY

    new_zone = mock_config_entry.options[CONF_ZONES]["valve.os_zone_3"]
    assert new_zone[CONF_SHUTOFF_ENABLED] is True
    assert new_zone[CONF_ALERTS_ENABLED] is True
    assert new_zone[CONF_CALIBRATED_FLOW] is None
    assert new_zone[CONF_THRESHOLD_MULTIPLIER] == DEFAULT_THRESHOLD_MULTIPLIER


async def test_options_flow_remove_valve_clears_data(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_flume_entity: str,
    mock_valve_entities: list[str],
) -> None:
    """Test that removing a valve from the monitored list clears its zone data (SETUP-04)."""
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] == FlowResultType.FORM

    # Select only zone_1 (removing zone_2)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_FLUME_ENTITY_ID: "sensor.flume_current_interval",
            CONF_MONITORED_ZONES: ["switch.rachio_zone_1"],
            CONF_POLL_INTERVAL: DEFAULT_POLL_INTERVAL,
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "zones"

    # Configure zone_1
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_SHUTOFF_ENABLED: True,
            CONF_ALERTS_ENABLED: True,
            CONF_THRESHOLD_MULTIPLIER: DEFAULT_THRESHOLD_MULTIPLIER,
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY

    # zone_2 must be gone
    assert "switch.rachio_zone_2" not in mock_config_entry.options[CONF_ZONES]


async def test_options_per_zone_shutoff(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_flume_entity: str,
    mock_valve_entities: list[str],
) -> None:
    """Test that shutoff_enabled can be changed per zone (SETUP-05)."""
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_FLUME_ENTITY_ID: "sensor.flume_current_interval",
            CONF_MONITORED_ZONES: ["switch.rachio_zone_1", "switch.rachio_zone_2"],
            CONF_POLL_INTERVAL: DEFAULT_POLL_INTERVAL,
        },
    )
    # Set zone_1 shutoff to False
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_SHUTOFF_ENABLED: False,
            CONF_ALERTS_ENABLED: True,
            CONF_THRESHOLD_MULTIPLIER: DEFAULT_THRESHOLD_MULTIPLIER,
        },
    )
    # Configure zone_2
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_SHUTOFF_ENABLED: False,
            CONF_ALERTS_ENABLED: True,
            CONF_THRESHOLD_MULTIPLIER: 2.0,
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert mock_config_entry.options[CONF_ZONES]["switch.rachio_zone_1"][CONF_SHUTOFF_ENABLED] is False


async def test_options_per_zone_alerts(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_flume_entity: str,
    mock_valve_entities: list[str],
) -> None:
    """Test that alerts_enabled can be changed per zone (SETUP-06)."""
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_FLUME_ENTITY_ID: "sensor.flume_current_interval",
            CONF_MONITORED_ZONES: ["switch.rachio_zone_1", "switch.rachio_zone_2"],
            CONF_POLL_INTERVAL: DEFAULT_POLL_INTERVAL,
        },
    )
    # Set zone_1 alerts to False
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_SHUTOFF_ENABLED: True,
            CONF_ALERTS_ENABLED: False,
            CONF_THRESHOLD_MULTIPLIER: DEFAULT_THRESHOLD_MULTIPLIER,
        },
    )
    # Configure zone_2
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_SHUTOFF_ENABLED: False,
            CONF_ALERTS_ENABLED: True,
            CONF_THRESHOLD_MULTIPLIER: 2.0,
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert mock_config_entry.options[CONF_ZONES]["switch.rachio_zone_1"][CONF_ALERTS_ENABLED] is False


async def test_options_per_zone_threshold(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_flume_entity: str,
    mock_valve_entities: list[str],
) -> None:
    """Test that threshold_multiplier can be changed per zone (SETUP-07)."""
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_FLUME_ENTITY_ID: "sensor.flume_current_interval",
            CONF_MONITORED_ZONES: ["switch.rachio_zone_1", "switch.rachio_zone_2"],
            CONF_POLL_INTERVAL: DEFAULT_POLL_INTERVAL,
        },
    )
    # Set zone_1 threshold to 2.5
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_SHUTOFF_ENABLED: True,
            CONF_ALERTS_ENABLED: True,
            CONF_THRESHOLD_MULTIPLIER: 2.5,
        },
    )
    # Configure zone_2
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_SHUTOFF_ENABLED: False,
            CONF_ALERTS_ENABLED: True,
            CONF_THRESHOLD_MULTIPLIER: 2.0,
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert mock_config_entry.options[CONF_ZONES]["switch.rachio_zone_1"][CONF_THRESHOLD_MULTIPLIER] == 2.5
