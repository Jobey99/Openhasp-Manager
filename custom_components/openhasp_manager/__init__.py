"""openHASP Manager - Auto-discover and control openHASP buttons."""
from __future__ import annotations

import json
import logging
import re

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, CONF_PLATE_TOPIC, CONF_BUTTON_MAPPINGS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up openHASP Manager from a config entry."""
    topic_prefix = entry.data.get(CONF_PLATE_TOPIC, "hasp/plate")
    mappings = dict(entry.options.get(CONF_BUTTON_MAPPINGS, {}))

    # Register static path for the designer
    import os
    static_dir = os.path.join(os.path.dirname(__file__), "www")
    
    if os.path.exists(static_dir):
        hass.http.register_static_path(
            "/openhasp_manager",
            static_dir,
            cache_headers=False,
        )
    else:
        _LOGGER.warning("Designer UI directory not found at %s", static_dir)

    manager = OpenHASPManager(hass, entry, topic_prefix, mappings)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = manager

    await manager.async_start()

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update - reload mappings without full restart."""
    manager: OpenHASPManager = hass.data[DOMAIN][entry.entry_id]
    new_mappings = dict(entry.options.get(CONF_BUTTON_MAPPINGS, {}))
    await manager.async_update_mappings(new_mappings)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    manager: OpenHASPManager = hass.data[DOMAIN].pop(entry.entry_id, None)
    if manager:
        await manager.async_stop()
    return True


