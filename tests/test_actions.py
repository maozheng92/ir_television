"""Stdlib tests for feature flags, source rules, and service payloads."""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path

_PKG_DIR = Path(__file__).resolve().parents[1] / "custom_components" / "ir_television"
_PKG_NAME = "ir_television_pure"


def _load_helpers():
    """Import const + actions without executing the HA-dependent package __init__."""
    if f"{_PKG_NAME}.actions" in sys.modules:
        return sys.modules[f"{_PKG_NAME}.const"], sys.modules[f"{_PKG_NAME}.actions"]

    pkg = types.ModuleType(_PKG_NAME)
    pkg.__path__ = [str(_PKG_DIR)]
    sys.modules[_PKG_NAME] = pkg

    def _load(modname: str, filename: str):
        spec = importlib.util.spec_from_file_location(
            f"{_PKG_NAME}.{modname}",
            _PKG_DIR / filename,
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load {_PKG_DIR / filename}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"{_PKG_NAME}.{modname}"] = module
        spec.loader.exec_module(module)
        return module

    const_mod = _load("const", "const.py")
    actions_mod = _load("actions", "actions.py")
    return const_mod, actions_mod


const, actions = _load_helpers()

ACTION_BROADLINK = const.ACTION_BROADLINK
ACTION_BUTTON = const.ACTION_BUTTON
FEATURE_NEXT_TRACK = const.FEATURE_NEXT_TRACK
FEATURE_PAUSE = const.FEATURE_PAUSE
FEATURE_PLAY = const.FEATURE_PLAY
FEATURE_PREVIOUS_TRACK = const.FEATURE_PREVIOUS_TRACK
FEATURE_SELECT_SOURCE = const.FEATURE_SELECT_SOURCE
FEATURE_TURN_OFF = const.FEATURE_TURN_OFF
FEATURE_TURN_ON = const.FEATURE_TURN_ON
FEATURE_VOLUME_MUTE = const.FEATURE_VOLUME_MUTE
FEATURE_VOLUME_STEP = const.FEATURE_VOLUME_STEP
INTENT_PAUSE = const.INTENT_PAUSE
INTENT_PLAY = const.INTENT_PLAY
INTENT_PLAY_PAUSE = const.INTENT_PLAY_PAUSE
INTENT_TOGGLE = const.INTENT_TOGGLE
INTENT_TURN_OFF = const.INTENT_TURN_OFF
INTENT_TURN_ON = const.INTENT_TURN_ON

action_is_valid = actions.action_is_valid
build_button_service_data = actions.build_button_service_data
build_remote_service_data = actions.build_remote_service_data
build_source_list = actions.build_source_list
compute_supported_features = actions.compute_supported_features
copy_config = actions.copy_config
find_source = actions.find_source
has_useful_config = actions.has_useful_config
normalize_power_sensor = actions.normalize_power_sensor
parse_action_input = actions.parse_action_input
parse_broadlink_codes_payload = actions.parse_broadlink_codes_payload
power_is_on_from_sensor = actions.power_is_on_from_sensor
resolve_command_key = actions.resolve_command_key
validate_source_name = actions.validate_source_name


def _ir(command: str, device: str | None = "tv") -> dict:
    action = {
        "type": ACTION_BROADLINK,
        "entity_id": "remote.rm4",
        "command": command,
    }
    if device:
        action["device"] = device
    return action


def _btn(entity_id: str = "button.tv_ok") -> dict:
    return {"type": ACTION_BUTTON, "entity_id": entity_id}


