import asyncio
from datetime import timedelta
import logging
from os import name
import typing
from custom_components.girahs.entity import GiraEntity
from custom_components.girahs.helper import create_cmd, to_ga, to_gira_pct, to_hass_byte

from homeassistant import core
from homeassistant import config_entries
from homeassistant.components import cover
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
    logger.debug("Setting up cover")
    api: HomeServerV2 = hass.data[DOMAIN]["api"]
    covers = [HomeServerCover(l, api) for l in api.covers]

    # Add the entities to Home Asssitant
    add_entities(covers)


class HomeServerCover(GiraEntity, CoverEntity):
    def __init__(self, cover: dict, api: HomeServerV2) -> None:
        GiraEntity.__init__(self, cover, api)
        CoverEntity.__init__(self)
        logger.debug("Cover %s", cover)
        self._attr_unique_id = cover["position_state_address"][0]
        self._attr_move_long_address = cover["move_long_address"][0]
        self._attr_move_short_address = cover["move_short_address"][0]
        self._attr_position_address = cover["position_address"][0]
        self._attr_stop_address = cover["stop_address"][0]

        # Setup device class and supported features
        self._attr_is_closed = None
        self._attr_device_class = DEVICE_CLASS_SHADE
        self._attr_supported_features = (
            SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_STOP | SUPPORT_SET_POSITION
        )

        # Register for updates
        api.add_entity(cover["position_state_address"][0], self)

    def should_poll(self) -> bool:
        return False

    async def handle_cmd(self, cmd: dict) -> None:
        """This method is called for all registered state addresses that should be
        observed"""
        val = cmd["value"]
        if val != self._attr_current_cover_position:
            logger.info("Updating state for %s", self._attr_position_address)
            self._attr_current_cover_position = val
            if self.hass is None:
                return
            self.schedule_update_ha_state()

    async def async_open_cover(self, **kwargs):
        cmd = create_cmd(to_ga(self._attr_move_long_address), -1)
        asyncio.create_task(self._attr_api.send_command(cmd))

    async def async_close_cover(self, **kwargs):
        cmd = create_cmd(to_ga(self._attr_move_long_address), 1)
        asyncio.create_task(self._attr_api.send_command(cmd))

    async def async_set_cover_position(self, **kwargs):
        val = kwargs[ATTR_POSITION]
        cmd = create_cmd(to_ga(self._attr_position_address), val)
        asyncio.create_task(self._attr_api.send_command(cmd))

    async def async_stop_cover(self, **kwargs):
        cmd = create_cmd(to_ga(self._attr_stop_address), 0)
        asyncio.create_task(self._attr_api.send_command(cmd))
