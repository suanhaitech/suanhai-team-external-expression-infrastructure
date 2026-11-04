"""复用课程制作经验后的素材/逐页检查回归；所有写入限于隔离目录。"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

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
import browser_support


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

    def test_root_alias_and_relative_root_preserve_paths_and_boundary(self):
        # 含 .. 的合法根别名在各平台都会复现“已resolve目标/未resolve根”的错误；
        # 同时验证公开Python入口接受相对根，不依赖CLI先替它规范化。
        alias = self.root / ".." / self.root.name
        record = assets.register(alias, self.specification)
        self.assertEqual([item["path"] for item in record["assets"]], ["original.svg", "derived.svg"])
        self.assertEqual(assets.validate(alias, record)["status"], "pass")
        self.assertEqual(assets.local_file(alias, "original.svg"), (self.root / "original.svg").resolve())
        from contextlib import chdir
        with chdir(self.root.parent):
            relative = Path(self.root.name)
            self.assertEqual(assets.register(relative, self.specification), record)
            self.assertEqual(assets.validate(relative, record)["status"], "pass")
            self.assertEqual(assets.local_file(relative, "original.svg"), (self.root / "original.svg").resolve())
            with self.assertRaises(ValueError):
                assets.local_file(relative, "../outside.svg")

    @unittest.skipUnless(os.name == "nt", "Windows 8.3 路径别名专项")
    def test_windows_short_root_resolves_to_same_registered_assets(self):
        import ctypes
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        get_short_path = kernel32.GetShortPathNameW
        get_short_path.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32]
        get_short_path.restype = ctypes.c_uint32
        buffer = ctypes.create_unicode_buffer(32768)
        length = get_short_path(str(self.root.resolve()), buffer, len(buffer))
        if not length or length >= len(buffer):
            self.skipTest("测试卷未提供可用8.3短路径")
        short = Path(buffer.value)
        if os.path.normcase(str(short)) == os.path.normcase(str(self.root.resolve())):
            self.skipTest("测试卷未生成不同形式的8.3短路径")
        record = assets.register(short, self.specification)
        self.assertEqual(record, assets.register(self.root.resolve(), self.specification))
        self.assertEqual(assets.validate(short, record)["status"], "pass")
        self.assertEqual(assets.local_file(short, "original.svg"), (self.root / "original.svg").resolve())

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
    def test_browser_sandbox_default_and_explicit_ci_policy_are_separate(self):
        with mock.patch.object(browser_support, "find_browser", return_value=sys.executable):
            for sandbox in (True, False):
                with mock.patch.object(browser_support.subprocess, "Popen", side_effect=OSError("合成启动失败")) as launch:
                    with self.assertRaises(browser_support.BrowserUnavailable):
                        with browser_support.ChromiumSession(sandbox=sandbox):
                            pass
                    self.assertEqual("--no-sandbox" in launch.call_args.args[0], not sandbox)

    def test_devtools_loopback_does_not_use_environment_proxy(self):
        with tempfile.TemporaryDirectory(prefix="devtools-proxy-test-") as folder:
            root = Path(folder)
            (root / "version.json").write_text('{"Browser":"synthetic"}', encoding="utf-8")
            with browser_support.LocalArtifactServer(root) as origin:
                port = int(origin.rsplit(":", 1)[1])
                environment = {"http_proxy": "http://127.0.0.1:1", "HTTP_PROXY": "http://127.0.0.1:1", "all_proxy": "http://127.0.0.1:1", "ALL_PROXY": "http://127.0.0.1:1", "no_proxy": "", "NO_PROXY": ""}
                with mock.patch.dict(os.environ, environment):
                    self.assertEqual(browser_support._local_json(port, "/version.json"), {"Browser": "synthetic"})

    def test_devtools_startup_retries_temporary_http_not_ready(self):
        if not browser_support.find_browser():
            self.skipTest("未安装本机 Chromium；启动重试浏览器验证 not-run")
        original = browser_support._local_json
        attempts = []
        def delayed_ready(*args, **kwargs):
            attempts.append(args)
            if len(attempts) == 1:
                raise TimeoutError("合成端口文件先就绪、HTTP暂未就绪")
            return original(*args, **kwargs)
        with mock.patch.object(browser_support, "_local_json", side_effect=delayed_ready):
            with browser_support.ChromiumSession(sandbox=not sys.platform.startswith("linux")) as session:
                self.assertEqual(session.evaluate("1 + 1"), 2)
        self.assertGreaterEqual(len(attempts), 3)

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

    def test_full_page_plan_detects_manual_page_omission(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            html = root / "index.html"
            html.write_text('<html><head><meta name="viewport" content="width=device-width"></head><body><section id="page-one" data-page-id="page-one" data-deck-page>正文</section></body></html>', encoding="utf-8")
            (root / "page-plan.json").write_text(json.dumps({"schema_version": 1, "pages": [{"id": "page-one"}, {"id": "page-two"}]}), encoding="utf-8")
            self.assertEqual(viewport.static_check(html)["status"], "fail")
            (root / "page-plan.json").write_text(json.dumps({"schema_version": 1, "pages": [{"id": "page-one"}]}), encoding="utf-8")
            self.assertEqual(viewport.static_check(html)["status"], "pass")

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

    @unittest.skipUnless(os.name == "nt", "Windows 8.3 路径兼容回归")
    def test_gallery_short_directory_alias_keeps_local_image_url(self):
        import ctypes
        with tempfile.TemporaryDirectory(prefix="course-gallery-long-directory-") as folder:
            root = Path(folder).resolve()
            short_path = ctypes.windll.kernel32.GetShortPathNameW
            short_path.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32]
            short_path.restype = ctypes.c_uint32
            buffer = ctypes.create_unicode_buffer(32768)
            size = short_path(str(root), buffer, len(buffer))
            self.assertTrue(0 < size < len(buffer), "无法读取临时目录的短路径")
            alias = Path(buffer.value)
            if alias == root:
                self.skipTest("此文件系统未提供 8.3 别名")
            image = root / "desktop-p001.png"
            image.write_bytes(b"placeholder")
            record = {"browser": {"viewports": [{"id": "desktop", "page": 1, "status": "pass", "screenshot": str(image)}]}}
            target = alias / "comparison.html"
            viewport.write_gallery(target, record, record)
            content = target.read_text(encoding="utf-8")
            self.assertEqual(content.count('src="desktop-p001.png"'), 2)

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
            container = container.replace('<link rel="stylesheet" href="styles.css" />', '<link rel="stylesheet" href="viewer.css" /><style>[hidden]{display:none!important} [data-deck-controls]{position:fixed;bottom:0;left:0;right:0;height:60px;background:white} [data-deck-page]{min-height:300px} #page-two{height:140px;min-height:0;overflow:auto} .blocked{position:fixed;bottom:10px} .too-tall{height:300px}</style>').replace('<link rel="stylesheet" href="deck.css" />', '')
            container = container.replace('<!-- SUANHAI_DECK_PAGES -->', '<section id="page-one" data-deck-page data-speaker-note="中性备注"><h1>图解</h1><a href="image.svg" data-source-image="image.svg" data-source-caption="中性结构图">查看完整原图</a></section><section id="page-two" data-deck-page><h1>第二页</h1><p class="blocked">故意被导航遮挡</p><div class="too-tall">超过单页可视高度</div></section>')
            container = container.replace('<script src="deck.js"></script>', '<script src="deck.js"></script><script src="viewer.js"></script>')
            path = root / "index.html"
            path.write_text(container, encoding="utf-8")
            # 与既有演示稿CI一致，只在隔离Linux runner的合成样例中明确选择无沙箱。
            # 消费者默认保留沙箱；不能在启动失败后自动关闭或把失败改成skip。
            ci_sandbox = not sys.platform.startswith("linux")
            report = viewport.browser_check(path, [("desktop", 1366, 768, "screen"), ("phone", 390, 844, "screen")], root / "shots", backend="cdp", all_pages=True, interactions=True, sandbox=ci_sandbox)
            if report["status"] == "not-run":
                self.fail(f"本机浏览器存在但无法执行：{report}")
            self.assertEqual(len(report["viewports"]), 4, report)
            self.assertEqual(report["status"], "fail", report)
            self.assertTrue(report["viewports"][1]["metrics"]["navigationOverlap"], report)
            self.assertTrue(report["viewports"][1]["metrics"]["pageVerticalOverflow"], report)
            for interaction in report["interactions"]:
                self.assertEqual(interaction["status"], "not-run" if interaction["id"] in {"report-anchors", "display-modes", "fullscreen", "pdf-dialog"} else "pass", interaction)
            self.assertEqual(len(list((root / "shots").glob("*.png"))), 4)
            # 同一成品移除故意缺陷后必须通过，证明检查不是永远报错的测试替身。
            path.write_text(container.replace('class="blocked"', 'class="readable"').replace('<div class="too-tall">超过单页可视高度</div>', ''), encoding="utf-8")
            passing = viewport.browser_check(path, [("desktop", 1366, 768, "screen"), ("phone", 390, 844, "screen")], None, backend="cdp", all_pages=True, interactions=True, sandbox=ci_sandbox)
            self.assertEqual(passing["status"], "pass", passing)


if __name__ == "__main__":
    unittest.main()
