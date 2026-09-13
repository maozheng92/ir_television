"""Voluptuous schemas and selectors for the config / options flows."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .actions import (
    button_entity_ids,
    button_press_interval,
    button_repeat_default,
    parse_broadlink_codes_payload,
    summarize_action,
)
from .const import (
    ACTION_BROADLINK,
    ACTION_BUTTON,
    ATTR_COMMAND,
    ATTR_DEVICE,
    ATTR_ENTITY_ID,
    ATTR_NUM_REPEATS,
    ATTR_TYPE,
    CONF_ACTION_TYPE,
    CONF_BUTTON_ENTITY,
    CONF_BUTTON_REPEATS,
    CONF_COMMAND,
    CONF_DEFAULT_DEVICE,
    CONF_DEFAULT_REMOTE,
    CONF_DEVICE,
    CONF_INTERVAL,
    CONF_MANUFACTURER,
    CONF_NAME,
    CONF_REORDER_ACTION,
    CONF_SOURCE_ORDER,
    DEFAULT_BUTTON_INTERVAL,
    DEFAULT_MANUFACTURER,
    REORDER_ACTION_APPLY,
    REORDER_ACTION_BACK,
    CONF_NUM_REPEATS,
    CONF_POWER_SENSOR,
    CONF_POWER_SENSOR_INVERT,
    CONF_REMOTE_ENTITY,
    CONF_SOURCE_NAME,
    POWER_MODE_ON_OFF,
    POWER_MODE_SKIP,
    POWER_MODE_TOGGLE,
)


def _text(multiline: bool = False) -> TextSelector:
    return TextSelector(
        TextSelectorConfig(type=TextSelectorType.TEXT, multiline=multiline)
    )


def _state_label(state: State | None, entity_id: str) -> str:
    if state is None:
        return entity_id
    name = state.name or entity_id
    if name == entity_id:
        return entity_id
    return f"{name} ({entity_id})"


def entity_dropdown(
    hass: HomeAssistant,
    domain: str,
    *,
    current: str | None = None,
) -> SelectSelector | TextSelector:
    """Dropdown of current entities in a domain; text field if none exist."""
    entity_ids = list(hass.states.async_entity_ids(domain))
    options: list[dict[str, str]] = []
    seen: set[str] = set()
    for entity_id in entity_ids:
        options.append(
            {
                "value": entity_id,
                "label": _state_label(hass.states.get(entity_id), entity_id),
            }
        )
        seen.add(entity_id)
    if current and current not in seen:
        options.append({"value": current, "label": current})
    if not options:
        return _text()
    options.sort(key=lambda item: item["label"].lower())
    return SelectSelector(
        SelectSelectorConfig(
            options=options,
            mode=SelectSelectorMode.DROPDOWN,
            custom_value=False,
            sort=False,
        )
    )


def entity_multi_dropdown(
    hass: HomeAssistant,
    domain: str,
    *,
    current: list[str] | None = None,
) -> SelectSelector | TextSelector:
    """Multi-select of entities; drag to set press order when reorder is available."""
    current_ids = [item for item in (current or []) if isinstance(item, str) and item]
    entity_ids = list(hass.states.async_entity_ids(domain))
    options: list[dict[str, str]] = []
    seen: set[str] = set()
    for entity_id in current_ids + entity_ids:
        if entity_id in seen:
            continue
        options.append(
            {
                "value": entity_id,
                "label": _state_label(hass.states.get(entity_id), entity_id),
            }
        )
        seen.add(entity_id)
    if not options:
        return _text()
    config: dict[str, Any] = {
        "options": options,
        "multiple": True,
        "custom_value": False,
        "sort": False,
        "reorder": True,
        "mode": SelectSelectorMode.LIST,
    }
    try:
        selector = SelectSelector(config)
    except (vol.Invalid, TypeError, ValueError):
        fallback = dict(config)
        fallback.pop("reorder", None)
        selector = SelectSelector(fallback)
    raw = getattr(selector, "config", None)
    if isinstance(raw, dict):
        raw["reorder"] = True
        raw["multiple"] = True
        raw["sort"] = False
    return selector


def learned_broadlink_names(hass: HomeAssistant) -> tuple[list[str], list[str]]:
    """Read device and command names from official Broadlink code storage."""
    devices: set[str] = set()
    commands: set[str] = set()
    storage = Path(hass.config.path(".storage"))
    if not storage.is_dir():
        return [], []
    for path in storage.glob("broadlink_remote_*_codes"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            continue
        found_devices, found_commands = parse_broadlink_codes_payload(payload)
        devices.update(found_devices)
        commands.update(found_commands)
    return sorted(devices), sorted(commands)


def _name_dropdown(names: list[str], *, current: str = "") -> SelectSelector:
    options = list(names)
    if current and current not in options:
        options = [current, *options]
    return SelectSelector(
        SelectSelectorConfig(
            options=options,
            mode=SelectSelectorMode.DROPDOWN,
            custom_value=True,
        )
    )


def name_schema(
    default: str | None = None,
    manufacturer: str | None = None,
) -> vol.Schema:
    """TV display name plus HomeKit / device manufacturer."""
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=default or ""): _text(),
            vol.Required(
                CONF_MANUFACTURER,
                default=manufacturer or DEFAULT_MANUFACTURER,
            ): _text(),
        }
    )


def _source_order_selector(names: list[str]) -> SelectSelector:
    """List every source and enable the frontend drag handle when available."""
    config: dict[str, Any] = {
        "options": list(names),
        "multiple": True,
        "custom_value": False,
        "sort": False,
        "reorder": True,
    }
    try:
        selector = SelectSelector(config)
    except (vol.Invalid, TypeError, ValueError):
        fallback = dict(config)
        fallback.pop("reorder", None)
        selector = SelectSelector(fallback)
    raw = getattr(selector, "config", None)
    if isinstance(raw, dict):
        raw["reorder"] = True
        raw["multiple"] = True
        raw["sort"] = False
    return selector


def source_reorder_schema(names: list[str]) -> vol.Schema:
    """Show the full source list for drag-and-drop reorder, plus a back action."""
    return vol.Schema(
        {
            vol.Required(
                CONF_REORDER_ACTION, default=REORDER_ACTION_APPLY
            ): SelectSelector(
                SelectSelectorConfig(
                    options=[REORDER_ACTION_BACK, REORDER_ACTION_APPLY],
                    mode=SelectSelectorMode.LIST,
                    translation_key="reorder_action",
                )
            ),
            vol.Required(CONF_SOURCE_ORDER, default=list(names)): _source_order_selector(
                names
            ),
        }
    )


def defaults_schema(hass: HomeAssistant, data: dict[str, Any]) -> vol.Schema:
    """Optional default Broadlink remote + device name."""
    current_remote = data.get(CONF_DEFAULT_REMOTE) or None
    devices, _commands = learned_broadlink_names(hass)
    current_device = data.get(CONF_DEFAULT_DEVICE) or ""
    schema: dict[Any, Any] = {}
    remote_key: Any
    if current_remote:
        remote_key = vol.Optional(CONF_DEFAULT_REMOTE, default=current_remote)
    else:
        remote_key = vol.Optional(CONF_DEFAULT_REMOTE)
    schema[remote_key] = entity_dropdown(hass, "remote", current=current_remote)
    if devices:
        if current_device:
            schema[vol.Optional(CONF_DEFAULT_DEVICE, default=current_device)] = (
                _name_dropdown(devices, current=current_device)
            )
        else:
            schema[vol.Optional(CONF_DEFAULT_DEVICE)] = _name_dropdown(
                devices, current=current_device
            )
    else:
        schema[vol.Optional(CONF_DEFAULT_DEVICE, default=current_device)] = _text()
    return vol.Schema(schema)


def power_sensor_schema(
    hass: HomeAssistant,
    sensor: str | None = None,
    invert: bool = False,
) -> vol.Schema:
    """Optional binary_sensor used as TV power feedback."""
    schema: dict[Any, Any] = {}
    if sensor:
        schema[vol.Optional(CONF_POWER_SENSOR, default=sensor)] = entity_dropdown(
            hass, "binary_sensor", current=sensor
        )
    else:
        schema[vol.Optional(CONF_POWER_SENSOR)] = entity_dropdown(
            hass, "binary_sensor", current=sensor
        )
    schema[vol.Required(CONF_POWER_SENSOR_INVERT, default=invert)] = BooleanSelector()
    return vol.Schema(schema)


def power_mode_schema(default: str = POWER_MODE_TOGGLE) -> vol.Schema:
    """Choose how power is mapped."""
    return vol.Schema(
        {
            vol.Required("power_mode", default=default): SelectSelector(
                SelectSelectorConfig(
                    options=[POWER_MODE_TOGGLE, POWER_MODE_ON_OFF, POWER_MODE_SKIP],
                    mode=SelectSelectorMode.LIST,
                    translation_key="power_mode",
                )
            )
        }
    )


def command_multi_schema(keys: tuple[str, ...] | list[str], selected: list[str]) -> vol.Schema:
    """Pick which commands in a group to configure."""
    return vol.Schema(
        {
            vol.Optional("commands", default=selected): SelectSelector(
                SelectSelectorConfig(
                    options=list(keys),
                    multiple=True,
                    mode=SelectSelectorMode.LIST,
                    translation_key="command_key",
                )
            )
        }
    )


def options_group_schema(
    keys: tuple[str, ...] | list[str],
    commands: dict[str, Any],
) -> vol.Schema:
    """Keep / set / remove each command in a group (options flow)."""
    schema: dict[Any, Any] = {}
    for key in keys:
        if commands.get(key):
            options = ["keep", "set", "remove"]
            default = "keep"
        else:
            options = ["skip", "set"]
            default = "skip"
        schema[vol.Required(key, default=default)] = SelectSelector(
            SelectSelectorConfig(
                options=options,
                mode=SelectSelectorMode.DROPDOWN,
                translation_key="cmd_edit",
            )
        )
    return vol.Schema(schema)


def action_schema(
    hass: HomeAssistant,
    *,
    defaults: dict[str, Any],
    existing: dict[str, Any] | None = None,
) -> vol.Schema:
    """Broadlink or button mapping form."""
    existing = existing or {}
    default_type = existing.get(ATTR_TYPE)
    if default_type not in (ACTION_BROADLINK, ACTION_BUTTON):
        default_type = ACTION_BROADLINK

    suggested_remote = existing.get(ATTR_ENTITY_ID) if existing.get(ATTR_TYPE) == ACTION_BROADLINK else None
    suggested_remote = suggested_remote or defaults.get(CONF_DEFAULT_REMOTE)
    suggested_device = ""
    if existing.get(ATTR_TYPE) == ACTION_BROADLINK:
        suggested_device = existing.get(ATTR_DEVICE) or ""
    if not suggested_device:
        suggested_device = defaults.get(CONF_DEFAULT_DEVICE) or ""
    suggested_command = ""
    if existing.get(ATTR_TYPE) == ACTION_BROADLINK:
        suggested_command = existing.get(ATTR_COMMAND) or ""
    suggested_buttons = (
        button_entity_ids(existing) if existing.get(ATTR_TYPE) == ACTION_BUTTON else []
    )
    suggested_repeats = existing.get(ATTR_NUM_REPEATS, 1)
    suggested_button_repeats = button_repeat_default(existing)
    suggested_interval = (
        button_press_interval(existing)
        if existing.get(ATTR_TYPE) == ACTION_BUTTON
        else DEFAULT_BUTTON_INTERVAL
    )

    devices, commands = learned_broadlink_names(hass)
    if suggested_device:
        device_field: Any = _name_dropdown(devices, current=suggested_device) if devices else _text()
    elif devices:
        device_field = _name_dropdown(devices, current=suggested_device)
    else:
        device_field = _text()

    if suggested_command:
        command_field: Any = (
            _name_dropdown(commands, current=suggested_command) if commands else _text()
        )
    elif commands:
        command_field = _name_dropdown(commands, current=suggested_command)
    else:
        command_field = _text()

    schema: dict[Any, Any] = {
        vol.Required(CONF_ACTION_TYPE, default=default_type): SelectSelector(
            SelectSelectorConfig(
                options=[ACTION_BROADLINK, ACTION_BUTTON],
                mode=SelectSelectorMode.LIST,
                translation_key="action_type",
            )
        ),
    }
    if suggested_remote:
        schema[vol.Optional(CONF_REMOTE_ENTITY, default=suggested_remote)] = entity_dropdown(
            hass, "remote", current=suggested_remote
        )
    else:
        schema[vol.Optional(CONF_REMOTE_ENTITY)] = entity_dropdown(
            hass, "remote", current=suggested_remote
        )
    if suggested_device:
        schema[vol.Optional(CONF_DEVICE, default=suggested_device)] = device_field
    else:
        schema[vol.Optional(CONF_DEVICE)] = device_field
    if suggested_command:
        schema[vol.Optional(CONF_COMMAND, default=suggested_command)] = command_field
    else:
        schema[vol.Optional(CONF_COMMAND)] = command_field
    schema[
        vol.Optional(CONF_NUM_REPEATS, default=suggested_repeats)
    ] = NumberSelector(
        NumberSelectorConfig(
            min=1,
            max=10,
            step=1,
            mode=NumberSelectorMode.BOX,
        )
    )
    if suggested_buttons:
        schema[vol.Optional(CONF_BUTTON_ENTITY, default=suggested_buttons)] = (
            entity_multi_dropdown(hass, "button", current=suggested_buttons)
        )
    else:
        schema[vol.Optional(CONF_BUTTON_ENTITY)] = entity_multi_dropdown(
            hass, "button", current=suggested_buttons
        )
    schema[
        vol.Optional(CONF_BUTTON_REPEATS, default=suggested_button_repeats)
    ] = NumberSelector(
        NumberSelectorConfig(
            min=1,
            max=10,
            step=1,
            mode=NumberSelectorMode.BOX,
        )
    )
    schema[
        vol.Optional(CONF_INTERVAL, default=suggested_interval)
    ] = NumberSelector(
        NumberSelectorConfig(
            min=0,
            max=10,
            step=0.1,
            mode=NumberSelectorMode.BOX,
        )
    )
    return vol.Schema(schema)


def source_name_schema(default: str = "") -> vol.Schema:
    """Source display name."""
    return vol.Schema({vol.Required(CONF_SOURCE_NAME, default=default): _text()})


def source_ask_schema(has_sources: bool) -> vol.Schema:
    """Add another source?"""
    return vol.Schema(
        {
            vol.Required("add_source", default=not has_sources): BooleanSelector(),
        }
    )


def source_pick_schema(names: list[str]) -> vol.Schema:
    """Pick an existing source."""
    return vol.Schema(
        {
            vol.Required("source"): SelectSelector(
                SelectSelectorConfig(
                    options=names,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            )
        }
    )


def current_mappings_text(commands: dict[str, Any], keys: tuple[str, ...] | list[str]) -> str:
    """Plain-text list of current mappings for form descriptions."""
    lines: list[str] = []
    for key in keys:
        lines.append(f"{key}: {summarize_action(commands.get(key))}")
    return "\n".join(lines) if lines else "—"
