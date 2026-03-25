"""Tests for Lovelace card static path registration."""
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.irrigation_monitor.const import DOMAIN


async def test_www_file_exists():
    """The JS card file must exist in the www/ directory."""
    js_path = Path(__file__).parent.parent / "custom_components" / "irrigation_monitor" / "www" / "irrigation-monitor-card.js"
    assert js_path.is_file(), f"Card JS file not found at {js_path}"


async def test_static_path_registered(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
):
    """async_setup_entry must register the JS file as a static path."""
    mock_register = AsyncMock()
    hass.http = AsyncMock()
    hass.http.async_register_static_paths = mock_register

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    mock_register.assert_called_once()
    args = mock_register.call_args[0][0]
    assert len(args) == 1
    config = args[0]
    assert config.url_path == "/irrigation_monitor/irrigation-monitor-card.js"
    assert "irrigation-monitor-card.js" in config.path
    assert config.cache_headers is True
