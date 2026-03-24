"""Tests for the calibrate button entity and calibration sequence."""
import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry


@pytest.mark.xfail(reason="not implemented")
async def test_button_entities_created(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """CALIB-01: verify button entities are registered per monitored zone."""
    pytest.fail("not implemented")


@pytest.mark.xfail(reason="not implemented")
async def test_calibrate_aborts_on_background_flow(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """CALIB-02: background flow > threshold aborts calibration with notification."""
    pytest.fail("not implemented")


@pytest.mark.xfail(reason="not implemented")
async def test_calibrate_aborts_when_zone_running(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """CALIB-03: zone already on aborts calibration with notification."""
    pytest.fail("not implemented")


@pytest.mark.xfail(reason="not implemented")
async def test_calibration_full_sequence(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """CALIB-04: full sequence — valve on, stabilize, sample, average, save."""
    pytest.fail("not implemented")


@pytest.mark.xfail(reason="not implemented")
async def test_calibration_stabilization_timeout(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """CALIB-04: 60s stabilization timeout fires failure notification and turns valve off."""
    pytest.fail("not implemented")


@pytest.mark.xfail(reason="not implemented")
async def test_calibration_flume_unavailable_mid_run(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """CALIB-04: Flume goes unavailable mid-calibration — fail gracefully and turn valve off."""
    pytest.fail("not implemented")


@pytest.mark.xfail(reason="not implemented")
async def test_calibration_saves_to_options(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """CALIB-05: first calibration writes calibrated_flow to ConfigEntry.options."""
    pytest.fail("not implemented")


@pytest.mark.xfail(reason="not implemented")
async def test_recalibration_pending_flow(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """CALIB-05: re-calibration stores pending result and fires confirm notification."""
    pytest.fail("not implemented")


@pytest.mark.xfail(reason="not implemented")
async def test_recalibration_save_action(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """CALIB-05: Save action writes new calibrated_flow; Cancel discards pending result."""
    pytest.fail("not implemented")


@pytest.mark.xfail(reason="not implemented")
async def test_calibration_turns_valve_off_on_success(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """CALIB-06: valve is turned off after successful calibration."""
    pytest.fail("not implemented")


@pytest.mark.xfail(reason="not implemented")
async def test_calibration_turns_valve_off_on_failure(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """CALIB-06: valve is turned off after calibration failure."""
    pytest.fail("not implemented")


@pytest.mark.xfail(reason="not implemented")
async def test_calibration_success_notification(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """CALIB-06: success notification contains the measured flow rate."""
    pytest.fail("not implemented")
