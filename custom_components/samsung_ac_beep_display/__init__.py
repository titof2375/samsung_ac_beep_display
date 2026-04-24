"""Samsung AC Beep & Display — HACS integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SmartThingsApiClient, SmartThingsConnectionError
from .const import CONF_TOKEN, DOMAIN
from .coordinator import SamsungAcCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["switch"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    token = entry.data[CONF_TOKEN]
    session = async_get_clientsession(hass)
    client = SmartThingsApiClient(token, session)

    try:
        devices = await client.get_ac_devices()
    except SmartThingsConnectionError as err:
        _LOGGER.error("Cannot connect to SmartThings: %s", err)
        return False

    if not devices:
        _LOGGER.warning("No Samsung AC devices found in SmartThings")

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
