from datetime import timedelta
import logging
from os import name
import typing
from custom_components.girahs.helper import to_gira_pct, to_hass_byte

from homeassistant import core
from homeassistant import config_entries
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    COLOR_MODE_BRIGHTNESS,
    COLOR_MODE_ONOFF,
    LightEntity,
)
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .gira import Accessory, HomeServerHass

# Polling Interval used by the platform
SCAN_INTERVAL = timedelta(seconds=5)

logger = logging.getLogger(__name__)


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_devices,
) -> None:
    """Set up entry."""
    api: HomeServerHass = hass.data[DOMAIN][config_entry.entry_id]
    logger.debug("Setting up GiraHS lights %s", api.api.token)

    logger.debug("Triggering async loading of devices")
    await async_update_items(hass, api, async_add_devices)


async def async_update_items(
    hass: core.HomeAssistant, api: HomeServerHass, async_add_devices
) -> None:
    new_lights = []
    for l in api.lights:
        new_lights.append(HomeServerLight(l, api))
    logger.debug("Found %d lights", len(new_lights))
    if new_lights:
        async_add_devices(new_lights)


class HomeServerLight(LightEntity):
    """An entity using CoordinatorEntity.

    The CoordinatorEntity class provides:
      should_poll
      async_update
      async_added_to_hass
      available
    """

    def __init__(self, light: Accessory, api: HomeServerHass) -> None:
        super().__init__()
        self._api = api
        self._is_on = False
        self._brightness = 0
        self._light = light

        # Convert the data points to
        self._functions = {k["name"]: k["uid"] for k in self._light.data_points}

    @property
    def unique_id(self) -> typing.Optional[str]:
        return self._light.uid

    @property
    def device_id(self) -> typing.Optional[str]:
        return self.unique_id

    @property
    def name(self) -> typing.Optional[str]:
        return f"{self._light.display_name} ({self._light.location})"

    @property
    def device_info(self) -> typing.Optional[DeviceInfo]:
        info = {
            "identifiers": {(DOMAIN, self.device_id)},
            "name": self.name,
            "manufacturer": "Gira HomeServer Passthrough",
            "via_device": (DOMAIN, "HomeServer"),
        }
        return info

    @property
    def supported_color_modes(self) -> typing.Optional[set[str]]:
        tmp = set(COLOR_MODE_ONOFF)
        if len([x for x in self._light.data_points if x["name"] == "Brightness"]):
            tmp.add(COLOR_MODE_BRIGHTNESS)
        return tmp

    async def async_turn_on(self, **kwargs):
        """Turn device on."""
        logger.debug("Attributes %s", kwargs)
        if not self._is_on:
            self._is_on = True
            if ATTR_BRIGHTNESS in kwargs:
                val = to_gira_pct(kwargs[ATTR_BRIGHTNESS])
                await self._api.set_value(self._functions["Brightness"], val)
            else:
                await self._api.set_value(self._functions["OnOff"], True)
        else:
            if ATTR_BRIGHTNESS in kwargs:
                logger.debug("Attributes %s  %s", self._functions["Brightness"], kwargs)
                val = to_gira_pct(kwargs[ATTR_BRIGHTNESS])
                await self._api.set_value(self._functions["Brightness"], val)

    async def async_turn_off(self, **kwargs):
        """Turn device off."""
        self._is_on = False
        await self._api.set_value(self._functions["OnOff"], False)

    @property
    def is_on(self) -> bool:
        return self._is_on

    @property
    def brightness(self) -> typing.Optional[int]:
        """Return the brightness of this light between 0..255."""
        return self._brightness

    async def async_update(self) -> None:
        result = await self._api.get_values(self._light.uid)
        for x in result:
            if self._functions["OnOff"] == x["uid"]:
                self._is_on = x["value"]
            elif self._functions["Brightness"] == x["uid"]:
                self._brightness = to_hass_byte(x["value"])
        pass
