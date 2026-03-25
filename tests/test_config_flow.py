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
    mock_flume_entity: str,
    mock_valve_entities: list[str],
) -> None:
    """Options flow preserves existing calibrated_flow — CRITICAL merge test (SETUP-04)."""
    # Pre-seed entry with calibrated_flow=3.5 on zone_1
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_FLUME_ENTITY_ID: mock_flume_entity,
            CONF_MONITORED_ZONES: mock_valve_entities[:2],
            CONF_POLL_INTERVAL: DEFAULT_POLL_INTERVAL,
        },
        options={
            CONF_ZONES: {
                mock_valve_entities[0]: {
                    CONF_SHUTOFF_ENABLED: True,
                    CONF_ALERTS_ENABLED: True,
                    CONF_CALIBRATED_FLOW: 3.5,
                    CONF_THRESHOLD_MULTIPLIER: DEFAULT_THRESHOLD_MULTIPLIER,
                },
                mock_valve_entities[1]: {
                    CONF_SHUTOFF_ENABLED: True,
                    CONF_ALERTS_ENABLED: True,
                    CONF_CALIBRATED_FLOW: None,
                    CONF_THRESHOLD_MULTIPLIER: DEFAULT_THRESHOLD_MULTIPLIER,
                },
            }
        },
    )
    entry.add_to_hass(hass)

    # Options flow is now single-step: init → create_entry
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_FLUME_ENTITY_ID: mock_flume_entity,
            CONF_MONITORED_ZONES: mock_valve_entities[:2],
            CONF_POLL_INTERVAL: DEFAULT_POLL_INTERVAL,
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY

    # CRITICAL: calibrated_flow=3.5 must survive the options flow round-trip
    assert entry.options[CONF_ZONES]["switch.rachio_zone_1"][CONF_CALIBRATED_FLOW] == 3.5


async def test_options_flow_add_new_valve_gets_defaults(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_flume_entity: str,
    mock_valve_entities: list[str],
) -> None:
    """A newly added valve gets default zone settings immediately (SETUP-04)."""
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] == FlowResultType.FORM

    # Add valve.os_zone_3 (new) alongside the existing two — single step
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_FLUME_ENTITY_ID: mock_flume_entity,
            CONF_MONITORED_ZONES: [
                "switch.rachio_zone_1",
                "switch.rachio_zone_2",
                "valve.os_zone_3",
            ],
            CONF_POLL_INTERVAL: DEFAULT_POLL_INTERVAL,
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
    """Removing a valve from the monitored list clears its zone data (SETUP-04)."""
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] == FlowResultType.FORM

    # Select only zone_1 (drop zone_2) — single step
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_FLUME_ENTITY_ID: mock_flume_entity,
            CONF_MONITORED_ZONES: ["switch.rachio_zone_1"],
            CONF_POLL_INTERVAL: DEFAULT_POLL_INTERVAL,
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert "switch.rachio_zone_2" not in mock_config_entry.options[CONF_ZONES]


async def test_options_per_zone_shutoff(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """ShutoffEnabledSwitch reads default from options and writes back on toggle (SETUP-05)."""
    from custom_components.irrigation_monitor.switch import ShutoffEnabledSwitch

    zone_id = "switch.rachio_zone_1"
    switch = ShutoffEnabledSwitch(mock_config_entry, zone_id, {})
    switch.hass = hass

    assert switch.is_on is True  # default from fixture
    await switch.async_turn_off()
    assert mock_config_entry.options[CONF_ZONES][zone_id][CONF_SHUTOFF_ENABLED] is False
    await switch.async_turn_on()
    assert mock_config_entry.options[CONF_ZONES][zone_id][CONF_SHUTOFF_ENABLED] is True


async def test_options_per_zone_alerts(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """AlertsEnabledSwitch reads default from options and writes back on toggle (SETUP-06)."""
    from custom_components.irrigation_monitor.switch import AlertsEnabledSwitch

    zone_id = "switch.rachio_zone_1"
    switch = AlertsEnabledSwitch(mock_config_entry, zone_id, {})
    switch.hass = hass

    assert switch.is_on is True  # default from fixture
    await switch.async_turn_off()
    assert mock_config_entry.options[CONF_ZONES][zone_id][CONF_ALERTS_ENABLED] is False
    await switch.async_turn_on()
    assert mock_config_entry.options[CONF_ZONES][zone_id][CONF_ALERTS_ENABLED] is True


async def test_options_per_zone_threshold(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """ThresholdMultiplierNumber reads from options and writes back on set (SETUP-07)."""
    from custom_components.irrigation_monitor.number import ThresholdMultiplierNumber

    zone_id = "switch.rachio_zone_1"
    number = ThresholdMultiplierNumber(mock_config_entry, zone_id, {})
    number.hass = hass

    assert number.native_value == DEFAULT_THRESHOLD_MULTIPLIER  # 1.5 from fixture
    await number.async_set_native_value(1.8)
    assert mock_config_entry.options[CONF_ZONES][zone_id][CONF_THRESHOLD_MULTIPLIER] == 1.8
