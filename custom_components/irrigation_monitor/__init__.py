"""The Irrigation Monitor integration."""
from __future__ import annotations

from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import IrrigationCoordinator

PLATFORMS: list[str] = ["sensor", "button"]

type IrrigationConfigEntry = ConfigEntry[IrrigationCoordinator]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register Lovelace card JS as a static path at domain load time.

    Runs once when the integration is loaded, before any config entries are
    set up. This ensures the card file is served even if async_setup_entry
    fails (e.g., Flume sensor unavailable during first load).
    """
    www_path = str(Path(__file__).parent / "www" / "irrigation-monitor-card.js")
    try:
        await hass.http.async_register_static_paths(
            [StaticPathConfig("/local/irrigation-monitor-card.js", www_path, True)]
        )
    except Exception:
        # Already registered (e.g., HA reload) -- safe to ignore
        pass
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
