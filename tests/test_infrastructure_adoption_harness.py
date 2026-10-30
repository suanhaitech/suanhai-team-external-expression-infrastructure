"""以临时 Git 仓验证既有仓库 Harness 安装工具的边界。"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


SOURCE_SCRIPT = Path(__file__).resolve().parents[1] / "tools/infrastructure-adoption-harness/install_harness.py"
REPOSITORY = "suanhai-team-external-expression-infrastructure"
EXPECTED_URL = f"https://github.com/suanhaitech/{REPOSITORY}.git"
TOOL_ID = "consumer.infrastructure-adoption-harness"
TOOL_PATH = "tools/infrastructure-adoption-harness"
ENTRYPOINT = f"{TOOL_PATH}/install_harness.py"
SUBMODULE_PATH = "custom location/infra module"


class InfrastructureAdoptionHarnessTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="infrastructure-adoption-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.infra_source = self.base / "infra-source"
        # 仓库根路径本身位于名为 vendor 的目录下，必须允许这种正常工作区布局。
        self.consumer = self.base / "vendor" / "consumer workspace"
        self.infra_source.mkdir()
        self.consumer.mkdir(parents=True)
        self._init_repo(self.infra_source, "infrastructure fixture")
        self._write_tool_manifest(self.infra_source)
        (self.infra_source / ENTRYPOINT).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SOURCE_SCRIPT, self.infra_source / ENTRYPOINT)
        preflight_entrypoint = self.infra_source / "tools/submodule-preflight/submodule_preflight.py"
        preflight_entrypoint.parent.mkdir(parents=True, exist_ok=True)
        preflight_entrypoint.write_text("# test fixture\n", encoding="utf-8")
        for relative in (
            "docs/consumer-repository-bootstrap.md",
            "docs/consumer-repository-harness-v0.1.md",
            "docs/submodule-consumer-versioning.md",
        ):
            document = self.infra_source / relative
            document.parent.mkdir(parents=True, exist_ok=True)
            document.write_text("protocol fixture\n", encoding="utf-8")
        self._git(self.infra_source, "add", "manifest.yml", ENTRYPOINT, "tools", "docs")
        self._git(self.infra_source, "commit", "-m", "add installer fixture")

        self._init_repo(self.consumer, "consumer fixture")
        (self.consumer / "README.md").write_text("existing consumer\n", encoding="utf-8")
        (self.consumer / "AGENTS.md").write_text("# Existing rules\n\nKeep these rules.\n", encoding="utf-8")
        self._git(self.consumer, "add", "README.md", "AGENTS.md")
        self._git(self.consumer, "commit", "-m", "initial consumer")
        self._git(self.consumer, "-c", "protocol.file.allow=always", "submodule", "add", str(self.infra_source), SUBMODULE_PATH)

        modules = self.consumer / ".gitmodules"
        content = modules.read_text(encoding="utf-8")
        content = re.sub(r"(?m)^\s*url\s*=\s*.*$", f"\turl = {EXPECTED_URL}", content)
        modules.write_text(content, encoding="utf-8")
        self._git(self.consumer, "add", ".gitmodules", SUBMODULE_PATH)
        self._git(self.consumer, "commit", "-m", "pin infrastructure fixture")

        self.submodule = self.consumer / SUBMODULE_PATH
        self.script = self.submodule / ENTRYPOINT
        self.parent_head = self._git(self.consumer, "rev-parse", "HEAD").stdout.strip()
        self.submodule_head = self._git(self.submodule, "rev-parse", "HEAD").stdout.strip()

    @staticmethod
    def _environment() -> dict[str, str]:
        return {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "GIT_ALLOW_PROTOCOL": "file",
            # 临时克隆出来的 submodule 不继承父测试仓的 user.* 配置；
            # 在进程环境提供隔离身份，让 Linux CI 无需修改全局 Git 配置也能造出测试提交。
            "GIT_AUTHOR_NAME": "Infrastructure Adoption Test",
            "GIT_AUTHOR_EMAIL": "infrastructure-adoption-test@example.invalid",
            "GIT_COMMITTER_NAME": "Infrastructure Adoption Test",
            "GIT_COMMITTER_EMAIL": "infrastructure-adoption-test@example.invalid",
        }

    def _git(self, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(cwd), *args],
            cwd=self.base,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=self._environment(),
            check=True,
        )

    def _init_repo(self, path: Path, name: str) -> None:
        subprocess.run(["git", "init", str(path)], cwd=self.base, check=True, capture_output=True)
        self._git(path, "config", "user.email", "test@example.invalid")
        self._git(path, "config", "user.name", name)
        (path / "README.md").write_text(f"{name}\n", encoding="utf-8")
        self._git(path, "add", "README.md")
        self._git(path, "commit", "-m", "initial")

    @staticmethod
    def _write_tool_manifest(root: Path) -> None:
        manifest = f"""schema_version: 2
