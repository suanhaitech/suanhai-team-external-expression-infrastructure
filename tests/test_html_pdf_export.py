"""HTML PDF 导出工具的安全边界和浏览器集成测试。"""

from __future__ import annotations

import json
import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest

_MODULE_PATH = Path(__file__).resolve().parents[1] / "tools/html-pdf-export/export_pdf.py"
_SPEC = importlib.util.spec_from_file_location("html_pdf_export", _MODULE_PATH)
assert _SPEC and _SPEC.loader
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
ExportError = _MODULE.ExportError
run = _MODULE.run


class HtmlPdfExportTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="html-pdf-export-")
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        (self.root / "assets").mkdir()
        (self.root / "assets" / "site.css").write_text(
            "@page { size: A4; margin: 12mm; } body { font-family: sans-serif; }",
            encoding="utf-8",
        )
        (self.root / "index.html").write_text(
            "<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'>"
            "<link rel='stylesheet' href='assets/site.css'></head>"
            "<body><h1>PDF export fixture</h1><p>offline content</p></body></html>",
            encoding="utf-8",
        )

    def test_missing_browser_is_explicit_not_run_and_records_metadata(self) -> None:
        result = run(
            type("Args", (), {
                "root": str(self.root), "input": "index.html", "output": "report.pdf",
                "browser": str(self.root / "missing-browser"), "paper": "a4", "landscape": False,
                "margin_mm": 12.0, "scale": 1.0, "no_background": False,
                "prefer_css_page_size": False, "metadata": "pdf-export.json", "timeout": 5.0,
            })()
        )
        self.assertEqual(result["status"], "not-run")
        self.assertFalse((self.root / "report.pdf").exists())
        saved = json.loads((self.root / "pdf-export.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["tool"], "html.pdf-export")
        self.assertIn("未检测到", saved["reason"])

    def test_rejects_path_escape_and_existing_output(self) -> None:
        args = type("Args", (), {
            "root": str(self.root), "input": "../index.html", "output": "report.pdf",
            "browser": str(self.root / "missing-browser"), "paper": "a4", "landscape": False,
            "margin_mm": 12.0, "scale": 1.0, "no_background": False,
            "prefer_css_page_size": False, "metadata": "pdf-export.json", "timeout": 5.0,
        })()
        with self.assertRaises(ExportError):
            run(args)
        args.input = "index.html"
        (self.root / "report.pdf").write_bytes(b"existing")
        with self.assertRaises(ExportError):
            run(args)

    def test_rejects_invalid_print_settings_and_metadata_collision(self) -> None:
        base = {
            "root": str(self.root), "input": "index.html", "output": "report.pdf",
            "browser": str(self.root / "missing-browser"), "paper": "a4", "landscape": False,
            "margin_mm": 12.0, "scale": 1.0, "no_background": False,
            "prefer_css_page_size": False, "metadata": "pdf-export.json", "timeout": 5.0,
        }
        for field, value in (("margin_mm", -1.0), ("scale", 0.01), ("timeout", 0.5)):
            args = type("Args", (), {**base, field: value})()
            with self.assertRaises(ExportError):
                run(args)
        args = type("Args", (), {**base, "output": "same.json", "metadata": "same.json"})()
        with self.assertRaises(ExportError):
            run(args)

    def test_browser_export_creates_pdf_when_edge_or_chrome_is_available(self) -> None:
        browser = (
            shutil.which("msedge")
            or shutil.which("chrome")
            or next(
                (
                    str(path)
                    for path in (
                        Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
                        Path("C:/Program Files/Microsoft/Edge/Application/msedge.exe"),
                    )
                    if path.is_file()
                ),
                None,
            )
        )
        if not browser:
            self.skipTest("测试机没有可用的 Chrome/Edge")
        args = type("Args", (), {
            "root": str(self.root), "input": "index.html", "output": "report.pdf",
            "browser": browser, "paper": "a4", "landscape": False,
            "margin_mm": 12.0, "scale": 1.0, "no_background": False,
            "prefer_css_page_size": False, "metadata": "pdf-export.json", "timeout": 30.0,
        })()
        result = run(args)
        self.assertEqual(result["status"], "completed")
        pdf = self.root / "report.pdf"
        self.assertTrue(pdf.read_bytes().startswith(b"%PDF-"))
        self.assertEqual(result["sha256"], __import__("hashlib").sha256(pdf.read_bytes()).hexdigest())
        self.assertEqual(json.loads((self.root / "pdf-export.json").read_text(encoding="utf-8"))["output"], "report.pdf")


if __name__ == "__main__":
    unittest.main()
