"""Config flow Samsung AC SmartThings — OAuth2 entièrement automatique."""
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

APP_NAME_PREFIX = "ha-ac-st-"


class SamsungAcOAuthCallbackView(HomeAssistantView):
    """Reçoit le code OAuth depuis SmartThings."""

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
            _LOGGER.error("OAuth callback échoué: %s (%s)", err, type(err).__name__)
            return web.Response(
                text=f"<html><body>Erreur: {err}</body></html>",
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
        self._redirect_uri: str | None = None
        self._oauth_url: str | None = None
        self._oauth_code: str | None = None

    # ------------------------------------------------------------------
    # Étape 1 : saisie du PAT
    # ------------------------------------------------------------------

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            pat = user_input["pat"].strip()
            session = async_get_clientsession(self.hass)

            # Vérifier le PAT
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
                return await self.async_step_setup_app()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Étape 2 : trouver ou créer l'app SmartThings automatiquement
    # ------------------------------------------------------------------

    async def async_step_setup_app(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        import json as _json

        session = async_get_clientsession(self.hass)

        # Déterminer l'URL externe HTTPS de HA
        ha_url = None
        for kwargs in [
            {"allow_internal": False, "prefer_external": True},
            {"allow_internal": True, "allow_ip": False},
        ]:
            try:
                url = get_url(self.hass, **kwargs)
                if url.startswith("https://"):
                    ha_url = url
                    break
            except NoURLAvailableError:
                continue

        if not ha_url:
            return self.async_abort(reason="no_url_available")

        self._redirect_uri = f"{ha_url}{OAUTH_CALLBACK_PATH}"
        headers = {
            "Authorization": f"Bearer {self._pat}",
            "Content-Type": "application/json",
        }

        # ── 1. Chercher une app existante ─────────────────────────────
        app_id = None
        client_id = None

        try:
            async with session.get(
                f"{ST_API_BASE}/apps",
                headers={"Authorization": f"Bearer {self._pat}"},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as r:
                if r.status == 200:
                    data = await r.json()
                    for item in data.get("items", []):
                        if item.get("appName", "").startswith(APP_NAME_PREFIX):
                            app_id = item.get("appId")
                            client_id = item.get("oauthClientId")
                            _LOGGER.debug("App existante trouvée: %s (%s)", item.get("appName"), app_id)
                            break
                elif r.status == 403:
                    _LOGGER.warning("GET /apps: scope r:apps:* manquant — création directe")
        except aiohttp.ClientError as err:
            _LOGGER.warning("GET /apps échoué: %s", err)

        # ── 2. App trouvée → mettre à jour redirect + régénérer secret ─
        if app_id:
            try:
                async with session.put(
                    f"{ST_API_BASE}/apps/{app_id}/oauth",
                    headers=headers,
                    json={
                        "clientName": "Samsung AC HA",
                        "scope": OAUTH_SCOPES.split(),
                        "redirectUris": [self._redirect_uri],
                    },
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as r:
                    _LOGGER.debug("PUT oauth redirect — HTTP %s", r.status)
            except aiohttp.ClientError:
                pass

            try:
                async with session.post(
                    f"{ST_API_BASE}/apps/{app_id}/oauth/generate",
                    headers=headers,
                    json={},
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as r:
                    if r.status == 200:
                        creds = await r.json()
                        oauth = creds.get("oauthClientDetails") or creds
                        self._client_id = oauth.get("clientId") or client_id
                        self._client_secret = oauth.get("clientSecret")
            except aiohttp.ClientError as err:
                _LOGGER.error("Régénération credentials: %s", err)

        # ── 3. Pas d'app → créer avec nom UUID unique ─────────────────
        else:
            app_name = f"{APP_NAME_PREFIX}{uuid.uuid4().hex[:12]}"
            _LOGGER.debug("Création app: %s", app_name)

            try:
                async with session.post(
                    f"{ST_API_BASE}/apps",
                    headers=headers,
                    json={
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
                    },
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as r:
                    body = await r.text()
                    _LOGGER.debug("POST /apps — HTTP %s: %s", r.status, body[:300])

                    if r.status == 401:
                        return self.async_abort(reason="invalid_auth")
                    if r.status == 403:
                        return self.async_abort(reason="insufficient_permissions")
                    if r.status not in (200, 201):
                        _LOGGER.error("Création app échouée %s: %s", r.status, body)
                        return self.async_abort(reason="app_creation_failed")

                    data = _json.loads(body)
                    oauth = data.get("oauthClientDetails") or {}
                    self._client_id = oauth.get("clientId") or data.get("oauthClientId")
                    self._client_secret = oauth.get("clientSecret") or data.get("oauthClientSecret")

            except aiohttp.ClientError as err:
                _LOGGER.error("Connexion impossible: %s", err)
                return self.async_abort(reason="cannot_connect")

        if not self._client_id or not self._client_secret:
            return self.async_abort(reason="app_creation_failed")

        # Enregistrer le callback OAuth
        _register_oauth_view(self.hass)

        # Construire l'URL d'autorisation
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
    # Étape 3 : réception du code OAuth
    # ------------------------------------------------------------------

    async def async_step_oauth(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is None:
            return self.async_external_step(step_id="oauth", url=self._oauth_url)

        self._oauth_code = user_input.get("code")
        return self.async_external_step_done(next_step_id="finish")

    # ------------------------------------------------------------------
    # Étape 4 : échange du code et création de l'entrée
    # ------------------------------------------------------------------

    async def async_step_finish(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if not self._oauth_code:
            return self.async_abort(reason="oauth_error")

        tokens = await self._exchange_code(self._oauth_code)
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
