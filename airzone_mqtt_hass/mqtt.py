"""MQTT."""

import asyncio
import logging
from typing import Any

import paho.mqtt.client as mqtt
from paho.mqtt.client import ConnectFlags, DisconnectFlags
from paho.mqtt.enums import CallbackAPIVersion
from paho.mqtt.properties import Properties
from paho.mqtt.reasoncodes import ReasonCode

from .config import Config
from .const import MqttPayloadType

_LOGGER = logging.getLogger(__name__)


class Mqtt:
    """MQTT."""

    def __init__(self, config: Config) -> None:
        """MQTT init."""
        self.config = config
        self.loop = asyncio.get_running_loop()

        self.mqtt_client = mqtt.Client(CallbackAPIVersion.VERSION2)
        self.mqtt_event_connect = asyncio.Event()
        self.mqtt_event_disconnect = asyncio.Event()
        self.mqtt_event_subscribe = asyncio.Event()
        self.mqtt_is_connected = False

        if not config.mqtt.is_anon():
            self.mqtt_client.username_pw_set(
                username=config.mqtt.user,
                password=config.mqtt.password,
            )

        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_disconnect = self.on_disconnect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.on_subscribe = self.on_subscribe

        self.rx_event = asyncio.Event()
        self.rx_lock = asyncio.Lock()
        self.rx_list: list[mqtt.MQTTMessage] = []

    def connect(self) -> None:
        """Connect to MQTT broker."""
        self.mqtt_event_connect.clear()
        self.mqtt_event_disconnect.clear()
        self.mqtt_event_subscribe.clear()

        self.mqtt_client.connect(
            self.config.mqtt.host,
            self.config.mqtt.port,
        )
        self.mqtt_client.loop_start()

    def disconnect(self) -> None:
        """Disconnect from MQTT broker."""
        self.mqtt_event_connect.clear()
        self.mqtt_event_disconnect.clear()
        self.mqtt_event_subscribe.clear()

        self.mqtt_client.disconnect()
        self.mqtt_client.loop_stop()

    async def publish(
        self,
        topic: str,
        payload: MqttPayloadType = None,
        qos: int = 0,
        retain: bool = False,
    ) -> None:
        """Publish message on MQTT topic."""
        self.mqtt_client.publish(topic, payload, qos, retain)

    def subscribe(self, topic: str) -> None:
        """Perform a MQTT subscription."""
        self.mqtt_client.subscribe(topic)

    def on_connect(
        self,
        client: mqtt.Client,
        userdata: Any,
        flags: ConnectFlags,
        reason_code: ReasonCode,
        properties: Properties | None,
    ) -> None:
        # pylint: disable=unused-argument
        """MQTT connection event callback."""
        self.mqtt_is_connected = reason_code.value == 0

        self.mqtt_event_connect.set()

    def on_disconnect(
        self,
        client: mqtt.Client,
        userdata: Any,
        flags: DisconnectFlags,
        reason_code: ReasonCode,
        properties: Properties | None,
    ) -> None:
        # pylint: disable=unused-argument
        """MQTT disconnection event callback."""
        self.mqtt_is_connected = False

        self.mqtt_event_disconnect.set()

    def on_message(
        self,
        client: mqtt.Client,
        userdata: Any,
        message: mqtt.MQTTMessage,
    ) -> None:
        # pylint: disable=unused-argument
        """MQTT message event callback."""
        asyncio.run_coroutine_threadsafe(self.rx_msg_push(message), self.loop)

    def on_subscribe(
        self,
        client: mqtt.Client,
        userdata: Any,
        mid: int,
        reason_codes: list[ReasonCode],
        properties: Properties | None,
    ) -> None:
        # pylint: disable=unused-argument
        """MQTT subscription event callback."""
        self.mqtt_event_subscribe.set()

    async def rx_msg_push(self, message: mqtt.MQTTMessage) -> None:
        """MQTT RX message queue."""
        async with self.rx_lock:
            _LOGGER.debug("rx_msg_push: topic=%s", message.topic)
            self.rx_list.append(message)
            self.rx_event.set()

    async def rx_msg_pop(self) -> mqtt.MQTTMessage | None:
        """MQTT RX message process."""
        msg: mqtt.MQTTMessage | None = None

        await self.rx_event.wait()

        async with self.rx_lock:
            if len(self.rx_list) > 0:
                msg = self.rx_list.pop(0)
                _LOGGER.debug("rx_msg_pop: %s", msg.topic)
            if len(self.rx_list) == 0:
                self.rx_event.clear()

        return msg
