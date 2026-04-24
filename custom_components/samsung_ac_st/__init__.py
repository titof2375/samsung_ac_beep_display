"""Samsung AC SmartThings — authentification par token personnel (PAT)."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SmartThingsApiClient, SmartThingsAuthError, SmartThingsConnectionError
from .const import CONF_TOKEN, DOMAIN
from .coordinator import SamsungAcCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["climate", "switch", "sensor", "select"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    token = entry.data[CONF_TOKEN]
    session = async_get_clientsession(hass)

    # Le token PAT SmartThings ne expire pas — on le passe directement
    async def get_token() -> str:
        return token

    client = SmartThingsApiClient(session, get_token)

    try:
        devices = await client.get_ac_devices()
    except SmartThingsAuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except SmartThingsConnectionError as err:
        raise ConfigEntryNotReady(str(err)) from err

    if not devices:
        _LOGGER.warning("Aucun climatiseur Samsung trouvé dans SmartThings")

    coordinator = SamsungAcCoordinator(hass, client, devices)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded
