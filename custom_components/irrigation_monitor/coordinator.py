"""DataUpdateCoordinator for the Irrigation Monitor integration."""
from __future__ import annotations

import asyncio
import logging
import statistics
from dataclasses import dataclass
from datetime import date, timedelta

from homeassistant.components.persistent_notification import async_create, async_dismiss
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_ALERTS_ENABLED,
    CONF_BACKGROUND_THRESHOLD,
    CONF_CALIBRATED_FLOW,
    CONF_FLUME_ENTITY_ID,
    CONF_MONITORED_ZONES,
    CONF_POLL_INTERVAL,
    CONF_RAMP_UP_POLLS,
    CONF_SHUTOFF_ENABLED,
    CONF_THRESHOLD_MULTIPLIER,
    CONF_ZONES,
    DEFAULT_BACKGROUND_THRESHOLD,
    DEFAULT_RAMP_UP_POLLS,
    DEFAULT_THRESHOLD_MULTIPLIER,
    DOMAIN,
    SAMPLE_COUNT,
    SAMPLE_INTERVAL,
    SAVE_DELAY,
    STABILIZATION_POLL_INTERVAL,
    STABILIZATION_TIMEOUT,
    STORAGE_KEY,
    STORAGE_VERSION,
    VARIANCE_THRESHOLD,
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
        self._pending_calibrations: dict[str, float] = {}
        self._calibrating: set[str] = set()
        self._zone_was_on: dict[str, bool] = {}
        self._ramp_up_counters: dict[str, int] = {}
        self._leak_notified: set[str] = set()
        self._leak_statuses: dict[str, str] = {}
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

            # --- Leak detection (Phase 5) ---
            ramp_up_polls = self._entry.options.get(CONF_RAMP_UP_POLLS, DEFAULT_RAMP_UP_POLLS)
            was_on = self._zone_was_on.get(zone_id, False)

            # Transition detection
            if not was_on and is_on:  # OFF -> ON
                self._ramp_up_counters[zone_id] = ramp_up_polls
            elif was_on and not is_on:  # ON -> OFF
                self._leak_notified.discard(zone_id)
                if self._leak_statuses.get(zone_id) != "leak_detected":
                    self._leak_statuses[zone_id] = "idle"

            # Leak detection (only when ON, calibrated, ramp-up exhausted)
            if is_on and calibrated_flow is not None:
                ramp = self._ramp_up_counters.get(zone_id, 0)
                if ramp > 0:
                    self._ramp_up_counters[zone_id] = ramp - 1
                    self._leak_statuses[zone_id] = "running"
                else:
                    leak_threshold = zone_cfg.get(CONF_THRESHOLD_MULTIPLIER, DEFAULT_THRESHOLD_MULTIPLIER)
                    if flow_rate > calibrated_flow * leak_threshold:
                        self._leak_statuses[zone_id] = "leak_detected"
                        shutoff_enabled = zone_cfg.get(CONF_SHUTOFF_ENABLED, True)
                        if shutoff_enabled:
                            await self._turn_valve(zone_id, turn_on=False)
                        if zone_cfg.get(CONF_ALERTS_ENABLED, True) and zone_id not in self._leak_notified:
                            await self._fire_leak_notification(zone_id, flow_rate, calibrated_flow, shutoff_enabled)
                            self._leak_notified.add(zone_id)
                    else:
                        self._leak_statuses[zone_id] = "running"
            elif is_on:
                # Running but uncalibrated — skip detection silently
                self._leak_statuses[zone_id] = "running"
            elif self._leak_statuses.get(zone_id) != "leak_detected":
                self._leak_statuses[zone_id] = "idle"

            # MUST BE LAST in the per-zone loop body:
            self._zone_was_on[zone_id] = is_on

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

    async def _turn_valve(self, zone_id: str, turn_on: bool) -> None:
        """Turn a valve on or off using the correct service for its domain."""
        domain = zone_id.split(".")[0]
        if turn_on:
            service = "turn_on" if domain == "switch" else "open_valve"
        else:
            service = "turn_off" if domain == "switch" else "close_valve"
        await self.hass.services.async_call(
            domain, service, {"entity_id": zone_id}, blocking=True
        )

    async def _fire_leak_notification(
        self, zone_id: str, flow_rate: float, calibrated_flow: float, shutoff_enabled: bool
    ) -> None:
        """Fire a persistent notification for a detected leak."""
        shutoff_msg = "Valve has been shut off." if shutoff_enabled else "Valve shutoff is disabled."
        zone_slug = zone_id.replace(".", "_")
        async_create(
            self.hass,
            (
                f"Leak detected on {zone_id}. "
                f"Flow: {flow_rate:.1f} gal/min (expected: {calibrated_flow:.1f} gal/min). "
                f"{shutoff_msg}"
            ),
            title="Irrigation Monitor — Leak Alert",
            notification_id=f"leak_{zone_slug}",
        )

    def _write_calibrated_flow(self, zone_id: str, flow: float) -> None:
        """Persist calibrated flow to ConfigEntry.options using safe nested copy.

        ConfigEntry.options is a MappingProxyType. Shallow dict() copy is NOT enough
        for nested zones dict. Must copy each level before mutating.
        async_update_entry is a @callback -- do NOT await it.
        """
        existing = dict(self._entry.options)
        zones = dict(existing.get(CONF_ZONES, {}))
        zone_cfg = dict(zones.get(zone_id, {}))
        zone_cfg[CONF_CALIBRATED_FLOW] = flow
        zones[zone_id] = zone_cfg
        existing[CONF_ZONES] = zones
        self.hass.config_entries.async_update_entry(self._entry, options=existing)

    def _register_calibration_action_listener(
        self, zone_id: str, old_flow: float, new_flow: float
    ) -> None:
        """Register a one-time event listener for Save/Cancel action buttons.

        Listens for 'mobile_app_notification_action' events. Save writes new flow
        to ConfigEntry.options; Cancel discards pending value. Listener is cleaned
        up on entry unload if user never responds.
        """
        zone_slug = zone_id.replace(".", "_")
        save_action = f"irrigation_monitor_confirm_calibration_{zone_slug}"
        cancel_action = f"irrigation_monitor_cancel_calibration_{zone_slug}"

        @callback
        def _handle_action(event: Event) -> None:
            action = event.data.get("action")
            if action == save_action:
                self._write_calibrated_flow(zone_id, new_flow)
                self._pending_calibrations.pop(zone_id, None)
                async_dismiss(self.hass, f"calib_{zone_id}_confirm")
                async_create(
                    self.hass,
                    f"Zone {zone_id} calibration saved: {new_flow:.1f} gal/min",
                    title="Irrigation Monitor",
                    notification_id=f"calib_{zone_id}_saved",
                )
            elif action == cancel_action:
                self._pending_calibrations.pop(zone_id, None)
                async_dismiss(self.hass, f"calib_{zone_id}_confirm")
            else:
                return  # Not our action -- do not unsubscribe
            unsub()  # One-shot: remove listener after handling

        unsub = self.hass.bus.async_listen(
            "mobile_app_notification_action", _handle_action
        )
        # Ensure listener is cleaned up if entry is unloaded before user responds
        self._entry.async_on_unload(unsub)

    async def async_calibrate_zone(self, zone_id: str) -> None:
        """Full calibration sequence for one zone."""
        # --- Duplicate press guard ---
        if zone_id in self._calibrating:
            return
        self._calibrating.add(zone_id)

        try:
            # --- CALIB-02: Background flow check ---
            threshold = self._entry.data.get(
                CONF_BACKGROUND_THRESHOLD, DEFAULT_BACKGROUND_THRESHOLD
            )
            flume_id = self._entry.data[CONF_FLUME_ENTITY_ID]
            state = self.hass.states.get(flume_id)
            if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                async_create(
                    self.hass,
                    "Calibration failed: Flume sensor unavailable.",
                    title="Irrigation Monitor",
                    notification_id=f"calib_{zone_id}_fail",
                )
                return

            current_flow = float(state.state)
            if current_flow > threshold:
                async_create(
                    self.hass,
                    f"Background water flow detected ({current_flow:.1f} gal/min). "
                    "Stop all other water use before calibrating.",
                    title="Irrigation Monitor",
                    notification_id=f"calib_{zone_id}_background",
                )
                return

            # --- CALIB-03: Zone already running guard ---
            if self._zone_is_on(zone_id):
                async_create(
                    self.hass,
                    f"Zone {zone_id} is already running. Stop it first.",
                    title="Irrigation Monitor",
                    notification_id=f"calib_{zone_id}_running",
                )
                return

            # --- CALIB-04: Start calibration ---
            async_create(
                self.hass,
                f"Calibrating {zone_id}... please wait.",
                title="Irrigation Monitor",
                notification_id=f"calib_{zone_id}_progress",
            )

            try:
                await self._turn_valve(zone_id, turn_on=True)

                # Variance detection loop (max STABILIZATION_TIMEOUT, poll every STABILIZATION_POLL_INTERVAL)
                readings: list[float] = []
                elapsed = 0
                stable = False
                while elapsed < STABILIZATION_TIMEOUT:
                    await asyncio.sleep(STABILIZATION_POLL_INTERVAL)
                    elapsed += STABILIZATION_POLL_INTERVAL
                    s = self.hass.states.get(flume_id)
                    if s is None or s.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                        raise RuntimeError("Flume went unavailable during calibration")
                    readings.append(float(s.state))
                    if len(readings) >= 3:
                        if statistics.stdev(readings[-3:]) < VARIANCE_THRESHOLD:
                            stable = True
                            break

                if not stable:
                    raise RuntimeError("Flow did not stabilize within 60 seconds")

                # Sample SAMPLE_COUNT readings over SAMPLE_COUNT * SAMPLE_INTERVAL seconds
                samples: list[float] = []
                for _ in range(SAMPLE_COUNT):
                    await asyncio.sleep(SAMPLE_INTERVAL)
                    s = self.hass.states.get(flume_id)
                    if s is None or s.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                        raise RuntimeError("Flume went unavailable during sampling")
                    samples.append(float(s.state))
                new_flow = sum(samples) / len(samples)

                # --- CALIB-05: Persist or pending ---
                zones_cfg = self._entry.options.get(CONF_ZONES, {})
                old_flow = zones_cfg.get(zone_id, {}).get(CONF_CALIBRATED_FLOW)

                if old_flow is not None:
                    # Re-calibration: store pending, fire action notification
                    self._pending_calibrations[zone_id] = new_flow
                    self._register_calibration_action_listener(zone_id, old_flow, new_flow)
                    async_dismiss(self.hass, f"calib_{zone_id}_progress")
                    zone_slug = zone_id.replace(".", "_")
                    await self.hass.services.async_call(
                        "persistent_notification",
                        "create",
                        {
                            "message": (
                                f"Zone {zone_id} recalibration complete.\n"
                                f"Old: {old_flow:.1f} gal/min -> New: {new_flow:.1f} gal/min.\n"
                                "Save or Cancel?"
                            ),
                            "title": "Irrigation Monitor",
                            "notification_id": f"calib_{zone_id}_confirm",
                            "actions": [
                                {
                                    "action": f"irrigation_monitor_confirm_calibration_{zone_slug}",
                                    "title": "Save",
                                },
                                {
                                    "action": f"irrigation_monitor_cancel_calibration_{zone_slug}",
                                    "title": "Cancel",
                                },
                            ],
                        },
                    )
                else:
                    # --- First calibration: write immediately ---
                    self._write_calibrated_flow(zone_id, new_flow)
                    async_dismiss(self.hass, f"calib_{zone_id}_progress")
                    async_create(
                        self.hass,
                        f"Zone {zone_id} calibrated: {new_flow:.1f} gal/min",
                        title="Irrigation Monitor",
                        notification_id=f"calib_{zone_id}_success",
                    )

            except Exception as err:
                async_dismiss(self.hass, f"calib_{zone_id}_progress")
                async_create(
                    self.hass,
                    f"Calibration failed for {zone_id}: {err}",
                    title="Irrigation Monitor",
                    notification_id=f"calib_{zone_id}_fail",
                )
                _LOGGER.exception("Calibration error for %s", zone_id)
            finally:
                # --- CALIB-06: Always turn valve off ---
                await self._turn_valve(zone_id, turn_on=False)

        finally:
            self._calibrating.discard(zone_id)
