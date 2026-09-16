"""Config Flow and Options Flow for IR Television."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
import voluptuous as vol

try:
    from homeassistant.config_entries import ConfigFlowResult
except ImportError:  # Home Assistant < 2024.4
    ConfigFlowResult = dict[str, Any]  # type: ignore[misc,assignment]

from .actions import (
    copy_config,
    format_button_sequence,
    format_source_order,
    has_useful_config,
    reorder_sources,
    normalize_power_sensor,
    normalize_source_name,
    parse_action_input,
    parse_source_button_ids,
    parse_source_button_sequence,
    validate_source_name,
)
from .const import (
    ACTION_BUTTON,
    ATTR_ACTION,
    ATTR_NAME,
    ATTR_TYPE,
    CHANNEL_COMMANDS,
    CMD_POWER_TOGGLE,
    CMD_TURN_OFF,
    CMD_TURN_ON,
    CONF_ACTION_TYPE,
    CONF_COMMANDS,
    CONF_DEFAULT_DEVICE,
    CONF_DEFAULT_REMOTE,
    CONF_REMOTE_ENTITY,
    CONF_MANUFACTURER,
    CONF_NAME,
    CONF_POWER_SENSOR,
    CONF_POWER_SENSOR_INVERT,
    CONF_REORDER_ACTION,
    CONF_SOURCE_NAME,
    CONF_SOURCE_ORDER,
    CONF_SOURCES,
    DEFAULT_MANUFACTURER,
    DOMAIN,
    REORDER_ACTION_BACK,
    NAV_COMMANDS,
    PLAYBACK_COMMANDS,
    POWER_COMMANDS,
    POWER_MODE_ON_OFF,
    POWER_MODE_SKIP,
    POWER_MODE_TOGGLE,
    VOLUME_COMMANDS,
    command_label,
)
from .flow_schemas import (
    action_schema,
    command_multi_schema,
    current_mappings_text,
    defaults_schema,
    is_harmony_remote,
    name_schema,
    options_group_schema,
    power_mode_schema,
    power_sensor_schema,
    source_ask_schema,
    source_button_repeats_schema,
    source_name_schema,
    source_pick_schema,
    source_reorder_schema,
)


def _lang(hass) -> str:
    return getattr(getattr(hass, "config", None), "language", None) or "en"


class TelevisionFlowMixin:
    """Shared wizard state and steps for setup and options."""

    _data: dict[str, Any]
    _queue: list[str]
    _after_queue: str
    _source_draft: dict[str, Any]
    _edit_source_index: int | None
    _button_sequence_ids: list[str]
    _options_mode: bool

    def _reset_wizard(self, data: dict[str, Any] | None = None) -> None:
        self._data = data or {
            CONF_NAME: "",
            CONF_COMMANDS: {},
            CONF_SOURCES: [],
            CONF_DEFAULT_REMOTE: None,
            CONF_DEFAULT_DEVICE: None,
            CONF_POWER_SENSOR: None,
            CONF_POWER_SENSOR_INVERT: False,
            CONF_MANUFACTURER: DEFAULT_MANUFACTURER,
        }
        if CONF_COMMANDS not in self._data or self._data[CONF_COMMANDS] is None:
            self._data[CONF_COMMANDS] = {}
        if CONF_SOURCES not in self._data or self._data[CONF_SOURCES] is None:
            self._data[CONF_SOURCES] = []
        self._data.setdefault(CONF_POWER_SENSOR, None)
        self._data.setdefault(CONF_POWER_SENSOR_INVERT, False)
        self._data.setdefault(CONF_MANUFACTURER, DEFAULT_MANUFACTURER)
        self._queue = []
        self._after_queue = "volume_select"
        self._source_draft = {}
        self._edit_source_index = None
        self._button_sequence_ids = []
        self._options_mode = False

    def _cmd_label(self, key: str) -> str:
        return command_label(_lang(self.hass), key)

    def _queue_commands(self, keys: list[str], after: str) -> None:
        self._queue = [key for key in keys if key]
        self._after_queue = after

    async def _proceed_after_queue(self) -> ConfigFlowResult:
        dest = self._after_queue
        handlers = {
            "volume_select": self.async_step_volume_select,
            "playback_select": self.async_step_playback_select,
            "channel_select": self.async_step_channel_select,
            "nav_select": self.async_step_nav_select,
            "source_ask": self.async_step_source_ask,
            "power_sensor": self.async_step_power_sensor,
            "source_finish_add": self._finish_source_add,
            "source_finish_edit": self._finish_source_edit,
        }
        options_menu = getattr(self, "async_step_init", None)
        if callable(options_menu):
            handlers["options_menu"] = options_menu
        handler = handlers.get(dest)
        if handler is None:
            return await self.async_step_source_ask()
        return await handler()

    async def async_step_defaults(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Optional default IR remote (Broadlink or Harmony Hub) + device."""
        if user_input is not None:
            remote = user_input.get(CONF_DEFAULT_REMOTE) or None
            device = (user_input.get(CONF_DEFAULT_DEVICE) or "").strip() or None
            self._data[CONF_DEFAULT_REMOTE] = remote
            self._data[CONF_DEFAULT_DEVICE] = device
            if self._options_mode:
                return await self.async_step_init()
            # One power key on the entity row (turn on / turn off share it).
            self._queue_commands([CMD_POWER_TOGGLE], "power_sensor")
            return await self.async_step_command()

        return self.async_show_form(
            step_id="defaults",
            data_schema=defaults_schema(self.hass, self._data),
        )

    async def async_step_power_mode(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose on/off, toggle, or skip."""
        commands = self._data[CONF_COMMANDS]
        if commands.get(CMD_POWER_TOGGLE):
            current = POWER_MODE_TOGGLE
        elif commands.get(CMD_TURN_ON) or commands.get(CMD_TURN_OFF):
            current = POWER_MODE_ON_OFF
        else:
            current = POWER_MODE_SKIP if self._options_mode else POWER_MODE_TOGGLE

        if user_input is not None:
            mode = user_input["power_mode"]
            for key in POWER_COMMANDS:
                commands.pop(key, None)
            if mode == POWER_MODE_SKIP:
                if self._options_mode:
                    return await self.async_step_init()
                return await self.async_step_power_sensor()
            if mode == POWER_MODE_TOGGLE:
                self._queue_commands(
                    [CMD_POWER_TOGGLE],
                    "options_menu" if self._options_mode else "power_sensor",
                )
            else:
                self._queue_commands(
                    [CMD_TURN_ON, CMD_TURN_OFF],
                    "options_menu" if self._options_mode else "power_sensor",
                )
            return await self.async_step_command()

        return self.async_show_form(
            step_id="power_mode",
            data_schema=power_mode_schema(current),
            description_placeholders={
                "current": current_mappings_text(commands, POWER_COMMANDS),
            },
        )

    async def async_step_power_sensor(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Optional binary_sensor for real on/off feedback."""
        errors: dict[str, str] = {}
        if user_input is not None:
            sensor, error = normalize_power_sensor(user_input.get(CONF_POWER_SENSOR))
            if error:
                errors["base"] = error
            else:
                self._data[CONF_POWER_SENSOR] = sensor
                self._data[CONF_POWER_SENSOR_INVERT] = bool(
                    user_input.get(CONF_POWER_SENSOR_INVERT)
                )
                if self._options_mode:
                    return await self.async_step_init()
                return await self.async_step_volume_select()

        current = self._data.get(CONF_POWER_SENSOR)
        return self.async_show_form(
            step_id="power_sensor",
            data_schema=power_sensor_schema(
                self.hass,
                current,
                bool(self._data.get(CONF_POWER_SENSOR_INVERT)),
            ),
            errors=errors,
            description_placeholders={
                "current_sensor": current or "—",
            },
        )

    async def async_step_command(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure the next queued command mapping."""
        if not self._queue:
            return await self._proceed_after_queue()

        key = self._queue[0]
        errors: dict[str, str] = {}
        if user_input is not None:
            action, error = parse_action_input(
                user_input,
                defaults=self._data,
                require_device=is_harmony_remote(
                    self.hass,
                    user_input.get(CONF_REMOTE_ENTITY)
                    or self._data.get(CONF_DEFAULT_REMOTE),
                ),
            )
            if error:
                errors["base"] = error
            else:
                assert action is not None
                self._data[CONF_COMMANDS][key] = action
                self._queue.pop(0)
                if self._queue:
                    return await self.async_step_command()
                return await self._proceed_after_queue()

        existing = self._data[CONF_COMMANDS].get(key)
        return self.async_show_form(
            step_id="command",
            data_schema=action_schema(
                self.hass,
                defaults=self._data,
                existing=existing,
            ),
            errors=errors,
            description_placeholders={
                "command": self._cmd_label(key),
                "command_key": key,
            },
        )

    async def async_step_volume_select(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pick volume commands (initial setup)."""
        return await self._async_group_select(
            user_input,
            step_id="volume_select",
            keys=VOLUME_COMMANDS,
            after="playback_select",
        )

    async def async_step_playback_select(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pick playback commands (initial setup)."""
        return await self._async_group_select(
            user_input,
            step_id="playback_select",
            keys=PLAYBACK_COMMANDS,
            after="channel_select",
        )

    async def async_step_channel_select(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pick channel / track commands (initial setup)."""
        return await self._async_group_select(
            user_input,
            step_id="channel_select",
            keys=CHANNEL_COMMANDS,
            after="nav_select",
        )

    async def async_step_nav_select(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pick directional / menu keys (initial setup)."""
        return await self._async_group_select(
            user_input,
            step_id="nav_select",
            keys=NAV_COMMANDS,
            after="source_ask",
        )

    async def _async_group_select(
        self,
        user_input: dict[str, Any] | None,
        *,
        step_id: str,
        keys: tuple[str, ...],
        after: str,
    ) -> ConfigFlowResult:
        commands = self._data[CONF_COMMANDS]
        selected = [key for key in keys if commands.get(key)]
        if user_input is not None:
            chosen = list(user_input.get("commands") or [])
            for key in keys:
                if key not in chosen:
                    commands.pop(key, None)
            self._queue_commands(chosen, after)
            if self._queue:
                return await self.async_step_command()
            return await self._proceed_after_queue()

        return self.async_show_form(
            step_id=step_id,
            data_schema=command_multi_schema(keys, selected),
            description_placeholders={
                "current": current_mappings_text(commands, keys),
            },
        )

    async def async_step_volume(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Options: keep / set / remove volume commands."""
        return await self._async_options_group(user_input, "volume", VOLUME_COMMANDS)

    async def async_step_playback(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Options: keep / set / remove playback commands."""
        return await self._async_options_group(user_input, "playback", PLAYBACK_COMMANDS)

    async def async_step_channel(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Options: keep / set / remove channel commands."""
        return await self._async_options_group(user_input, "channel", CHANNEL_COMMANDS)

    async def async_step_navigation(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Options: keep / set / remove navigation keys."""
        return await self._async_options_group(user_input, "navigation", NAV_COMMANDS)

    async def _async_options_group(
        self,
        user_input: dict[str, Any] | None,
        step_id: str,
        keys: tuple[str, ...],
    ) -> ConfigFlowResult:
        commands = self._data[CONF_COMMANDS]
        if user_input is not None:
            to_set: list[str] = []
            for key in keys:
                choice = user_input.get(key, "keep")
                if choice == "remove":
                    commands.pop(key, None)
                elif choice == "set":
                    to_set.append(key)
            self._queue_commands(to_set, "options_menu")
            if self._queue:
                return await self.async_step_command()
            return await self.async_step_init()

        return self.async_show_form(
            step_id=step_id,
            data_schema=options_group_schema(keys, commands),
            description_placeholders={
                "current": current_mappings_text(commands, keys),
            },
        )

    async def async_step_source_ask(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask whether to add a source, or finish setup."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input.get("add_source"):
                return await self.async_step_source_add()
            if not has_useful_config(self._data[CONF_COMMANDS], self._data[CONF_SOURCES]):
                errors["base"] = "no_commands"
            else:
                return self._finish_create_entry()

        names = [str(src.get(ATTR_NAME, "")) for src in self._data[CONF_SOURCES]]
        return self.async_show_form(
            step_id="source_ask",
            data_schema=source_ask_schema(bool(self._data[CONF_SOURCES])),
            errors=errors,
            description_placeholders={
                "source_count": str(len(self._data[CONF_SOURCES])),
                "source_names": format_source_order(self._data[CONF_SOURCES])
                if names
                else "—",
            },
        )

    async def async_step_source_add(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Name a new source."""
        errors: dict[str, str] = {}
        if user_input is not None:
            name = normalize_source_name(user_input.get(CONF_SOURCE_NAME))
            error = validate_source_name(name, self._data[CONF_SOURCES])
            if error:
                errors["base"] = error
            else:
                self._source_draft = {ATTR_NAME: name}
                self._edit_source_index = None
                self._queue_commands([], "source_finish_add")
                return await self.async_step_source_action()

        return self.async_show_form(
            step_id="source_add",
            data_schema=source_name_schema(),
            errors=errors,
        )

    async def async_step_source_action(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Map the current source to an IR remote or a button."""
        errors: dict[str, str] = {}
        existing = None
        if self._edit_source_index is not None:
            existing = self._data[CONF_SOURCES][self._edit_source_index].get(ATTR_ACTION)
        elif self._source_draft.get(ATTR_ACTION):
            existing = self._source_draft.get(ATTR_ACTION)

        if user_input is not None:
            if user_input.get(CONF_ACTION_TYPE) == ACTION_BUTTON:
                ids, error = parse_source_button_ids(user_input)
                if error:
                    errors["base"] = error
                else:
                    assert ids is not None
                    self._button_sequence_ids = ids
                    return await self.async_step_source_button_repeats()
            else:
                action, error = parse_action_input(
                    user_input,
                    defaults=self._data,
                    require_device=is_harmony_remote(
                        self.hass,
                        user_input.get(CONF_REMOTE_ENTITY)
                        or self._data.get(CONF_DEFAULT_REMOTE),
                    ),
                )
                if error:
                    errors["base"] = error
                else:
                    self._button_sequence_ids = []
                    self._source_draft[ATTR_ACTION] = action
                    if self._edit_source_index is not None:
                        return await self._finish_source_edit()
                    return await self._finish_source_add()

        name = self._source_draft.get(ATTR_NAME, "")
        return self.async_show_form(
            step_id="source_action",
            data_schema=action_schema(
                self.hass,
                defaults=self._data,
                existing=existing,
                allow_button_sequence=True,
            ),
            errors=errors,
            description_placeholders={"source_name": name},
        )

    async def async_step_source_button_repeats(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Set a repeat count for each selected source button."""
        ids = list(self._button_sequence_ids)
        if not ids:
            return await self.async_step_source_action()

        existing = None
        if self._edit_source_index is not None:
            existing = self._data[CONF_SOURCES][self._edit_source_index].get(ATTR_ACTION)
        elif self._source_draft.get(ATTR_ACTION):
            existing = self._source_draft.get(ATTR_ACTION)
        if not isinstance(existing, dict) or existing.get(ATTR_TYPE) != ACTION_BUTTON:
            existing = None

        errors: dict[str, str] = {}
        if user_input is not None:
            action, error = parse_source_button_sequence(ids, user_input)
            if error:
                errors["base"] = error
            else:
                self._source_draft[ATTR_ACTION] = action
                self._button_sequence_ids = []
                if self._edit_source_index is not None:
                    return await self._finish_source_edit()
                return await self._finish_source_add()

        name = self._source_draft.get(ATTR_NAME, "")
        return self.async_show_form(
            step_id="source_button_repeats",
            data_schema=source_button_repeats_schema(ids, existing),
            errors=errors,
            description_placeholders={
                "source_name": name,
                "button_order": format_button_sequence(ids),
            },
        )

    async def _finish_source_add(self) -> ConfigFlowResult:
        self._data[CONF_SOURCES].append(
            {
                ATTR_NAME: self._source_draft[ATTR_NAME],
                ATTR_ACTION: self._source_draft[ATTR_ACTION],
            }
        )
        self._source_draft = {}
        self._button_sequence_ids = []
        if self._options_mode:
            return await self.async_step_sources()
        return await self.async_step_source_ask()

    async def _finish_source_edit(self) -> ConfigFlowResult:
        idx = self._edit_source_index
        assert idx is not None
        self._data[CONF_SOURCES][idx] = {
            ATTR_NAME: self._source_draft[ATTR_NAME],
            ATTR_ACTION: self._source_draft[ATTR_ACTION],
        }
        self._source_draft = {}
        self._edit_source_index = None
        self._button_sequence_ids = []
        return await self.async_step_sources()

    async def async_step_sources(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Options: manage the source list."""
        names = [str(src.get(ATTR_NAME, "")) for src in self._data[CONF_SOURCES]]
        menu = ["source_add"]
        if names:
            menu.extend(["source_edit", "source_delete"])
        if len(names) >= 2:
            menu.append("source_reorder")
        menu.append("init")
        return self.async_show_menu(
            step_id="sources",
            menu_options=menu,
            description_placeholders={
                "source_count": str(len(names)),
                "source_names": format_source_order(self._data[CONF_SOURCES])
                if names
                else "—",
            },
        )

    async def async_step_source_reorder(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """List every source and accept a drag-and-drop permutation."""
        names = [str(src.get(ATTR_NAME, "")) for src in self._data[CONF_SOURCES]]
        if len(names) < 2:
            return await self.async_step_sources()
        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input.get(CONF_REORDER_ACTION) == REORDER_ACTION_BACK:
                return await self.async_step_sources()
            ordered = user_input.get(CONF_SOURCE_ORDER) or []
            new_sources, error = reorder_sources(self._data[CONF_SOURCES], ordered)
            if error:
                errors["base"] = error
            else:
                self._data[CONF_SOURCES] = new_sources
                return await self.async_step_sources()
        return self.async_show_form(
            step_id="source_reorder",
            data_schema=source_reorder_schema(names),
            errors=errors,
            description_placeholders={
                "source_order": format_source_order(self._data[CONF_SOURCES]),
            },
        )

    async def async_step_source_edit(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pick a source to edit."""
        names = [str(src.get(ATTR_NAME, "")) for src in self._data[CONF_SOURCES]]
        if not names:
            return await self.async_step_sources()
        if user_input is not None:
            picked = user_input["source"]
            for idx, src in enumerate(self._data[CONF_SOURCES]):
                if src.get(ATTR_NAME) == picked:
                    self._edit_source_index = idx
                    self._source_draft = {
                        ATTR_NAME: src.get(ATTR_NAME, ""),
                        ATTR_ACTION: dict(src.get(ATTR_ACTION) or {}),
                    }
                    return await self.async_step_source_edit_name()
            return await self.async_step_sources()

        return self.async_show_form(
            step_id="source_edit",
            data_schema=source_pick_schema(names),
        )

    async def async_step_source_edit_name(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Rename a source, then optionally remap its action."""
        errors: dict[str, str] = {}
        current = self._source_draft.get(ATTR_NAME, "")
        if user_input is not None:
            name = normalize_source_name(user_input.get(CONF_SOURCE_NAME))
            error = validate_source_name(
                name, self._data[CONF_SOURCES], exclude_index=self._edit_source_index
            )
            if error:
                errors["base"] = error
            else:
                self._source_draft[ATTR_NAME] = name
                return await self.async_step_source_action()

        return self.async_show_form(
            step_id="source_edit_name",
            data_schema=source_name_schema(current),
            errors=errors,
        )

    async def async_step_source_delete(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Delete a source."""
        names = [str(src.get(ATTR_NAME, "")) for src in self._data[CONF_SOURCES]]
        if not names:
            return await self.async_step_sources()
        if user_input is not None:
            picked = user_input["source"]
            self._data[CONF_SOURCES] = [
                src for src in self._data[CONF_SOURCES] if src.get(ATTR_NAME) != picked
            ]
            return await self.async_step_sources()

        return self.async_show_form(
            step_id="source_delete",
            data_schema=source_pick_schema(names),
        )

    def _finish_create_entry(self) -> ConfigFlowResult:
        raise NotImplementedError


class IRTelevisionConfigFlow(ConfigFlow, TelevisionFlowMixin, domain=DOMAIN):
    """Initial setup wizard."""

    VERSION = 1

    def __init__(self) -> None:
        super().__init__()
        self._reset_wizard()

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow (HA < 2024.12 still passes the entry)."""
        return IRTelevisionOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Name the television."""
        errors: dict[str, str] = {}
        if user_input is not None:
            name = normalize_source_name(user_input.get(CONF_NAME))
            manufacturer = (
                normalize_source_name(user_input.get(CONF_MANUFACTURER))
                or DEFAULT_MANUFACTURER
            )
            if not name:
                errors["base"] = "empty_name"
            else:
                self._data[CONF_NAME] = name
                self._data[CONF_MANUFACTURER] = manufacturer
                return await self.async_step_defaults()

        return self.async_show_form(
            step_id="user",
            data_schema=name_schema(
                self._data.get(CONF_NAME),
                self._data.get(CONF_MANUFACTURER),
            ),
            errors=errors,
        )

    def _finish_create_entry(self) -> ConfigFlowResult:
        return self.async_create_entry(title=self._data[CONF_NAME], data=self._data)


class IRTelevisionOptionsFlow(OptionsFlow, TelevisionFlowMixin):
    """Edit name, commands, and sources after install."""

    def __init__(self, config_entry: ConfigEntry | None = None) -> None:
        try:
            super().__init__(config_entry)  # type: ignore[misc]
        except TypeError:
            super().__init__()
        self._config_entry_compat = config_entry
        self._ready = False
        self._reset_wizard()
        self._options_mode = True

    def _entry(self) -> ConfigEntry:
        entry = getattr(self, "config_entry", None) or self._config_entry_compat
        if entry is None:
            raise RuntimeError("Config entry is not available")
        return entry

    def _ensure(self) -> None:
        if self._ready:
            return
        self._reset_wizard(copy_config(dict(self._entry().data)))
        if not self._data.get(CONF_NAME):
            self._data[CONF_NAME] = self._entry().title
        self._options_mode = True
        self._ready = True

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Options menu."""
        self._ensure()
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "name",
                "defaults",
                "power",
                "power_sensor",
                "volume",
                "playback",
                "channel",
                "navigation",
                "sources",
                "save",
            ],
            description_placeholders={
                "name": self._data.get(CONF_NAME) or self._entry().title,
                "command_count": str(len(self._data[CONF_COMMANDS])),
                "source_count": str(len(self._data[CONF_SOURCES])),
                "power_sensor": self._data.get(CONF_POWER_SENSOR) or "—",
            },
        )

    async def async_step_name(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Rename the television."""
        self._ensure()
        errors: dict[str, str] = {}
        if user_input is not None:
            name = normalize_source_name(user_input.get(CONF_NAME))
            manufacturer = (
                normalize_source_name(user_input.get(CONF_MANUFACTURER))
                or DEFAULT_MANUFACTURER
            )
            if not name:
                errors["base"] = "empty_name"
            else:
                self._data[CONF_NAME] = name
                self._data[CONF_MANUFACTURER] = manufacturer
                return await self.async_step_init()
        return self.async_show_form(
            step_id="name",
            data_schema=name_schema(
                self._data.get(CONF_NAME),
                self._data.get(CONF_MANUFACTURER),
            ),
            errors=errors,
        )

    async def async_step_power(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Reconfigure power from the options menu."""
        self._ensure()
        return await self.async_step_power_mode(user_input)

    async def async_step_power_sensor(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Reconfigure the power binary_sensor from the options menu."""
        self._ensure()
        return await super().async_step_power_sensor(user_input)

    async def async_step_defaults(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        self._ensure()
        return await super().async_step_defaults(user_input)

    async def async_step_volume(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        self._ensure()
        return await super().async_step_volume(user_input)

    async def async_step_playback(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        self._ensure()
        return await super().async_step_playback(user_input)

    async def async_step_channel(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        self._ensure()
        return await super().async_step_channel(user_input)

    async def async_step_navigation(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        self._ensure()
        return await super().async_step_navigation(user_input)

    async def async_step_sources(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        self._ensure()
        return await super().async_step_sources(user_input)

    async def async_step_source_add(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        self._ensure()
        return await super().async_step_source_add(user_input)

    async def async_step_source_reorder(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        self._ensure()
        return await super().async_step_source_reorder(user_input)

    async def async_step_source_action(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        self._ensure()
        return await super().async_step_source_action(user_input)

    async def async_step_source_button_repeats(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        self._ensure()
        return await super().async_step_source_button_repeats(user_input)

    async def async_step_save(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Persist options onto the config entry and reload."""
        self._ensure()
        errors: dict[str, str] = {}
        if not has_useful_config(self._data[CONF_COMMANDS], self._data[CONF_SOURCES]):
            errors["base"] = "no_commands"
            return self.async_show_form(
                step_id="save",
                data_schema=vol.Schema({}),
                errors=errors,
            )

        entry = self._entry()
        self.hass.config_entries.async_update_entry(
            entry,
            data=self._data,
            title=self._data[CONF_NAME],
        )
        return self.async_create_entry(title="", data={})

    def _finish_create_entry(self) -> ConfigFlowResult:
        # Not used in options (save step writes the entry).
        return self.async_abort(reason="unknown")
