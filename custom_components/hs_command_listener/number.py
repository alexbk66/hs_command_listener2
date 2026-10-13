
import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from homeassistant.components.number import NumberEntity
from .const import DOMAIN
from .device import apply_device_info

_LOGGER = logging.getLogger(__name__)

class DynamicNumber(NumberEntity):
    def __init__(self, entity_id, name, min_v, max_v, step):
        self.entity_id = f"number.{entity_id}"
        self._attr_unique_id = f"number_{entity_id}"
        self._attr_name = name
        # HS is authoritative. Keep the entity unknown until AKHomeAssistant
        # publishes the current HS value; never fabricate the minimum value.
        self._attr_native_value = None
        self._attr_native_min_value = min_v
        self._attr_native_max_value = max_v
        self._attr_native_step = step
        self._attr_should_poll = False
        # Generate a state event even when the requested value is unchanged.
        self._attr_force_update = True

    async def async_set_native_value(self, value):
        self._attr_native_value = value
        self.async_write_ha_state()


async def async_setup_entry(hass, config_entry, async_add_entities):

    async def _handler(entity_type, entity_id, name, command):
        if entity_type != "NUMBER":
            return

        entity = DynamicNumber(
            entity_id, name,
            command.min if command.min is not None else 0,
            command.max if command.max is not None else 100,
            command.step if command.step is not None else 1,
        )

        apply_device_info(entity, command)
        async_add_entities([entity])


    async_dispatcher_connect(hass, f"{DOMAIN}_create_entity", _handler)
