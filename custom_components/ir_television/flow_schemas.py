"""Voluptuous schemas and selectors for the config / options flows."""

from __future__ import annotations

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
    button_repeat_map,
    load_json_file,
    parse_broadlink_codes_payload,
    parse_harmony_config,
    resolve_broadlink_codes_path,
    resolve_harmony_conf_path,
    summarize_action,
)
from .const import (
    ACTION_BROADLINK,
    ACTION_BUTTON,
    ATTR_COMMAND,
    ATTR_DEVICE,
    ATTR_ENTITY_ID,
    ATTR_INTERVAL,
    ATTR_NUM_REPEATS,
    ATTR_TYPE,
    CONF_ACTION_TYPE,
    CONF_BUTTON_ENTITY,
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


def _remote_lookup(
    hass: HomeAssistant, entity_id: str | None
) -> tuple[str | None, list[str]]:
    """Return (platform, identifiers) for a remote entity."""
    if not entity_id or not isinstance(entity_id, str):
        return None, []
    identifiers: list[str] = [entity_id]
    if "." in entity_id:
        identifiers.append(entity_id.split(".", 1)[1])
    platform: str | None = None
    try:
        from homeassistant.helpers import device_registry as dr
        from homeassistant.helpers import entity_registry as er

        ent = er.async_get(hass).async_get(entity_id)
    except Exception:  # noqa: BLE001 — registry is optional during tests
        ent = None
    if ent is not None:
        platform = getattr(ent, "platform", None) or None
        unique_id = getattr(ent, "unique_id", None)
        if unique_id:
            identifiers.append(str(unique_id))
        entry_id = getattr(ent, "config_entry_id", None)
        if entry_id:
            identifiers.append(str(entry_id))
            try:
                entry = hass.config_entries.async_get_entry(entry_id)
            except Exception:  # noqa: BLE001
                entry = None
            if entry is not None:
                if getattr(entry, "unique_id", None):
                    identifiers.append(str(entry.unique_id))
                if getattr(entry, "title", None):
                    identifiers.append(str(entry.title))
                data = getattr(entry, "data", None) or {}
                if isinstance(data, dict):
                    for key in ("unique_id", "name", "hub_name"):
                        if data.get(key):
                            identifiers.append(str(data[key]))
        device_id = getattr(ent, "device_id", None)
        if device_id:
            try:
                device = dr.async_get(hass).async_get(device_id)
            except Exception:  # noqa: BLE001
                device = None
            if device is not None:
                for _domain, ident in getattr(device, "identifiers", None) or ():
                    if ident:
                        identifiers.append(str(ident))
                for conn_type, value in getattr(device, "connections", None) or ():
                    if value:
                        identifiers.append(str(value))
                    if conn_type == "mac" and value:
                        identifiers.append(str(value).replace(":", ""))
    return platform, identifiers


def _config_dir(hass: HomeAssistant) -> Path:
    return Path(hass.config.path(""))


def _storage_dir(hass: HomeAssistant) -> Path:
    return Path(hass.config.path(".storage"))


def ir_codes_file(
    hass: HomeAssistant, entity_id: str | None
) -> Path | None:
    """Codes/conf file for this remote: Broadlink storage or Harmony conf."""
    platform, identifiers = _remote_lookup(hass, entity_id)
    config_dir = _config_dir(hass)
    storage_dir = _storage_dir(hass)
    if platform == "harmony" or (
        platform is None and is_harmony_remote(hass, entity_id, _lookup=False)
    ):
        return resolve_harmony_conf_path(config_dir, identifiers)
    if platform == "broadlink":
        return resolve_broadlink_codes_path(storage_dir, identifiers)
    return resolve_harmony_conf_path(
        config_dir, identifiers
    ) or resolve_broadlink_codes_path(storage_dir, identifiers)


def ir_codes_filename(hass: HomeAssistant, entity_id: str | None) -> str:
    path = ir_codes_file(hass, entity_id)
    return path.name if path is not None else "—"


def learned_broadlink_names(
    hass: HomeAssistant,
    *,
    remote_entity_id: str | None = None,
    device: str | None = None,
) -> tuple[list[str], list[str]]:
    """Device and command names from this Broadlink remote's codes file."""
    _platform, identifiers = _remote_lookup(hass, remote_entity_id)
    path = resolve_broadlink_codes_path(_storage_dir(hass), identifiers)
    payload = load_json_file(path)
    if payload is None:
        return [], []
    return parse_broadlink_codes_payload(payload, device=device)


def _merge_unique(left: list[str], right: list[str]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for name in [*left, *right]:
        if name and name not in seen:
            seen.add(name)
            merged.append(name)
    return merged


def is_harmony_remote(
    hass: HomeAssistant,
    entity_id: str | None,
    *,
    _lookup: bool = True,
) -> bool:
    """True when the remote belongs to Logitech Harmony Hub."""
    if not entity_id or not isinstance(entity_id, str):
        return False
    platform, identifiers = (
        _remote_lookup(hass, entity_id) if _lookup else (None, [])
    )
    if platform == "harmony":
        return True
    if platform == "broadlink":
        return False
    if _lookup and resolve_harmony_conf_path(_config_dir(hass), identifiers):
        return True
    state = hass.states.get(entity_id) if getattr(hass, "states", None) else None
    attrs = getattr(state, "attributes", None) if state is not None else None
    return isinstance(attrs, dict) and "current_activity" in attrs


def _looks_like_harmony_config(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    if isinstance(value.get("device"), list):
        return True
    devices = value.get("Devices")
    if not isinstance(devices, dict):
        devices = value.get("devices")
    return isinstance(devices, dict)


def _harmony_config_from_obj(value: Any) -> dict[str, Any] | None:
    if _looks_like_harmony_config(value):
        return value
    nested = value.get("config") if isinstance(value, dict) else None
    if _looks_like_harmony_config(nested):
        return nested
    for attr in ("config", "_config", "harmony_config", "hub_config"):
        cfg = getattr(value, attr, None)
        if callable(cfg):
            try:
                cfg = cfg()
            except TypeError:
                continue
        if _looks_like_harmony_config(cfg):
            return cfg
    client = getattr(value, "_client", None) or getattr(value, "client", None)
    if client is None:
        return None
    for attr in ("hub_config", "config", "_config"):
        cfg = getattr(client, attr, None)
        if callable(cfg):
            try:
                cfg = cfg()
            except TypeError:
                continue
        if _looks_like_harmony_config(cfg):
            return cfg
    return None


def _harmony_configs(
    hass: HomeAssistant, remote_entity_id: str | None = None
) -> list[dict[str, Any]]:
    """Hub configs from hass.data, limited to this remote's config entry."""
    domain_data = getattr(hass, "data", None)
    harmony_data = domain_data.get("harmony") if isinstance(domain_data, dict) else None
    configs: list[dict[str, Any]] = []
    entry_id: str | None = None
    if remote_entity_id:
        try:
            from homeassistant.helpers import entity_registry as er

            ent = er.async_get(hass).async_get(remote_entity_id)
        except Exception:  # noqa: BLE001
            ent = None
        if ent is not None and getattr(ent, "platform", None) == "harmony":
            entry_id = getattr(ent, "config_entry_id", None)

    if isinstance(harmony_data, dict):
        if entry_id and entry_id in harmony_data:
            values = [harmony_data[entry_id]]
        elif entry_id:
            values = []
        else:
            values = []
        for value in values:
            cfg = _harmony_config_from_obj(value)
            if cfg is not None:
                configs.append(cfg)
    return configs


def learned_harmony_names(
    hass: HomeAssistant,
    *,
    remote_entity_id: str | None = None,
    device: str | None = None,
) -> tuple[list[str], list[str]]:
    """Device labels/ids and command names from this Harmony Hub's conf file."""
    _platform, identifiers = _remote_lookup(hass, remote_entity_id)
    path = resolve_harmony_conf_path(_config_dir(hass), identifiers)
    payload = load_json_file(path)
    if payload is not None:
        devices, commands = parse_harmony_config(payload, device=device)
        if device and not commands:
            devices, commands = parse_harmony_config(payload)
        return devices, commands
    devices: list[str] = []
    commands: list[str] = []
    for blob in _harmony_configs(hass, remote_entity_id):
        found_devices, found_commands = parse_harmony_config(blob, device=device)
        devices = _merge_unique(devices, found_devices)
        commands = _merge_unique(commands, found_commands)
    if device and not commands:
        for blob in _harmony_configs(hass, remote_entity_id):
            _devices, found_commands = parse_harmony_config(blob)
            commands = _merge_unique(commands, found_commands)
            devices = _merge_unique(devices, _devices)
    return devices, commands


def learned_ir_names(
    hass: HomeAssistant,
    *,
    remote_entity_id: str | None = None,
    device: str | None = None,
) -> tuple[list[str], list[str]]:
    """Device and command names from the selected remote's codes/conf file."""
    if not remote_entity_id:
        return [], []
    if is_harmony_remote(hass, remote_entity_id):
        return learned_harmony_names(
            hass, remote_entity_id=remote_entity_id, device=device
        )
    return learned_broadlink_names(
        hass, remote_entity_id=remote_entity_id, device=device
    )


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
    """Pick the default IR remote entity (device list is the next step)."""
    current_remote = data.get(CONF_DEFAULT_REMOTE) or None
    schema: dict[Any, Any] = {}
    if current_remote:
        schema[vol.Optional(CONF_DEFAULT_REMOTE, default=current_remote)] = (
            entity_dropdown(hass, "remote", current=current_remote)
        )
    else:
        schema[vol.Optional(CONF_DEFAULT_REMOTE)] = entity_dropdown(
            hass, "remote", current=current_remote
        )
    return vol.Schema(schema)


def defaults_device_schema(hass: HomeAssistant, data: dict[str, Any]) -> vol.Schema:
    """IR devices from the selected remote's codes/conf file (always a dropdown)."""
    current_remote = data.get(CONF_DEFAULT_REMOTE) or None
    devices, _commands = learned_ir_names(hass, remote_entity_id=current_remote)
    current_device = data.get(CONF_DEFAULT_DEVICE) or ""
    schema: dict[Any, Any] = {}
    if current_device:
        schema[vol.Optional(CONF_DEFAULT_DEVICE, default=current_device)] = (
            _name_dropdown(devices, current=current_device)
        )
    else:
        schema[vol.Optional(CONF_DEFAULT_DEVICE)] = _name_dropdown(
            devices, current=current_device
        )
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
    allow_button_sequence: bool = False,
    include_ir_details: bool = True,
) -> vol.Schema:
    """IR remote (Broadlink / Harmony Hub) or button mapping form.

    ``allow_button_sequence`` is only for input sources (multi-select).
    Per-button repeats and interval are collected in a later step.
    Other commands take a single button.
    """
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
    suggested_button = suggested_buttons[0] if suggested_buttons else None
    suggested_repeats = existing.get(ATTR_NUM_REPEATS, 1)

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
    if include_ir_details:
        devices, commands = learned_ir_names(
            hass, remote_entity_id=suggested_remote, device=suggested_device or None
        )
        device_field: Any = _name_dropdown(devices, current=suggested_device)
        if suggested_command:
            command_field: Any = (
                _name_dropdown(commands, current=suggested_command) if commands else _text()
            )
        elif commands:
            command_field = _name_dropdown(commands, current=suggested_command)
        else:
            command_field = _text()
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
    if allow_button_sequence:
        if suggested_buttons:
            schema[vol.Optional(CONF_BUTTON_ENTITY, default=suggested_buttons)] = (
                entity_multi_dropdown(hass, "button", current=suggested_buttons)
            )
        else:
            schema[vol.Optional(CONF_BUTTON_ENTITY)] = entity_multi_dropdown(
                hass, "button", current=suggested_buttons
            )
    elif suggested_button:
        schema[vol.Optional(CONF_BUTTON_ENTITY, default=suggested_button)] = (
            entity_dropdown(hass, "button", current=suggested_button)
        )
    else:
        schema[vol.Optional(CONF_BUTTON_ENTITY)] = entity_dropdown(
            hass, "button", current=suggested_button
        )
    return vol.Schema(schema)


def ir_details_schema(
    hass: HomeAssistant,
    *,
    remote_entity_id: str | None,
    defaults: dict[str, Any],
    existing: dict[str, Any] | None = None,
) -> vol.Schema:
    """Device, command, and repeats for the selected IR remote's codes file."""
    existing = existing or {}
    suggested_device = ""
    if existing.get(ATTR_TYPE) == ACTION_BROADLINK:
        suggested_device = existing.get(ATTR_DEVICE) or ""
    if not suggested_device:
        suggested_device = defaults.get(CONF_DEFAULT_DEVICE) or ""
    suggested_command = ""
    if existing.get(ATTR_TYPE) == ACTION_BROADLINK:
        suggested_command = existing.get(ATTR_COMMAND) or ""
    suggested_repeats = existing.get(ATTR_NUM_REPEATS, 1)
    devices, commands = learned_ir_names(
        hass, remote_entity_id=remote_entity_id, device=suggested_device or None
    )
    device_field: Any = _name_dropdown(devices, current=suggested_device)
    if suggested_command:
        command_field: Any = (
            _name_dropdown(commands, current=suggested_command) if commands else _text()
        )
    elif commands:
        command_field = _name_dropdown(commands, current=suggested_command)
    else:
        command_field = _text()
    schema: dict[Any, Any] = {}
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
    return vol.Schema(schema)


def source_button_repeats_schema(
    ids: list[str],
    existing: dict[str, Any] | None = None,
) -> vol.Schema:
    """One repeat count per selected source button, plus shared interval."""
    existing = existing or {}
    repeats_by_id = button_repeat_map(existing)
    fallback = button_repeat_default(existing)
    if existing.get(ATTR_TYPE) == ACTION_BUTTON and ATTR_INTERVAL in existing:
        suggested_interval = button_press_interval(existing)
    elif existing.get(ATTR_TYPE) == ACTION_BUTTON:
        suggested_interval = 0.0
    else:
        suggested_interval = DEFAULT_BUTTON_INTERVAL
    schema: dict[Any, Any] = {}
    for entity_id in ids:
        default = repeats_by_id.get(entity_id, fallback)
        schema[vol.Optional(entity_id, default=default)] = NumberSelector(
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
