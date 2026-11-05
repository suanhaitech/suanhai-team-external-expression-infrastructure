"""周期汇报资产回归：合成内容验证组合、事实边界与真实浏览器阅读。

模板可复用不意味着项目事实通过验收；这里故意包含未知进度、拟议计划、
长标题和不同条目数量，防止共享资产只能展示某份报告的理想样例。
"""
from contextlib import ExitStack
import copy
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "infrastructure/html"
CORE = HTML / "components/core-v1"
EXAMPLE = HTML / "examples/project-progress"
PAGES = ("project-status-v1", "workstream-research-v1", "conclusion-evidence-v1", "workstream-plan-v1")
COMPONENTS = ("status.progress", "evidence.claim-source", "action.plan-table")


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MATERIALIZE = load("progress_materialize", "infrastructure/html/tools/materialize/materialize_html.py")
BROWSER = load("progress_browser", "infrastructure/html/tools/browser_support.py")


def build(theme="editorial-green", repeated=False):
    plan = json.loads((EXAMPLE / "page-plan.json").read_text(encoding="utf-8"))
    if repeated:
        page = copy.deepcopy(plan["pages"][1])
        page["id"] = "topic-second"
        plan["pages"].append(page)
    return MATERIALIZE.build_plan(
        ROOT, MATERIALIZE.parse_manifest(ROOT / "manifest.yml"), None,
        "html.semantic-components-v1", [], [], [], "EXPR-20261105-1234abcd", "v001", 1, 1,
        "a" * 40, {"revision": 1, "title": "合成周期报告", "audience": "示例合作方", "purpose": "检查资产边界"}, [],
        "html.container.presentation-deck-v1", [], "expression.scenario.project-progress-communication-v1", plan, theme,
    )


def contrast(a, b):
    def luminance(color):
        channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        values = [x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4 for x in channels]
        return sum(x * weight for x, weight in zip(values, (.2126, .7152, .0722)))
    left, right = sorted((luminance(a), luminance(b)))
    return (right + .05) / (left + .05)


class ProjectReportContractTests(unittest.TestCase):
    def test_page_fragments_and_shared_dependencies_are_real(self):
        for name in PAGES:
            folder = HTML / "templates/single-page/content" / name
            metadata = MATERIALIZE.single_page_metadata(folder / "template.yml")
            markup = (folder / "page.html").read_text(encoding="utf-8")
            MATERIALIZE.validate_single_page_fragment(markup, metadata, (folder / "styles.css").read_bytes())
            for style in metadata["shared_styles"]:
                self.assertTrue((HTML / style).is_file(), style)
            self.assertNotRegex(markup, r"SGSim|TensorFem|PETSc|50%|30%|40%|[A-Z]:\\")

    def test_real_composition_themes_repeated_ids_and_page_scoped_components(self):
        for theme in ("editorial-green", "editorial-warm"):
            files, record = build(theme, repeated=True)
            markup = files[PurePosixPath("index.html")].decode()
            self.assertEqual(len(record["pages"]), 5)
            ids = re.findall(r'(?<![\w:-])id="([^"]+)"', markup)
            self.assertEqual(len(ids), len(set(ids)), ids)
            self.assertIn(f"themes/{theme}.css", markup)
            self.assertIn('id="topic-second-report-page-title"', markup)
            self.assertIn('data-component="status.progress"', markup)
            self.assertIn('data-component="action.plan-table"', markup)
            self.assertIn(PurePosixPath("assets/shared/styles/project-report-v1/styles.css"), files)
            self.assertNotIn("SUANHAI_COMPONENTS:supporting", markup)
        plan = json.loads((EXAMPLE / "page-plan.json").read_text(encoding="utf-8"))
        plan["pages"][1]["components"] = [{"slot": "supporting", "id": cid} for cid in COMPONENTS]
        files, record = MATERIALIZE.build_plan(
            ROOT, MATERIALIZE.parse_manifest(ROOT / "manifest.yml"), None,
            "html.semantic-components-v1", [], [], [], "EXPR-20261105-1234abcd", "v001", 1, 1, "a" * 40,
            {"revision": 1, "title": "组件例子", "audience": "示例合作方", "purpose": "核对组件"}, [], "html.container.presentation-deck-v1", [], None, plan, "editorial-green")
        self.assertEqual({item["id"] for item in record["semantic_components"]}, set(COMPONENTS))

    def test_component_unknown_state_and_contracts_do_not_invent_a_number(self):
        catalog = MATERIALIZE.component_catalog(CORE / "index.yml", "html.semantic-components-v1")
        for cid in COMPONENTS:
            entry = catalog[cid]
            data = json.loads((CORE / entry["contract"]).read_text(encoding="utf-8"))
            markup = (CORE / entry["template"]).read_text(encoding="utf-8")
            self.assertTrue(set(data["required_slots"]).issubset(set(re.findall(r'data-slot="([^"]+)"', markup))))
            self.assertIn("source_ids", data["required_slots"] + data["optional_slots"])
            self.assertTrue(data["provenance"])
        progress = (CORE / catalog["status.progress"]["template"]).read_text(encoding="utf-8")
        tag = re.search(r"<progress\b[^>]*>", progress)[0]
        self.assertIn("hidden", tag)
        self.assertNotRegex(tag, r'(?<![\w-])value=')
        self.assertIn("待确认", progress)
        claim = (CORE / catalog["evidence.claim-source"]["template"]).read_text(encoding="utf-8")
        self.assertNotIn('href="#"', claim)

    def test_green_text_contrast_and_documentation_links(self):
        css = (CORE / "themes/editorial-green.css").read_text(encoding="utf-8")
        colors = dict(re.findall(r"--ex-color-([a-z-]+):\s*(#[0-9a-f]{6})", css))
        for foreground in ("ink", "muted", "accent"):
            for background in ("page", "surface"):
                self.assertGreaterEqual(contrast(colors[foreground], colors[background]), 4.5, (foreground, background))
        docs = [ROOT / "docs/project-report-reusable-assets.md", *(HTML / "templates/single-page/content" / name / "README.md" for name in PAGES)]
        for doc in docs:
            for link in re.findall(r"\]\(([^)]+)\)", doc.read_text(encoding="utf-8")):
                if "://" in link or link.startswith("#"):
                    continue
                self.assertTrue((doc.parent / link.split("?", 1)[0].split("#", 1)[0]).exists(), (doc, link))


class ProjectReportBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        browser = BROWSER.find_browser(None)
        if not browser:
            raise unittest.SkipTest("本机无Chromium；布局not-run")
        cls.resources = ExitStack()
        cls.addClassCleanup(cls.resources.close)
        cls.workspace = Path(cls.resources.enter_context(tempfile.TemporaryDirectory(prefix="project-report-assets-", ignore_cleanup_errors=True)))
        shutil.copytree(HTML, cls.workspace / "html")
        files, _ = build()
        for relative, content in files.items():
            path = cls.workspace / "deck" / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        cls.base = cls.resources.enter_context(BROWSER.LocalArtifactServer(cls.workspace)) + "/"
        cls.session = cls.resources.enter_context(BROWSER.ChromiumSession(browser, timeout=30, sandbox=not sys.platform.startswith("linux")))

    def setUp(self):
        self.session.viewport(1366, 900, "screen")
        self.session.navigate(self.base + "html/examples/project-progress/index.html")

    def evaluate(self, expression):
        return self.session.evaluate(expression)

    def settle(self):
        self.evaluate("new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))")

    def test_filled_preview_reflows_and_long_titles_remain_readable(self):
        self.evaluate("document.querySelector('.sp-workstream-research h2').textContent='接口设计与 Observable Execution：复杂输入条件下的长标题验证'")
        for width in (320, 390, 768, 1366):
            self.session.viewport(width, 900, "screen")
            self.settle()
            result = self.evaluate("({width:innerWidth,scroll:document.documentElement.scrollWidth,font:Math.min(...[...document.querySelectorAll('.ex-report-page p')].map(p=>parseFloat(getComputedStyle(p).fontSize)))})")
            self.assertLessEqual(result["scroll"], width + 1, result)
            self.assertGreaterEqual(result["font"], 14)
        typo = self.evaluate("[document.querySelector('.sp-workstream-research h2'),document.querySelector('.ex-report-research__result')].map(e=>({size:getComputedStyle(e).fontSize,weight:getComputedStyle(e).fontWeight,left:e.getBoundingClientRect().left}))")
        self.assertEqual(typo[0], typo[1])

    def test_one_three_five_items_and_native_progress_boundaries(self):
        self.evaluate("window.question=document.querySelector('.ex-report-research__questions').firstElementChild.outerHTML;window.planRow=document.querySelector('.ex-plan-table tbody').firstElementChild.outerHTML;window.stage=document.querySelector('.ex-report-status__stages').firstElementChild.outerHTML")
        for count in (1, 3, 5):
            self.evaluate(f"document.querySelector('.ex-report-research__questions').innerHTML=window.question.repeat({count});document.querySelector('.ex-plan-table tbody').innerHTML=window.planRow.repeat({count});document.querySelector('.ex-report-status__stages').innerHTML=window.stage.repeat({count})")
            for width in (390, 768, 1366):
                self.session.viewport(width, 900, "screen")
                self.settle()
                self.assertLessEqual(self.evaluate("document.documentElement.scrollWidth"), width + 1)
        for value in (0, 100):
            result = self.evaluate(f"(()=>{{let p=document.querySelector('progress');p.value={value};return {{value:p.value,max:p.max,width:p.getBoundingClientRect().width}}}})()")
            self.assertEqual(result["value"], value)
            self.assertEqual(result["max"], 100)
            self.assertGreater(result["width"], 0)

    def test_actual_container_combination_and_theme_switch(self):
        self.session.navigate(self.base + "deck/index.html")
        self.settle()
        self.assertEqual(self.evaluate("document.querySelectorAll('[data-deck-page]').length"), 4)
        for width, height in ((1366, 768), (1920, 1080), (768, 1024), (390, 844)):
            self.session.viewport(width, height, "screen")
            self.evaluate("document.querySelector('[data-page-select]').value='0';document.querySelector('[data-page-select]').dispatchEvent(new Event('change'))")
            for i in range(4):
                # 使用既有导航按钮切页，不创建测试专用的显示状态。
                if i:
                    self.evaluate("document.querySelector('[data-page-next]').click()")
                self.settle()
                metrics = self.evaluate("(()=>{let p=[...document.querySelectorAll('[data-deck-page]')].find(e=>!e.hidden),r=p.firstElementChild;r.scrollTop=r.scrollHeight;return {id:p.id,width:r.clientWidth,scroll:r.scrollWidth,background:getComputedStyle(r).backgroundColor,bodyHeight:r.clientHeight,scrollHeight:r.scrollHeight,endReached:r.scrollTop+r.clientHeight>=r.scrollHeight-1}})()")
                self.assertLessEqual(metrics["scroll"], metrics["width"] + 1, metrics)
                if width >= 1200:
                    self.assertLessEqual(metrics["scrollHeight"], metrics["bodyHeight"] + 1, (width, height, metrics))
                self.assertTrue(metrics["endReached"], metrics)
                self.assertEqual(metrics["background"], "rgb(237, 244, 241)")
        self.session.navigate(self.base + "html/templates/single-page/preview/index.html?theme=editorial-green")
        self.evaluate("new Promise((resolve,reject)=>{let n=0;function check(){if(document.querySelectorAll('.preview-item').length===21)resolve(true);else if(++n>100)reject(Error('preview incomplete'));else setTimeout(check,50)}check()})")
        # 预览异步插入样式表；页面节点齐全不等于CSS已加载，不能提前把透明背景当回归。
        # 等资源成功而非等待目标颜色，样式文件失效或配色错误仍应明确失败。
        self.evaluate("""Promise.all([...document.querySelectorAll('link[rel="stylesheet"]')].map(link => {
          if (link.sheet) return Promise.resolve();
          return new Promise((resolve, reject) => {
            const timer=setTimeout(() => reject(Error('stylesheet timeout: '+link.href)), 5000);
            link.addEventListener('load', () => {clearTimeout(timer);resolve();}, {once:true});
            link.addEventListener('error', () => {clearTimeout(timer);reject(Error('stylesheet failed: '+link.href));}, {once:true});
          });
        })).then(() => document.fonts.ready)""")
        self.settle()
        colors = self.evaluate("[...document.querySelectorAll('.preview-item__page > section')].map(e=>getComputedStyle(e).backgroundColor)")
        self.assertEqual(set(colors), {"rgb(237, 244, 241)"})

    def test_local_evidence_target_and_print_natural_flow(self):
        self.evaluate("document.querySelector('.ex-claim-source a').click()")
        self.settle()
        self.assertTrue(self.evaluate("location.hash==='#trial' && !!document.getElementById('trial')"))
        self.session.navigate(self.base + "html/examples/project-progress/index.html")
        self.session.viewport(1123, 794, "print")
        values = self.evaluate("[...document.querySelectorAll('.ex-report-page')].map(e=>({height:e.clientHeight,scroll:e.scrollHeight,overflow:getComputedStyle(e).overflowY}))")
        self.assertTrue(all(x["scroll"] <= x["height"] + 1 and x["overflow"] != "hidden" for x in values), values)


if __name__ == "__main__":
    unittest.main()
