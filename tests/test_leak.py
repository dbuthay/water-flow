"""Wave 0 test stubs for Phase 5 leak detection (DETECT-01 through DETECT-04).

All tests are marked xfail(strict=True) — they will be turned GREEN in Plan 05-02
once the sensor and button entities are wired to coordinator._leak_statuses.
"""
import pytest

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.irrigation_monitor.const import (
    CONF_CALIBRATED_FLOW,
    CONF_SHUTOFF_ENABLED,
    CONF_ALERTS_ENABLED,
    CONF_RAMP_UP_POLLS,
    CONF_THRESHOLD_MULTIPLIER,
    CONF_ZONES,
)


# ---------------------------------------------------------------------------
# DETECT-01: Basic threshold comparison
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="RED — not yet implemented", strict=True)
async def test_leak_detection_fires(
    hass: HomeAssistant,
    mock_calibrated_config_entry: MockConfigEntry,
    mock_valve_entities: list[str],
) -> None:
    """DETECT-01: Zone 1 ON, flow 4.0 > 2.0*1.5=3.0 → status becomes 'leak_detected'."""
    pytest.fail("Not implemented")


@pytest.mark.xfail(reason="RED — not yet implemented", strict=True)
async def test_uncalibrated_zone_no_leak(
    hass: HomeAssistant,
    mock_calibrated_config_entry: MockConfigEntry,
    mock_valve_entities: list[str],
) -> None:
    """DETECT-01: Zone 2 (uncalibrated) ON, high flow → status stays 'running', not 'leak_detected'."""
    pytest.fail("Not implemented")


# ---------------------------------------------------------------------------
# DETECT-02: Ramp-up skip window
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="RED — not yet implemented", strict=True)
async def test_ramp_up_skips_detection(
    hass: HomeAssistant,
    mock_calibrated_config_entry: MockConfigEntry,
    mock_valve_entities: list[str],
) -> None:
    """DETECT-02: With ramp_up_polls=2, first 2 polls skip detection even if flow exceeds threshold."""
    pytest.fail("Not implemented")


@pytest.mark.xfail(reason="RED — not yet implemented", strict=True)
async def test_ramp_up_resets_on_restart(
    hass: HomeAssistant,
    mock_calibrated_config_entry: MockConfigEntry,
    mock_valve_entities: list[str],
) -> None:
    """DETECT-02: OFF->ON transition resets ramp counter; detection resumes after countdown."""
    pytest.fail("Not implemented")


# ---------------------------------------------------------------------------
# DETECT-03: Auto-shutoff
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="RED — not yet implemented", strict=True)
async def test_leak_triggers_shutoff(
    hass: HomeAssistant,
    mock_calibrated_config_entry: MockConfigEntry,
    mock_valve_entities: list[str],
) -> None:
    """DETECT-03: shutoff_enabled=True, leak detected → _turn_valve called with turn_on=False."""
    pytest.fail("Not implemented")


@pytest.mark.xfail(reason="RED — not yet implemented", strict=True)
async def test_leak_no_shutoff_when_disabled(
    hass: HomeAssistant,
    mock_calibrated_config_entry: MockConfigEntry,
    mock_valve_entities: list[str],
) -> None:
    """DETECT-03: shutoff_enabled=False, leak detected → _turn_valve NOT called."""
    pytest.fail("Not implemented")


# ---------------------------------------------------------------------------
# DETECT-04: Notification firing and deduplication
# ---------------------------------------------------------------------------


@pytest.mark.xfail(reason="RED — not yet implemented", strict=True)
async def test_leak_notification_fires(
    hass: HomeAssistant,
    mock_calibrated_config_entry: MockConfigEntry,
    mock_valve_entities: list[str],
) -> None:
    """DETECT-04: alerts_enabled=True, leak detected → persistent_notification.async_create called."""
    pytest.fail("Not implemented")


@pytest.mark.xfail(reason="RED — not yet implemented", strict=True)
async def test_leak_notification_dedup(
    hass: HomeAssistant,
    mock_calibrated_config_entry: MockConfigEntry,
    mock_valve_entities: list[str],
) -> None:
    """DETECT-04: Second poll with same leak does NOT fire a second notification."""
    pytest.fail("Not implemented")


@pytest.mark.xfail(reason="RED — not yet implemented", strict=True)
async def test_leak_notification_clears_on_restart(
    hass: HomeAssistant,
    mock_calibrated_config_entry: MockConfigEntry,
    mock_valve_entities: list[str],
) -> None:
    """DETECT-04: ON->OFF clears dedup; next ON with leak fires notification again."""
    pytest.fail("Not implemented")


@pytest.mark.xfail(reason="RED — not yet implemented", strict=True)
async def test_leak_notification_content(
    hass: HomeAssistant,
    mock_calibrated_config_entry: MockConfigEntry,
    mock_valve_entities: list[str],
) -> None:
    """DETECT-04: Notification message contains zone_id, flow rate, calibrated flow, shutoff status."""
    pytest.fail("Not implemented")
