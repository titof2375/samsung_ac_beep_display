"""Config flow Samsung AC SmartThings — OAuth2 avec credentials fournis par l'utilisateur."""
from __future__ import annotations

import base64
import logging
import time
from typing import Any
from urllib.parse import quote

import aiohttp
import voluptuous as vol
from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.network import NoURLAvailableError, get_url

from .const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_REFRESH_TOKEN,
    CONF_TOKEN,
    CONF_TOKEN_EXPIRES_AT,
    DOMAIN,
    OAUTH_CALLBACK_PATH,
    OAUTH_SCOPES,
    ST_AUTH_URL,
    ST_TOKEN_URL,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema({
    vol.Required(CONF_CLIENT_ID): str,
    vol.Required(CONF_CLIENT_SECRET): str,
})


class SamsungAcOAuthCallbackView(HomeAssistantView):
    """Reçoit le code OAuth depuis SmartThings et continue le config flow."""

    url = OAUTH_CALLBACK_PATH
    name = "api:samsung_ac_st:oauth:callback"
    requires_auth = False

    async def get(self, request: web.Request) -> web.Response:
        hass = request.app["hass"]
        code = request.query.get("code")
        flow_id = request.query.get("state")

        if not code or not flow_id:
            return web.Response(
                text="<html><body>Paramètres manquants.</body></html>",
                content_type="text/html",
                status=400,
            )

        try:
            await hass.config_entries.flow.async_configure(
                flow_id, user_input={"code": code}
            )
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Erreur lors de la configuration OAuth: %s", err)
            return web.Response(
                text="<html><body>Erreur de configuration.</body></html>",
                content_type="text/html",
                status=500,
            )

        raise web.HTTPFound("/config/integrations")


class SamsungAcConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow OAuth2 pour Samsung AC SmartThings."""

    VERSION = 1

    def __init__(self) -> None:
        self._client_id: str | None = None
        self._client_secret: str | None = None
        self._redirect_uri: str | None = None
        self._oauth_url: str | None = None

    # ------------------------------------------------------------------
    # Étape 1 : saisie du client_id et client_secret
    # ------------------------------------------------------------------

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            client_id = user_input[CONF_CLIENT_ID].strip()
            client_secret = user_input[CONF_CLIENT_SECRET].strip()

            if not client_id:
                errors[CONF_CLIENT_ID] = "invalid_client_id"
            elif not client_secret:
                errors[CONF_CLIENT_SECRET] = "invalid_client_secret"

            if not errors:
                self._client_id = client_id
                self._client_secret = client_secret
                return await self._async_start_oauth()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Démarrage du flow OAuth externe
    # ------------------------------------------------------------------

    async def _async_start_oauth(self) -> ConfigFlowResult:
        # SmartThings exige HTTPS — on préfère l'URL externe
        ha_url = None
        for kwargs in [
            {"allow_internal": False, "prefer_external": True},
            {"allow_internal": True, "allow_ip": False},
            {"allow_internal": True, "allow_ip": True},
        ]:
            try:
                ha_url = get_url(self.hass, **kwargs)
                if ha_url.startswith("https://"):
                    break
            except NoURLAvailableError:
                continue

        if not ha_url:
            return self.async_abort(reason="no_url_available")
        if not ha_url.startswith("https://"):
            return self.async_abort(reason="https_required")

        self._redirect_uri = f"{ha_url}{OAUTH_CALLBACK_PATH}"
        _register_oauth_view(self.hass)

        scope_encoded = quote(OAUTH_SCOPES, safe="")
        redirect_encoded = quote(self._redirect_uri, safe="")
        self._oauth_url = (
            f"{ST_AUTH_URL}"
            f"?client_id={self._client_id}"
            f"&redirect_uri={redirect_encoded}"
            f"&response_type=code"
            f"&scope={scope_encoded}"
            f"&state={self.flow_id}"
        )

        return self.async_external_step(step_id="oauth", url=self._oauth_url)

    # ------------------------------------------------------------------
    # Étape 2 : réception du code OAuth (via la vue de callback)
    # ------------------------------------------------------------------

    async def async_step_oauth(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is None:
            return self.async_external_step(step_id="oauth", url=self._oauth_url)

        code = user_input.get("code")
        if not code:
            return self.async_abort(reason="oauth_error")

        tokens = await self._exchange_code(code)
        if tokens is None:
            return self.async_abort(reason="token_exchange_failed")

        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")
        expires_in = tokens.get("expires_in", 86400)

        if not access_token or not refresh_token:
            return self.async_abort(reason="token_exchange_failed")

        await self.async_set_unique_id(f"samsung_ac_{self._client_id}")
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title="Samsung AC SmartThings",
            data={
                CONF_CLIENT_ID: self._client_id,
                CONF_CLIENT_SECRET: self._client_secret,
                CONF_TOKEN: access_token,
                CONF_REFRESH_TOKEN: refresh_token,
                CONF_TOKEN_EXPIRES_AT: time.time() + expires_in,
            },
        )

    # ------------------------------------------------------------------
    # Re-auth
    # ------------------------------------------------------------------

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        return await self.async_step_user()

    # ------------------------------------------------------------------
    # Échange du code OAuth contre des tokens
    # ------------------------------------------------------------------

    async def _exchange_code(self, code: str) -> dict | None:
        session = async_get_clientsession(self.hass)
        credentials = f"{self._client_id}:{self._client_secret}"
        auth_header = base64.b64encode(credentials.encode()).decode()

        try:
            async with session.post(
                ST_TOKEN_URL,
                headers={
                    "Authorization": f"Basic {auth_header}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self._redirect_uri,
                },
                timeout=aiohttp.ClientTimeout(total=30),
            ) as r:
                if r.status != 200:
                    body = await r.text()
                    _LOGGER.error("Échange token échoué %s: %s", r.status, body)
                    return None
                return await r.json()
        except aiohttp.ClientError as err:
            _LOGGER.error("Erreur échange token: %s", err)
            return None


def _register_oauth_view(hass) -> None:
    """Enregistre la vue de callback OAuth (idempotent)."""
    if hass.data.get(DOMAIN, {}).get("_oauth_view_registered"):
        return
    hass.http.register_view(SamsungAcOAuthCallbackView())
    hass.data.setdefault(DOMAIN, {})["_oauth_view_registered"] = True
