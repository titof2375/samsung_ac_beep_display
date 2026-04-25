"""Config flow Samsung AC SmartThings — OAuth2 avec création/récupération de SmartApp."""
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
        self._redirect_uri: str | None = None
        self._oauth_url: str | None = None

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
    # Étape 2 : trouver ou créer le SmartApp
    # ------------------------------------------------------------------

    async def async_step_create_app(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        import hashlib
        import json as _json

        session = async_get_clientsession(self.hass)

        try:
            ha_url = get_url(self.hass, allow_internal=True, allow_ip=True)
        except NoURLAvailableError:
            return self.async_abort(reason="no_url_available")

        self._redirect_uri = f"{ha_url}{OAUTH_CALLBACK_PATH}"
        headers = {
            "Authorization": f"Bearer {self._pat}",
            "Content-Type": "application/json",
        }

        # Nom déterministe pour les nouvelles créations
        ha_hash = hashlib.md5(ha_url.encode()).hexdigest()[:16]
        app_name = f"samsung-ac-ha-{ha_hash}"

        app_id = None
        client_id = None

        # ── 1. Chercher par nom déterministe ──────────────────────────
        try:
            async with session.get(
                f"{ST_API_BASE}/apps/{app_name}",
                headers={"Authorization": f"Bearer {self._pat}"},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as r:
                _LOGGER.debug("GET app '%s' — HTTP %s", app_name, r.status)
                if r.status == 200:
                    data = await r.json()
                    app_id = data.get("appId")
                    client_id = data.get("oauthClientId")
                    _LOGGER.debug("App trouvée par nom déterministe: %s", app_id)
        except aiohttp.ClientError:
            pass

        # ── 2. Chercher dans la liste de toutes les apps ──────────────
        if not app_id:
            try:
                async with session.get(
                    f"{ST_API_BASE}/apps",
                    headers={"Authorization": f"Bearer {self._pat}"},
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as r:
                    _LOGGER.debug("GET /apps — HTTP %s", r.status)
                    if r.status == 200:
                        data = await r.json()
                        items = data.get("items", [])
                        _LOGGER.debug("Liste apps: %d app(s) trouvée(s)", len(items))
                        for item in items:
                            name = item.get("appName", "")
                            _LOGGER.debug("  app: %s (%s)", name, item.get("appId"))
                            if name.startswith("samsung-ac-ha-"):
                                app_id = item.get("appId")
                                client_id = item.get("oauthClientId")
                                _LOGGER.debug("App samsung-ac-ha-* trouvée: %s", app_id)
                                break
                    elif r.status == 403:
                        _LOGGER.warning("GET /apps — 403 : scope r:apps:* manquant dans le PAT")
            except aiohttp.ClientError as err:
                _LOGGER.warning("GET /apps échoué: %s", err)

        # ── 3. App trouvée → mettre à jour redirect + régénérer secret ─
        if app_id:
            _LOGGER.debug("Réutilisation de l'app existante: %s", app_id)

            # Mettre à jour le redirect URI
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
                    _LOGGER.debug("PUT /apps/{id}/oauth — HTTP %s", r.status)
            except aiohttp.ClientError as err:
                _LOGGER.warning("Mise à jour redirect URI échouée: %s", err)

            # Régénérer le client_secret
            try:
                async with session.post(
                    f"{ST_API_BASE}/apps/{app_id}/oauth/generate",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as r:
                    body = await r.text()
                    _LOGGER.debug("POST /apps/{id}/oauth/generate — HTTP %s: %s", r.status, body[:300])
                    if r.status == 200:
                        creds = _json.loads(body)
                        oauth = creds.get("oauthClientDetails") or creds
                        self._client_id = oauth.get("clientId") or client_id
                        self._client_secret = oauth.get("clientSecret")
            except aiohttp.ClientError as err:
                _LOGGER.error("Régénération credentials échouée: %s", err)

            if not self._client_id or not self._client_secret:
                _LOGGER.error("Impossible de récupérer les credentials (appId=%s)", app_id)
                return self.async_abort(reason="app_creation_failed")

        # ── 4. Pas d'app existante → créer ───────────────────────────
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
            _LOGGER.debug("Création SmartApp: %s", app_name)
            try:
                async with session.post(
                    f"{ST_API_BASE}/apps",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as r:
                    body = await r.text()
                    _LOGGER.debug("POST /apps — HTTP %s: %s", r.status, body[:400])
                    if r.status == 401:
                        return self.async_abort(reason="invalid_auth")
                    if r.status == 403:
                        return self.async_abort(reason="insufficient_permissions")
                    if r.status == 422:
                        # L'app existe quelque part mais on n'a pas pu la lire (scope manquant)
                        _LOGGER.error(
                            "422 : app existe mais introuvable — ajoutez le scope r:apps:* à votre PAT"
                        )
                        return self.async_abort(reason="app_exists_no_read")
                    if r.status not in (200, 201):
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

        # Construire l'URL d'autorisation SmartThings
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
