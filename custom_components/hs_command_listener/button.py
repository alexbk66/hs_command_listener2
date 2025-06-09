import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.components.button import ButtonEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class DynamicButton(ButtonEntity):
    def __init__(self, entity_id: str, name: str) -> None:
        self.entity_id = f"button.{entity_id}"
        self._attr_unique_id = f"button_{entity_id}"
        self._attr_name = name

    async def async_press(self) -> None:
        _LOGGER.debug("DynamicButton pressed: %s", self.entity_id)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Register DynamicButton via dispatcher."""

    async def _handle_create(entity_type, entity_id, name, command):
        if entity_type != "BUTTON":
            return

        entity = DynamicButton(entity_id, name)
        #async_add_entities([entity])
        hass.async_create_task(async_add_entities([entity]))

    async_dispatcher_connect(hass, f"{DOMAIN}_create_entity", _handle_create)