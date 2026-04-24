"""Config flow + reauth flow for Samsung AC SmartThings."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SmartThingsApiClient, SmartThingsAuthError, SmartThingsConnectionError
from .const import CONF_TOKEN, DOMAIN

_LOGGER = logging.getLogger(__name__)

TOKEN_SCHEMA = vol.Schema({vol.Required(CONF_TOKEN): str})


async def _validate(hass, token: str) -> str | None:
    """Return error key or None if valid."""
    client = SmartThingsApiClient(token.strip(), async_get_clientsession(hass))
    try:
        await client.validate_token()
        return None
    except SmartThingsAuthError:
        return "invalid_auth"
    except SmartThingsConnectionError:
        return "cannot_connect"
    except Exception:
        _LOGGER.exception("Unexpected error during SmartThings validation")
        return "unknown"


class SamsungAcConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Initial setup: ask for SmartThings PAT token."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            token = user_input[CONF_TOKEN].strip()
            error = await _validate(self.hass, token)
            if error:
                errors["base"] = error
            else:
                await self.async_set_unique_id(token[:8])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Samsung AC (SmartThings)",
                    data={CONF_TOKEN: token},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=TOKEN_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return SamsungAcOptionsFlow(config_entry)


class SamsungAcOptionsFlow(config_entries.OptionsFlow):
    """Allow token update from the Options menu."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            token = user_input[CONF_TOKEN].strip()
            error = await _validate(self.hass, token)
            if error:
                errors["base"] = error
            else:
                self.hass.config_entries.async_update_entry(
                    self._config_entry, data={CONF_TOKEN: token}
                )
                return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(
                    CONF_TOKEN,
                    default=self._config_entry.data.get(CONF_TOKEN, ""),
                ): str
            }),
            errors=errors,
        )


class SamsungAcReauthFlow(config_entries.ConfigEntryBaseFlow):
    """Re-authentication flow shown when token is rejected (401)."""

    async def async_step_reauth(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            token = user_input[CONF_TOKEN].strip()
            error = await _validate(self.hass, token)
            if error:
                errors["base"] = error
            else:
                entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
                self.hass.config_entries.async_update_entry(
                    entry, data={CONF_TOKEN: token}
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=TOKEN_SCHEMA,
            errors=errors,
            description_placeholders={
                "message": "Votre token SmartThings a expiré. Créez-en un nouveau sur account.smartthings.com/tokens (sans date d'expiration)."
            },
        )
