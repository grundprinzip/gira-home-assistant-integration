import asyncio
import logging
import typing
import json
import websockets
from websockets.exceptions import ConnectionClosed

from collections import UserDict
from functools import partial
from requests.auth import HTTPBasicAuth
from custom_components.girahs.entity import GiraEntity

from homeassistant.helpers import entity


try:
    from .const import DOMAIN
except ImportError:
    from const import DOMAIN

# from const import DOMAIN

from homeassistant import config_entries, core, exceptions, helpers
from homeassistant.helpers.entity import Entity
from homeassistant.const import CONF_HOST, CONF_USERNAME, CONF_PASSWORD

_LOG = logging.getLogger(__name__)


class AuthException(Exception):
    pass


class FetchException(Exception):
    pass


class Accessory(object):
    def __init__(
        self,
        uid: str,
        display_name: str,
        location: str,
        channel_type: str,
        data_points: typing.List,
        trade: str,
    ) -> None:
        super().__init__()
        self._uid = uid
        self._display_name = display_name
        self._location = location
        self._channel_type = channel_type
        self._data_points = data_points
        self._trade = trade

    @property
    def uid(self) -> str:
        return self._uid

    @property
    def display_name(self) -> str:
        return self._display_name

    @property
    def location(self) -> str:
        return self._location

    @property
    def channel_type(self) -> str:
        return self._channel_type

    @property
    def data_points(self) -> typing.List:
        return self._data_points

    @property
    def trade(self) -> str:
        return self._trade

    def __repr__(self) -> str:
        return f"<Accessory: {self.display_name}({self.uid})@{self.location}>"


AccessoryList = list[Accessory]
V = typing.TypeVar("V", str, int, float, bool, None)


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
        _LOG.info("Adding entity %s %s", address, entity)
        self._entities[address] = entity
        pass

    async def send_command(self, cmd: dict) -> None:
        await self._websocket.send(json.dumps(cmd))

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

        if address in self._entities:
            # Add the translated address to the object and defer execution into a new task
            # to avoid blocking the IO.
            cmd["address"] = address
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