class FeatureFlagTests(unittest.TestCase):
    def test_empty(self) -> None:
        self.assertEqual(compute_supported_features({}, []), 0)

    def test_power_toggle_enables_on_and_off(self) -> None:
        commands = {"power_toggle": _ir("power")}
        bits = compute_supported_features(commands, [])
        self.assertTrue(bits & FEATURE_TURN_ON)
        self.assertTrue(bits & FEATURE_TURN_OFF)
        self.assertFalse(bits & FEATURE_VOLUME_STEP)

    def test_on_off_separate(self) -> None:
        commands = {"turn_on": _ir("on"), "turn_off": _ir("off")}
        bits = compute_supported_features(commands, [])
        self.assertTrue(bits & FEATURE_TURN_ON)
        self.assertTrue(bits & FEATURE_TURN_OFF)

    def test_volume_and_mute(self) -> None:
        commands = {
            "volume_up": _ir("volup"),
            "volume_mute": _btn("button.mute"),
        }
        bits = compute_supported_features(commands, [])
        self.assertTrue(bits & FEATURE_VOLUME_STEP)
        self.assertTrue(bits & FEATURE_VOLUME_MUTE)

    def test_play_pause_single_key(self) -> None:
        bits = compute_supported_features({"play_pause": _ir("pp")}, [])
        self.assertTrue(bits & FEATURE_PLAY)
        self.assertTrue(bits & FEATURE_PAUSE)

    def test_play_only(self) -> None:
        bits = compute_supported_features({"play": _ir("play")}, [])
        self.assertTrue(bits & FEATURE_PLAY)
        self.assertFalse(bits & FEATURE_PAUSE)

    def test_channels_and_sources(self) -> None:
        commands = {"next_track": _ir("ch+"), "previous_track": _ir("ch-")}
        sources = [{"name": "HDMI 1", "action": _ir("hdmi1")}]
        bits = compute_supported_features(commands, sources)
        self.assertTrue(bits & FEATURE_NEXT_TRACK)
        self.assertTrue(bits & FEATURE_PREVIOUS_TRACK)
        self.assertTrue(bits & FEATURE_SELECT_SOURCE)

    def test_source_list_ignores_blank(self) -> None:
        self.assertEqual(
            build_source_list([{"name": "  HDMI 1 "}, {"name": "  "}, "x"]),
            ["HDMI 1"],
        )


class ResolveCommandTests(unittest.TestCase):
    def test_power_toggle_fallback(self) -> None:
        commands = {"power_toggle": _ir("pwr")}
        self.assertEqual(resolve_command_key(commands, INTENT_TURN_ON), "power_toggle")
        self.assertEqual(resolve_command_key(commands, INTENT_TURN_OFF), "power_toggle")
        self.assertEqual(resolve_command_key(commands, INTENT_TOGGLE), "power_toggle")

    def test_prefer_dedicated_on(self) -> None:
        commands = {"turn_on": _ir("on"), "power_toggle": _ir("pwr")}
        self.assertEqual(resolve_command_key(commands, INTENT_TURN_ON), "turn_on")

    def test_play_maps_to_play_pause(self) -> None:
        commands = {"play_pause": _ir("pp")}
        self.assertEqual(resolve_command_key(commands, INTENT_PLAY), "play_pause")
        self.assertEqual(resolve_command_key(commands, INTENT_PAUSE), "play_pause")
        self.assertEqual(resolve_command_key(commands, INTENT_PLAY_PAUSE), "play_pause")

    def test_missing_is_none(self) -> None:
        self.assertIsNone(resolve_command_key({}, INTENT_TURN_ON))
        self.assertIsNone(resolve_command_key({"turn_on": {}}, INTENT_TURN_ON))


class SourceValidationTests(unittest.TestCase):
    def test_trim_and_empty(self) -> None:
        self.assertEqual(validate_source_name("  ", []), "empty_name")
        self.assertIsNone(validate_source_name("Netflix", []))

    def test_duplicate_case_insensitive(self) -> None:
        sources = [{"name": "HDMI 1", "action": _ir("h1")}]
        self.assertEqual(validate_source_name("hdmi 1", sources), "duplicate_source")
        self.assertIsNone(validate_source_name("hdmi 1", sources, exclude_index=0))

    def test_find_source(self) -> None:
        sources = [{"name": "Netflix", "action": _btn()}]
        self.assertIsNotNone(find_source(sources, "netflix"))
        self.assertIsNone(find_source(sources, "YouTube"))

    def test_has_useful_config(self) -> None:
        self.assertFalse(has_useful_config({}, []))
        self.assertTrue(has_useful_config({"volume_up": _ir("v+")}, []))
        self.assertTrue(
            has_useful_config({}, [{"name": "HDMI 1", "action": _ir("h1")}])
        )


