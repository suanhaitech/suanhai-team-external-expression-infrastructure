"""课程实践提炼页面的契约与真实浏览器边界回归。

测试使用中性内容和本地SVG，检查长标题、2/3/4项及窄屏；不据此宣称项目内容验收。
"""
from __future__ import annotations

from contextlib import ExitStack
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
SINGLE = ROOT / "infrastructure/html/templates/single-page"
NEW_PAGES = (
    ("cover", "technical-editorial-v1"),
    ("content", "stages-v1"),
    ("content", "observation-v1"),
    ("content", "definition-mapping-v1"),
    ("content", "comparison-v1"),
    ("content", "figure-analysis-v1"),
    ("content", "keyword-grid-v1"),
)
COMPONENTS = ("content.definition", "content.mapping", "content.keyword-grid", "evidence.observation", "evidence.figure-analysis")

def load_module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

PDF = load_module("course_assets_pdf", "infrastructure/html/tools/pdf-export/export_pdf.py")
MATERIALIZE = load_module("course_assets_materialize", "infrastructure/html/tools/materialize/materialize_html.py")

class CoursePageAssetContractTests(unittest.TestCase):
    def test_every_new_package_has_valid_fragment_and_local_assets(self):
        for role, variant in NEW_PAGES:
            with self.subTest(page=variant):
                folder = SINGLE / role / variant
                metadata = MATERIALIZE.single_page_metadata(folder / "template.yml")
                markup = (folder / "page.html").read_text(encoding="utf-8")
                styles = (folder / "styles.css").read_text(encoding="utf-8")
                MATERIALIZE.validate_single_page_fragment(markup, metadata, styles.encode("utf-8"))
                self.assertEqual(metadata["id"], f"html.single-page.{role}.{variant}")
                self.assertIn("styles/presentation-v1/styles.css", metadata["shared_styles"])
                for relative in re.findall(r'src="([^"]+)"', markup):
                    self.assertTrue((folder / relative).is_file(), relative)
                self.assertNotRegex(markup + styles, r"(?i)https?://|deepseek|super.agent|suanhaios|[a-z]:\\")
                if role == "content":
                    self.assertEqual(metadata["component_slots"], ["supporting"])
                    self.assertEqual(markup.count("<!-- SUANHAI_COMPONENTS:supporting -->"), 1)

    def test_component_contracts_are_discoverable_and_preserve_evidence_boundaries(self):
        package = ROOT / "infrastructure/html/components/core-v1"
        catalog = (package / "index.yml").read_text(encoding="utf-8")
        for component in COMPONENTS:
            contract = json.loads((package / f"semantic/contracts/{component}.json").read_text(encoding="utf-8"))
            self.assertEqual(contract["id"], component)
            self.assertIn("source_ids", contract["optional_slots"])
            self.assertIn(f"- id: {component}", catalog)
            self.assertTrue(contract["provenance"])
        observation = json.loads((package / "semantic/contracts/evidence.observation.json").read_text(encoding="utf-8"))
        self.assertTrue({"scope", "source", "source_status"}.issubset(observation["required_slots"]))
        mapping = json.loads((package / "semantic/contracts/content.mapping.json").read_text(encoding="utf-8"))
        self.assertIn("relationship_state", mapping["required_slots"])

    def test_figure_analysis_has_optional_reader_and_plain_link_fallback(self):
        markup = (SINGLE / "content/figure-analysis-v1/page.html").read_text(encoding="utf-8")
        self.assertIn('href="assets/diagram.svg"', markup)
        self.assertIn('data-source-image="assets/diagram.svg"', markup)
        self.assertIn('data-source-caption="', markup)
        self.assertIn('aria-label="查看完整示例图"', markup)

    def test_preview_covers_new_assets_and_preserves_relative_image_base(self):
        script = (SINGLE / "preview/preview.js").read_text(encoding="utf-8")
        for _, variant in NEW_PAGES:
            self.assertIn(f'variant: "{variant}"', script)
        self.assertIn("assetBase", script)
        self.assertIn("new URL(value, assetBase)", script)
        if shutil.which("node"):
            result = subprocess.run(["node", "--check", str(SINGLE / "preview/preview.js")], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

class CoursePageAssetBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        browser = PDF._find_browser(None)
        if not browser:
            raise unittest.SkipTest("本机无Chrome/Edge/Chromium，真实浏览器布局检查not-run")
        cls.resources = ExitStack()
        cls.addClassCleanup(cls.resources.close)
        workspace = Path(cls.resources.enter_context(tempfile.TemporaryDirectory(prefix="course-page-assets-", ignore_cleanup_errors=True)))
        artifact = workspace / "artifact"
        artifact.mkdir()
        # 保留目录树，和生产物料化一样让本地图像相对页面包解析。
        shutil.copytree(ROOT / "infrastructure/html", artifact / "html")
        heads = ['<link rel="stylesheet" href="html/templates/containers/presentation-deck-v1/deck.css">', '<link rel="stylesheet" href="html/components/core-v1/foundations/tokens.css">',
                 '<link rel="stylesheet" href="html/components/core-v1/themes/editorial-warm.css">',
                 '<link rel="stylesheet" href="html/styles/presentation-v1/styles.css">']
        fragments = []
        for role, variant in NEW_PAGES:
            prefix = f"html/templates/single-page/{role}/{variant}"
            heads.append(f'<link rel="stylesheet" href="{prefix}/styles.css">')
            markup = (SINGLE / role / variant / "page.html").read_text(encoding="utf-8")
            markup = markup.replace('src="assets/', f'src="{prefix}/assets/')
            markup = markup.replace('href="assets/', f'href="{prefix}/assets/')
            markup = markup.replace('data-source-image="assets/', f'data-source-image="{prefix}/assets/')
            markup = markup.replace("<!-- SUANHAI_PAGE_NUMBER -->", "01")
            fragments.append('<div class="frame deck-page">' + markup + '</div>')
        document = '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'+''.join(heads)+ '<style>body{margin:0}.frame{container-type:inline-size;max-width:1280px;margin:0 auto}</style></head><body>'+''.join(fragments)+'</body></html>'
        (artifact / "index.html").write_text(document, encoding="utf-8")
        cls.server = PDF.LocalArtifactServer(artifact)
        cls.url = cls.resources.enter_context(cls.server)
        profile = workspace / "profile"
        profile.mkdir()
        cls.process = subprocess.Popen([browser, "--headless=new", "--disable-gpu", "--disable-background-networking", "--disable-extensions", "--disable-sync", "--no-first-run", "--no-default-browser-check", "--remote-debugging-address=127.0.0.1", "--remote-debugging-port=0", *(["--no-sandbox"] if sys.platform.startswith("linux") else []), f"--user-data-dir={profile}", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cls.resources.callback(cls.close_browser)
        cls.cdp = None
        deadline = time.monotonic() + 20
        port_file = profile / "DevToolsActivePort"
        while time.monotonic() < deadline:
            if port_file.is_file():
                lines = port_file.read_text(encoding="ascii", errors="replace").splitlines()
                if lines and lines[0].isdigit():
                    port = int(lines[0]); break
            time.sleep(.1)
        else:
            raise AssertionError("浏览器未在20秒内启动DevTools")
        target = next(x for x in PDF._http_json(f"http://127.0.0.1:{port}/json/list") if x.get("type") == "page")
        cls.cdp = PDF.CDP(target["webSocketDebuggerUrl"], timeout=15)
        cls.cdp.call("Page.enable")
        cls.cdp.call("Runtime.enable")
        cls.cdp.call("Page.navigate", {"url": cls.url})
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            state = cls.cdp.call("Runtime.evaluate", {"expression": "document.readyState", "returnByValue": True})["result"].get("value")
            if state == "complete": break
            time.sleep(.05)

    @classmethod
    def close_browser(cls):
        if cls.cdp:
            try: cls.cdp.call("Browser.close")
            except Exception: pass
            cls.cdp.close()
        if cls.process.poll() is None:
            cls.process.terminate()
            try: cls.process.wait(timeout=5)
            except subprocess.TimeoutExpired: cls.process.kill(); cls.process.wait(timeout=5)

    def evaluate(self, expression):
        response = self.cdp.call("Runtime.evaluate", {"expression": expression, "returnByValue": True, "awaitPromise": True})
        self.assertNotIn("exceptionDetails", response, response)
        return response["result"].get("value")

    def viewport(self, width):
        self.cdp.call("Emulation.setDeviceMetricsOverride", {"width": width, "height": 900, "deviceScaleFactor": 1, "mobile": False})
        self.evaluate("new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")

    def test_local_figures_load_and_narrow_layout_does_not_overflow(self):
        self.assertTrue(self.evaluate("[...document.images].every(i=>i.complete&&i.naturalWidth>0)"))
        for width in (320, 390, 768, 1366):
            with self.subTest(width=width):
                self.viewport(width)
                result = self.evaluate("({width:innerWidth,scroll:document.documentElement.scrollWidth,font:Math.min(...[...document.querySelectorAll('.ex-page p')].map(p=>parseFloat(getComputedStyle(p).fontSize)))})")
                self.assertLessEqual(result["scroll"], width + 1, result)
                self.assertGreaterEqual(result["font"], 14)

    def test_long_mixed_language_titles_and_two_three_four_items_remain_readable(self):
        self.evaluate("document.querySelector('.sp-cover-technical__title').textContent='理解 Distributed Coordination and Observable Execution：复杂系统中的长标题与中英文混排机制'")
        for width in (320, 390, 1366):
            self.viewport(width)
            self.assertLessEqual(self.evaluate("document.documentElement.scrollWidth"), width+1)
        # 可重复结构的2/3/4项都要检查，而不是只验证默认四格样例。
        for selector in (".sp-content-stages__grid", ".sp-content-keyword-grid__grid"):
            self.evaluate(f"window.itemTemplate=document.querySelector({json.dumps(selector)}).firstElementChild.outerHTML")
            for count in (2, 3, 4):
                self.evaluate(f"document.querySelector({json.dumps(selector)}).innerHTML=window.itemTemplate.repeat({count})")
                for width in (320, 768, 1366):
                    self.viewport(width)
                    self.assertLessEqual(self.evaluate("document.documentElement.scrollWidth"), width+1, (selector,count,width))

    def test_container_defaults_do_not_force_short_cover_title_to_wrap(self):
        self.viewport(1366)
        self.evaluate("document.querySelector('.sp-cover-technical__title').textContent='理解可恢复的记录'")
        dimensions = self.evaluate("(()=>{let e=document.querySelector('.sp-cover-technical__title'),s=getComputedStyle(e);return {max:s.maxWidth,height:e.getBoundingClientRect().height,line:parseFloat(s.lineHeight)}})()")
        self.assertEqual(dimensions["max"], "none")
        self.assertLessEqual(dimensions["height"], dimensions["line"] + 1, dimensions)

    def test_keyword_modifier_and_keyword_keep_equal_typographic_weight(self):
        self.viewport(1366)
        values = self.evaluate("(()=>{let h=document.querySelector('.sp-content-keyword-grid__grid h3');return [...h.children].map(x=>({size:getComputedStyle(x).fontSize,weight:getComputedStyle(x).fontWeight}))})()")
        self.assertEqual(values[0], values[1])

if __name__ == "__main__":
    unittest.main()
