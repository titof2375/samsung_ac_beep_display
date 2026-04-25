"""Config flow Samsung AC SmartThings — OAuth2 via SmartApp dynamique."""
from __future__ import annotations

import base64
import logging
import time
import uuid
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
    CONF_APP_ID,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_REFRESH_TOKEN,
    CONF_TOKEN,
    CONF_TOKEN_EXPIRES_AT,
    DOMAIN,
    OAUTH_CALLBACK_PATH,
    OAUTH_SCOPES,
    ST_API_BASE,
    ST_AUTH_URL,
    ST_TOKEN_URL,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema({
    vol.Required("pat"): str,
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
        self._pat: str | None = None
        self._client_id: str | None = None
        self._client_secret: str | None = None
        self._app_id: str | None = None
        self._redirect_uri: str | None = None
        self._oauth_url: str | None = None

    # ------------------------------------------------------------------
    # Étape 1 : saisie du PAT temporaire
    # ------------------------------------------------------------------

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            pat = user_input["pat"].strip()
            session = async_get_clientsession(self.hass)

            try:
                async with session.get(
                    f"{ST_API_BASE}/devices",
                    headers={"Authorization": f"Bearer {pat}"},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as r:
                    if r.status == 401:
                        errors["base"] = "invalid_auth"
                    elif r.status != 200:
                        errors["base"] = "cannot_connect"
            except aiohttp.ClientError:
                errors["base"] = "cannot_connect"

            if not errors:
                self._pat = pat
                return await self.async_step_create_app()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Étape 2 : création OU réutilisation du SmartApp
    # ------------------------------------------------------------------

    async def async_step_create_app(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        import hashlib
        import json as _json

        session = async_get_clientsession(self.hass)

        # Déterminer l'URL de HA pour le redirect OAuth
        try:
            ha_url = get_url(self.hass, allow_internal=True, allow_ip=True)
        except NoURLAvailableError:
            return self.async_abort(reason="no_url_available")

        self._redirect_uri = f"{ha_url}{OAUTH_CALLBACK_PATH}"
        headers = {
            "Authorization": f"Bearer {self._pat}",
            "Content-Type": "application/json",
        }

        # Nom déterministe basé sur l'URL de HA — stable d'une tentative à l'autre
        ha_hash = hashlib.md5(ha_url.encode()).hexdigest()[:16]
        app_name = f"samsung-ac-ha-{ha_hash}"
        _LOGGER.debug("Nom déterministe SmartApp: %s", app_name)

        # ── 1. Chercher l'app par son nom déterministe ────────────────────
        existing_app_id = None
        existing_client_id = None
        try:
            async with session.get(
                f"{ST_API_BASE}/apps/{app_name}",
                headers={"Authorization": f"Bearer {self._pat}"},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as r:
                body = await r.text()
                _LOGGER.debug("GET app '%s' — HTTP %s: %s", app_name, r.status, body[:200])
                if r.status == 200:
                    app_data = _json.loads(body)
                    existing_app_id = app_data.get("appId")
                    existing_client_id = app_data.get("oauthClientId")
                    _LOGGER.debug("SmartApp existant trouvé: %s", existing_app_id)
        except aiohttp.ClientError:
            pass

        # ── 2a. App existant → mettre à jour le redirect URI + régénérer les credentials ──
        if existing_app_id:
            self._app_id = existing_app_id

            # Mettre à jour le redirect URI de l'app
            try:
                async with session.put(
                    f"{ST_API_BASE}/apps/{existing_app_id}/oauth",
                    headers=headers,
                    json={
                        "clientName": "Samsung AC HA",
                        "scope": OAUTH_SCOPES.split(),
                        "redirectUris": [self._redirect_uri],
                    },
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as r:
                    _LOGGER.debug("Mise à jour redirect URI — HTTP %s", r.status)
            except aiohttp.ClientError:
                pass

            # Régénérer le client_secret
            try:
                async with session.post(
                    f"{ST_API_BASE}/apps/{existing_app_id}/oauth/generate",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as r:
                    body = await r.text()
                    _LOGGER.debug("Régénération credentials — HTTP %s: %s", r.status, body[:300])
                    if r.status == 200:
                        creds = _json.loads(body)
                        oauth_details = creds.get("oauthClientDetails") or creds
                        self._client_id = oauth_details.get("clientId") or existing_client_id
                        self._client_secret = oauth_details.get("clientSecret")
            except aiohttp.ClientError as err:
                _LOGGER.error("Erreur régénération credentials: %s", err)

            if not self._client_id or not self._client_secret:
                _LOGGER.error("Impossible de régénérer les credentials (appId=%s)", existing_app_id)
                return self.async_abort(reason="app_creation_failed")

        # ── 2b. App inexistant → créer ────────────────────────────────────
        else:
            payload = {
                "appName": app_name,
                "displayName": "Samsung AC HA Integration",
                "description": "Home Assistant integration for Samsung AC climate control",
                "appType": "API_ONLY",
                "classifications": ["AUTOMATION"],
                "apiOnly": {},
                "oauth": {
                    "clientName": "Samsung AC HA",
                    "scope": OAUTH_SCOPES.split(),
                    "redirectUris": [self._redirect_uri],
                },
            }
            _LOGGER.debug("Création SmartApp — appName: %s", app_name)
            try:
                async with session.post(
                    f"{ST_API_BASE}/apps",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as r:
                    body = await r.text()
                    _LOGGER.debug("Création SmartApp — HTTP %s: %s", r.status, body[:400])
                    if r.status == 401:
                        return self.async_abort(reason="invalid_auth")
                    if r.status == 403:
                        return self.async_abort(reason="insufficient_permissions")
                    if r.status == 422:
                        # L'app existe mais on ne peut pas le lire — tenter de régénérer par nom
                        _LOGGER.warning("App '%s' existe mais GET échoué — tentative de récupération via oauth/generate", app_name)
                        return self.async_abort(reason="app_exists_no_read")
                    if r.status not in (200, 201):
                        _LOGGER.error("Création SmartApp échouée %s: %s", r.status, body[:400])
                        return self.async_abort(reason="app_creation_failed")
                    data = _json.loads(body)
            except aiohttp.ClientError as err:
                _LOGGER.error("Connexion impossible: %s", err)
                return self.async_abort(reason="cannot_connect")

            oauth_details = data.get("oauthClientDetails") or {}
            self._client_id = oauth_details.get("clientId") or data.get("oauthClientId")
            self._client_secret = oauth_details.get("clientSecret") or data.get("oauthClientSecret")
            self._app_id = data.get("appId")

        if not self._client_id or not self._client_secret:
            _LOGGER.error("client_id/client_secret manquants")
            return self.async_abort(reason="app_creation_failed")

        if not self._client_id or not self._client_secret:
            _LOGGER.error("client_id/client_secret manquants dans la réponse: %s", data)
            return self.async_abort(reason="app_creation_failed")

        # Enregistrer la vue de callback (une seule fois)
        _register_oauth_view(self.hass)

        # Construire l'URL OAuth SmartThings
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
    # Étape 3 : réception du code OAuth (via la vue de callback)
    # ------------------------------------------------------------------

    async def async_step_oauth(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is None:
            # Toujours en attente du callback SmartThings
            return self.async_external_step(step_id="oauth", url=self._oauth_url)

        code = user_input.get("code")
        if not code:
            return self.async_abort(reason="oauth_error")

        # Échanger le code contre des tokens
        tokens = await self._exchange_code(code)
        if tokens is None:
            return self.async_abort(reason="token_exchange_failed")

        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")
        expires_in = tokens.get("expires_in", 86400)

        if not access_token or not refresh_token:
            return self.async_abort(reason="token_exchange_failed")

        await self.async_set_unique_id(f"samsung_ac_{self._app_id}")
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title="Samsung AC SmartThings",
            data={
                CONF_CLIENT_ID: self._client_id,
                CONF_CLIENT_SECRET: self._client_secret,
                CONF_APP_ID: self._app_id,
                CONF_TOKEN: access_token,
                CONF_REFRESH_TOKEN: refresh_token,
                CONF_TOKEN_EXPIRES_AT: time.time() + expires_in,
            },
        )

    # ------------------------------------------------------------------
    # Re-auth (token révoqué ou refresh_token expiré)
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
