import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.components.button import ButtonEntity
from homeassistant.components.number import NumberEntity
from homeassistant.components.select import SelectEntity

_LOGGER = logging.getLogger(__name__)

class DynamicToggle(SwitchEntity):
    def __init__(self, entity_id, name):
        self.entity_id = f"switch.{entity_id}"
        self._attr_name = name
        self._attr_unique_id = f"toggle_{entity_id}"
        self._attr_is_on = False
        self._attr_should_poll = False
        self.platform = "switch"

    @property
    def unique_id(self):
        return self._attr_unique_id

    @property
    def name(self):
        return self._attr_name

    @property
    def is_on(self):
        return self._attr_is_on

    @property
    def available(self):
        return True

    async def async_turn_on(self, **kwargs):
        _LOGGER.debug("Turning ON %s", self.entity_id)
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        _LOGGER.debug("Turning OFF %s", self.entity_id)
        self._attr_is_on = False
        self.async_write_ha_state()


class DynamicButton(ButtonEntity):
    def __init__(self, entity_id, name):
        self._attr_name = name
        self._attr_unique_id = f"button_{entity_id}"
        self.platform = "button"
        self._pressed = False

    @property
    def unique_id(self):
        return self._attr_unique_id

    async def async_press(self):
        _LOGGER.debug("Button pressed: %s", self._attr_name)
        self._pressed = True
        self.async_write_ha_state()


class DynamicNumber(NumberEntity):
    def __init__(self, entity_id, name):
        self._attr_name = name
        self._attr_unique_id = f"number_{entity_id}"
        self.platform = "number"
        self._attr_native_value = 0
        self._attr_min_value = 0
        self._attr_max_value = 100
        self._attr_step = 1
        self._attr_should_poll = False

    @property
    def unique_id(self):
        return self._attr_unique_id

    async def async_set_native_value(self, value):
        _LOGGER.debug("Setting number %s to %s", self._attr_name, value)
        self._attr_native_value = value
        self.async_write_ha_state()


class DynamicSelect(SelectEntity):
    def __init__(self, entity_id, name):
        self._attr_name = name
        self._attr_unique_id = f"select_{entity_id}"
        self.platform = "select"
        self._attr_options = ["Option 1", "Option 2", "Option 3"]
        self._attr_current_option = self._attr_options[0]
        self._attr_should_poll = False

    @property
    def unique_id(self):
        return self._attr_unique_id

    async def async_select_option(self, option: str):
        _LOGGER.debug("Select %s changed to %s", self._attr_name, option)
        if option in self._attr_options:
            self._attr_current_option = option
            self.async_write_ha_state()

