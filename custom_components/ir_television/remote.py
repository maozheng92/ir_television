"""Remote on the same TV device — not a separate HomeKit accessory.

Matches official braviatv.remote.BraviaTVRemote: ``_attr_name = None``, no
``RemoteEntityFeature.ACTIVITY``. HomeKit Television / iOS Control Center
Remote is built only from the ``media_player`` (device_class=tv). This entity
exists so HA automations can call ``remote.send_command`` with IR key names.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable
from typing import Any

from homeassistant.components.remote import ATTR_NUM_REPEATS, RemoteEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .actions import resolve_homekit_remote_key
from .command_sender import async_send_action
from .const import CONF_COMMANDS, CONF_NAME, DOMAIN, MANUFACTURER, MODEL

_LOGGER = logging.getLogger(__name__)

_OFF_STATES = {"off", "unavailable", "unknown", "none", ""}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the TV remote on the same device as the media player."""
    async_add_entities([IRTelevisionRemote(hass, entry)])


class IRTelevisionRemote(RemoteEntity):
    """IR remote that shares the television device (Sony-style, no ACTIVITY)."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_icon = "mdi:remote"
    _attr_should_poll = False
    _attr_assumed_state = True

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_remote"

    def _runtime(self) -> dict[str, Any]:
        data = self.hass.data.get(DOMAIN, {}).get(self._entry.entry_id)
        return data if isinstance(data, dict) else {}

    def _tv_entity_id(self) -> str | None:
        tv_id = self._runtime().get("tv_entity_id")
        return str(tv_id) if tv_id else None

    def _tv_state(self):
        tv_id = self._tv_entity_id()
        if not tv_id:
            return None
        return self.hass.states.get(tv_id)

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.data.get(CONF_NAME) or self._entry.title,
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    @property
    def is_on(self) -> bool:
        """Return true if the television is on."""
        state = self._tv_state()
        if state is None:
            return False
        return str(state.state).lower() not in _OFF_STATES

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._runtime()["remote_entity_id"] = self.entity_id
        self.hass.async_create_task(self._async_watch_tv())

    async def _async_watch_tv(self) -> None:
        for _ in range(100):
            tv_id = self._tv_entity_id()
            if tv_id:
                self.async_on_remove(
                    async_track_state_change_event(
                        self.hass, [tv_id], self._async_tv_changed
                    )
                )
                self.async_write_ha_state()
                return
            await asyncio.sleep(0.05)

    @callback
    def _async_tv_changed(self, event: Event) -> None:
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the television on."""
        tv_id = self._tv_entity_id()
        if not tv_id:
            _LOGGER.warning("IR Television remote: media_player entity is not ready")
            return
        await self.hass.services.async_call(
            "media_player",
            "turn_on",
            {"entity_id": tv_id},
            blocking=True,
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the television off."""
        tv_id = self._tv_entity_id()
        if not tv_id:
            return
        await self.hass.services.async_call(
            "media_player",
            "turn_off",
            {"entity_id": tv_id},
            blocking=True,
        )

    async def async_send_command(self, command: Iterable[str], **kwargs: Any) -> None:
        """Send named keys (up/ok or HomeKit key_name) as IR/button."""
        repeats = kwargs.get(ATTR_NUM_REPEATS, 1)
        try:
            repeats = max(1, int(repeats))
        except (TypeError, ValueError):
            repeats = 1
        commands = dict(self._entry.data.get(CONF_COMMANDS) or {})
        for _ in range(repeats):
            for raw in command:
                key = resolve_homekit_remote_key(commands, str(raw))
                if key is None:
                    _LOGGER.debug(
                        "IR Television remote: command '%s' is not mapped", raw
                    )
                    continue
                await async_send_action(self.hass, commands.get(key), f"remote:{raw}")
        self.async_write_ha_state()
