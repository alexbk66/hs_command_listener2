
import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from homeassistant.components.switch import SwitchEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class DynamicToggle(SwitchEntity):
    def __init__(self, entity_id, name):
        self.entity_id = f"switch.{entity_id}"
        self._attr_unique_id = f"toggle_{entity_id}"
        self._attr_name = name
        self._attr_is_on = False
        self._attr_should_poll = False

    @property
    def is_on(self):
        return self._attr_is_on

    async def async_turn_on(self, **kwargs):
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        self._attr_is_on = False
        self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
) -> None:
    """Listen for dispatcher signals and create switches."""

    async def _handler(entity_type, entity_id, name, command):
        if entity_type != "TOGGLE":
            return
        
        entity = DynamicToggle(entity_id, name)
        #async_add_entities([entity])
        hass.async_create_task(async_add_entities([entity]))

    async_dispatcher_connect(hass, f"{DOMAIN}_create_entity", _handler)
