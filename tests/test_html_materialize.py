"""HTML 模板与组件物料化的 submodule 锁定、预览和写入安全测试。"""

from __future__ import annotations

from html.parser import HTMLParser
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL = Path("infrastructure/html/tools/materialize/materialize_html.py")
SUBMODULE = Path("vendor/suanhai-team-external-expression-infrastructure")
TASK_ID = "EXPR-20261031-1234abcd"
PUBLIC_URL = "https://github.com/suanhaitech/suanhai-team-external-expression-infrastructure.git"
TEMPLATE_ID = "html.project-report-v1"
PRESENTATION_TEMPLATE_ID = "html.presentation-deck-v1"
PRESENTATION_CONTAINER_ID = "html.container.presentation-deck-v1"
SINGLE_PAGE_IDS = (
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
)
COMPONENT_ID = "html.semantic-components-v1"
RUNTIME_KIT_ID = "html.runtime-kit-v1"


def environment() -> dict[str, str]:
    return {
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUTF8": "1",
        "GIT_ALLOW_PROTOCOL": "file",
        "GIT_TERMINAL_PROMPT": "0",
    }


def git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=environment(),
    )
    if result.returncode:
        raise AssertionError(result.stderr or result.stdout)
    return result.stdout.strip()


class HtmlMaterializeIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_temp = tempfile.TemporaryDirectory(prefix="html-materialize-source-")
        cls.addClassCleanup(cls.source_temp.cleanup)
        cls.source = Path(cls.source_temp.name) / "infrastructure"
        cls.source.mkdir()
        git(cls.source, "init", "--initial-branch=main")
        git(cls.source, "config", "user.name", "HTML Materialize Test")
        git(cls.source, "config", "user.email", "test@example.invalid")
        git(cls.source, "config", "core.autocrlf", "false")

        shutil.copytree(REPO_ROOT / "infrastructure/html", cls.source / "infrastructure/html")
        shutil.copytree(REPO_ROOT / "scenarios", cls.source / "scenarios")
        page_fragment = cls.source / "infrastructure/html/templates/single-page/content/sample-v1"
        page_fragment.mkdir(parents=True)
        (page_fragment / "template.yml").write_text(
            "id: html.page.content.sample-v1\nversion: 1.0.0\nentrypoint: page.html\n",
            encoding="utf-8",
        )
        (page_fragment / "page.html").write_text(
            '<section data-page-template="content">测试片段</section>\n', encoding="utf-8"
        )
        (cls.source / "manifest.yml").write_text(
            "schema_version: 2\n"
            "repository: suanhai-team-external-expression-infrastructure\n"
            "capabilities:\n"
            "  - id: html.project-report-v1\n"
            "    kind: template\n"
            "    path: infrastructure/html/templates/presets/project-report-v1\n"
            "    entrypoint: infrastructure/html/templates/presets/project-report-v1/index.html\n"
            "    purpose: test\n"
            "  - id: html.presentation-deck-v1\n"
            "    kind: template\n"
            "    path: infrastructure/html/templates/presets/presentation-deck-v1\n"
            "    entrypoint: infrastructure/html/templates/presets/presentation-deck-v1/index.html\n"
            "    purpose: test\n"
            "  - id: html.container.presentation-deck-v1\n"
            "    kind: template\n"
            "    path: infrastructure/html/templates/containers/presentation-deck-v1\n"
            "    entrypoint: infrastructure/html/templates/containers/presentation-deck-v1/index.html\n"
            "    purpose: test\n"
            "  - id: html.page.content.sample-v1\n"
            "    kind: template\n"
            "    path: infrastructure/html/templates/single-page/content/sample-v1\n"
            "    entrypoint: infrastructure/html/templates/single-page/content/sample-v1/page.html\n"
            "    purpose: test\n"
            "  - id: html.container.sample-v1\n"
            "    kind: template\n"
            "    path: infrastructure/html/templates/containers/sample-v1\n"
            "    entrypoint: infrastructure/html/templates/containers/sample-v1/index.html\n"
            "    purpose: test\n"
            "  - id: html.preset-rogue-v1\n"
            "    kind: template\n"
            "    path: infrastructure/html/templates/presets-rogue/sample-v1\n"
            "    entrypoint: infrastructure/html/templates/presets-rogue/sample-v1/index.html\n"
            "    purpose: test\n"
            "  - id: html.semantic-components-v1\n"
            "    kind: template\n"
            "    path: infrastructure/html/components/core-v1\n"
            "    entrypoint: infrastructure/html/components/core-v1/README.md\n"
            "    purpose: test\n"
            "  - id: html.responsive-layout-v1\n"
            "    kind: template\n"
            "    path: infrastructure/html/styles/responsive-v1\n"
            "    entrypoint: infrastructure/html/styles/responsive-v1/styles.css\n"
            "    purpose: test\n"
            "  - id: html.runtime-kit-v1\n"
            "    kind: template\n"
            "    path: infrastructure/html/runtime-kits/runtime-kit-v1\n"
            "    entrypoint: infrastructure/html/runtime-kits/runtime-kit-v1/runtime.js\n"
            "    purpose: test\n"
            "  - id: html.image-viewer-v1\n"
            "    kind: template\n"
            "    path: infrastructure/html/runtime-kits/image-viewer-v1\n"
            "    entrypoint: infrastructure/html/runtime-kits/image-viewer-v1/runtime.js\n"
            "    purpose: test\n"
            "  - id: html.materialize\n"
            "    kind: tool\n"
            "    path: infrastructure/html/tools/materialize\n"
            "    entrypoint: infrastructure/html/tools/materialize/materialize_html.py\n"
            "    purpose: test\n",
            encoding="utf-8",
        )
        page_paths = {
            "html.single-page.cover.editorial-v1": "cover/editorial-v1",
            "html.single-page.agenda.route-v1": "agenda/route-v1",
            "html.single-page.transition.statement-v1": "transition/statement-v1",
            "html.single-page.content.evidence-v1": "content/evidence-v1",
            "html.single-page.content.method-v1": "content/method-v1",
            "html.single-page.content.project-overview-v1": "content/project-overview-v1",
            "html.single-page.content.workstream-update-v1": "content/workstream-update-v1",
            "html.single-page.content.dependencies-v1": "content/dependencies-v1",
            "html.single-page.closing.action-v1": "closing/action-v1",
            "html.single-page.appendix.source-register-v1": "appendix/source-register-v1",
        }
        manifest_path = cls.source / "manifest.yml"
        manifest_text = manifest_path.read_text(encoding="utf-8")
        page_capabilities = "".join(
            f"  - id: {page_id}\n"
            "    kind: template\n"
            f"    path: infrastructure/html/templates/single-page/{page_path}\n"
            f"    entrypoint: infrastructure/html/templates/single-page/{page_path}/page.html\n"
            "    purpose: test\n"
            for page_id, page_path in page_paths.items()
        )
        manifest_text = manifest_text.replace("  - id: html.semantic-components-v1\n", page_capabilities + "  - id: html.semantic-components-v1\n")
        manifest_path.write_text(manifest_text, encoding="utf-8")
        git(cls.source, "add", ".")
        git(cls.source, "commit", "-m", "test infrastructure snapshot")
        cls.source_commit = git(cls.source, "rev-parse", "HEAD")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="html-materialize-consumer-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "consumer"
        self.root.mkdir()
        git(self.root, "init", "--initial-branch=main")
        git(self.root, "config", "user.name", "HTML Consumer Test")
        git(self.root, "config", "user.email", "test@example.invalid")
        git(self.root, "config", "core.autocrlf", "false")
        (self.root / "README.md").write_text("consumer fixture\n", encoding="utf-8")
        git(self.root, "add", "README.md")
        git(self.root, "commit", "-m", "initial consumer")
        git(self.root, "submodule", "add", str(self.source), SUBMODULE.as_posix())
        section = "submodule.vendor/suanhai-team-external-expression-infrastructure"
        git(self.root, "config", "--file", ".gitmodules", f"{section}.url", PUBLIC_URL)
        git(self.root, "add", ".gitmodules", SUBMODULE.as_posix())
        git(self.root, "commit", "-m", "pin infrastructure")
        self.infrastructure = self.root / SUBMODULE
        self.output = self.root / "reports" / TASK_ID / "v001"
        (self.root / "tasks" / TASK_ID).mkdir(parents=True)
        task = {
            "schema_version": 1,
            "id": TASK_ID,
            "status": "working",
            "revision": 1,
            "version": 4,
            "infrastructure_commit": self.source_commit,
            "brief": {
                "output": f"reports/{TASK_ID}",
                "audience": "内部评审者",
                "purpose": "验证 HTML 页面骨架物料化",
            },
        }
        (self.root / "tasks" / TASK_ID / "task.json").write_text(
            json.dumps(task, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    def cli(self, *arguments: str, ok: bool = True, template_id: str | None = TEMPLATE_ID) -> dict:
        script = self.infrastructure / TOOL
        template_arguments = ["--template-id", template_id] if template_id else []
        result = subprocess.run(
            [sys.executable, str(script), "--root", str(self.root), "--task-id", TASK_ID,
             *template_arguments, *( ["--component-id", COMPONENT_ID] if template_id else []), *arguments],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=environment(),
        )
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            return json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0, "预期工具拒绝不安全输入")
        return json.loads(result.stderr)

    def test_page_plan_cli_binds_preview_and_derives_only_target_page(self):
        plan_file = self.root / "tasks" / TASK_ID / "page-plan.json"
        document = {"schema_version": 1, "sources": [], "pages": [
            {"id": "page-one", "template_id": SINGLE_PAGE_IDS[4], "title": "第一页", "objective": "解释", "core_message": "方法"},
            {"id": "page-two", "template_id": SINGLE_PAGE_IDS[4], "title": "第二页", "objective": "迁移", "core_message": "练习", "notes": "默认隐藏备注"},
        ]}
        def save():
            plan_file.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
        save()
        arguments = ["--container-id", PRESENTATION_CONTAINER_ID, "--page-plan", plan_file.relative_to(self.root).as_posix()]
        preview = self.cli(*arguments, template_id=None)
        document["pages"][1]["title"] = "第二页修订"
        save()
        rejected = self.cli(*arguments, "--apply", "--expect-plan-sha256", preview["plan_sha256"], "--expect-task-version", "4", template_id=None, ok=False)
        self.assertIn("计划摘要不匹配", rejected["error"])
        preview = self.cli(*arguments, template_id=None)
        self.cli(*arguments, "--apply", "--expect-plan-sha256", preview["plan_sha256"], "--expect-task-version", "4", template_id=None)
        baseline = (self.output / "index.html").read_bytes()
        task_file = self.root / "tasks" / TASK_ID / "task.json"
        task = json.loads(task_file.read_text(encoding="utf-8"))
        task.update(revision=2, version=5)
        task_file.write_text(json.dumps(task), encoding="utf-8")
        document["pages"][1]["title"] = "第三次局部改进"
        save()
        arguments += ["--baseline-version", "v001", "--replace-page", "page-two"]
        preview = self.cli(*arguments, template_id=None)
        self.cli(*arguments, "--apply", "--expect-plan-sha256", preview["plan_sha256"], "--expect-task-version", "5", template_id=None)
        self.assertEqual((self.output / "index.html").read_bytes(), baseline)
        new_output = self.output.parent / "v002"
        self.assertIn("第三次局部改进", (new_output / "index.html").read_text(encoding="utf-8"))
        metadata = json.loads((new_output / "materialization.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["revision_source"]["preserved_pages"], ["page-one"])

    def test_dry_run_then_apply_copies_assets_and_records_provenance(self):
        before = git(self.root, "status", "--porcelain")
        preview = self.cli()
        self.assertEqual(preview["mode"], "dry-run")
        self.assertEqual(preview["written"], [])
        self.assertIn(f"reports/{TASK_ID}/v001/index.html", preview["would_write"])
        self.assertIn("reports/" + TASK_ID + "/v001/assets/html-semantic-components-v1/styles.css", preview["would_write"])
        self.assertEqual(git(self.root, "status", "--porcelain"), before)
        self.assertFalse(self.output.exists())

        applied = self.cli(
            "--apply",
            "--expect-plan-sha256", preview["plan_sha256"],
            "--expect-task-version", str(preview["task_record_version"]),
        )
        self.assertEqual(applied["written"], preview["would_write"])
        html = (self.output / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="assets/html-semantic-components-v1/styles.css"', html)
        self.assertIn('data-component="status.phase"', html)
        self.assertIn('data-component="action.next-step"', html)
        self.assertTrue((self.output / "assets/html-semantic-components-v1/semantic/status/phase/template.html").is_file())
        record = json.loads((self.output / "materialization.json").read_text(encoding="utf-8"))
        self.assertEqual(record["infrastructure"]["commit"], self.source_commit)
        self.assertEqual(record["template"]["id"], TEMPLATE_ID)
        self.assertEqual(record["components"][0]["id"], COMPONENT_ID)
        self.assertTrue(all(len(item["sha256"]) == 64 for item in record["files"]))
        self.assertIn("report.yml", {item["path"] for item in record["files"]})
        self.assertNotIn("materialization.json", {item["path"] for item in record["files"]})
        report = (self.output / "report.yml").read_text(encoding="utf-8")
        self.assertIn('template: "html.project-report-v1"', report)
        self.assertIn('audience: "内部评审者"', report)
        self.assertIn("layouts: []", report)
        self.assertIn('"html.runtime-kit-v1"', report)
        self.assertIn('"html.image-viewer-v1"', report)
        self.assertEqual([kit["id"] for kit in record["runtime_kits"]], ["html.runtime-kit-v1", "html.image-viewer-v1"])
        self.assertIn('tool: html.materialize', report)

    def test_presentation_deck_template_is_materialized_as_a_self_contained_deck(self):
        preview = self.cli("--runtime-kit-id", RUNTIME_KIT_ID, template_id=PRESENTATION_TEMPLATE_ID)
        expected = {
            f"reports/{TASK_ID}/v001/index.html",
            f"reports/{TASK_ID}/v001/styles.css",
            f"reports/{TASK_ID}/v001/deck.css",
            f"reports/{TASK_ID}/v001/deck.js",
        }
        self.assertTrue(expected.issubset(set(preview["would_write"])))
        applied = self.cli(
            "--runtime-kit-id", RUNTIME_KIT_ID,
            "--apply",
            "--expect-plan-sha256", preview["plan_sha256"],
            "--expect-task-version", str(preview["task_record_version"]),
            template_id=PRESENTATION_TEMPLATE_ID,
        )
        record = json.loads((self.output / "materialization.json").read_text(encoding="utf-8"))
        self.assertEqual(record["template"]["id"], PRESENTATION_TEMPLATE_ID)
        html = (self.output / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="deck.css"', html)
        self.assertIn('src="deck.js"', html)
        self.assertIn('data-page-prev', html)
        self.assertIn('data-page-select', html)
        self.assertIn('data-page-next', html)
        self.assertIn('data-deck-page', html)
        self.assertIn('href="assets/html-runtime-kit-v1/runtime.css"', html)
        self.assertFalse("https://" in html or "http://" in html)

    def test_single_pages_compose_in_order_and_repeat_without_duplicate_assets_or_ids(self):
        page_ids = [
            SINGLE_PAGE_IDS[0],
            SINGLE_PAGE_IDS[1],
            SINGLE_PAGE_IDS[3],
            SINGLE_PAGE_IDS[3],
            SINGLE_PAGE_IDS[5],
        ]
        arguments = ["--container-id", PRESENTATION_CONTAINER_ID]
        for page_id in page_ids:
            arguments.extend(("--page-id", page_id))
        arguments.extend(("--runtime-kit-id", RUNTIME_KIT_ID))
        preview = self.cli(*arguments, template_id=None)
        self.assertEqual([page["id"] for page in preview["pages"]], page_ids)
        self.assertEqual([page["order"] for page in preview["pages"]], [1, 2, 3, 4, 5])
        self.assertEqual(len(preview["would_write"]), len(set(preview["would_write"])))
        self.assertIn(
            f"reports/{TASK_ID}/v001/assets/html-single-page-content-evidence-v1/styles.css",
            preview["would_write"],
        )

        applied = self.cli(
            *arguments,
            "--apply", "--expect-plan-sha256", preview["plan_sha256"],
            "--expect-task-version", str(preview["task_record_version"]),
            template_id=None,
        )
        html = (self.output / "index.html").read_text(encoding="utf-8")
        record = json.loads((self.output / "materialization.json").read_text(encoding="utf-8"))
        report = (self.output / "report.yml").read_text(encoding="utf-8")
        self.assertEqual(applied["pages"], preview["pages"])
        self.assertEqual([page["id"] for page in record["pages"]], page_ids)
        self.assertEqual(html.count("data-deck-page"), len(page_ids))
        self.assertEqual(len(set(re.findall(r'id="(slide-\d{2})"', html))), len(page_ids))
        self.assertNotIn("SUANHAI_DECK_PAGES", html)
        self.assertNotIn("SUANHAI_PAGE_STYLESHEETS", html)
        self.assertNotIn("SUANHAI_PAGE_NUMBER", html)
        self.assertEqual(html.count("html-single-page-content-evidence-v1/styles.css"), 1)
        self.assertEqual(html.count('class="deck-page-number"'), len(page_ids))
        self.assertIn('href="assets/html-runtime-kit-v1/runtime.css"', html)
        self.assertIn('src="assets/html-runtime-kit-v1/runtime.js"', html)
        self.assertIn(f'"{page_ids[0]}"', report)
        self.assertIn("components: []", report)
        self.assertIn("semantic_components: []", report)

    def test_write_failure_reports_exception_type_phase_and_target(self):
        module_path = REPO_ROOT / TOOL
        spec = importlib.util.spec_from_file_location("materialize_html_under_test", module_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        materializer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(materializer)

        with tempfile.TemporaryDirectory(prefix="html-materialize-write-error-") as temporary:
            root = Path(temporary)
            destination = root / "reports" / "v001" / "broken.html"
            original_open = Path.open

            def fail_destination(path: Path, mode: str = "r", *args, **kwargs):
                if path == destination and mode == "xb":
                    raise MemoryError()
                return original_open(path, mode, *args, **kwargs)

            with patch.object(Path, "open", fail_destination):
                with self.assertRaises(materializer.MaterializeError) as raised:
                    materializer.apply_files(root, [(destination, b"content")])

            message = str(raised.exception)
            self.assertIn("创建目标文件：reports/v001/broken.html", message)
            self.assertIn("MemoryError", message)
            self.assertIn("MemoryError()", message)
            self.assertIn("本次写入已回滚", message)
            self.assertFalse(destination.exists())
            self.assertEqual(list(root.glob(".html-materialize-*")), [])

    def test_repeated_single_page_apply_rolls_back_and_can_retry_after_write_failure(self):
        page_ids = [
            SINGLE_PAGE_IDS[0],
            SINGLE_PAGE_IDS[3],
            SINGLE_PAGE_IDS[3],
            SINGLE_PAGE_IDS[5],
        ]
        arguments = ["--container-id", PRESENTATION_CONTAINER_ID]
        for page_id in page_ids:
            arguments.extend(("--page-id", page_id))
        preview = self.cli(*arguments, template_id=None)
        self.assertGreater(len(preview["would_write"]), 1)

        module_path = REPO_ROOT / TOOL
        spec = importlib.util.spec_from_file_location("materialize_html_cli_under_test", module_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        materializer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(materializer)
        manifest = materializer.parse_manifest(self.infrastructure / "manifest.yml")
        commit = git(self.infrastructure, "rev-parse", "HEAD")
        task = materializer.read_task_context(self.root, TASK_ID, commit)
        package, _ = materializer.build_plan(
            self.infrastructure,
            manifest,
            None,
            COMPONENT_ID,
            [],
            None,
            [],
            TASK_ID,
            task["version_name"],
            task["revision"],
            task["version"],
            commit,
            task,
            [],
            PRESENTATION_CONTAINER_ID,
            page_ids,
            None,
            None,
            None,
        )
        writes, unchanged, conflicts = materializer.plan_materialization(self.root, self.output, package)
        self.assertFalse(unchanged)
        self.assertFalse(conflicts)
        self.assertEqual(len(writes), len(preview["would_write"]))
        failing_relative = writes[-1][0].relative_to(self.root).as_posix()
        failing_path = self.root / failing_relative
        original_copyfileobj = materializer.shutil.copyfileobj

        def fail_one_target(source, destination, length=0):
            if Path(destination.name) == failing_path:
                raise MemoryError()
            return original_copyfileobj(source, destination, length)

        with patch.object(materializer.shutil, "copyfileobj", fail_one_target):
            with self.assertRaises(materializer.MaterializeError) as raised:
                materializer.apply_files(self.root, writes)

        error = str(raised.exception)
        self.assertIn("复制暂存文件", error)
        self.assertIn(failing_relative, error)
        self.assertIn("MemoryError", error)
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.root.glob(".html-materialize-*")), [])

        materializer.apply_files(self.root, writes)
        self.assertEqual(len(writes), len(preview["would_write"]))
        self.assertTrue(self.output.joinpath("index.html").is_file())

    def test_project_report_composition_preserves_provenance_and_repeated_page_references(self):
        scenario_id = "expression.scenario.project-progress-communication-v1"
        # 验证物料化记录追溯到固定基础设施的实际版本，正常升版不应让断言失效。
        catalog = json.loads((self.infrastructure / "scenarios/catalog.json").read_text(encoding="utf-8"))
        scenario_version = next(item["version"] for item in catalog["scenarios"] if item["id"] == scenario_id)
        page_ids = [
            "html.single-page.cover.editorial-v1",
            "html.single-page.content.project-overview-v1",
            "html.single-page.content.workstream-update-v1",
            "html.single-page.content.workstream-update-v1",
            "html.single-page.content.dependencies-v1",
            "html.single-page.closing.action-v1",
            "html.single-page.appendix.source-register-v1",
        ]
        arguments = ["--container-id", PRESENTATION_CONTAINER_ID, "--scenario-id", scenario_id]
        for page_id in page_ids:
            arguments.extend(("--page-id", page_id))
        arguments.extend(("--source-id", "synthetic-project-report"))

        preview = self.cli(*arguments, template_id=None)
        self.assertFalse(self.output.exists())
        self.assertEqual([page["id"] for page in preview["pages"]], page_ids)
        self.assertEqual(preview["scenario"]["id"], scenario_id)
        self.assertEqual(preview["scenario"]["version"], scenario_version)
        applied = self.cli(
            *arguments,
            "--apply", "--expect-plan-sha256", preview["plan_sha256"],
            "--expect-task-version", str(preview["task_record_version"]),
            template_id=None,
        )
        self.assertEqual(applied["pages"], preview["pages"])
        self.assertEqual(applied["written"], preview["would_write"])
        record = json.loads((self.output / "materialization.json").read_text(encoding="utf-8"))
        self.assertEqual(record["scenario"], preview["scenario"])
        self.assertEqual(record["infrastructure"]["commit"], self.source_commit)
        self.assertEqual([page["id"] for page in record["pages"]], page_ids)
        self.assertEqual([page["order"] for page in record["pages"]], list(range(1, len(page_ids) + 1)))

        # 重复主线是两个内容实例，必须有各自的 ID 和标签引用；样式资源则仍共用一份。
        class References(HTMLParser):
            def __init__(self):
                super().__init__()
                self.nodes = []

            def handle_starttag(self, tag, attrs):
                self.nodes.append((tag, dict(attrs)))

        parser = References()
        parser.feed((self.output / "index.html").read_text(encoding="utf-8"))
        ids = [attrs["id"] for _, attrs in parser.nodes if "id" in attrs]
        self.assertEqual(len(ids), len(set(ids)))
        label_targets = [
            target
            for _, attrs in parser.nodes
            for target in attrs.get("aria-labelledby", "").split()
        ]
        self.assertGreaterEqual(len(label_targets), len(page_ids))
        self.assertTrue(set(label_targets).issubset(ids), set(label_targets) - set(ids))
        self.assertEqual(
            [attrs["id"] for _, attrs in parser.nodes if "data-deck-page" in attrs],
            [f"slide-{order:02d}" for order in range(1, len(page_ids) + 1)],
        )
        self.assertEqual(
            [attrs["data-single-page-role"] for _, attrs in parser.nodes if "data-single-page-role" in attrs],
            [page["role"] for page in record["pages"]],
        )
        self.assertEqual(
            [attrs["data-single-page-variant"] for _, attrs in parser.nodes if "data-single-page-variant" in attrs],
            [page["variant"] for page in record["pages"] if page["role"] == "content"],
        )
        workstream_css = "assets/html-single-page-content-workstream-update-v1/styles.css"
        self.assertEqual(
            sum(attrs.get("href") == workstream_css for tag, attrs in parser.nodes if tag == "link"), 1
        )
        self.assertEqual(sum(item["path"] == workstream_css for item in record["files"]), 1)
        self.assertTrue((self.output / workstream_css).is_file())
        for page in record["pages"]:
            with self.subTest(page=page["destination"]):
                self.assertTrue((self.infrastructure / page["source"]).is_dir())
                self.assertTrue((self.infrastructure / page["entrypoint"]).is_file())
                self.assertEqual(page["entrypoint"], page["source"] + "/page.html")
                self.assertEqual(page["destination"], f"index.html#slide-{page['order']:02d}")

        report = (self.output / "report.yml").read_text(encoding="utf-8")
        page_block = re.search(r"(?ms)^pages:\n(.*?)^components:", report)
        self.assertIsNotNone(page_block)
        self.assertEqual(
            [json.loads(value) for value in re.findall(r"(?m)^  - (.+)$", page_block.group(1))], page_ids
        )
        self.assertIn(f'id: "{scenario_id}"', report)
        self.assertIn(f'version: "{scenario_version}"', report)
        self.assertIn('profile: "scenarios/project-progress-communication-v1/README.md"', report)
        self.assertIn('  - "synthetic-project-report"', report)
        self.assertIn(f'infrastructure_commit: "{self.source_commit}"', report)

    def test_single_page_selection_requires_a_container_and_old_preset_mode_stays_explicit(self):
        missing_container = self.cli("--page-id", SINGLE_PAGE_IDS[0], ok=False)
        self.assertIn("--page-id 只能与 --container-id 一起使用", missing_container["error"])
        unknown_page = self.cli("--container-id", PRESENTATION_CONTAINER_ID, "--page-id", "html.single-page.missing-v1", ok=False, template_id=None)
        self.assertIn("没有登记单页模板", unknown_page["error"])
        rejected_component = self.cli(
            "--container-id", PRESENTATION_CONTAINER_ID,
            "--page-id", SINGLE_PAGE_IDS[0], "--component-id", "action.next-step",
            ok=False, template_id=None,
        )
        self.assertIn("暂不接受 --component-id", rejected_component["error"])

    def test_registered_scenario_is_written_to_report_and_materialization_provenance(self):
        scenario_id = "expression.scenario.course-learning-v1"
        preview = self.cli("--scenario-id", scenario_id)
        self.assertEqual(preview["scenario"]["id"], scenario_id)
        applied = self.cli(
            "--scenario-id", scenario_id,
            "--apply", "--expect-plan-sha256", preview["plan_sha256"],
            "--expect-task-version", str(preview["task_record_version"]),
        )
        record = json.loads((self.output / "materialization.json").read_text(encoding="utf-8"))
        self.assertEqual(record["scenario"]["id"], scenario_id)
        self.assertEqual(record["scenario"]["profile"], "scenarios/course-learning-v1/README.md")
        report = (self.output / "report.yml").read_text(encoding="utf-8")
        self.assertIn(f'id: "{scenario_id}"', report)
        self.assertIn('profile: "scenarios/course-learning-v1/README.md"', report)
        self.assertLess(report.index("components:"), report.index("scenario:"))
        self.assertIn('  - "status.phase"', report)
        self.assertIn('  - "action.next-step"', report)

    def test_unknown_or_unimplemented_scenario_is_rejected(self):
        result = self.cli("--scenario-id", "expression.scenario.not-registered-v1", ok=False)
        self.assertIn("没有唯一登记该场景", result["error"])
        self.assertFalse(self.output.exists())

    def test_only_complete_presets_are_accepted_by_template_id(self):
        for capability_id in (
            "html.page.content.sample-v1",
            "html.container.sample-v1",
            "html.preset-rogue-v1",
        ):
            with self.subTest(capability_id=capability_id):
                error = self.cli(ok=False, template_id=capability_id)
                self.assertIn("presets/ 下的完整组合预设", error["error"])

    def test_layout_package_is_materialized_and_linked(self):
        preview = self.cli("--layout-id", "html.responsive-layout-v1")
        self.assertIn(
            f"reports/{TASK_ID}/v001/assets/html-responsive-layout-v1/styles.css",
            preview["would_write"],
        )
        applied = self.cli(
            "--layout-id", "html.responsive-layout-v1",
            "--apply",
            "--expect-plan-sha256", preview["plan_sha256"],
            "--expect-task-version", str(preview["task_record_version"]),
        )
        self.assertEqual(applied["layouts"][0]["id"], "html.responsive-layout-v1")
        html = (self.output / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="assets/html-responsive-layout-v1/styles.css"', html)
        self.assertTrue((self.output / "assets/html-responsive-layout-v1/media.css").is_file())
        record = json.loads((self.output / "materialization.json").read_text(encoding="utf-8"))
        self.assertEqual(record["layouts"][0]["id"], "html.responsive-layout-v1")

    def test_runtime_kit_is_materialized_with_offline_assets_and_controls(self):
        preview = self.cli("--runtime-kit-id", RUNTIME_KIT_ID)
        self.assertEqual(preview["runtime_kits"][0]["id"], RUNTIME_KIT_ID)
        runtime_root = f"reports/{TASK_ID}/v001/assets/html-runtime-kit-v1"
        expected = {
            f"{runtime_root}/runtime.css",
            f"{runtime_root}/runtime.js",
            f"{runtime_root}/math/katex.min.css",
            f"{runtime_root}/math/katex.min.js",
            f"{runtime_root}/math/LICENSE",
            f"{runtime_root}/math/fonts/KaTeX_Main-Regular.woff2",
        }
        self.assertTrue(expected.issubset(set(preview["would_write"])))

        applied = self.cli(
            "--runtime-kit-id", RUNTIME_KIT_ID,
            "--apply",
            "--expect-plan-sha256", preview["plan_sha256"],
            "--expect-task-version", str(preview["task_record_version"]),
        )
        self.assertEqual(applied["runtime_kits"][0]["id"], RUNTIME_KIT_ID)
        html = (self.output / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="assets/html-runtime-kit-v1/runtime.css"', html)
        self.assertIn('href="assets/html-runtime-kit-v1/math/katex.min.css"', html)
        self.assertIn('src="assets/html-runtime-kit-v1/math/katex.min.js"', html)
        self.assertIn('src="assets/html-runtime-kit-v1/runtime.js"', html)
        self.assertIn('data-runtime-toolbar', html)
        self.assertTrue((self.output / "assets/html-runtime-kit-v1/math/LICENSE").is_file())
        self.assertTrue((self.output / "assets/html-runtime-kit-v1/math/fonts/KaTeX_Main-Regular.woff2").is_file())
        record = json.loads((self.output / "materialization.json").read_text(encoding="utf-8"))
        self.assertEqual(record["runtime_kits"][0]["id"], RUNTIME_KIT_ID)
        self.assertEqual(record["runtime_kits"][0]["version"], "1.1.0")
        report = (self.output / "report.yml").read_text(encoding="utf-8")
        self.assertIn('runtime_kits:', report)
        self.assertIn('"html.runtime-kit-v1"', report)

    def test_runtime_kit_selection_is_idempotent(self):
        preview = self.cli("--runtime-kit-id", RUNTIME_KIT_ID)
        args = (
            "--runtime-kit-id", RUNTIME_KIT_ID,
            "--apply", "--expect-plan-sha256", preview["plan_sha256"],
            "--expect-task-version", str(preview["task_record_version"]),
        )
        first = self.cli(*args)
        self.assertTrue(first["written"])
        second = self.cli(*args)
        self.assertEqual(second["written"], [])
        self.assertEqual(set(second["unchanged"]), set(preview["would_write"]))

    def test_apply_requires_matching_preview_and_task_versions(self):
        missing = self.cli("--apply", ok=False)
        self.assertIn("--expect-plan-sha256", missing["error"])
        preview = self.cli()
        mismatch = self.cli(
            "--apply", "--expect-plan-sha256", "0" * 64,
            "--expect-task-version", str(preview["task_record_version"]), ok=False,
        )
        self.assertIn("计划摘要不匹配", mismatch["error"])
        self.assertFalse(self.output.exists())

    def test_apply_is_idempotent_but_refuses_changed_materialized_files(self):
        preview = self.cli()
        args = (
            "--apply", "--expect-plan-sha256", preview["plan_sha256"],
            "--expect-task-version", str(preview["task_record_version"]),
        )
        first = self.cli(*args)
        self.assertTrue(first["written"])
        second = self.cli(*args)
        self.assertEqual(second["written"], [])
        self.assertEqual(set(second["unchanged"]), set(preview["would_write"]))
        (self.output / "index.html").write_text("user edit\n", encoding="utf-8")
        changed = self.cli(*args, ok=False)
        self.assertIn("已有不同内容", changed["error"])
        self.assertEqual((self.output / "index.html").read_text(encoding="utf-8"), "user edit\n")

    def test_all_conflicts_are_detected_before_any_file_is_written(self):
        self.output.mkdir(parents=True)
        (self.output / "report.css").write_text("user-owned\n", encoding="utf-8")
        result = self.cli(ok=False)
        self.assertIn("没有写入文件", result["error"])
        self.assertFalse((self.output / "index.html").exists())
        self.assertEqual((self.output / "report.css").read_text(encoding="utf-8"), "user-owned\n")

    def test_task_must_be_working_and_output_must_match_revision(self):
        task_path = self.root / "tasks" / TASK_ID / "task.json"
        task = json.loads(task_path.read_text(encoding="utf-8"))
        task["status"] = "ready"
        task_path.write_text(json.dumps(task), encoding="utf-8")
        result = self.cli(ok=False)
        self.assertIn("working", result["error"])
        task["status"] = "working"
        task["brief"]["output"] = f"reports/{TASK_ID}/v002"
        task_path.write_text(json.dumps(task), encoding="utf-8")
        result = self.cli(ok=False)
        self.assertIn("当前修订", result["error"])

    def test_custom_output_root_requires_consumer_configuration(self):
        task_path = self.root / "tasks" / TASK_ID / "task.json"
        task = json.loads(task_path.read_text(encoding="utf-8"))
        task["brief"]["output"] = f"web/{TASK_ID}/v001"
        task_path.write_text(json.dumps(task), encoding="utf-8")
        denied = self.cli(ok=False)
        self.assertIn("未允许使用作品目录 web", denied["error"])
        config = self.root / ".suanhai/expression.json"
        config.parent.mkdir()
        config.write_text(json.dumps({"schema_version": 1, "output_roots": ["web"]}), encoding="utf-8")
        allowed = self.cli()
        self.assertEqual(allowed["output"], f"web/{TASK_ID}/v001")

    def test_custom_submodule_path_is_supported(self):
        custom = Path("custom location") / "infrastructure"
        (self.root / custom.parent).mkdir(parents=True)
        git(self.root, "mv", SUBMODULE.as_posix(), custom.as_posix())
        section = "submodule.vendor/suanhai-team-external-expression-infrastructure"
        git(self.root, "config", "--file", ".gitmodules", f"{section}.path", custom.as_posix())
        git(self.root, "add", ".gitmodules", custom.as_posix())
        git(self.root, "commit", "-m", "move infrastructure to custom path")
        self.infrastructure = self.root / custom
        preview = self.cli("--submodule-path", custom.as_posix())
        self.assertEqual(preview["output"], f"reports/{TASK_ID}/v001")
        self.assertEqual(preview["infrastructure_commit"], self.source_commit)

    def test_manifest_and_submodule_lock_are_required(self):
        bad_id = self.cli("--template-id", "html.not-registered", ok=False)
        self.assertIn("Manifest 没有登记", bad_id["error"])
        task_path = self.root / "tasks" / TASK_ID / "task.json"
        task = json.loads(task_path.read_text(encoding="utf-8"))
        task["infrastructure_commit"] = "0" * 40
        task_path.write_text(json.dumps(task), encoding="utf-8")
        mismatch = self.cli(ok=False)
        self.assertIn("任务当前修订固定", mismatch["error"])


if __name__ == "__main__":
    unittest.main()
