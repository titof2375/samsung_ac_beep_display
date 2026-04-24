"""DataUpdateCoordinator for Samsung AC Beep & Display."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SmartThingsApiClient, SmartThingsConnectionError
from .const import DOMAIN, POLL_INTERVAL

_LOGGER = logging.getLogger(__name__)


class SamsungAcCoordinator(DataUpdateCoordinator):
    """Polls SmartThings for display/beep state of all AC devices."""

    def __init__(self, hass: HomeAssistant, client: SmartThingsApiClient, devices: list[dict]) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=POLL_INTERVAL),
        )
        self.client = client
        self.devices = devices  # list of {device_id, label, capabilities}

    async def _async_update_data(self) -> dict:
        """Fetch status for all AC devices. Returns {device_id: {display, beep}}."""
        result = {}
        for dev in self.devices:
            did = dev["device_id"]
            try:
                result[did] = await self.client.get_device_status(did)
            except SmartThingsConnectionError as err:
                raise UpdateFailed(f"SmartThings unreachable: {err}") from err
        return result
