"""Airzone MQTT Update."""

from enum import IntEnum


class UpdateType(IntEnum):
    """Airzone MQTT update type."""

    FULL = 1
    PARTIAL = 2
