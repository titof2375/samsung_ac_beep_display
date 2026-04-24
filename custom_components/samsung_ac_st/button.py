"""Boutons d'action — réinitialisation du filtre."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
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
    entities = []
    for device in coordinator.devices:
        entities.append(FilterResetButton(coordinator, device))
        entities.append(SelfCheckButton(coordinator, device))
    async_add_entities(entities)


class FilterResetButton(CoordinatorEntity[SamsungAcCoordinator], ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Réinitialiser filtre"
    _attr_icon = "mdi:filter-remove"

    def __init__(self, coordinator: SamsungAcCoordinator, device: dict) -> None:
        super().__init__(coordinator)
        self._device_id = device["device_id"]
        self._label = device["label"]
        self._attr_unique_id = f"{self._device_id}_filter_reset"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self._label,
            manufacturer="Samsung",
            model="Air Conditioner",
        )

    async def async_press(self) -> None:
        await self.coordinator.client.reset_filter(self._device_id)
        await self.coordinator.async_request_refresh()


class SelfCheckButton(CoordinatorEntity[SamsungAcCoordinator], ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Lancer le diagnostic"
    _attr_icon = "mdi:stethoscope"

    def __init__(self, coordinator: SamsungAcCoordinator, device: dict) -> None:
        super().__init__(coordinator)
        self._device_id = device["device_id"]
        self._label = device["label"]
        self._attr_unique_id = f"{self._device_id}_self_check"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self._label,
            manufacturer="Samsung",
            model="Air Conditioner",
        )

    async def async_press(self) -> None:
        await self.coordinator.client.start_self_check(self._device_id)
        await self.coordinator.async_request_refresh()
