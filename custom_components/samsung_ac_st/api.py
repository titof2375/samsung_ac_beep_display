"""SmartThings API client — token fourni dynamiquement par OAuth2."""
from __future__ import annotations

import logging
from typing import Any, Callable, Coroutine

import aiohttp

from .const import (
    CAP_AC_MODE, CAP_AUDIO_VOLUME, CAP_AUTO_CLEANING, CAP_COOL_SETPOINT,
    CAP_DUST_ALARM, CAP_DUST_FILTER, CAP_EXECUTE, CAP_FAN_MODE, CAP_HUMIDITY,
    CAP_OPTIONAL_MODE, CAP_SELF_CHECK, CAP_SWING, CAP_SWITCH, CAP_TEMP,
    CAP_TROPICAL_NIGHT, HA_TO_ST_FAN, HA_TO_ST_MODE, HA_TO_ST_SWING,
    OCF_PATH, OPT_DISPLAY_OFF, OPT_DISPLAY_ON, ST_API_BASE,
)

_LOGGER = logging.getLogger(__name__)

# Fonction qui retourne le token frais (fournie par __init__.py via OAuth2 session)
TokenFn = Callable[[], Coroutine[Any, Any, str]]


class SmartThingsAuthError(Exception):
    """Token révoqué ou invalide."""


class SmartThingsConnectionError(Exception):
    """Impossible de joindre l'API."""


