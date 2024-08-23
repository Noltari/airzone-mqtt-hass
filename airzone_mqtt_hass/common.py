"""Airzone MQTT Common."""

from __future__ import annotations

from datetime import datetime
from enum import IntEnum, StrEnum
from typing import Any, Final

from .const import TZ_UTC


class AZ_Mode(IntEnum):
    """Airzone MQTT HVAC modes."""

    UNKNOWN = -1

    STOP = 0
    AUTO = 1
    COOLING = 2
    HEATING = 3
    VENTILATION = 4
    DRY = 5
    EMERGENCY_HEAT = 6
    HEAT_AIR = 7
    HEAT_RADIANT = 8
    HEAT_COMBINED = 9
    COOL_AIR = 10
    COOL_RADIANT = 11
    COOL_COMBINED = 12
    BYPASS = 13
    RECOVERY = 14
    REGULATION_TEMP = 15
    PURIFICATION = 16
    FAN_PURIFICATION = 17
    FAN_ENERGY = 18

    @classmethod
    def _missing_(cls, value: Any) -> AZ_Mode:
        return cls.UNKNOWN


class AZ_TemperatureUnit(IntEnum):
    """Airzone MQTT temperature units."""

    CELSIUS = 0
    FAHRENHEIT = 1


HA_PERCENTAGE: Final[str] = "%"


class HA_Platform(StrEnum):
    """Home Assistant entity platforms."""

    BINARY_SENSOR = "binary_sensor"
    SENSOR = "sensor"


class HA_SensorDeviceClass(StrEnum):
    """Device class for sensors."""

    HUMIDITY = "humidity"
    TEMPERATURE = "temperature"


class HA_UnitOfTemperature(StrEnum):
    """Home Assistant Temperature units."""

    CELSIUS = "°C"
    FAHRENHEIT = "°F"
    KELVIN = "K"


def get_current_dt() -> datetime:
    """Get current datetime."""
    return datetime.now(tz=TZ_UTC)
