"""Leak detection tests for Phase 5 (DETECT-01 through DETECT-04).

All tests use mock_calibrated_config_entry (zone 1 calibrated at 2.0 gal/min,
threshold 1.5x = leak at > 3.0 gal/min, ramp_up_polls=0).
"""
import pytest
from unittest.mock import patch, AsyncMock

from pytest_homeassistant_custom_component.common import MockConfigEntry
from homeassistant.core import HomeAssistant

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
    CONF_RAMP_UP_POLLS,
)


# ---------------------------------------------------------------------------
# DETECT-01: Basic threshold comparison
# ---------------------------------------------------------------------------


async def test_leak_detection_fires(
    hass: HomeAssistant,
    mock_calibrated_config_entry: MockConfigEntry,
    mock_valve_entities: list[str],
) -> None:
    """DETECT-01: Zone 1 ON, flow 4.0 > 2.0*1.5=3.0 -> status becomes 'leak_detected'."""
    await hass.config_entries.async_setup(mock_calibrated_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_calibrated_config_entry.runtime_data

    # Zone 1 on, flow exceeds threshold
    hass.states.async_set(mock_valve_entities[0], "on")
    hass.states.async_set("sensor.flume_current_interval", "4.0")

    # Mock _turn_valve to avoid ServiceNotFound in test harness
    with patch.object(coordinator, "_turn_valve", new_callable=AsyncMock):
        await coordinator.async_refresh()
        await hass.async_block_till_done()

    state = hass.states.get("sensor.irrigation_monitor_switch_rachio_zone_1_status")
    assert state is not None
    assert state.state == "leak_detected"


async def test_uncalibrated_zone_no_leak(
    hass: HomeAssistant,
    mock_calibrated_config_entry: MockConfigEntry,
    mock_valve_entities: list[str],
) -> None:
    """DETECT-01: Zone 2 (uncalibrated) ON, high flow -> status stays 'running', not 'leak_detected'."""
    await hass.config_entries.async_setup(mock_calibrated_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_calibrated_config_entry.runtime_data

    # Zone 2 is uncalibrated; set very high flow
    hass.states.async_set(mock_valve_entities[1], "on")
    hass.states.async_set("sensor.flume_current_interval", "10.0")

    await coordinator.async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get("sensor.irrigation_monitor_switch_rachio_zone_2_status")
    assert state is not None
    assert state.state == "running"
    assert state.state != "leak_detected"


# ---------------------------------------------------------------------------
# DETECT-02: Ramp-up skip window
# ---------------------------------------------------------------------------


async def test_ramp_up_skips_detection(
    hass: HomeAssistant,
    mock_valve_entities: list[str],
    mock_flume_entity: str,
) -> None:
    """DETECT-02: With ramp_up_polls=2, first 2 polls skip detection even if flow exceeds threshold."""
    # Use a dedicated entry with ramp_up_polls=2 (not the fixture default of 0)
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_FLUME_ENTITY_ID: mock_flume_entity,
            CONF_MONITORED_ZONES: mock_valve_entities[:2],
            CONF_POLL_INTERVAL: 30,
        },
        options={
            CONF_ZONES: {
                mock_valve_entities[0]: {
                    CONF_SHUTOFF_ENABLED: True,
                    CONF_ALERTS_ENABLED: True,
                    CONF_CALIBRATED_FLOW: 2.0,
                    CONF_THRESHOLD_MULTIPLIER: 1.5,
                },
                mock_valve_entities[1]: {
                    CONF_SHUTOFF_ENABLED: True,
                    CONF_ALERTS_ENABLED: True,
                    CONF_CALIBRATED_FLOW: None,
                    CONF_THRESHOLD_MULTIPLIER: 1.5,
                },
            },
            CONF_RAMP_UP_POLLS: 2,
        },
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    coordinator = entry.runtime_data

    # Zone 1 on, flow exceeds threshold (4.0 > 3.0)
    hass.states.async_set(mock_valve_entities[0], "on")
    hass.states.async_set("sensor.flume_current_interval", "4.0")

    # Mock _turn_valve to avoid ServiceNotFound in test harness
    with patch.object(coordinator, "_turn_valve", new_callable=AsyncMock):
        # First refresh: ramp-up active (counter=2), should be "running" not "leak_detected"
        await coordinator.async_refresh()
        await hass.async_block_till_done()
        state = hass.states.get("sensor.irrigation_monitor_switch_rachio_zone_1_status")
        assert state.state == "running", f"Expected 'running' on poll 1, got '{state.state}'"

        # Second refresh: ramp-up still active (counter=1), still "running"
        await coordinator.async_refresh()
        await hass.async_block_till_done()
        state = hass.states.get("sensor.irrigation_monitor_switch_rachio_zone_1_status")
        assert state.state == "running", f"Expected 'running' on poll 2, got '{state.state}'"

        # Third refresh: ramp-up exhausted (counter=0), now "leak_detected"
        await coordinator.async_refresh()
        await hass.async_block_till_done()
        state = hass.states.get("sensor.irrigation_monitor_switch_rachio_zone_1_status")
        assert state.state == "leak_detected", f"Expected 'leak_detected' on poll 3, got '{state.state}'"


async def test_ramp_up_resets_on_restart(
    hass: HomeAssistant,
    mock_valve_entities: list[str],
    mock_flume_entity: str,
) -> None:
    """DETECT-02: OFF->ON transition resets ramp counter; detection resumes after countdown."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_FLUME_ENTITY_ID: mock_flume_entity,
            CONF_MONITORED_ZONES: mock_valve_entities[:2],
            CONF_POLL_INTERVAL: 30,
        },
        options={
            CONF_ZONES: {
                mock_valve_entities[0]: {
                    CONF_SHUTOFF_ENABLED: True,
                    CONF_ALERTS_ENABLED: True,
                    CONF_CALIBRATED_FLOW: 2.0,
                    CONF_THRESHOLD_MULTIPLIER: 1.5,
                },
                mock_valve_entities[1]: {
                    CONF_SHUTOFF_ENABLED: True,
                    CONF_ALERTS_ENABLED: True,
                    CONF_CALIBRATED_FLOW: None,
                    CONF_THRESHOLD_MULTIPLIER: 1.5,
                },
            },
            CONF_RAMP_UP_POLLS: 1,
        },
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    coordinator = entry.runtime_data

    # Zone 1 ON, flow exceeds threshold
    hass.states.async_set(mock_valve_entities[0], "on")
    hass.states.async_set("sensor.flume_current_interval", "4.0")

    # Mock _turn_valve to avoid ServiceNotFound in test harness
    with patch.object(coordinator, "_turn_valve", new_callable=AsyncMock):
        # First refresh: ramp-up skips (counter=1 -> 0)
        await coordinator.async_refresh()
        await hass.async_block_till_done()
        state = hass.states.get("sensor.irrigation_monitor_switch_rachio_zone_1_status")
        assert state.state == "running"

        # Second refresh: leak detected (ramp-up exhausted)
        await coordinator.async_refresh()
        await hass.async_block_till_done()
        state = hass.states.get("sensor.irrigation_monitor_switch_rachio_zone_1_status")
        assert state.state == "leak_detected"

        # Zone turns OFF
        hass.states.async_set(mock_valve_entities[0], "off")
        hass.states.async_set("sensor.flume_current_interval", "0.0")
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        # Zone turns ON again: ramp-up counter should reset to 1
        hass.states.async_set(mock_valve_entities[0], "on")
        hass.states.async_set("sensor.flume_current_interval", "4.0")
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        # After re-start: should be "running" (ramp-up active again)
        state = hass.states.get("sensor.irrigation_monitor_switch_rachio_zone_1_status")
        assert state.state == "running", (
            f"Expected 'running' after re-start (ramp-up reset), got '{state.state}'"
        )


# ---------------------------------------------------------------------------
# DETECT-03: Auto-shutoff
# ---------------------------------------------------------------------------


async def test_leak_triggers_shutoff(
    hass: HomeAssistant,
    mock_calibrated_config_entry: MockConfigEntry,
    mock_valve_entities: list[str],
) -> None:
    """DETECT-03: shutoff_enabled=True, leak detected -> _turn_valve called with turn_on=False."""
    await hass.config_entries.async_setup(mock_calibrated_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_calibrated_config_entry.runtime_data

    hass.states.async_set(mock_valve_entities[0], "on")
    hass.states.async_set("sensor.flume_current_interval", "4.0")

    with patch.object(
        coordinator,
        "_turn_valve",
        new_callable=AsyncMock,
    ) as mock_turn_valve:
        await coordinator.async_refresh()
        await hass.async_block_till_done()
        mock_turn_valve.assert_awaited_once_with(mock_valve_entities[0], turn_on=False)

    state = hass.states.get("sensor.irrigation_monitor_switch_rachio_zone_1_status")
    assert state.state == "leak_detected"


async def test_leak_no_shutoff_when_disabled(
    hass: HomeAssistant,
    mock_valve_entities: list[str],
    mock_flume_entity: str,
) -> None:
    """DETECT-03: shutoff_enabled=False, leak detected -> _turn_valve NOT called. Status still leak_detected."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_FLUME_ENTITY_ID: mock_flume_entity,
            CONF_MONITORED_ZONES: mock_valve_entities[:2],
            CONF_POLL_INTERVAL: 30,
        },
        options={
            CONF_ZONES: {
                mock_valve_entities[0]: {
                    CONF_SHUTOFF_ENABLED: False,  # shutoff disabled
                    CONF_ALERTS_ENABLED: True,
                    CONF_CALIBRATED_FLOW: 2.0,
                    CONF_THRESHOLD_MULTIPLIER: 1.5,
                },
                mock_valve_entities[1]: {
                    CONF_SHUTOFF_ENABLED: True,
                    CONF_ALERTS_ENABLED: True,
                    CONF_CALIBRATED_FLOW: None,
                    CONF_THRESHOLD_MULTIPLIER: 1.5,
                },
            },
            CONF_RAMP_UP_POLLS: 0,
        },
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    coordinator = entry.runtime_data

    hass.states.async_set(mock_valve_entities[0], "on")
    hass.states.async_set("sensor.flume_current_interval", "4.0")

    with patch.object(
        coordinator,
        "_turn_valve",
        new_callable=AsyncMock,
    ) as mock_turn_valve:
        await coordinator.async_refresh()
        await hass.async_block_till_done()
        mock_turn_valve.assert_not_called()

    state = hass.states.get("sensor.irrigation_monitor_switch_rachio_zone_1_status")
    assert state.state == "leak_detected"


