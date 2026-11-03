"""复用课程制作经验后的素材/逐页检查回归；所有写入限于隔离目录。"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "infrastructure/html/tools"
VIEWPORT = TOOLS / "viewport-check/viewport_check.py"
SOURCE = TOOLS / "source-assets/source_assets.py"
KIT = ROOT / "infrastructure/html/runtime-kits/image-viewer-v1"
CONTAINER = ROOT / "infrastructure/html/templates/containers/presentation-deck-v1"


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


assets = module("course_source_assets", SOURCE)
viewport = module("course_viewport", VIEWPORT)


class SourceAssetsTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="course-source-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / "original.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 600"></svg>', encoding="utf-8")
        (self.root / "derived.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" width="600" height="300"></svg>', encoding="utf-8")
        self.specification = {"assets": [{"id": "original", "path": "original.svg", "source_url": "https://example.invalid/diagram"}, {"id": "derived", "path": "derived.svg", "role": "derived", "source": "中性测试标注", "derived_from": "original", "transformation": "添加编号"}]}

    def test_register_dimensions_derivation_and_hash_tampering(self):
        record = assets.register(self.root, self.specification)
        self.assertEqual((record["assets"][0]["width"], record["assets"][0]["height"]), (1200, 600))
        self.assertEqual(assets.validate(self.root, record)["status"], "pass")
        (self.root / "original.svg").write_text("changed", encoding="utf-8")
        self.assertEqual(assets.validate(self.root, record)["status"], "fail")

    def test_reject_escape_duplicate_missing_parent_cycle_and_credential_url(self):
        scenarios = [
            [{"id": "x", "path": "../outside.svg", "source": "test"}],
            [{"id": "x", "path": "original.svg", "source": "test"}, {"id": "x", "path": "derived.svg", "source": "test"}],
            [{"id": "x", "path": "original.svg", "source": "test", "role": "derived", "derived_from": "absent", "transformation": "crop"}],
            [{"id": "x", "path": "original.svg", "source": "test", "role": "derived", "derived_from": "y", "transformation": "crop"}, {"id": "y", "path": "derived.svg", "source": "test", "role": "derived", "derived_from": "x", "transformation": "crop"}],
            [{"id": "x", "path": "original.svg", "source_url": "https://user:secret@example.invalid/"}],
        ]
        for values in scenarios:
            with self.subTest(values=values), self.assertRaises((ValueError, FileNotFoundError)):
                assets.register(self.root, {"assets": values})

    def test_dry_run_apply_plan_and_no_overwrite(self):
        spec_path = self.root / "specification.json"
        spec_path.write_text(json.dumps(self.specification), encoding="utf-8")
        command = [sys.executable, str(SOURCE), "register", "--root", str(self.root), "--input", str(spec_path)]
        preview = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(preview.returncode, 0, preview.stdout + preview.stderr)
        plan = json.loads(preview.stdout)
        self.assertFalse((self.root / "source-assets.json").exists())
        wrong = subprocess.run(command + ["--apply", "--expect-plan-sha256", "wrong"], capture_output=True)
        self.assertNotEqual(wrong.returncode, 0)
        applied = subprocess.run(command + ["--apply", "--expect-plan-sha256", plan["plan_sha256"]], capture_output=True)
        self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 2)


class CourseCheckTest(unittest.TestCase):
    def test_missing_browser_is_not_run_and_external_citation_is_not_runtime(self):
        with tempfile.TemporaryDirectory(prefix="course-unavailable-") as folder:
            path = Path(folder) / "index.html"
            path.write_text('<html><meta name="viewport" content="width=device-width"><body><a href="https://example.invalid/article">来源</a></body></html>', encoding="utf-8")
            self.assertEqual(viewport.static_check(path)["status"], "pass")
            record = viewport.browser_check(path, [("desktop", 1366, 768, "screen")], None, backend="cdp", browser=str(Path(folder) / "missing-browser"))
            self.assertEqual(record["status"], "not-run")

    def test_none_backend_is_honestly_not_run_and_schema_valid(self):
        with tempfile.TemporaryDirectory(prefix="course-check-") as folder:
            path = Path(folder) / "index.html"
            path.write_text('<html><meta name="viewport" content="width=device-width"><body>中性样例</body></html>', encoding="utf-8")
            result = subprocess.run([sys.executable, str(VIEWPORT), "--html", str(path), "--backend", "none"], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(result.returncode, 0, result.stderr)
            record = json.loads(result.stdout)
            self.assertEqual(record["status"], "not-run")
            self.assertEqual(record["static"]["status"], "pass")
            try:
                import jsonschema
            except ImportError:
                return
            schema = json.loads((ROOT / "infrastructure/html/schemas/check-result.schema.json").read_text(encoding="utf-8"))
            jsonschema.validate(record, schema)
            record["html_sha256"] = None
            record["status"] = "pass"
            with self.assertRaises(jsonschema.ValidationError):
                jsonschema.validate(record, schema)

    def test_gallery_outputs_offline_version_comparison(self):
        with tempfile.TemporaryDirectory(prefix="course-gallery-") as folder:
            root = Path(folder)
            image = root / "desktop-p001.png"
            image.write_bytes(b"placeholder")
            record = {"browser": {"viewports": [{"id": "desktop", "page": 1, "status": "pass", "screenshot": str(image)}]}}
            target = root / "comparison.html"
            viewport.write_gallery(target, record, record)
            content = target.read_text(encoding="utf-8")
            self.assertIn("上一版", content)
            self.assertIn("当前版", content)
            self.assertEqual(content.count('src="desktop-p001.png"'), 2)
            self.assertNotIn("https://", content)

    def test_cdp_all_pages_detects_overlap_and_checks_viewer(self):
        from browser_support import find_browser
        if not find_browser():
            self.skipTest("未安装本机 Chromium，浏览器验证需在有浏览器的环境运行")
        with tempfile.TemporaryDirectory(prefix="course-browser-") as folder:
            root = Path(folder)
            for name in ("deck.js",):
                shutil.copy2(CONTAINER / name, root / name)
            shutil.copy2(KIT / "runtime.js", root / "viewer.js")
            shutil.copy2(KIT / "runtime.css", root / "viewer.css")
            (root / "image.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="600"><rect width="1200" height="600" fill="navy"/></svg>', encoding="utf-8")
            container = (CONTAINER / "index.html").read_text(encoding="utf-8")
            container = container.replace('<link rel="stylesheet" href="styles.css" />', '<link rel="stylesheet" href="viewer.css" /><style>[hidden]{display:none!important} [data-deck-controls]{position:fixed;bottom:0;left:0;right:0;height:60px;background:white} [data-deck-page]{min-height:300px} .blocked{position:fixed;bottom:10px}</style>').replace('<link rel="stylesheet" href="deck.css" />', '')
            container = container.replace('<!-- SUANHAI_DECK_PAGES -->', '<section id="page-one" data-deck-page data-speaker-note="中性备注"><h1>图解</h1><a href="image.svg" data-source-image="image.svg" data-source-caption="中性结构图">查看完整原图</a></section><section id="page-two" data-deck-page><h1>第二页</h1><p class="blocked">故意被导航遮挡</p></section>')
            container = container.replace('<script src="deck.js"></script>', '<script src="deck.js"></script><script src="viewer.js"></script>')
            path = root / "index.html"
            path.write_text(container, encoding="utf-8")
            report = viewport.browser_check(path, [("desktop", 1366, 768, "screen"), ("phone", 390, 844, "screen")], root / "shots", backend="cdp", all_pages=True, interactions=True)
            if report["status"] == "not-run":
                self.fail(f"本机浏览器存在但无法执行：{report}")
            self.assertEqual(len(report["viewports"]), 4, report)
            self.assertEqual(report["status"], "fail", report)
            self.assertTrue(report["viewports"][1]["metrics"]["navigationOverlap"], report)
            for interaction in report["interactions"]:
                self.assertEqual(interaction["status"], "pass", interaction)
            self.assertEqual(len(list((root / "shots").glob("*.png"))), 4)
            # 同一成品移除故意缺陷后必须通过，证明检查不是永远报错的测试替身。
            path.write_text(container.replace('class="blocked"', 'class="readable"'), encoding="utf-8")
            passing = viewport.browser_check(path, [("desktop", 1366, 768, "screen"), ("phone", 390, 844, "screen")], None, backend="cdp", all_pages=True, interactions=True)
            self.assertEqual(passing["status"], "pass", passing)


if __name__ == "__main__":
    unittest.main()
