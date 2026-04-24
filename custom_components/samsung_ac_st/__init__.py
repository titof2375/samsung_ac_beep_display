"""Samsung AC SmartThings — OAuth2, refresh automatique du token."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.config_entry_oauth2_flow import (
    OAuth2Session,
    async_get_config_entry_implementation,
)

from .api import SmartThingsApiClient, SmartThingsAuthError, SmartThingsConnectionError
from .const import DOMAIN
from .coordinator import SamsungAcCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["climate", "switch", "sensor", "select"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    try:
        implementation = await async_get_config_entry_implementation(hass, entry)
    except KeyError:
        # L'entrée a été créée sans OAuth2 — demande une re-authentification
        raise ConfigEntryAuthFailed(
            "Configuration OAuth2 incomplète. Veuillez supprimer et reconfigurer l'intégration."
        )

    oauth_session = OAuth2Session(hass, entry, implementation)

    async def get_token() -> str:
        """Retourne un access_token toujours valide (HA le rafraîchit si besoin)."""
        await oauth_session.async_ensure_token_valid()
        return oauth_session.token[CONF_ACCESS_TOKEN]

    session = async_get_clientsession(hass)
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
