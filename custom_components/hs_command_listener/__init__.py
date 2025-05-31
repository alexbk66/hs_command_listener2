import logging
from homeassistant.core import HomeAssistant
from homeassistant.helpers import discovery
from .command_processor import CommandProcessor
from .const import DOMAIN, STORAGE_KEY, ENTITY_ID_COMMAND

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict):
    _LOGGER.debug("Setting up hs_command_listener integration")

    # Load the text platform to create the command input
    await discovery.async_load_platform(hass, "text", DOMAIN, {}, config)
    _LOGGER.debug("Text platform loaded")

    # Initialize command processor (loads persisted entities)
    processor = CommandProcessor(hass)
    await processor.async_initialize()
    _LOGGER.debug("CommandProcessor initialized with entities: %s", processor.entities)
    await processor.monitor()
    _LOGGER.debug("CommandProcessor monitoring started")
    return True
