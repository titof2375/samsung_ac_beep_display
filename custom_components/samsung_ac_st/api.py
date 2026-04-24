"""SmartThings API client — full Samsung AC control."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import (
    CAP_AC_MODE, CAP_COOL_SETPOINT, CAP_EXECUTE, CAP_FAN_MODE,
    CAP_HEAT_SETPOINT, CAP_HUMIDITY, CAP_SWING, CAP_SWITCH, CAP_TEMP,
    HA_TO_ST_FAN, HA_TO_ST_MODE, HA_TO_ST_SWING,
    OCF_PATH, OPT_BEEP_OFF, OPT_BEEP_ON, OPT_DISPLAY_OFF, OPT_DISPLAY_ON,
    ST_API_BASE,
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
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    async def _get(self, path: str) -> Any:
        try:
            async with self._session.get(
                f"{ST_API_BASE}{path}",
                headers=self._headers(),
                timeout=aiohttp.ClientTimeout(total=15),
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
                headers=self._headers(),
                json={"commands": commands},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as r:
                if r.status == 401:
                    raise SmartThingsAuthError("Invalid SmartThings token")
                r.raise_for_status()
        except SmartThingsAuthError:
            raise
        except aiohttp.ClientError as err:
            raise SmartThingsConnectionError(str(err)) from err

    def _cmd(self, capability: str, command: str, arguments: list | None = None) -> dict:
        c = {"component": "main", "capability": capability, "command": command}
        if arguments is not None:
            c["arguments"] = arguments
        return c

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    async def validate_token(self) -> None:
        await self._get("/devices")

    async def get_ac_devices(self) -> list[dict]:
        """Return all SmartThings devices with airConditionerMode capability."""
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
        """Fetch full device status and return a parsed dict."""
        raw = await self._get(f"/devices/{device_id}/status")
        main = raw.get("components", {}).get("main", {})

        def _val(cap: str, attr: str):
            return main.get(cap, {}).get(attr, {}).get("value")

        state: dict[str, Any] = {}

        # Power
        sw = _val(CAP_SWITCH, "switch")
        state["is_on"] = sw == "on" if sw is not None else None

        # Mode
        st_mode = _val(CAP_AC_MODE, "airConditionerMode")
        state["mode"] = st_mode  # kept as ST string; climate.py converts

        # Temperatures
        state["current_temp"] = _val(CAP_TEMP, "temperature")
        state["cool_setpoint"] = _val(CAP_COOL_SETPOINT, "coolingSetpoint")
        state["heat_setpoint"] = _val(CAP_HEAT_SETPOINT, "heatingSetpoint")

        # Humidity
        state["humidity"] = _val(CAP_HUMIDITY, "humidity")

        # Fan
        state["fan_mode"] = _val(CAP_FAN_MODE, "fanMode")

        # Swing
        state["swing"] = _val(CAP_SWING, "fanOscillationMode")

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

    async def set_temperature(self, device_id: str, temp: float, ha_mode: str) -> None:
        if ha_mode == "heat":
            await self._command(device_id, [self._cmd(CAP_HEAT_SETPOINT, "setHeatingSetpoint", [temp])])
        else:
            await self._command(device_id, [self._cmd(CAP_COOL_SETPOINT, "setCoolingSetpoint", [temp])])

    async def set_fan_mode(self, device_id: str, ha_fan: str) -> None:
        st_fan = HA_TO_ST_FAN.get(ha_fan, "auto")
        await self._command(device_id, [self._cmd(CAP_FAN_MODE, "setFanMode", [st_fan])])

    async def set_swing(self, device_id: str, ha_swing: str) -> None:
        st_swing = HA_TO_ST_SWING.get(ha_swing, "fixed")
        await self._command(device_id, [self._cmd(CAP_SWING, "setFanOscillationMode", [st_swing])])

    # ------------------------------------------------------------------
    # Display & Beep
    # ------------------------------------------------------------------

    async def set_display(self, device_id: str, on: bool) -> None:
        option = OPT_DISPLAY_ON if on else OPT_DISPLAY_OFF
        await self._execute_option(device_id, option)

    async def set_beep(self, device_id: str, on: bool) -> None:
        option = OPT_BEEP_ON if on else OPT_BEEP_OFF
        await self._execute_option(device_id, option)

    async def _execute_option(self, device_id: str, option: str) -> None:
        await self._command(device_id, [{
            "component": "main",
            "capability": CAP_EXECUTE,
            "command": "execute",
            "arguments": [OCF_PATH, {"x.com.samsung.da.options": [option]}],
        }])
