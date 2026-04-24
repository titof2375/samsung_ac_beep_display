"""SmartThings API client — full Samsung AC control."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import (
    CAP_AC_MODE, CAP_AUDIO_VOLUME, CAP_AUTO_CLEANING, CAP_COOL_SETPOINT,
    CAP_DUST_ALARM, CAP_DUST_FILTER, CAP_EXECUTE, CAP_FAN_MODE,
    CAP_HUMIDITY, CAP_OPTIONAL_MODE, CAP_SWING, CAP_SWITCH, CAP_TEMP,
    CAP_TROPICAL_NIGHT,
    HA_TO_ST_FAN, HA_TO_ST_MODE, HA_TO_ST_SWING,
    OCF_PATH, OPT_DISPLAY_OFF, OPT_DISPLAY_ON, ST_API_BASE,
)

_LOGGER = logging.getLogger(__name__)


class SmartThingsAuthError(Exception):
    """Invalid token."""


class SmartThingsConnectionError(Exception):
    """Cannot reach SmartThings API."""


class SmartThingsApiClient:
    """Full async SmartThings client for Samsung AC."""

    def __init__(self, token: str, session: aiohttp.ClientSession) -> None:
        self._token = token
        self._session = session

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"}

    async def _get(self, path: str) -> Any:
        try:
            async with self._session.get(
                f"{ST_API_BASE}{path}", headers=self._headers(),
                timeout=aiohttp.ClientTimeout(total=15)
            ) as r:
                if r.status == 401:
                    raise SmartThingsAuthError("Invalid SmartThings token")
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
                headers=self._headers(), json={"commands": commands},
                timeout=aiohttp.ClientTimeout(total=15)
            ) as r:
                if r.status == 401:
                    raise SmartThingsAuthError("Invalid SmartThings token")
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

    async def validate_token(self) -> None:
        await self._get("/devices")

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

        # Disabled capabilities (don't read them)
        disabled = set(_val("custom.disabledCapabilities", "disabledCapabilities") or [])

        state: dict[str, Any] = {}

        # Power
        state["is_on"] = _val(CAP_SWITCH, "switch") == "on"

        # AC mode
        state["mode"] = _val(CAP_AC_MODE, "airConditionerMode")
        state["supported_modes"] = _val(CAP_AC_MODE, "supportedAcModes") or []

        # Temperature
        state["current_temp"]  = _val(CAP_TEMP, "temperature")
        state["cool_setpoint"] = _val(CAP_COOL_SETPOINT, "coolingSetpoint")

        # Humidity
        state["humidity"] = _val(CAP_HUMIDITY, "humidity")

        # Fan
        state["fan_mode"]           = _val(CAP_FAN_MODE, "fanMode")
        state["supported_fan_modes"] = _val(CAP_FAN_MODE, "supportedAcFanModes") or []

        # Swing
        state["swing"]           = _val(CAP_SWING, "fanOscillationMode")
        state["supported_swing"] = _val(CAP_SWING, "supportedFanOscillationModes") or []

        # Optional mode (Wind-Free, sleep, quiet, speed)
        state["optional_mode"]           = _val(CAP_OPTIONAL_MODE, "acOptionalMode") or "off"
        state["supported_optional_modes"] = _val(CAP_OPTIONAL_MODE, "supportedAcOptionalMode") or []

        # Beep volume (0=mute, 100=full)
        if CAP_AUDIO_VOLUME not in disabled:
            state["volume"] = _val(CAP_AUDIO_VOLUME, "volume")

        # Auto-cleaning
        if CAP_AUTO_CLEANING not in disabled:
            state["auto_cleaning"] = _val(CAP_AUTO_CLEANING, "autoCleaningMode") == "on"
            state["auto_cleaning_state"] = _val(CAP_AUTO_CLEANING, "operatingState")

        # Dust filter
        if CAP_DUST_FILTER not in disabled:
            state["filter_status"] = _val(CAP_DUST_FILTER, "dustFilterStatus")
            state["filter_usage"]  = _val(CAP_DUST_FILTER, "dustFilterUsage")

        # Tropical night mode level
        if CAP_TROPICAL_NIGHT not in disabled:
            state["tropical_night_level"] = _val(CAP_TROPICAL_NIGHT, "acTropicalNightModeLevel")

        return state

    # ------------------------------------------------------------------
    # Climate controls
    # ------------------------------------------------------------------

    async def turn_on(self, device_id: str) -> None:
        await self._command(device_id, [self._cmd(CAP_SWITCH, "on")])

    async def turn_off(self, device_id: str) -> None:
        await self._command(device_id, [self._cmd(CAP_SWITCH, "off")])

    async def set_mode(self, device_id: str, ha_mode: str) -> None:
        st_mode = HA_TO_ST_MODE.get(ha_mode, "cool")
        await self._command(device_id, [self._cmd(CAP_AC_MODE, "setAirConditionerMode", [st_mode])])

    async def set_temperature(self, device_id: str, temp: float) -> None:
        await self._command(device_id, [self._cmd(CAP_COOL_SETPOINT, "setCoolingSetpoint", [temp])])

    async def set_fan_mode(self, device_id: str, ha_fan: str) -> None:
        st_fan = HA_TO_ST_FAN.get(ha_fan, "auto")
        await self._command(device_id, [self._cmd(CAP_FAN_MODE, "setFanMode", [st_fan])])

    async def set_swing(self, device_id: str, ha_swing: str) -> None:
        st_swing = HA_TO_ST_SWING.get(ha_swing, "fixed")
        await self._command(device_id, [self._cmd(CAP_SWING, "setFanOscillationMode", [st_swing])])

    # ------------------------------------------------------------------
    # Optional mode (Wind-Free, sleep, quiet, speed)
    # ------------------------------------------------------------------

    async def set_optional_mode(self, device_id: str, mode: str) -> None:
        await self._command(device_id, [self._cmd(CAP_OPTIONAL_MODE, "setAcOptionalMode", [mode])])

    # ------------------------------------------------------------------
    # Beep — via audioVolume (0 = mute, 100 = on)
    # ------------------------------------------------------------------

    async def set_beep(self, device_id: str, on: bool) -> None:
        volume = 100 if on else 0
        await self._command(device_id, [self._cmd(CAP_AUDIO_VOLUME, "setVolume", [volume])])

    # ------------------------------------------------------------------
    # Display — via OCF execute
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
    # Auto-cleaning
    # ------------------------------------------------------------------

    async def set_auto_cleaning(self, device_id: str, on: bool) -> None:
        mode = "on" if on else "off"
        await self._command(device_id, [self._cmd(CAP_AUTO_CLEANING, "setAutoCleaningMode", [mode])])
