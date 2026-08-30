"""Voluptuous schemas and selectors for the config / options flows."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
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

from .actions import summarize_action
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
    CONF_COMMAND,
    CONF_DEFAULT_DEVICE,
    CONF_DEFAULT_REMOTE,
    CONF_DEVICE,
    CONF_NAME,
    CONF_NUM_REPEATS,
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


def name_schema(default: str | None = None) -> vol.Schema:
    """TV display name."""
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=default or ""): _text(),
        }
    )


def defaults_schema(data: dict[str, Any]) -> vol.Schema:
    """Optional default Broadlink remote + device name."""
    return vol.Schema(
        {
            vol.Optional(
                CONF_DEFAULT_REMOTE,
                description={"suggested_value": data.get(CONF_DEFAULT_REMOTE)},
            ): EntitySelector(EntitySelectorConfig(domain="remote")),
            vol.Optional(
                CONF_DEFAULT_DEVICE,
                default=data.get(CONF_DEFAULT_DEVICE) or "",
            ): _text(),
        }
    )


def power_mode_schema(default: str = POWER_MODE_ON_OFF) -> vol.Schema:
    """Choose how power is mapped."""
    return vol.Schema(
        {
            vol.Required("power_mode", default=default): SelectSelector(
                SelectSelectorConfig(
                    options=[POWER_MODE_ON_OFF, POWER_MODE_TOGGLE, POWER_MODE_SKIP],
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
    suggested_button = (
        existing.get(ATTR_ENTITY_ID) if existing.get(ATTR_TYPE) == ACTION_BUTTON else None
    )
    suggested_repeats = existing.get(ATTR_NUM_REPEATS, 1)

    return vol.Schema(
        {
            vol.Required(CONF_ACTION_TYPE, default=default_type): SelectSelector(
                SelectSelectorConfig(
                    options=[ACTION_BROADLINK, ACTION_BUTTON],
                    mode=SelectSelectorMode.LIST,
                    translation_key="action_type",
                )
            ),
            vol.Optional(
                CONF_REMOTE_ENTITY,
                description={"suggested_value": suggested_remote},
            ): EntitySelector(EntitySelectorConfig(domain="remote")),
            vol.Optional(CONF_DEVICE, default=suggested_device): _text(),
            vol.Optional(CONF_COMMAND, default=suggested_command): _text(),
            vol.Optional(
                CONF_NUM_REPEATS,
                default=suggested_repeats,
            ): NumberSelector(
                NumberSelectorConfig(
                    min=1,
                    max=10,
                    step=1,
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(
                CONF_BUTTON_ENTITY,
                description={"suggested_value": suggested_button},
            ): EntitySelector(EntitySelectorConfig(domain="button")),
        }
    )


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
