"""Constants for the IR Television integration."""

from __future__ import annotations

DOMAIN = "ir_television"
PLATFORMS = ["media_player", "remote", "button"]

# Shown when the user configured no HDMI / app sources. HomeKit needs at least
# one Input Source (CHAR_ACTIVE_IDENTIFIER) for the Control Center Remote.
DEFAULT_SOURCE_NAME = "TV"

# Fired by HA HomeKit TelevisionMediaPlayer when the iOS Control Center Remote
# sends a D-pad / menu key (see homeassistant.components.homekit).
EVENT_HOMEKIT_TV_REMOTE_KEY_PRESSED = "homekit_tv_remote_key_pressed"

DEFAULT_MANUFACTURER = "IR Television"
# Shown under the device name in Settings → Devices (same as HomeKit Model).
DEVICE_MODEL = "Media Player"
MANUFACTURER = DEFAULT_MANUFACTURER

CONF_NAME = "name"
CONF_MANUFACTURER = "manufacturer"
CONF_COMMANDS = "commands"
CONF_SOURCES = "sources"
CONF_DEFAULT_REMOTE = "default_remote"
CONF_DEFAULT_DEVICE = "default_device"
CONF_POWER_SENSOR = "power_sensor"
CONF_POWER_SENSOR_INVERT = "power_sensor_invert"

# Action payload keys
CONF_ACTION_TYPE = "action_type"
CONF_REMOTE_ENTITY = "remote_entity"
CONF_BUTTON_ENTITY = "button_entity"
CONF_DEVICE = "device"
CONF_COMMAND = "command"
CONF_NUM_REPEATS = "num_repeats"
CONF_BUTTON_REPEATS = "button_repeats"
CONF_INTERVAL = "interval"
CONF_SOURCE_NAME = "source_name"
CONF_SOURCE_ORDER = "source_order"
CONF_REORDER_ACTION = "reorder_action"
REORDER_ACTION_APPLY = "apply"
REORDER_ACTION_BACK = "back"

ACTION_BROADLINK = "broadlink"
ACTION_BUTTON = "button"

# Stored action dict keys
ATTR_TYPE = "type"
ATTR_ENTITY_ID = "entity_id"
ATTR_DEVICE = "device"
ATTR_COMMAND = "command"
ATTR_NUM_REPEATS = "num_repeats"
ATTR_NAME = "name"
ATTR_ACTION = "action"
ATTR_BUTTONS = "buttons"
ATTR_INTERVAL = "interval"
ATTR_REPEATS = "repeats"
DEFAULT_BUTTON_INTERVAL = 0.3
MAX_BUTTON_REPEATS = 10
MAX_BUTTON_INTERVAL = 10.0

# Command keys (stored in entry.data["commands"])
CMD_TURN_ON = "turn_on"
CMD_TURN_OFF = "turn_off"
CMD_POWER_TOGGLE = "power_toggle"
CMD_VOLUME_UP = "volume_up"
CMD_VOLUME_DOWN = "volume_down"
CMD_VOLUME_MUTE = "volume_mute"
CMD_PLAY = "play"
CMD_PAUSE = "pause"
CMD_PLAY_PAUSE = "play_pause"
CMD_STOP = "stop"
CMD_NEXT_TRACK = "next_track"
CMD_PREVIOUS_TRACK = "previous_track"
CMD_UP = "up"
CMD_DOWN = "down"
CMD_LEFT = "left"
CMD_RIGHT = "right"
CMD_OK = "ok"
CMD_BACK = "back"
CMD_HOME = "home"
CMD_MENU = "menu"
CMD_INFO = "info"

POWER_COMMANDS = (CMD_TURN_ON, CMD_TURN_OFF, CMD_POWER_TOGGLE)
VOLUME_COMMANDS = (CMD_VOLUME_UP, CMD_VOLUME_DOWN, CMD_VOLUME_MUTE)
PLAYBACK_COMMANDS = (CMD_PLAY, CMD_PAUSE, CMD_PLAY_PAUSE, CMD_STOP)
CHANNEL_COMMANDS = (CMD_NEXT_TRACK, CMD_PREVIOUS_TRACK)
NAV_COMMANDS = (
    CMD_UP,
    CMD_DOWN,
    CMD_LEFT,
    CMD_RIGHT,
    CMD_OK,
    CMD_BACK,
    CMD_HOME,
    CMD_MENU,
    CMD_INFO,
)

ALL_COMMANDS = (
    POWER_COMMANDS + VOLUME_COMMANDS + PLAYBACK_COMMANDS + CHANNEL_COMMANDS + NAV_COMMANDS
)

POWER_MODE_ON_OFF = "on_off"
POWER_MODE_TOGGLE = "toggle"
POWER_MODE_SKIP = "skip"

# Intents resolved by helpers (may map to a different stored command)
INTENT_TURN_ON = "turn_on"
INTENT_TURN_OFF = "turn_off"
INTENT_TOGGLE = "toggle"
INTENT_PLAY = "play"
INTENT_PAUSE = "pause"
INTENT_PLAY_PAUSE = "play_pause"
INTENT_STOP = "stop"
INTENT_VOLUME_UP = "volume_up"
INTENT_VOLUME_DOWN = "volume_down"
INTENT_VOLUME_MUTE = "volume_mute"
INTENT_NEXT = "next_track"
INTENT_PREVIOUS = "previous_track"

