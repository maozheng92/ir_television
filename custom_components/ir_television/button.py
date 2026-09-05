"""Extra remote-key buttons (d-pad, back, home, menu, info) on the same device.

Official braviatv only ships CONFIG buttons (reboot / terminate apps). D-pad
keys stay DIAGNOSTIC so HomeKit never mixes them into the Television accessory.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .command_sender import async_send_action
from .const import BUTTON_ICONS, CONF_COMMANDS, DOMAIN, NAV_COMMANDS
from .entity import IRTelevisionEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create a button entity for each configured navigation key plus HomeKit helper."""
    commands = entry.data.get(CONF_COMMANDS) or {}
    entities: list[ButtonEntity] = [
        IRTelevisionKeyButton(hass, entry, key, commands[key])
        for key in NAV_COMMANDS
        if commands.get(key)
    ]
    entities.append(IRTelevisionRecreateHomeKitButton(hass, entry))
    async_add_entities(entities)


class IRTelevisionKeyButton(IRTelevisionEntity, ButtonEntity):
    """Dashboard / automation button that sends one IR or button command."""

    _attr_should_poll = False
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, key: str, action: dict[str, Any]
    ) -> None:
        super().__init__(hass, entry)
        self._key = key
        self._action = action
        self._attr_unique_id = f"{entry.entry_id}_key_{key}"
        self._attr_translation_key = key
        self._attr_icon = BUTTON_ICONS.get(key, "mdi:remote")

    async def async_press(self) -> None:
        await async_send_action(self.hass, self._action, f"key:{self._key}")


class IRTelevisionRecreateHomeKitButton(IRTelevisionEntity, ButtonEntity):
    """Optional pairing helper — not part of the braviatv entity set."""

    _attr_should_poll = False
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "recreate_homekit"
    _attr_icon = "mdi:apple"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, entry)
        self._attr_unique_id = f"{entry.entry_id}_recreate_homekit"

    async def async_press(self) -> None:
        runtime = self.hass.data.get(DOMAIN, {}).get(self._entry.entry_id) or {}
        entity_ids: list[str] = []
        if isinstance(runtime, dict):
            for key in ("tv_entity_id", "remote_entity_id"):
                if runtime.get(key):
                    entity_ids.append(str(runtime[key]))
        if not entity_ids:
            return
        from .homekit_expose import async_recreate_homekit_tv_accessory

        await async_recreate_homekit_tv_accessory(self.hass, entity_ids)
