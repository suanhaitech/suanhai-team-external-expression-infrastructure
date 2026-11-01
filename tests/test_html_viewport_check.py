"""响应式布局包和 viewport 检查器的离线回归测试。"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/html-viewport-check/viewport_check.py"
LAYOUT = ROOT / "formats/web/html/layouts/responsive-v1"


class HtmlViewportCheckTest(unittest.TestCase):
    def test_layout_package_has_aspect_ratio_and_print_contract(self):
        package = (LAYOUT / "package.yml").read_text(encoding="utf-8")
        catalog = (LAYOUT / "index.yml").read_text(encoding="utf-8")
        css = (LAYOUT / "media.css").read_text(encoding="utf-8")
        self.assertIn("id: html.responsive-layout-v1", package)
        self.assertIn("print-a4", catalog)
        self.assertIn("max-aspect-ratio", css)
        self.assertIn("min-aspect-ratio", css)
        self.assertIn("@media print", css)

    def test_static_check_passes_without_browser(self):
        with tempfile.TemporaryDirectory(prefix="viewport-check-") as directory:
            root = Path(directory)
            (root / "styles.css").write_text("body { color: black; }\n", encoding="utf-8")
            html = root / "index.html"
            html.write_text('<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="stylesheet" href="styles.css"></head><body>ok</body></html>', encoding="utf-8")
            result = subprocess.run([sys.executable, str(TOOL), "--html", str(html)], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["static"]["status"], "pass")
            self.assertEqual(payload["tool"], "html.viewport-check")
            self.assertIn(payload["browser"]["status"], {"pass", "not-run"})
            self.assertEqual(len(payload["viewports"]), 5)

    def test_static_check_rejects_remote_and_missing_resources(self):
        with tempfile.TemporaryDirectory(prefix="viewport-check-") as directory:
            html = Path(directory) / "index.html"
            html.write_text('<html><head><link rel="stylesheet" href="missing.css"></head><body><img src="https://example.com/a.png"></body></html>', encoding="utf-8")
            result = subprocess.run([sys.executable, str(TOOL), "--html", str(html)], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["static"]["status"], "fail")
            self.assertGreaterEqual(len(payload["static"]["errors"]), 2)

    def test_custom_viewport_parser_and_output(self):
        with tempfile.TemporaryDirectory(prefix="viewport-check-") as directory:
            root = Path(directory)
            html = root / "index.html"
            html.write_text('<html><head><meta name="viewport" content="width=device-width"></head><body></body></html>', encoding="utf-8")
            output = root / "result.json"
            result = subprocess.run([sys.executable, str(TOOL), "--html", str(html), "--viewport", "phone=390x844", "--output", str(output)], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["viewports"], [{"id": "phone", "width": 390, "height": 844, "media": "screen"}])

    def test_cli_json_survives_non_utf8_windows_console(self):
        with tempfile.TemporaryDirectory(prefix="viewport-check-") as directory:
            root = Path(directory)
            html = root / "index.html"
            html.write_text('<html><head><meta name="viewport" content="width=device-width"></head><body></body></html>', encoding="utf-8")
            environment = {**os.environ, "PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"}
            result = subprocess.run(
                [sys.executable, str(TOOL), "--html", str(html), "--viewport", "phone=390x844"],
                capture_output=True,
                env=environment,
            )
            self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", errors="replace"))
            payload = json.loads(result.stdout.decode("utf-8"))
            self.assertEqual(payload["tool"], "html.viewport-check")


if __name__ == "__main__":
    unittest.main()
