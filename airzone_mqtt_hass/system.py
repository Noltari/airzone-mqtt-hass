"""Airzone MQTT System."""

import logging
from typing import Any

from .const import AZ_MODEL_SYSTEM
from .device import Device
from .update import UpdateType

_LOGGER = logging.getLogger(__name__)


class System(Device):
    """Airzone MQTT System."""

    def __init__(self, data: dict[str, Any]) -> None:
        """Airzone MQTT System init."""
        super().__init__(data)

        self.model: str = AZ_MODEL_SYSTEM
        self.name: str = f"System [{self.get_id()}]"

        _LOGGER.debug("System created with id=%s", self.device_id)

    def set_mqtt_topic(self, pfx: str) -> None:
        """Airzone Zone set MQTT topic."""
        self.mqtt_topic = f"{pfx}/system/{self.get_id_ha()}"

    def data(self) -> dict[str, Any]:
        """Airzone MQTT System data."""
        data = super().data()

        return data

    def update(self, data: dict[str, Any], update_type: UpdateType) -> None:
        """Airzone MQTT System update data."""
        super().update(data, update_type)

        if update_type == UpdateType.PARTIAL:
            _LOGGER.debug("System[%s] updated with data=%s", self.get_id(), data)

    def ha_mqtt_components(self) -> dict[str, Any]:
        """Zone Home Assistant MQTT config data."""
        return {}
