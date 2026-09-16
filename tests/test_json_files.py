"""Guard against empty or invalid translation JSON (breaks the HA config flow)."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

_PKG = Path(__file__).resolve().parents[1] / "custom_components" / "ir_television"


class JsonFileTests(unittest.TestCase):
    def test_all_packaged_json_parses_and_is_nonempty(self) -> None:
        files = sorted(_PKG.rglob("*.json"))
        self.assertTrue(files, f"no json files under {_PKG}")
        required = {
            _PKG / "manifest.json",
            _PKG / "strings.json",
            _PKG / "icons.json",
            _PKG / "translations" / "en.json",
            _PKG / "translations" / "zh-Hans.json",
        }
        missing = [path for path in required if not path.is_file()]
        self.assertEqual(missing, [], f"required json missing: {missing}")

        for path in files:
            raw = path.read_bytes()
            self.assertGreater(
                len(raw.strip()),
                0,
                f"{path.relative_to(_PKG)} is empty — Home Assistant cannot load the config flow",
            )
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as err:
                self.fail(f"{path.relative_to(_PKG)} is not valid JSON: {err}")
            self.assertIsInstance(payload, dict, path.name)

    def test_english_translation_has_config_flow(self) -> None:
        payload = json.loads((_PKG / "translations" / "en.json").read_text(encoding="utf-8"))
        self.assertIn("config", payload)
        self.assertIn("step", payload["config"])
        self.assertIn("user", payload["config"]["step"])

    def test_ir_device_steps_exist_in_all_locales(self) -> None:
        required_config = ("defaults", "defaults_device", "ir_details")
        required_options = ("defaults", "defaults_device", "ir_details")
        for name in ("strings.json", "translations/en.json", "translations/zh-Hans.json"):
            payload = json.loads((_PKG / name).read_text(encoding="utf-8"))
            config_steps = payload["config"]["step"]
            options_steps = payload["options"]["step"]
            for step in required_config:
                self.assertIn(step, config_steps, f"{name} config.{step}")
            for step in required_options:
                self.assertIn(step, options_steps, f"{name} options.{step}")
            self.assertNotIn(
                "default_device",
                config_steps["defaults"].get("data", {}),
                f"{name} defaults should only pick the remote",
            )

    def test_brand_icons_exist(self) -> None:
        brand = _PKG / "brand"
        for name in ("icon.png", "icon@2x.png", "logo.png"):
            path = brand / name
            self.assertTrue(path.is_file(), f"missing {path}")
            self.assertGreater(path.stat().st_size, 1024, f"{name} is too small")
        root_icon = _PKG.parents[1] / "icon.png"
        self.assertTrue(root_icon.is_file(), "missing repo-root icon.png for HACS")
        self.assertGreater(root_icon.stat().st_size, 1024)


if __name__ == "__main__":
    unittest.main()
