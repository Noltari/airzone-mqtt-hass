"""Home Assistant MQTT."""

import asyncio
import logging

from .config import Config
from .const import HAD_ONLINE, HAD_STATUS

_LOGGER = logging.getLogger(__name__)


class HomeAssistant:
    """Home Assistant MQTT."""

    def __init__(self, config: Config) -> None:
        """Home Assistant MQTT init."""
        self.config = config
        self.mqtt_config_event: asyncio.Event = asyncio.Event()
        self.online = True

        self.mqtt_topic = config.topic_homeassistant

    def msg_status(self, payload: bytes) -> None:
        """Home Assistant MQTT status message."""
        status = str(payload)

        self.online = status == HAD_ONLINE

        _LOGGER.debug("HA MQTT online=%s.", self.online)

        if self.online:
            self.mqtt_config_event.set()

    def msg_unknown(self, topic: list[str], payload: bytes) -> None:
        """Home Assistant MQTT unknown message."""
        _LOGGER.warning("msg_unknown: topic=%s payload=%s", topic, payload)

    async def msg_process(
        self,
        topic_str: str,
        payload: bytes,
    ) -> None:
        """Home Assistant MQTT message callback."""
        topic_str = topic_str.removeprefix(f"{self.mqtt_topic}/")

        topic = topic_str.split("/")
        if topic[0] == HAD_STATUS:
            self.msg_status(payload)
        else:
            self.msg_unknown(topic, payload)

    def get_topic_status(self) -> str:
        """Home Assistant MQTT status topic."""
        return f"{self.config.topic_homeassistant}/status"
