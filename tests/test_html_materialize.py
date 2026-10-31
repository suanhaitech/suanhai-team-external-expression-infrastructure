"""HTML 模板与组件物料化的 submodule 锁定、预览和写入安全测试。"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL = Path("tools/html-materialize/materialize_html.py")
SUBMODULE = Path("vendor/suanhai-team-external-expression-infrastructure")
TASK_ID = "EXPR-20261031-1234abcd"
PUBLIC_URL = "https://github.com/suanhaitech/suanhai-team-external-expression-infrastructure.git"
TEMPLATE_ID = "html.project-report-v1"
COMPONENT_ID = "html.semantic-components-v1"


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

        shutil.copytree(REPO_ROOT / "formats/web/html", cls.source / "formats/web/html")
        (cls.source / TOOL.parent).mkdir(parents=True)
        shutil.copy2(REPO_ROOT / TOOL, cls.source / TOOL)
        (cls.source / "manifest.yml").write_text(
            "schema_version: 2\n"
            "repository: suanhai-team-external-expression-infrastructure\n"
            "capabilities:\n"
            "  - id: html.project-report-v1\n"
            "    kind: template\n"
            "    path: formats/web/html/page-templates/project-report-v1\n"
            "    entrypoint: formats/web/html/page-templates/project-report-v1/index.html\n"
            "    purpose: test\n"
            "  - id: html.semantic-components-v1\n"
            "    kind: template\n"
            "    path: formats/web/html/components/core-v1\n"
            "    entrypoint: formats/web/html/components/core-v1/README.md\n"
            "    purpose: test\n",
            encoding="utf-8",
        )
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

    def cli(self, *arguments: str, ok: bool = True) -> dict:
        script = self.infrastructure / TOOL
        result = subprocess.run(
            [sys.executable, str(script), "--root", str(self.root), "--task-id", TASK_ID,
             "--template-id", TEMPLATE_ID, "--component-id", COMPONENT_ID, *arguments],
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
        self.assertIn('tool: html.materialize', report)

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
        self.assertIn("任务创建时固定", mismatch["error"])


if __name__ == "__main__":
    unittest.main()
