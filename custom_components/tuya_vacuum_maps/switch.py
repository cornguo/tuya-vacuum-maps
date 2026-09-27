"""Switches that select the rooms to clean."""

import math
from typing import Any

from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .coordinator import VacuumMapRuntime
from .entity import VacuumMapEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add a switch for each room, including rooms added to the map later."""
    runtime: VacuumMapRuntime = config_entry.runtime_data
    added_rooms: set[int] = set()

    @callback
    def add_new_rooms() -> None:
        new_rooms = runtime.coordinator.data.rooms.keys() - added_rooms
        added_rooms.update(new_rooms)
        if new_rooms:
            async_add_entities(
                RoomSwitch(runtime, room_id) for room_id in sorted(new_rooms)
            )

    add_new_rooms()
    config_entry.async_on_unload(runtime.coordinator.async_add_listener(add_new_rooms))


class RoomSwitch(VacuumMapEntity, SwitchEntity, RestoreEntity):
    """Select a room to clean.

    Rooms are cleaned in the order their switches were turned on.
    """

    _attr_has_entity_name = True
    _attr_icon = "mdi:floor-plan"

    def __init__(self, runtime: VacuumMapRuntime, room_id: int) -> None:
        """Initialize the switch."""
        super().__init__(runtime, SWITCH_DOMAIN, f"room_{room_id}")
        self.room_id = room_id

    @property
    def name(self) -> str:
        """Return the room's name, as renamed in the vacuum's app."""
        return self.coordinator.data.rooms.get(self.room_id, f"Room {self.room_id}")

    @property
    def available(self) -> bool:
        """Return whether the room is still on the map."""
        return super().available and self.room_id in self.coordinator.data.rooms

    @property
    def is_on(self) -> bool:
        """Return whether the room is selected."""
        return self.room_id in self._runtime.selected_rooms

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the room id and its place in the cleaning order."""
        attributes: dict[str, Any] = {"room_id": self.room_id}
        if self.is_on:
            attributes["order"] = self._runtime.selected_rooms.index(self.room_id) + 1
        return attributes

    async def async_added_to_hass(self) -> None:
        """Restore whether the room was selected, and its place in the order."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if (
            last_state
            and last_state.state == STATE_ON
            and self.room_id not in self._runtime.selected_rooms
        ):
            restored_order = self._runtime.restored_order
            restored_order[self.room_id] = last_state.attributes.get("order", math.inf)
            self._runtime.selected_rooms.append(self.room_id)
            # Switches are restored by room id; put them back in their old order
            self._runtime.selected_rooms.sort(
                key=lambda room_id: restored_order.get(room_id, math.inf)
            )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Select the room, after the rooms already selected."""
        if self.room_id not in self._runtime.selected_rooms:
            self._runtime.selected_rooms.append(self.room_id)
        self._update_room_switches()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Deselect the room."""
        if self.room_id in self._runtime.selected_rooms:
            self._runtime.selected_rooms.remove(self.room_id)
        self._update_room_switches()

    def _update_room_switches(self) -> None:
        """Write this and the other rooms' states, whose order may change."""
        # The coordinator's listeners include every room switch
        self.coordinator.async_update_listeners()
