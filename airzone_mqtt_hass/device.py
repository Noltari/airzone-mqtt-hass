"""Airzone MQTT Device."""

from abc import ABC, abstractmethod
import logging
import re
from typing import Any

from .common import AZ_TemperatureUnit, HA_UnitOfTemperature
from .const import (
    API_DEVICE_ID,
    API_IS_CONNECTED,
    API_META,
    API_PARAMETERS,
    API_SYSTEM_ID,
    API_UNITS,
    AZ_MANUFACTURER,
    AZD_DEVICE_ID,
    AZD_ID,
    AZD_IS_CONNECTED,
    AZD_SYSTEM_ID,
    AZD_UNITS,
    HAD_COMPONENTS,
    HAD_DEVICE,
    HAD_IDENTIFIERS,
    HAD_MANUFACTURER,
    HAD_MODEL,
    HAD_NAME,
    HAD_STATE,
    HAD_STATE_TOPIC,
)
from .update import UpdateType

_LOGGER = logging.getLogger(__name__)


class Device(ABC):
    """Airzone MQTT Device."""

    model: str
    mqtt_topic: str
    name: str

    def __init__(self, data: dict[str, Any]) -> None:
        """Airzone MQTT Device init."""
        self.device_id = str(data.get(API_DEVICE_ID))
        self.is_connected = False
        self.manufacturer = AZ_MANUFACTURER
        self.system_id = str(data.get(API_SYSTEM_ID))
        self.units = AZ_TemperatureUnit.CELSIUS

        _LOGGER.debug("Device created with id=%s", self.device_id)

    def get_id(self) -> str:
        """Airzone MQTT Device ID."""
        return f"{self.system_id}:{self.device_id}"

    def get_id_ha(self) -> str:
        """Airzone MQTT Device ID for Home Assistant."""
        return re.sub("[^0-9a-zA-Z_-]+", "_", self.get_id())

    def get_is_connected(self) -> bool:
        """Airzone MQTT Device connection."""
        return self.is_connected

    def get_manufacturer(self) -> str:
        """Airzone MQTT Device manufacturer."""
        return self.manufacturer

    def get_model(self) -> str:
        """Airzone MQTT Device model."""
        return self.model

    def get_mqtt_topic(self, sfx: str | None = None) -> str:
        """Airzone Zone get MQTT topic."""
        if sfx is not None:
            return f"{self.mqtt_topic}/{sfx}"
        return self.mqtt_topic

    def get_name(self) -> str:
        """Airzone MQTT Device name."""
        return self.name

    def get_units(self) -> AZ_TemperatureUnit:
        """Airzone MQTT Device units."""
        return self.units

    def get_units_ha(self) -> HA_UnitOfTemperature:
        """Airzone MQTT Device units."""
        units_dict = {
            AZ_TemperatureUnit.CELSIUS: HA_UnitOfTemperature.CELSIUS,
            AZ_TemperatureUnit.FAHRENHEIT: HA_UnitOfTemperature.FAHRENHEIT,
        }
        return units_dict.get(self.get_units(), HA_UnitOfTemperature.CELSIUS)

    def data(self) -> dict[str, Any]:
        """Airzone MQTT Device data."""
        data: dict[str, Any] = {
            AZD_DEVICE_ID: self.device_id,
            AZD_ID: self.get_id(),
            AZD_IS_CONNECTED: self.is_connected,
            AZD_SYSTEM_ID: self.system_id,
            AZD_UNITS: self.units,
        }

        return data

    def update(self, data: dict[str, Any], update_type: UpdateType) -> None:
        """Airzone MQTT Device update."""
        meta: dict[str, Any] = data.get(API_META, {})
        parameters: dict[str, Any] = data.get(API_PARAMETERS, {})

        is_connected = parameters.get(API_IS_CONNECTED)
        if is_connected is not None:
            self.is_connected = bool(is_connected)

        units = meta.get(API_UNITS)
        if units is not None:
            self.units = AZ_TemperatureUnit(units)

        if update_type == UpdateType.PARTIAL:
            _LOGGER.debug("Device[%s] updated with data=%s", self.get_id(), data)

    def ha_mqtt_device(self) -> dict[str, Any]:
        """Zone Home Assistant MQTT config data."""
        return {
            HAD_IDENTIFIERS: self.get_id_ha(),
            HAD_MANUFACTURER: self.get_manufacturer(),
            HAD_MODEL: self.get_model(),
            HAD_NAME: self.get_name(),
        }

    @abstractmethod
    def ha_mqtt_components(self) -> dict[str, Any]:
        """Zone Home Assistant MQTT config data."""
        raise NotImplementedError("ha_mqtt_device not implemented")

    def ha_mqtt_config(self) -> dict[str, Any]:
        """Zone Home Assistant MQTT config data."""
        return {
            HAD_COMPONENTS: self.ha_mqtt_components(),
            HAD_DEVICE: self.ha_mqtt_device(),
            HAD_STATE_TOPIC: self.get_mqtt_topic(HAD_STATE),
        }