repository: {REPOSITORY}
capabilities:
  - id: {TOOL_ID}
    kind: tool
    path: {TOOL_PATH}
    entrypoint: {ENTRYPOINT}
    purpose: test fixture
  - id: consumer.submodule-preflight
    kind: tool
    path: tools/submodule-preflight
    entrypoint: tools/submodule-preflight/submodule_preflight.py
    purpose: test fixture
"""
        target = root / "manifest.yml"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(manifest, encoding="utf-8")

    def run_tool_at(self, consumer: Path, *arguments: str, expected_code: int = 0) -> tuple[dict, subprocess.CompletedProcess[str]]:
        script = consumer / SUBMODULE_PATH / ENTRYPOINT
        result = subprocess.run(
            [sys.executable, str(script), "--root", str(consumer), "--submodule-path", SUBMODULE_PATH, *arguments],
            cwd=consumer,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=self._environment(),
        )
        self.assertEqual(result.returncode, expected_code, result.stderr or result.stdout)
        try:
            payload = json.loads(result.stdout if expected_code == 0 else result.stderr)
        except json.JSONDecodeError:
            self.fail(f"工具未返回合法 JSON：stdout={result.stdout!r} stderr={result.stderr!r}")
        return payload, result

    def run_tool(self, *arguments: str, expected_code: int = 0) -> tuple[dict, subprocess.CompletedProcess[str]]:
        return self.run_tool_at(self.consumer, *arguments, expected_code=expected_code)

    def test_dry_run_shows_reviewable_plan_and_does_not_write(self):
        agents = self.consumer / "AGENTS.md"
        before = agents.read_bytes()
        payload, _ = self.run_tool("--dry-run")
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["agents_action"], "append")
        self.assertIn("+## 共享 Suanhai 对外表达基础设施", payload["planned_diff"])
        self.assertNotIn("Keep these rules.", payload["planned_diff"])
        self.assertIn("BEGIN suanhai-infrastructure-consumer-harness:v1", payload["planned_harness"])
        self.assertRegex(payload["plan_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(agents.read_bytes(), before)
        self.assertEqual(self._git(self.consumer, "rev-parse", "HEAD").stdout.strip(), self.parent_head)
        self.assertEqual(self._git(self.submodule, "rev-parse", "HEAD").stdout.strip(), self.submodule_head)
        self.assertEqual(self._git(self.consumer, "status", "--porcelain").stdout.strip(), "")

    def test_create_plan_for_missing_agents_is_complete(self):
        agents = self.consumer / "AGENTS.md"
        agents.unlink()
        payload, _ = self.run_tool("--dry-run")
        self.assertEqual(payload["agents_action"], "create")
        self.assertIn("/dev/null", payload["planned_diff"])
        self.assertIn("+++ AGENTS.md (planned)", payload["planned_diff"])
        self.assertIn("BEGIN suanhai-infrastructure-consumer-harness:v1", payload["planned_diff"])
        self.assertFalse(agents.exists())

    def test_append_preserves_existing_mixed_line_endings_byte_for_byte(self):
        agents = self.consumer / "AGENTS.md"
        original = b"# Existing CRLF\r\nsecond line uses LF\nlast line has no newline"
        agents.write_bytes(original)
        preview, _ = self.run_tool("--dry-run")
        self.run_tool("--apply", "--expect-plan-sha256", preview["plan_sha256"])
        self.assertTrue(agents.read_bytes().startswith(original))

    def test_apply_uses_current_preview_hash_and_preserves_existing_rules(self):
        agents = self.consumer / "AGENTS.md"
        preview, _ = self.run_tool("--dry-run")
        payload, _ = self.run_tool("--apply", "--expect-plan-sha256", preview["plan_sha256"])
        result = agents.read_text(encoding="utf-8")
        self.assertTrue(payload["written"])
        self.assertTrue(result.startswith("# Existing rules\n\nKeep these rules.\n"))
        self.assertEqual(result.count("BEGIN suanhai-infrastructure-consumer-harness:v1"), 1)
        self.assertEqual(result.count("END suanhai-infrastructure-consumer-harness:v1"), 1)
        self.assertEqual(self._git(self.consumer, "rev-parse", "HEAD").stdout.strip(), self.parent_head)
        self.assertEqual(self._git(self.submodule, "status", "--porcelain").stdout.strip(), "")
        changed = self._git(self.consumer, "status", "--porcelain").stdout.splitlines()
        self.assertEqual(changed, [" M AGENTS.md"])
        self.assertEqual(list(self.consumer.glob(".suanhai-harness-*.tmp")), [])

    def test_second_install_is_unchanged(self):
        preview, _ = self.run_tool("--dry-run")
        self.run_tool("--apply", "--expect-plan-sha256", preview["plan_sha256"])
        unchanged, _ = self.run_tool("--dry-run")
        self.assertEqual(unchanged["agents_action"], "unchanged")
        self.assertFalse(unchanged["would_write"])
        self.assertEqual(unchanged["planned_diff"], "")
        self.run_tool("--apply", "--expect-plan-sha256", unchanged["plan_sha256"])

    def test_existing_fixed_submodule_can_install_missing_consumer_harness(self):
        """既有 gitlink 已正确固定时，只补根 Harness，不要求升级 submodule。"""
        agents = self.consumer / "AGENTS.md"
        original = agents.read_bytes()
        preview, _ = self.run_tool("--dry-run")
        self.assertEqual(preview["agents_action"], "append")
        self.run_tool("--apply", "--expect-plan-sha256", preview["plan_sha256"])
        self.assertTrue(agents.read_bytes().startswith(original))
        self.assertEqual(self._git(self.consumer, "rev-parse", "HEAD").stdout.strip(), self.parent_head)
        self.assertEqual(self._git(self.submodule, "rev-parse", "HEAD").stdout.strip(), self.submodule_head)
        self.assertIn("BEGIN suanhai-infrastructure-consumer-harness:v1", agents.read_text(encoding="utf-8"))

    def test_fresh_consumer_adds_fixed_submodule_then_installs_persistent_harness(self):
        """端到端覆盖模板外新仓：添加 gitlink，再把共享规则安装进根 AGENTS.md。"""
        fresh = self.base / "fresh-consumer"
        self._init_repo(fresh, "fresh consumer")

        self._git(fresh, "-c", "protocol.file.allow=always", "submodule", "add", str(self.infra_source), SUBMODULE_PATH)
        modules = fresh / ".gitmodules"
        content = re.sub(
            r"(?m)^([ \t]*url[ \t]*=[ \t]*).*$",
            rf"\g<1>{EXPECTED_URL}",
            modules.read_text(encoding="utf-8"),
        )
        modules.write_text(content, encoding="utf-8")
        self._git(fresh, "add", ".gitmodules", SUBMODULE_PATH)

        gitlink = self._git(fresh, "ls-files", "--stage", "--", SUBMODULE_PATH).stdout
        expected_sha = self._git(fresh / SUBMODULE_PATH, "rev-parse", "HEAD").stdout.strip()
        self.assertIn(f"160000 {expected_sha} 0\t{SUBMODULE_PATH}", gitlink)

        preview, _ = self.run_tool_at(fresh, "--dry-run")
        self.assertEqual(preview["agents_action"], "create")
        applied, _ = self.run_tool_at(fresh, "--apply", "--expect-plan-sha256", preview["plan_sha256"])
        self.assertTrue(applied["written"])
        self.assertIn("BEGIN suanhai-infrastructure-consumer-harness:v1", (fresh / "AGENTS.md").read_text(encoding="utf-8"))
        self.assertEqual(self._git(fresh / SUBMODULE_PATH, "rev-parse", "HEAD").stdout.strip(), expected_sha)
        self.assertEqual(self._git(fresh / SUBMODULE_PATH, "status", "--porcelain").stdout.strip(), "")
        status = self._git(fresh, "status", "--porcelain").stdout.splitlines()
        self.assertEqual(status[0], "A  .gitmodules")
        self.assertIn(SUBMODULE_PATH, status[1])
        self.assertEqual(status[2], "?? AGENTS.md")

    def test_apply_rejects_plan_that_changed_after_review(self):
        preview, _ = self.run_tool("--dry-run")
        agents = self.consumer / "AGENTS.md"
        agents.write_text(agents.read_text(encoding="utf-8") + "new human rule\n", encoding="utf-8")
        before = agents.read_bytes()
        _, result = self.run_tool("--apply", "--expect-plan-sha256", preview["plan_sha256"], expected_code=1)
        self.assertIn("dry-run 的 SHA-256 不一致", result.stderr)
        self.assertEqual(agents.read_bytes(), before)

    def test_duplicate_or_conflicting_markers_are_rejected(self):
        agents = self.consumer / "AGENTS.md"
        conflicting = "# Existing\n\n<!-- BEGIN suanhai-infrastructure-consumer-harness:v1 -->\nwrong\n<!-- END suanhai-infrastructure-consumer-harness:v1 -->\n"
        agents.write_text(conflicting, encoding="utf-8")
        before = agents.read_bytes()
        _, result = self.run_tool("--dry-run", expected_code=1)
        self.assertIn("存在不同内容", result.stderr)
        self.assertEqual(agents.read_bytes(), before)

        duplicate = conflicting + "\n" + conflicting
        agents.write_text(duplicate, encoding="utf-8")
        before = agents.read_bytes()
        _, result = self.run_tool("--dry-run", expected_code=1)
        self.assertIn("标记重复或不成对", result.stderr)
        self.assertEqual(agents.read_bytes(), before)

    def test_apply_requires_dry_run_hash(self):
        _, result = self.run_tool("--apply", expected_code=1)
        self.assertIn("必须携带 dry-run 返回", result.stderr)
        self.assertNotIn("BEGIN suanhai-infrastructure-consumer-harness:v1", (self.consumer / "AGENTS.md").read_text(encoding="utf-8"))

    def test_dirty_submodule_is_rejected(self):
        (self.submodule / "untracked.txt").write_text("local change", encoding="utf-8")
        _, result = self.run_tool("--dry-run", expected_code=1)
        self.assertIn("工作区不干净", result.stderr)
        self.assertFalse((self.consumer / "AGENTS.md").read_text(encoding="utf-8").count("BEGIN suanhai-infrastructure-consumer-harness:v1"))

    def test_wrong_url_is_rejected(self):
        modules = self.consumer / ".gitmodules"
        modules.write_text(modules.read_text(encoding="utf-8").replace(EXPECTED_URL, "https://example.invalid/wrong.git"), encoding="utf-8")
        _, result = self.run_tool("--dry-run", expected_code=1)
        self.assertIn("submodule URL 必须是", result.stderr)

    def test_submodule_path_traversal_is_rejected(self):
        result = subprocess.run(
            [sys.executable, str(self.script), "--root", str(self.consumer), "--submodule-path", "../escape", "--dry-run"],
            cwd=self.consumer,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=self._environment(),
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("不允许空片段、. 或 ..", result.stderr)
        self.assertFalse((self.consumer / "../escape").exists())

    def test_wrong_manifest_entry_is_rejected(self):
        manifest = self.submodule / "manifest.yml"
        manifest.write_text(manifest.read_text(encoding="utf-8").replace(f"id: {TOOL_ID}", "id: consumer.other"), encoding="utf-8")
        _, result = self.run_tool("--dry-run", expected_code=1)
        self.assertIn("未注册", result.stderr)

    def test_missing_consumer_protocol_document_is_rejected(self):
        document = self.submodule / "docs/consumer-repository-harness-v0.1.md"
        document.unlink()
        _, result = self.run_tool("--dry-run", expected_code=1)
        self.assertIn("缺少 Harness 必需协议文件", result.stderr)

    def test_missing_long_term_preflight_capability_is_rejected(self):
        manifest = self.submodule / "manifest.yml"
        text = manifest.read_text(encoding="utf-8")
        text = text.split("  - id: consumer.submodule-preflight", 1)[0]
        manifest.write_text(text, encoding="utf-8")
        _, result = self.run_tool("--dry-run", expected_code=1)
        self.assertIn("长期 Harness 依赖 consumer.submodule-preflight", result.stderr)

    def test_invalid_long_term_preflight_interface_is_rejected(self):
        manifest = self.submodule / "manifest.yml"
        original = manifest.read_text(encoding="utf-8")
        manifest.write_text(original.replace(
            "    entrypoint: tools/submodule-preflight/submodule_preflight.py",
            "    entrypoint: tools/submodule-preflight/missing.py",
        ), encoding="utf-8")
        _, result = self.run_tool("--dry-run", expected_code=1)
        self.assertIn("consumer.submodule-preflight 的 entrypoint 不符合接口约定", result.stderr)

    def test_missing_long_term_preflight_entrypoint_is_rejected(self):
        (self.submodule / "tools/submodule-preflight/submodule_preflight.py").unlink()
        _, result = self.run_tool("--dry-run", expected_code=1)
        self.assertIn("入口路径不存在或类型错误", result.stderr)

    def test_duplicate_manifest_tool_id_is_rejected(self):
        manifest = self.submodule / "manifest.yml"
        original = manifest.read_text(encoding="utf-8")
        capability = original.split("capabilities:\n", 1)[1]
        manifest.write_text(original + "  - id: " + capability.split("- id: ", 1)[1], encoding="utf-8")
        _, result = self.run_tool("--dry-run", expected_code=1)
        self.assertIn("重复注册", result.stderr)

    def test_parent_gitlink_must_match_submodule_head(self):
        self._git(self.submodule, "checkout", "--detach", "HEAD~0")
        (self.submodule / "next.txt").write_text("new commit\n", encoding="utf-8")
        self._git(self.submodule, "add", "next.txt")
        self._git(self.submodule, "commit", "-m", "advance submodule")
        _, result = self.run_tool("--dry-run", expected_code=1)
        self.assertIn("HEAD (", result.stderr)
        self.assertIn("与父仓 index gitlink", result.stderr)

    def test_spaces_in_submodule_path_and_vendor_parent_are_supported(self):
        payload, _ = self.run_tool("--dry-run")
        self.assertEqual(payload["submodule_path"], SUBMODULE_PATH)
        self.assertEqual(payload["agents_action"], "append")

    def test_cp1252_terminal_still_returns_utf8_json(self):
        result = subprocess.run(
            [sys.executable, str(self.script), "--root", str(self.consumer), "--submodule-path", SUBMODULE_PATH, "--dry-run"],
            cwd=self.consumer,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={**self._environment(), "PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertIn("固定使用 Suanhai", payload["planned_harness"])


if __name__ == "__main__":
    unittest.main()
