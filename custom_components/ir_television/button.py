"""Extra remote-key buttons (d-pad, back, home, menu, info) on the same device."""

from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .command_sender import async_send_action
from .const import (
    BUTTON_ICONS,
    CONF_COMMANDS,
    CONF_NAME,
    DOMAIN,
    MANUFACTURER,
    MODEL,
    NAV_COMMANDS,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create a button entity for each configured navigation key."""
    commands = entry.data.get(CONF_COMMANDS) or {}
    entities = [
        IRTelevisionKeyButton(entry, key, commands[key])
        for key in NAV_COMMANDS
        if commands.get(key)
    ]
    async_add_entities(entities)


class IRTelevisionKeyButton(ButtonEntity):
    """Dashboard / automation button that sends one IR or button command."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry, key: str, action: dict[str, Any]) -> None:
        self._entry = entry
        self._key = key
        self._action = action
        self._attr_unique_id = f"{entry.entry_id}_key_{key}"
        self._attr_translation_key = key
        self._attr_icon = BUTTON_ICONS.get(key, "mdi:remote")

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.data.get(CONF_NAME) or self._entry.title,
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    async def async_press(self) -> None:
        await async_send_action(self.hass, self._action, f"key:{self._key}")
