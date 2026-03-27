"""Config flow for openHASP Manager."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    TextSelector,
    TextSelectorConfig,
)

from .const import DOMAIN, CONF_PLATE_TOPIC, CONF_BUTTON_MAPPINGS, DEFAULT_TOPIC_PREFIX

_LOGGER = logging.getLogger(__name__)


class OpenHASPManagerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for openHASP Manager."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle initial setup step - enter the plate MQTT topic."""
        errors = {}

        if user_input is not None:
            topic = user_input.get(CONF_PLATE_TOPIC, DEFAULT_TOPIC_PREFIX)
            # Extract plate name for the title
            plate_name = topic.split("/")[-1] if "/" in topic else topic

            await self.async_set_unique_id(topic)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"openHASP: {plate_name}",
                data={CONF_PLATE_TOPIC: topic},
                options={CONF_BUTTON_MAPPINGS: {}},
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_PLATE_TOPIC, default=DEFAULT_TOPIC_PREFIX
                    ): TextSelector(TextSelectorConfig(type="text")),
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return OpenHASPManagerOptionsFlow(config_entry)


class OpenHASPManagerOptionsFlow(OptionsFlow):
    """Handle options flow - map buttons to entities."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show form to map discovered buttons to HA entities."""
        if user_input is not None:
            # Save the mappings
            mappings = {}
            for key, value in user_input.items():
                if not value:
                    continue
                
                # Try to extract ID from "Friendly Name (p1b2)"
                import re
                match = re.search(r"\(p(\d+)b(\d+)\)$", key)
                if match:
                    btn_id = f"p{match.group(1)}b{match.group(2)}"
                    mappings[btn_id] = value
                # Fallback for manual Page X, Button Y labels
                elif "Page " in key and "Button " in key:
                    match = re.search(r"Page (\d+), Button (\d+)", key)
                    if match:
                        btn_id = f"p{match.group(1)}b{match.group(2)}"
                        mappings[btn_id] = value
                # Legacy support for internal btn_p1b1 format
                elif key.startswith("btn_"):
                    btn_id = key[4:]
                    mappings[btn_id] = value
                # Direct ID support or match
                elif re.match(r"p\d+b\d+", key):
                    mappings[key] = value

            return self.async_create_entry(
                title="",
                data={CONF_BUTTON_MAPPINGS: mappings},
            )

        # Get discovered buttons from the manager
        manager = self.hass.data.get(DOMAIN, {}).get(self._config_entry.entry_id)
        current_mappings = dict(
            self._config_entry.options.get(CONF_BUTTON_MAPPINGS, {})
        )

        # Combine discovered buttons with any previously mapped buttons
        all_buttons: dict[str, str] = {}  # {btn_id: label}
        if manager:
            all_buttons.update(manager.discovered_buttons)
        for btn_id in current_mappings:
            if btn_id not in all_buttons:
                all_buttons[btn_id] = ""

        if not all_buttons:
            return self.async_show_form(
                step_id="init",
                data_schema=vol.Schema({}),
                description_placeholders={
                    "message": "No buttons discovered yet. Press some buttons on your panel first, then come back here."
                },
            )

        # Sort buttons naturally (p1b1, p1b2, ..., p1b13, p2b1, ...)
        def sort_key(btn_id: str):
            import re
            match = re.match(r"p(\d+)b(\d+)", btn_id)
            if match:
                return (int(match.group(1)), int(match.group(2)))
            return (999, 999)

        sorted_buttons = sorted(all_buttons.keys(), key=sort_key)

        # Build schema with one entity selector per button
        schema_dict = {}
        for btn_id in sorted_buttons:
            # Create a friendly label using the button's actual text
            # We put the ID in brackets so we can easily parse it back on save
            btn_label = all_buttons.get(btn_id, "")
            if btn_label:
                display_label = f"{btn_label} ({btn_id})"
            else:
                import re
                match = re.match(r"p(\d+)b(\d+)", btn_id)
                if match:
                    display_label = f"Page {match.group(1)}, Button {match.group(2)}"
                else:
                    display_label = btn_id

            current_value = current_mappings.get(btn_id, "")

            # We use the friendly label as the vol.Optional key directly
            # Home Assistant will display this string as the field name
            schema_dict[
                vol.Optional(display_label, default=current_value)
            ] = EntitySelector(
                EntitySelectorConfig(
                    domain=["light", "switch", "fan", "input_boolean", "script", "scene"]
                )
            )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_dict),
            description_placeholders={
                "message": "Assign Home Assistant entities to your panel buttons below."
            },
        )
