"""用真实资产验证跨 Agent 页面协议、装配和局部修订边界。"""
import copy
import importlib.util
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("course_materializer", ROOT / "infrastructure/html/tools/materialize/materialize_html.py")
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)
MANIFEST = TOOL.parse_manifest(ROOT / "manifest.yml")


def plan():
    return {"schema_version": 1, "sources": [{"id": "source-demo"}], "pages": [
        {"id": "page-cover", "template_id": "html.single-page.cover.technical-editorial-v1", "title": "长标题 Mixed title <safe>", "objective": "引入", "core_message": "范围", "source_ids": ["source-demo"]},
        {"id": "page-method", "template_id": "html.single-page.content.definition-mapping-v1", "title": "方法说明", "objective": "解释", "core_message": "机制", "notes": "仅在备注显示", "responds_to": ["page-cover"], "components": [{"slot": "supporting", "id": "content.definition"}]},
    ]}


def build(document, version="v001", **kwargs):
    context = {"revision": 1, "title": "匿名示例", "audience": "学习者", "purpose": "理解机制"}
    return TOOL.build_plan(ROOT, MANIFEST, None, "html.semantic-components-v1", [], ["html.responsive-layout-v1", "html.presentation-foundation-v1"], ["html.runtime-kit-v1", "html.image-viewer-v1"], "EXPR-20261104-1234abcd", version, 1, 4, "a" * 40, context, [], "html.container.presentation-deck-v1", [], "expression.scenario.course-learning-v1", document, "editorial-warm", **kwargs)


class CourseMaterializationTest(unittest.TestCase):
    def test_real_assets_slots_theme_images_and_multiple_runtime_kits(self):
        files, record = build(plan())
        html = files[PurePosixPath("index.html")].decode()
        self.assertIn('id="page-cover"', html)
        self.assertIn("&lt;safe&gt;", html)
        self.assertIn('data-speaker-note="仅在备注显示"', html)
        self.assertNotIn("SUANHAI_COMPONENTS:supporting", html)
        self.assertEqual(len(record["runtime_kits"]), 2)
        self.assertEqual(len(record["layouts"]), 2)
        self.assertIn("html-image-viewer-v1/runtime.js", html)
        self.assertIn("editorial-warm.css", html)
        self.assertTrue(any(path.suffix == ".svg" for path in files))
        self.assertTrue(any("assets/shared/styles/presentation-v1/styles.css" == path.as_posix() for path in files))

    def test_duplicate_pages_dangling_sources_and_callbacks_rejected(self):
        for mutation in (lambda p: p["pages"].append(copy.deepcopy(p["pages"][0])), lambda p: p["pages"][0].update(source_ids=["missing"]), lambda p: p["pages"][1].update(responds_to=["missing"])):
            document = plan()
            mutation(document)
            with self.assertRaises(TOOL.MaterializeError):
                build(document)

    def test_undeclared_component_slot_and_unknown_text_slot_rejected(self):
        document = plan()
        document["pages"][1]["components"][0]["slot"] = "unknown"
        with self.assertRaises(TOOL.MaterializeError):
            build(document)
        document = plan()
        document["pages"][1]["slots"] = {"unknown": "content"}
        with self.assertRaises(TOOL.MaterializeError):
            build(document)

    def test_revision_preserves_baseline_and_non_target_page_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            baseline = root / "courses/EXPR-20261104-1234abcd/v001"
            old_files, _ = build(plan())
            for path, data in old_files.items():
                output = baseline / path
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(data)
            before = (baseline / "index.html").read_bytes()
            document = plan()
            document["pages"][1]["title"] = "改进后的说明"
            new_files, record = build(document, "v002")
            task = {"output": baseline.parent / "v002", "version_name": "v002"}
            result, metadata = TOOL.derive_revision(root, task, new_files, record, "v001", ["page-method"])
            self.assertEqual((baseline / "index.html").read_bytes(), before)
            self.assertIn("改进后的说明", result[PurePosixPath("index.html")].decode())
            self.assertEqual(metadata["revision_source"]["preserved_pages"], ["page-cover"])
            document["pages"][0]["title"] = "越界修改"
            files, record = build(document, "v002")
            with self.assertRaises(TOOL.MaterializeError):
                TOOL.derive_revision(root, task, files, record, "v001", ["page-method"])
            files, record = build(plan(), "v002")
            record["runtime_kits"] = []
            with self.assertRaises(TOOL.MaterializeError):
                TOOL.derive_revision(root, task, files, record, "v001", ["page-method"])

    def test_asset_bytes_preview_apply_is_idempotent_and_preserves_user_rules(self):
        tool = ROOT / "infrastructure/repository-management/tools/asset-bytes/protect_asset_bytes.py"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run(["git", "init", "--initial-branch=main", str(root)], check=True, capture_output=True)
            original = b"*.png binary\n"
            (root / ".gitattributes").write_bytes(original)
            def run(*extra):
                result = subprocess.run([sys.executable, str(tool), "--root", str(root), *extra], text=True, encoding="utf-8", capture_output=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                return json.loads(result.stdout)
            preview = run()
            self.assertEqual((root / ".gitattributes").read_bytes(), original)
            run("--apply", "--expect-plan-sha256", preview["plan_sha256"])
            self.assertTrue((root / ".gitattributes").read_bytes().startswith(original))
            self.assertFalse(run()["would_write"])
            checked = subprocess.run(["git", "-C", str(root), "check-attr", "text", "--", "courses/sample.md"], capture_output=True, text=True)
            self.assertIn("unset", checked.stdout)


if __name__ == "__main__":
    unittest.main()
