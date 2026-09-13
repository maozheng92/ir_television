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
    CMD_BACK,
    CMD_DOWN,
    CMD_HOME,
    CMD_INFO,
    CMD_LEFT,
    CMD_OK,
    CMD_PAUSE,
    CMD_PLAY,
    CMD_PLAY_PAUSE,
    CMD_POWER_TOGGLE,
    CMD_RIGHT,
    CMD_STOP,
    CMD_TURN_OFF,
    CMD_TURN_ON,
    CMD_UP,
    CMD_VOLUME_DOWN,
    CMD_VOLUME_MUTE,
    CMD_VOLUME_UP,
    CONF_ACTION_TYPE,
    CONF_BUTTON_ENTITY,
    CONF_COMMAND,
    CONF_DEFAULT_DEVICE,
    CONF_DEFAULT_REMOTE,
    CONF_DEVICE,
    CONF_MANUFACTURER,
    CONF_NUM_REPEATS,
    CONF_POWER_SENSOR,
    CONF_POWER_SENSOR_INVERT,
    CONF_REMOTE_ENTITY,
    DEFAULT_MANUFACTURER,
    DEFAULT_SOURCE_NAME,
    HOMEKIT_DEFAULT_BRIDGE_PORT,
    HOMEKIT_EXCLUDE_ENTITIES,
    HOMEKIT_FILTER,
    HOMEKIT_INCLUDE_DOMAINS,
    HOMEKIT_INCLUDE_ENTITIES,
    HOMEKIT_MODE,
    HOMEKIT_MODE_ACCESSORY,
    HOMEKIT_MODE_BRIDGE,
    HOMEKIT_PORT,
    HOMEKIT_TV_FEATURES,
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


def resolve_manufacturer(data: dict[str, Any] | None) -> str:
    """Return the configured manufacturer, or the integration default."""
    raw = (data or {}).get(CONF_MANUFACTURER)
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return DEFAULT_MANUFACTURER


def format_source_order(sources: list[Any] | None) -> str:
    """Human-readable source order for config-flow placeholders."""
    names = _configured_source_names(sources)
    if not names:
        return "—"
    return " → ".join(f"{index}. {name}" for index, name in enumerate(names, start=1))


def move_source(
    sources: list[SourceDict] | None, name: str, *, delta: int
) -> list[SourceDict]:
    """Return a copy of ``sources`` with ``name`` moved by ``delta`` (-1 / +1)."""
    items: list[SourceDict] = [
        dict(source) for source in (sources or []) if isinstance(source, dict)
    ]
    target = normalize_source_name(name).lower()
    if not target or delta == 0:
        return items
    index = next(
        (
            idx
            for idx, source in enumerate(items)
            if normalize_source_name(str(source.get(ATTR_NAME, ""))).lower() == target
        ),
        None,
    )
    if index is None:
        return items
    new_index = index + int(delta)
    if new_index < 0 or new_index >= len(items):
        return items
    items[index], items[new_index] = items[new_index], items[index]
    return items


def reorder_sources(
    sources: list[SourceDict] | None, ordered_names: list[Any] | None
) -> tuple[list[SourceDict], str | None]:
    """Return sources in ``ordered_names`` order.

    The name set must match exactly (just a permutation). On mismatch
    returns the original copy and an error key.
    """
    items: list[SourceDict] = [
        dict(source) for source in (sources or []) if isinstance(source, dict)
    ]
    by_key: dict[str, SourceDict] = {}
    expected: list[str] = []
    for source in items:
        key = normalize_source_name(str(source.get(ATTR_NAME, ""))).lower()
        if not key:
            continue
        by_key[key] = source
        expected.append(key)

    if isinstance(ordered_names, str):
        raw_names = [ordered_names]
    else:
        raw_names = list(ordered_names or [])
    got = [normalize_source_name(str(name)) for name in raw_names]
    got_keys = [name.lower() for name in got if name]
    if got_keys != expected and sorted(got_keys) == sorted(expected) and len(got_keys) == len(expected):
        return [by_key[key] for key in got_keys], None
    if got_keys == expected:
        return items, None
    return items, "incomplete_source_order"


