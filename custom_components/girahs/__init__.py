import asyncio
from attr import has
from custom_components.girahs.gira import HomeServerV2
from homeassistant import config_entries, core
from homeassistant.const import CONF_HOST
from homeassistant.helpers import config_validation
from .const import DOMAIN


import homeassistant.components.knx.schema as sch

from functools import partial

import logging
import voluptuous as vol
import time
import threading


CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.All(
            vol.Schema(
                {
                    vol.Required(CONF_HOST): config_validation.string,
                    **sch.ClimateSchema.platform_node(),
                    **sch.SwitchSchema.platform_node(),
                    **sch.LightSchema.platform_node(),
                    **sch.WeatherSchema.platform_node(),
                    **sch.CoverSchema.platform_node(),
                    **sch.SensorSchema.platform_node(),
                    **sch.BinarySensorSchema.platform_node(),
                }
            )
        )
    },
    extra=vol.ALLOW_EXTRA,
)

logger = logging.getLogger(__name__)


async def delay_connect(gira: HomeServerV2) -> None:
    asyncio.sleep(10)
    asyncio.create_task(gira.connect())


async def async_setup(hass: core.HomeAssistant, config: config_entries.ConfigType):
    logger.info("Registering Gira KNX Gateway")
    gira = HomeServerV2(config)
    hass.data[DOMAIN] = {"api": gira}

    # Load all platforms
    for p in [
        "light",
        "switch",
        "cover",
        "climate",
        "weather",
        "binary_sensor",
        "sensor",
    ]:
        hass.helpers.discovery.load_platform(p, DOMAIN, {}, config)

    asyncio.create_task(delay_connect(gira))
    return True
