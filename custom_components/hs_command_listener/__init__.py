import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.dispatcher import async_dispatcher_send


from .const import DOMAIN, PLATFORMS
from .command_processor import CommandProcessor

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry: ConfigEntry):
    # Initialize command processor
    processor = CommandProcessor(hass)

    # forward the platforms FIRST
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # now restore entities (platforms are ready)
    await processor.async_initialize()
    _LOGGER.debug("CommandProcessor initialized with entities: %s", processor.entities)

    # Store processor in hass.data for later access/unload
    hass.data.setdefault(DOMAIN, {})["processor"] = processor
    ###########################################
    hass.async_create_task(processor.monitor())
    ###########################################
    _LOGGER.debug("CommandProcessor monitoring started")

    # Forward setup to platform(s), like text
    #await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Notify dynamic platforms to register ?
    async_dispatcher_send(hass, f"{DOMAIN}_platform_reload")

    return True
