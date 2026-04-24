"""Config flow OAuth2 pour Samsung AC SmartThings."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.config_entry_oauth2_flow import AbstractOAuth2FlowHandler

from .application_credentials import SCOPES
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class SamsungAcConfigFlow(AbstractOAuth2FlowHandler, domain=DOMAIN):
    """Config flow OAuth2 — HA gère le refresh automatique du token."""

    DOMAIN = DOMAIN
    VERSION = 1

    @property
    def logger(self) -> logging.Logger:
        return _LOGGER

    @property
    def extra_authorize_data(self) -> dict:
        return {"scope": " ".join(SCOPES)}

    async def async_oauth_create_entry(self, data: dict[str, Any]) -> dict:
        """Appelé après autorisation OAuth2 réussie."""
        return self.async_create_entry(
            title="Samsung AC (SmartThings)",
            data=data,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> dict:
        """Re-authentification si le refresh token est révoqué."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        if user_input is None:
            return self.async_show_form(step_id="reauth_confirm")
        return await self.async_step_user()
