"""Switch entities: display and beep for each Samsung AC."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

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
class SamsungAcSwitchDescription(SwitchEntityDescription):
    state_fn: Callable[[dict], bool | None]
    turn_on_fn: Callable
    turn_off_fn: Callable


SWITCH_TYPES: tuple[SamsungAcSwitchDescription, ...] = (
    SamsungAcSwitchDescription(
        key="display",
        name="Écran",
        icon="mdi:television",
        state_fn=lambda status: status.get("display"),
        turn_on_fn=lambda client, did: client.set_display(did, True),
        turn_off_fn=lambda client, did: client.set_display(did, False),
    ),
    SamsungAcSwitchDescription(
        key="beep",
        name="Bip",
        icon="mdi:volume-high",
        state_fn=lambda status: status.get("beep"),
        turn_on_fn=lambda client, did: client.set_beep(did, True),
        turn_off_fn=lambda client, did: client.set_beep(did, False),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SamsungAcCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for device in coordinator.devices:
        for desc in SWITCH_TYPES:
            entities.append(SamsungAcSwitch(coordinator, device, desc))
    async_add_entities(entities)


class SamsungAcSwitch(CoordinatorEntity[SamsungAcCoordinator], SwitchEntity):
    """A switch that controls display or beep on a Samsung AC."""

    entity_description: SamsungAcSwitchDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SamsungAcCoordinator,
        device: dict,
        description: SamsungAcSwitchDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._device_id = device["device_id"]
        self._device_label = device["label"]
        self._attr_unique_id = f"{self._device_id}_{description.key}"
        # Optimistic state when SmartThings can't return current value
        self._optimistic_state: bool | None = None

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self._device_label,
            manufacturer="Samsung",
            model="Air Conditioner",
        )

    @property
    def is_on(self) -> bool | None:
        coordinator_state = self.entity_description.state_fn(
            self.coordinator.data.get(self._device_id, {})
        )
        # Prefer coordinator data; fall back to optimistic state
        if coordinator_state is not None:
            return coordinator_state
        return self._optimistic_state

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.entity_description.turn_on_fn(self.coordinator.client, self._device_id)
        self._optimistic_state = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.entity_description.turn_off_fn(self.coordinator.client, self._device_id)
        self._optimistic_state = False
        self.async_write_ha_state()
