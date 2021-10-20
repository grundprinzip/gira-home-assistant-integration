from datetime import timedelta
import logging
from os import name
import typing

from homeassistant import core
from homeassistant import config_entries
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    CURRENT_HVAC_HEAT,
    HVAC_MODE_HEAT,
    SUPPORT_TARGET_TEMPERATURE,
)
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN
from .gira import Accessory, HomeServerHass

# Polling Interval used by the platform
SCAN_INTERVAL = timedelta(seconds=30)

logger = logging.getLogger(__name__)


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_devices,
) -> None:
    """Set up entry."""
    api: HomeServerHass = hass.data[DOMAIN][config_entry.entry_id]
    logger.info("Setting up GiraHS covers %s", api.api.token)

    logger.info("Triggering async loading of devices")
    await async_update_items(hass, api, async_add_devices)


async def async_update_items(
    hass: core.HomeAssistant, api: HomeServerHass, async_add_devices
) -> None:
    new_entities = []
    for c in api.hvac:
        new_entities.append(HomeServerClimate(c, api))
    logger.info("Found %d covers", len(new_entities))
    if new_entities:
        async_add_devices(new_entities)


class HomeServerClimate(ClimateEntity):
    def __init__(self, c: Accessory, api: HomeServerHass) -> None:
        super().__init__()
        self._api = api
        self._accessory = c
        self._functions = {k["name"]: k["uid"] for k in self._accessory.data_points}

    @property
    def unique_id(self) -> typing.Optional[str]:
        return self._accessory.uid

    @property
    def device_id(self) -> typing.Optional[str]:
        return self.unique_id

    @property
    def name(self) -> typing.Optional[str]:
        return f"{self._accessory.display_name} ({self._accessory.location})"

    @property
    def temperature_unit(self) -> str:
        return TEMP_CELSIUS

    @property
    def supported_features(self) -> int:
        return SUPPORT_TARGET_TEMPERATURE

    @property
    def hvac_action(self) -> typing.Optional[str]:
        return CURRENT_HVAC_HEAT

    @property
    def hvac_mode(self) -> str:
        return HVAC_MODE_HEAT

    def set_hvac_mode(self, hvac_mode: str) -> None:
        pass

    @property
    def hvac_modes(self) -> list[str]:
        return [HVAC_MODE_HEAT]

    @property
    def target_temperature_step(self) -> typing.Optional[float]:
        return 1.0

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        logger.info("%s", kwargs)
        # self._api.set_value(self._functions["Set-Point"], kwargs[ATTR_TEMPERATURE])

    async def async_update(self) -> None:
        result = await self._api.get_values(self._accessory.uid)
        for x in result:
            if self._functions["Current"] == x["uid"]:
                self._attr_current_temperature = x["value"]
            elif self._functions["Set-Point"] == x["uid"]:
                self._attr_target_temperature = x["value"]
