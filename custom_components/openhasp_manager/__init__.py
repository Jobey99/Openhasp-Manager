"""openHASP Manager - Auto-discover and control openHASP buttons."""
from __future__ import annotations

import json
import logging
import re

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er, network

from .const import DOMAIN, CONF_PLATE_TOPIC, CONF_BUTTON_MAPPINGS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up openHASP Manager from a config entry."""
    topic_prefix = entry.data.get(CONF_PLATE_TOPIC, "hasp/plate")
    mappings = dict(entry.options.get(CONF_BUTTON_MAPPINGS, {}))

    manager = OpenHASPManager(hass, entry, topic_prefix, mappings)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = manager

    await manager.async_start()

    # Forward entry setups to platforms
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    # Register popup service
    if not hass.services.has_service(DOMAIN, "push_popup"):
        async def handle_push_popup(call) -> None:
            text = call.data.get("text", "")
            duration = call.data.get("duration", 10)
            buttons = call.data.get("buttons", ["OK"])
            
            for mgr in hass.data[DOMAIN].values():
                await mgr.async_push_popup(text, duration, buttons)

        hass.services.async_register(DOMAIN, "push_popup", handle_push_popup)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update - reload mappings without full restart."""
    manager: OpenHASPManager = hass.data[DOMAIN][entry.entry_id]
    new_mappings = dict(entry.options.get(CONF_BUTTON_MAPPINGS, {}))
    await manager.async_update_mappings(new_mappings)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    manager: OpenHASPManager = hass.data[DOMAIN].pop(entry.entry_id, None)
    if manager:
        await manager.async_stop()
    return unload_ok


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
        self.current_page = 1

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

        from datetime import timedelta
        from homeassistant.helpers.event import async_track_time_interval
        self._unsub_mqtt.append(
            async_track_time_interval(
                self.hass, self._handle_camera_update_timer, timedelta(seconds=5)
            )
        )

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

        obj_id = topic_parts[-1]  # e.g. "p1b2", "page" or "statusupdate"

        if obj_id == "page":
            try:
                self.current_page = int(msg.payload)
                _LOGGER.info("Plate %s is now on page %d", self.topic_prefix, self.current_page)
            except (ValueError, TypeError):
                pass
            return

        if obj_id == "statusupdate":
            try:
                payload = json.loads(msg.payload)
                rssi = payload.get("rssi")
                if rssi is not None:
                    icon = "E640"  # wifi-outline
                    if rssi >= -50:
                        icon = "E63E"
                    elif rssi >= -60:
                        icon = "E63D"
                    elif rssi >= -70:
                        icon = "E63C"
                    elif rssi >= -80:
                        icon = "E63B"
                    
                    pct = min(100, max(0, 2 * (rssi + 100)))
                    wifi_text = f"\\u{icon} {pct}%"
                    self.hass.async_create_task(
                        mqtt.async_publish(self.hass, f"{self.topic_prefix}/command/p0b11.text", wifi_text)
                    )
            except Exception:
                pass
            return

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
        val = payload.get("val")
        color = payload.get("color")

        # Check if this button has a mapped entity
        target_entity = self.mappings.get(obj_id)
        if not target_entity:
            return

        domain = target_entity.split(".")[0]

        # Handle Dropdown changes (val = index)
        if val is not None and event == "changed" and domain == "input_select":
            state = self.hass.states.get(target_entity)
            if state:
                options = state.attributes.get("options", [])
                try:
                    selected_opt = options[int(val)]
                    self.hass.async_create_task(
                        self.hass.services.async_call("input_select", "select_option", {"entity_id": target_entity, "option": selected_opt})
                    )
                except (IndexError, ValueError):
                    pass
            return
            
        # Handle RGB color wheel changes
        if color is not None and domain == "light":
            if isinstance(color, str) and color.startswith("#"):
                r = int(color[1:3], 16)
                g = int(color[3:5], 16)
                b = int(color[5:7], 16)
                self.hass.async_create_task(
                    self.hass.services.async_call("light", "turn_on", {"entity_id": target_entity, "rgb_color": [r, g, b]})
                )
            return

        # Handle value/slider changes (Brightness, Fan Speed, Volume, Thermostat)
        if val is not None and (event == "changed" or event == "up"):
            if domain == "climate":
                self.hass.async_create_task(self.hass.services.async_call("climate", "set_temperature", {"entity_id": target_entity, "temperature": float(val)}))
                return
            elif domain == "light":
                self.hass.async_create_task(self.hass.services.async_call("light", "turn_on", {"entity_id": target_entity, "brightness_pct": min(100, int(val))}))
                return
            elif domain == "fan":
                self.hass.async_create_task(self.hass.services.async_call("fan", "set_percentage", {"entity_id": target_entity, "percentage": min(100, int(val))}))
                return
            elif domain == "media_player":
                self.hass.async_create_task(self.hass.services.async_call("media_player", "volume_set", {"entity_id": target_entity, "volume_level": float(val)/100.0}))
                return

        if event != "up":
            return  # Only act on button release for toggles/actions

        _LOGGER.info("Button %s pressed (event: %s) → action on %s", obj_id, event, target_entity)

        # Handle Climate Setpoint Buttons (+ / -)
        if domain == "climate":
            btn_text = self.discovered_buttons.get(obj_id, "").lower()
            state = self.hass.states.get(target_entity)
            if state and ("+" in btn_text or "up" in btn_text or "inc" in btn_text):
                new_temp = float(state.attributes.get("temperature", 20)) + 0.5
                self.hass.async_create_task(self.hass.services.async_call("climate", "set_temperature", {"entity_id": target_entity, "temperature": new_temp}))
            elif state and ("-" in btn_text or "down" in btn_text or "dec" in btn_text):
                new_temp = float(state.attributes.get("temperature", 20)) - 0.5
                self.hass.async_create_task(self.hass.services.async_call("climate", "set_temperature", {"entity_id": target_entity, "temperature": new_temp}))
            return

        # Handle Media Player Toggle Buttons (play/pause/next)
        if domain == "media_player":
            btn_text = self.discovered_buttons.get(obj_id, "").lower()
            if "play" in btn_text or "pause" in btn_text:
                self.hass.async_create_task(self.hass.services.async_call("media_player", "media_play_pause", {"entity_id": target_entity}))
            elif "next" in btn_text:
                self.hass.async_create_task(self.hass.services.async_call("media_player", "media_next_track", {"entity_id": target_entity}))
            elif "prev" in btn_text or "back" in btn_text:
                self.hass.async_create_task(self.hass.services.async_call("media_player", "media_previous_track", {"entity_id": target_entity}))
            return

        # Toggle the mapped entity
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
            """When a mapped HA entity changes, update the panel."""
            entity_id = event.data.get("entity_id")
            new_state = event.data.get("new_state")
            if new_state is None:
                return

            # Find buttons/objects that map to this entity
            for obj_id, mapped_entity in self.mappings.items():
                if mapped_entity == entity_id:
                    self.hass.async_create_task(self._update_obj_from_state(obj_id, new_state))

        self._unsub_state.append(
            async_track_state_change_event(self.hass, entity_ids, _state_changed)
        )

    async def _update_obj_from_state(self, obj_id, state) -> None:
        """Intelligently update a panel object based on HA state and object type."""
        domain = state.entity_id.split(".")[0]
        
        # Determine the target property (val for gauges/sliders, text for labels, etc)
        # We don't know the exact object type here without querying, 
        # so we rely on the HA domain and common conventions.
        
        if domain in ("light", "switch", "fan", "input_boolean", "media_player"):
            val = 1 if state.state in ("on", "playing") else 0
            await mqtt.async_publish(self.hass, f"{self.topic_prefix}/command/{obj_id}.val", str(val))
            
            # Update specific slider values if the state is on
            if state.state in ("on", "playing"):
                if domain == "light" and "brightness" in state.attributes:
                    pct = round(state.attributes["brightness"] / 2.55)
                    await mqtt.async_publish(self.hass, f"{self.topic_prefix}/command/{obj_id}.val", str(pct))
                elif domain == "fan" and "percentage" in state.attributes:
                    await mqtt.async_publish(self.hass, f"{self.topic_prefix}/command/{obj_id}.val", str(state.attributes["percentage"]))
                elif domain == "media_player" and "volume_level" in state.attributes:
                    pct = round(state.attributes["volume_level"] * 100)
                    await mqtt.async_publish(self.hass, f"{self.topic_prefix}/command/{obj_id}.val", str(pct))
                
                # RGB Color picker sync
                if domain == "light" and "rgb_color" in state.attributes:
                    rgb = state.attributes["rgb_color"]
                    hex_color = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
                    await mqtt.async_publish(self.hass, f"{self.topic_prefix}/command/{obj_id}.color", hex_color)
        
        elif domain == "input_select":
            opts = state.attributes.get("options", [])
            try:
                idx = opts.index(state.state)
                await mqtt.async_publish(self.hass, f"{self.topic_prefix}/command/{obj_id}.val", str(idx))
            except ValueError:
                pass
            
            # Push options list string to dropdown
            opt_str = "\\n".join(opts) # Use explicit \n literal over MQTT
            await mqtt.async_publish(self.hass, f"{self.topic_prefix}/command/{obj_id}.options", opt_str)

        elif domain == "sensor":
            # For sensors, try to send to .val (if gauge) AND .text (if label)
            # openHASP ignores commands for properties that don't exist, so this is safe.
            try:
                val = float(state.state)
                await mqtt.async_publish(self.hass, f"{self.topic_prefix}/command/{obj_id}.val", str(val))
            except (ValueError, TypeError):
                pass
            
            unit = state.attributes.get("unit_of_measurement", "")
            text = f"{state.state}{unit}"
            await mqtt.async_publish(self.hass, f"{self.topic_prefix}/command/{obj_id}.text", text)

        elif domain == "climate":
            # If it's a label, show current temp. If it's a button/val, show target.
            curr_temp = state.attributes.get("current_temperature")
            target_temp = state.attributes.get("temperature")
            
            if curr_temp is not None:
                await mqtt.async_publish(self.hass, f"{self.topic_prefix}/command/{obj_id}.text", f"{curr_temp}°")
            if target_temp is not None:
                await mqtt.async_publish(self.hass, f"{self.topic_prefix}/command/{obj_id}.val", str(target_temp))

        elif domain == "camera":
            entity_picture = state.attributes.get("entity_picture")
            if entity_picture:
                try:
                    base_url = network.get_url(self.hass, allow_internal=True)
                except Exception:
                    base_url = ""
                if base_url:
                    import time
                    timestamp = int(time.time())
                    full_url = f"{base_url}{entity_picture}&t={timestamp}"
                    await mqtt.async_publish(self.hass, f"{self.topic_prefix}/command/{obj_id}.src", full_url)

    @callback
    def _handle_camera_update_timer(self, now) -> None:
        """Periodic callback to update cameras."""
        self.hass.async_create_task(self._async_update_cameras())

    async def _async_update_cameras(self) -> None:
        """Periodically update camera snapshots on the panel."""
        # Update clock on Status Bar preset (Page 0, ID 12)
        try:
            import datetime
            now_time = datetime.datetime.now().strftime("%I:%M %p")
            if now_time.startswith("0"):
                now_time = now_time[1:]
            await mqtt.async_publish(self.hass, f"{self.topic_prefix}/command/p0b12.text", now_time)
        except Exception:
            pass

        for obj_id, target_entity in self.mappings.items():
            if not target_entity:
                continue
            if not target_entity.startswith("camera."):
                continue

            # Parse page number from obj_id (e.g., "p3b15" -> page 3)
            match = re.match(r"p(\d+)b\d+", obj_id)
            if not match:
                continue
            obj_page = int(match.group(1))

            # Only update if the panel is currently on the page containing the camera
            if self.current_page != obj_page:
                continue

            # Fetch camera state and get entity_picture attribute
            state = self.hass.states.get(target_entity)
            if not state:
                continue

            entity_picture = state.attributes.get("entity_picture")
            if not entity_picture:
                continue

            try:
                base_url = network.get_url(self.hass, allow_internal=True)
            except Exception:
                base_url = ""

            if not base_url:
                continue

            import time
            timestamp = int(time.time())
            full_url = f"{base_url}{entity_picture}&t={timestamp}"

            _LOGGER.debug("Periodic camera update for %s -> %s: %s", target_entity, obj_id, full_url)
            await mqtt.async_publish(self.hass, f"{self.topic_prefix}/command/{obj_id}.src", full_url)

    async def async_push_popup(self, text: str, duration: int = 10, buttons: list[str] = None) -> None:
        """Push a message box popup to the openHASP panel."""
        if not buttons:
            buttons = ["OK"]
        payload = {
            "page": 0,
            "id": 75,
            "obj": "msgbox",
            "text": text,
            "options": buttons,
            "auto_close": duration * 1000
        }
        await mqtt.async_publish(self.hass, f"{self.topic_prefix}/command/jsonl", json.dumps(payload))

    async def _sync_all_button_states(self) -> None:
        """Push current state of all mapped entities to the panel."""
        for obj_id, entity_id in self.mappings.items():
            if not entity_id:
                continue
            state = self.hass.states.get(entity_id)
            if state:
                await self._update_obj_from_state(obj_id, state)
