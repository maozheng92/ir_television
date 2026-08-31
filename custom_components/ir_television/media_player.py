"""Television media_player — device_class TV for Apple HomeKit / Control Center Remote."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.restore_state import RestoreEntity

from .actions import (
    build_source_list,
    compute_supported_features,
    find_source,
    normalize_source_name,
    power_is_on_from_sensor,
    resolve_command_key,
    resolve_homekit_remote_key,
)
from .command_sender import async_send_action
from .const import (
    ATTR_ACTION,
    CONF_COMMANDS,
    CONF_NAME,
    CONF_POWER_SENSOR,
    CONF_POWER_SENSOR_INVERT,
    CONF_SOURCES,
    DOMAIN,
    EVENT_HOMEKIT_TV_REMOTE_KEY_PRESSED,
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
    """TV controlled by IR or button entities, with optional binary_sensor power."""

    _attr_device_class = MediaPlayerDeviceClass.TV
    _attr_icon = "mdi:television"
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
        self._volume = 0.5  # optimistic 0..1 like braviatv (HomeKit CHAR_VOLUME)
        self._source: str | None = None
        self._media: str | None = None  # playing | paused | None

    def _commands(self) -> dict[str, Any]:
        return dict(self._entry.data.get(CONF_COMMANDS) or {})

    def _sources(self) -> list[dict[str, Any]]:
        return list(self._entry.data.get(CONF_SOURCES) or [])

    @property
    def _power_sensor(self) -> str | None:
        sensor = self._entry.data.get(CONF_POWER_SENSOR)
        if isinstance(sensor, str) and sensor.strip():
            return sensor.strip()
        return None

    @property
    def _power_sensor_invert(self) -> bool:
        return bool(self._entry.data.get(CONF_POWER_SENSOR_INVERT))

    @property
    def assumed_state(self) -> bool:
        """Power is assumed unless a binary_sensor is providing feedback."""
        return self._power_sensor is None

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
    def volume_level(self) -> float | None:
        """Absolute volume 0..1 so HomeKit adds TelevisionSpeaker CHAR_VOLUME."""
        return self._volume

    @property
    def source(self) -> str | None:
        return self._source

    @property
    def source_list(self) -> list[str]:
        """Always at least one input so HomeKit creates Input Source services."""
        return build_source_list(self._sources())

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        sensor = self._power_sensor
        if not sensor:
            return None
        attrs: dict[str, Any] = {"power_sensor": sensor}
        if self._power_sensor_invert:
            attrs["power_sensor_invert"] = True
        return attrs

    def _apply_power(self, is_on: bool) -> None:
        self._is_on = is_on
        if not is_on:
            self._media = None

    def _mark_on_from_command(self) -> None:
        """Optimistic on only when there is no power sensor to contradict us."""
        if self._power_sensor:
            return
        self._is_on = True

    def _sync_from_power_sensor(self) -> bool:
        """Apply current binary_sensor state. Returns True if a clear reading was used."""
        sensor = self._power_sensor
        if not sensor:
            return False
        state = self.hass.states.get(sensor)
        parsed = power_is_on_from_sensor(
            None if state is None else state.state,
            invert=self._power_sensor_invert,
        )
        if parsed is None:
            return False
        self._apply_power(parsed)
        return True

    @callback
    def _async_power_sensor_event(self, event: Event) -> None:
        new_state = event.data.get("new_state") if event.data else None
        parsed = power_is_on_from_sensor(
            None if new_state is None else getattr(new_state, "state", None),
            invert=self._power_sensor_invert,
        )
        if parsed is None:
            return
        self._apply_power(parsed)
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None:
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
            if attrs.get("volume_level") is not None:
                try:
                    self._volume = max(0.0, min(1.0, float(attrs["volume_level"])))
                except (TypeError, ValueError):
                    pass
            if attrs.get("source"):
                self._source = str(attrs["source"])

        if not self._source:
            names = build_source_list(self._sources())
            if names:
                self._source = names[0]

        sensor = self._power_sensor
        if sensor:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass, [sensor], self._async_power_sensor_event
                )
            )
            self._sync_from_power_sensor()

        self.async_on_remove(
            self.hass.bus.async_listen(
                EVENT_HOMEKIT_TV_REMOTE_KEY_PRESSED,
                self._async_homekit_tv_remote_key,
            )
        )
        self.hass.async_create_task(self._async_expose_homekit())

    async def _async_fire(self, intent: str) -> bool:
        commands = self._commands()
        key = resolve_command_key(commands, intent)
        if key is None:
            _LOGGER.debug(
                "IR Television '%s': %s is not mapped; HomeKit state still updates",
                self._entry.title,
                intent,
            )
            return False
        return await async_send_action(self.hass, commands.get(key), intent)

    async def _async_expose_homekit(self) -> None:
        """Pair this TV as a HomeKit accessory so Control Center Remote lists it."""
        for _ in range(100):
            if self.hass.states.get(self.entity_id) is not None:
                break
            await asyncio.sleep(0.05)
        else:
            _LOGGER.debug(
                "IR Television '%s': no state yet; skip HomeKit accessory create",
                self._entry.title,
            )
            return
        from .homekit_expose import async_ensure_homekit_tv_accessory

        await async_ensure_homekit_tv_accessory(self.hass, self.entity_id)

    async def async_turn_on(self) -> None:
        await self._async_fire(INTENT_TURN_ON)
        self._apply_power(True)
        self.async_write_ha_state()

    async def async_turn_off(self) -> None:
        await self._async_fire(INTENT_TURN_OFF)
        self._apply_power(False)
        self.async_write_ha_state()

    async def async_toggle(self) -> None:
        commands = self._commands()
        toggle_key = resolve_command_key(commands, INTENT_TOGGLE)
        if toggle_key:
            if await async_send_action(self.hass, commands.get(toggle_key), INTENT_TOGGLE):
                self._apply_power(not self._is_on)
                self.async_write_ha_state()
            return
        if self._is_on:
            await self.async_turn_off()
        else:
            await self.async_turn_on()

    async def async_volume_up(self) -> None:
        await self._async_fire(INTENT_VOLUME_UP)
        self._volume = min(1.0, self._volume + 0.05)
        self._mark_on_from_command()
        self.async_write_ha_state()

    async def async_volume_down(self) -> None:
        await self._async_fire(INTENT_VOLUME_DOWN)
        self._volume = max(0.0, self._volume - 0.05)
        self._mark_on_from_command()
        self.async_write_ha_state()

    async def async_set_volume_level(self, volume: float) -> None:
        """HomeKit CHAR_VOLUME (braviatv also implements this)."""
        target = max(0.0, min(1.0, float(volume)))
        old = self._volume
        self._volume = target
        if target > old + 0.001:
            await self._async_fire(INTENT_VOLUME_UP)
        elif target < old - 0.001:
            await self._async_fire(INTENT_VOLUME_DOWN)
        self._mark_on_from_command()
        self.async_write_ha_state()

    async def async_mute_volume(self, mute: bool) -> None:
        await self._async_fire(INTENT_VOLUME_MUTE)
        self._muted = mute
        self._mark_on_from_command()
        self.async_write_ha_state()

    async def async_media_play(self) -> None:
        await self._async_fire(INTENT_PLAY)
        self._mark_on_from_command()
        self._media = "playing"
        self.async_write_ha_state()

    async def async_media_pause(self) -> None:
        await self._async_fire(INTENT_PAUSE)
        self._mark_on_from_command()
        self._media = "paused"
        self.async_write_ha_state()

    async def async_media_play_pause(self) -> None:
        commands = self._commands()
        dedicated = resolve_command_key(commands, INTENT_PLAY_PAUSE)
        if dedicated:
            if await async_send_action(self.hass, commands.get(dedicated), INTENT_PLAY_PAUSE):
                self._mark_on_from_command()
                self._media = "paused" if self._media == "playing" else "playing"
                self.async_write_ha_state()
            return
        if self._media == "playing":
            await self.async_media_pause()
        else:
            await self.async_media_play()

    async def async_media_stop(self) -> None:
        await self._async_fire(INTENT_STOP)
        self._mark_on_from_command()
        self._media = "paused"
        self.async_write_ha_state()

    async def async_media_next_track(self) -> None:
        await self._async_fire(INTENT_NEXT)
        self._mark_on_from_command()
        self.async_write_ha_state()

    async def async_media_previous_track(self) -> None:
        await self._async_fire(INTENT_PREVIOUS)
        self._mark_on_from_command()
        self.async_write_ha_state()

    async def _async_homekit_tv_remote_key(self, event: Event) -> None:
        """Map Apple Control Center Remote keys to configured IR/button commands."""
        data = event.data or {}
        if data.get("entity_id") != self.entity_id:
            return
        key_name = data.get("key_name")
        commands = self._commands()
        cmd_key = resolve_homekit_remote_key(commands, key_name)
        if cmd_key is None:
            _LOGGER.debug(
                "IR Television '%s': HomeKit remote key '%s' is not mapped; ignoring",
                self._entry.title,
                key_name,
            )
            return
        if await async_send_action(
            self.hass, commands.get(cmd_key), f"homekit:{key_name}"
        ):
            self._mark_on_from_command()
            self.async_write_ha_state()

    async def async_select_source(self, source: str) -> None:
        match = find_source(self._sources(), source)
        if match is not None:
            if await async_send_action(
                self.hass, match.get(ATTR_ACTION), f"source:{source}"
            ):
                self._source = match.get("name") or source
                self._mark_on_from_command()
                self.async_write_ha_state()
            return

        # Implicit default source (e.g. "TV") has no IR action — just remember it
        # so HomeKit CHAR_ACTIVE_IDENTIFIER stays in sync.
        target = normalize_source_name(source).lower()
        for name in build_source_list(self._sources()):
            if name.lower() == target:
                self._source = name
                self._mark_on_from_command()
                self.async_write_ha_state()
                return

        _LOGGER.warning(
            "IR Television '%s': unknown source '%s'",
            self._entry.title,
            source,
        )
