"""Config flow for Samsung AC SmartThings."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SmartThingsApiClient, SmartThingsAuthError, SmartThingsConnectionError
from .const import CONF_TOKEN, DOMAIN

_LOGGER = logging.getLogger(__name__)


class SamsungAcConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Setup flow: just ask for the SmartThings PAT token."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            token = user_input[CONF_TOKEN].strip()
            client = SmartThingsApiClient(token, async_get_clientsession(self.hass))
            try:
                await client.validate_token()
            except SmartThingsAuthError:
                errors["base"] = "invalid_auth"
            except SmartThingsConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error")
                errors["base"] = "unknown"

            if not errors:
                await self.async_set_unique_id(token[:8])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Samsung AC (SmartThings)",
                    data={CONF_TOKEN: token},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_TOKEN): str}),
            errors=errors,
        )
