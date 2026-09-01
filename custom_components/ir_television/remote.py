"""Activity remote — HomeKit ActivityRemote (type_remotes.py) for Control Center.

Apple's Control Center Remote lists HomeKit accessories that expose a Television
service. HA builds that from either:

* ``media_player`` + ``device_class=tv`` → TelevisionMediaPlayer
* ``remote`` + ``RemoteEntityFeature.ACTIVITY`` → ActivityRemote

Both subclasses of ``RemoteInputSelectAccessory`` in HomeKit's type_remotes.py.
The activity remote is a dedicated accessory (one entity, accessory mode) whose
activities are this TV's HDMI / app sources.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable
from typing import Any

from homeassistant.components.remote import RemoteEntity, RemoteEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .actions import build_source_list, current_source_name, resolve_homekit_remote_key
from .command_sender import async_send_action
from .const import (
    CONF_COMMANDS,
    CONF_NAME,
    CONF_SOURCES,
    DOMAIN,
    MANUFACTURER,
    MODEL,
)

_LOGGER = logging.getLogger(__name__)

_OFF_STATES = {"off", "unavailable", "unknown", "none", ""}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the HomeKit activity remote."""
    async_add_entities([IRTelevisionActivityRemote(hass, entry)])


class IRTelevisionActivityRemote(RemoteEntity):
    """Remote with activities so HomeKit creates ActivityRemote (iOS Remote)."""

    _attr_has_entity_name = True
    _attr_translation_key = "activity_remote"
    _attr_should_poll = False
    _attr_assumed_state = True
    _attr_supported_features = RemoteEntityFeature.ACTIVITY

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_activity_remote"

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
        state = self._tv_state()
        if state is None:
            return False
        return str(state.state).lower() not in _OFF_STATES

    @property
    def activity_list(self) -> list[str]:
        sources = list(self._entry.data.get(CONF_SOURCES) or [])
        return build_source_list(sources)

    @property
    def current_activity(self) -> str | None:
        sources = list(self._entry.data.get(CONF_SOURCES) or [])
        state = self._tv_state()
        source = None if state is None else state.attributes.get("source")
        return current_source_name(None if source is None else str(source), sources)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        runtime = self._runtime()
        runtime["remote_entity_id"] = self.entity_id
        self.hass.async_create_task(self._async_watch_tv())
        self.hass.async_create_task(self._async_expose_homekit())

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

    async def _async_expose_homekit(self) -> None:
        for _ in range(100):
            if self.hass.states.get(self.entity_id) is not None:
                break
            await asyncio.sleep(0.05)
        else:
            return
        from .homekit_expose import async_ensure_homekit_tv_accessory

        await async_ensure_homekit_tv_accessory(self.hass, self.entity_id)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Power on, or switch activity (HomeKit CHAR_ACTIVE_IDENTIFIER)."""
        activity = kwargs.get("activity")
        tv_id = self._tv_entity_id()
        if not tv_id:
            _LOGGER.warning("IR Television remote: media_player entity is not ready")
            return
        if activity:
            await self.hass.services.async_call(
                "media_player",
                "select_source",
                {"entity_id": tv_id, "source": activity},
                blocking=True,
            )
            return
        await self.hass.services.async_call(
            "media_player",
            "turn_on",
            {"entity_id": tv_id},
            blocking=True,
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
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
        """Send named keys (up/down/ok or HomeKit key_name) as IR/button."""
        commands = dict(self._entry.data.get(CONF_COMMANDS) or {})
        for raw in command:
            key = resolve_homekit_remote_key(commands, str(raw))
            if key is None:
                _LOGGER.debug(
                    "IR Television remote: command '%s' is not mapped", raw
                )
                continue
            await async_send_action(self.hass, commands.get(key), f"remote:{raw}")
        self.async_write_ha_state()
