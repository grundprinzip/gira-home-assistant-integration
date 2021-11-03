import asyncio
from datetime import timedelta
import logging
from os import name
import typing
from custom_components.girahs.entity import GiraEntity
from custom_components.girahs.helper import create_cmd, to_ga, to_gira_pct, to_hass_byte

from homeassistant import core
from homeassistant import config_entries
from homeassistant.components import weather
from homeassistant.components.cover import (
    ATTR_POSITION,
    DEVICE_CLASS_SHADE,
    SUPPORT_CLOSE,
    SUPPORT_OPEN,
    SUPPORT_SET_POSITION,
    SUPPORT_STOP,
    CoverEntity,
)
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import TEMP_CELSIUS
from homeassistant.helpers.entity import DeviceInfo, ToggleEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType

from .const import DOMAIN
from .gira import HomeServerV2

logger = logging.getLogger(__name__)


def setup_platform(
    hass: core.HomeAssistant,
    config: config_entries.ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: typing.Optional[DiscoveryInfoType] = None,
) -> None:
    logger.info("Setting up Switches")
    api: HomeServerV2 = hass.data[DOMAIN]["api"]

    covers = [HomeServerWeather(l, api) for l in api.weathers]

    # Add the entities to Home Asssitant
    add_entities(covers)


class HomeServerWeather(GiraEntity, weather.WeatherEntity):
    def __init__(self, data: dict, api: HomeServerV2) -> None:
        GiraEntity.__init__(self, data, api)
        weather.WeatherEntity.__init__(self)
        logger.info("Weather %s", data)
        self._attr_unique_id = data["name"]
        self._attr_address_wind_bearing = data["address_wind_bearing"][0]
        self._attr_address_wind_speed = data["address_wind_speed"][0]
        self._attr_address_temperature = data["address_temperature"][0]
        self._attr_address_brightness_south = data["address_brightness_south"][0]
        self._attr_address_brightness_west = data["address_brightness_west"][0]
        self._attr_address_brightness_east = data["address_brightness_east"][0]
        self._attr_address_brightness_north = data["address_brightness_north"][0]
        self._attr_address_air_pressure = data["address_air_pressure"][0]
        self._attr_address_wind_bearing = data["address_humidity"][0]

        # Configure the unit
        self._attr_temperature_unit = TEMP_CELSIUS
        self._attr_condition = ""
        self._attr_temperature = 0

        for a in [
            self._attr_address_temperature,
            self._attr_address_wind_speed,
            self._attr_address_wind_bearing,
            self._attr_address_air_pressure,
        ]:
            self._attr_api.add_entity(a, self)

    async def handle_cmd(self, cmd: dict) -> None:
        value = cmd["value"]

        if cmd["address"] == self._attr_address_temperature:
            self._attr_temperature = value
            self.schedule_update_ha_state()

        if cmd["address"] == self._attr_address_air_pressure:
            # resolution is 0.01 hpa ->
            self._attr_pressure = value / 100
            self.schedule_update_ha_state()

        if cmd["address"] == self._attr_address_wind_speed:
            # Resolution is
            self._attr_wind_speed = value * 3.6
            self.schedule_update_ha_state()

        if cmd["address"] == self._attr_address_wind_bearing:
            self._attr_wind_bearing = value
            self.schedule_update_ha_state()
