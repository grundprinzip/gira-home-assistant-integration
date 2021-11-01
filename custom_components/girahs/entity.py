import abc
from typing import Optional

from homeassistant.helpers import entity


class GiraEntity(entity.Entity):
    def __init__(self) -> None:
        super().__init__()
        self._attr_address: Optional[str]
        self._attr_state_address: Optional[str]

    async def handle_cmd(self, cmd: dict) -> None:
        raise NotImplementedError("Not implemented")
