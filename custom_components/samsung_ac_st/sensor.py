"""Humidity sensor for Samsung AC via SmartThings."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SamsungAcCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SamsungAcCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        SamsungAcHumiditySensor(coordinator, device) for device in coordinator.devices
    )


class SamsungAcHumiditySensor(CoordinatorEntity[SamsungAcCoordinator], SensorEntity):
    """Room humidity sensor from Samsung AC."""

    _attr_has_entity_name = True
    _attr_name = "Humidité"
    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, coordinator: SamsungAcCoordinator, device: dict) -> None:
        super().__init__(coordinator)
        self._device_id = device["device_id"]
        self._label = device["label"]
        self._attr_unique_id = f"{self._device_id}_humidity"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self._label,
            manufacturer="Samsung",
            model="Air Conditioner",
        )

    @property
    def native_value(self) -> int | None:
        h = self.coordinator.data.get(self._device_id, {}).get("humidity")
        return int(h) if h is not None else None
