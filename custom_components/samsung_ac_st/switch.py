"""Switch entities: display and beep per Samsung AC."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Coroutine

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SamsungAcCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class SamsungAcSwitchDesc(SwitchEntityDescription):
    turn_on_fn: Callable[..., Coroutine]
    turn_off_fn: Callable[..., Coroutine]


SWITCHES: tuple[SamsungAcSwitchDesc, ...] = (
    SamsungAcSwitchDesc(
        key="display",
        name="Écran",
        icon="mdi:television",
        turn_on_fn=lambda c, did: c.set_display(did, True),
        turn_off_fn=lambda c, did: c.set_display(did, False),
    ),
    SamsungAcSwitchDesc(
        key="beep",
        name="Bip",
        icon="mdi:volume-high",
        turn_on_fn=lambda c, did: c.set_beep(did, True),
        turn_off_fn=lambda c, did: c.set_beep(did, False),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SamsungAcCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        SamsungAcSwitch(coordinator, device, desc)
        for device in coordinator.devices
        for desc in SWITCHES
    )


class SamsungAcSwitch(CoordinatorEntity[SamsungAcCoordinator], SwitchEntity):
    """Display or beep switch for one Samsung AC unit."""

    entity_description: SamsungAcSwitchDesc
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SamsungAcCoordinator,
        device: dict,
        description: SamsungAcSwitchDesc,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._device_id = device["device_id"]
        self._label = device["label"]
        self._attr_unique_id = f"{self._device_id}_{description.key}"
        self._optimistic: bool | None = None

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self._label,
            manufacturer="Samsung",
            model="Air Conditioner",
        )

    @property
    def is_on(self) -> bool | None:
        return self._optimistic

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.entity_description.turn_on_fn(self.coordinator.client, self._device_id)
        self._optimistic = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.entity_description.turn_off_fn(self.coordinator.client, self._device_id)
        self._optimistic = False
        self.async_write_ha_state()