class SmartThingsApiClient:
    """Client async SmartThings. Le token est rafraîchi automatiquement par HA."""

    def __init__(self, session: aiohttp.ClientSession, get_token: TokenFn) -> None:
        self._session = session
        self._get_token = get_token  # coroutine → retourne un access_token frais

    async def _headers(self) -> dict:
        token = await self._get_token()
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async def _get(self, path: str) -> Any:
        try:
            async with self._session.get(
                f"{ST_API_BASE}{path}",
                headers=await self._headers(),
                timeout=aiohttp.ClientTimeout(total=15),
            ) as r:
                if r.status == 401:
                    raise SmartThingsAuthError("Token révoqué — re-authentification nécessaire")
                r.raise_for_status()
                return await r.json()
        except SmartThingsAuthError:
            raise
        except aiohttp.ClientError as err:
            raise SmartThingsConnectionError(str(err)) from err

    async def _command(self, device_id: str, commands: list[dict]) -> None:
        try:
            async with self._session.post(
                f"{ST_API_BASE}/devices/{device_id}/commands",
                headers=await self._headers(),
                json={"commands": commands},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as r:
                if r.status == 401:
                    raise SmartThingsAuthError("Token révoqué — re-authentification nécessaire")
                r.raise_for_status()
        except SmartThingsAuthError:
            raise
        except aiohttp.ClientError as err:
            raise SmartThingsConnectionError(str(err)) from err

    def _cmd(self, cap: str, command: str, args: list | None = None) -> dict:
        c: dict = {"component": "main", "capability": cap, "command": command}
        if args is not None:
            c["arguments"] = args
        return c

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    async def get_ac_devices(self) -> list[dict]:
        data = await self._get("/devices")
        result = []
        for dev in data.get("items", []):
            caps = {
                c.get("id")
                for comp in dev.get("components", [])
                for c in comp.get("capabilities", [])
            }
            if CAP_AC_MODE in caps:
                result.append({
                    "device_id": dev["deviceId"],
                    "label": dev.get("label") or dev.get("name", dev["deviceId"]),
                    "capabilities": caps,
                })
        return result

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    async def get_status(self, device_id: str) -> dict:
        raw = await self._get(f"/devices/{device_id}/status")
        main = raw.get("components", {}).get("main", {})

        def _val(cap: str, attr: str):
            return main.get(cap, {}).get(attr, {}).get("value")

        disabled = set(_val("custom.disabledCapabilities", "disabledCapabilities") or [])
        state: dict[str, Any] = {}

        state["is_on"]           = _val(CAP_SWITCH, "switch") == "on"
        state["mode"]            = _val(CAP_AC_MODE, "airConditionerMode")
        state["supported_modes"] = _val(CAP_AC_MODE, "supportedAcModes") or []
        state["current_temp"]    = _val(CAP_TEMP, "temperature")
        state["cool_setpoint"]   = _val(CAP_COOL_SETPOINT, "coolingSetpoint")
        state["humidity"]        = _val(CAP_HUMIDITY, "humidity")
        state["fan_mode"]             = _val(CAP_FAN_MODE, "fanMode")
        state["supported_fan_modes"]  = _val(CAP_FAN_MODE, "supportedAcFanModes") or []
        state["swing"]           = _val(CAP_SWING, "fanOscillationMode")
        state["supported_swing"] = _val(CAP_SWING, "supportedFanOscillationModes") or []
        state["optional_mode"]            = _val(CAP_OPTIONAL_MODE, "acOptionalMode") or "off"
        state["supported_optional_modes"] = _val(CAP_OPTIONAL_MODE, "supportedAcOptionalMode") or []

        if CAP_AUDIO_VOLUME not in disabled:
            state["volume"] = _val(CAP_AUDIO_VOLUME, "volume")
        if CAP_AUTO_CLEANING not in disabled:
            state["auto_cleaning"]       = _val(CAP_AUTO_CLEANING, "autoCleaningMode") == "on"
            state["auto_cleaning_state"] = _val(CAP_AUTO_CLEANING, "operatingState")
        if CAP_DUST_FILTER not in disabled:
            state["filter_status"]     = _val(CAP_DUST_FILTER, "dustFilterStatus")
            state["filter_usage"]      = _val(CAP_DUST_FILTER, "dustFilterUsage")
            state["filter_capacity"]   = _val(CAP_DUST_FILTER, "dustFilterCapacity")
            state["filter_last_reset"] = _val(CAP_DUST_FILTER, "dustFilterLastResetDate")
        if CAP_DUST_ALARM not in disabled:
            state["filter_alarm_threshold"]  = _val(CAP_DUST_ALARM, "alarmThreshold")
            state["filter_alarm_thresholds"] = _val(CAP_DUST_ALARM, "supportedAlarmThresholds") or []
        if CAP_TROPICAL_NIGHT not in disabled:
            state["tropical_night_level"] = _val(CAP_TROPICAL_NIGHT, "acTropicalNightModeLevel")
        if CAP_SELF_CHECK not in disabled:
            state["self_check_status"] = _val(CAP_SELF_CHECK, "status")
            state["self_check_errors"] = _val(CAP_SELF_CHECK, "errors") or []

        return state

    # ------------------------------------------------------------------
    # Climate
    # ------------------------------------------------------------------

    async def turn_on(self, device_id: str) -> None:
        await self._command(device_id, [self._cmd(CAP_SWITCH, "on")])

    async def turn_off(self, device_id: str) -> None:
        await self._command(device_id, [self._cmd(CAP_SWITCH, "off")])

    async def set_mode(self, device_id: str, ha_mode: str) -> None:
        await self._command(device_id, [self._cmd(CAP_AC_MODE, "setAirConditionerMode",
                                                   [HA_TO_ST_MODE.get(ha_mode, "cool")])])

    async def set_temperature(self, device_id: str, temp: float) -> None:
        await self._command(device_id, [self._cmd(CAP_COOL_SETPOINT, "setCoolingSetpoint", [temp])])

    async def set_fan_mode(self, device_id: str, ha_fan: str) -> None:
        await self._command(device_id, [self._cmd(CAP_FAN_MODE, "setFanMode",
                                                   [HA_TO_ST_FAN.get(ha_fan, "auto")])])

    async def set_swing(self, device_id: str, ha_swing: str) -> None:
        await self._command(device_id, [self._cmd(CAP_SWING, "setFanOscillationMode",
                                                   [HA_TO_ST_SWING.get(ha_swing, "fixed")])])

    # ------------------------------------------------------------------
    # Mode spécial (Wind-Free, sleep, quiet, speed)
    # ------------------------------------------------------------------

    async def set_optional_mode(self, device_id: str, mode: str) -> None:
        await self._command(device_id, [self._cmd(CAP_OPTIONAL_MODE, "setAcOptionalMode", [mode])])

    # ------------------------------------------------------------------
    # Bip — via OCF execute (Volume_Mute / Volume_100)
    # Identique au script samsung_ac_cloud.py de production
    # ------------------------------------------------------------------

    async def set_beep(self, device_id: str, on: bool) -> None:
        option = "Volume_100" if on else "Volume_Mute"
        await self._command(device_id, [{
            "component": "main",
            "capability": CAP_EXECUTE,
            "command": "execute",
            "arguments": [OCF_PATH, {"x.com.samsung.da.options": [option]}],
        }])

    # ------------------------------------------------------------------
    # Écran — via OCF execute
    # ------------------------------------------------------------------

    async def set_display(self, device_id: str, on: bool) -> None:
        option = OPT_DISPLAY_ON if on else OPT_DISPLAY_OFF
        await self._command(device_id, [{
            "component": "main",
            "capability": CAP_EXECUTE,
            "command": "execute",
            "arguments": [OCF_PATH, {"x.com.samsung.da.options": [option]}],
        }])

    # ------------------------------------------------------------------
    # Nettoyage auto
    # ------------------------------------------------------------------

    async def set_auto_cleaning(self, device_id: str, on: bool) -> None:
        await self._command(device_id, [self._cmd(CAP_AUTO_CLEANING, "setAutoCleaningMode",
                                                   ["on" if on else "off"])])

    # ------------------------------------------------------------------
    # Reset filtre
    # ------------------------------------------------------------------

    async def reset_filter(self, device_id: str) -> None:
        await self._command(device_id, [self._cmd(CAP_DUST_FILTER, "resetDustFilter")])

    async def set_filter_alarm_threshold(self, device_id: str, hours: int) -> None:
        await self._command(device_id, [self._cmd(CAP_DUST_ALARM, "setAlarmThreshold", [hours])])

    # ------------------------------------------------------------------
    # Nuit tropicale
    # ------------------------------------------------------------------

    async def set_tropical_night_level(self, device_id: str, level: int) -> None:
        await self._command(device_id, [self._cmd(CAP_TROPICAL_NIGHT, "setAcTropicalNightModeLevel", [level])])

    # ------------------------------------------------------------------
    # Auto-diagnostic
    # ------------------------------------------------------------------

    async def start_self_check(self, device_id: str) -> None:
        await self._command(device_id, [self._cmd(CAP_SELF_CHECK, "startSelfCheck")])
