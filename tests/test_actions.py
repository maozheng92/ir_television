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
FEATURE_BROWSE_MEDIA = const.FEATURE_BROWSE_MEDIA
FEATURE_NEXT_TRACK = const.FEATURE_NEXT_TRACK
FEATURE_PAUSE = const.FEATURE_PAUSE
FEATURE_PLAY = const.FEATURE_PLAY
FEATURE_PLAY_MEDIA = const.FEATURE_PLAY_MEDIA
FEATURE_PREVIOUS_TRACK = const.FEATURE_PREVIOUS_TRACK
FEATURE_SELECT_SOURCE = const.FEATURE_SELECT_SOURCE
FEATURE_STOP = const.FEATURE_STOP
FEATURE_TURN_OFF = const.FEATURE_TURN_OFF
FEATURE_TURN_ON = const.FEATURE_TURN_ON
FEATURE_VOLUME_MUTE = const.FEATURE_VOLUME_MUTE
FEATURE_VOLUME_SET = const.FEATURE_VOLUME_SET
FEATURE_VOLUME_STEP = const.FEATURE_VOLUME_STEP
HOMEKIT_TV_FEATURES = const.HOMEKIT_TV_FEATURES
INTENT_PAUSE = const.INTENT_PAUSE
INTENT_PLAY = const.INTENT_PLAY
INTENT_PLAY_PAUSE = const.INTENT_PLAY_PAUSE
INTENT_TOGGLE = const.INTENT_TOGGLE
INTENT_TURN_OFF = const.INTENT_TURN_OFF
INTENT_TURN_ON = const.INTENT_TURN_ON
DEFAULT_SOURCE_NAME = const.DEFAULT_SOURCE_NAME

action_is_valid = actions.action_is_valid
build_button_service_data = actions.build_button_service_data
build_remote_service_data = actions.build_remote_service_data
build_source_list = actions.build_source_list
compute_supported_features = actions.compute_supported_features
current_source_name = actions.current_source_name
collect_homekit_ports = actions.collect_homekit_ports
copy_config = actions.copy_config
find_source = actions.find_source
has_useful_config = actions.has_useful_config
homekit_accessory_entity_ids = actions.homekit_accessory_entity_ids
next_homekit_port = actions.next_homekit_port
normalize_power_sensor = actions.normalize_power_sensor
parse_action_input = actions.parse_action_input
parse_broadlink_codes_payload = actions.parse_broadlink_codes_payload
power_is_on_from_sensor = actions.power_is_on_from_sensor
resolve_command_key = actions.resolve_command_key
resolve_homekit_remote_key = actions.resolve_homekit_remote_key
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
    def test_always_matches_sony_bravia_homekit_bits(self) -> None:
        """Sparse features make iOS skip the TV; braviatv always advertises 155581."""
        bits = compute_supported_features({}, [])
        self.assertEqual(bits, HOMEKIT_TV_FEATURES)
        self.assertEqual(bits, 155581)
        self.assertTrue(bits & FEATURE_TURN_ON)
        self.assertTrue(bits & FEATURE_TURN_OFF)
        self.assertTrue(bits & FEATURE_VOLUME_STEP)
        self.assertTrue(bits & FEATURE_VOLUME_MUTE)
        self.assertTrue(bits & FEATURE_VOLUME_SET)
        self.assertTrue(bits & FEATURE_SELECT_SOURCE)
        self.assertTrue(bits & FEATURE_PLAY)
        self.assertTrue(bits & FEATURE_PAUSE)
        self.assertTrue(bits & FEATURE_STOP)
        self.assertTrue(bits & FEATURE_NEXT_TRACK)
        self.assertTrue(bits & FEATURE_PREVIOUS_TRACK)
        self.assertTrue(bits & FEATURE_PLAY_MEDIA)
        self.assertTrue(bits & FEATURE_BROWSE_MEDIA)

    def test_mapped_commands_do_not_change_bits(self) -> None:
        commands = {"power_toggle": _ir("power"), "play": _ir("play")}
        self.assertEqual(compute_supported_features(commands, []), HOMEKIT_TV_FEATURES)

    def test_on_off_separate_still_full_mask(self) -> None:
        commands = {"turn_on": _ir("on"), "turn_off": _ir("off")}
        self.assertEqual(compute_supported_features(commands, []), HOMEKIT_TV_FEATURES)

    def test_volume_and_mute_still_full_mask(self) -> None:
        commands = {
            "volume_up": _ir("volup"),
            "volume_mute": _btn("button.mute"),
        }
        self.assertEqual(compute_supported_features(commands, []), HOMEKIT_TV_FEATURES)

    def test_play_pause_single_key_still_full_mask(self) -> None:
        self.assertEqual(
            compute_supported_features({"play_pause": _ir("pp")}, []),
            HOMEKIT_TV_FEATURES,
        )

    def test_channels_and_sources_still_full_mask(self) -> None:
        commands = {"next_track": _ir("ch+"), "previous_track": _ir("ch-")}
        sources = [{"name": "HDMI 1", "action": _ir("hdmi1")}]
        self.assertEqual(
            compute_supported_features(commands, sources), HOMEKIT_TV_FEATURES
        )

    def test_source_list_ignores_blank(self) -> None:
        self.assertEqual(
            build_source_list([{"name": "  HDMI 1 "}, {"name": "  "}, "x"]),
            ["HDMI 1"],
        )

    def test_default_source_when_none_configured(self) -> None:
        self.assertEqual(build_source_list([]), [DEFAULT_SOURCE_NAME])
        self.assertEqual(build_source_list(None), [DEFAULT_SOURCE_NAME])
        self.assertEqual(build_source_list([{"name": "  "}]), [DEFAULT_SOURCE_NAME])

    def test_current_source_always_in_list(self) -> None:
        sources = [{"name": "HDMI1"}, {"name": "HDMI2"}]
        self.assertEqual(current_source_name("HDMI2", sources), "HDMI2")
        self.assertEqual(current_source_name("hdmi1", sources), "HDMI1")
        self.assertEqual(current_source_name(None, sources), "HDMI1")
        self.assertEqual(current_source_name("missing", sources), "HDMI1")


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