def _has_action(commands: dict[str, Any], key: str) -> bool:
    action = commands.get(key)
    return bool(action) and isinstance(action, dict) and bool(action.get(ATTR_TYPE))


def compute_supported_features(
    commands: dict[str, Any] | None,
    sources: list[Any] | None,
) -> int:
    """Return a MediaPlayerEntityFeature bitmask for HomeKit Television.

    Matches the official Sony Bravia integration: the bits are advertised even
    when the user has not mapped every IR key. HomeKit snapshots features at
    accessory pairing; a sparse bitmask makes iOS treat the entity as switches
    (or skip it) instead of listing it in Control Center Remote.
    """
    del commands, sources
    return int(HOMEKIT_TV_FEATURES)


def split_homekit_iid_key(key: str) -> tuple[str, str, str]:
    """Split an HA HomeKit iid key ``{service}_{unique}_{char}_``."""
    body = key[:-1] if key.endswith("_") else key
    parts = body.split("_")
    service = parts[0] if parts else ""
    if len(parts) < 2:
        return service, "", ""
    char = parts[-1]
    unique = "_".join(parts[1:-1])
    return service, unique, char


def decode_homekit_iid_allocations(
    allocations: dict[str, Any] | None,
) -> dict[str, Any]:
    """Summarize a ``homekit.*.iids`` allocations blob.

    A working iOS Control Center Remote accessory is a *single* HAP accessory
    (aid 1 in accessory mode) with Television (D8) + RemoteKey (E8) + at least
    one Input Source (D9). TelevisionSpeaker (113) is optional but present for
    volume. A Bridge would typically have aid 1 *without* D8 (bridge info only)
    and the TV on aid 2+.
    """
    accessories: list[dict[str, Any]] = []
    for aid, mapping in (allocations or {}).items():
        if not isinstance(mapping, dict):
            continue
        sources: list[str] = []
        chars_by_service: dict[str, set[str]] = {}
        for key in mapping:
            service, unique, char = split_homekit_iid_key(str(key))
            bucket = f"{service}:{unique}" if unique else service
            chars_by_service.setdefault(bucket, set())
            if char:
                chars_by_service[bucket].add(char)
            if service == "D9" and unique and unique not in sources:
                sources.append(unique)
        has_television = any(name == "D8" or name.startswith("D8:") for name in chars_by_service)
        tv_chars = chars_by_service.get("D8", set())
        accessories.append(
            {
                "aid": str(aid),
                "has_accessory_information": "3E" in chars_by_service,
                "has_protocol_information": "A2" in chars_by_service,
                "has_television": has_television,
                "has_remote_key": "E8" in tv_chars,
                "has_sleep_discovery": "E1" in tv_chars,
                "has_speaker": any(
                    name == "113" or name.startswith("113:") for name in chars_by_service
                ),
                "input_sources": sources,
                "ios_remote_ready": bool(
                    has_television and "E8" in tv_chars and sources
                ),
            }
        )
    tv_on_aid1 = bool(accessories and accessories[0].get("ios_remote_ready"))
    return {
        "accessory_count": len(accessories),
        "looks_like_accessory_mode_tv": tv_on_aid1 and len(accessories) == 1,
        "accessories": accessories,
    }


# HAP mDNS TXT ``ci`` (pyhap / HAP-NodeJS / Apple HomeKitADK).
# 24 is Apple TV, not a generic television. 31 is Television.
HAP_CATEGORY_APPLE_TV = 24
HAP_CATEGORY_TELEVISION = 31
HAP_CATEGORY_AUDIO_RECEIVER = 34
HAP_CATEGORY_TV_SET_TOP_BOX = 35
HAP_CATEGORY_TV_STREAMING_STICK = 36

HAP_CATEGORY_NAMES = {
    HAP_CATEGORY_APPLE_TV: "apple_tv",
    HAP_CATEGORY_TELEVISION: "television",
    HAP_CATEGORY_AUDIO_RECEIVER: "audio_receiver",
    HAP_CATEGORY_TV_SET_TOP_BOX: "tv_set_top_box",
    HAP_CATEGORY_TV_STREAMING_STICK: "tv_streaming_stick",
}


