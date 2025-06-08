
import logging
from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class DynamicButton(ButtonEntity):
    def __init__(self, entity_id, name):
        self.entity_id = f"button.{entity_id}"
        self._attr_unique_id = f"button_{entity_id}"
        self._attr_name = name

    async def async_press(self):
        _LOGGER.debug("Button %s pressed", self.entity_id)

async def async_setup_entry(hass, config_entry, async_add_entities):
    def _handler(entity_type, entity_id, name, command):
        if entity_type != "BUTTON":
            return
        async_add_entities([DynamicButton(entity_id, name)])
    async_dispatcher_connect(hass, f"{DOMAIN}_create_entity", _handler)
