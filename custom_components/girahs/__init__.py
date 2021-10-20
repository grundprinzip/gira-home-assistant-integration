from custom_components.girahs.gira import HomeServerHass
from homeassistant import config_entries, core
from homeassistant.helpers import device_registry
from .const import DOMAIN


async def async_setup_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
):
    home_server = HomeServerHass(hass, entry)
    if not await home_server.setup():
        return False
    dr = await device_registry.async_get_registry(hass)
    dr.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "homeserver")},
        manufacturer="Gira",
        name="HomeServer",
        model="4",
    )
    return True
