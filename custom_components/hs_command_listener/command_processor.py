import re
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.dispatcher import async_dispatcher_send
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
            await self._create_entity(entity_type, entityID, name, command=None, persist=False)
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

        #####################################################################
        if await self._handle_special_command(command):
            return
        #####################################################################

        entity_type = command.type.upper()
        name = command.name
        entityID = command.entityID
        force = getattr(command, "force", True)

        cmd_type = command.command.lower()

        if cmd_type == "create":
            await self._handle_create_command(command)
        elif cmd_type == "delete":
            await self._delete_entity(command)
        else:
            _LOGGER.debug("Unsupported command type: %s", cmd_type)


    async def _handle_create_command(self, command: Command):
        entity_type = command.type.upper()
        name = command.name
        entityID = command.entityID
        force = getattr(command, "force", True)

        platform_name = self.entity_classes[entity_type](entityID, name).platform
        full_entity_id = f"{platform_name}.{entityID}"
        registry = er.async_get(self.hass)
        existing = registry.async_get(full_entity_id)

        if existing:
            if not force:
                _LOGGER.debug("Entity already exists in registry and force is false: %s", full_entity_id)
                return
            _LOGGER.warning("Entity %s already exists; removing from registry to force recreation", full_entity_id)
            registry.async_remove(existing.entity_id)

        # Clean any existing in-memory entry before adding
        self.entities = [
            e for e in self.entities
            if not (e[STR_TYPE] == entity_type and e[STR_ENTITYID] == entityID)
        ]

        #####################################################################
        await self._create_entity(entity_type, entityID, name, command=command, persist=True)
        #####################################################################


    async def _create_entity(self, entity_type, entityID, name, command: Command = None, persist=True):
        _LOGGER.debug("Creating entity type=%s entityID=%s name=%s", entity_type, entityID, name)

        if entity_type not in self.entity_classes:
            _LOGGER.warning("Entity type %s not supported and no dynamic class found.", entity_type)
            return

        try:
            entity_class = self.entity_classes[entity_type]

            # Create entity with extra parameters if needed
            if entity_type == "NUMBER":
                min_val = command.min if command else None
                max_val = command.max if command else None
                entity = entity_class(entityID, name, min_val, max_val)

            elif entity_type == "SELECT":
                options = getattr(command, "options", None) if command else None
                entity = entity_class(entityID, name, options)

            else:
                entity = entity_class(entityID, name)

            component = EntityComponent(_LOGGER, entity.platform, self.hass)
            _LOGGER.debug("Assigning unique_id: %s", entity._attr_unique_id)
            await component.async_add_entities([entity])
            _LOGGER.debug("Dynamic entity created: %s.%s", entity.platform, entityID)

        except Exception as e:
            _LOGGER.exception("Error creating dynamic entity %s: %s", entityID, e)
            return

        if persist:
            self.entities.append({STR_TYPE: entity_type, STR_ENTITYID: entityID, STR_NAME: name})
            await self.store.async_save(self.entities)
            _LOGGER.debug("Persisted entities updated: %s", self.entities)


    async def _delete_entity(self, command: Command):
        entity_type = command.type.upper()
        entity_id = command.entityID

        if not entity_type or not entity_id:
            _LOGGER.warning("Missing type or entityID in delete command")
            return

        try:
            # Get platform name (e.g. "switch", "number")
            entity_class = self.entity_classes.get(entity_type)
            if not entity_class:
                _LOGGER.warning("Unknown entity type: %s", entity_type)
                return

            platform = entity_class(entity_id, "dummy").platform
            full_entity_id = f"{platform}.{entity_id}"

            # Remove from HA registry
            registry = er.async_get(self.hass)
            if registry.async_get(full_entity_id):
                registry.async_remove(full_entity_id)
                _LOGGER.info("Deleted entity: %s", full_entity_id)
            else:
                _LOGGER.warning("Entity not found in registry: %s", full_entity_id)

            # Remove from internal list
            self.entities = [
                e for e in self.entities
                if not (e[STR_TYPE] == entity_type and e[STR_ENTITYID] == entity_id)
            ]

            await self.store.async_save(self.entities)

        except Exception as e:
            _LOGGER.exception("Failed to delete entity %s: %s", entity_id, e)


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