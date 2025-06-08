from homeassistant.helpers.storage import Store

STORAGE_VERSION = 1
STORAGE_KEY = "hs_command_listener_entities.json"

class EntityStore:
    def __init__(self, hass):
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)

    async def async_load(self):
        return await self._store.async_load() or []


    async def async_save(self, data):
        await self._store.async_save(data)
