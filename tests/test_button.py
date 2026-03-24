"""Tests for the calibrate button entity and calibration sequence."""
import pytest
from unittest.mock import patch, AsyncMock, call
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.irrigation_monitor.const import (
    DOMAIN,
    CONF_ZONES,
    CONF_CALIBRATED_FLOW,
)


async def _setup_integration(hass: HomeAssistant, entry: MockConfigEntry):
    """Load the integration and return the coordinator."""
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry.runtime_data


async def test_button_entities_created(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """CALIB-01: verify button entities are registered per monitored zone."""
    await _setup_integration(hass, mock_config_entry)

    assert hass.states.get("button.irrigation_monitor_switch_rachio_zone_1_calibrate") is not None
    assert hass.states.get("button.irrigation_monitor_switch_rachio_zone_2_calibrate") is not None


async def test_calibrate_aborts_on_background_flow(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """CALIB-02: background flow > threshold aborts calibration with notification."""
    coordinator = await _setup_integration(hass, mock_config_entry)

    zone_id = "switch.rachio_zone_1"
    # Set Flume flow above threshold (0.1 default)
    hass.states.async_set("sensor.flume_current_interval", "0.5")

    service_calls = []

    async def mock_service(call):
        service_calls.append(call)

    hass.services.async_register("switch", "turn_on", mock_service)
    hass.services.async_register("switch", "turn_off", mock_service)

    with patch(
        "custom_components.irrigation_monitor.coordinator.async_create"
    ) as mock_notify:
        await coordinator.async_calibrate_zone(zone_id)

        # Should fire background flow notification
        mock_notify.assert_called_once()
        call_args = mock_notify.call_args
        assert "Background water flow detected" in call_args[0][1]
        assert call_args[1]["notification_id"] == f"calib_{zone_id}_background"

    # Valve must NOT have been turned on
    turn_on_calls = [c for c in service_calls if c.service == "turn_on"]
    assert len(turn_on_calls) == 0


async def test_calibrate_aborts_when_zone_running(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """CALIB-03: zone already on aborts calibration with notification."""
    coordinator = await _setup_integration(hass, mock_config_entry)

    zone_id = "switch.rachio_zone_1"
    # Set Flume flow below threshold to pass background check
    hass.states.async_set("sensor.flume_current_interval", "0.0")
    # Set zone state to on
    hass.states.async_set(zone_id, "on")

    with patch(
        "custom_components.irrigation_monitor.coordinator.async_create"
    ) as mock_notify:
        await coordinator.async_calibrate_zone(zone_id)

        mock_notify.assert_called_once()
        call_args = mock_notify.call_args
        assert "already running" in call_args[0][1]
        assert call_args[1]["notification_id"] == f"calib_{zone_id}_running"


async def test_calibration_full_sequence(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """CALIB-04: full sequence — valve on, stabilize, sample, average, save."""
    coordinator = await _setup_integration(hass, mock_config_entry)

    zone_id = "switch.rachio_zone_1"
    # Set Flume to 0.0 to pass background check
    hass.states.async_set("sensor.flume_current_interval", "0.0")
    # Zone is off (default from conftest)

    service_calls = []

    async def mock_service(svc_call):
        service_calls.append(svc_call)

    hass.services.async_register("switch", "turn_on", mock_service)
    hass.services.async_register("switch", "turn_off", mock_service)

    # After valve turns on, set Flume to a stable value so variance detection passes
    original_sleep = None

    async def mock_sleep(delay):
        # After first sleep (variance poll), update Flume state to stable value
        hass.states.async_set("sensor.flume_current_interval", "2.0")

    with patch(
        "custom_components.irrigation_monitor.coordinator.asyncio.sleep",
        side_effect=mock_sleep,
    ):
        await coordinator.async_calibrate_zone(zone_id)

    # calibrated_flow should have been written to options
    assert mock_config_entry.options[CONF_ZONES][zone_id][CONF_CALIBRATED_FLOW] == pytest.approx(2.0)


async def test_calibration_stabilization_timeout(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """CALIB-04: 60s stabilization timeout fires failure notification and turns valve off."""
    coordinator = await _setup_integration(hass, mock_config_entry)

    zone_id = "switch.rachio_zone_1"
    hass.states.async_set("sensor.flume_current_interval", "0.0")

    service_calls = []

    async def mock_service(svc_call):
        service_calls.append(svc_call)

    hass.services.async_register("switch", "turn_on", mock_service)
    hass.services.async_register("switch", "turn_off", mock_service)

    # Use a counter to alternate Flume values so stdev never drops below threshold
    call_counter = [0]

    async def mock_sleep_alternating(delay):
        call_counter[0] += 1
        # Alternate between two very different values so stdev stays high
        val = "1.0" if call_counter[0] % 2 == 0 else "5.0"
        hass.states.async_set("sensor.flume_current_interval", val)

    with patch(
        "custom_components.irrigation_monitor.coordinator.asyncio.sleep",
        side_effect=mock_sleep_alternating,
    ):
        with patch(
            "custom_components.irrigation_monitor.coordinator.async_create"
        ) as mock_notify:
            await coordinator.async_calibrate_zone(zone_id)

            # Should have fired a failure notification
            fail_calls = [
                c for c in mock_notify.call_args_list
                if c[1].get("notification_id", "").endswith("_fail")
            ]
            assert len(fail_calls) > 0
            fail_msg = fail_calls[0][0][1]
            assert "stabilize" in fail_msg.lower() or "Calibration failed" in fail_msg

    # Valve must have been turned off even after failure
    turn_off_calls = [c for c in service_calls if c.service == "turn_off"]
    assert len(turn_off_calls) >= 1


async def test_calibration_flume_unavailable_mid_run(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """CALIB-04: Flume goes unavailable mid-calibration — fail gracefully and turn valve off."""
    coordinator = await _setup_integration(hass, mock_config_entry)

    zone_id = "switch.rachio_zone_1"
    # Start with valid flow (below threshold)
    hass.states.async_set("sensor.flume_current_interval", "0.0")

    service_calls = []

    async def mock_service(svc_call):
        service_calls.append(svc_call)

    hass.services.async_register("switch", "turn_on", mock_service)
    hass.services.async_register("switch", "turn_off", mock_service)

    call_counter = [0]

    async def mock_sleep_then_unavail(delay):
        call_counter[0] += 1
        if call_counter[0] == 1:
            # After first sleep, Flume goes unavailable
            hass.states.async_set("sensor.flume_current_interval", STATE_UNAVAILABLE)

    with patch(
        "custom_components.irrigation_monitor.coordinator.asyncio.sleep",
        side_effect=mock_sleep_then_unavail,
    ):
        with patch(
            "custom_components.irrigation_monitor.coordinator.async_create"
        ) as mock_notify:
            await coordinator.async_calibrate_zone(zone_id)

            fail_calls = [
                c for c in mock_notify.call_args_list
                if c[1].get("notification_id", "").endswith("_fail")
            ]
            assert len(fail_calls) > 0
            fail_msg = fail_calls[0][0][1]
            assert "unavailable" in fail_msg.lower() or "Calibration failed" in fail_msg

    # Valve must have been turned off even after failure
    turn_off_calls = [c for c in service_calls if c.service == "turn_off"]
    assert len(turn_off_calls) >= 1


async def test_calibration_saves_to_options(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """CALIB-05: first calibration writes calibrated_flow to ConfigEntry.options."""
    coordinator = await _setup_integration(hass, mock_config_entry)

    zone_id = "switch.rachio_zone_1"
    hass.states.async_set("sensor.flume_current_interval", "0.0")

    service_calls = []

    async def mock_service(svc_call):
        service_calls.append(svc_call)

    hass.services.async_register("switch", "turn_on", mock_service)
    hass.services.async_register("switch", "turn_off", mock_service)

    async def mock_sleep(delay):
        hass.states.async_set("sensor.flume_current_interval", "2.0")

    with patch(
        "custom_components.irrigation_monitor.coordinator.asyncio.sleep",
        side_effect=mock_sleep,
    ):
        await coordinator.async_calibrate_zone(zone_id)

    # The calibrated_flow must be written to ConfigEntry.options
    assert mock_config_entry.options[CONF_ZONES][zone_id][CONF_CALIBRATED_FLOW] == pytest.approx(2.0)


async def test_recalibration_pending_flow(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """CALIB-05: re-calibration stores pending result and fires confirm notification."""
    coordinator = await _setup_integration(hass, mock_config_entry)

    zone_id = "switch.rachio_zone_1"
    other_zone_id = "switch.rachio_zone_2"

    # Set existing calibrated_flow to simulate a previously-calibrated zone
    hass.config_entries.async_update_entry(
        mock_config_entry,
        options={
            CONF_ZONES: {
                zone_id: {
                    **mock_config_entry.options[CONF_ZONES][zone_id],
                    CONF_CALIBRATED_FLOW: 1.5,
                },
                other_zone_id: mock_config_entry.options[CONF_ZONES][other_zone_id],
            }
        },
    )

    # Pass background check (Flume at 0.0) and zone is off
    hass.states.async_set("sensor.flume_current_interval", "0.0")

    service_calls = []

    async def mock_service(svc_call):
        service_calls.append(svc_call)

    hass.services.async_register("switch", "turn_on", mock_service)
    hass.services.async_register("switch", "turn_off", mock_service)

    async def mock_sleep(delay):
        # Update Flume to stable value so variance detection passes quickly
        hass.states.async_set("sensor.flume_current_interval", "2.0")

    with patch(
        "custom_components.irrigation_monitor.coordinator.asyncio.sleep",
        side_effect=mock_sleep,
    ):
        await coordinator.async_calibrate_zone(zone_id)

    # New flow should be stored as pending (not yet written to options)
    assert coordinator._pending_calibrations[zone_id] == pytest.approx(2.0)
    # Old value must NOT be overwritten yet
    assert mock_config_entry.options[CONF_ZONES][zone_id][CONF_CALIBRATED_FLOW] == pytest.approx(1.5)


async def test_recalibration_save_action(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """CALIB-05: Save action writes new calibrated_flow; Cancel discards pending result."""
    coordinator = await _setup_integration(hass, mock_config_entry)

    zone_id = "switch.rachio_zone_1"
    other_zone_id = "switch.rachio_zone_2"
    zone_slug = zone_id.replace(".", "_")

    # Set existing calibrated_flow
    hass.config_entries.async_update_entry(
        mock_config_entry,
        options={
            CONF_ZONES: {
                zone_id: {
                    **mock_config_entry.options[CONF_ZONES][zone_id],
                    CONF_CALIBRATED_FLOW: 1.5,
                },
                other_zone_id: mock_config_entry.options[CONF_ZONES][other_zone_id],
            }
        },
    )

    hass.states.async_set("sensor.flume_current_interval", "0.0")

    service_calls = []

    async def mock_service(svc_call):
        service_calls.append(svc_call)

    hass.services.async_register("switch", "turn_on", mock_service)
    hass.services.async_register("switch", "turn_off", mock_service)

    async def mock_sleep(delay):
        hass.states.async_set("sensor.flume_current_interval", "2.0")

    # Run re-calibration to get pending state
    with patch(
        "custom_components.irrigation_monitor.coordinator.asyncio.sleep",
        side_effect=mock_sleep,
    ):
        await coordinator.async_calibrate_zone(zone_id)

    assert coordinator._pending_calibrations[zone_id] == pytest.approx(2.0)

    # --- Test Save action ---
    hass.bus.async_fire(
        "mobile_app_notification_action",
        {"action": f"irrigation_monitor_confirm_calibration_{zone_slug}"},
    )
    await hass.async_block_till_done()

    # New flow must be written to options
    assert mock_config_entry.options[CONF_ZONES][zone_id][CONF_CALIBRATED_FLOW] == pytest.approx(2.0)
    # Pending state must be cleared
    assert zone_id not in coordinator._pending_calibrations

    # --- Test Cancel action ---
    # Run re-calibration again to get new pending state
    # Reset old flow value first (it was overwritten to 2.0 by save)
    hass.config_entries.async_update_entry(
        mock_config_entry,
        options={
            CONF_ZONES: {
                zone_id: {
                    **mock_config_entry.options[CONF_ZONES][zone_id],
                    CONF_CALIBRATED_FLOW: 2.0,
                },
                other_zone_id: mock_config_entry.options[CONF_ZONES][other_zone_id],
            }
        },
    )

    hass.states.async_set("sensor.flume_current_interval", "0.0")

    async def mock_sleep_3(delay):
        hass.states.async_set("sensor.flume_current_interval", "3.0")

    with patch(
        "custom_components.irrigation_monitor.coordinator.asyncio.sleep",
        side_effect=mock_sleep_3,
    ):
        await coordinator.async_calibrate_zone(zone_id)

    assert coordinator._pending_calibrations[zone_id] == pytest.approx(3.0)

    # Fire cancel event
    hass.bus.async_fire(
        "mobile_app_notification_action",
        {"action": f"irrigation_monitor_cancel_calibration_{zone_slug}"},
    )
    await hass.async_block_till_done()

    # Pending must be cleared
    assert zone_id not in coordinator._pending_calibrations
    # Options must still hold the previously-saved 2.0 (cancel did not change it)
    assert mock_config_entry.options[CONF_ZONES][zone_id][CONF_CALIBRATED_FLOW] == pytest.approx(2.0)


async def test_calibration_turns_valve_off_on_success(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """CALIB-06: valve is turned off after successful calibration."""
    coordinator = await _setup_integration(hass, mock_config_entry)

    zone_id = "switch.rachio_zone_1"
    hass.states.async_set("sensor.flume_current_interval", "0.0")

    service_calls = []

    async def mock_service(svc_call):
        service_calls.append(svc_call)

    hass.services.async_register("switch", "turn_on", mock_service)
    hass.services.async_register("switch", "turn_off", mock_service)

    async def mock_sleep(delay):
        hass.states.async_set("sensor.flume_current_interval", "2.0")

    with patch(
        "custom_components.irrigation_monitor.coordinator.asyncio.sleep",
        side_effect=mock_sleep,
    ):
        await coordinator.async_calibrate_zone(zone_id)

    # Verify turn_off was called with the zone entity_id
    turn_off_calls = [c for c in service_calls if c.service == "turn_off"]
    assert len(turn_off_calls) >= 1
    assert any(
        c.data.get("entity_id") == zone_id for c in turn_off_calls
    )


async def test_calibration_turns_valve_off_on_failure(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """CALIB-06: valve is turned off after calibration failure."""
    coordinator = await _setup_integration(hass, mock_config_entry)

    zone_id = "switch.rachio_zone_1"
    hass.states.async_set("sensor.flume_current_interval", "0.0")

    service_calls = []

    async def mock_service(svc_call):
        service_calls.append(svc_call)

    hass.services.async_register("switch", "turn_on", mock_service)
    hass.services.async_register("switch", "turn_off", mock_service)

    call_counter = [0]

    async def mock_sleep_then_unavail(delay):
        call_counter[0] += 1
        if call_counter[0] == 1:
            hass.states.async_set("sensor.flume_current_interval", STATE_UNAVAILABLE)

    with patch(
        "custom_components.irrigation_monitor.coordinator.asyncio.sleep",
        side_effect=mock_sleep_then_unavail,
    ):
        await coordinator.async_calibrate_zone(zone_id)

    # Valve must have been turned off even after failure
    turn_off_calls = [c for c in service_calls if c.service == "turn_off"]
    assert len(turn_off_calls) >= 1


async def test_calibration_success_notification(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """CALIB-06: success notification contains the measured flow rate."""
    coordinator = await _setup_integration(hass, mock_config_entry)

    zone_id = "switch.rachio_zone_1"
    hass.states.async_set("sensor.flume_current_interval", "0.0")

    service_calls = []

    async def mock_service(svc_call):
        service_calls.append(svc_call)

    hass.services.async_register("switch", "turn_on", mock_service)
    hass.services.async_register("switch", "turn_off", mock_service)

    async def mock_sleep(delay):
        hass.states.async_set("sensor.flume_current_interval", "2.0")

    with patch(
        "custom_components.irrigation_monitor.coordinator.asyncio.sleep",
        side_effect=mock_sleep,
    ):
        with patch(
            "custom_components.irrigation_monitor.coordinator.async_create"
        ) as mock_notify:
            await coordinator.async_calibrate_zone(zone_id)

            # Find the success notification
            success_calls = [
                c for c in mock_notify.call_args_list
                if c[1].get("notification_id", "").endswith("_success")
            ]
            assert len(success_calls) == 1
            success_msg = success_calls[0][0][1]
            assert "calibrated" in success_msg.lower()
            assert "2.0 gal/min" in success_msg
