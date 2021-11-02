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
from homeassistant.components.switch import SwitchEntity
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

    covers = [HomeServerSwitch(l, api) for l in api.switches]

    # Add the entities to Home Asssitant
    add_entities(covers)


class HomeServerSwitch(GiraEntity, SwitchEntity):
    def __init__(self, data: dict, api: HomeServerV2) -> None:
        GiraEntity.__init__(self, data, api)
        SwitchEntity.__init__(self)
        logger.info("Switch %s", data)
        self._attr_unique_id = data["address"][0]
        self._attr_address = data["address"][0]
        self._attr_state_address = data["state_address"][0]
        self._attr_switch_address = data["address"][0]
        self._attr_is_on = False

        self._attr_api.add_entity(self._attr_address, self)

    def should_poll(self) -> bool:
        return False

    async def handle_cmd(self, cmd: dict) -> None:
        val = cmd["value"]
        if val == 1 and not self._attr_is_on:
            self._attr_is_on = True
            self.schedule_update_ha_state()
        if val == 0 and self._attr_is_on:
            self._attr_is_on = False
            self.schedule_update_ha_state()

    async def async_turn_on(self, **kwargs):
        # Changing brightness will turn the lamp on as well
        if not self._attr_is_on:
            cmd = create_cmd(to_ga(self._attr_address), 1)
            asyncio.create_task(self._attr_api.send_command(cmd))
            self._attr_is_on = True

    async def async_turn_off(self, **kwargs: typing.Any) -> None:
        if self._attr_is_on:
            cmd = create_cmd(to_ga(self._attr_address), 0)
            asyncio.create_task(self._attr_api.send_command(cmd))
            self._attr_is_on = False
