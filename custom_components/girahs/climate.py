from datetime import timedelta
import logging
from os import name
import typing
from custom_components.girahs.entity import GiraEntity

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
    logger.debug("Setting up climate")
    api: HomeServerV2 = hass.data[DOMAIN]["api"]

    accs = [HomeServerClimate(l, api) for l in api.climates]

    # Add the entities to Home Asssitant
    add_entities(accs)


class HomeServerClimate(GiraEntity, ClimateEntity):
    def __init__(self, c: dict, api: HomeServerV2) -> None:
        GiraEntity.__init__(self, c, api)
        ClimateEntity.__init__(self)
        self._attr_unique_id = c["temperature_address"][0]
        self._attr_temperature_address = c["temperature_address"][0]
        self._attr_target_temperature_state_address = c[
            "target_temperature_state_address"
        ][0]

        self._attr_hvac_mode = HVAC_MODE_HEAT
        self._attr_hvac_modes = [HVAC_MODE_HEAT]
        self._attr_temperature_unit = TEMP_CELSIUS
        self._attr_supported_features = SUPPORT_TARGET_TEMPERATURE

        # Register update handler
        self._attr_api.add_entity(self._attr_temperature_address, self)
        self._attr_api.add_entity(self._attr_target_temperature_state_address, self)

    def should_poll(self) -> bool:
        return False

    async def handle_cmd(self, cmd: dict) -> None:
        """This method is called for all registered state addresses that should be
        observed"""
        val = cmd["value"]
        a = cmd["address"]

        if (
            a == self._attr_temperature_address
            and val != self._attr_current_temperature
        ):
            self._attr_current_temperature = val
            self.schedule_update_ha_state()

        if (
            a == self._attr_target_temperature_state_address
            and val != self._attr_target_temperature
        ):
            self._attr_target_temperature = val
            self.schedule_update_ha_state()

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        logger.info("%s", kwargs)
        # self._api.set_value(self._functions["Set-Point"], kwargs[ATTR_TEMPERATURE])
