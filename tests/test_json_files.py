"""Guard against empty or invalid translation JSON (breaks the HA config flow)."""

from __future__ import annotations

import json
import struct
import unittest
import zlib
from pathlib import Path

_PKG = Path(__file__).resolve().parents[1] / "custom_components" / "ir_television"


def _png_pixel(path: Path, x: int, y: int) -> tuple[int, ...]:
    """Return one RGBA pixel without an image library."""
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise AssertionError(f"{path.name} is not a PNG")
    pos = 8
    width = height = color_type = None
    idat = bytearray()
    while pos + 8 <= len(data):
        length = struct.unpack(">I", data[pos : pos + 4])[0]
        chunk_type = data[pos + 4 : pos + 8]
        chunk = data[pos + 8 : pos + 8 + length]
        pos += 12 + length
        if chunk_type == b"IHDR":
            width, height, _bit_depth, color_type = struct.unpack(">IIBB", chunk[:10])
        elif chunk_type == b"IDAT":
            idat.extend(chunk)
        elif chunk_type == b"IEND":
            break
    if width is None or height is None or color_type not in (2, 6):
        raise AssertionError(f"{path.name} is not an RGB or RGBA PNG")
    channels = 4 if color_type == 6 else 3
    stride = width * channels
    raw = zlib.decompress(bytes(idat))
    rows: list[bytearray] = []
    cursor = 0
    previous = bytearray(stride)
    for _ in range(height):
        filter_type = raw[cursor]
        cursor += 1
        row = bytearray(raw[cursor : cursor + stride])
        cursor += stride
        for index in range(stride):
            left = row[index - channels] if index >= channels else 0
            up = previous[index]
            up_left = previous[index - channels] if index >= channels else 0
            if filter_type == 0:
                predictor = 0
            elif filter_type == 1:
                predictor = left
            elif filter_type == 2:
                predictor = up
            elif filter_type == 3:
                predictor = (left + up) // 2
            elif filter_type == 4:
                estimate = left + up - up_left
                distances = (
                    abs(estimate - left),
                    abs(estimate - up),
                    abs(estimate - up_left),
                )
                predictor = (left, up, up_left)[distances.index(min(distances))]
            else:
                raise AssertionError(f"unsupported PNG filter {filter_type}")
            row[index] = (row[index] + predictor) & 255
        previous = row
        rows.append(row)
    start = x * channels
    pixel = tuple(rows[y][start : start + channels])
    if channels == 3:
        return (*pixel, 255)
    return pixel


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
        for path in (brand / "icon.png", brand / "icon@2x.png", root_icon):
            corner = _png_pixel(path, 0, 0)
            self.assertEqual(
                corner[3],
                0,
                f"{path.name} corner is opaque; the white border should be transparent",
            )


if __name__ == "__main__":
    unittest.main()
