import logging
from typing import Optional, List
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from homeassistant.components.text import TextEntity

from .command import Command
from .const import DOMAIN, ENTITY_ID_COMMAND

_LOGGER = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# 1. Static text helper for sending commands INTO the integration
# ----------------------------------------------------------------------

class HSTextEntity(TextEntity):

    def __init__(self):
        self._attr_unique_id = ENTITY_ID_COMMAND
        self._attr_has_entity_name = True
        self._attr_name = "HS Command Input"
        self._attr_native_value = ""
        self.entity_id = f"text.{ENTITY_ID_COMMAND}"
        _LOGGER.debug("HSTextEntity created with id %s", ENTITY_ID_COMMAND)

    async def async_set_value(self, value: str):
        _LOGGER.debug("HSTextEntity set to '%s'", value)
        self._attr_native_value = value
        self.async_write_ha_state()


# ----------------------------------------------------------------------
# 2. Dynamic TEXT entity created via dispatcher
# ----------------------------------------------------------------------

class DynamicText(TextEntity):
    """TextEntity created and removed on demand."""

    def __init__(
        self,
        entity_id: str,
        name: str,
        min_chars: int = 0,
        max_chars: int = 255,
        pattern: Optional[str] = None,
    ) -> None:
        self.entity_id = f"text.{entity_id}"
        self._attr_unique_id = f"text_{entity_id}"
        self._attr_name = name
        self._attr_native_value = ""
        self._attr_min = min_chars
        self._attr_max = max_chars
        self._attr_pattern = pattern  # shown as “Pattern” in the UI

    async def async_set_value(self, value: str) -> None:
        self._attr_native_value = value
        self.async_write_ha_state()


# ----------------------------------------------------------------------
# 3. Platform setup – register fixed helper and dynamic handler
# ----------------------------------------------------------------------

#async def async_setup_entry(
#    hass: HomeAssistant,
#    entry: ConfigEntry,
#    async_add_entities: AddEntitiesCallback
#) -> None:
#    _LOGGER.debug("Setting up text platform for hs_command_listener via async_setup_entry")
#    async_add_entities([HSTextEntity()])
#    _LOGGER.debug("HSTextEntity added to platform")

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Register the fixed command helper and listen for dynamic TEXT creation."""

    # 3-A  add the static command-input helper
    async_add_entities([HSTextEntity()])   #  ← no await / no create_task
    #hass.async_create_task(async_add_entities([HSTextEntity()]))

    _LOGGER.debug("HSTextEntity created (command input)")

    # 3-B  dynamic creation via dispatcher
    async def _handle_create(
        entity_type: str,
        entity_id: str,
        name: str,
        command: "Command",
    ) -> None:
        if entity_type != "TEXT":
            return

        entity = DynamicText(
            entity_id,
            name,
            getattr(command, "min", 0),
            getattr(command, "max", 255),
            getattr(command, "pattern", None),
        )

        async_add_entities([entity])         # ← no await
        #await async_add_entities([entity])
        #hass.async_create_task(async_add_entities([entity]))
        _LOGGER.debug("DynamicText created: %s", entity.entity_id)

    async_dispatcher_connect(hass, f"{DOMAIN}_create_entity", _handle_create)