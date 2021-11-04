import logging
import typing
from custom_components.girahs.entity import GiraEntity

from homeassistant import core
from homeassistant import config_entries
from homeassistant.components import sensor
from homeassistant.const import DEVICE_CLASS_ILLUMINANCE, DEVICE_CLASS_TEMPERATURE
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

    entities = [HomeServerSensor(l, api) for l in api.sensors]

    # Add the entities to Home Asssitant
    add_entities(entities)


class HomeServerSensor(GiraEntity, sensor.SensorEntity):
    def __init__(self, data: dict, api: "HomeServerV2") -> None:
        GiraEntity.__init__(self, data, api)
        sensor.SensorEntity.__init__(self)

        self._attr_unique_id = data["state_address"][0]
        self._attr_address = data["state_address"][0]
        self._attr_device_class = self._to_device_class(data["type"])
        self._attr_state_class = data["state_class"] if "state_class" in data else None

        self._attr_api.add_entity(self._attr_address, self)

    def _to_device_class(self, type):
        if type == "common_temperature":
            return DEVICE_CLASS_TEMPERATURE
        if type == "luminous_flux":
            return DEVICE_CLASS_ILLUMINANCE
        return None

    async def handle_cmd(self, cmd: dict) -> None:
        val = cmd["value"]
        if val != self._attr_native_value:
            self._attr_native_value = val
            if self.hass is None:
                return
            self.schedule_update_ha_state()
