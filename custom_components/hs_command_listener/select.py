
import logging
from homeassistant.components.select import SelectEntity
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class DynamicSelect(SelectEntity):
    def __init__(self, entity_id, name, options=None):
        self.entity_id = f"select.{entity_id}"
        self._attr_unique_id = f"select_{entity_id}"
        self._attr_name = name
        self._attr_options = options or ["Option 1", "Option 2"]
        self._attr_current_option = self._attr_options[0]

    async def async_select_option(self, option):
        if option in self._attr_options:
            self._attr_current_option = option
            self.async_write_ha_state()

async def async_setup_entry(hass, config_entry, async_add_entities):
    def _handler(entity_type, entity_id, name, command):
        if entity_type != "SELECT":
            return
        async_add_entities([DynamicSelect(entity_id, name)])
    async_dispatcher_connect(hass, f"{DOMAIN}_create_entity", _handler)
