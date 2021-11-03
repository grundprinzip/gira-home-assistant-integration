import asyncio
from datetime import timedelta
import logging
from os import name
import typing
from custom_components.girahs.entity import GiraEntity

from homeassistant import core
from homeassistant import config_entries
from homeassistant.components import binary_sensor
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
    logger.info("Setting up binary sensor")
    api: HomeServerV2 = hass.data[DOMAIN]["api"]

    entities = [HomeServerBinarySensor(l, api) for l in api.binary_sensors]

    # Add the entities to Home Asssitant
    add_entities(entities)


class HomeServerBinarySensor(GiraEntity, binary_sensor.BinarySensorEntity):

  def __init__(self, data: dict, api: "HomeServerV2") -> None:
      GiraEntity.__init__(self, data, api)
      binary_sensor.BinarySensorEntity.__init__(self)

      self._attr_address = data["state_address"][0]
      self._attr_device_class = data["device_class"]

      self._attr_api.add_entity(self._attr_address, self)

  async def handle_cmd(self, cmd: dict) -> None:
        val = cmd["value"]
        if val != self._attr_is_on:
          self._attr_is_on = val
          if self.hass is None:
                return
          self.schedule_update_ha_state()

