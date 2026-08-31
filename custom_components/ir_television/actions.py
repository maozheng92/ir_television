"""Pure helpers for command mapping, features, and sources.

This module must not import Home Assistant so it can be unit-tested with stdlib.
"""

from __future__ import annotations

from typing import Any

from .const import (
    ACTION_BROADLINK,
    ACTION_BUTTON,
    ATTR_ACTION,
    ATTR_COMMAND,
    ATTR_DEVICE,
    ATTR_ENTITY_ID,
    ATTR_NAME,
    ATTR_NUM_REPEATS,
    ATTR_TYPE,
    CMD_PAUSE,
    CMD_PLAY,
    CMD_PLAY_PAUSE,
    CMD_POWER_TOGGLE,
    CMD_STOP,
    CMD_TURN_OFF,
    CMD_TURN_ON,
    CMD_VOLUME_DOWN,
    CMD_VOLUME_MUTE,
    CMD_VOLUME_UP,
    CONF_ACTION_TYPE,
    CONF_BUTTON_ENTITY,
    CONF_COMMAND,
    CONF_DEFAULT_DEVICE,
    CONF_DEFAULT_REMOTE,
    CONF_DEVICE,
    CONF_NUM_REPEATS,
    CONF_POWER_SENSOR,
    CONF_POWER_SENSOR_INVERT,
    CONF_REMOTE_ENTITY,
    FEATURE_NEXT_TRACK,
    FEATURE_PAUSE,
    FEATURE_PLAY,
    FEATURE_PREVIOUS_TRACK,
    FEATURE_SELECT_SOURCE,
    FEATURE_STOP,
    FEATURE_TURN_OFF,
    FEATURE_TURN_ON,
    FEATURE_VOLUME_MUTE,
    FEATURE_VOLUME_STEP,
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
)

ActionDict = dict[str, Any]
SourceDict = dict[str, Any]


def _has_action(commands: dict[str, Any], key: str) -> bool:
    action = commands.get(key)
    return bool(action) and isinstance(action, dict) and bool(action.get(ATTR_TYPE))


def compute_supported_features(
    commands: dict[str, Any] | None,
    sources: list[Any] | None,
) -> int:
    """Return a MediaPlayerEntityFeature bitmask for configured commands."""
    commands = commands or {}
    features = 0

    if _has_action(commands, CMD_TURN_ON) or _has_action(commands, CMD_POWER_TOGGLE):
        features |= FEATURE_TURN_ON
    if _has_action(commands, CMD_TURN_OFF) or _has_action(commands, CMD_POWER_TOGGLE):
        features |= FEATURE_TURN_OFF
    if _has_action(commands, CMD_VOLUME_UP) or _has_action(commands, CMD_VOLUME_DOWN):
        features |= FEATURE_VOLUME_STEP
    if _has_action(commands, CMD_VOLUME_MUTE):
        features |= FEATURE_VOLUME_MUTE
    if _has_action(commands, CMD_PLAY) or _has_action(commands, CMD_PLAY_PAUSE):
        features |= FEATURE_PLAY
    if _has_action(commands, CMD_PAUSE) or _has_action(commands, CMD_PLAY_PAUSE):
        features |= FEATURE_PAUSE
    if _has_action(commands, CMD_STOP):
        features |= FEATURE_STOP
    if _has_action(commands, INTENT_NEXT):
        features |= FEATURE_NEXT_TRACK
    if _has_action(commands, INTENT_PREVIOUS):
        features |= FEATURE_PREVIOUS_TRACK
    if build_source_list(sources):
        features |= FEATURE_SELECT_SOURCE
    return features


