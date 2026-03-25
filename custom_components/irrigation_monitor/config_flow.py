"""Config flow for Irrigation Monitor."""
from __future__ import annotations

from typing import Any

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    EntityFilterSelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    SelectOptionDict,
)
import voluptuous as vol

from .const import (
    CONF_ALERTS_ENABLED,
    CONF_CALIBRATED_FLOW,
    CONF_FLUME_ENTITY_ID,
    CONF_MONITORED_ZONES,
    CONF_POLL_INTERVAL,
    CONF_SHUTOFF_ENABLED,
    CONF_THRESHOLD_MULTIPLIER,
    CONF_ZONES,
    DEFAULT_ALERTS_ENABLED,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_SHUTOFF_ENABLED,
    DEFAULT_THRESHOLD_MULTIPLIER,
    DOMAIN,
    VALVE_DOMAINS,
)


class IrrigationMonitorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle config flow for Irrigation Monitor."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._flume_entity_id: str = ""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 1: Pick the Flume sensor entity."""
        if user_input is not None:
            self._flume_entity_id = user_input[CONF_FLUME_ENTITY_ID]
            return await self.async_step_valves()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_FLUME_ENTITY_ID): EntitySelector(
                        EntitySelectorConfig(
                            filter=EntityFilterSelectorConfig(
                                integration="flume",
                            )
                        )
                    ),
                }
            ),
        )

    async def async_step_valves(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 2: Pick irrigation valves to monitor."""
        if user_input is not None:
            selected_zones = user_input[CONF_MONITORED_ZONES]
            options_zones = {
                entity_id: {
                    CONF_SHUTOFF_ENABLED: DEFAULT_SHUTOFF_ENABLED,
                    CONF_ALERTS_ENABLED: DEFAULT_ALERTS_ENABLED,
                    CONF_CALIBRATED_FLOW: None,
                    CONF_THRESHOLD_MULTIPLIER: DEFAULT_THRESHOLD_MULTIPLIER,
                }
                for entity_id in selected_zones
            }
            return self.async_create_entry(
                title="Irrigation Monitor",
                data={
                    CONF_FLUME_ENTITY_ID: self._flume_entity_id,
                    CONF_MONITORED_ZONES: selected_zones,
                    CONF_POLL_INTERVAL: DEFAULT_POLL_INTERVAL,
                },
                options={CONF_ZONES: options_zones},
            )

        valve_candidates = self._discover_valve_entities()
        options = [
            SelectOptionDict(value=eid, label=f"{name} ({eid})")
            for eid, name in valve_candidates
        ]

        return self.async_show_form(
            step_id="valves",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MONITORED_ZONES): SelectSelector(
                        SelectSelectorConfig(options=options, multiple=True)
                    ),
                }
            ),
        )

    def _discover_valve_entities(self) -> list[tuple[str, str]]:
        """Return sorted list of (entity_id, friendly_name) valve candidates."""
        registry = er.async_get(self.hass)
        candidates = []
        for entry in registry.entities.values():
            if entry.domain not in VALVE_DOMAINS:
                continue
            name = entry.name or entry.original_name or entry.entity_id
            candidates.append((entry.entity_id, name))
        return sorted(candidates, key=lambda x: x[1])

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "IrrigationMonitorOptionsFlowHandler":
        """Get the options flow handler."""
        return IrrigationMonitorOptionsFlowHandler()


class IrrigationMonitorOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Irrigation Monitor.

    Only manages Flume sensor, monitored valve list, and poll interval.
    Per-zone settings (shutoff, alerts, threshold) are configured directly
    on each zone's device page via switch and number entities.
    """

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Update Flume sensor, valve list, and poll interval."""
        if user_input is not None:
            new_zones = user_input[CONF_MONITORED_ZONES]

            # CRITICAL merge: preserve all existing zone data (calibrated_flow,
            # shutoff/alerts toggles, threshold) for zones that remain monitored.
            # New zones get defaults. Removed zones are dropped (clearing their data).
            existing = dict(self.config_entry.options)
            old_zones = existing.get(CONF_ZONES, {})
            updated_zones: dict[str, dict[str, Any]] = {}
            for zone_id in new_zones:
                if zone_id in old_zones:
                    updated_zones[zone_id] = old_zones[zone_id]
                else:
                    updated_zones[zone_id] = {
                        CONF_SHUTOFF_ENABLED: DEFAULT_SHUTOFF_ENABLED,
                        CONF_ALERTS_ENABLED: DEFAULT_ALERTS_ENABLED,
                        CONF_CALIBRATED_FLOW: None,
                        CONF_THRESHOLD_MULTIPLIER: DEFAULT_THRESHOLD_MULTIPLIER,
                    }
            existing[CONF_ZONES] = updated_zones

            # Update ConfigEntry.data (flume entity, valve list, poll interval)
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data={
                    CONF_FLUME_ENTITY_ID: user_input[CONF_FLUME_ENTITY_ID],
                    CONF_MONITORED_ZONES: new_zones,
                    CONF_POLL_INTERVAL: user_input[CONF_POLL_INTERVAL],
                },
            )
            return self.async_create_entry(data=existing)

        valve_candidates = self._discover_valve_entities()
        valve_options = [
            SelectOptionDict(value=eid, label=f"{name} ({eid})")
            for eid, name in valve_candidates
        ]
        current_data = self.config_entry.data

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_FLUME_ENTITY_ID,
                        default=current_data.get(CONF_FLUME_ENTITY_ID),
                    ): EntitySelector(
                        EntitySelectorConfig(
                            filter=EntityFilterSelectorConfig(
                                integration="flume",
                            )
                        )
                    ),
                    vol.Required(
                        CONF_MONITORED_ZONES,
                        default=current_data.get(CONF_MONITORED_ZONES, []),
                    ): SelectSelector(
                        SelectSelectorConfig(options=valve_options, multiple=True)
                    ),
                    vol.Optional(
                        CONF_POLL_INTERVAL,
                        default=current_data.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
                    ): NumberSelector(
                        NumberSelectorConfig(min=10, max=300, step=5, unit_of_measurement="s")
                    ),
                }
            ),
        )

    def _discover_valve_entities(self) -> list[tuple[str, str]]:
        """Return sorted list of (entity_id, friendly_name) valve candidates."""
        registry = er.async_get(self.hass)
        candidates = []
        for entry in registry.entities.values():
            if entry.domain not in VALVE_DOMAINS:
                continue
            name = entry.name or entry.original_name or entry.entity_id
            candidates.append((entry.entity_id, name))
        return sorted(candidates, key=lambda x: x[1])
