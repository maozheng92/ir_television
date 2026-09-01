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


if __name__ == "__main__":
    unittest.main()
