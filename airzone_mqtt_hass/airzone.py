"""Airzone MQTT."""

import asyncio
from collections.abc import Callable, Coroutine
from datetime import datetime, timedelta
import json
import logging
from typing import Any

from .common import HA_Platform, get_current_dt
from .config import Config
from .const import (
    AMT_EVENTS,
    AMT_INVOKE,
    AMT_ONLINE,
    AMT_REQUEST,
    AMT_RESPONSE,
    AMT_STATUS,
    AMT_V1,
    API_AZ_GET_STATUS,
    API_AZ_SYSTEM,
    API_AZ_ZONE,
    API_BODY,
    API_CMD,
    API_DESTINATION,
    API_DEVICE_ID,
    API_DEVICE_TYPE,
    API_DEVICES,
    API_HEADERS,
    API_ONLINE,
    API_REQ_ID,
    API_SYSTEM_ID,
    API_TS,
    HAD_AVAILABILITY,
    HAD_COMPONENTS,
    HAD_DEVICE,
    HAD_OFFLINE,
    HAD_ONLINE,
    HAD_STATE,
    TZ_UTC,
    MqttPayloadType,
)
from .device import Device
from .exceptions import AirzoneOffline, AirzonePollError, AirzoneTimeout
from .system import System
from .update import UpdateType
from .zone import Zone

_LOGGER = logging.getLogger(__name__)


