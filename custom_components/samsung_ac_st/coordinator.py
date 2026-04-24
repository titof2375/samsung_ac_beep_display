"""DataUpdateCoordinator for Samsung AC ST."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SmartThingsApiClient, SmartThingsConnectionError
from .const import DOMAIN, POLL_INTERVAL

_LOGGER = logging.getLogger(__name__)


class SamsungAcCoordinator(DataUpdateCoordinator[dict]):
    """Polls SmartThings every 30s for all AC devices."""

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
        self.devices = devices  # [{device_id, label, capabilities}]

    async def _async_update_data(self) -> dict:
        """Returns {device_id: status_dict} for all AC devices."""
        result: dict = {}
        for dev in self.devices:
            did = dev["device_id"]
            try:
                result[did] = await self.client.get_status(did)
            except SmartThingsConnectionError as err:
                raise UpdateFailed(f"SmartThings unreachable: {err}") from err
        return result
