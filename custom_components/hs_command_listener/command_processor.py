import logging
import re

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers import entity_registry as er

from .storage import EntityStore
from .command import Command
from .entities import DynamicToggle, DynamicButton, DynamicNumber, DynamicSelect
from .const import DOMAIN, STORAGE_KEY, ENTITY_ID_COMMAND, STR_ENTITYID, STR_NAME, STR_TYPE
from .const import COMMAND_DEBUG, COMMAND_PURGE, COMMAND_CREATE, COMMAND_ENABLE, COMMAND_DISABLE

_LOGGER = logging.getLogger(__name__)
DEBUG_ENABLED = True # False



class CommandProcessor:
    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self.store = EntityStore(hass)
        self.entities = []  # list of dicts: {type, name}
        self.entity_classes = {
            "TOGGLE": DynamicToggle,
            "BUTTON": DynamicButton,
            "NUMBER": DynamicNumber,
            "SELECT": DynamicSelect
        }

        _LOGGER.debug("CommandProcessor instantiated")

    async def async_initialize(self):
        stored = await self.store.async_load()
        _LOGGER.debug("Loaded persisted entities: %s", stored)
        normalized_entities = []
        
        for item in stored:
            entity_type = item.get(STR_TYPE)
            name = item.get(STR_NAME)
            entityID = item.get(STR_ENTITYID)
        
            # Fallback for legacy entries missing 'entityID'
            if not entityID:
                entityID = name.strip().lower().replace(" ", "_")
                _LOGGER.warning("Legacy entity entry missing entityID; derived as: %s", entityID)
            
            #####################################################################
            await self._create_entity(entity_type, entityID, name, persist=False)
            #####################################################################

            normalized_entities.append({
                STR_TYPE: entity_type,
                STR_NAME: name,
                STR_ENTITYID: entityID
            })
        
        self.entities = normalized_entities
        await self.store.async_save(self.entities)


    async def async_shutdown(self):
        # implement cleanup if needed
        pass


    async def monitor(self):
        _LOGGER.debug("Monitoring state changes for %s", ENTITY_ID_COMMAND)
        async def handle_state_change(event):
            entity_id = event.data.get("entity_id")

            if entity_id.startswith("text."):
                _LOGGER.debug("Event state change from id: '%s', data: %s", entity_id, event.data)
            
            if entity_id != f"text.{ENTITY_ID_COMMAND}":
                return

            new_value = event.data.get("new_state").state
            _LOGGER.debug("Detected text entity state change: %s", new_value)
            await self.process_command(new_value)

        self.hass.bus.async_listen("state_changed", handle_state_change)


    # Example: {"command": "create", "type": "TOGGLE", "name": "XXX"}
    async def process_command(self, cmd: str):
        _LOGGER.debug("Processing command: %s", cmd)

        try:
            if not cmd.strip():
                _LOGGER.debug("Empty command received; ignoring")
                return
            command = Command.from_json(cmd)
        except Exception as e:
            _LOGGER.warning("Invalid command input or JSON parsing failed: %s", e)
            return

        if not command:
            _LOGGER.debug("Command is not valid JSON or missing fields")
            return

        _LOGGER.debug("Processing command: %s", command)

        if await self._handle_special_command(command):
            return

        if command.command.lower() != "create":
            _LOGGER.debug("Unsupported command type: %s", command.command)
            return

        entity_type = command.type.upper()
        name = command.name
        entityID = command.entityID
        force = getattr(command, "force", True)

        if any(e for e in self.entities if e[STR_ENTITYID] == entityID and e[STR_TYPE] == entity_type):
            if not force:
                _LOGGER.debug("Entity already exists: %s %s", entity_type, entityID)
                return
            else:
                # --- START CHANGE: Force delete existing entity from registry ---
                registry = er.async_get(self.hass)
                platform_name = self.entity_classes[entity_type](entityID, name).platform
                existing = registry.async_get(f"{platform_name}.{entityID}")
                if existing:
                    _LOGGER.warning("Entity %s already exists; removing from registry to force recreation", existing.entity_id)
                    registry.async_remove(existing.entity_id)
                # --- END CHANGE ---

        #####################################################################
        await self._create_entity(entity_type, entityID, name, persist=True)
        #####################################################################



    async def _create_entity(self, entity_type, entityID, name, persist=True):
        _LOGGER.debug("Creating entity type=%s entityID=%s name=%s", entity_type, entityID, name)

        if entity_type in self.entity_classes:
            try:
                entity_class = self.entity_classes[entity_type]

                entity = entity_class(entityID, name)

                component = EntityComponent(_LOGGER, entity.platform, self.hass)
                _LOGGER.debug("Assigning unique_id: %s", entity._attr_unique_id)
                await component.async_add_entities([entity])
                _LOGGER.debug("Dynamic entity created: %s.%s", entity.platform, entityID)
            except Exception as e:
                _LOGGER.exception("Error creating dynamic entity %s: %s", entityID, e)
                return
        else:
            _LOGGER.warning("Entity type %s not supported and no dynamic class found.", entity_type)
            return

        if persist:
            self.entities.append({STR_TYPE: entity_type, STR_ENTITYID: entityID, STR_NAME: name})
            await self.store.async_save(self.entities)
            _LOGGER.debug("Persisted entities updated: %s", self.entities)


    async def _handle_special_command(self, command: Command) -> bool:
        global DEBUG_ENABLED
        cmd = command.command.lower()
        if cmd == COMMAND_DEBUG:
            if command.type.upper() == COMMAND_ENABLE:
                DEBUG_ENABLED = True
                _LOGGER.setLevel(logging.DEBUG)
                _LOGGER.debug("Debug logging ENABLED")
            elif command.type.upper() == COMMAND_DISABLE:
                DEBUG_ENABLED = False
                _LOGGER.setLevel(logging.INFO)
                _LOGGER.info("Debug logging DISABLED")
            else:
                _LOGGER.warning("Unknown debug command type: %s", command.type)
            return True
        elif cmd == COMMAND_PURGE:
            self.entities = []
            await self.store.async_save(self.entities)
            _LOGGER.warning("All dynamically persisted entities have been purged")
            return True
        return False