class Airzone:
    """Airzone MQTT API."""

    callback_function: Callable[[], Coroutine[Any, Any, None]] | None
    mqtt_publish: Callable[[str, MqttPayloadType, int, bool], Coroutine[Any, Any, None]]

    def __init__(self, config: Config) -> None:
        """Airzone MQTT API init."""
        self.api_init: bool = False
        self.api_init_event: asyncio.Event = asyncio.Event()
        self.api_lock: asyncio.Lock = asyncio.Lock()
        self.api_raw_data: dict[str, Any] = {
            API_AZ_GET_STATUS: None,
        }
        self.api_resp: asyncio.Event = asyncio.Event()
        self.api_req_id: str = ""
        self.callback_function = None
        self.config: Config = config
        self.loop = asyncio.get_running_loop()
        self.mqtt_prefix: str = f"{config.topic_airzone}/{AMT_V1}"
        self.mqtt_topic: str = config.topic_airzone
        self.online: bool = False
        self.online_event: asyncio.Event = asyncio.Event()
        self.poll_timeout: timedelta = config.poll_timeout
        self.scan_interval: timedelta = config.scan_interval
        self.systems: dict[str, System] = {}
        self.update_dt: datetime | None = None
        self.zones: dict[str, Zone] = {}

    def api_safe_str(self, topic: str) -> str:
        """Airzone MQTT API safe string."""
        return topic.replace(".", "_")

    def api_az_get_status(self, data: dict[str, Any]) -> None:
        """Airzone MQTT API az->get_status."""
        cur_dt = get_current_dt()

        self.api_raw_data[API_AZ_GET_STATUS] = data

        body: dict[str, Any] = data.get(API_BODY, {})
        devices: list[dict[str, Any]] = body.get(API_DEVICES, [])

        mqtt_topic_pfx = f"{self.config.topic_interface}/{self.mqtt_topic}"
        for device in devices:
            dev_type = device.get(API_DEVICE_TYPE)

            if dev_type == API_AZ_SYSTEM:
                system = System(device)
                system.update(device, UpdateType.FULL)
                system.set_mqtt_topic(mqtt_topic_pfx)
                system_id = system.get_id()
                if system_id not in self.systems:
                    self.systems[system_id] = system
            elif dev_type == API_AZ_ZONE:
                zone = Zone(device)
                zone.update(device, UpdateType.FULL)
                zone.set_mqtt_topic(mqtt_topic_pfx)
                zone_id = zone.get_id()
                if zone_id not in self.zones:
                    self.zones[zone_id] = zone
            else:
                _LOGGER.warning("api_az_get_status: unknown device=%s", device)

        _LOGGER.debug("api_az_get_status: API init done.")

        if not self.api_init:
            self.api_init = True
            self.api_init_event.set()

        self.update_dt = cur_dt

    def cmd_destination(self, topic: str) -> str:
        """Airzone MQTT cmd destination."""
        topic = self.api_safe_str(topic)
        return f"{self.mqtt_prefix}/{AMT_RESPONSE}/{topic}"

    def cmd_req_id(self, req_id: str) -> str:
        """Airzone MQTT cmd req_id."""
        req_id = self.api_safe_str(req_id)

        cur_dt = get_current_dt()
        cur_date = f"{cur_dt.year}/{cur_dt.month}/{cur_dt.day}"
        cur_time = f"{cur_dt.hour}:{cur_dt.minute}:{cur_dt.second}"
        cur_us = cur_dt.microsecond
        time_id = f"{cur_date}-{cur_time}.{cur_us}"

        return f"{AMT_REQUEST}-{time_id}-{req_id}"

    def cmd_payload(self, data: dict[str, Any]) -> str:
        """Airzone MQTT cmd payload."""
        return json.dumps(data)

    async def cmd_invoke(self, data: dict[str, Any]) -> None:
        """Airzone MQTT cmd invoke."""
        topic = f"{self.mqtt_prefix}/{AMT_INVOKE}"
        payload = self.cmd_payload(data)

        headers = data.get(API_HEADERS, {})
        req_id = headers.get(API_REQ_ID, "")

        async with self.api_lock:
            self.api_resp.clear()
            self.api_req_id = req_id
            await self.mqtt_publish(topic, payload, 0, False)
            await self.api_resp.wait()

    async def cmd_az_get_status(self) -> None:
        """Airzone MQTT cmd az->get_status."""
        data: dict[str, Any] = {
            API_HEADERS: {
                API_CMD: API_AZ_GET_STATUS,
                API_DESTINATION: self.cmd_destination(API_AZ_GET_STATUS),
                API_REQ_ID: self.cmd_req_id(API_AZ_GET_STATUS),
            },
            API_BODY: None,
        }

        await self.cmd_invoke(data)

    async def msg_events_status(self, topic: list[str], payload: bytes) -> None:
        """Airzone MQTT events status message."""
        if topic[0] == AMT_STATUS:
            topic.pop(0)

        data = json.loads(payload)

        body = data.get(API_BODY, {})
        device_id = body.get(API_DEVICE_ID)
        device_type = body.get(API_DEVICE_TYPE)
        system_id = body.get(API_SYSTEM_ID)

        if device_type == API_AZ_SYSTEM:
            system = self.get_system(system_id, device_id)
            if system is not None:
                system.update(body, UpdateType.PARTIAL)
                await self.update_callback(data)
        elif device_type == API_AZ_ZONE:
            zone = self.get_zone(system_id, device_id)
            if zone is not None:
                zone.update(body, UpdateType.PARTIAL)
                await self.update_callback(data)
        else:
            _LOGGER.warning("msg_events: topic=%s payload=%s", topic, payload)

    async def msg_events(self, topic: list[str], payload: bytes) -> None:
        """Airzone MQTT events message."""
        if topic[0] == AMT_EVENTS:
            topic.pop(0)

        if topic[0] == AMT_STATUS:
            await self.msg_events_status(topic, payload)
        else:
            _LOGGER.warning("msg_events: topic=%s payload=%s", topic, payload)

    def msg_invoke(self, topic: list[str], payload: bytes) -> None:
        """Airzone MQTT invoke message."""
        _LOGGER.debug("msg_invoke: topic=%s payload=%s", topic, payload)

    def msg_online(self, payload: bytes) -> None:
        """Airzone MQTT online message."""
        data = json.loads(payload)

        self.online = data.get(API_ONLINE, False)

        if self.online:
            self.online_event.set()
        else:
            self.online_event.clear()

        _LOGGER.debug("Airzone MQTT online=%s.", self.online)

    async def msg_response(self, topic: list[str], payload: bytes) -> None:
        """Airzone MQTT response message."""
        data = json.loads(payload)

        headers = data.get(API_HEADERS, {})
        req_id = headers.get(API_REQ_ID)

        if req_id == self.api_req_id:
            self.api_resp.set()
        else:
            _LOGGER.error("Unexpected API response: req_id=%s", req_id)

        if topic[0] == AMT_RESPONSE:
            topic.pop(0)

        if topic[0] == self.api_safe_str(API_AZ_GET_STATUS):
            self.api_az_get_status(data)
            await self.update_callback({})
        else:
            _LOGGER.warning("msg_response: topic=%s payload=%s", topic, payload)

    def msg_unknown(self, topic: list[str], payload: bytes) -> None:
        """Airzone MQTT unknown message."""
        _LOGGER.warning("msg_unknown: topic=%s payload=%s", topic, payload)

    async def msg_process(
        self,
        topic_str: str,
        payload: bytes,
    ) -> None:
        """Airzone MQTT message callback."""
        topic_str = topic_str.removeprefix(f"{self.mqtt_prefix}/")

        topic = topic_str.split("/")
        if topic[0] == AMT_EVENTS:
            await self.msg_events(topic, payload)
        elif topic[0] == AMT_INVOKE:
            self.msg_invoke(topic, payload)
        elif topic[0] == AMT_ONLINE:
            self.msg_online(payload)
        elif topic[0] == AMT_RESPONSE:
            await self.msg_response(topic, payload)
        else:
            self.msg_unknown(topic, payload)

    def get_api_raw_data(self) -> dict[str, Any]:
        """Airzone MQTT API raw data."""
        return self.api_raw_data

    def get_dev_avail(self, device: Device) -> dict[str, Any]:
        """Airzone MQTT device availability."""
        if self.online and device.get_is_connected():
            state = HAD_ONLINE
        else:
            state = HAD_OFFLINE

        return {
            HAD_STATE: state,
        }

    def get_topic_subs(self) -> str:
        """Airzone MQTT topic subscription."""
        return f"{self.mqtt_prefix}/#"

    def get_system(self, system_id: str, device_id: str) -> System | None:
        """Airzone MQTT get system by IDs."""
        return self.systems.get(f"{system_id}:{device_id}")

    def get_zone(self, system_id: str, device_id: str) -> Zone | None:
        """Airzone MQTT get zone by IDs."""
        return self.zones.get(f"{system_id}:{device_id}")

    async def _update_events(self) -> bool:
        """Perform an events update of Airzone MQTT data."""
        if not self.api_init:
            return False

        if not self.online:
            return False

        if self.update_dt is None:
            return False

        return (get_current_dt() - self.update_dt) <= self.poll_timeout

    async def _update_polling(self) -> None:
        """Perform a polling update of Airzone MQTT data."""
        if not self.online:
            raise AirzoneOffline("Airzone MQTT device offline")

        try:
            async with asyncio.timeout(self.poll_timeout.total_seconds()):
                await self.cmd_az_get_status()
        except TimeoutError as err:
            self.api_lock.release()
            raise AirzoneTimeout(err) from err

        if not self.api_init:
            raise AirzonePollError("Airzone MQTT polling failed")

    async def update(self) -> None:
        """Airzone MQTT update."""
        if not await self._update_events():
            if self.api_init:
                _LOGGER.warning("airzone: polling update")

            await self._update_polling()

    async def update_callback(self, data: dict[str, Any]) -> None:
        """Run update callback."""
        data_ts = data.get(API_HEADERS, {}).get(API_TS)
        if data_ts is not None:
            self.update_dt = datetime.fromtimestamp(float(data_ts), tz=TZ_UTC)
        else:
            self.update_dt = get_current_dt()

        if self.callback_function is not None:
            await self.callback_function()

    def set_update_callback(
        self,
        callback_function: Callable[[], Coroutine[Any, Any, None]],
    ) -> None:
        """Set update callback."""
        self.callback_function = callback_function

    async def mqtt_update_system(self, system: System) -> None:
        """Publish MQTT system data."""
        system_topic = system.get_mqtt_topic()
        system_data = system.data()
        system_json = json.dumps(system_data)
        await self.mqtt_publish(
            f"{system_topic}/state",
            system_json,
            0,
            False,
        )

        avail_data = self.get_dev_avail(system)
        avail_json = json.dumps(avail_data)
        await self.mqtt_publish(
            f"{system_topic}/{HAD_AVAILABILITY}",
            avail_json,
            0,
            False,
        )

    async def mqtt_update_zone(self, zone: Zone) -> None:
        """Publish MQTT zone data."""
        zone_topic = zone.get_mqtt_topic()
        zone_data = zone.data()
        zone_json = json.dumps(zone_data)
        await self.mqtt_publish(
            f"{zone_topic}/state",
            zone_json,
            0,
            False,
        )

        avail_data = self.get_dev_avail(zone)
        avail_json = json.dumps(avail_data)
        await self.mqtt_publish(
            f"{zone_topic}/{HAD_AVAILABILITY}",
            avail_json,
            0,
            False,
        )

    async def mqtt_update(self) -> None:
        """Publish MQTT data."""
        tasks = []

        for system in self.systems.values():
            system_task = asyncio.create_task(self.mqtt_update_system(system))
            tasks.append(system_task)

        for zone in self.zones.values():
            zone_task = asyncio.create_task(self.mqtt_update_zone(zone))
            tasks.append(zone_task)

        asyncio.gather(*tasks)

    async def ha_config_pub_binary_sensors(
        self, binary_sensors: dict[str, Any], device: dict[str, Any]
    ) -> None:
        """Publish Home Assistant binary sensors."""
        _LOGGER.error("ha_config_pub_binary_sensors: device=%s", device)
        for binary_sensor in binary_sensors:
            _LOGGER.error(
                "ha_config_pub_binary_sensors: binary_sensor=%s", binary_sensor
            )

    async def ha_config_pub_sensors(
        self, sensors: dict[str, Any], device: dict[str, Any]
    ) -> None:
        """Publish Home Assistant sensors."""
        _LOGGER.error("ha_config_pub_binary_sensors: device=%s", device)
        for sensor in sensors:

            _LOGGER.error("ha_config_pub_sensors: sensor=%s", sensor)

    async def ha_config_pub(self) -> None:
        """Publish Home Assistant config."""
        tasks = []

        dev_list = list(self.systems.values()) + list(self.zones.values())

        for dev in dev_list:
            config = dev.ha_mqtt_config()
            components: dict[str, dict[str, Any]] = config.get(HAD_COMPONENTS, {})
            device: dict[str, Any] = config.get(HAD_DEVICE, {})

            binary_sensors = components.get(HA_Platform.BINARY_SENSOR, {})
            binary_sensors_task = asyncio.create_task(
                self.ha_config_pub_binary_sensors(binary_sensors, device)
            )
            tasks.append(binary_sensors_task)

            sensors = components.get(HA_Platform.SENSOR, {})
            sensors_task = asyncio.create_task(
                self.ha_config_pub_sensors(sensors, device)
            )
            tasks.append(sensors_task)

        asyncio.gather(*tasks)