class OpenHASPManager:
    """Manages MQTT communication with an openHASP plate."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        topic_prefix: str,
        mappings: dict[str, str],
    ) -> None:
        self.hass = hass
        self.entry = entry
        self.topic_prefix = topic_prefix  # e.g. "hasp/plate"
        self.mappings = mappings  # {"p1b2": "light.living_room", ...}
        self.discovered_buttons: dict[str, str] = {}  # {"p1b2": "Living Room Lamp", ...}
        self._unsub_mqtt: list = []
        self._unsub_state: list = []

    async def async_start(self) -> None:
        """Subscribe to MQTT and start listening for button events."""
        # Subscribe to all state messages from this plate
        state_topic = f"{self.topic_prefix}/state/+"
        self._unsub_mqtt.append(
            await mqtt.async_subscribe(
                self.hass, state_topic, self._handle_state_message
            )
        )

        # Subscribe to LWT (online/offline status)
        lwt_topic = f"{self.topic_prefix}/LWT"
        self._unsub_mqtt.append(
            await mqtt.async_subscribe(
                self.hass, lwt_topic, self._handle_lwt_message
            )
        )

        # Set up state listeners for all currently mapped entities
        self._setup_state_listeners()

        _LOGGER.info(
            "openHASP Manager started for %s with %d mappings",
            self.topic_prefix,
            len(self.mappings),
        )

    async def async_stop(self) -> None:
        """Unsubscribe from MQTT and clean up."""
        for unsub in self._unsub_mqtt:
            unsub()
        self._unsub_mqtt.clear()
        for unsub in self._unsub_state:
            unsub()
        self._unsub_state.clear()

    async def async_update_mappings(self, new_mappings: dict[str, str]) -> None:
        """Update button-to-entity mappings and refresh state listeners."""
        self.mappings = new_mappings
        # Clear old state listeners
        for unsub in self._unsub_state:
            unsub()
        self._unsub_state.clear()
        # Re-setup
        self._setup_state_listeners()
        # Sync all button states immediately
        await self._sync_all_button_states()

    @callback
    def _handle_state_message(self, msg) -> None:
        """Handle incoming button state MQTT messages."""
        # Topic format: hasp/plate/state/p1b2
        topic_parts = msg.topic.split("/")
        if len(topic_parts) < 4:
            return

        obj_id = topic_parts[-1]  # e.g. "p1b2"

        # Only track button objects (pXbY pattern)
        if not re.match(r"p\d+b\d+", obj_id):
            return

        # Parse the payload
        try:
            payload = json.loads(msg.payload)
        except (json.JSONDecodeError, TypeError):
            return

        # Check if this is a text response (from our query)
        if "text" in payload and "event" not in payload:
            raw_text = payload["text"]
            # Strip the icon character (unicode private use area) and clean up
            clean_label = ""
            for char in raw_text:
                if ord(char) >= 0xE000:
                    continue  # Skip MDI icon characters
                clean_label += char
            clean_label = clean_label.strip().replace("\n", " ")
            if clean_label:
                self.discovered_buttons[obj_id] = clean_label
                _LOGGER.info("Got label for %s: %s", obj_id, clean_label)
            return

        # Register newly discovered buttons
        if obj_id not in self.discovered_buttons:
            self.discovered_buttons[obj_id] = ""  # Placeholder until we get the text
            _LOGGER.info("Discovered openHASP button: %s", obj_id)
            # Query the button's text label from the panel
            query_topic = f"{self.topic_prefix}/command"
            self.hass.async_create_task(
                mqtt.async_publish(self.hass, query_topic, f"{obj_id}.text")
            )
            # Fire an event so the UI can update
            self.hass.bus.async_fire(
                f"{DOMAIN}_button_discovered",
                {"plate": self.topic_prefix, "button": obj_id},
            )

        event = payload.get("event")
        if event != "up":
            return  # Only act on button release

        # Check if this button has a mapped entity
        target_entity = self.mappings.get(obj_id)
        if not target_entity:
            _LOGGER.debug("Button %s pressed but no entity mapped", obj_id)
            return

        _LOGGER.info("Button %s pressed → toggling %s", obj_id, target_entity)

        # Toggle the mapped entity
        domain = target_entity.split(".")[0]
        if domain in ("light", "switch", "fan", "input_boolean"):
            self.hass.async_create_task(
                self.hass.services.async_call(
                    "homeassistant",
                    "toggle",
                    {"entity_id": target_entity},
                )
            )
        elif domain == "script":
            self.hass.async_create_task(
                self.hass.services.async_call(
                    "script", "turn_on", {"entity_id": target_entity}
                )
            )
        elif domain == "scene":
            self.hass.async_create_task(
                self.hass.services.async_call(
                    "scene", "turn_on", {"entity_id": target_entity}
                )
            )

    @callback
    def _handle_lwt_message(self, msg) -> None:
        """Handle plate online/offline status."""
        if msg.payload.lower() == "online":
            _LOGGER.info("Plate %s came online, syncing states", self.topic_prefix)
            self.hass.async_create_task(self._sync_all_button_states())

    def _setup_state_listeners(self) -> None:
        """Listen for HA entity state changes to update button visuals."""
        from homeassistant.helpers.event import async_track_state_change_event

        entity_ids = [eid for eid in self.mappings.values() if eid]
        if not entity_ids:
            return

        @callback
        def _state_changed(event) -> None:
            """When a mapped HA entity changes, update the button on the panel."""
            entity_id = event.data.get("entity_id")
            new_state = event.data.get("new_state")
            if new_state is None:
                return

            # Find which button(s) map to this entity
            for btn_id, mapped_entity in self.mappings.items():
                if mapped_entity == entity_id:
                    val = 1 if new_state.state == "on" else 0
                    topic = f"{self.topic_prefix}/command/{btn_id}.val"
                    self.hass.async_create_task(
                        mqtt.async_publish(self.hass, topic, str(val))
                    )

        self._unsub_state.append(
            async_track_state_change_event(self.hass, entity_ids, _state_changed)
        )

    async def _sync_all_button_states(self) -> None:
        """Push current state of all mapped entities to the panel buttons."""
        for btn_id, entity_id in self.mappings.items():
            if not entity_id:
                continue
            state = self.hass.states.get(entity_id)
            if state:
                val = 1 if state.state == "on" else 0
                topic = f"{self.topic_prefix}/command/{btn_id}.val"
                await mqtt.async_publish(self.hass, topic, str(val))
