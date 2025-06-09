import logging
from typing import List, Optional

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from homeassistant.components.select import SelectEntity

from .command import Command
from .const import DOMAIN

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
        self._attr_current_option = self._attr_options[0]

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
                getattr(command, "options", None)
            )
        #async_add_entities([entity])
        hass.async_create_task(async_add_entities([entity]))

    async_dispatcher_connect(hass, f"{DOMAIN}_create_entity", _handle_create)