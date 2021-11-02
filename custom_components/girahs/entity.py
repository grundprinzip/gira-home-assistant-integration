import abc
from typing import Optional

# from custom_components.girahs.gira import HomeServerV2

from homeassistant.helpers import entity


class GiraEntity(entity.Entity):
    def __init__(self, data: dict, api: "HomeServerV2") -> None:
        super().__init__()
        self._attr_address: Optional[str]
        self._attr_state_address: Optional[str]

        # Setup API and name
        self._attr_api = api
        self._attr_name = data["name"]

    async def handle_cmd(self, cmd: dict) -> None:
        raise NotImplementedError("Not implemented")