def decode_hap_mdns_txt(txt: dict[str, Any] | None) -> dict[str, Any]:
    """Interpret HAP ``_hap._tcp`` TXT records (Discovery / Bonjour).

    ``ci=31`` is Television. ``ci=24`` is Apple TV. ``sf`` bit 0 set
    (``sf=1``) means *not paired*.
    """

    def _as_int(key: str) -> int | None:
        raw = (txt or {}).get(key)
        if raw is None or raw == "":
            return None
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None

    sf = _as_int("sf") or 0
    ci = _as_int("ci")
    not_paired = bool(sf & 1)
    return {
        "category": ci,
        "category_name": HAP_CATEGORY_NAMES.get(ci) if ci is not None else None,
        "is_television": ci == HAP_CATEGORY_TELEVISION,
        "is_apple_tv": ci == HAP_CATEGORY_APPLE_TV,
        "not_paired": not_paired,
        "paired": not not_paired,
        "protocol": str((txt or {}).get("pv") or ""),
        "config_number": _as_int("c#"),
        "accessory_id": str((txt or {}).get("id") or ""),
        "model": str((txt or {}).get("md") or ""),
        "ios_remote_listed": ci == HAP_CATEGORY_TELEVISION and not not_paired,
    }


def homekit_entry_mode(data: dict[str, Any], options: dict[str, Any]) -> str:
    """Return HomeKit mode. Missing mode is a bridge (HA default)."""
    mode = options.get(HOMEKIT_MODE, data.get(HOMEKIT_MODE))
    if mode == HOMEKIT_MODE_ACCESSORY:
        return HOMEKIT_MODE_ACCESSORY
    return HOMEKIT_MODE_BRIDGE


def homekit_filter_dict(data: dict[str, Any], options: dict[str, Any]) -> dict[str, Any]:
    """Return the entity filter. Options win after a UI edit."""
    for blob in (options, data):
        filt = blob.get(HOMEKIT_FILTER)
        if isinstance(filt, dict):
            return dict(filt)
    return {}


