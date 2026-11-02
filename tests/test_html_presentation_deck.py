"""用真实浏览器检查演示稿的翻页、可读布局、打印和无脚本降级。

复用 PDF 工具已有的本地 HTTP 与 CDP 协议，不引入 Playwright/Selenium 依赖。
测试夹具从当前工作树物料化到临时目录，因此无需提交或改写消费端仓库。
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from pathlib import PurePosixPath
import subprocess
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PDF = load_module("presentation_deck_pdf_test", "infrastructure/html/tools/pdf-export/export_pdf.py")
MATERIALIZE = load_module("presentation_deck_materialize_test", "infrastructure/html/tools/materialize/materialize_html.py")


class HtmlPresentationDeckBrowserTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        browser = PDF._find_browser(None)
        if not browser:
            raise unittest.SkipTest("未找到本机 Chrome/Edge/Chromium；浏览器交互与布局检查 not-run")

        cls.temp = tempfile.TemporaryDirectory(prefix="html-deck-browser-", ignore_cleanup_errors=True)
        cls.addClassCleanup(cls.temp.cleanup)
        cls.workspace = Path(cls.temp.name)
        artifact = cls.workspace / "artifact"
        artifact.mkdir()
        files, _ = MATERIALIZE.build_plan(
            infrastructure=ROOT,
            manifest=MATERIALIZE.parse_manifest(ROOT / "manifest.yml"),
            template_id=None,
            component_package_id="html.semantic-components-v1",
            component_ids=[],
            layout_id="html.responsive-layout-v1",
            runtime_kit_id="html.runtime-kit-v1",
            task_id="EXPR-20261102-1234abcd",
            version="v001",
            task_revision=1,
            task_record_version=4,
            infrastructure_commit="0" * 40,
            task_context={"revision": 1, "title": "演示稿浏览器测试", "audience": "测试者", "purpose": "验证演示稿交互与排版"},
            source_ids=[],
            container_id="html.container.presentation-deck-v1",
            page_ids=[
                "html.single-page.cover.editorial-v1",
                "html.single-page.agenda.route-v1",
                "html.single-page.transition.statement-v1",
                "html.single-page.content.evidence-v1",
                "html.single-page.content.method-v1",
                "html.single-page.closing.action-v1",
                "html.single-page.appendix.source-register-v1",
            ],
        )
        index_path = PurePosixPath("index.html")
        generated_html = files[index_path].decode("utf-8")
        generated_html = generated_html.replace("[先说判断，再让读者看到依据]", "材料化后的真实页面标题")
        files[index_path] = generated_html.encode("utf-8")
        for relative, content in files.items():
            target = artifact.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)

        cls.server = PDF.LocalArtifactServer(artifact)
        cls.url = cls.server.__enter__()
        cls.addClassCleanup(cls.server.__exit__, None, None, None)
        profile = cls.workspace / "profile"
        profile.mkdir()
        cls.process = subprocess.Popen(
            [browser, "--headless=new", "--disable-gpu", "--disable-dev-shm-usage",
             "--disable-background-networking", "--disable-extensions", "--disable-sync",
             "--no-first-run", "--no-default-browser-check", "--remote-debugging-address=127.0.0.1",
             "--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE localhost, EXCLUDE 127.0.0.1",
             "--remote-debugging-port=0", f"--user-data-dir={profile}", "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        cls.cdp = None
        cls.addClassCleanup(cls.close_browser)
        active_port = profile / "DevToolsActivePort"
        deadline = time.monotonic() + 20
        port = None
        while time.monotonic() < deadline:
            if active_port.is_file():
                try:
                    lines = active_port.read_text(encoding="ascii", errors="replace").splitlines()
                except PermissionError:
                    lines = []
                if lines and lines[0].isdigit():
                    port = int(lines[0])
                    break
            time.sleep(0.1)
        if port is None:
            raise AssertionError("找到浏览器但未在 20 秒内启动 DevTools")
        # 浏览器可能在启动期间替换 about:blank 目标；只重连初始化阶段的失效目标，
        # 正式测试中的协议错误仍直接失败，不把页面回归隐藏为环境跳过。
        deadline = time.monotonic() + 5
        while True:
            try:
                targets = PDF._http_json(f"http://127.0.0.1:{port}/json/list")
                target = next(item for item in targets if item.get("type") == "page")
                cls.cdp = PDF.CDP(target["webSocketDebuggerUrl"], timeout=15)
                cls.cdp.call("Page.enable")
                cls.cdp.call("Runtime.enable")
                break
            except (OSError, PDF.ExportError, StopIteration):
                if cls.cdp:
                    cls.cdp.close()
                    cls.cdp = None
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.1)

    @classmethod
    def close_browser(cls):
        if cls.cdp:
            try:
                cls.cdp.call("Browser.close")
            except Exception:
                pass
            cls.cdp.close()
        if cls.process.poll() is None:
            cls.process.terminate()
            try:
                cls.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                cls.process.kill()
                cls.process.wait(timeout=5)

    def evaluate(self, expression: str):
        result = self.cdp.call("Runtime.evaluate", {"expression": expression, "returnByValue": True, "awaitPromise": True})
        self.assertNotIn("exceptionDetails", result, result)
        return result["result"].get("value")

    def settle(self):
        # 修改 viewport、媒体或 DOM 后等两帧，避免读取浏览器尚未重排的尺寸。
        self.evaluate("new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve(true))))")

    def viewport(self, width: int, height: int):
        self.cdp.call("Emulation.setDeviceMetricsOverride", {"width": width, "height": height, "deviceScaleFactor": 1, "mobile": False})
        self.settle()

    def setUp(self):
        self.cdp.call("Emulation.setScriptExecutionDisabled", {"value": False})
        self.cdp.call("Emulation.setEmulatedMedia", {"media": "screen"})
        self.cdp.call("Emulation.setDeviceMetricsOverride", {"width": 1366, "height": 768, "deviceScaleFactor": 1, "mobile": False})
        self.cdp.events.clear()
        self.cdp.call("Page.navigate", {"url": f"{self.url}/index.html?test={self._testMethodName}"})
        self.cdp.wait_event("Page.loadEventFired", timeout=15)
        self.evaluate("document.fonts.ready.then(() => true)")
        self.settle()
        self.assertTrue(self.evaluate("document.documentElement.classList.contains('deck--ready')"))

    def tearDown(self):
        self.cdp.call("Emulation.setScriptExecutionDisabled", {"value": False})

    def click(self, selector: str):
        self.evaluate(f"document.querySelector({json.dumps(selector)}).click()")
        self.settle()

    def select_page(self, index: int):
        self.evaluate(f"(() => {{ const select = document.querySelector('[data-page-select]'); select.value = '{index}'; select.dispatchEvent(new Event('change', {{bubbles: true}})); }})()")
        self.settle()

    def test_bottom_navigation_boundaries_keyboard_and_safe_notes(self):
        count = self.evaluate("document.querySelectorAll('[data-deck-page]').length")
        self.assertGreaterEqual(count, 6)
        self.assertEqual(
            self.evaluate("document.querySelector('[data-page-select]').options[3].textContent"),
            "04 · 材料化后的真实页面标题",
        )
        self.assertTrue(self.evaluate("Boolean(document.querySelector('[data-deck-stage]').compareDocumentPosition(document.querySelector('[data-deck-controls]')) & Node.DOCUMENT_POSITION_FOLLOWING)"))
        self.assertTrue(self.evaluate("document.querySelector('[data-page-prev]').disabled"))
        self.evaluate("new Promise((resolve, reject) => { const script=document.createElement('script'); script.src='deck.js'; script.onload=() => resolve(true); script.onerror=() => reject(new Error('重复加载翻页脚本失败')); document.body.appendChild(script); })")
        self.assertEqual(self.evaluate("document.querySelector('[data-page-select]').options.length"), count)
        self.click("[data-page-next]")
        self.assertEqual(self.evaluate("document.querySelector('[data-page-select]').value"), "1")
        self.click("[data-page-prev]")
        self.assertEqual(self.evaluate("document.querySelector('[data-page-select]').value"), "0")
        # 短屏让前后两页均高于可视区，避免浏览器因文档变短自动夹取滚动位置而误通过。
        self.viewport(390, 600)
        self.select_page(1)
        self.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
        self.settle()
        self.assertGreater(self.evaluate("window.scrollY"), 0)
        self.click("[data-page-next]")
        self.assertEqual(self.evaluate("document.querySelector('[data-page-select]').value"), "2")
        self.assertLessEqual(abs(self.evaluate("document.querySelector('[data-deck-stage]').getBoundingClientRect().top")), 2)
        self.assertTrue(self.evaluate("document.querySelector('[data-deck-page]:not([hidden])').getBoundingClientRect().top >= -2"))
        self.viewport(1366, 768)
        self.select_page(count - 1)
        self.assertTrue(self.evaluate("document.querySelector('[data-page-next]').disabled"))
        self.evaluate("document.body.dispatchEvent(new KeyboardEvent('keydown', {key: 'Home', bubbles: true, cancelable: true}))")
        self.assertEqual(self.evaluate("document.querySelector('[data-page-select]').value"), "0")
        self.evaluate("document.body.dispatchEvent(new KeyboardEvent('keydown', {key: 'End', bubbles: true, cancelable: true}))")
        self.assertEqual(self.evaluate("document.querySelector('[data-page-select]').value"), str(count - 1))
        self.assertTrue(self.evaluate("document.querySelector('[data-page-select]').dispatchEvent(new KeyboardEvent('keydown', {key: 'Home', bubbles: true, cancelable: true}))"))
        self.assertEqual(self.evaluate("document.querySelector('[data-page-select]').value"), str(count - 1))
        note = "<img src=x onerror='window.unexpectedNoteScript=true'>备注原文"
        self.evaluate(f"document.querySelectorAll('[data-deck-page]')[{count - 1}].setAttribute('data-speaker-note', {json.dumps(note)})")
        self.click("[data-notes-toggle]")
        self.assertEqual(self.evaluate("document.querySelector('[data-deck-notes-content]').textContent"), note)
        self.assertEqual(self.evaluate("document.querySelector('[data-deck-notes-content]').children.length"), 0)
        self.assertFalse(self.evaluate("Boolean(window.unexpectedNoteScript)"))

    def test_each_page_is_readable_across_viewports_ratios_and_runtime_modes(self):
        count = self.evaluate("document.querySelectorAll('[data-deck-page]').length")
        for width, height, ratio, mode in (
            (390, 844, "auto", "auto"), (768, 1024, "auto", "auto"),
            (1366, 768, "auto", "auto"), (1920, 1080, "auto", "auto"),
            (1366, 768, "portrait", "auto"), (1366, 768, "auto", "narrow"),
        ):
            with self.subTest(width=width, height=height, ratio=ratio, mode=mode):
                self.viewport(width, height)
                self.evaluate(f"(() => {{ const select=document.querySelector('[data-deck-ratio-select]'); select.value={json.dumps(ratio)}; select.dispatchEvent(new Event('change', {{bubbles:true}})); }})()")
                self.click(f"[data-runtime-mode='{mode}']")
                self.assertEqual(self.evaluate("document.documentElement.getAttribute('data-deck-ratio')"), ratio)
                if mode == "narrow":
                    self.assertEqual(self.evaluate("document.documentElement.getAttribute('data-layout-mode')"), "narrow")
                    self.assertLessEqual(self.evaluate("document.querySelector('[data-deck-stage]').clientWidth"), 430)
                if ratio == "portrait" and width > 760:
                    self.assertLess(self.evaluate("document.querySelector('[data-deck-stage]').clientWidth"), width / 2)
                for index in range(count):
                    self.select_page(index)
                    metrics = self.evaluate("(() => { const page=document.querySelector('[data-deck-page]:not([hidden])'); return {rootWidth:document.documentElement.scrollWidth, viewport:innerWidth, pageWidth:page.clientWidth, scrollWidth:page.scrollWidth, pageHeight:page.clientHeight, scrollHeight:page.scrollHeight, page:page.id}; })()")
                    self.assertLessEqual(metrics["rootWidth"], metrics["viewport"] + 2, metrics)
                    self.assertLessEqual(metrics["scrollWidth"], metrics["pageWidth"] + 2, metrics)
                    self.assertLessEqual(metrics["scrollHeight"], metrics["pageHeight"] + 2, metrics)

    def test_print_shows_all_pages_without_clipping(self):
        self.cdp.call("Emulation.setEmulatedMedia", {"media": "print"})
        self.settle()
        metrics = self.evaluate("[...document.querySelectorAll('[data-deck-page]')].map(page => ({id:page.id, display:getComputedStyle(page).display, overflow:getComputedStyle(page).overflow, height:page.clientHeight, scrollHeight:page.scrollHeight, breakAfter:getComputedStyle(page).breakAfter}))")
        for page in metrics:
            self.assertNotEqual(page["display"], "none", page)
            self.assertNotEqual(page["overflow"], "hidden", page)
            self.assertLessEqual(page["scrollHeight"], page["height"] + 2, page)
        self.assertTrue(all(page["breakAfter"] == "page" for page in metrics[:-1]))
        self.assertEqual(self.evaluate("getComputedStyle(document.querySelector('[data-deck-controls]')).display"), "none")

    def test_without_javascript_all_pages_remain_readable(self):
        self.cdp.call("Emulation.setScriptExecutionDisabled", {"value": True})
        self.cdp.events.clear()
        self.cdp.call("Page.reload", {"ignoreCache": True})
        self.cdp.wait_event("Page.loadEventFired", timeout=15)
        self.assertFalse(self.evaluate("document.documentElement.classList.contains('deck--ready')"))
        self.assertTrue(self.evaluate("[...document.querySelectorAll('[data-deck-page]')].every(page => !page.hidden && getComputedStyle(page).display !== 'none')"))
        self.assertEqual(self.evaluate("getComputedStyle(document.querySelector('[data-deck-controls]')).display"), "none")


if __name__ == "__main__":
    unittest.main()
