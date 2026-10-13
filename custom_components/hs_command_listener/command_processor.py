
import logging
from dataclasses import asdict
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import device_registry as dr
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
            # Restore the complete create command. Older stored records contain only
            # type/entityID/name, so missing optional fields use Command defaults.
            cmd = Command.from_dict({
                **item,
                "command": COMMAND_CREATE,
                "force": False
            })

            await self._dispatch_create(
                cmd.type,
                cmd.entityID,
                cmd.name,
                cmd
            )


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
        if cmd.type is None or cmd.entityID is None:
            _LOGGER.warning("CREATE/DELETE requires type and entityID")
            return
        # Remove any duplicate record in self.entities
        self.entities = [e for e in self.entities if not (e[STR_TYPE]==cmd.type and e[STR_ENTITYID]==cmd.entityID)]
        await self._dispatch_create(cmd.type, cmd.entityID, cmd.name, cmd)
        # Preserve all entity-specific creation parameters so the entity can be
        # recreated identically after Home Assistant restarts.
        self.entities.append(asdict(cmd))
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


    @staticmethod
    def _entity_domain(entity_type: str) -> str:
        """Return the Home Assistant domain for a command entity type."""

        return "switch" if entity_type.upper() == "TOGGLE" else entity_type.lower()


    def _remove_empty_device(self, device_id: str | None) -> None:
        """Remove a Home Assistant device when it has no registered entities."""

        if device_id is None:
            return

        entity_registry = er.async_get(self.hass)

        # Disabled entities still belong to the device, so include them in the check.
        if er.async_entries_for_device(
            entity_registry,
            device_id,
            include_disabled_entities=True,
        ):
            return

        device_registry = dr.async_get(self.hass)
        device = device_registry.async_get(device_id)
        if device is None:
            return

        device_registry.async_remove_device(device_id)
        _LOGGER.debug("Removed empty device from registry: %s", device.name)


    async def _delete(self, cmd: Command):
        if cmd.type is None or cmd.entityID is None:
            _LOGGER.warning("CREATE/DELETE requires type and entityID")
            return

        uid = f"{cmd.type.lower()}_{cmd.entityID}"
        entity_id = f"{self._entity_domain(cmd.type)}.{cmd.entityID}"

        # 1️ Remove from registry
        registry = er.async_get(self.hass)
        to_remove = [e for e in registry.entities.values() if e.unique_id == uid]

        # Remember affected devices before removing their entities from the registry.
        device_ids = {
            e.device_id
            for e in to_remove
            if e.device_id is not None
        }

        for entry in to_remove:
            registry.async_remove(entry.entity_id)
            _LOGGER.debug("Removed entity from registry: %s", entry.entity_id)

        # Remove the HA device if this was its last registered entity.
        for device_id in device_ids:
            self._remove_empty_device(device_id)

        # 2️ Remove from the running state-machine
        self.hass.states.async_remove(entity_id)

        # 3️ Update our own storage
        self.entities = [e for e in self.entities if not (e[STR_TYPE]==cmd.type and e[STR_ENTITYID]==cmd.entityID)]
        await self.store.async_save(self.entities)


    async def _purge(self) -> None:
        """Delete every dynamic entity we know about — registry, states, storage."""
        registry = er.async_get(self.hass)
        device_ids = set()

        # iterate over a copy, because we'll mutate self.entities
        for item in list(self.entities):
            entity_type = item[STR_TYPE]
            entity_id   = item[STR_ENTITYID]

            # full entity_id, e.g. "switch.homeseer_713"
            full_id = f"{self._entity_domain(entity_type)}.{entity_id}"

            # 1️. remove from registry
            ent = registry.async_get(full_id)
            if ent:
                if ent.device_id is not None:
                    device_ids.add(ent.device_id)

                registry.async_remove(full_id)

            # 2️. remove from running state-machine
            self.hass.states.async_remove(full_id)

            # 3️. drop from our internal list
            self.entities.remove(item)

        # Remove any devices which became empty after the purge.
        for device_id in device_ids:
            self._remove_empty_device(device_id)

        await self.store.async_save(self.entities)
        _LOGGER.warning("All dynamic entities purged from registry, state, and storage")



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
            await self._purge()
            return True

        return False