class ParseActionTests(unittest.TestCase):
    def test_broadlink_uses_defaults(self) -> None:
        action, err = parse_action_input(
            {"action_type": ACTION_BROADLINK, "command": " power_on "},
            defaults={"default_remote": "remote.rm4", "default_device": "living_tv"},
        )
        self.assertIsNone(err)
        self.assertEqual(
            action,
            {
                "type": ACTION_BROADLINK,
                "entity_id": "remote.rm4",
                "command": "power_on",
                "device": "living_tv",
            },
        )

    def test_broadlink_missing_remote(self) -> None:
        action, err = parse_action_input(
            {"action_type": ACTION_BROADLINK, "command": "ok"}
        )
        self.assertIsNone(action)
        self.assertEqual(err, "missing_remote")

    def test_broadlink_missing_command(self) -> None:
        _, err = parse_action_input(
            {"action_type": ACTION_BROADLINK, "remote_entity": "remote.rm4"}
        )
        self.assertEqual(err, "missing_command")

    def test_rejects_wrong_domain(self) -> None:
        _, err = parse_action_input(
            {
                "action_type": ACTION_BROADLINK,
                "remote_entity": "switch.rm4",
                "command": "ok",
            }
        )
        self.assertEqual(err, "invalid_entity")

    def test_button(self) -> None:
        action, err = parse_action_input(
            {"action_type": ACTION_BUTTON, "button_entity": "button.tv_netflix"}
        )
        self.assertIsNone(err)
        self.assertEqual(action, _btn("button.tv_netflix"))

    def test_repeats(self) -> None:
        action, err = parse_action_input(
            {
                "action_type": ACTION_BROADLINK,
                "remote_entity": "remote.rm4",
                "command": "volup",
                "num_repeats": 3,
            }
        )
        self.assertIsNone(err)
        self.assertEqual(action["num_repeats"], 3)

    def test_service_payloads(self) -> None:
        ir = _ir("hdmi_1", "living_tv")
        ir["num_repeats"] = 2
        self.assertEqual(
            build_remote_service_data(ir),
            {
                "entity_id": "remote.rm4",
                "command": "hdmi_1",
                "num_repeats": 2,
                "device": "living_tv",
            },
        )
        self.assertEqual(
            build_button_service_data(_btn("button.x")),
            {"entity_id": "button.x"},
        )

    def test_action_is_valid(self) -> None:
        self.assertTrue(action_is_valid(_ir("ok")))
        self.assertTrue(action_is_valid(_btn()))
        self.assertFalse(
            action_is_valid({"type": ACTION_BROADLINK, "entity_id": "remote.x"})
        )
        self.assertFalse(action_is_valid(None))


class PowerSensorTests(unittest.TestCase):
    def test_on_off(self) -> None:
        self.assertTrue(power_is_on_from_sensor("on"))
        self.assertFalse(power_is_on_from_sensor("off"))
        self.assertTrue(power_is_on_from_sensor("ON"))

    def test_unknown(self) -> None:
        self.assertIsNone(power_is_on_from_sensor(None))
        self.assertIsNone(power_is_on_from_sensor("unavailable"))
        self.assertIsNone(power_is_on_from_sensor("unknown"))
        self.assertIsNone(power_is_on_from_sensor(""))
        self.assertIsNone(power_is_on_from_sensor("playing"))

    def test_invert(self) -> None:
        self.assertFalse(power_is_on_from_sensor("on", invert=True))
        self.assertTrue(power_is_on_from_sensor("off", invert=True))
        self.assertIsNone(power_is_on_from_sensor("unavailable", invert=True))

    def test_normalize(self) -> None:
        self.assertEqual(normalize_power_sensor(None), (None, None))
        self.assertEqual(normalize_power_sensor("  "), (None, None))
        self.assertEqual(
            normalize_power_sensor("binary_sensor.tv_power"),
            ("binary_sensor.tv_power", None),
        )
        self.assertEqual(
            normalize_power_sensor("sensor.tv_power"),
            (None, "invalid_power_sensor"),
        )

    def test_copy_config_keeps_sensor(self) -> None:
        copied = copy_config(
            {
                "name": "Living TV",
                "commands": {"volume_up": _ir("v+")},
                "sources": [],
                "power_sensor": "binary_sensor.plug_tv",
                "power_sensor_invert": True,
            }
        )
        self.assertEqual(copied["power_sensor"], "binary_sensor.plug_tv")
        self.assertTrue(copied["power_sensor_invert"])

    def test_copy_config_defaults_sensor(self) -> None:
        copied = copy_config({"name": "TV", "commands": {}, "sources": []})
        self.assertIsNone(copied["power_sensor"])
        self.assertFalse(copied["power_sensor_invert"])


class BroadlinkCodesTests(unittest.TestCase):
    def test_storage_wrapper(self) -> None:
        devices, commands = parse_broadlink_codes_payload(
            {
                "version": 1,
                "data": {
                    "living_tv": {"power_on": "JgBQ", "hdmi_1": "JgBR"},
                    "soundbar": {"mute": "JgBS"},
                },
            }
        )
        self.assertEqual(devices, ["living_tv", "soundbar"])
        self.assertEqual(commands, ["hdmi_1", "mute", "power_on"])

    def test_inner_mapping(self) -> None:
        devices, commands = parse_broadlink_codes_payload({"tv": {"ok": "xx"}})
        self.assertEqual(devices, ["tv"])
        self.assertEqual(commands, ["ok"])

    def test_invalid(self) -> None:
        self.assertEqual(parse_broadlink_codes_payload(None), ([], []))
        self.assertEqual(parse_broadlink_codes_payload([]), ([], []))


if __name__ == "__main__":
    unittest.main()
