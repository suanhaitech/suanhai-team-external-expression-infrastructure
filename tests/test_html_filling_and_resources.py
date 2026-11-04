"""验证填写协议及实际引用资源；仅使用临时目录内的合成内容。"""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("filling_viewport", ROOT / "infrastructure/html/tools/viewport-check/viewport_check.py")
viewport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(viewport)


class FillingAndResourcesTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix="html-filling-synthetic-")
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.html = self.root / "index.html"

    def page(self, body="", head=""):
        self.html.write_text('<html><head><meta name="viewport" content="width=device-width">' + head + '</head><body>' + body + '</body></html>', encoding="utf-8")

    def test_reachable_css_cycle_ignores_unused_compatibility_file(self):
        self.page(head='<link rel="stylesheet" href="main.css">')
        (self.root / "main.css").write_text('@import "nested.css"; body{background:url("image.svg#icon")}', encoding="utf-8")
        (self.root / "nested.css").write_text('@import url("main.css");', encoding="utf-8")
        (self.root / "image.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")
        (self.root / "unused.css").write_text('body{background:url(data:image/svg+xml,unused)}', encoding="utf-8")
        report = viewport.static_check(self.html)
        self.assertEqual(report["status"], "pass", report)
        self.assertEqual({item["path"] for item in report["resources"]}, {"index.html", "main.css", "nested.css", "image.svg"})
        before = report["resources_sha256"]
        (self.root / "nested.css").write_text('body{color:navy}', encoding="utf-8")
        self.assertNotEqual(before, viewport.static_check(self.html)["resources_sha256"])

    def test_inline_css_remote_import_and_encoded_escape_are_rejected(self):
        self.page(head='<style>@import "https://example.invalid/style.css";</style>', body='<p style="background:url(%2e%2e/outside.svg)">合成</p>')
        result = viewport.static_check(self.html)
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("越出" in error for error in result["errors"]))
        self.assertTrue(any("远程" in error for error in result["errors"]))

    def test_missing_nested_css_resource_fails(self):
        self.page(head='<link rel="stylesheet" href="a.css">')
        (self.root / "a.css").write_text('@import "missing.css";', encoding="utf-8")
        self.assertEqual(viewport.static_check(self.html)["status"], "fail")

    def test_template_allows_content_slots_but_never_invalid_state(self):
        self.page('<article data-component="evidence.claim" data-state="unverified"><span>待核验</span><p>[判断]</p></article>')
        self.assertEqual(viewport.static_check(self.html, "template")["status"], "pass")
        self.assertEqual(viewport.static_check(self.html, "report")["status"], "fail")
        self.page('<article data-component="evidence.claim" data-state="[confirmed|candidate]">待核验</article>')
        self.assertEqual(viewport.static_check(self.html, "template")["status"], "fail")
        self.page('<p data-author-hint>复制这个单元</p>')
        self.assertEqual(viewport.static_check(self.html, "report")["status"], "fail")

    def test_public_component_can_be_filled_repeated_and_change_state(self):
        fragment = (ROOT / "infrastructure/html/components/core-v1/semantic/evidence/claim/template.html").read_text(encoding="utf-8")
        fragment = fragment.replace("[可复查的判断]", "合成验证：两个中性模块连通").replace("[来源 ID、限制或核对人]", "synthetic-only，非项目事实")
        confirmed = fragment.replace('data-state="unverified"', 'data-state="confirmed"').replace("待核验", "已核验")
        for body in (fragment, fragment + confirmed, confirmed):
            self.page(body)
            self.assertEqual(viewport.static_check(self.html, "report")["status"], "pass")

    def test_stock_long_page_passes_without_removing_compatibility_assets(self):
        shutil.copytree(ROOT / "infrastructure/html/templates/presets/project-report-v1", self.root, dirs_exist_ok=True)
        report = viewport.static_check(self.html)
        self.assertEqual(report["status"], "pass", report)
        self.assertTrue((self.root / "styles.css").exists())
        self.assertNotIn("styles.css", {item["path"] for item in report["resources"]})

    def test_cdp_full_document_and_missing_long_page_anchor(self):
        from browser_support import find_browser
        if not find_browser():
            self.skipTest("本机无 Chromium")
        self.page('<nav class="report-nav"><a href="#missing">目标</a></nav><p style="height:1800px">合成内容</p>')
        result = viewport.browser_check(self.html, [("phone", 390, 844, "screen")], self.root / "shots", backend="cdp", interactions=True, full_page=True, sandbox=not sys.platform.startswith("linux"))
        self.assertEqual(result["status"], "fail", result)
        anchors = next(item for item in result["interactions"] if item["id"] == "report-anchors")
        self.assertEqual(anchors["missing"], ["missing"])
        # PNG 的 IHDR 高度直接验证实际截图字节，避免只检查请求参数。
        shot = self.root / "shots/phone-p001.png"
        self.assertGreater(int.from_bytes(shot.read_bytes()[20:24], "big"), 844)


if __name__ == "__main__":
    unittest.main()