def resolve_command_key(commands: dict[str, Any] | None, intent: str) -> str | None:
    """Map a high-level media_player intent to a configured command key."""
    commands = commands or {}

    if intent == INTENT_TURN_ON:
        if _has_action(commands, CMD_TURN_ON):
            return CMD_TURN_ON
        if _has_action(commands, CMD_POWER_TOGGLE):
            return CMD_POWER_TOGGLE
        return None

    if intent == INTENT_TURN_OFF:
        if _has_action(commands, CMD_TURN_OFF):
            return CMD_TURN_OFF
        if _has_action(commands, CMD_POWER_TOGGLE):
            return CMD_POWER_TOGGLE
        return None

    if intent == INTENT_TOGGLE:
        if _has_action(commands, CMD_POWER_TOGGLE):
            return CMD_POWER_TOGGLE
        return None  # caller should dispatch to on/off using assumed state

    if intent == INTENT_PLAY:
        if _has_action(commands, CMD_PLAY):
            return CMD_PLAY
        if _has_action(commands, CMD_PLAY_PAUSE):
            return CMD_PLAY_PAUSE
        return None

    if intent == INTENT_PAUSE:
        if _has_action(commands, CMD_PAUSE):
            return CMD_PAUSE
        if _has_action(commands, CMD_PLAY_PAUSE):
            return CMD_PLAY_PAUSE
        return None

    if intent == INTENT_PLAY_PAUSE:
        if _has_action(commands, CMD_PLAY_PAUSE):
            return CMD_PLAY_PAUSE
        return None

    if intent == INTENT_STOP:
        return CMD_STOP if _has_action(commands, CMD_STOP) else None

    if intent == INTENT_VOLUME_UP:
        return CMD_VOLUME_UP if _has_action(commands, CMD_VOLUME_UP) else None

    if intent == INTENT_VOLUME_DOWN:
        return CMD_VOLUME_DOWN if _has_action(commands, CMD_VOLUME_DOWN) else None

    if intent == INTENT_VOLUME_MUTE:
        return CMD_VOLUME_MUTE if _has_action(commands, CMD_VOLUME_MUTE) else None

    if intent == INTENT_NEXT:
        return INTENT_NEXT if _has_action(commands, INTENT_NEXT) else None

    if intent == INTENT_PREVIOUS:
        return INTENT_PREVIOUS if _has_action(commands, INTENT_PREVIOUS) else None

    if _has_action(commands, intent):
        return intent
    return None


def normalize_source_name(name: str | None) -> str:
    """Strip surrounding whitespace from a source name."""
    return (name or "").strip()


def validate_source_name(
    name: str | None,
    sources: list[SourceDict] | None,
    exclude_index: int | None = None,
) -> str | None:
    """Return an error key if the source name is invalid, else None."""
    cleaned = normalize_source_name(name)
    if not cleaned:
        return "empty_name"
    sources = sources or []
    for idx, source in enumerate(sources):
        if exclude_index is not None and idx == exclude_index:
            continue
        existing = normalize_source_name(str(source.get(ATTR_NAME, "")))
        if existing.lower() == cleaned.lower():
            return "duplicate_source"
    return None


def build_source_list(sources: list[Any] | None) -> list[str]:
    """Return display names for configured sources."""
    names: list[str] = []
    for source in sources or []:
        if not isinstance(source, dict):
            continue
        name = normalize_source_name(str(source.get(ATTR_NAME, "")))
        if name:
            names.append(name)
    return names


def find_source(sources: list[SourceDict] | None, name: str) -> SourceDict | None:
    """Find a source by display name (case-insensitive)."""
    target = normalize_source_name(name).lower()
    if not target:
        return None
    for source in sources or []:
        if normalize_source_name(str(source.get(ATTR_NAME, ""))).lower() == target:
            return source
    return None


def has_useful_config(commands: dict[str, Any] | None, sources: list[Any] | None) -> bool:
    """True if at least one command or source is configured."""
    commands = commands or {}
    if any(_has_action(commands, key) for key in commands):
        return True
    return bool(build_source_list(sources))


def action_is_valid(action: Any) -> bool:
    """Return True if an action payload can be sent."""
    if not isinstance(action, dict):
        return False
    action_type = action.get(ATTR_TYPE)
    entity_id = action.get(ATTR_ENTITY_ID)
    if not entity_id or not isinstance(entity_id, str):
        return False
    if action_type == ACTION_BROADLINK:
        if not entity_id.startswith("remote."):
            return False
        command = action.get(ATTR_COMMAND)
        return bool(isinstance(command, str) and command.strip())
    if action_type == ACTION_BUTTON:
        return entity_id.startswith("button.")
    return False


