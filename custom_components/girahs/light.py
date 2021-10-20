from datetime import timedelta
import logging
import typing

from homeassistant import core
from homeassistant import config_entries
from homeassistant.components.light import COLOR_MODE_ONOFF, LightEntity
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
    logger.info("Setting up GiraHS lights %s", api.api.token)

    logger.info("Triggering async loading of devices")
    await async_update_items(hass, api, async_add_devices)


async def async_update_items(
    hass: core.HomeAssistant, api: HomeServerHass, async_add_devices
) -> None:
    new_lights = []
    for l in api.lights:
        new_lights.append(HomeServerLight(l, api))
    logger.info("Found %d lights", len(new_lights))
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
        self._light = light

    @property
    def unique_id(self) -> typing.Optional[str]:
        return self._light.uid

    @property
    def device_id(self) -> typing.Optional[str]:
        return self.unique_id

    @property
    def name(self) -> typing.Optional[str]:
        return self._light.display_name

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
    def color_mode(self) -> typing.Optional[str]:
        return COLOR_MODE_ONOFF

    @property
    def supported_color_modes(self) -> typing.Optional[set[str]]:
        return set(COLOR_MODE_ONOFF)

    def turn_on(self, **kwargs):
        """Turn the device on."""
        self._is_on = True

    async def async_turn_on(self, **kwargs):
        """Turn device on."""
        self._is_on = True

    def turn_off(self, **kwargs):
        """Turn the device off."""
        self._is_on = False

    async def async_turn_off(self, **kwargs):
        """Turn device off."""
        self._is_on = False

    def is_on(self) -> bool:
        return self._is_on

    def update(self) -> None:
        # logger.info("Sync update")
        pass

    async def async_update(self) -> None:
        # logger.info("Async update")
        pass
