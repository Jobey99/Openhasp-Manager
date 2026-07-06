"""Sensor platform for openHASP Manager."""
from __future__ import annotations

import json
import logging
from homeassistant.components.sensor import SensorEntity, SensorStateClass, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components import mqtt

from .const import DOMAIN, CONF_PLATE_TOPIC

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up openHASP sensors."""
    topic_prefix = config_entry.data.get(CONF_PLATE_TOPIC, "hasp/plate")
    plate_name = topic_prefix.split("/")[-1] if "/" in topic_prefix else topic_prefix

    sensors = [
        OpenHASPWiFiSensor(plate_name, topic_prefix),
        OpenHASPUptimeSensor(plate_name, topic_prefix),
        OpenHASPSensor(plate_name, topic_prefix, "ip", "IP Address", None, None),
        OpenHASPSensor(plate_name, topic_prefix, "heapFree", "Free Heap", "B", SensorStateClass.MEASUREMENT),
    ]

    async_add_entities(sensors)


class OpenHASPSensor(SensorEntity):
    """Representation of an openHASP status sensor."""

    _attr_has_entity_name = True

    def __init__(self, plate_name: str, topic_prefix: str, key: str, name: str, unit: str | None = None, state_class: SensorStateClass | None = None) -> None:
        self._plate_name = plate_name
        self._topic_prefix = topic_prefix
        self._key = key
        self._name = f"{name}"
        self._unit = unit
        self._state_class = state_class
        self._state = None
        self._unsub_mqtt = None

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"{self._topic_prefix}_{self._key}"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self) -> str | None:
        """Return unit of measurement."""
        return self._unit

    @property
    def state_class(self) -> SensorStateClass | None:
        """Return state class."""
        return self._state_class

    @property
    def device_info(self):
        """Return device info link."""
        return {
            "identifiers": {(DOMAIN, self._topic_prefix)},
            "name": f"openHASP {self._plate_name}",
            "manufacturer": "openHASP",
        }

    async def async_added_to_hass(self) -> None:
        """Subscribe to MQTT status updates."""
        @callback
        def _message_received(msg) -> None:
            try:
                payload = json.loads(msg.payload)
                val = payload.get(self._key)
                if val is not None:
                    self._state = val
                    self.async_write_ha_state()
            except Exception:
                pass

        self._unsub_mqtt = await mqtt.async_subscribe(
            self.hass, f"{self._topic_prefix}/state/statusupdate", _message_received
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from MQTT."""
        if self._unsub_mqtt:
            self._unsub_mqtt()


class OpenHASPWiFiSensor(OpenHASPSensor):
    """WiFi Signal Sensor."""

    def __init__(self, plate_name: str, topic_prefix: str) -> None:
        super().__init__(plate_name, topic_prefix, "rssi", "WiFi Signal", "dBm", SensorStateClass.MEASUREMENT)

    @property
    def device_class(self) -> SensorDeviceClass | None:
        """Return device class."""
        return SensorDeviceClass.SIGNAL_STRENGTH


class OpenHASPUptimeSensor(OpenHASPSensor):
    """Uptime Sensor."""

    def __init__(self, plate_name: str, topic_prefix: str) -> None:
        super().__init__(plate_name, topic_prefix, "uptime", "Uptime", "s", SensorStateClass.TOTAL_INCREASING)

    @property
    def device_class(self) -> SensorDeviceClass | None:
        """Return device class."""
        return SensorDeviceClass.DURATION
