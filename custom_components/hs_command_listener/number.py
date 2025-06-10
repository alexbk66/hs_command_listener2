
import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from homeassistant.components.number import NumberEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class DynamicNumber(NumberEntity):
    def __init__(self, entity_id, name, min_v, max_v, step):
        self.entity_id = f"number.{entity_id}"
        self._attr_unique_id = f"number_{entity_id}"
        self._attr_name = name
        self._attr_native_value = min_v
        self._attr_native_min_value = min_v
        self._attr_native_max_value = max_v
        self._attr_native_step = step
        self._attr_should_poll = False

    async def async_set_native_value(self, value):
        self._attr_native_value = value
        self.async_write_ha_state()


async def async_setup_entry(hass, config_entry, async_add_entities):

    async def _handler(entity_type, entity_id, name, command):
        if entity_type != "NUMBER":
            return

        entity = DynamicNumber(
            entity_id, name,
            getattr(command, "min", 0),
            getattr(command, "max", 100),
            getattr(command, "step", 1)
        )

        async_add_entities([entity])          # ← just call, no await / no task
        #hass.async_create_task(async_add_entities([entity]))


    async_dispatcher_connect(hass, f"{DOMAIN}_create_entity", _handler)
