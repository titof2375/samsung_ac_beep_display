"""SmartThings API client for Samsung AC Beep & Display control."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import (
    CAP_AC_MODE,
    CAP_EXECUTE,
    CAP_AC_LIGHTING,
    CAP_SOUND_MODE,
    OCF_PATH,
    OPT_BEEP_OFF,
    OPT_BEEP_ON,
    OPT_LIGHT_OFF,
    OPT_LIGHT_ON,
    ST_API_BASE,
)

_LOGGER = logging.getLogger(__name__)


class SmartThingsAuthError(Exception):
    """Invalid token."""


class SmartThingsConnectionError(Exception):
    """Cannot reach SmartThings API."""


class SmartThingsApiClient:
    """Async client for SmartThings REST API."""

    def __init__(self, token: str, session: aiohttp.ClientSession) -> None:
        self._token = token
        self._session = session

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    async def _get(self, path: str) -> Any:
        url = f"{ST_API_BASE}{path}"
        try:
            async with self._session.get(url, headers=self._headers(), timeout=aiohttp.ClientTimeout(total=15)) as r:
                if r.status == 401:
                    raise SmartThingsAuthError("Invalid SmartThings token")
                r.raise_for_status()
                return await r.json()
        except SmartThingsAuthError:
            raise
        except aiohttp.ClientError as err:
            raise SmartThingsConnectionError(str(err)) from err

    async def _post(self, path: str, payload: dict) -> Any:
        url = f"{ST_API_BASE}{path}"
        try:
            async with self._session.post(
                url, headers=self._headers(), json=payload, timeout=aiohttp.ClientTimeout(total=15)
            ) as r:
                if r.status == 401:
                    raise SmartThingsAuthError("Invalid SmartThings token")
                r.raise_for_status()
                try:
                    return await r.json()
                except Exception:
                    return {}
        except SmartThingsAuthError:
            raise
        except aiohttp.ClientError as err:
            raise SmartThingsConnectionError(str(err)) from err

    # ------------------------------------------------------------------
    # Device discovery
    # ------------------------------------------------------------------

    async def get_ac_devices(self) -> list[dict]:
        """Return all SmartThings devices that support airConditionerMode."""
        data = await self._get("/devices")
        devices = data.get("items", [])
        ac_devices = []
        for dev in devices:
            caps = [c.get("id") for c in dev.get("components", [{}])[0].get("capabilities", [])]
            if CAP_AC_MODE in caps:
                ac_devices.append(
                    {
                        "device_id": dev["deviceId"],
                        "label": dev.get("label", dev.get("name", dev["deviceId"])),
                        "capabilities": caps,
                    }
                )
        return ac_devices

    async def validate_token(self) -> bool:
        """Raise SmartThingsAuthError if token is invalid."""
        await self._get("/devices")
        return True

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    async def get_device_status(self, device_id: str) -> dict:
        """Return status dict with display and beep state (best-effort)."""
        status: dict = {"display": None, "beep": None}
        try:
            data = await self._get(f"/devices/{device_id}/status")
            main = data.get("components", {}).get("main", {})

            # Display via samsungce.airConditionerLighting
            lighting = main.get(CAP_AC_LIGHTING, {})
            if lighting:
                level = lighting.get("acLightingLevel", {}).get("value")
                if level is not None:
                    status["display"] = level != "off"

            # Beep via samsungce.soundMode
            sound = main.get(CAP_SOUND_MODE, {})
            if sound:
                mode = sound.get("soundMode", {}).get("value")
                if mode is not None:
                    status["beep"] = mode != "mute"

        except Exception as err:
            _LOGGER.debug("Could not read device status for %s: %s", device_id, err)

        return status

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    async def set_display(self, device_id: str, on: bool) -> None:
        """Turn AC display on or off."""
        # Samsung naming is inverted: Light_On = display OFF, Light_Off = display ON
        option = OPT_LIGHT_ON if not on else OPT_LIGHT_OFF
        await self._execute_option(device_id, option)
        _LOGGER.debug("Set display %s for %s (option=%s)", "on" if on else "off", device_id, option)

    async def set_beep(self, device_id: str, on: bool) -> None:
        """Enable or disable AC beep sound."""
        option = OPT_BEEP_ON if on else OPT_BEEP_OFF
        await self._execute_option(device_id, option)
        _LOGGER.debug("Set beep %s for %s (option=%s)", "on" if on else "off", device_id, option)

    async def _execute_option(self, device_id: str, option: str) -> None:
        payload = {
            "commands": [
                {
                    "component": "main",
                    "capability": CAP_EXECUTE,
                    "command": "execute",
                    "arguments": [
                        OCF_PATH,
                        {"x.com.samsung.da.options": [option]},
                    ],
                }
            ]
        }
        await self._post(f"/devices/{device_id}/commands", payload)
