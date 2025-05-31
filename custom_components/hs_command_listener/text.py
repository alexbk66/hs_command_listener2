import logging
from homeassistant.core import HomeAssistant
from homeassistant.components.text import TextEntity

from .const import DOMAIN, STORAGE_KEY, ENTITY_ID_COMMAND

_LOGGER = logging.getLogger(__name__)

class HSTextEntity(TextEntity):
    _attr_has_entity_name = True
    _attr_unique_id = ENTITY_ID_COMMAND
    _attr_name = "HS Command Input"
    _attr_native_value = ""

    def __init__(self):
        self._attr_name = "HS Command Input"
        self.entity_id  = "text." + ENTITY_ID_COMMAND
        self._attr_native_value = ""
        _LOGGER.debug("HSTextEntity created with id %s", ENTITY_ID_COMMAND)

    async def async_set_value(self, value: str):
        _LOGGER.debug("HSTextEntity set to '%s'", value)
        self._attr_native_value = value
        await self.async_update_ha_state()
        self.async_write_ha_state()

async def async_setup_platform(hass: HomeAssistant, config, add_entities, discovery_info=None):
    _LOGGER.debug("Setting up text platform for hs_command_listener")
    add_entities([HSTextEntity()])
    _LOGGER.debug("HSTextEntity added to platform")