def parse_action_input(
    user_input: dict[str, Any],
    defaults: dict[str, Any] | None = None,
) -> tuple[ActionDict | None, str | None]:
    """Parse a config-flow form into a stored action.

    Returns (action, error_key). error_key is set on validation failure.
    """
    defaults = defaults or {}
    action_type = user_input.get(CONF_ACTION_TYPE)

    if action_type == ACTION_BROADLINK:
        entity_id = user_input.get(CONF_REMOTE_ENTITY) or defaults.get(CONF_DEFAULT_REMOTE)
        command = str(user_input.get(CONF_COMMAND) or "").strip()
        device = str(user_input.get(CONF_DEVICE) or "").strip() or defaults.get(
            CONF_DEFAULT_DEVICE
        )
        if isinstance(device, str):
            device = device.strip() or None
        else:
            device = None

        if not entity_id:
            return None, "missing_remote"
        if not isinstance(entity_id, str) or not entity_id.startswith("remote."):
            return None, "invalid_entity"
        if not command:
            return None, "missing_command"

        action: ActionDict = {
            ATTR_TYPE: ACTION_BROADLINK,
            ATTR_ENTITY_ID: entity_id,
            ATTR_COMMAND: command,
        }
        if device:
            action[ATTR_DEVICE] = device
        repeats = user_input.get(CONF_NUM_REPEATS)
        if repeats is not None:
            try:
                repeats_int = int(repeats)
            except (TypeError, ValueError):
                return None, "invalid_repeats"
            if repeats_int < 1 or repeats_int > 10:
                return None, "invalid_repeats"
            if repeats_int != 1:
                action[ATTR_NUM_REPEATS] = repeats_int
        return action, None

    if action_type == ACTION_BUTTON:
        entity_id = user_input.get(CONF_BUTTON_ENTITY)
        if not entity_id:
            return None, "missing_button"
        if not isinstance(entity_id, str) or not entity_id.startswith("button."):
            return None, "invalid_entity"
        return {ATTR_TYPE: ACTION_BUTTON, ATTR_ENTITY_ID: entity_id}, None

    return None, "invalid_action_type"


def build_remote_service_data(action: ActionDict) -> dict[str, Any]:
    """Build remote.send_command service data from a Broadlink action."""
    data: dict[str, Any] = {
        "entity_id": action[ATTR_ENTITY_ID],
        "command": action[ATTR_COMMAND],
        "num_repeats": int(action.get(ATTR_NUM_REPEATS, 1)),
    }
    device = action.get(ATTR_DEVICE)
    if device:
        data["device"] = device
    return data


def build_button_service_data(action: ActionDict) -> dict[str, Any]:
    """Build button.press service data from a button action."""
    return {"entity_id": action[ATTR_ENTITY_ID]}


def summarize_action(action: ActionDict | None) -> str:
    """Short human-readable summary used in options descriptions."""
    if not action_is_valid(action):
        return "—"
    assert action is not None
    if action[ATTR_TYPE] == ACTION_BUTTON:
        return f"button:{action[ATTR_ENTITY_ID]}"
    device = action.get(ATTR_DEVICE)
    suffix = f" / {device}" if device else ""
    return f"ir:{action[ATTR_ENTITY_ID]}{suffix} → {action[ATTR_COMMAND]}"


def copy_config(data: dict[str, Any]) -> dict[str, Any]:
    """Deep-ish copy of integration config stored on the config entry."""
    commands = data.get("commands") or {}
    sources = data.get("sources") or []
    sensor = data.get(CONF_POWER_SENSOR) or None
    if isinstance(sensor, str):
        sensor = sensor.strip() or None
    else:
        sensor = None
    return {
        "name": data.get("name", ""),
        "commands": {key: dict(value) for key, value in commands.items() if value},
        "sources": [
            {
                ATTR_NAME: src.get(ATTR_NAME, ""),
                ATTR_ACTION: dict(src[ATTR_ACTION]) if src.get(ATTR_ACTION) else {},
            }
            for src in sources
            if isinstance(src, dict)
        ],
        CONF_DEFAULT_REMOTE: data.get(CONF_DEFAULT_REMOTE),
        CONF_DEFAULT_DEVICE: data.get(CONF_DEFAULT_DEVICE),
        CONF_POWER_SENSOR: sensor,
        CONF_POWER_SENSOR_INVERT: bool(data.get(CONF_POWER_SENSOR_INVERT)),
    }


_SENSOR_ON = "on"
_SENSOR_OFF = "off"
_SENSOR_UNKNOWN = {"unavailable", "unknown", "none", ""}


def power_is_on_from_sensor(state: str | None, *, invert: bool = False) -> bool | None:
    """Map a binary_sensor state to TV power.

    Returns True/False when the sensor reports a clear on/off, else None
    (unavailable, unknown, or missing). invert=True means sensor on = TV off.
    """
    if state is None:
        return None
    value = str(state).strip().lower()
    if value in _SENSOR_UNKNOWN or value not in (_SENSOR_ON, _SENSOR_OFF):
        return None
    is_on = value == _SENSOR_ON
    return (not is_on) if invert else is_on


def normalize_power_sensor(entity_id: str | None) -> tuple[str | None, str | None]:
    """Validate an optional binary_sensor entity id.

    Returns (entity_id_or_none, error_key).
    """
    if not entity_id:
        return None, None
    cleaned = str(entity_id).strip()
    if not cleaned:
        return None, None
    if not cleaned.startswith("binary_sensor."):
        return None, "invalid_power_sensor"
    return cleaned, None
