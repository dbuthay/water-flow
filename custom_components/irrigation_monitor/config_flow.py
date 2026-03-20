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
    """Handle options flow — implemented in Plan 02."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Placeholder — Plan 02 implements full options flow."""
        return self.async_create_entry(data=self.config_entry.options)
