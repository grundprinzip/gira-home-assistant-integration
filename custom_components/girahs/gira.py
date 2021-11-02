import asyncio
import logging
import json
import websockets
from websockets.exceptions import ConnectionClosed

from custom_components.girahs.entity import GiraEntity

try:
    from .const import DOMAIN
except ImportError:
    from const import DOMAIN

# from const import DOMAIN

from homeassistant import config_entries, core, exceptions, helpers
from homeassistant.helpers.entity import Entity
from homeassistant.const import CONF_HOST, CONF_USERNAME, CONF_PASSWORD

logger = logging.getLogger(__name__)


class HomeServerV2(object):
    def __init__(self, config: config_entries.ConfigType) -> None:
        self._host = config[DOMAIN][CONF_HOST]
        self.switches = config[DOMAIN]["switch"]
        self.covers = config[DOMAIN]["cover"]
        self.lights = config[DOMAIN]["light"]
        self.sensors = config[DOMAIN]["sensor"]
        self.climates = config[DOMAIN]["climate"]
        self.weathers = config[DOMAIN]["weather"]
        self._entities: dict[str, GiraEntity] = {}

    def add_entity(self, address: str, entity: GiraEntity) -> None:
        logger.debug("Adding entity %s %s", address, entity)
        self._entities[address] = entity
        pass

    async def send_command(self, cmd: dict) -> None:
        data = json.dumps(cmd)
        logger.debug("Sending event: %s", data)
        await self._websocket.send(data)

    async def handle_value_changed(self, cmd: dict) -> None:
        """
        Dict in the form of {cmd: type, ga: address, value: val}
        """
        if not "ga" in cmd:
            return

        ga = int(cmd["ga"])
        x = int(ga / 2048)
        y = int((ga - x * 2048) / 256)
        z = int((ga - x * 2048 - y * 256))
        address = f"{x}/{y}/{z}"
        cmd["address"] = address

        logger.info("Received message: %s", cmd)

        if address in self._entities:
            # Add the translated address to the object and defer execution into a new task
            # to avoid blocking the IO.
            asyncio.create_task(self._entities[address].handle_cmd(cmd))

    async def process_gira_events(self) -> None:
        """Connect to the homeserver and prcess inbound messages.

        The loop will automatically reconnect if something breaks."""
        async for websocket in websockets.connect(
            f"ws://{self._host}/cogw?AUTHORIZATION="
        ):
            self._websocket = websocket
            try:
                while True:
                    d = await websocket.recv()
                    asyncio.create_task(self.handle_value_changed(json.loads(d)))
            except ConnectionClosed:
                continue

    async def connect(self) -> None:
        asyncio.create_task(self.process_gira_events())
