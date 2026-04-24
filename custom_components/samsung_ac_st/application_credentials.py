"""Application credentials platform for Samsung AC SmartThings."""
from __future__ import annotations

import logging
from json import JSONDecodeError
from typing import cast

from aiohttp import BasicAuth, ClientError

from homeassistant.components.application_credentials import (
    AuthImplementation,
    AuthorizationServer,
    ClientCredential,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.config_entry_oauth2_flow import AbstractOAuth2Implementation

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

AUTHORIZE_URL = "https://api.smartthings.com/oauth/authorize"
TOKEN_URL = "https://auth-global.api.smartthings.com/oauth/token"

# Scopes requis pour lire + contrôler les appareils
SCOPES = ["r:devices:*", "x:devices:*", "l:devices"]


async def async_get_auth_implementation(
    hass: HomeAssistant,
    auth_domain: str,
    credential: ClientCredential,
) -> AbstractOAuth2Implementation:
    return SmartThingsOAuth2Implementation(
        hass,
        DOMAIN,
        credential,
        authorization_server=AuthorizationServer(
            authorize_url=AUTHORIZE_URL,
            token_url=TOKEN_URL,
        ),
    )


class SmartThingsOAuth2Implementation(AuthImplementation):
    """OAuth2 pour SmartThings — même implémentation que l'intégration officielle HA."""

    @property
    def extra_authorize_data(self) -> dict:
        return {"scope": " ".join(SCOPES)}

    async def _token_request(self, data: dict) -> dict:
        session = async_get_clientsession(self.hass)
        resp = await session.post(
            self.token_url,
            data=data,
            auth=BasicAuth(self.client_id, self.client_secret),
        )
        if resp.status >= 400:
            try:
                error_response = await resp.json()
            except (ClientError, JSONDecodeError):
                error_response = {}
            _LOGGER.error(
                "Erreur token SmartThings (%s): %s",
                error_response.get("error", "unknown"),
                error_response.get("error_description", "unknown error"),
            )
            resp.raise_for_status()
        return cast(dict, await resp.json())
