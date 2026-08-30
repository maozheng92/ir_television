"""Television media_player — device_class TV for the iOS Remote widget."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .actions import (
    build_source_list,
    compute_supported_features,
    find_source,
    resolve_command_key,
)
from .command_sender import async_send_action
from .const import (
    ATTR_ACTION,
    CONF_COMMANDS,
    CONF_NAME,
    CONF_SOURCES,
    DOMAIN,
    INTENT_PAUSE,
    INTENT_PLAY,
    INTENT_PLAY_PAUSE,
    INTENT_STOP,
    INTENT_TOGGLE,
    INTENT_TURN_OFF,
    INTENT_TURN_ON,
    INTENT_VOLUME_DOWN,
    INTENT_VOLUME_MUTE,
    INTENT_VOLUME_UP,
    INTENT_NEXT,
    INTENT_PREVIOUS,
    MANUFACTURER,
    MODEL,
)

_LOGGER = logging.getLogger(__name__)

_OFF_STATES = {"off", "unavailable", "unknown"}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the television media player."""
    async_add_entities([IRTelevisionMediaPlayer(hass, entry)])


class IRTelevisionMediaPlayer(MediaPlayerEntity, RestoreEntity):
    """Assumed-state TV controlled by IR or button entities."""

    _attr_device_class = MediaPlayerDeviceClass.TV
    _attr_assumed_state = True
    _attr_has_entity_name = True
    _attr_name = None
    _attr_should_poll = False
    _attr_available = True

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_tv"
        self._is_on = False
        self._muted = False
        self._source: str | None = None
        self._media: str | None = None  # playing | paused | None

    def _commands(self) -> dict[str, Any]:
        return dict(self._entry.data.get(CONF_COMMANDS) or {})

    def _sources(self) -> list[dict[str, Any]]:
        return list(self._entry.data.get(CONF_SOURCES) or [])

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.data.get(CONF_NAME) or self._entry.title,
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    @property
    def supported_features(self) -> MediaPlayerEntityFeature:
        bits = compute_supported_features(self._commands(), self._sources())
        return MediaPlayerEntityFeature(bits)

    @property
    def state(self) -> MediaPlayerState:
        if not self._is_on:
            return MediaPlayerState.OFF
        if self._media == "playing":
            return MediaPlayerState.PLAYING
        if self._media == "paused":
            return MediaPlayerState.PAUSED
        return MediaPlayerState.ON

    @property
    def is_volume_muted(self) -> bool:
        return self._muted

    @property
    def source(self) -> str | None:
        return self._source

    @property
    def source_list(self) -> list[str] | None:
        names = build_source_list(self._sources())
        return names or None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is None:
            return
        state = last.state
        if state in _OFF_STATES:
            self._is_on = False
            self._media = None
        else:
            self._is_on = True
            if state == "playing":
                self._media = "playing"
            elif state == "paused":
                self._media = "paused"
        attrs = last.attributes or {}
        if "is_volume_muted" in attrs:
            self._muted = bool(attrs.get("is_volume_muted"))
        if attrs.get("source"):
            self._source = str(attrs["source"])

    async def _async_fire(self, intent: str) -> bool:
        commands = self._commands()
        key = resolve_command_key(commands, intent)
        if key is None:
            _LOGGER.warning(
                "IR Television '%s': %s is not mapped; ignoring",
                self._entry.title,
                intent,
            )
            return False
        return await async_send_action(self.hass, commands.get(key), intent)

    async def async_turn_on(self) -> None:
        if await self._async_fire(INTENT_TURN_ON):
            self._is_on = True
            self.async_write_ha_state()

    async def async_turn_off(self) -> None:
        if await self._async_fire(INTENT_TURN_OFF):
            self._is_on = False
            self._media = None
            self.async_write_ha_state()

    async def async_toggle(self) -> None:
        commands = self._commands()
        toggle_key = resolve_command_key(commands, INTENT_TOGGLE)
        if toggle_key:
            if await async_send_action(self.hass, commands.get(toggle_key), INTENT_TOGGLE):
                self._is_on = not self._is_on
                if not self._is_on:
                    self._media = None
                self.async_write_ha_state()
            return
        if self._is_on:
            await self.async_turn_off()
        else:
            await self.async_turn_on()

    async def async_volume_up(self) -> None:
        if await self._async_fire(INTENT_VOLUME_UP):
            self._is_on = True
            self.async_write_ha_state()

    async def async_volume_down(self) -> None:
        if await self._async_fire(INTENT_VOLUME_DOWN):
            self._is_on = True
            self.async_write_ha_state()

    async def async_mute_volume(self, mute: bool) -> None:
        if await self._async_fire(INTENT_VOLUME_MUTE):
            self._muted = mute
            self._is_on = True
            self.async_write_ha_state()

    async def async_media_play(self) -> None:
        if await self._async_fire(INTENT_PLAY):
            self._is_on = True
            self._media = "playing"
            self.async_write_ha_state()

    async def async_media_pause(self) -> None:
        if await self._async_fire(INTENT_PAUSE):
            self._is_on = True
            self._media = "paused"
            self.async_write_ha_state()

    async def async_media_play_pause(self) -> None:
        commands = self._commands()
        dedicated = resolve_command_key(commands, INTENT_PLAY_PAUSE)
        if dedicated:
            if await async_send_action(self.hass, commands.get(dedicated), INTENT_PLAY_PAUSE):
                self._is_on = True
                self._media = "paused" if self._media == "playing" else "playing"
                self.async_write_ha_state()
            return
        if self._media == "playing":
            await self.async_media_pause()
        else:
            await self.async_media_play()

    async def async_media_stop(self) -> None:
        if await self._async_fire(INTENT_STOP):
            self._is_on = True
            self._media = "paused"
            self.async_write_ha_state()

    async def async_media_next_track(self) -> None:
        if await self._async_fire(INTENT_NEXT):
            self._is_on = True
            self.async_write_ha_state()

    async def async_media_previous_track(self) -> None:
        if await self._async_fire(INTENT_PREVIOUS):
            self._is_on = True
            self.async_write_ha_state()

    async def async_select_source(self, source: str) -> None:
        match = find_source(self._sources(), source)
        if match is None:
            _LOGGER.warning(
                "IR Television '%s': unknown source '%s'",
                self._entry.title,
                source,
            )
            return
        if await async_send_action(self.hass, match.get(ATTR_ACTION), f"source:{source}"):
            self._source = match.get("name") or source
            self._is_on = True
            self.async_write_ha_state()
