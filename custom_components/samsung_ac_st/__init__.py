"""Samsung AC SmartThings — OAuth2 avec refresh automatique du token."""
from __future__ import annotations

import base64
import logging
import time

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SmartThingsApiClient, SmartThingsAuthError, SmartThingsConnectionError
from .const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_REFRESH_TOKEN,
    CONF_TOKEN,
    CONF_TOKEN_EXPIRES_AT,
    DOMAIN,
    ST_TOKEN_URL,
)
from .coordinator import SamsungAcCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["climate", "switch", "sensor", "select", "button"]

# Marge avant expiration (5 minutes)
_TOKEN_REFRESH_MARGIN = 300


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = async_get_clientsession(hass)

    if CONF_REFRESH_TOKEN in entry.data:
        # Entrée OAuth2 : refresh automatique du token
        get_token = _make_oauth_token_getter(hass, entry, session)
    else:
        # Entrée ancienne (PAT direct) — rétrocompatibilité
        pat = entry.data[CONF_TOKEN]

        async def get_token() -> str:
            return pat

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
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded


def _make_oauth_token_getter(hass: HomeAssistant, entry: ConfigEntry, session):
    """Retourne une coroutine qui fournit un access_token valide, en le rafraîchissant si nécessaire."""

    async def get_token() -> str:
        now = time.time()
        expires_at = entry.data.get(CONF_TOKEN_EXPIRES_AT, 0)

        if now >= expires_at - _TOKEN_REFRESH_MARGIN:
            _LOGGER.debug("Access token expiré, rafraîchissement en cours…")
            new_data = await _refresh_access_token(
                session,
                entry.data[CONF_CLIENT_ID],
                entry.data[CONF_CLIENT_SECRET],
                entry.data[CONF_REFRESH_TOKEN],
            )
            if new_data is None:
                raise SmartThingsAuthError(
                    "Impossible de rafraîchir le token OAuth — re-authentification requise"
                )

            updated = dict(entry.data)
            updated[CONF_TOKEN] = new_data["access_token"]
            updated[CONF_REFRESH_TOKEN] = new_data.get(
                "refresh_token", entry.data[CONF_REFRESH_TOKEN]
            )
            updated[CONF_TOKEN_EXPIRES_AT] = now + new_data.get("expires_in", 86400)

            hass.config_entries.async_update_entry(entry, data=updated)
            _LOGGER.info("Token OAuth rafraîchi, expire dans %ds", new_data.get("expires_in", 86400))
            return updated[CONF_TOKEN]

        return entry.data[CONF_TOKEN]

    return get_token


async def _refresh_access_token(
    session: aiohttp.ClientSession,
    client_id: str,
    client_secret: str,
    refresh_token: str,
) -> dict | None:
    """Appelle SmartThings pour renouveler l'access_token via le refresh_token."""
    credentials = f"{client_id}:{client_secret}"
    auth_header = base64.b64encode(credentials.encode()).decode()

    try:
        async with session.post(
            ST_TOKEN_URL,
            headers={
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            timeout=aiohttp.ClientTimeout(total=30),
        ) as r:
            if r.status == 401:
                _LOGGER.error("Refresh token invalide ou révoqué (401)")
                return None
            if r.status != 200:
                body = await r.text()
                _LOGGER.error("Rafraîchissement token échoué %s: %s", r.status, body)
                return None
            return await r.json()
    except aiohttp.ClientError as err:
        _LOGGER.error("Erreur réseau lors du rafraîchissement du token: %s", err)
        return None
