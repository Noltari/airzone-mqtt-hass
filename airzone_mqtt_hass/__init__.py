"""Airzone MQTT to Home Assistant."""

import asyncio
import logging

from .airzone import Airzone
from .config import Config
from .homeassistant import HomeAssistant
from .interface import Interface
from .mqtt import Mqtt

_LOGGER = logging.getLogger(__name__)


async def async_main() -> None:
    """Airzone MQTT Home Assistant async entry."""

    config = Config()

    airzone = Airzone(config)
    homeassistant = HomeAssistant(config)
    mqtt = Mqtt(config)

    interface = Interface(
        config,
        airzone,
        homeassistant,
        mqtt,
    )

    await interface.start()

    try:
        tasks = [
            asyncio.create_task(interface.airzone_task()),
            asyncio.create_task(interface.homeassistant_config_task()),
            asyncio.create_task(interface.task()),
            asyncio.create_task(interface.mqtt_task()),
        ]
        await asyncio.gather(*tasks)
    except Exception as err:  # pylint: disable=broad-exception-caught
        await interface.stop()
        raise err


def main() -> None:
    """Airzone MQTT Home Assistant entry."""
    loop = asyncio.new_event_loop()
    loop.run_until_complete(async_main())


if __name__ == "__main__":
    main()
