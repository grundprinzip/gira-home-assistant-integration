import typing
from .const import DEFAULT_HOST
from .gira import AuthException, HomeServer
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from . import DOMAIN
from homeassistant import config_entries
import voluptuous as vol
import logging

from homeassistant.const import CONF_USERNAME, CONF_PASSWORD, CONF_HOST

_LOGGER = logging.getLogger(__name__)

OptStrAnyMap = typing.TypeVar("OptStrAnyMap", dict[str, typing.Any], None)
OptStrStrMap = typing.TypeVar("OptStrStrMap", dict[str, str], None)


class GiraHomeAssistantIntegration(config_entries.ConfigFlow, domain=DOMAIN):
    """One simple configuration flow to configure the Gira HomeServer connection.

    TODO: reauth"""

    VERSION = 1

    def __init__(self) -> None:
        super().__init__()
        self._name = "GiraHomeServer"
        self._host: str
        self._username: str
        self._password: str
        self._gira: HomeServer

    async def init_home_server(self) -> typing.Optional[str]:
        """Initialize the connection and check if we can auth"""
        if not self._host or not self._username or not self._password:
            return "missing_config_value"

        g = HomeServer(self._username, self._password, self._host)
        try:
            await self.hass.async_add_executor_job(g.login)
            self._gira = g
            return None
        except AuthException:
            return "invalid_auth"
        except:
            return "unknown_error"

    async def async_step_user(self, user_input: OptStrAnyMap = None):
        """Configuration of the user."""
        if user_input is None:
            return self._show_setup_form_init()
        self._host = user_input[CONF_HOST]
        self._username = user_input[CONF_USERNAME]
        self._password = user_input[CONF_PASSWORD]

        if not (error := await self.init_home_server()):
            if await self.async_check_configured_entry():
                error = "already_configured"

        if error:
            return self._show_setup_form_init({"base": error})

        return self._async_create_entry()

    async def async_check_configured_entry(
        self,
    ) -> typing.Optional[config_entries.ConfigEntries]:
        """Check if entry is configured."""
        for entry in self._async_current_entries(include_ignore=False):
            if entry.data[CONF_HOST] == self._host:
                return entry
        return None

    @callback
    def _async_create_entry(self) -> FlowResult:
        """Async create flow handler entry."""
        return self.async_create_entry(
            title=self._name,
            data={
                CONF_HOST: self._host,
                CONF_PASSWORD: self._password,
                CONF_USERNAME: self._username,
            },
        )

    def _show_setup_form_init(self, errors: OptStrStrMap = None) -> FlowResult:
        """Show the setup form to the user."""
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_HOST, default=DEFAULT_HOST): str,
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors or {},
        )
