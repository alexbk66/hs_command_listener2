"""Helpers for associating dynamic entities with Home Assistant devices."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .command import Command
from .const import DOMAIN


def apply_device_info(entity: Entity, command: Command) -> None:
    """Associate an entity with its originating HomeSeer root device."""

    if command.deviceID is None or not command.deviceName:
        return

    entity._attr_device_info = DeviceInfo(
        identifiers={(DOMAIN, f"device_{command.deviceID}")},
        name=command.deviceName,
        suggested_area=command.deviceArea,
    )
