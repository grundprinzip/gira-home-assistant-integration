from collections import UserDict
import json
import requests
import logging
import typing
from requests.auth import HTTPBasicAuth

from homeassistant import config_entries, core
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
    ) -> None:
        super().__init__()
        self._uid = uid
        self._display_name = display_name
        self._location = location
        self._channel_type = channel_type
        self._data_points = data_points

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

    def __repr__(self) -> str:
        return f"<Accessory: {self.display_name}({self.uid})@{self.location}>"


AccessoryList = list[Accessory]
V = typing.TypeVar("V", str, int, float, bool, None)


class HomeServer(object):

    CLIENT = "HomeAssistant"

    def __init__(self, username, password, host) -> None:
        super().__init__()
        # Create empty token
        self.token = ""
        self.username = username
        self.password = password
        self.host = host

    def login(self) -> bool:
        """Login to the Gira HS and obtain a new toke for the application"""
        endpoint = f"https://{self.host}/api/clients"
        _LOG.info(f"Connecting to: {endpoint} {self.username} {self.password}")
        _LOG.info(f'{{client:"{HomeServer.CLIENT}"}}')
        response = requests.post(
            endpoint,
            data=json.dumps({"client": HomeServer.CLIENT}),
            auth=HTTPBasicAuth(self.username, self.password),
            verify=False,
        )
        if response.status_code != 200:
            # _LOG.error(f"Error loging in {response.text}")
            raise AuthException(f"Could not login to Gira HS at {self.host}")
        data = response.json()
        self.token = data["token"]
        # _LOG.debug("Received token from HS.")
        return True

    def fetchAllObjects(self) -> None:
        """Fetches all configuration objects from Gira HS. After all data is fetched,
        the data can be transformed into local objects."""

        endpoint = f"https://{self.host}/api/uiconfig"
        response = requests.get(
            endpoint,
            params={"token": self.token, "expand": "parameters,locations,trades"},
            verify=False,
        )
        if response.status_code != 200:
            _LOG.error(f"Error fetching KOs {response.text}")
            raise FetchException("Could not fetch KOs")
        self.data = response.json()

    def transformAccessories(self) -> AccessoryList:
        """Transforms the local list of acessories into items recognizable by the system"""
        _LOG.debug("Transforming all accessories")
        location_map = self.buildLocationMap(self.data["locations"])
        result = []
        for fn in self.data["functions"]:
            loc = location_map.get(fn["uid"], "None")
            result.append(
                Accessory(
                    fn["uid"],
                    fn["displayName"],
                    loc,
                    fn["channelType"],
                    fn["dataPoints"],
                )
            )
        return result

    def buildLocationMap(self, data: typing.List, parent="") -> typing.Dict:
        """Recursively processes the input map to build a proper UID to location naming"""
        prefix = parent + "/" if len(parent) > 0 else parent
        result = {}
        for d in data:
            new_parent = f"{prefix}{d['displayName']}"
            for f in d["functions"]:
                result[f] = new_parent
            tmp = self.buildLocationMap(d["locations"], new_parent)
            result.update(tmp)
        return result

    def getValue(self, uid: str) -> V:
        endpoint = f"https://{self.host}/api/values/{uid}"
        response = requests.get(endpoint, params={"token": self.token}, verify=False)
        if response.status_code != 200:
            raise FetchException(f"Could not load value for {uid}")
        for v in response.json()["values"]:
            if v["uid"] == uid:
                return v["value"]
        return None

    def setValue(self, uid: str, value: V) -> None:
        endpoint = f"https://{self.host}/api/values/{uid}"
        response = requests.put(
            endpoint, data={"value": value}, params={"token": self.token}, verify=False
        )
        if response.status_code != 200:
            raise FetchException(f"Could not load value for {uid}")
        for v in response.json()["values"]:
            if v["uid"] == uid:
                return v["value"]
        return None


class HomeServerHass:
    def __init__(
        self, hass: core.HomeAssistant, entry: config_entries.ConfigEntry
    ) -> None:
        self.api = HomeServer(
            entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD], entry.data[CONF_HOST]
        )
        self._hass = hass
        self._config = entry
        self._accessories: typing.List[Accessory]

    async def setup(self) -> bool:
        """Do the intiial setup of the HomeServer"""
        # Login.
        if not await self._hass.async_add_executor_job(self.api.login):
            return False
        # Fetch all known items.
        await self._hass.async_add_executor_job(self.api.fetchAllObjects)
        # Transform the items in things we can reason about.
        self._accessories = self.api.transformAccessories()
        return True


if __name__ == "__main__":
    import os

    logging.basicConfig(level=logging.DEBUG)
    logging.debug("Start...")
    logging.debug(f"Connecting with User : {os.environ.get('HS_USERNAME')}")
    hs = HomeServer(
        os.environ.get("HS_USERNAME"), os.environ.get("HS_PASSWORD"), "192.168.178.5"
    )
    hs.login()
    hs.fetchAllObjects()

    objs = hs.transformAccessories()
    for o in objs:
        if o.uid == "f287":
            fn = o.data_points[0]["uid"]
            print(hs.getValue(fn))

    # logging.debug(hs.transformAccessories())
