"""DataUpdateCoordinator for Samsung AC ST."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SmartThingsApiClient, SmartThingsAuthError, SmartThingsConnectionError
from .const import DOMAIN, POLL_INTERVAL

_LOGGER = logging.getLogger(__name__)


class SamsungAcCoordinator(DataUpdateCoordinator[dict]):
    """Polls SmartThings every 30s. Triggers re-auth if token expires."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: SmartThingsApiClient,
        devices: list[dict],
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=POLL_INTERVAL),
        )
        self.client = client
        self.devices = devices

    async def _async_update_data(self) -> dict:
        result: dict = {}
        for dev in self.devices:
            did = dev["device_id"]
            try:
                result[did] = await self.client.get_status(did)
            except SmartThingsAuthError as err:
                # Token expiré → HA affiche une notification et ouvre le flux de re-auth
                raise ConfigEntryAuthFailed(str(err)) from err
            except SmartThingsConnectionError as err:
                raise UpdateFailed(f"SmartThings unreachable: {err}") from err
        return result
