import logging
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from .const import DOMAIN
from .entities import DynamicNumber

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the number platform dynamically."""
    _LOGGER.debug("Setting up number platform")

    processor = hass.data[DOMAIN][config_entry.entry_id]

    def add_dynamic_entities():
        numbers = [
            entity for entity in processor.get_all_entities()
            if isinstance(entity, DynamicNumber)
        ]
        _LOGGER.debug("Registering %d number entities", len(numbers))
        async_add_entities(numbers)

    # First call immediately in case entities already exist
    add_dynamic_entities()

    # Also hook into reload signal
    async_dispatcher_connect(
        hass, f"{DOMAIN}_platform_reload", add_dynamic_entities
    )

    return True