def describe_homekit_entries(
    entries: list[tuple[dict[str, Any], dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Summarize HomeKit config entries (data, options) for diagnostics."""
    described: list[dict[str, Any]] = []
    for data, options in entries:
        filt = homekit_filter_dict(data, options)
        described.append(
            {
                "mode": homekit_entry_mode(data, options),
                "name": options.get("name", data.get("name")),
                "port": options.get(HOMEKIT_PORT, data.get(HOMEKIT_PORT)),
                "include_domains": list(filt.get(HOMEKIT_INCLUDE_DOMAINS) or []),
                "include_entities": list(filt.get(HOMEKIT_INCLUDE_ENTITIES) or []),
                "exclude_entities": list(filt.get(HOMEKIT_EXCLUDE_ENTITIES) or []),
            }
        )
    return described


def homekit_entries_for_entity(
    entries: list[tuple[dict[str, Any], dict[str, Any], str]],
    entity_id: str,
) -> list[str]:
    """Return config entry ids whose include_entities list contains ``entity_id``.

    Each item is ``(data, options, entry_id)``. Does not treat include_domains
    as a match — a HomeKit *bridge* that includes the ``media_player`` domain
    must never be deleted just because this TV exists.
    """
    matches: list[str] = []
    for data, options, entry_id in entries:
        filt = homekit_filter_dict(data, options)
        include = [str(item) for item in (filt.get(HOMEKIT_INCLUDE_ENTITIES) or [])]
        if entity_id in include:
            matches.append(entry_id)
    return matches


def homekit_accessory_entries_for_entity(
    entries: list[tuple[dict[str, Any], dict[str, Any], str]],
    entity_id: str,
) -> list[str]:
    """Accessory-mode HomeKit entries that expose exactly this entity.

    Safe to delete/recreate. Never returns a bridge (Sony lives on that bridge).
    """
    matches: list[str] = []
    for data, options, entry_id in entries:
        if homekit_entry_mode(data, options) != HOMEKIT_MODE_ACCESSORY:
            continue
        filt = homekit_filter_dict(data, options)
        include = [str(item) for item in (filt.get(HOMEKIT_INCLUDE_ENTITIES) or [])]
        if entity_id in include:
            matches.append(entry_id)
    return matches


def pick_homekit_bridge_entry_id(
    entries: list[tuple[dict[str, Any], dict[str, Any], str]],
) -> str | None:
    """Pick the HomeKit Bridge that already exposes TVs (Sony's path).

    Prefers a bridge that includes the ``media_player`` domain or any
    ``media_player.*`` entity — that is the instance Sony Bravia was added to.
    """
    scored: list[tuple[int, str]] = []
    for data, options, entry_id in entries:
        if homekit_entry_mode(data, options) == HOMEKIT_MODE_ACCESSORY:
            continue
        filt = homekit_filter_dict(data, options)
        include_domains = [str(item) for item in (filt.get(HOMEKIT_INCLUDE_DOMAINS) or [])]
        include_entities = [str(item) for item in (filt.get(HOMEKIT_INCLUDE_ENTITIES) or [])]
        score = 0
        if "media_player" in include_domains:
            score += 2
        if any(item.startswith("media_player.") for item in include_entities):
            score += 1
        scored.append((score, entry_id))
    if not scored:
        return None
    scored.sort(key=lambda item: (-item[0], item[1]))
    return scored[0][1]


def build_bridge_filter_including(
    filt: dict[str, Any] | None, entity_id: str
) -> dict[str, Any]:
    """Return a copy of ``filt`` that explicitly includes ``entity_id``.

    Home Assistant includes an entity listed in ``include_entities`` even when
    the domain is not in ``include_domains``. Also drops the entity from
    ``exclude_entities`` so a previous exclude cannot hide it.
    """
    new_filt = dict(filt or {})
    include_entities = [str(item) for item in (new_filt.get(HOMEKIT_INCLUDE_ENTITIES) or [])]
    exclude_entities = [str(item) for item in (new_filt.get(HOMEKIT_EXCLUDE_ENTITIES) or [])]
    if entity_id not in include_entities:
        include_entities.append(entity_id)
    exclude_entities = [item for item in exclude_entities if item != entity_id]
    new_filt[HOMEKIT_INCLUDE_ENTITIES] = include_entities
    new_filt[HOMEKIT_EXCLUDE_ENTITIES] = exclude_entities
    return new_filt


def homekit_accessory_entity_ids(entries: list[tuple[dict[str, Any], dict[str, Any]]]) -> set[str]:
    """Return entity ids already exposed as HomeKit accessory-mode TVs.

    Each item is ``(entry.data, entry.options)``. HomeKit stores mode/filter on
    data for accessory-source entries, and on options after some UI edits.
    """
    entity_ids: set[str] = set()
    for data, options in entries:
        mode = options.get(HOMEKIT_MODE, data.get(HOMEKIT_MODE))
        if mode != HOMEKIT_MODE_ACCESSORY:
            continue
        filt = options.get(HOMEKIT_FILTER) or data.get(HOMEKIT_FILTER) or {}
        include = filt.get(HOMEKIT_INCLUDE_ENTITIES) or []
        if include:
            entity_ids.add(str(include[0]))
    return entity_ids


def collect_homekit_ports(entries: list[tuple[dict[str, Any], dict[str, Any]]]) -> set[int]:
    """Ports already used by HomeKit config entries."""
    ports: set[int] = set()
    for data, options in entries:
        for blob in (options, data):
            port = blob.get(HOMEKIT_PORT)
            if port is None:
                continue
            try:
                ports.add(int(port))
            except (TypeError, ValueError):
                continue
    return ports


def next_homekit_port(
    used_ports: set[int], start: int = HOMEKIT_DEFAULT_BRIDGE_PORT + 1
) -> int:
    """Pick the next free HomeKit TCP port (default bridge uses 21063)."""
    port = start
    while port in used_ports:
        port += 1
    return port


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


# HomeKit Television REMOTE_KEYS → stored command keys (see homekit/const.py).
# Fallbacks are applied in resolve_homekit_remote_key.
HOMEKIT_REMOTE_KEY_COMMANDS: dict[str, str] = {
    "arrow_up": CMD_UP,
    "arrow_down": CMD_DOWN,
    "arrow_left": CMD_LEFT,
    "arrow_right": CMD_RIGHT,
    "select": CMD_OK,
    "back": CMD_BACK,
    "information": CMD_INFO,
    "next_track": INTENT_NEXT,
    "previous_track": INTENT_PREVIOUS,
}


def resolve_homekit_remote_key(
    commands: dict[str, Any] | None, key_name: str | None
) -> str | None:
    """Map a HomeKit ``key_name`` to a configured IR/button command key.

    HomeKit fires ``homekit_tv_remote_key_pressed`` with names such as
    ``arrow_up``, ``select``, ``exit``, ``play_pause``. Returns the stored
    command key to send, or None if nothing is mapped.

    Fallbacks:
    - play_pause → play, then pause
    - exit / home → home, then back
    - rewind → previous_track, then left
    - fast_forward → next_track, then right
    """
    commands = commands or {}
    key = (key_name or "").strip().lower()
    if not key:
        return None

    if key == "play_pause":
        for candidate in (CMD_PLAY_PAUSE, CMD_PLAY, CMD_PAUSE):
            if _has_action(commands, candidate):
                return candidate
        return None

    if key in ("exit", "home"):
        for candidate in (CMD_HOME, CMD_BACK):
            if _has_action(commands, candidate):
                return candidate
        return None

    if key == "rewind":
        for candidate in (INTENT_PREVIOUS, CMD_LEFT):
            if _has_action(commands, candidate):
                return candidate
        return None

    if key == "fast_forward":
        for candidate in (INTENT_NEXT, CMD_RIGHT):
            if _has_action(commands, candidate):
                return candidate
        return None

    mapped = HOMEKIT_REMOTE_KEY_COMMANDS.get(key)
    if mapped and _has_action(commands, mapped):
        return mapped
    # remote.send_command("up") / stored IR key names, not only HomeKit names
    if _has_action(commands, key):
        return key
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


def _configured_source_names(sources: list[Any] | None) -> list[str]:
    """Return display names the user actually configured (may be empty)."""
    names: list[str] = []
    for source in sources or []:
        if not isinstance(source, dict):
            continue
        name = normalize_source_name(str(source.get(ATTR_NAME, "")))
        if name:
            names.append(name)
    return names


def build_source_list(sources: list[Any] | None) -> list[str]:
    """Return display names for sources.

    Always includes at least ``DEFAULT_SOURCE_NAME`` ("TV") so HomeKit can
    create Input Source services even when the user added none.
    """
    return _configured_source_names(sources) or [DEFAULT_SOURCE_NAME]


def current_source_name(source: str | None, sources: list[Any] | None) -> str | None:
    """Return a source that always exists in ``source_list``.

    HomeKit CHAR_ACTIVE_IDENTIFIER must match an Input Source. If the stored
    current source is missing, fall back to the first advertised name.
    """
    names = build_source_list(sources)
    if not names:
        return None
    target = normalize_source_name(source).lower()
    if target:
        for name in names:
            if name.lower() == target:
                return name
    return names[0]


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
    """True if at least one command or user-configured source is set.

    The implicit default "TV" source does not count — the user must still
    map at least one IR/button command or a real HDMI/app source.
    """
    commands = commands or {}
    if any(_has_action(commands, key) for key in commands):
        return True
    return bool(_configured_source_names(sources))


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
        CONF_MANUFACTURER: resolve_manufacturer(data),
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


def parse_broadlink_codes_payload(payload: Any) -> tuple[list[str], list[str]]:
    """Extract learned Broadlink device and command names from a codes file.

    Accepts either the storage wrapper ``{"data": {...}}`` or the inner mapping
    ``{device_name: {command_name: code}}``.
    """
    devices: set[str] = set()
    commands: set[str] = set()
    if not isinstance(payload, dict):
        return [], []
    inner = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    if not isinstance(inner, dict):
        return [], []
    for device_name, cmds in inner.items():
        name = str(device_name).strip() if device_name is not None else ""
        if name:
            devices.add(name)
        if not isinstance(cmds, dict):
            continue
        for command in cmds:
            cmd = str(command).strip() if command is not None else ""
            if cmd:
                commands.add(cmd)
    return sorted(devices), sorted(commands)
