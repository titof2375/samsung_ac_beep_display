"""Climate entity for Samsung AC via SmartThings."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    HA_TO_ST_FAN,
    HA_TO_ST_SWING,
    ST_TO_HA_FAN,
    ST_TO_HA_MODE,
    ST_TO_HA_SWING,
)
from .coordinator import SamsungAcCoordinator

_LOGGER = logging.getLogger(__name__)

HVAC_MODES = [
    HVACMode.OFF,
    HVACMode.COOL,
    HVACMode.HEAT,
    HVACMode.AUTO,
    HVACMode.FAN_ONLY,
    HVACMode.DRY,
]

FAN_MODES = ["auto", "low", "medium", "high", "turbo"]
SWING_MODES = ["off", "vertical", "horizontal", "both"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SamsungAcCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        SamsungAcClimate(coordinator, device) for device in coordinator.devices
    )


class SamsungAcClimate(CoordinatorEntity[SamsungAcCoordinator], ClimateEntity):
    """Full climate control for one Samsung AC unit."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = HVAC_MODES
    _attr_fan_modes = FAN_MODES
    _attr_swing_modes = SWING_MODES
    _attr_target_temperature_step = 1.0
    _attr_min_temp = 16.0
    _attr_max_temp = 30.0
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.SWING_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    def __init__(self, coordinator: SamsungAcCoordinator, device: dict) -> None:
        super().__init__(coordinator)
        self._device_id = device["device_id"]
        self._label = device["label"]
        self._attr_unique_id = self._device_id

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self._label,
            manufacturer="Samsung",
            model="Air Conditioner",
        )

    def _status(self) -> dict:
        return self.coordinator.data.get(self._device_id, {})

    @property
    def hvac_mode(self) -> HVACMode:
        s = self._status()
        if not s.get("is_on"):
            return HVACMode.OFF
        st_mode = s.get("mode", "cool")
        return HVACMode(ST_TO_HA_MODE.get(st_mode, "cool"))

    @property
    def current_temperature(self) -> float | None:
        return self._status().get("current_temp")

    @property
    def target_temperature(self) -> float | None:
        s = self._status()
        if self.hvac_mode == HVACMode.HEAT:
            return s.get("heat_setpoint")
        return s.get("cool_setpoint")

    @property
    def current_humidity(self) -> int | None:
        h = self._status().get("humidity")
        return int(h) if h is not None else None

    @property
    def fan_mode(self) -> str | None:
        st_fan = self._status().get("fan_mode")
        return ST_TO_HA_FAN.get(st_fan, "auto") if st_fan else None

    @property
    def swing_mode(self) -> str | None:
        st_swing = self._status().get("swing")
        return ST_TO_HA_SWING.get(st_swing, "off") if st_swing else None

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.OFF:
            await self.coordinator.client.turn_off(self._device_id)
        else:
            if self.hvac_mode == HVACMode.OFF:
                await self.coordinator.client.turn_on(self._device_id)
            await self.coordinator.client.set_mode(self._device_id, hvac_mode.value)
        await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is not None:
            await self.coordinator.client.set_temperature(
                self._device_id, temp, self.hvac_mode.value
            )
            await self.coordinator.async_request_refresh()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        await self.coordinator.client.set_fan_mode(self._device_id, fan_mode)
        await self.coordinator.async_request_refresh()

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        await self.coordinator.client.set_swing(self._device_id, swing_mode)
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self) -> None:
        await self.coordinator.client.turn_on(self._device_id)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self) -> None:
        await self.coordinator.client.turn_off(self._device_id)
        await self.coordinator.async_request_refresh()
