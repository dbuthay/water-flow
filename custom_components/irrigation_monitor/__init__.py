"""The Irrigation Monitor integration."""
from __future__ import annotations

from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import IrrigationCoordinator

PLATFORMS: list[str] = ["sensor", "button", "switch", "number"]

type IrrigationConfigEntry = ConfigEntry[IrrigationCoordinator]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register Lovelace card JS as a static path at domain load time.

    Uses /irrigation_monitor/ prefix to avoid conflicting with HA's
    built-in /local/ handler which serves the config www directory.
    """
    import logging
    _LOGGER = logging.getLogger(__name__)

    www_path = str(Path(__file__).parent / "www" / "irrigation-monitor-card.js")
    url = "/irrigation_monitor/irrigation-monitor-card.js"
    try:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(url, www_path, True)]
        )
        _LOGGER.info("Registered Lovelace card at %s -> %s", url, www_path)
    except Exception as err:
        _LOGGER.warning("Could not register Lovelace card static path: %s", err)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: IrrigationConfigEntry) -> bool:
    """Set up irrigation_monitor from a config entry."""
    coordinator = IrrigationCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: IrrigationConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
