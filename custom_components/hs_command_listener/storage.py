from homeassistant.helpers.storage import Store
from .const import DOMAIN, STORAGE_KEY, ENTITY_ID_COMMAND

STORAGE_VERSION = 1

class EntityStore:
    def __init__(self, hass):
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)

    async def async_load(self):
        data = await self._store.async_load()
        return data or []

    async def async_save(self, entities):
        await self._store.async_save(entities)