# MediaPlayerEntityFeature bit values (homeassistant.components.media_player)
FEATURE_PAUSE = 1
FEATURE_VOLUME_SET = 4
FEATURE_VOLUME_MUTE = 8
FEATURE_PREVIOUS_TRACK = 16
FEATURE_NEXT_TRACK = 32
FEATURE_TURN_ON = 128
FEATURE_TURN_OFF = 256
FEATURE_PLAY_MEDIA = 512
FEATURE_VOLUME_STEP = 1024
FEATURE_SELECT_SOURCE = 2048
FEATURE_STOP = 4096
FEATURE_PLAY = 16384
FEATURE_BROWSE_MEDIA = 131072

# Official braviatv media_player._attr_supported_features (bitmask 155581).
# HomeKit snapshots this at pairing; a sparse mask makes iOS skip the TV.
HOMEKIT_TV_FEATURES = (
    FEATURE_PAUSE
    | FEATURE_VOLUME_SET
    | FEATURE_VOLUME_MUTE
    | FEATURE_PREVIOUS_TRACK
    | FEATURE_NEXT_TRACK
    | FEATURE_TURN_ON
    | FEATURE_TURN_OFF
    | FEATURE_PLAY_MEDIA
    | FEATURE_VOLUME_STEP
    | FEATURE_SELECT_SOURCE
    | FEATURE_STOP
    | FEATURE_PLAY
    | FEATURE_BROWSE_MEDIA
)

HOMEKIT_DOMAIN = "homekit"
HOMEKIT_MODE_ACCESSORY = "accessory"
HOMEKIT_MODE_BRIDGE = "bridge"
HOMEKIT_DEFAULT_BRIDGE_PORT = 21063
HOMEKIT_FILTER = "filter"
HOMEKIT_INCLUDE_DOMAINS = "include_domains"
HOMEKIT_INCLUDE_ENTITIES = "include_entities"
HOMEKIT_EXCLUDE_ENTITIES = "exclude_entities"
HOMEKIT_PORT = "port"
HOMEKIT_MODE = "mode"

BUTTON_ICONS = {
    CMD_UP: "mdi:arrow-up",
    CMD_DOWN: "mdi:arrow-down",
    CMD_LEFT: "mdi:arrow-left",
    CMD_RIGHT: "mdi:arrow-right",
    CMD_OK: "mdi:checkbox-blank-circle",
    CMD_BACK: "mdi:arrow-u-left-top",
    CMD_HOME: "mdi:home",
    CMD_MENU: "mdi:menu",
    CMD_INFO: "mdi:information",
}

COMMAND_LABELS_EN = {
    CMD_TURN_ON: "Power on",
    CMD_TURN_OFF: "Power off",
    CMD_POWER_TOGGLE: "Power toggle",
    CMD_VOLUME_UP: "Volume up",
    CMD_VOLUME_DOWN: "Volume down",
    CMD_VOLUME_MUTE: "Mute",
    CMD_PLAY: "Play",
    CMD_PAUSE: "Pause",
    CMD_PLAY_PAUSE: "Play / Pause",
    CMD_STOP: "Stop",
    CMD_NEXT_TRACK: "Channel / next",
    CMD_PREVIOUS_TRACK: "Channel / previous",
    CMD_UP: "Up",
    CMD_DOWN: "Down",
    CMD_LEFT: "Left",
    CMD_RIGHT: "Right",
    CMD_OK: "OK / Select",
    CMD_BACK: "Back",
    CMD_HOME: "Home",
    CMD_MENU: "Menu",
    CMD_INFO: "Info",
}

COMMAND_LABELS_ZH = {
    CMD_TURN_ON: "开机",
    CMD_TURN_OFF: "关机",
    CMD_POWER_TOGGLE: "电源开关（切换）",
    CMD_VOLUME_UP: "音量加",
    CMD_VOLUME_DOWN: "音量减",
    CMD_VOLUME_MUTE: "静音",
    CMD_PLAY: "播放",
    CMD_PAUSE: "暂停",
    CMD_PLAY_PAUSE: "播放/暂停",
    CMD_STOP: "停止",
    CMD_NEXT_TRACK: "频道加 / 下一首",
    CMD_PREVIOUS_TRACK: "频道减 / 上一首",
    CMD_UP: "上",
    CMD_DOWN: "下",
    CMD_LEFT: "左",
    CMD_RIGHT: "右",
    CMD_OK: "确定 / 选择",
    CMD_BACK: "返回",
    CMD_HOME: "主页",
    CMD_MENU: "菜单",
    CMD_INFO: "信息",
}


def command_label(language: str | None, key: str) -> str:
    """Return a localized label for a command key."""
    lang = (language or "en").lower()
    table = COMMAND_LABELS_ZH if lang.startswith("zh") else COMMAND_LABELS_EN
    return table.get(key, key)
