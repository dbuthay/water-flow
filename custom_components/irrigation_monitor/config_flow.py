"""Config flow for Irrigation Monitor."""
from __future__ import annotations

from typing import Any

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import (
    BooleanSelector,
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
    """Handle options flow for Irrigation Monitor."""

    def __init__(self) -> None:
        """Initialize the options flow."""
        self._new_zone_ids: list[str] = []
        self._zone_iterator: list[str] = []
        self._zone_settings: dict[str, dict[str, Any]] = {}
        self._new_flume_entity_id: str = ""
        self._new_poll_interval: int = DEFAULT_POLL_INTERVAL

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 1: Change Flume sensor, valve list, and poll interval."""
        if user_input is not None:
            self._new_flume_entity_id = user_input[CONF_FLUME_ENTITY_ID]
            self._new_poll_interval = user_input[CONF_POLL_INTERVAL]
            self._new_zone_ids = user_input[CONF_MONITORED_ZONES]
            self._zone_settings = {}
            self._zone_iterator = list(self._new_zone_ids)
            return await self.async_step_zones()

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

    async def async_step_zones(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 2: Per-zone settings — iterates one zone at a time."""
        if user_input is not None and self._zone_iterator:
            # Store settings for the zone we just configured
            current_zone = self._zone_iterator[0]
            self._zone_settings[current_zone] = {
                CONF_SHUTOFF_ENABLED: user_input[CONF_SHUTOFF_ENABLED],
                CONF_ALERTS_ENABLED: user_input[CONF_ALERTS_ENABLED],
                CONF_THRESHOLD_MULTIPLIER: user_input[CONF_THRESHOLD_MULTIPLIER],
            }
            self._zone_iterator.pop(0)

        if not self._zone_iterator:
            # All zones configured — apply CRITICAL merge pattern
            existing = dict(self.config_entry.options)
            old_zones = existing.get(CONF_ZONES, {})
            updated_zones: dict[str, dict[str, Any]] = {}

            for zone_id in self._new_zone_ids:
                if zone_id in self._zone_settings:
                    # User provided new settings for this zone — merge with existing
                    if zone_id in old_zones:
                        base = dict(old_zones[zone_id])
                    else:
                        # New zone: start with defaults (ensures calibrated_flow=None)
                        base = {
                            CONF_SHUTOFF_ENABLED: DEFAULT_SHUTOFF_ENABLED,
                            CONF_ALERTS_ENABLED: DEFAULT_ALERTS_ENABLED,
                            CONF_CALIBRATED_FLOW: None,
                            CONF_THRESHOLD_MULTIPLIER: DEFAULT_THRESHOLD_MULTIPLIER,
                        }
                    base.update(self._zone_settings[zone_id])
                    updated_zones[zone_id] = base
                elif zone_id in old_zones:
                    # Existing zone not re-configured — preserve entirely (incl. calibrated_flow)
                    updated_zones[zone_id] = old_zones[zone_id]
                else:
                    # Brand new zone — apply defaults
                    updated_zones[zone_id] = {
                        CONF_SHUTOFF_ENABLED: DEFAULT_SHUTOFF_ENABLED,
                        CONF_ALERTS_ENABLED: DEFAULT_ALERTS_ENABLED,
                        CONF_CALIBRATED_FLOW: None,
                        CONF_THRESHOLD_MULTIPLIER: DEFAULT_THRESHOLD_MULTIPLIER,
                    }

            existing[CONF_ZONES] = updated_zones

            # Update ConfigEntry.data with new flume/valves/poll settings
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data={
                    CONF_FLUME_ENTITY_ID: self._new_flume_entity_id,
                    CONF_MONITORED_ZONES: self._new_zone_ids,
                    CONF_POLL_INTERVAL: self._new_poll_interval,
                },
            )

            return self.async_create_entry(data=existing)

        # Show form for next zone in iterator
        zone_id = self._zone_iterator[0]
        existing_zone = self.config_entry.options.get(CONF_ZONES, {}).get(zone_id, {})

        # Resolve friendly name for the title placeholder (falls back to entity_id)
        registry = er.async_get(self.hass)
        reg_entry = registry.async_get(zone_id)
        zone_name = (reg_entry.name or reg_entry.original_name or zone_id) if reg_entry else zone_id

        return self.async_show_form(
            step_id="zones",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SHUTOFF_ENABLED,
                        default=existing_zone.get(CONF_SHUTOFF_ENABLED, DEFAULT_SHUTOFF_ENABLED),
                    ): BooleanSelector(),
                    vol.Required(
                        CONF_ALERTS_ENABLED,
                        default=existing_zone.get(CONF_ALERTS_ENABLED, DEFAULT_ALERTS_ENABLED),
                    ): BooleanSelector(),
                    vol.Required(
                        CONF_THRESHOLD_MULTIPLIER,
                        default=existing_zone.get(
                            CONF_THRESHOLD_MULTIPLIER, DEFAULT_THRESHOLD_MULTIPLIER
                        ),
                    ): NumberSelector(
                        NumberSelectorConfig(min=1.0, max=5.0, step=0.1)
                    ),
                }
            ),
            description_placeholders={"zone_name": zone_name},
        )