class HomeKitRemoteKeyTests(unittest.TestCase):
    def _nav(self) -> dict:
        return {
            "up": _ir("up"),
            "down": _ir("down"),
            "left": _ir("left"),
            "right": _ir("right"),
            "ok": _ir("ok"),
            "back": _ir("back"),
            "home": _ir("home"),
            "info": _ir("info"),
            "play_pause": _ir("pp"),
            "next_track": _ir("ch+"),
            "previous_track": _ir("ch-"),
        }

    def test_dpad_and_select(self) -> None:
        commands = self._nav()
        self.assertEqual(resolve_homekit_remote_key(commands, "arrow_up"), "up")
        self.assertEqual(resolve_homekit_remote_key(commands, "arrow_down"), "down")
        self.assertEqual(resolve_homekit_remote_key(commands, "arrow_left"), "left")
        self.assertEqual(resolve_homekit_remote_key(commands, "arrow_right"), "right")
        self.assertEqual(resolve_homekit_remote_key(commands, "select"), "ok")
        self.assertEqual(resolve_homekit_remote_key(commands, "back"), "back")
        self.assertEqual(resolve_homekit_remote_key(commands, "information"), "info")
        self.assertEqual(resolve_homekit_remote_key(commands, "next_track"), "next_track")
        self.assertEqual(
            resolve_homekit_remote_key(commands, "previous_track"), "previous_track"
        )

    def test_key_name_is_trimmed_and_case_insensitive(self) -> None:
        commands = {"up": _ir("up")}
        self.assertEqual(resolve_homekit_remote_key(commands, "  ARROW_UP  "), "up")

    def test_play_pause_falls_back_to_play_then_pause(self) -> None:
        self.assertEqual(
            resolve_homekit_remote_key({"play_pause": _ir("pp")}, "play_pause"),
            "play_pause",
        )
        self.assertEqual(
            resolve_homekit_remote_key({"play": _ir("play")}, "play_pause"),
            "play",
        )
        self.assertEqual(
            resolve_homekit_remote_key({"pause": _ir("pause")}, "play_pause"),
            "pause",
        )
        self.assertIsNone(resolve_homekit_remote_key({}, "play_pause"))

    def test_exit_and_home_fall_back_to_back(self) -> None:
        with_home = {"home": _ir("home"), "back": _ir("back")}
        self.assertEqual(resolve_homekit_remote_key(with_home, "exit"), "home")
        self.assertEqual(resolve_homekit_remote_key(with_home, "home"), "home")
        back_only = {"back": _ir("back")}
        self.assertEqual(resolve_homekit_remote_key(back_only, "exit"), "back")
        self.assertEqual(resolve_homekit_remote_key(back_only, "home"), "back")
        self.assertIsNone(resolve_homekit_remote_key({}, "exit"))

    def test_rewind_and_fast_forward(self) -> None:
        both = {"next_track": _ir("ch+"), "previous_track": _ir("ch-")}
        self.assertEqual(resolve_homekit_remote_key(both, "rewind"), "previous_track")
        self.assertEqual(resolve_homekit_remote_key(both, "fast_forward"), "next_track")
        arrows = {"left": _ir("left"), "right": _ir("right")}
        self.assertEqual(resolve_homekit_remote_key(arrows, "rewind"), "left")
        self.assertEqual(resolve_homekit_remote_key(arrows, "fast_forward"), "right")

    def test_unmapped_or_empty_is_none(self) -> None:
        commands = self._nav()
        self.assertIsNone(resolve_homekit_remote_key(commands, "unknown"))
        self.assertIsNone(resolve_homekit_remote_key(commands, ""))
        self.assertIsNone(resolve_homekit_remote_key(commands, None))
        self.assertIsNone(resolve_homekit_remote_key({}, "arrow_up"))
        self.assertIsNone(resolve_homekit_remote_key({"up": {}}, "arrow_up"))

    def test_stored_command_key_is_accepted(self) -> None:
        commands = {"up": _ir("up"), "ok": _ir("ok")}
        self.assertEqual(resolve_homekit_remote_key(commands, "up"), "up")
        self.assertEqual(resolve_homekit_remote_key(commands, "OK"), "ok")


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


