
import logging
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import DOMAIN, ENTITY_ID_COMMAND, STR_ENTITYID, STR_NAME, STR_TYPE
from .const import COMMAND_DEBUG, COMMAND_PURGE, COMMAND_CREATE, COMMAND_DELETE, COMMAND_ENABLE, COMMAND_DISABLE

from .command import Command
from .storage import EntityStore

_LOGGER = logging.getLogger(__name__)

class CommandProcessor:
    def __init__(self, hass):
        self.hass = hass
        self.store = EntityStore(hass)
        self.entities = []


    async def async_initialize(self):
        self.entities = await self.store.async_load()
        _LOGGER.debug("Restoring %s entities from storage", len(self.entities))
        for item in self.entities:
            await self._dispatch_create(item[STR_TYPE], item[STR_ENTITYID], item[STR_NAME], Command(
                command=COMMAND_CREATE,
                type=item[STR_TYPE],
                name=item[STR_NAME],
                entityID=item[STR_ENTITYID],
                force=False
            ))


    async def monitor(self):
        _LOGGER.debug("Monitoring state changes for %s", ENTITY_ID_COMMAND)

        async def _listener(event):
            entity_id = event.data.get("entity_id")
            if entity_id.startswith("text."):
                _LOGGER.debug("Event state change from id: '%s', data: %s", entity_id, event.data)

            if entity_id != f"text.{ENTITY_ID_COMMAND}":
                return

            state = event.data.get("new_state")
            _LOGGER.debug("Detected text entity state change: %s", state)
            if not state or not state.state:
                return

            #######################################
            await self.process_command(state.state)
            #######################################

        self.hass.bus.async_listen("state_changed", _listener)


    # Example: {"command": "create", "type": "TOGGLE", "name": "XXX"}
    async def process_command(self, raw: str):
        try:
            if not raw.strip():
                _LOGGER.debug("Empty command received; ignoring")
                return
            cmd = Command.from_json(raw)
        except Exception as exc:
            _LOGGER.warning("Invalid command JSON: %s", exc)
            return

        #####################################################################
        if await self._handle_special_command(cmd):
            return
        #####################################################################

        if cmd.command == COMMAND_CREATE:
            await self._create(cmd)
        elif cmd.command == COMMAND_DELETE:
            await self._delete(cmd)
        else:
            _LOGGER.warning("Unsupported command: %s", cmd.command)


    async def _create(self, cmd: Command):
        _LOGGER.debug("Processing CREATE command: %s", cmd)
        # Remove any duplicate record in self.entities
        self.entities = [e for e in self.entities if not (e[STR_TYPE]==cmd.type and e[STR_ENTITYID]==cmd.entityID)]
        await self._dispatch_create(cmd.type, cmd.entityID, cmd.name, cmd)
        self.entities.append({STR_TYPE: cmd.type, STR_ENTITYID: cmd.entityID, STR_NAME: cmd.name})
        await self.store.async_save(self.entities)


    async def _dispatch_create(self, etype, entity_id, name, cmd):
        async_dispatcher_send(
            self.hass,
            f"{DOMAIN}_create_entity",
            etype.upper(),
            entity_id,
            name,
            cmd
        )


    async def _delete(self, cmd: Command):
        uid = f"{cmd.type.lower()}_{cmd.entityID}"
        entity_id = f"{cmd.type.lower()}.{cmd.entityID}"

        # 1️ Remove from registry
        registry = er.async_get(self.hass)
        to_remove = [e.entity_id for e in registry.entities.values() if e.unique_id == uid]
        for ent_id in to_remove:
            registry.async_remove(ent_id)
            _LOGGER.debug("Removed entity from registry: %s", ent_id)

        # 2️ Remove from the running state-machine
        self.hass.states.async_remove(entity_id)

        # 3️ Remove the preserved “restore” entry so it won’t come back on restart
        restorer: RestoreStateData | None = self.hass.data.get("restore_state")
        if restorer and entity_id in restorer.last_states:
            del restorer.last_states[entity_id]

        # 4️ Update our own storage
        self.entities = [e for e in self.entities if not (e[STR_TYPE]==cmd.type and e[STR_ENTITYID]==cmd.entityID)]
        await self.store.async_save(self.entities)


    async def _purge(self):
        self.entities.clear()
        await self.store.async_save(self.entities)
        _LOGGER.warning("All entities purged")


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
            self._purge()
            return True

        return False