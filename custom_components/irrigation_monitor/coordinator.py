"""DataUpdateCoordinator for the Irrigation Monitor integration."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_CALIBRATED_FLOW,
    CONF_FLUME_ENTITY_ID,
    CONF_MONITORED_ZONES,
    CONF_POLL_INTERVAL,
    CONF_THRESHOLD_MULTIPLIER,
    CONF_ZONES,
    DOMAIN,
    SAVE_DELAY,
    STORAGE_KEY,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class ZoneData:
    """Per-zone data returned by the coordinator each poll."""

    flow_rate: float    # gal/min — 0.0 when idle
    daily_usage: float  # gal accumulated since midnight
    is_available: bool  # True when Flume data is valid


class IrrigationCoordinator(DataUpdateCoordinator[dict[str, ZoneData]]):
    """Coordinator that polls the Flume sensor and attributes flow to zones."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._entry = entry
        self._store = Store(hass, version=STORAGE_VERSION, key=STORAGE_KEY)
        self._daily_totals: dict[str, float] = {}
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,  # REQUIRED: explicit config_entry (HA 2026.x)
            name=DOMAIN,
            update_interval=timedelta(seconds=entry.data[CONF_POLL_INTERVAL]),
        )

    async def _async_setup(self) -> None:
        """Load persisted totals on first setup and register midnight callback."""
        stored = await self._store.async_load()
        today = date.today().isoformat()
        if stored and stored.get("date") == today:
            self._daily_totals = dict(stored.get("zones", {}))
        else:
            # HA was offline at midnight or first run — reset totals
            self._daily_totals = {}
            self._store.async_delay_save(self._data_to_save, 0)

        # Register midnight reset, cancelled on entry unload
        unsub = async_track_time_change(
            self.hass, self._midnight_reset, hour=0, minute=0, second=0
        )
        self._entry.async_on_unload(unsub)

        # Flush Store to disk when entry is unloaded (async_delay_save won't fire until
        # EVENT_HOMEASSISTANT_FINAL_WRITE, which is too late for tests + entry reload)
        async def _flush_store() -> None:
            await self._store.async_save(self._data_to_save())

        self._entry.async_on_unload(_flush_store)

    async def _async_update_data(self) -> dict[str, ZoneData]:
        """Poll Flume and attribute flow to monitored zones."""
        flume_id = self._entry.data[CONF_FLUME_ENTITY_ID]
        state = self.hass.states.get(flume_id)
        if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            raise UpdateFailed(f"Flume sensor {flume_id} is unavailable")
        try:
            flume_flow = float(state.state)
        except ValueError as err:
            raise UpdateFailed(
                f"Flume sensor returned non-numeric state: {state.state}"
            ) from err

        zones_config = self._entry.options.get(CONF_ZONES, {})
        monitored: list[str] = self._entry.data[CONF_MONITORED_ZONES]
        interval_seconds: int = self._entry.data[CONF_POLL_INTERVAL]
        result: dict[str, ZoneData] = {}

        # Build active calibrated zones dict for multi-zone overlap detection
        active_calibrated: dict[str, float] = {
            z: zones_config[z][CONF_CALIBRATED_FLOW]
            for z in monitored
            if self._zone_is_on(z)
            and zones_config.get(z, {}).get(CONF_CALIBRATED_FLOW) is not None
        }
        calibrated_sum = sum(active_calibrated.values())

        for zone_id in monitored:
            zone_cfg = zones_config.get(zone_id, {})
            is_on = self._zone_is_on(zone_id)
            calibrated_flow = zone_cfg.get(CONF_CALIBRATED_FLOW)

            if not is_on:
                flow_rate = 0.0
                usage_increment = 0.0
            elif calibrated_flow is not None:
                # This zone is calibrated and running
                threshold = zone_cfg.get(CONF_THRESHOLD_MULTIPLIER, 1.5)
                if (
                    calibrated_sum > 0
                    and abs(flume_flow - calibrated_sum) / calibrated_sum
                    <= (threshold - 1.0)
                ):
                    # Flume reading matches sum of calibrated zones: attribute calibrated value
                    flow_rate = calibrated_flow
                elif len(active_calibrated) == 1:
                    # Single calibrated zone running alone: attribute full Flume reading
                    flow_rate = flume_flow
                else:
                    # Ambiguous overlap: can't resolve attribution
                    flow_rate = 0.0
                usage_increment = flow_rate * (interval_seconds / 60.0)
            else:
                # Uncalibrated zone running
                # Only attribute full Flume flow when no calibrated zones muddy the reading
                flow_rate = flume_flow if len(active_calibrated) == 0 else 0.0
                usage_increment = flow_rate * (interval_seconds / 60.0)

            self._daily_totals[zone_id] = self._daily_totals.get(zone_id, 0.0) + usage_increment
            result[zone_id] = ZoneData(
                flow_rate=flow_rate,
                daily_usage=self._daily_totals[zone_id],
                is_available=True,
            )

        self._store.async_delay_save(self._data_to_save, SAVE_DELAY)
        return result

    def _zone_is_on(self, entity_id: str) -> bool:
        """Return True if the zone is currently running.

        Valve domain entities use 'open'/'closed'; switch entities use 'on'/'off'.
        """
        state = self.hass.states.get(entity_id)
        if state is None:
            return False
        domain = entity_id.split(".")[0]
        if domain == "valve":
            return state.state == "open"
        return state.state in ("on", "true")

    def _data_to_save(self) -> dict:
        """Return the data dict for Store persistence."""
        return {"date": date.today().isoformat(), "zones": dict(self._daily_totals)}

    async def _midnight_reset(self, _now) -> None:
        """Reset all daily totals at midnight and refresh entities."""
        self._daily_totals = {z: 0.0 for z in self._daily_totals}
        self._store.async_delay_save(self._data_to_save, 0)
        await self.async_refresh()
