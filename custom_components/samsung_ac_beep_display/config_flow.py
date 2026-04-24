"""Config flow for Samsung AC Beep & Display."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SmartThingsApiClient, SmartThingsAuthError, SmartThingsConnectionError
from .const import CONF_TOKEN, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_TOKEN): str,
    }
)


class SamsungAcConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow for Samsung AC Beep & Display."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            token = user_input[CONF_TOKEN].strip()
            session = async_get_clientsession(self.hass)
            client = SmartThingsApiClient(token, session)

            try:
                await client.validate_token()
            except SmartThingsAuthError:
                errors["base"] = "invalid_auth"
            except SmartThingsConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during SmartThings validation")
                errors["base"] = "unknown"

            if not errors:
                await self.async_set_unique_id(token[:8])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Samsung AC Beep & Display",
                    data={CONF_TOKEN: token},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )
