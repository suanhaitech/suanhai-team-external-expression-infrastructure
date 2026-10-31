"""HTML 制作工作流和语义组件包的文件协议回归测试。"""

from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / "workflows/html-production"
COMPONENTS = ROOT / "formats/web/html/components/core-v1"


class HtmlProductionDocumentationTest(unittest.TestCase):
    def test_presentation_forms_are_parallel_to_html_internal_assets(self):
        formats = (ROOT / "formats/README.md").read_text(encoding="utf-8")
        web = (ROOT / "formats/web/README.md").read_text(encoding="utf-8")
        html = (ROOT / "formats/web/html/README.md").read_text(encoding="utf-8")
        self.assertIn("网页、文档、演示文稿和打印物在这里并列", formats)
        self.assertIn("与文档、演示文稿等并列的呈现形式", web)
        self.assertIn("HTML 不是模板的上层", html)
        self.assertTrue((ROOT / "formats/document/README.md").is_file())
        self.assertTrue((ROOT / "formats/slides/README.md").is_file())
        self.assertTrue((ROOT / "formats/print/README.md").is_file())

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
        self.assertIn("entrypoint: workflows/html-production/ENTRYPOINT.md", manifest)
        self.assertIn("id: html.semantic-components-v1", manifest)
        self.assertIn("entrypoint: formats/web/html/components/core-v1/README.md", manifest)
        self.assertIn("path: formats/web/html/page-templates/project-report-v1", manifest)
        self.assertIn("entrypoint: formats/web/html/page-templates/project-report-v1/index.html", manifest)
        self.assertIn("id: html.materialize", manifest)
        self.assertIn("entrypoint: tools/html-materialize/materialize_html.py", manifest)

    def test_materialize_tool_and_report_schema_are_declared(self):
        tool = (ROOT / "tools/html-materialize/README.md").read_text(encoding="utf-8")
        schema = json.loads((ROOT / "schemas/html/report.schema.json").read_text(encoding="utf-8"))
        self.assertIn("--expect-plan-sha256", tool)
        self.assertIn("materialization.json", tool)
        self.assertEqual(schema["properties"]["materialization"]["properties"]["tool"]["const"], "html.materialize")
        self.assertIn("materialization", schema["required"])

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
        self.assertIn("从 .gitmodules 解析基础设施 submodule 的实际相对路径", doc)
        self.assertIn("不执行 git submodule update --remote", doc)
        self.assertIn("149759f18edf54c83bdfbadf8326c3031c10bb4f", doc)
        self.assertIn("fetch origin codex/feat-html-production-workflow", doc)
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
