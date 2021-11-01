import asyncio
from datetime import timedelta
import logging
from os import name
from re import S
import typing
from custom_components.girahs import helper
from custom_components.girahs.entity import GiraEntity
from custom_components.girahs.helper import create_cmd, to_ga, to_gira_pct, to_hass_byte

from homeassistant import core, helpers
from homeassistant import config_entries
from homeassistant.components import light
from homeassistant.helpers.typing import DiscoveryInfoType
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    COLOR_MODE_BRIGHTNESS,
    COLOR_MODE_ONOFF,
    SUPPORT_BRIGHTNESS,
    LightEntity,
)
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .gira import Accessory, HomeServerV2


logger = logging.getLogger(__name__)


def setup_platform(
    hass: core.HomeAssistant,
    config: config_entries.ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: typing.Optional[DiscoveryInfoType] = None,
) -> None:
    logger.info("Setting up lights")
    api: HomeServerV2 = hass.data[DOMAIN]["api"]

    lights = [HomeServerLight(l, api) for l in api.lights]
    # Adding lights
    api.all_lights = lights

    add_entities(lights)


class HomeServerLight(GiraEntity, LightEntity):
    def __init__(self, light: dict, api: HomeServerV2) -> None:
        super().__init__()

        self._attr_unique_id = light["address"][0]
        self._attr_is_on = True
        self._attr_brightness = 128
        self._attr_name = light["name"]
        self._attr_state_address = light["state_address"][0]
        self._attr_address = light["address"][0]
        self._attr_brightness_address = (
            light["brightness_address"][0] if "brightness_address" in light else None
        )

        # Color Mode
        if "brightness_address" in light:
            self._attr_color_mode = COLOR_MODE_BRIGHTNESS
            self._attr_supported_color_modes = set(
                [COLOR_MODE_ONOFF, COLOR_MODE_BRIGHTNESS]
            )
            self._attr_supported_features = SUPPORT_BRIGHTNESS
            pass
        else:
            self._attr_color_mode = COLOR_MODE_ONOFF
            self._attr_supported_color_modes = set(COLOR_MODE_ONOFF)
            pass

        logger.info("%s %s", self._attr_name, self._attr_color_mode)

        # Subscribe to updates on the on-off
        api.add_entity(self._attr_state_address, self)
        # Subscribe to updates on the brightness
        api.add_entity(self._attr_brightness_address, self)
        self._attr_api = api

    async def handle_cmd(self, cmd: dict) -> None:
        dirty = False
        # Handle On Off
        if cmd["address"] == self._attr_state_address:
            # Turn off
            if cmd["value"] == 0 and self._attr_is_on:
                self._attr_is_on = False
                dirty = True
            # Turn On
            if cmd["value"] == 1 and not self._attr_is_on:
                self._attr_is_on = True
                dirty = True

        # Handle Brightness
        if cmd["address"] == self._attr_brightness_address:
            value = cmd["value"]
            if cmd["cmd"] == 1 and value != self._attr_brightness:
                self._attr_brightness = helper.to_hass_byte(value)
                dirty = True
            if cmd["cmd"] == 2:
                self._attr_brightness += helper.to_hass_byte(value)
                dirty = True

        if dirty:
            self.schedule_update_ha_state()

    def should_poll(self) -> bool:
        return False

    async def async_turn_on(self, **kwargs):
        # Only if the lamp supports brightness allow changing the brightness.
        if self._attr_color_mode == COLOR_MODE_BRIGHTNESS and ATTR_BRIGHTNESS in kwargs:
            self._attr_brightness = kwargs.get(ATTR_BRIGHTNESS, 255)
            cmd = create_cmd(
                to_ga(self._attr_brightness_address), to_gira_pct(self._attr_brightness)
            )
            asyncio.create_task(self._attr_api.send_command(cmd))

        # Changing brightness will turn the lamp on as well
        if not self._attr_is_on and not ATTR_BRIGHTNESS in kwargs:
            cmd = create_cmd(to_ga(self._attr_address), 1)
            asyncio.create_task(self._attr_api.send_command(cmd))
            self._attr_is_on = True

    async def async_turn_off(self, **kwargs: typing.Any) -> None:
        if self._attr_is_on:
            cmd = create_cmd(to_ga(self._attr_address), 0)
            asyncio.create_task(self._attr_api.send_command(cmd))
            self._attr_is_on = False