# ---------------------------------------------------------------------------
# DETECT-04: Notification firing and deduplication
# ---------------------------------------------------------------------------


async def test_leak_notification_fires(
    hass: HomeAssistant,
    mock_calibrated_config_entry: MockConfigEntry,
    mock_valve_entities: list[str],
) -> None:
    """DETECT-04: alerts_enabled=True, leak detected -> persistent_notification async_create called."""
    await hass.config_entries.async_setup(mock_calibrated_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_calibrated_config_entry.runtime_data

    hass.states.async_set(mock_valve_entities[0], "on")
    hass.states.async_set("sensor.flume_current_interval", "4.0")

    with patch.object(coordinator, "_turn_valve", new_callable=AsyncMock), \
         patch("custom_components.irrigation_monitor.coordinator.async_create") as mock_notify:
        await coordinator.async_refresh()
        await hass.async_block_till_done()
        mock_notify.assert_called_once()


async def test_leak_notification_dedup(
    hass: HomeAssistant,
    mock_calibrated_config_entry: MockConfigEntry,
    mock_valve_entities: list[str],
) -> None:
    """DETECT-04: Second poll with same leak does NOT fire a second notification."""
    await hass.config_entries.async_setup(mock_calibrated_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_calibrated_config_entry.runtime_data

    hass.states.async_set(mock_valve_entities[0], "on")
    hass.states.async_set("sensor.flume_current_interval", "4.0")

    with patch.object(coordinator, "_turn_valve", new_callable=AsyncMock), \
         patch("custom_components.irrigation_monitor.coordinator.async_create") as mock_notify:
        # First refresh: notification fires
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        # Second refresh: same leak, no new notification
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        assert mock_notify.call_count == 1, (
            f"Expected 1 notification call, got {mock_notify.call_count}"
        )


async def test_leak_notification_clears_on_restart(
    hass: HomeAssistant,
    mock_calibrated_config_entry: MockConfigEntry,
    mock_valve_entities: list[str],
) -> None:
    """DETECT-04: ON->OFF clears dedup; next ON with leak fires notification again."""
    await hass.config_entries.async_setup(mock_calibrated_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_calibrated_config_entry.runtime_data

    with patch.object(coordinator, "_turn_valve", new_callable=AsyncMock), \
         patch("custom_components.irrigation_monitor.coordinator.async_create") as mock_notify:
        # Zone 1 on, flow=4.0 -> first leak notification
        hass.states.async_set(mock_valve_entities[0], "on")
        hass.states.async_set("sensor.flume_current_interval", "4.0")
        await coordinator.async_refresh()
        await hass.async_block_till_done()
        assert mock_notify.call_count == 1

        # Zone 1 off -> clears _leak_notified
        hass.states.async_set(mock_valve_entities[0], "off")
        hass.states.async_set("sensor.flume_current_interval", "0.0")
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        # Zone 1 on again -> second leak notification should fire
        hass.states.async_set(mock_valve_entities[0], "on")
        hass.states.async_set("sensor.flume_current_interval", "4.0")
        await coordinator.async_refresh()
        await hass.async_block_till_done()
        assert mock_notify.call_count == 2, (
            f"Expected 2 notification calls after restart, got {mock_notify.call_count}"
        )


async def test_leak_notification_content(
    hass: HomeAssistant,
    mock_calibrated_config_entry: MockConfigEntry,
    mock_valve_entities: list[str],
) -> None:
    """DETECT-04: Notification message contains zone_id, flow rate, calibrated flow, shutoff status."""
    await hass.config_entries.async_setup(mock_calibrated_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_calibrated_config_entry.runtime_data

    hass.states.async_set(mock_valve_entities[0], "on")
    hass.states.async_set("sensor.flume_current_interval", "4.0")

    with patch.object(coordinator, "_turn_valve", new_callable=AsyncMock), \
         patch("custom_components.irrigation_monitor.coordinator.async_create") as mock_notify:
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        assert mock_notify.called, "async_create was not called"
        call_args = mock_notify.call_args
        # async_create(hass, message, title=..., notification_id=...)
        # positional args: (hass, message)
        message = call_args.args[1]
        title = call_args.kwargs.get("title")
        notification_id = call_args.kwargs.get("notification_id")

        assert "switch.rachio_zone_1" in message, f"zone_id not in message: {message!r}"
        assert "4.0 gal/min" in message, f"flow rate not in message: {message!r}"
        assert "2.0 gal/min" in message, f"calibrated flow not in message: {message!r}"
        assert "Valve has been shut off." in message, f"shutoff msg not in message: {message!r}"
        assert title == "Irrigation Monitor — Leak Alert", f"Wrong title: {title!r}"
        assert notification_id == "leak_switch_rachio_zone_1", f"Wrong notif ID: {notification_id!r}"


# ---------------------------------------------------------------------------
# DETECT-05: Acknowledge button clears status
# ---------------------------------------------------------------------------


async def test_acknowledge_clears_status(
    hass: HomeAssistant,
    mock_calibrated_config_entry: MockConfigEntry,
    mock_valve_entities: list[str],
) -> None:
    """DETECT-05: Pressing acknowledge button clears 'leak_detected' status to 'idle'."""
    await hass.config_entries.async_setup(mock_calibrated_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_calibrated_config_entry.runtime_data

    # Trigger leak (mock _turn_valve to avoid ServiceNotFound in test harness)
    hass.states.async_set(mock_valve_entities[0], "on")
    hass.states.async_set("sensor.flume_current_interval", "4.0")
    with patch.object(coordinator, "_turn_valve", new_callable=AsyncMock):
        await coordinator.async_refresh()
        await hass.async_block_till_done()

    state = hass.states.get("sensor.irrigation_monitor_switch_rachio_zone_1_status")
    assert state.state == "leak_detected"

    # Press the acknowledge button
    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.irrigation_monitor_switch_rachio_zone_1_acknowledge_leak"},
        blocking=True,
    )
    await hass.async_block_till_done()

    state = hass.states.get("sensor.irrigation_monitor_switch_rachio_zone_1_status")
    assert state.state == "idle", f"Expected 'idle' after acknowledge, got '{state.state}'"
