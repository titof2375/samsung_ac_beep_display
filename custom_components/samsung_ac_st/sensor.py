"""Sensors: humidity + filter status + filter usage."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, FILTER_STATUS_ICONS
from .coordinator import SamsungAcCoordinator


@dataclass(frozen=True, kw_only=True)
class SamsungAcSensorDesc(SensorEntityDescription):
    value_fn: Callable[[dict], object]
    available_fn: Callable[[dict], bool] = lambda s: True


SENSORS: tuple[SamsungAcSensorDesc, ...] = (
    SamsungAcSensorDesc(
        key="humidity",
        name="Humidité",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda s: int(s["humidity"]) if s.get("humidity") is not None else None,
    ),
    SamsungAcSensorDesc(
        key="filter_usage",
        name="Filtre usage",
        icon="mdi:air-filter",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda s: s.get("filter_usage"),
        available_fn=lambda s: s.get("filter_usage") is not None,
    ),
    SamsungAcSensorDesc(
        key="filter_status",
        name="Filtre état",
        icon="mdi:air-filter",
        value_fn=lambda s: s.get("filter_status"),
        available_fn=lambda s: s.get("filter_status") is not None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SamsungAcCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        SamsungAcSensor(coordinator, device, desc)
        for device in coordinator.devices
        for desc in SENSORS
    )


class SamsungAcSensor(CoordinatorEntity[SamsungAcCoordinator], SensorEntity):
    entity_description: SamsungAcSensorDesc
    _attr_has_entity_name = True

    def __init__(self, coordinator: SamsungAcCoordinator, device: dict, desc: SamsungAcSensorDesc) -> None:
        super().__init__(coordinator)
        self.entity_description = desc
        self._device_id = device["device_id"]
        self._label = device["label"]
        self._attr_unique_id = f"{self._device_id}_{desc.key}"

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
    def available(self) -> bool:
        return self.entity_description.available_fn(self._status())

    @property
    def native_value(self):
        return self.entity_description.value_fn(self._status())

    @property
    def icon(self) -> str | None:
        if self.entity_description.key == "filter_status":
            status = self._status().get("filter_status", "normal")
            return FILTER_STATUS_ICONS.get(status, "mdi:air-filter")
        return self.entity_description.icon
