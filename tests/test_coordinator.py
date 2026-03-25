"""Tests for irrigation_monitor coordinator and sensors."""
import pytest
from datetime import date, timedelta, datetime
from unittest.mock import patch

from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)
from homeassistant.core import HomeAssistant
from homeassistant.const import STATE_UNAVAILABLE

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


async def test_sensor_entities_created(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """USAGE-01: Sensor entities created per zone with correct states."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Daily usage sensor for zone 1
    state = hass.states.get("sensor.irrigation_monitor_switch_rachio_zone_1_daily_usage")
    assert state is not None
    assert state.state == "0.0"  # starts at zero

    # Flow rate sensor for zone 1
    state = hass.states.get("sensor.irrigation_monitor_switch_rachio_zone_1_flow_rate")
    assert state is not None

    # Zone 2 sensors
    state = hass.states.get("sensor.irrigation_monitor_switch_rachio_zone_2_daily_usage")
    assert state is not None


async def test_flow_rate_zero_when_idle(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """USAGE-01: flow_rate is 0 when zone is idle (off)."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.irrigation_monitor_switch_rachio_zone_1_flow_rate")
    assert state is not None
    assert float(state.state) == 0.0


async def test_daily_usage_accumulates(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_valve_entities: list[str],
) -> None:
    """USAGE-01: daily_usage accumulates while zone runs."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Turn zone 1 on
    hass.states.async_set(mock_valve_entities[0], "on")
    # Set Flume to read 2.0 gal/min
    hass.states.async_set("sensor.flume_current_interval", "2.0")

    # Trigger coordinator refresh
    coordinator = mock_config_entry.runtime_data
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get("sensor.irrigation_monitor_switch_rachio_zone_1_daily_usage")
    assert float(state.state) > 0.0


async def test_flume_unavailable_entities_unavailable(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """USAGE-01: All entities unavailable when Flume is unavailable."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    hass.states.async_set("sensor.flume_current_interval", STATE_UNAVAILABLE)
    coordinator = mock_config_entry.runtime_data
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get("sensor.irrigation_monitor_switch_rachio_zone_1_daily_usage")
    assert state.state == STATE_UNAVAILABLE


async def test_totals_persist_across_restart(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_flume_entity: str,
    mock_valve_entities: list[str],
) -> None:
    """USAGE-02: Totals persist after unload + reload."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Accumulate some usage
    hass.states.async_set(mock_valve_entities[0], "on")
    hass.states.async_set(mock_flume_entity, "2.0")
    coordinator = mock_config_entry.runtime_data
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get("sensor.irrigation_monitor_switch_rachio_zone_1_daily_usage")
    accumulated = float(state.state)
    assert accumulated > 0.0

    # Unload and reload
    await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Re-set entity states (they're cleared on unload)
    hass.states.async_set(mock_flume_entity, "2.0",
                          attributes={"unit_of_measurement": "gal/min"})
    hass.states.async_set(mock_valve_entities[0], "off")
    hass.states.async_set(mock_valve_entities[1], "off")

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.irrigation_monitor_switch_rachio_zone_1_daily_usage")
    assert float(state.state) == pytest.approx(accumulated, abs=0.01)


async def test_midnight_reset_zeroes_totals(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_valve_entities: list[str],
) -> None:
    """USAGE-02: Midnight reset zeroes all daily totals."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Accumulate usage
    hass.states.async_set(mock_valve_entities[0], "on")
    hass.states.async_set("sensor.flume_current_interval", "2.0")
    coordinator = mock_config_entry.runtime_data
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    # Verify non-zero
    state = hass.states.get("sensor.irrigation_monitor_switch_rachio_zone_1_daily_usage")
    assert float(state.state) > 0.0

    hass.states.async_set(mock_valve_entities[0], "off")

    # Fire a far-future midnight to guarantee it's after the coordinator's
    # scheduled next-midnight time (async_track_time_change schedules the
    # *next* midnight after setup; firing a past midnight won't trigger it).
    async_fire_time_changed(hass, datetime(2030, 1, 1, 0, 0, 0))
    await hass.async_block_till_done()
    await hass.async_block_till_done()

    state = hass.states.get("sensor.irrigation_monitor_switch_rachio_zone_1_daily_usage")
    assert float(state.state) == 0.0


async def test_stale_date_resets_totals(
    hass: HomeAssistant,
    mock_flume_entity: str,
    mock_valve_entities: list[str],
) -> None:
    """USAGE-03: Startup with stale stored date resets totals to 0."""
    # Pre-populate Store with yesterday's data
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    store_data = {
        "date": yesterday,
        "zones": {mock_valve_entities[0]: 42.5, mock_valve_entities[1]: 10.0},
    }

    # Patch Store.async_load to return stale data
    with patch(
        "custom_components.irrigation_monitor.coordinator.Store.async_load",
        return_value=store_data,
    ):
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "flume_entity_id": mock_flume_entity,
                "monitored_zone_entity_ids": mock_valve_entities[:2],
                "poll_interval": 30,
            },
            options={
                "zones": {
                    mock_valve_entities[0]: {
                        "shutoff_enabled": True,
                        "alerts_enabled": True,
                        "calibrated_flow": None,
                        "threshold_multiplier": 1.5,
                    },
                    mock_valve_entities[1]: {
                        "shutoff_enabled": True,
                        "alerts_enabled": True,
                        "calibrated_flow": None,
                        "threshold_multiplier": 1.5,
                    },
                }
            },
        )
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("sensor.irrigation_monitor_switch_rachio_zone_1_daily_usage")
    assert state is not None
    assert float(state.state) == 0.0
