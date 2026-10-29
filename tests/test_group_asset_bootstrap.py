"""通用小组模板铺设：真实 submodule 集成与不覆盖、回滚边界。"""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_RELATIVE = Path("tools/group-asset-bootstrap/materialize_template.py")
TEMPLATE_RELATIVE = Path("templates/group-asset-repository-v1")
SUBMODULE_RELATIVE = Path("vendor/suanhai-team-external-expression-infrastructure")
PUBLIC_URL = "https://github.com/suanhaitech/suanhai-team-external-expression-infrastructure.git"
SECTION = "submodule.vendor/suanhai-team-external-expression-infrastructure"

spec = importlib.util.spec_from_file_location("group_asset_bootstrap", REPO_ROOT / SCRIPT_RELATIVE)
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


def environment() -> dict[str, str]:
    return {
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUTF8": "1",
        # file 协议只供测试进程连接临时仓库，不修改用户的全局 Git 配置。
        "GIT_ALLOW_PROTOCOL": "file",
        "GIT_TERMINAL_PROMPT": "0",
    }


def git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *arguments],
        capture_output=True, text=True, encoding="utf-8", env=environment(),
    )
    if result.returncode:
        raise AssertionError(result.stderr or result.stdout)
    return result.stdout.strip()


def initialize_repository(root: Path) -> None:
    root.mkdir(parents=True)
    git(root, "init", "--initial-branch=main")
    git(root, "config", "user.name", "Bootstrap Test")
    git(root, "config", "user.email", "test@example.invalid")
    git(root, "config", "core.autocrlf", "false")


def snapshot(root: Path) -> dict[str, bytes | None]:
    """包含空目录，确保回滚不留下临时目录或半铺设文件。"""
    return {
        path.relative_to(root).as_posix(): path.read_bytes() if path.is_file() else None
        for path in root.rglob("*")
    }


class GroupAssetBootstrapIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 把未提交实现复制成隔离的 Git 快照；真实开发仓不会产生测试提交。
        cls.source_temp = tempfile.TemporaryDirectory(prefix="group-bootstrap-source-")
        cls.addClassCleanup(cls.source_temp.cleanup)
        cls.source = Path(cls.source_temp.name) / "infrastructure"
        initialize_repository(cls.source)
        (cls.source / SCRIPT_RELATIVE.parent).mkdir(parents=True)
        shutil.copy2(REPO_ROOT / SCRIPT_RELATIVE, cls.source / SCRIPT_RELATIVE)
        shutil.copytree(REPO_ROOT / TEMPLATE_RELATIVE, cls.source / TEMPLATE_RELATIVE)
        # Task-loop 作为消费端实际调用的共享工具，随临时基础设施快照一同固定。
        # 忽略解释器缓存，避免测试仓库带入机器生成物。
        shutil.copytree(
            REPO_ROOT / "harness/task-loop",
            cls.source / "harness/task-loop",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        shutil.copy2(REPO_ROOT / "manifest.yml", cls.source / "manifest.yml")
        git(cls.source, "add", ".")
        git(cls.source, "commit", "-m", "test snapshot")
        cls.previous_commit = git(cls.source, "rev-parse", "HEAD")
        (cls.source / "snapshot-version.txt").write_text("second test commit\n", encoding="utf-8")
        git(cls.source, "add", "snapshot-version.txt")
        git(cls.source, "commit", "-m", "test next commit")
        cls.locked_commit = git(cls.source, "rev-parse", "HEAD")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="group-bootstrap-consumer-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "consumer"
        initialize_repository(self.root)
        git(self.root, "submodule", "add", str(self.source), SUBMODULE_RELATIVE.as_posix())
        # 测试数据来自本地，提交的 .gitmodules 仍采用生产协议的公开 HTTPS URL。
        git(self.root, "config", "--file", ".gitmodules", f"{SECTION}.url", PUBLIC_URL)
        git(self.root, "add", ".gitmodules", SUBMODULE_RELATIVE.as_posix())
        git(self.root, "commit", "-m", "test consumer pinned infrastructure")
        self.infrastructure = self.root / SUBMODULE_RELATIVE
        self.script = self.infrastructure / SCRIPT_RELATIVE

    def cli(self, *arguments: str, ok: bool = True, root: Path | None = None) -> dict:
        consumer = root or self.root
        script = consumer / SUBMODULE_RELATIVE / SCRIPT_RELATIVE
        result = subprocess.run(
            [sys.executable, str(script), "--root", str(consumer), *arguments],
            capture_output=True, text=True, encoding="utf-8", env=environment(),
        )
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        else:
            self.assertNotEqual(result.returncode, 0, "应拒绝不满足前置条件的消费仓")
        return json.loads(result.stdout if ok else result.stderr)

    def test_dry_run_apply_and_repeat_preserve_locked_infrastructure(self):
        before = git(self.root, "status", "--porcelain")
        preview = self.cli("--dry-run")
        self.assertEqual(preview["mode"], "dry-run")
        self.assertEqual(preview["written"], [])
        self.assertIn("reports/README.md", preview["would_write"])
        self.assertEqual(git(self.root, "status", "--porcelain"), before)
        self.assertFalse((self.root / "README.md").exists())

        applied = self.cli("--apply")
        self.assertEqual(applied["submodule_commit"], self.locked_commit)
        self.assertEqual(applied["written"], preview["would_write"])
        for path in preview["would_write"]:
            self.assertEqual(
                (self.root / path).read_bytes(),
                (self.infrastructure / TEMPLATE_RELATIVE / path).read_bytes(),
            )
        self.assertTrue((self.root / "context/group/identity.md").is_file())
        self.assertTrue((self.root / "context/projects/_template/project-overview.md").is_file())
        self.assertFalse((self.root / "works").exists())
        before_repeat = snapshot(self.root)
        repeated = self.cli("--apply")
        self.assertEqual(repeated["written"], [])
        self.assertEqual(set(repeated["unchanged"]), set(preview["would_write"]))
        self.assertEqual(snapshot(self.root), before_repeat)
        self.assertEqual(git(self.infrastructure, "rev-parse", "HEAD"), self.locked_commit)
        self.assertEqual(git(self.infrastructure, "status", "--porcelain"), "")
        self.assertEqual(git(self.root, "rev-list", "--count", "HEAD"), "1")

    def test_no_mode_defaults_to_read_only_preview(self):
        before = snapshot(self.root)
        result = self.cli()
        self.assertEqual(result["mode"], "dry-run")
        self.assertEqual(result["written"], [])
        self.assertEqual(snapshot(self.root), before)

    def test_cp1252_terminal_preserves_utf8_preview_json(self):
        result = subprocess.run(
            [sys.executable, str(self.script), "--root", str(self.root), "--dry-run"],
            capture_output=True, text=True, encoding="utf-8",
            env={**environment(), "PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertIn("身份与项目事实须由真人确认", payload["note"])

    def test_conflict_is_rejected_before_any_template_file_is_written(self):
        (self.root / "README.md").write_text("keep user content\n", encoding="utf-8")
        before = snapshot(self.root)
        result = self.cli("--apply", ok=False)
        self.assertFalse(result["ok"])
        self.assertIn("README.md", result["error"])
        self.assertEqual(snapshot(self.root), before)
        self.assertFalse((self.root / "reports").exists())

    def test_wrong_submodule_url_is_rejected(self):
        git(self.root, "config", "--file", ".gitmodules", f"{SECTION}.url", "https://example.invalid/other.git")
        result = self.cli("--apply", ok=False)
        self.assertIn("URL", result["error"])
        self.assertFalse((self.root / "README.md").exists())

    def test_submodule_head_and_parent_gitlink_mismatch_is_rejected(self):
        git(self.infrastructure, "checkout", "--detach", self.previous_commit)
        result = self.cli("--apply", ok=False)
        self.assertIn("gitlink", result["error"])
        self.assertFalse((self.root / "README.md").exists())
        self.assertEqual(git(self.infrastructure, "rev-parse", "HEAD"), self.previous_commit)

    def test_dirty_submodule_is_rejected_and_local_file_is_preserved(self):
        local_file = self.infrastructure / "local-uncommitted.txt"
        local_file.write_text("keep me\n", encoding="utf-8")
        result = self.cli("--apply", ok=False)
        self.assertIn("不干净", result["error"])
        self.assertEqual(local_file.read_text(encoding="utf-8"), "keep me\n")
        self.assertFalse((self.root / "README.md").exists())

    def test_fresh_clone_can_initialize_same_gitlink_and_apply(self):
        fresh = self.base / "fresh-clone"
        git(self.base, "clone", str(self.root), str(fresh))
        # 仅在测试 clone 的本地配置替换传输地址，避免访问网络。
        git(fresh, "config", f"{SECTION}.url", str(self.source))
        git(fresh, "submodule", "update", "--init", "--recursive")
        self.assertEqual(git(fresh / SUBMODULE_RELATIVE, "rev-parse", "HEAD"), self.locked_commit)
        result = self.cli("--apply", root=fresh)
        self.assertTrue(result["ok"])
        self.assertTrue((fresh / "topics/README.md").is_file())
        self.assertTrue((fresh / "reports/README.md").is_file())

    def test_apply_succeeds_before_parent_repository_first_commit(self):
        unborn = self.base / "unborn-consumer"
        initialize_repository(unborn)
        git(unborn, "submodule", "add", str(self.source), SUBMODULE_RELATIVE.as_posix())
        git(unborn, "config", "--file", ".gitmodules", f"{SECTION}.url", PUBLIC_URL)
        git(unborn, "add", ".gitmodules", SUBMODULE_RELATIVE.as_posix())

        head = subprocess.run(
            ["git", "-C", str(unborn), "rev-parse", "--verify", "HEAD"],
            capture_output=True, text=True, encoding="utf-8", env=environment(),
        )
        self.assertNotEqual(head.returncode, 0, "该消费仓应仍处于 unborn 分支")
        gitlink = git(unborn, "ls-files", "--stage", "--", SUBMODULE_RELATIVE.as_posix())
        self.assertIn("160000", gitlink)

        result = self.cli("--apply", root=unborn)
        self.assertEqual(result["submodule_commit"], self.locked_commit)
        self.assertTrue((unborn / "README.md").is_file())
        self.assertIn("A", git(unborn, "status", "--short"))

    def test_template_can_register_and_complete_test_report_task(self):
        preview = self.cli("--apply")

        identity = self.root / "context/group/identity.md"
        identity.write_text(
            "# 测试夹具：小组身份\n\n"
            "> 仅用于验证模板任务流程，不代表任何真实小组或项目事实。\n",
            encoding="utf-8",
        )
        task_tool = self.infrastructure / "harness/task-loop/scripts/task_loop.py"

        def task_cli(*arguments: str) -> dict:
            result = subprocess.run(
                [sys.executable, str(task_tool), "--root", str(self.root), *arguments],
                capture_output=True, text=True, encoding="utf-8", env=environment(),
            )
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            return json.loads(result.stdout)

        task = task_cli("create", "--title", "模板报告输出测试", "--request", "验证任务循环能把报告产物关联到模板目录。", "--test")
        task_id = task["id"]
        task = task_cli(
            "brief", task_id, "--expect-version", str(task["version"]),
            "--audience", "自动化测试断言", "--purpose", "验证模板与任务工具的集成",
            "--scope", "只验证测试文件能登记到 reports，不表示真实项目交付",
            "--output", f"reports/{task_id}", "--acceptance", "任务校验通过且报告哈希可追溯",
            "--source", "context/group/identity.md",
        )
        task = task_cli(
            "event", task_id, "--expect-version", str(task["version"]), "--type", "align",
            "--note", "测试夹具完成合成范围对齐。",
            "--user-quote", "合成测试输入：本任务仅验证模板路径和任务状态工具。",
        )
        task = task_cli(
            "event", task_id, "--expect-version", str(task["version"]), "--type", "start",
            "--note", "开始合成的隔离测试，不处理任何项目事实。",
        )
        artifact = Path("reports") / task_id / "v001" / "test-report.md"
        artifact_path = self.root / artifact
        artifact_path.parent.mkdir(parents=True)
        artifact_path.write_text("# 测试报告\n\n仅验证目录与状态协议。\n", encoding="utf-8")
        task = task_cli(
            "event", task_id, "--expect-version", str(task["version"]), "--type", "review",
            "--note", "合成报告已登记，SHA-256 可核对；不代表真人评审。",
            "--artifact", artifact.as_posix(),
        )
        validation = task_cli("validate", task_id)
        self.assertTrue(validation["valid"])

        task = task_cli(
            "event", task_id, "--expect-version", str(task["version"]), "--type", "complete",
            "--note", "只记录隔离测试的模拟确认，不代表真人业务确认或发布授权。",
            "--user-quote", "合成测试断言：测试用例完成；不代表真实小组或客户确认。",
        )
        stored = json.loads((self.root / "tasks" / task_id / "task.json").read_text(encoding="utf-8"))
        view = (self.root / "tasks" / task_id / "task.md").read_text(encoding="utf-8")
        self.assertEqual(stored["mode"], "test")
        self.assertEqual(stored["status"], "completed")
        self.assertEqual(stored["artifacts"][0]["path"], artifact.as_posix())
        self.assertTrue((self.root / "tasks" / task_id / "task.json").is_file())
        self.assertTrue((self.root / "tasks" / task_id / "task.md").is_file())
        self.assertIn("reports/", view)
        self.assertIn("合成测试断言", stored["artifacts"][0]["completion_quote"])
        self.assertEqual(git(self.infrastructure, "status", "--porcelain"), "")
        self.assertEqual(git(self.infrastructure, "rev-parse", "HEAD"), preview["submodule_commit"])


class GroupAssetBootstrapFilesystemTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="group-bootstrap-boundaries-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "consumer"
        self.root.mkdir()

    def symlink(self, link: Path, target: Path, *, directory: bool = False) -> None:
        try:
            link.symlink_to(target, target_is_directory=directory)
        except (OSError, NotImplementedError) as error:
            self.skipTest(f"当前平台不允许创建测试符号链接：{error}")

    def test_illegal_template_paths_are_rejected(self):
        for relative in (Path("../escape.md"), self.base / "absolute.md", Path("nested/../escape.md"), Path(".git/config"), Path("vendor/infra/input.md")):
            with self.subTest(path=str(relative)):
                with self.assertRaises(bootstrap.BootstrapError):
                    bootstrap.plan_files(self.root, [(relative, b"no write")])
        self.assertEqual(snapshot(self.root), {})

    def test_symlink_directory_escape_is_rejected_without_writing(self):
        outside = self.base / "outside"
        outside.mkdir()
        self.symlink(self.root / "reports", outside, directory=True)
        _, _, conflicts = bootstrap.plan_files(self.root, [(Path("reports/output.md"), b"no write")])
        self.assertTrue(conflicts)
        self.assertEqual(list(outside.iterdir()), [])

    def test_repository_root_alias_uses_resolved_boundary(self):
        alias = self.base / "root-alias"
        self.symlink(alias, self.root, directory=True)
        writes, unchanged, conflicts = bootstrap.plan_files(alias, [(Path("report.md"), b"new")])
        self.assertEqual(conflicts, [])
        self.assertEqual(unchanged, [])
        self.assertEqual(len(writes), 1)

    def test_symlink_file_and_template_source_are_rejected(self):
        target = self.base / "target.md"
        target.write_bytes(b"keep")
        self.symlink(self.root / "README.md", target)
        _, _, conflicts = bootstrap.plan_files(self.root, [(Path("README.md"), b"no write")])
        self.assertTrue(conflicts)
        with self.assertRaises(bootstrap.BootstrapError):
            bootstrap.template_files(self.root)
        self.assertEqual(target.read_bytes(), b"keep")

    def test_existing_non_file_parent_is_reported_as_conflict(self):
        (self.root / "context").write_bytes(b"keep")
        _, _, conflicts = bootstrap.plan_files(self.root, [(Path("context/group/identity.md"), b"new")])
        self.assertTrue(conflicts)
        self.assertEqual((self.root / "context").read_bytes(), b"keep")

    @unittest.skipUnless(os.name == "nt", "Windows junction 专项边界")
    def test_windows_junction_escape_is_rejected_without_writing(self):
        outside = self.base / "outside"
        outside.mkdir()
        link = self.root / "reports"
        # junction 通常不需要创建 symlink 的管理员权限，可在普通 Windows
        # 工作站上覆盖目录重定向风险；所有路径都在本次临时测试目录。
        result = subprocess.run(
            ["cmd", "/d", "/c", "mklink", "/J", str(link), str(outside)],
            capture_output=True, env=environment(),
        )
        if result.returncode:
            self.skipTest("当前文件系统不允许创建测试 junction")
        try:
            _, _, conflicts = bootstrap.plan_files(self.root, [(Path("reports/output.md"), b"no write")])
            self.assertTrue(conflicts)
            self.assertEqual(list(outside.iterdir()), [])
        finally:
            # os.rmdir 删除 junction 本身，不递归遍历链接到的目标。
            link.rmdir()

    def test_install_failure_rolls_back_new_files_and_empty_directories(self):
        # 第二个目标父路径是普通文件，模拟安装阶段失败；第一个文件必须回滚。
        (self.root / "blocked").write_bytes(b"keep existing")
        before = snapshot(self.root)
        with self.assertRaises((OSError, bootstrap.BootstrapError)):
            bootstrap.apply_files(self.root, [
                (self.root / "created/nested/first.md", b"new"),
                (self.root / "blocked/second.md", b"fails"),
            ])
        self.assertEqual(snapshot(self.root), before)

    def test_file_created_after_planning_is_not_overwritten(self):
        writes, _, conflicts = bootstrap.plan_files(self.root, [(Path("report.md"), b"template")])
        self.assertFalse(conflicts)
        (self.root / "report.md").write_bytes(b"concurrent user content")
        with self.assertRaises((OSError, bootstrap.BootstrapError)):
            bootstrap.apply_files(self.root, writes)
        self.assertEqual((self.root / "report.md").read_bytes(), b"concurrent user content")
        self.assertEqual(list(self.root.iterdir()), [self.root / "report.md"])

    def test_partial_copy_failure_removes_current_and_previous_new_files(self):
        before = snapshot(self.root)
        original_copy = bootstrap.shutil.copyfileobj
        call_count = 0

        def fail_second_copy(source, destination):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                destination.write(b"partial")
                raise OSError("simulated disk write failure")
            original_copy(source, destination)

        with mock.patch.object(bootstrap.shutil, "copyfileobj", side_effect=fail_second_copy):
            with self.assertRaises(bootstrap.BootstrapError):
                bootstrap.apply_files(self.root, [
                    (self.root / "reports/first.md", b"first"),
                    (self.root / "context/group/second.md", b"second"),
                ])
        self.assertEqual(call_count, 2)
        self.assertEqual(snapshot(self.root), before)


if __name__ == "__main__":
    unittest.main()
