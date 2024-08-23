"""MQTT interface."""

import asyncio
import logging

from .airzone import Airzone
from .config import Config
from .exceptions import AirzoneError
from .homeassistant import HomeAssistant
from .mqtt import Mqtt

_LOGGER = logging.getLogger(__name__)


class Interface:
    """Interface class."""

    def __init__(
        self,
        config: Config,
        airzone: Airzone,
        homeassistant: HomeAssistant,
        mqtt: Mqtt,
    ) -> None:
        """Interface init."""
        self.airzone = airzone
        self.config = config
        self.homeassistant = homeassistant
        self.mqtt = mqtt

        self.mqtt_topic = config.topic_interface

        self.airzone_lock: asyncio.Lock = asyncio.Lock()

        self.airzone.set_update_callback(self.airzone_callback)

    async def start(self) -> None:
        """Interface start."""
        self.airzone.mqtt_publish = self.mqtt.publish

        self.homeassistant.mqtt_config_event.set()

        self.mqtt.connect()
        self.mqtt.subscribe(self.airzone.get_topic_subs())
        self.mqtt.subscribe(self.homeassistant.get_topic_status())

    async def stop(self) -> None:
        """Interface stop."""
        self.mqtt.disconnect()

    async def airzone_task(self) -> None:
        """Airzone task."""
        await self.airzone.online_event.wait()

        while True:
            try:
                await self.airzone.update()
            except AirzoneError as err:
                _LOGGER.error(err)
            await asyncio.sleep(self.airzone.scan_interval.total_seconds())

    async def airzone_callback(self) -> None:
        """Data callback."""
        async with self.airzone_lock:
            await self.airzone.mqtt_update()

    async def homeassistant_config_task(self) -> None:
        """Home Assistant task."""
        while True:
            await self.airzone.api_init_event.wait()
            await self.homeassistant.mqtt_config_event.wait()

            await self.airzone.ha_config_pub()
            self.homeassistant.mqtt_config_event.clear()

    async def mqtt_task(self) -> None:
        """MQTT task."""
        while True:
            msg = await self.mqtt.rx_msg_pop()
            if msg is None:
                continue

            if msg.topic.startswith(self.mqtt_topic):
                _LOGGER.warning("interface_rx: topic=%s", msg.topic)
            elif msg.topic.startswith(self.airzone.mqtt_topic):
                await self.airzone.msg_process(msg.topic, msg.payload)
                _LOGGER.warning("airzone_rx: topic=%s", msg.topic)
            elif msg.topic.startswith(self.homeassistant.mqtt_topic):
                await self.homeassistant.msg_process(msg.topic, msg.payload)
                _LOGGER.warning("homeassistant_rx: topic=%s", msg.topic)
            else:
                _LOGGER.error(
                    "mqtt_rx: unknown message topic=%s payload=%s",
                    msg.topic,
                    msg.payload,
                )

    async def task(self) -> None:
        """Interface task."""
        while True:
            # print(f"interface_task: {interface}")
            await asyncio.sleep(1)
