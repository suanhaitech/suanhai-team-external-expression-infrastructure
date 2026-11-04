"""交互组件真实浏览器回归；文件和浏览器 profile 均在隔离目录中产生。"""
from __future__ import annotations
import importlib.util
import os
from pathlib import Path
import shutil
import tempfile
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("interaction_browser", ROOT / "infrastructure/html/tools/browser_support.py")
browser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(browser)


class InteractionControlsBrowserTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="interaction-controls-", ignore_cleanup_errors=True)
        cls.addClassCleanup(cls.temp.cleanup)
        workspace = Path(cls.temp.name)
        shutil.copytree(ROOT / "infrastructure/html", workspace / "infrastructure/html")
        (workspace / "infrastructure/html/runtime-kits/preview/large.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" width="20000" height="12000"></svg>', encoding="utf-8")
        spec = importlib.util.spec_from_file_location("interaction_materializer", ROOT / "infrastructure/html/tools/materialize/materialize_html.py")
        materializer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(materializer)
        for template in ("html.project-report-v1", "html.presentation-deck-v1"):
            files, _ = materializer.build_plan(
                ROOT, materializer.parse_manifest(ROOT / "manifest.yml"), template,
                "html.semantic-components-v1", ["status.phase"], "html.responsive-layout-v1", None,
                "EXPR-20261104-1234abcd", "v001", 1, 1, "0" * 40,
                {"revision": 1, "title": "交互检查", "audience": "测试读者", "purpose": "验证组件兼容"}, [],
            )
            for relative, data in files.items():
                target = workspace / template / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
        cls.server = browser.LocalArtifactServer(workspace)
        cls.origin = cls.server.__enter__()
        cls.addClassCleanup(cls.server.__exit__, None, None, None)
        try:
            # 仅合成数据的 Linux CI runner 显式关闭沙箱；消费端和本机保持默认，失败不自动降级。
            isolated_ci = sys.platform.startswith("linux") and os.environ.get("CI") == "true"
            cls.session = browser.ChromiumSession(sandbox=not isolated_ci).__enter__()
        except browser.BrowserUnavailable as exc:
            raise unittest.SkipTest(str(exc))
        cls.addClassCleanup(cls.session.__exit__, None, None, None)

    def setUp(self):
        self.s = self.session
        self.s.viewport(1366, 900, "screen")
        self.s.navigate(self.origin + "/infrastructure/html/runtime-kits/preview/index.html")
        self.settle()

    def settle(self):
        self.s.evaluate("new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))")

    def wait_for(self, expression):
        # Chromium 的模态滚动区可能延后布局；等可观察的尺寸结果，超时仍失败。
        result = self.s.evaluate("new Promise(resolve => {let end=performance.now()+1500;function poll(){if(" + expression + ")resolve(true);else if(performance.now()>end)resolve(false);else requestAnimationFrame(poll);}poll();})")
        self.assertTrue(result, expression)

    def test_dock_visible_controls_and_readable_bottom_on_small_screens(self):
        for width in (320, 390, 768, 1366, 1920):
            self.s.viewport(width, 844, "screen")
            self.s.evaluate("document.querySelector('[data-notes-toggle]').click()")
            self.settle()
            self.s.evaluate("window.scrollTo(0,document.documentElement.scrollHeight)")
            self.settle()
            metrics = self.s.evaluate("""(() => {
                let controls = [...document.querySelectorAll('[data-deck-controls] button, [data-deck-controls] select')].filter(e=>e.getBoundingClientRect().width>0);
                let bar=document.querySelector('[data-deck-controls]').getBoundingClientRect();
                let notes=document.querySelector('[data-deck-notes-panel]');
                let content=document.querySelector('[data-deck-page]:not([hidden]) .lab-bottom').getBoundingClientRect();
                return {over:document.documentElement.scrollWidth>innerWidth,
                  clipped:controls.filter(e=>{let r=e.getBoundingClientRect();return r.left<0||r.right>innerWidth+1||r.height<43||r.top<bar.top||r.bottom>bar.bottom+1;}).length,
                  barInView:bar.top>=0&&bar.bottom<=innerHeight,
                  bottomReadable:content.bottom <= (notes.hidden?bar.top:notes.getBoundingClientRect().top)+1,
                  labels:[...document.querySelectorAll('.runtime-toolbar__button-label')].every(e=>getComputedStyle(e).display!=='none')};
            })()""")
            with self.subTest(width=width):
                self.assertFalse(metrics["over"], metrics)
                self.assertEqual(metrics["clipped"], 0, metrics)
                self.assertTrue(metrics["barInView"] and metrics["bottomReadable"] and metrics["labels"], metrics)

    def test_modes_ratio_and_initialization_are_independent(self):
        for mode in ("narrow", "tablet", "desktop", "auto"):
            self.s.evaluate(f"var s=document.querySelector('[data-runtime-mode-select]');s.value='{mode}';s.dispatchEvent(new Event('change'))")
            self.settle()
            self.assertEqual(self.s.evaluate("document.documentElement.getAttribute('data-layout-mode')||'auto'"), mode)
        # 重复初始化不能重复按钮/事件，且不能把已选择的状态重置。
        self.s.evaluate("window.SuanhaiRuntime.setMode('narrow');window.SuanhaiRuntime.init()")
        self.assertEqual(self.s.evaluate("document.documentElement.getAttribute('data-layout-mode')"), "narrow")
        self.assertEqual(self.s.evaluate("document.querySelectorAll('[data-runtime-fullscreen]').length"), 1)
        self.s.evaluate("document.querySelector('[data-deck-ratio-select]').value='classic';document.querySelector('[data-deck-ratio-select]').dispatchEvent(new Event('change'))")
        self.assertEqual(self.s.evaluate("document.documentElement.getAttribute('data-deck-ratio')"), "classic")
        self.assertTrue(self.s.evaluate("!!document.querySelector('[data-math] .katex')"))

    def test_fullscreen_with_trusted_mouse_and_rejection_feedback(self):
        if not self.s.evaluate("!!document.fullscreenEnabled"):
            self.skipTest("本次浏览器未开放全屏，不能视为通过")
        self.s.click("[data-runtime-fullscreen]")
        self.s.evaluate("new Promise(r=>setTimeout(r,200))")
        self.assertTrue(self.s.evaluate("!!document.fullscreenElement"))
        self.assertEqual(self.s.evaluate("document.querySelector('[data-runtime-fullscreen]').getAttribute('aria-pressed')"), "true")
        self.s.click("[data-runtime-fullscreen]")
        self.s.evaluate("new Promise(r=>setTimeout(r,200))")
        self.assertFalse(self.s.evaluate("!!document.fullscreenElement"))
        # 单独注入拒绝模拟权限失败，验证错误反馈；不将此段称为真实权限测试。
        self.s.evaluate("document.documentElement.requestFullscreen=()=>Promise.reject(new Error('denied'));document.querySelector('[data-runtime-fullscreen]').click()")
        self.settle()
        self.assertTrue(self.s.evaluate("!document.querySelector('[data-runtime-status]').hidden && document.querySelector('[data-runtime-status]').textContent.includes('重试')"))

    def test_print_entry_dispatches_once_and_print_media_contains_all_pages(self):
        self.s.evaluate("window.printCalls=0;window.print=()=>window.printCalls++;window.SuanhaiRuntime.init();document.querySelector('[data-runtime-pdf]').click()")
        self.s.evaluate("new Promise(r=>setTimeout(r,180))")
        self.assertEqual(self.s.evaluate("window.printCalls"), 1)
        self.s.viewport(1366, 900, "print")
        self.settle()
        self.assertTrue(self.s.evaluate("[...document.querySelectorAll('[data-deck-page]')].every(e=>getComputedStyle(e).display!=='none')"))
        self.assertEqual(self.s.evaluate("getComputedStyle(document.querySelector('[data-deck-controls]')).display"), "none")
        # 对话框是操作系统 UI；这里仅验证入口与打印媒体，不声称保存位置或纸张选择已验收。

    def open_image(self):
        self.s.evaluate("document.querySelector('[data-page-next]').click();document.querySelector('[data-source-image]').click()")
        self.s.evaluate("new Promise(r=>{let i=document.querySelector('[data-source-viewer-image]');if(i.complete)r();else i.addEventListener('load',r,{once:true})})")
        self.settle()

    def test_image_zoom_fit_drag_keyboard_and_focus_return(self):
        self.open_image()
        initial = self.s.evaluate("document.querySelector('[data-source-viewer-image]').getBoundingClientRect().width")
        self.s.click("[data-source-zoom-in]")
        self.wait_for(f"document.querySelector('[data-source-viewer-image]').getBoundingClientRect().width > {initial}")
        self.assertGreater(self.s.evaluate("document.querySelector('[data-source-viewer-image]').getBoundingClientRect().width"), initial)
        self.s.click("[data-source-actual]")
        self.assertEqual(self.s.evaluate("document.querySelector('[data-source-zoom]').value"), "100%")
        # 模态键盘事件不能触发背景翻页。
        self.s.key("ArrowRight")
        self.assertEqual(self.s.evaluate("document.querySelector('[data-page-select]').value"), "1")
        self.s.key("+")
        self.assertEqual(self.s.evaluate("document.querySelector('[data-source-zoom]').value"), "125%")
        self.s.evaluate("document.querySelector('.source-viewer__image').focus()")
        self.s.key("ArrowRight")
        self.s.evaluate("new Promise(r=>setTimeout(r,150))")
        self.assertGreater(self.s.evaluate("document.querySelector('.source-viewer__image').scrollLeft"), 0)
        point = self.s.evaluate("(() => {let v=document.querySelector('.source-viewer__image');v.scrollLeft=0;let r=v.getBoundingClientRect();return {x:r.left+r.width*.7,y:r.top+60};})()")
        self.s.cdp.call("Input.dispatchMouseEvent", {"type": "mousePressed", **point, "button": "left", "clickCount": 1})
        self.s.cdp.call("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": point["x"] - 200, "y": point["y"], "button": "left", "buttons": 1})
        self.s.cdp.call("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": point["x"] - 200, "y": point["y"], "button": "left", "clickCount": 1})
        self.wait_for("document.querySelector('.source-viewer__image').scrollLeft>100")
        self.s.click("[data-source-fit]")
        self.wait_for("document.querySelector('[data-source-viewer-image]').getBoundingClientRect().width<=document.querySelector('.source-viewer__image').clientWidth+1")
        self.assertTrue(self.s.evaluate("document.querySelector('[data-source-viewer-image]').getBoundingClientRect().width<=document.querySelector('.source-viewer__image').clientWidth+1"))
        self.s.key("Escape")
        self.settle()
        self.assertFalse(self.s.evaluate("document.querySelector('[data-source-viewer]').open"))
        self.assertTrue(self.s.evaluate("document.activeElement.matches('[data-source-image]')"))
        self.assertEqual(self.s.evaluate("document.body.style.overflow"), "")

    def test_image_failure_can_retry_and_mobile_fit_survives_resize(self):
        self.s.viewport(390, 844, "screen")
        self.open_image()
        self.s.viewport(320, 700, "screen")
        self.settle()
        self.assertTrue(self.s.evaluate("document.querySelector('[data-source-viewer-image]').getBoundingClientRect().width<=document.querySelector('.source-viewer__image').clientWidth+1"))
        self.s.key("Escape")
        self.settle()
        self.s.evaluate("var t=document.querySelector('[data-source-image]');window.originalSource=t.getAttribute('data-source-image');t.setAttribute('data-source-image','missing.svg');t.click()")
        self.s.evaluate("new Promise(r=>setTimeout(r,200))")
        self.assertTrue(self.s.evaluate("document.querySelector('[data-source-viewer-status]').textContent.includes('加载失败')"))
        self.s.key("Escape")
        self.settle()
        self.s.evaluate("var t=document.querySelector('[data-source-image]');t.setAttribute('data-source-image',window.originalSource);t.click()")
        self.s.evaluate("new Promise(r=>setTimeout(r,150))")
        self.assertTrue(self.s.evaluate("!document.querySelector('[data-source-viewer-image]').hidden"))

    def test_large_image_fits_entire_mobile_window(self):
        self.s.viewport(320, 700, "screen")
        self.s.evaluate("document.querySelector('[data-page-next]').click();document.querySelector('[data-source-image]').setAttribute('data-source-image','large.svg');document.querySelector('[data-source-image]').click()")
        self.wait_for("document.querySelector('[data-source-viewer-image]').naturalWidth===20000")
        self.wait_for("(() => {let i=document.querySelector('[data-source-viewer-image]').getBoundingClientRect(),v=document.querySelector('.source-viewer__image');return i.width<=v.clientWidth+1&&i.height<=v.clientHeight+1;})()")

    def test_missing_optional_controls_do_not_disable_navigation(self):
        # 在临时文档中移除备注/比例后重新运行真正脚本，验证组件之间的故障边界。
        self.s.evaluate("""async () => {}""")
        self.s.evaluate(r"""(async () => {
          let source=await (await fetch('../../templates/containers/presentation-deck-v1/deck.js')).text();
          document.querySelector('[data-deck-controls]').removeAttribute('data-deck-ready');
          document.querySelector('[data-notes-toggle]').remove();
          document.querySelector('[data-deck-notes-panel]').remove();
          document.querySelector('[data-deck-ratio-select]').remove();
          document.querySelector('[data-page-select]').replaceChildren();
          // 新文档消除旧监听，避免旧实现误通过。
          let markup=document.documentElement.outerHTML.replace(/<script[\s\S]*?<\/script>/g,'');
          document.open();document.write(markup);document.close();
          (0,eval)(source);
          document.querySelector('[data-page-next]').click();
          return true;
        })()""")
        self.assertEqual(self.s.evaluate("document.querySelector('[data-page-select]').value"), "1")

    def test_actual_artifact_interaction_checker(self):
        spec = importlib.util.spec_from_file_location("interaction_viewport", ROOT / "infrastructure/html/tools/viewport-check/viewport_check.py")
        checker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(checker)
        self.s.evaluate((ROOT / "infrastructure/html/tools/viewport-check/page_checks.js").read_text(encoding="utf-8"))
        checks = {item["id"]: item for item in checker.interaction_check(self.s)}
        for name in ("display-modes", "source-image-viewer", "source-image-zoom", "deck-keyboard", "speaker-notes"):
            self.assertEqual(checks[name]["status"], "pass", checks[name])
        supported = self.s.evaluate("!!document.fullscreenEnabled")
        self.assertEqual(checks["fullscreen"]["status"], "pass" if supported else "not-run", checks["fullscreen"])
        self.assertEqual(checks["pdf-dialog"]["status"], "not-run")

    def test_real_presets_share_defaults_and_mobile_controls_remain_usable(self):
        for template in ("html.project-report-v1", "html.presentation-deck-v1"):
            self.s.navigate(self.origin + "/" + template + "/index.html")
            for width in (320, 390, 1366):
                self.s.viewport(width, 844, "screen")
                self.settle()
                self.assertEqual(self.s.evaluate("document.querySelectorAll('[data-runtime-fullscreen]').length"), 1)
                self.assertEqual(self.s.evaluate("document.querySelectorAll('[data-runtime-pdf]').length"), 1)
                self.assertTrue(self.s.evaluate("!!window.SuanhaiImageViewer"))
                self.assertTrue(self.s.evaluate("[...document.querySelectorAll('[data-runtime-fullscreen], [data-runtime-pdf], [data-runtime-mode-select]')].every(e=>{let r=e.getBoundingClientRect();return r.width===0||(r.left>=0&&r.right<=innerWidth+1&&r.height>=43);})"))
                self.assertTrue(self.s.evaluate("document.documentElement.scrollWidth<=innerWidth+1"))
            if template == "html.presentation-deck-v1":
                self.s.click("[data-page-next]")
                self.assertEqual(self.s.evaluate("document.querySelector('[data-page-select]').value"), "1")
            self.s.evaluate("window.SuanhaiRuntime.setMode('narrow')")
            self.settle()
            self.assertEqual(self.s.evaluate("document.documentElement.getAttribute('data-layout-mode')"), "narrow")


if __name__ == "__main__":
    unittest.main()
