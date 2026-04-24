"""Config flow pour Samsung AC SmartThings — token personnel (PAT)."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_TOKEN, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema({
    vol.Required(CONF_TOKEN): str,
})


class SamsungAcConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow — saisie du token personnel SmartThings."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            token = user_input[CONF_TOKEN].strip()
            session = async_get_clientsession(self.hass)
            try:
                async with session.get(
                    "https://api.smartthings.com/v1/devices",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as r:
                    if r.status == 401:
                        errors["base"] = "invalid_auth"
                    elif r.status != 200:
                        errors["base"] = "cannot_connect"
            except aiohttp.ClientError:
                errors["base"] = "cannot_connect"

            if not errors:
                await self.async_set_unique_id(f"samsung_ac_{token[:8]}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Samsung AC SmartThings",
                    data={CONF_TOKEN: token},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Re-saisie du token si révoqué."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is None:
            return self.async_show_form(step_id="reauth_confirm")
        return await self.async_step_user()
