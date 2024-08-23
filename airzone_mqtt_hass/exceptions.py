"""Airzone MQTT Exceptions."""

from __future__ import annotations


class AirzoneError(Exception):
    """Base class for Airzone MQTT errors."""


class AirzoneOffline(AirzoneError):
    """Exception raised when Airzone device is offline."""


class AirzonePollError(AirzoneError):
    """Exception raised when Airzone device polling fails."""


class AirzoneTimeout(AirzoneError):
    """Exception raised when Airzone device times out."""
