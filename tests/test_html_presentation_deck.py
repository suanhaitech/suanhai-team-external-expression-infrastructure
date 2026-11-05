"""用真实浏览器检查演示稿的翻页、可读布局、打印和无脚本降级。

复用 PDF 工具已有的本地 HTTP 与 CDP 协议，不引入 Playwright/Selenium 依赖。
测试夹具从当前工作树物料化到临时目录，因此无需提交或改写消费端仓库。
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from pathlib import PurePosixPath
import re
import subprocess
import sys
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


class HtmlPresentationDeckPrintCssContractTest(unittest.TestCase):
    def test_print_stage_uses_available_width_in_container_and_preset(self):
        selector = re.compile(
            r"\.deck-stage,\s*html\.deck--ready\[data-layout-mode\]\s+\.deck-stage,"
            r"\s*\.deck--ready\[data-deck-ratio\]\s+\.deck-stage\s*\{([^}]*)\}"
        )
        for relative in (
            "infrastructure/html/templates/containers/presentation-deck-v1/deck.css",
            "infrastructure/html/templates/presets/presentation-deck-v1/deck.css",
        ):
            with self.subTest(asset=relative):
                css = (ROOT / relative).read_text(encoding="utf-8")
                rule = selector.search(css)
                self.assertIsNotNone(rule, f"缺少演示稿打印阶段规则：{relative}")
                self.assertRegex(rule.group(1), r"(?m)^\s*width:\s*100%;\s*$")

    def test_screen_pages_reserve_space_above_fixed_controls(self):
        for relative in (
            "infrastructure/html/templates/containers/presentation-deck-v1/deck.css",
            "infrastructure/html/templates/presets/presentation-deck-v1/deck.css",
        ):
            with self.subTest(asset=relative):
                css = (ROOT / relative).read_text(encoding="utf-8")
                self.assertIn("max-height: calc(100svh - var(--deck-controls-height, 80px) - var(--deck-notes-height, 0px) - 5rem)", css)
                self.assertIn("overflow-y: auto", css)
                self.assertIn("padding-bottom: 1rem", css)

    def test_fullscreen_keeps_the_window_composition_and_scales_the_page_as_a_unit(self):
        for relative in (
            "infrastructure/html/templates/containers/presentation-deck-v1/deck.css",
            "infrastructure/html/templates/presets/presentation-deck-v1/deck.css",
        ):
            with self.subTest(asset=relative):
                css = (ROOT / relative).read_text(encoding="utf-8")
                self.assertIn("transform: scale(var(--deck-content-scale, 1))", css)
                self.assertIn("height: var(--deck-design-height, 100svh)", css)
                self.assertIn("html.deck-fullscreen.deck-controls-visible .deck-controls", css)
        for relative in (
            "infrastructure/html/styles/presentation-v1/styles.css",
            "infrastructure/html/templates/single-page/cover/technical-editorial-v1/styles.css",
            "infrastructure/html/templates/single-page/transition/statement-v1/styles.css",
        ):
            with self.subTest(asset=relative):
                css = (ROOT / relative).read_text(encoding="utf-8")
                self.assertNotRegex(css, r"\b\d+(?:\.\d+)?vw\b")


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
                "html.single-page.content.project-overview-v1",
                "html.single-page.content.workstream-update-v1",
                "html.single-page.content.dependencies-v1",
                "html.single-page.cover.technical-editorial-v1",
                "html.single-page.content.definition-mapping-v1",
                "html.single-page.content.figure-analysis-v1",
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
             "--remote-debugging-port=0", *(["--no-sandbox"] if sys.platform.startswith("linux") else []),
             f"--user-data-dir={profile}", "about:blank"],
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
        # 演示容器在短屏内限制页面高度；验证超出部分可在当前页内部访问。
        self.viewport(390, 600)
        self.select_page(1)
        self.evaluate("(() => { const page=document.querySelector('[data-deck-page]:not([hidden]) > [data-single-page-role]'); page.scrollTop=page.scrollHeight; })()")
        self.settle()
        self.assertGreater(self.evaluate("document.querySelector('[data-deck-page]:not([hidden]) > [data-single-page-role]').scrollTop"), 0)
        self.click("[data-page-next]")
        self.assertEqual(self.evaluate("document.querySelector('[data-page-select]').value"), "2")
        self.assertGreaterEqual(self.evaluate("document.querySelector('[data-deck-stage]').getBoundingClientRect().top"), 0)
        self.assertTrue(self.evaluate("document.querySelector('[data-deck-page]:not([hidden])').getBoundingClientRect().top >= -2"))
        self.viewport(1366, 768)
        self.select_page(count - 1)
        self.assertTrue(self.evaluate("document.querySelector('[data-page-next]').disabled"))
        self.evaluate("document.body.dispatchEvent(new KeyboardEvent('keydown', {key: 'Home', bubbles: true, cancelable: true}))")
        self.assertEqual(self.evaluate("document.querySelector('[data-page-select]').value"), "0")
        self.evaluate("document.body.dispatchEvent(new KeyboardEvent('keydown', {key: 'ArrowRight', shiftKey: true, bubbles: true, cancelable: true}))")
        self.assertEqual(self.evaluate("document.querySelector('[data-page-select]').value"), "1")
        self.evaluate("document.body.dispatchEvent(new KeyboardEvent('keydown', {key: ' ', shiftKey: true, bubbles: true, cancelable: true}))")
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
                    metrics = self.evaluate("(() => { const page=document.querySelector('[data-deck-page]:not([hidden])'); const pageRect=page.getBoundingClientRect(); const controls=document.querySelector('[data-deck-controls]').getBoundingClientRect(); return {rootWidth:document.documentElement.scrollWidth, viewport:innerWidth, pageWidth:page.clientWidth, scrollWidth:page.scrollWidth, pageHeight:page.clientHeight, scrollHeight:page.scrollHeight, pageBottom:pageRect.bottom, controlsTop:controls.top, overflowY:getComputedStyle(page).overflowY, page:page.id}; })()")
                    self.assertLessEqual(metrics["rootWidth"], metrics["viewport"] + 2, metrics)
                    self.assertLessEqual(metrics["scrollWidth"], metrics["pageWidth"] + 2, metrics)
                    self.assertLessEqual(metrics["pageBottom"], metrics["controlsTop"] + 2, metrics)
                    if metrics["scrollHeight"] > metrics["pageHeight"] + 2:
                        self.assertIn(metrics["overflowY"], {"auto", "scroll"}, metrics)
                        self.assertGreater(self.evaluate("(() => { const page=document.querySelector('[data-deck-page]:not([hidden])'); page.scrollTop=page.scrollHeight; return page.scrollTop; })()"), 0, metrics)
                        self.evaluate("document.querySelector('[data-deck-page]:not([hidden])').scrollTop=0")

    def test_print_shows_all_pages_without_clipping(self):
        self.cdp.call("Emulation.setEmulatedMedia", {"media": "print"})
        self.settle()
        # Chromium 的打印媒体样式可能已匹配，但容器查询触发的后续布局仍保留
        # 屏幕画布宽度；本机可复现两帧后仍需下一次布局才恢复全宽。按打印的
        # 可观察结果有界等待，不把固定帧数当作布局完成。永久塌缩仍由原断言失败。
        deadline = time.monotonic() + 3
        while True:
            stage_metrics = self.evaluate("(() => { const shell=document.querySelector('.deck-shell').getBoundingClientRect(); const stage=document.querySelector('[data-deck-stage]'); const rect=stage.getBoundingClientRect(); return {shellWidth:shell.width, stageWidth:rect.width, printMedia:matchMedia('print').matches, stageDisplay:getComputedStyle(stage).display, stageContainer:getComputedStyle(stage).containerType}; })()")
            if stage_metrics["printMedia"] and stage_metrics["stageWidth"] >= stage_metrics["shellWidth"] * 0.9:
                break
            if time.monotonic() >= deadline:
                break
            time.sleep(0.025)
        self.assertTrue(stage_metrics["printMedia"], stage_metrics)
        self.assertGreaterEqual(stage_metrics["stageWidth"], stage_metrics["shellWidth"] * 0.9, stage_metrics)
        metrics = self.evaluate("[...document.querySelectorAll('[data-deck-page]')].map(page => ({id:page.id, display:getComputedStyle(page).display, overflow:getComputedStyle(page).overflow, height:page.clientHeight, scrollHeight:page.scrollHeight, breakAfter:getComputedStyle(page).breakAfter}))")
        for page in metrics:
            self.assertNotEqual(page["display"], "none", page)
            self.assertNotEqual(page["overflow"], "hidden", page)
            self.assertLessEqual(page["scrollHeight"], page["height"] + 2, page)
        self.assertTrue(all(page["breakAfter"] == "page" for page in metrics[:-1]))
        self.assertEqual(self.evaluate("getComputedStyle(document.querySelector('[data-deck-controls]')).display"), "none")

    def test_composed_canvas_fills_frame_and_folios_share_a_baseline(self):
        # 模板使用深浅两种背景及不同内容高度；不是只核对某一页的 CSS 字符串。
        for width, height in ((1366, 768), (1920, 1080), (390, 844)):
            self.viewport(width, height)
            metrics = []
            count = self.evaluate("document.querySelectorAll('[data-deck-page]').length")
            for index in range(count):
                self.select_page(index)
                item = self.evaluate("""(() => {
                  const page=document.querySelector('[data-deck-page]:not([hidden])');
                  const single=page.querySelector('[data-single-page-role]');
                  const folio=page.querySelector('.deck-page-folio');
                  const p=page.getBoundingClientRect(), s=single.getBoundingClientRect(), f=folio.getBoundingClientRect();
                  const n=folio.querySelector('.deck-page-number').getBoundingClientRect();
                  const style=getComputedStyle(page);
                  return {id:page.id, width:p.width, height:p.height, top:s.top-p.top, left:s.left-p.left,
                    right:p.right-s.right, bodyBottom:s.bottom, folioTop:f.top, numberBottom:n.bottom-p.top,
                    paper:style.backgroundColor, content:getComputedStyle(single).backgroundColor,
                    border:style.borderTopWidth, padding:style.paddingTop, shadow:style.boxShadow,
                    count:page.querySelectorAll('.deck-page-number').length};
                })()""")
                metrics.append(item)
                for gap in ("top", "left", "right"):
                    self.assertAlmostEqual(item[gap], 0, delta=1, msg=str(item))
                self.assertLessEqual(item["bodyBottom"], item["folioTop"] + 1, item)
                self.assertEqual((item["paper"], item["border"], item["padding"], item["shadow"], item["count"]),
                                 (item["content"], "0px", "0px", "none", 1), item)
            for field in ("width", "height", "numberBottom"):
                self.assertLessEqual(max(m[field] for m in metrics)-min(m[field] for m in metrics), 1, (field, metrics))

        # 页码属于画布固定行，正文滚到末尾也不会挤走页码或盖住最后一行。
        self.select_page(3)
        self.evaluate("""(() => { const single=document.querySelector('[data-deck-page]:not([hidden]) > [data-single-page-role]');
          const tall=document.createElement('p'); tall.style.height='1600px'; tall.textContent='长正文'; single.appendChild(tall);
          const end=document.createElement('p'); end.id='reading-end'; end.textContent='最后一行'; single.appendChild(end);
          single.scrollTop=single.scrollHeight; })()""")
        self.settle()
        self.assertTrue(self.evaluate("document.querySelector('#reading-end').getBoundingClientRect().bottom <= document.querySelector('[data-deck-page]:not([hidden]) .deck-page-folio').getBoundingClientRect().top + 1"))

    def test_fullscreen_scales_the_whole_page_and_reserves_space_for_controls(self):
        self.viewport(1180, 805)
        self.select_page(0)
        normal = self.evaluate("(() => { const page=document.querySelector('[data-deck-page]:not([hidden])'); const title=page.querySelector('h1,h2,h3'); return {page:page.getBoundingClientRect().toJSON(), title:title.getBoundingClientRect().toJSON()}; })()")
        self.evaluate("(() => { let active=false; Object.defineProperty(document,'fullscreenElement',{configurable:true,get:()=>active?document.documentElement:null}); document.documentElement.requestFullscreen=()=>{active=true;document.dispatchEvent(new Event('fullscreenchange'));return Promise.resolve()}; document.exitFullscreen=()=>{active=false;document.dispatchEvent(new Event('fullscreenchange'));return Promise.resolve()}; })()")
        self.click("[data-runtime-fullscreen]")
        self.viewport(1920, 1080)
        self.assertTrue(self.evaluate("document.documentElement.classList.contains('deck-fullscreen')"))
        full = self.evaluate("(() => { const page=document.querySelector('[data-deck-page]:not([hidden])'); const title=page.querySelector('h1,h2,h3'); return {page:page.getBoundingClientRect().toJSON(), title:title.getBoundingClientRect().toJSON(), scale:Number(getComputedStyle(page).getPropertyValue('--deck-content-scale'))}; })()")
        expected = min(1920 / normal["page"]["width"], 1080 / normal["page"]["height"])
        self.assertAlmostEqual(full["scale"], expected, delta=0.02, msg=f"normal={normal}; full={full}")
        self.assertAlmostEqual(full["page"]["width"] / normal["page"]["width"], expected, delta=0.02)
        self.assertAlmostEqual(full["title"]["height"] / normal["title"]["height"], expected, delta=0.05)
        self.assertGreater(full["scale"], 1.2)
        folios = []
        for index in range(self.evaluate("document.querySelectorAll('[data-deck-page]').length")):
            self.select_page(index)
            folios.append(self.evaluate("(() => {const p=document.querySelector('[data-deck-page]:not([hidden])'),r=p.getBoundingClientRect(),n=p.querySelector('.deck-page-number').getBoundingClientRect();return {height:r.height,baseline:n.bottom-r.top};})()"))
        for field in ("height", "baseline"):
            self.assertLessEqual(max(f[field] for f in folios)-min(f[field] for f in folios), 1, folios)

        self.evaluate("window.dispatchEvent(new PointerEvent('pointermove',{clientY:innerHeight-5}))")
        self.settle()
        controls = self.evaluate("(() => { const bar=document.querySelector('[data-deck-controls]').getBoundingClientRect(); const page=document.querySelector('[data-deck-page]:not([hidden])').getBoundingClientRect(); return {visible:document.documentElement.classList.contains('deck-controls-visible'),barTop:bar.top,pageBottom:page.bottom}; })()")
        self.assertTrue(controls["visible"])
        visible_scale = self.evaluate("Number(getComputedStyle(document.querySelector('[data-deck-page]:not([hidden])')).getPropertyValue('--deck-content-scale'))")
        self.assertLess(visible_scale, full["scale"])
        self.assertLess(controls["pageBottom"], controls["barTop"] + 2)

        self.evaluate("window.dispatchEvent(new PointerEvent('pointermove',{clientY:100}))")
        self.click("[data-runtime-fullscreen]")
        self.assertFalse(self.evaluate("document.documentElement.classList.contains('deck-fullscreen')"))

        self.viewport(390, 844)
        self.click("[data-runtime-fullscreen]")
        phone = self.evaluate("(() => { const page=document.querySelector('[data-deck-page]:not([hidden])'); return {width:page.getBoundingClientRect().width,transform:getComputedStyle(page).transform}; })()")
        self.assertAlmostEqual(phone["width"], 390, delta=2)
        self.assertEqual(phone["transform"], "none")
        self.evaluate("window.dispatchEvent(new PointerEvent('pointermove',{clientY:innerHeight-5}))")
        self.settle()
        self.assertTrue(self.evaluate("document.querySelector('[data-deck-page]:not([hidden])').getBoundingClientRect().bottom <= document.querySelector('[data-deck-controls]').getBoundingClientRect().top"))
        self.select_page(1)
        self.evaluate("(() => { const single=document.querySelector('[data-deck-page]:not([hidden]) > [data-single-page-role]'); const tail=document.createElement('p');tail.id='fullscreen-tail';tail.textContent='最后一行';single.appendChild(tail);single.scrollTop=single.scrollHeight; })()")
        self.assertTrue(self.evaluate("document.querySelector('[data-deck-page]:not([hidden]) .deck-page-number').getBoundingClientRect().bottom < document.querySelector('[data-deck-controls]').getBoundingClientRect().top"))
        self.assertTrue(self.evaluate("document.querySelector('#fullscreen-tail').getBoundingClientRect().bottom <= document.querySelector('[data-deck-page]:not([hidden]) .deck-page-folio').getBoundingClientRect().top + 1"))
        self.click("[data-runtime-fullscreen]")

    def test_short_desktop_canvas_fits_definition_and_figure_without_changing_fonts(self):
        # 浏览器工具栏、缩放或分屏会减少可用高度，不能只测 1366×768。
        # 使用中性长定义、三项图解，验证模板回收留白并完整显示图文，不靠裁切或缩字。
        self.evaluate("""(() => {
          // 消费端可定制页边距；共享短画布规则仍须正常覆盖，不能依赖删除其定制。
          const consumer=document.createElement('style');
          consumer.textContent='.deck-page > .ex-page {padding:.75rem 1.5rem} .ex-page__header {margin-bottom:1.5rem} .sp-content-figure-analysis figure img {max-height:15rem;width:auto;margin-inline:auto}';
          document.head.appendChild(consumer);
          const figure=document.querySelector('.sp-content-figure-analysis');
          figure.querySelector('.ex-page__title').textContent='案例讨论：跨入口的连续协作';
          figure.querySelector('.ex-page__lead').textContent='需求和修改决定在多个入口之间持续衔接。';
          figure.querySelector('figcaption').textContent='示意图，用于解释讨论过程。';
          figure.querySelector('.sp-content-figure-analysis__analysis').innerHTML=
            '<article><h3>场景</h3><p>成员在公共讨论中提出问题，随后进入代码评审。</p></article>'+
            '<article><h3>行动</h3><p>承接需求并保持相关上下文，在同一份修改中响应评审意见。</p></article>'+
            '<article><h3>边界</h3><p>提交候选修改不等于已经完成验收和发布。</p></article>';
          const definition=document.querySelector('.sp-content-definition-mapping');
          definition.querySelector('.ex-page__title').textContent='如何理解连续协作？';
          definition.querySelector('.sp-content-definition-mapping__definition p').textContent=
            '连续协作是在不同工作入口之间保持需求、上下文与修改决定的衔接，使后续参与者能够理解此前的判断与约束。';
          definition.querySelector('.sp-content-definition-mapping__rows').innerHTML=
            '<div><dt>信息衔接</dt><dd>在不同入口保留相关决定</dd></div>'+
            '<div><dt>任务推进</dt><dd>按已确认的目标持续工作</dd></div>'+
            '<div><dt>责任边界</dt><dd>将执行结果交回负责人评审</dd></div>';
        })()""")
        count = self.evaluate("document.querySelectorAll('[data-deck-page]').length")
        fonts = {}
        for width, height in ((1366, 768), (1280, 650), (1000, 700)):
            self.viewport(width, height)
            for index in (count-2, count-1):
                self.select_page(index)
                metrics = self.evaluate("""(() => {
                  const single=document.querySelector('[data-deck-page]:not([hidden]) > [data-single-page-role]');
                  const body=single.querySelector('.ex-page__body');
                  return {id:single.className,height:single.clientHeight,scroll:single.scrollHeight,
                    bodyFont:getComputedStyle(body).fontSize,titleFont:getComputedStyle(single.querySelector('h2')).fontSize,
                    overflow:getComputedStyle(single).overflowY};
                })()""")
                self.assertLessEqual(metrics['scroll'], metrics['height']+2, (width,height,metrics))
                self.assertEqual(metrics['overflow'], 'auto', metrics)
                self.assertEqual(metrics['bodyFont'], fonts.setdefault(index, metrics['bodyFont']), metrics)
        # 模拟进入全屏后的短画布保持：全屏扩大外层，内部查询仍使用设计尺寸。
        self.evaluate("""(() => { let active=false;
          Object.defineProperty(document,'fullscreenElement',{configurable:true,get:()=>active?document.documentElement:null});
          document.documentElement.requestFullscreen=()=>{active=true;document.dispatchEvent(new Event('fullscreenchange'));return Promise.resolve()};
          document.exitFullscreen=()=>{active=false;document.dispatchEvent(new Event('fullscreenchange'));return Promise.resolve()};
        })()""")
        self.click('[data-runtime-fullscreen]')
        self.viewport(1920, 1080)
        for index in (count-2, count-1):
            self.select_page(index)
            self.assertTrue(self.evaluate("(() => {const e=document.querySelector('[data-deck-page]:not([hidden]) > [data-single-page-role]');return e.scrollHeight<=e.clientHeight+2;})()"))
        self.click('[data-runtime-fullscreen]')

    def test_print_from_fullscreen_releases_screen_coordinates(self):
        self.evaluate("document.documentElement.classList.add('deck-fullscreen')")
        self.evaluate("document.querySelector('[data-deck-page]').style.setProperty('--deck-content-scale','1.6')")
        self.cdp.call("Emulation.setEmulatedMedia", {"media": "print"})
        self.settle()
        metrics = self.evaluate("[...document.querySelectorAll('[data-deck-page]')].map(page => ({display:getComputedStyle(page).display,position:getComputedStyle(page).position,transform:getComputedStyle(page).transform,overflow:getComputedStyle(page).overflow}))")
        for page in metrics:
            self.assertNotEqual(page["display"], "none", page)
            self.assertNotEqual(page["position"], "absolute", page)
            self.assertEqual(page["transform"], "none", page)
            self.assertEqual(page["overflow"], "visible", page)
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
