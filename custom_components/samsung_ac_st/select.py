"""Select entity for Samsung AC optional mode (Wind-Free, sommeil, silence, turbo)."""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, OPTIONAL_MODES
from .coordinator import SamsungAcCoordinator

_LOGGER = logging.getLogger(__name__)

# Libellés français pour chaque mode optionnel
MODE_LABELS = {
    "off":           "Désactivé",
    "sleep":         "Sommeil",
    "quiet":         "Silencieux",
    "speed":         "Turbo",
    "windFree":      "Sans courant d'air",
    "windFreeSleep": "Sans courant d'air (nuit)",
}

# Modes Wind-Free uniquement disponibles en refroidissement
WIND_FREE_MODES = {"windFree", "windFreeSleep"}

# Modes HVAC compatibles avec Wind-Free (micro-perforations = froid uniquement)
COOL_MODES = {"cool", "auto"}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SamsungAcCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        SamsungAcOptionalModeSelect(coordinator, device)
        for device in coordinator.devices
    )


class SamsungAcOptionalModeSelect(CoordinatorEntity[SamsungAcCoordinator], SelectEntity):
    """Select pour le mode spécial : Sans courant d'air / Sommeil / Silencieux / Turbo."""

    _attr_has_entity_name = True
    _attr_name = "Mode spécial"
    _attr_icon = "mdi:wind-power"

    def __init__(self, coordinator: SamsungAcCoordinator, device: dict) -> None:
        super().__init__(coordinator)
        self._device_id = device["device_id"]
        self._label = device["label"]
        self._attr_unique_id = f"{self._device_id}_optional_mode"

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

    def _in_cool_mode(self) -> bool:
        """Retourne True si le climatiseur est en mode refroidissement."""
        return self._status().get("mode", "") in COOL_MODES

    @property
    def options(self) -> list[str]:
        supported = self._status().get("supported_optional_modes") or OPTIONAL_MODES
        # Wind-Free uniquement en mode froid (ferme les volets → micro-perforations)
        filtered = [
            m for m in supported
            if m not in WIND_FREE_MODES or self._in_cool_mode()
        ]
        return [MODE_LABELS.get(m, m) for m in filtered]

    @property
    def current_option(self) -> str | None:
        mode = self._status().get("optional_mode", "off")
        return MODE_LABELS.get(mode, mode)

    async def async_select_option(self, option: str) -> None:
        reverse = {v: k for k, v in MODE_LABELS.items()}
        api_mode = reverse.get(option, option)
        await self.coordinator.client.set_optional_mode(self._device_id, api_mode)
        await self.coordinator.async_request_refresh()