class HomeKitIidDecodeTests(unittest.TestCase):
    def test_splits_iid_keys(self) -> None:
        self.assertEqual(actions.split_homekit_iid_key("D8___"), ("D8", "", ""))
        self.assertEqual(actions.split_homekit_iid_key("D8__E8_"), ("D8", "", "E8"))
        self.assertEqual(
            actions.split_homekit_iid_key("D9_HDMI1__"), ("D9", "HDMI1", "")
        )
        self.assertEqual(
            actions.split_homekit_iid_key("D9_HDMI1_E3_"), ("D9", "HDMI1", "E3")
        )
        self.assertEqual(actions.split_homekit_iid_key("113__11A_"), ("113", "", "11A"))

    def test_user_tcl_dump_is_accessory_mode_television(self) -> None:
        """The dump from HA storage is already a complete TelevisionMediaPlayer."""
        allocations = {
            "1": {
                "3E__14_": 2,
                "3E__20_": 3,
                "3E__21_": 4,
                "3E__23_": 5,
                "3E__30_": 6,
                "3E__52_": 7,
                "A2___": 8,
                "A2__37_": 9,
                "D8___": 10,
                "D8__B0_": 11,
                "D8__E7_": 12,
                "D8__E3_": 13,
                "D8__E8_": 14,
                "D8__E1_": 15,
                "D9_HDMI1__": 16,
                "D9_HDMI2__": 23,
                "D9_HDMI3__": 30,
                "D9_HDMI4__": 37,
                "113___": 44,
                "113__11A_": 45,
                "113__E9_": 48,
                "113__EA_": 49,
                "113__119_": 50,
            }
        }
        decoded = actions.decode_homekit_iid_allocations(allocations)
        self.assertTrue(decoded["looks_like_accessory_mode_tv"])
        acc = decoded["accessories"][0]
        self.assertTrue(acc["has_television"])
        self.assertTrue(acc["has_remote_key"])
        self.assertTrue(acc["has_sleep_discovery"])
        self.assertTrue(acc["has_speaker"])
        self.assertTrue(acc["ios_remote_ready"])
        self.assertEqual(acc["input_sources"], ["HDMI1", "HDMI2", "HDMI3", "HDMI4"])

    def test_bridge_aid1_without_television_is_not_ready(self) -> None:
        allocations = {
            "1": {"3E__14_": 2, "A2___": 3},
            "2": {"D8___": 10, "D8__E8_": 14, "D9_HDMI1__": 16},
        }
        decoded = actions.decode_homekit_iid_allocations(allocations)
        self.assertFalse(decoded["looks_like_accessory_mode_tv"])
        self.assertTrue(decoded["accessories"][1]["ios_remote_ready"])

    def test_homekit_entries_for_entity(self) -> None:
        entries = [
            (
                {
                    "mode": "accessory",
                    "filter": {"include_entities": ["media_player.tcl"]},
                },
                {},
                "entry_tv",
            ),
            (
                {"mode": "accessory", "filter": {"include_entities": ["remote.tcl"]}},
                {},
                "entry_remote",
            ),
            ({"mode": "bridge", "port": 21063}, {}, "entry_bridge"),
        ]
        self.assertEqual(
            actions.homekit_entries_for_entity(entries, "media_player.tcl"),
            ["entry_tv"],
        )
        self.assertEqual(
            actions.homekit_entries_for_entity(entries, "remote.tcl"),
            ["entry_remote"],
        )

    def test_unpaired_television_mdns_is_not_listed(self) -> None:
        decoded = actions.decode_hap_mdns_txt(
            {
                "c#": "2",
                "ci": "31",
                "ff": "0",
                "id": "8E:CB:0F:6D:29:D3",
                "md": "TCL",
                "pv": "1.1",
                "s#": "1",
                "sf": "1",
            }
        )
        self.assertTrue(decoded["is_television"])
        self.assertTrue(decoded["not_paired"])
        self.assertFalse(decoded["ios_remote_listed"])

    def test_paired_television_mdns_is_ready_for_remote(self) -> None:
        decoded = actions.decode_hap_mdns_txt(
            {
                "c#": "2",
                "ci": "31",
                "ff": "0",
                "id": "8E:CB:0F:6D:29:D3",
                "md": "TCL",
                "pv": "1.1",
                "s#": "1",
                "sf": "0",
            }
        )
        self.assertTrue(decoded["is_television"])
        self.assertEqual(decoded["category_name"], "television")
        self.assertFalse(decoded["is_apple_tv"])
        self.assertTrue(decoded["paired"])
        self.assertTrue(decoded["ios_remote_listed"])
        self.assertEqual(decoded["accessory_id"], "8E:CB:0F:6D:29:D3")

    def test_ci_24_is_apple_tv_not_television(self) -> None:
        decoded = actions.decode_hap_mdns_txt({"ci": "24", "sf": "0"})
        self.assertEqual(decoded["category"], 24)
        self.assertEqual(decoded["category_name"], "apple_tv")
        self.assertTrue(decoded["is_apple_tv"])
        self.assertFalse(decoded["is_television"])
        self.assertFalse(decoded["ios_remote_listed"])


class HomeKitAccessoryHelperTests(unittest.TestCase):
    def test_detects_accessory_entity(self) -> None:
        entries = [
            (
                {
                    "mode": "accessory",
                    "port": 21064,
                    "filter": {"include_entities": ["media_player.living_tv"]},
                },
                {},
            ),
            ({"mode": "bridge", "port": 21063}, {}),
        ]
        self.assertEqual(
            homekit_accessory_entity_ids(entries), {"media_player.living_tv"}
        )

    def test_reads_mode_from_options(self) -> None:
        entries = [
            (
                {"port": 21063},
                {
                    "mode": "accessory",
                    "filter": {"include_entities": ["media_player.sony"]},
                },
            )
        ]
        self.assertEqual(
            homekit_accessory_entity_ids(entries), {"media_player.sony"}
        )

    def test_next_port_skips_used(self) -> None:
        self.assertEqual(next_homekit_port({21064, 21065}), 21066)
        self.assertEqual(
            collect_homekit_ports(
                [
                    ({"port": 21063}, {}),
                    ({}, {"port": "21064"}),
                ]
            ),
            {21063, 21064},
        )


if __name__ == "__main__":
    unittest.main()
