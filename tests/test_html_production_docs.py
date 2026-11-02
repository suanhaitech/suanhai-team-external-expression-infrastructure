"""HTML 制作工作流和语义组件包的文件协议回归测试。"""

from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / "workflows/html/production"
COMPONENTS = ROOT / "infrastructure/html/components/core-v1"


class HtmlProductionDocumentationTest(unittest.TestCase):
    def test_workflows_and_infrastructure_are_parallel_sections(self):
        html = (ROOT / "infrastructure/html/README.md").read_text(encoding="utf-8")
        workflow = (ROOT / "workflows/html/production/WORKFLOW.md").read_text(encoding="utf-8")
        self.assertIn("主流程入口", html)
        self.assertIn("infrastructure/html/", html)
        self.assertIn("infrastructure/", workflow)
        self.assertTrue((ROOT / "workflows/html/production/ENTRYPOINT.md").is_file())
        self.assertTrue((ROOT / "infrastructure/html/templates/README.md").is_file())
        self.assertTrue((ROOT / "infrastructure/html/templates/containers/README.md").is_file())
        for role in ("cover", "transition", "content", "closing"):
            self.assertTrue((ROOT / "infrastructure/html/templates/single-page" / role / "README.md").is_file())
        self.assertTrue((ROOT / "infrastructure/html/templates/presets/README.md").is_file())
        self.assertTrue((ROOT / "infrastructure/html/templates/presets/project-report-v1/index.html").is_file())
        self.assertTrue((ROOT / "infrastructure/html/templates/presets/presentation-deck-v1/index.html").is_file())

    def test_workflow_has_protocol_entrypoint_and_forwardable_prompt(self):
        workflow = (WORKFLOW / "WORKFLOW.md").read_text(encoding="utf-8")
        entrypoint = (WORKFLOW / "ENTRYPOINT.md").read_text(encoding="utf-8")
        prompt = (WORKFLOW / "START_HTML_PRODUCTION.md").read_text(encoding="utf-8")

        self.assertIn("sources.yml", workflow)
        self.assertIn("不得自动提交", workflow)
        self.assertIn("v001", entrypoint)
        self.assertIn("sources", entrypoint)
        self.assertIn("不要一开始就写 HTML", prompt)
        self.assertIn("不要自动提交", prompt)
        self.assertIn("expression.html-production", entrypoint)
        self.assertIn("expression.task-record", workflow)

    def test_manifest_registers_workflow_and_component_package(self):
        manifest = (ROOT / "manifest.yml").read_text(encoding="utf-8")
        self.assertIn("id: expression.html-production", manifest)
        self.assertIn("entrypoint: workflows/html/production/ENTRYPOINT.md", manifest)
        self.assertIn("id: html.semantic-components-v1", manifest)
        self.assertIn("entrypoint: infrastructure/html/components/core-v1/README.md", manifest)
        self.assertIn("templates/presets/", manifest)
        self.assertNotIn("path: infrastructure/html/page-templates/", manifest)
        self.assertIn("path: infrastructure/html/templates/presets/project-report-v1", manifest)
        self.assertIn("entrypoint: infrastructure/html/templates/presets/project-report-v1/index.html", manifest)
        self.assertIn("id: html.presentation-deck-v1", manifest)
        self.assertIn("path: infrastructure/html/templates/presets/presentation-deck-v1", manifest)
        self.assertIn("entrypoint: infrastructure/html/templates/presets/presentation-deck-v1/index.html", manifest)
        self.assertIn("id: html.container.presentation-deck-v1", manifest)
        materializer = (ROOT / "infrastructure/html/tools/materialize/README.md").read_text(encoding="utf-8")
        self.assertIn("--container-id", materializer)
        self.assertIn("--page-id", materializer)
        self.assertIn("id: html.materialize", manifest)
        self.assertIn("entrypoint: infrastructure/html/tools/materialize/materialize_html.py", manifest)
        self.assertIn("id: html.responsive-layout-v1", manifest)
        self.assertIn("entrypoint: infrastructure/html/styles/responsive-v1/styles.css", manifest)
        self.assertIn("id: html.runtime-kit-v1", manifest)
        self.assertIn("entrypoint: infrastructure/html/runtime-kits/runtime-kit-v1/runtime.js", manifest)
        runtime = (ROOT / "infrastructure/html/runtime-kits/runtime-kit-v1/README.md").read_text(encoding="utf-8")
        self.assertIn("全屏模式", runtime)
        self.assertIn("保存 PDF", runtime)
        self.assertIn("id: html.viewport-check", manifest)
        self.assertIn("entrypoint: infrastructure/html/tools/viewport-check/viewport_check.py", manifest)
        self.assertIn("id: html.pdf-export", manifest)
        self.assertIn("entrypoint: infrastructure/html/tools/pdf-export/export_pdf.py", manifest)
        workflow = (WORKFLOW / "WORKFLOW.md").read_text(encoding="utf-8")
        self.assertIn("html.viewport-check", workflow)
        self.assertIn("html.pdf-export", workflow)
        deck = ROOT / "infrastructure/html/templates/presets/presentation-deck-v1"
        deck_html = (deck / "index.html").read_text(encoding="utf-8")
        deck_js = (deck / "deck.js").read_text(encoding="utf-8")
        deck_css = (deck / "deck.css").read_text(encoding="utf-8")
        self.assertIn("data-page-prev", deck_html)
        self.assertIn("data-page-select", deck_html)
        self.assertIn("data-page-next", deck_html)
        self.assertIn("data-deck-page", deck_html)
        self.assertIn("data-speaker-note", deck_html)
        self.assertIn("ArrowRight", deck_js)
        self.assertIn("PageDown", deck_js)
        self.assertIn("Home", deck_js)
        self.assertIn("data-page-prev", deck_js)
        self.assertIn("@media print", deck_css)
        self.assertIn("break-after: page", deck_css)
        self.assertIn("deck-controls", deck_css)
        self.assertNotIn("http://", deck_html + deck_js + deck_css)
        self.assertNotIn("https://", deck_html + deck_js + deck_css)

    def test_materialize_tool_and_report_schema_are_declared(self):
        tool = (ROOT / "infrastructure/html/tools/materialize/README.md").read_text(encoding="utf-8")
        schema = json.loads((ROOT / "infrastructure/html/schemas/report.schema.json").read_text(encoding="utf-8"))
        self.assertIn("--expect-plan-sha256", tool)
        self.assertIn("materialization.json", tool)
        self.assertEqual(schema["properties"]["materialization"]["properties"]["tool"]["const"], "html.materialize")
        self.assertIn("materialization", schema["required"])
        self.assertIn("pages", schema["properties"])
        self.assertEqual(schema["properties"]["components"].get("minItems"), 0)

    def test_materialized_report_metadata_is_valid_yaml_shape(self):
        fixture = ROOT / "tests/fixtures/html/materialized-report.yml"
        report = fixture.read_text(encoding="utf-8")
        self.assertIn("schema_version: 1", report)
        self.assertIn('template: "html.project-report-v1"', report)
        self.assertIn('  - "html.semantic-components-v1"', report)
        self.assertIn("  tool: html.materialize", report)

    def test_e2e_consumer_test_prompt_is_forwardable_and_pinned(self):
        doc = (ROOT / "docs/html-e2e-consumer-test.md").read_text(encoding="utf-8")
        self.assertIn("INFRA_COMMIT", doc)
        self.assertIn("--component-package-id html.semantic-components-v1", doc)
        self.assertIn("--component-id status.phase", doc)
        self.assertIn("html.viewport-check", doc)
        self.assertIn("html.pdf-export", doc)
        self.assertIn("viewport-check.json", doc)
        self.assertIn("pdf-export.json", doc)
        self.assertIn("--source-id synthetic-html-e2e", doc)
        self.assertIn("task-loop review", doc)
        self.assertIn("task-loop validate", doc)
        self.assertIn("git submodule update --remote", doc)
        self.assertIn("<测试者实际确认原话；不得由 Agent 编造>", doc)
        self.assertIn("mode: test", doc)
        self.assertIn("materialization.json", doc)
        self.assertIn("浏览器检查未执行", doc)
        self.assertIn(r'"^submodule\..*\.(path|url)$"', doc)
        self.assertNotIn(r'"^submodule\\..*\\.(path|url)$"', doc)
        self.assertIn('context/e2e-html-test/<TASK_ID>/source.md', doc)
        self.assertIn('Test-Path -LiteralPath $sourcePath', doc)
        self.assertIn('rg -n -g "*.html" -g "*.css"', doc)
        self.assertIn("以工具返回的完整清单为准", doc)
        self.assertIn("相对路径的本地 `@import` 可以保留", doc)
        self.assertIn("$rgExit -eq 0", doc)
        self.assertIn("$rgExit -gt 1", doc)

    def test_standalone_e2e_prompt_discovers_fixed_dependency(self):
        doc = (ROOT / "docs/html-e2e-consumer-test-prompt.md").read_text(encoding="utf-8")
        self.assertIn("可以从 Agent 当前打开的任意工作目录发送", doc)
        self.assertIn("D:\\Works\\Suanhaitech\\Repos", doc)
        self.assertIn("git clone --recurse-submodules", doc)
        self.assertIn("https://github.com/suanhaitech/suanhai-team-group-asset-template.git", doc)
        self.assertIn("git switch -c $testBranch", doc)
        self.assertIn("git status --short --branch", doc)
        self.assertIn("git submodule status --recursive", doc)
        self.assertIn("$consumerRoot", doc)
        self.assertIn("启动时所在目录", doc)
        self.assertIn("从 .gitmodules 解析基础设施 submodule 的实际相对路径", doc)
        self.assertIn("不执行 `git submodule update --remote`", doc)
        self.assertIn("ls-remote origin refs/heads/main", doc)
        self.assertIn("fetch origin main", doc)
        self.assertNotIn("149759f18edf54c83bdfbadf8326c3031c10bb4f", doc)
        self.assertNotIn("codex/feat-html-production-workflow", doc)
        self.assertIn("git diff --cached --submodule", doc)
        self.assertIn("--component-package-id html.semantic-components-v1", doc)
        self.assertIn("--component-id status.phase", doc)
        self.assertIn("--source-id synthetic-html-e2e", doc)
        self.assertIn("--test", doc)
        self.assertIn("--type review", doc)
        self.assertIn("validate $taskId", doc)
        self.assertIn("用户刚刚实际给出的确认原话", doc)
        self.assertIn("浏览器检查未执行", doc)
        self.assertIn('Test-Path -LiteralPath $sourcePath', doc)
        self.assertIn("相对路径的本地 `@import` 可以保留", doc)
        self.assertIn("$rgExit -eq 0", doc)
        self.assertIn("$rgExit -gt 1", doc)

    def test_component_package_is_self_contained_and_contracts_are_complete(self):
        package = (COMPONENTS / "package.yml").read_text(encoding="utf-8")
        catalog = (COMPONENTS / "index.yml").read_text(encoding="utf-8")
        example = (COMPONENTS / "examples/example.html").read_text(encoding="utf-8")
        self.assertIn("offline: true", package)
        self.assertIn("network_dependencies: []", package)
        self.assertIn("catalog: index.yml", package)
        self.assertIn("semantic/content/summary/component.yml", catalog)
        self.assertIn("semantic/status/metric/template.html", catalog)
        self.assertNotRegex(example, r"https?://|//cdn|@import")
        self.assertIn('rel="stylesheet" href="../styles.css"', example)

        contracts = sorted((COMPONENTS / "semantic/contracts").glob("*.json"))
        self.assertEqual(len(contracts), 6)
        required = {
            "id", "version", "role", "required_slots", "optional_slots",
            "states", "responsive", "accessibility",
        }
        ids = set()
        for path in contracts:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertTrue(required.issubset(data), path.name)
            self.assertNotIn(data["id"], ids)
            ids.add(data["id"])

        self.assertEqual(
            ids,
            {
                "content.summary", "status.phase", "status.metric",
                "evidence.claim", "evidence.source", "action.next-step",
            },
        )

    def test_component_css_contains_mobile_print_and_reduced_motion_rules(self):
        css = (COMPONENTS / "styles.css").read_text(encoding="utf-8")
        self.assertIn('url("layout/layout.css")', css)
        self.assertIn('url("semantic/semantic.css")', css)
        full_css = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (
                COMPONENTS / "foundations/base.css",
                COMPONENTS / "layout/layout.css",
                COMPONENTS / "semantic/semantic.css",
            )
        )
        self.assertIn("@media print", full_css)
        self.assertIn("@media (max-width: 760px)", full_css)
        self.assertIn("prefers-reduced-motion", full_css)
        self.assertIn("overflow-wrap: anywhere", full_css)

    def test_catalog_definitions_and_templates_exist_for_every_component(self):
        catalog = (COMPONENTS / "index.yml").read_text(encoding="utf-8")
        self.assertIn("schema_version: 1", catalog)
        component_ids = (
            "content.summary", "status.phase", "status.metric",
            "evidence.claim", "evidence.source", "action.next-step",
        )
        for component_id in component_ids:
            definition_marker = {
                "content.summary": "semantic/content/summary/component.yml",
                "status.phase": "semantic/status/phase/component.yml",
                "status.metric": "semantic/status/metric/component.yml",
                "evidence.claim": "semantic/evidence/claim/component.yml",
                "evidence.source": "semantic/evidence/source/component.yml",
                "action.next-step": "semantic/action/next-step/component.yml",
            }[component_id]
            template_marker = definition_marker.replace("component.yml", "template.html")
            self.assertIn(definition_marker, catalog)
            self.assertIn(template_marker, catalog)
            definition = (COMPONENTS / definition_marker).read_text(encoding="utf-8")
            self.assertIn(f"id: {component_id}", definition)
            self.assertIn("required_slots:", definition)
            styles_rel = next(
                line.split(":", 1)[1].strip()
                for line in definition.splitlines()
                if line.startswith("styles:")
            )
            self.assertTrue(
                (COMPONENTS / Path(definition_marker).parent / styles_rel).resolve().is_file(),
                component_id,
            )


if __name__ == "__main__":
    unittest.main()
