from datetime import timedelta
import logging
from os import name
import typing
from custom_components.girahs.helper import to_gira_pct, to_hass_byte

from homeassistant import core
from homeassistant import config_entries
from homeassistant.components.cover import (
    ATTR_POSITION,
    DEVICE_CLASS_SHADE,
    SUPPORT_CLOSE,
    SUPPORT_OPEN,
    SUPPORT_SET_POSITION,
    SUPPORT_STOP,
    CoverEntity,
)
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

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
    for c in api.covers:

        new_entities.append(HomeServerCover(c, api))
    logger.info("Found %d covers", len(new_entities))
    if new_entities:
        async_add_devices(new_entities)


class HomeServerCover(CoverEntity):
    def __init__(self, c: Accessory, api: HomeServerHass) -> None:
        super().__init__()
        self._cover = c
        self._api = api
        self._value = 0
        logger.info("%s", c.data_points)
        self._features = 0

        # Find the covering with the Position handle
        tmp = [x for x in c.data_points if x["name"] == "Position"]
        if len(tmp):
            self._position_uid = tmp[0]["uid"]
            self._features = self._features | SUPPORT_SET_POSITION
        else:
            self._position_uid = None

        tmp = [x for x in c.data_points if x["name"] == "Up-Down"]
        if len(tmp):
            self._up_down_uid = tmp[0]["uid"]
            self._features = self._features | SUPPORT_OPEN | SUPPORT_CLOSE

        tmp = [x for x in c.data_points if x["name"] == "Step-Up-Down"]
        if len(tmp):
            self._stop_uid = tmp[0]["uid"]
            self._features = self._features | SUPPORT_STOP

    @property
    def unique_id(self) -> typing.Optional[str]:
        return self._cover.uid

    @property
    def device_id(self) -> typing.Optional[str]:
        return self.unique_id

    @property
    def name(self) -> typing.Optional[str]:
        return f"{self._cover.display_name} ({self._cover.location})"

    @property
    def device_class(self) -> typing.Optional[str]:
        return DEVICE_CLASS_SHADE

    @property
    def supported_features(self) -> int:
        return self._features

    @property
    def is_closed(self) -> typing.Optional[bool]:
        return None

    @property
    def current_cover_position(self) -> typing.Optional[int]:
        return self._value

    @property
    def device_info(self) -> typing.Optional[DeviceInfo]:
        info = {
            "identifiers": {(DOMAIN, self.device_id)},
            "name": self.name,
            "manufacturer": "Gira HomeServer Passthrough",
            "via_device": (DOMAIN, "HomeServer"),
        }
        return info

    async def async_set_cover_position(self, **kwargs):
        """Move the cover to a specific position."""
        val = kwargs[ATTR_POSITION]
        logger.debug("Set position %s", val)
        await self._api.set_value(self._position_uid, val)

    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        await self._api.set_value(self._up_down_uid, 0)

    async def async_close_cover(self, **kwargs):
        """Close cover."""
        await self._api.set_value(self._up_down_uid, 1)

    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        await self._api.set_value(self._stop_uid, 1)

    async def async_update(self) -> None:
        # logger.info("Async update")
        if self._position_uid:
            tmp = await self._api.get_value(self._position_uid)
            logger.debug("Fetching for position %s %d", self._position_uid, tmp)
            self._value = tmp
