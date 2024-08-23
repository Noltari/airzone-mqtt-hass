"""Home Assistant MQTT."""

from datetime import timedelta
import logging

_LOGGER = logging.getLogger(__name__)


class MqttConfig:
    """MQTT Config class."""

    def __init__(self) -> None:
        """MQTT Config init."""
        self.host: str = "192.168.1.8"
        self.port: int = 1883
        self.user: str | None = None
        self.password: str | None = None

    def is_anon(self) -> bool:
        """MQTT uses anonymous authentication."""
        return self.user is None or self.password is None


class Config:
    """Config class."""

    def __init__(self) -> None:
        """Config init."""
        self.mqtt = MqttConfig()
        self.poll_timeout = timedelta(minutes=15)
        self.scan_interval = timedelta(seconds=60)
        self.topic_airzone = "airzone"
        self.topic_homeassistant = "homeassistant-test"
        self.topic_interface = "airzone-mqtt-hass"
