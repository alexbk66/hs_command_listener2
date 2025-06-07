import logging
import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.helpers import discovery
from homeassistant.config_entries import ConfigEntry

from .command_processor import CommandProcessor
from .const import DOMAIN, STORAGE_KEY, ENTITY_ID_COMMAND


CONFIG_SCHEMA = vol.Schema({}, extra=vol.ALLOW_EXTRA)
_LOGGER = logging.getLogger(__name__)


PLATFORM = "text"
PLATFORMS = [PLATFORM] # , "switch"


async def _setup_command_processor(hass: HomeAssistant):
    """Initialize and start the command processor."""
    processor = CommandProcessor(hass)
    await processor.async_initialize()
    _LOGGER.debug("CommandProcessor initialized with entities: %s", processor.entities)
    await processor.monitor()
    _LOGGER.debug("CommandProcessor monitoring started")
    return processor


#async def async_setup(hass: HomeAssistant, config: dict):
#    """Set up via YAML (legacy support)."""
#    
#    _LOGGER.debug("Setting up hs_command_listener integration")
#
#    # Load the text platform to create the command input
#    await discovery.async_load_platform(hass, PLATFORM, DOMAIN, {}, config)
#    _LOGGER.debug("Text platform loaded")
#
#    # Initialize command processor
#    await _setup_command_processor(hass)
#
#    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up from a config entry."""
    _LOGGER.debug("Setting up hs_command_listener integration via config entry")

    # Get configuration data from the config entry
    # entry.data contains the data from the config flow
    #config_data = entry.data

    # Initialize command processor
    processor = await _setup_command_processor(hass)

    # Store processor in hass.data for later access/unload
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = processor

    # Forward setup to platform(s), like text
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        processor = hass.data[DOMAIN].pop(entry.entry_id, None)
        if processor:
            await processor.async_shutdown()  # implement cleanup if needed
    return unload_ok