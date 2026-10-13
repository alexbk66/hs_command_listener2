import logging
from typing import List, Optional

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from homeassistant.components.select import SelectEntity

from .command import Command
from .const import DOMAIN
from .device import apply_device_info

_LOGGER = logging.getLogger(__name__)

class DynamicSelect(SelectEntity):
    def __init__(
        self,
        entity_id: str,
        name: str,
        options: Optional[List[str]] = None,
    ) -> None:
        self.entity_id = f"select.{entity_id}"
        self._attr_unique_id = f"select_{entity_id}"
        self._attr_name = name
        self._attr_options = options or ["Option 1", "Option 2"]
        # HS is authoritative. Keep the entity unknown until AKHomeAssistant
        # publishes the current HS option; never fabricate the first option.
        self._attr_current_option = None

    async def async_select_option(self, option: str) -> None:
        if option in self._attr_options:
            self._attr_current_option = option
            self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:

    async def _handle_create(entity_type, entity_id, name, command):
        if entity_type != "SELECT":
            return

        entity  = DynamicSelect(
                entity_id,
                name,
                getattr(command, "selects", None)
            )
        apply_device_info(entity, command)
        async_add_entities([entity])

    async_dispatcher_connect(hass, f"{DOMAIN}_create_entity", _handle_create)