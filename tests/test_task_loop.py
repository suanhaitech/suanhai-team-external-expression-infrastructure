"""任务循环的行为回归：所有任务和作品均位于临时消费仓库。"""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "harness/task-loop/scripts/task_loop.py"


class TaskLoopTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="expression-task-loop-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "consumer"
        self.make_consumer(self.root)

    @staticmethod
    def make_consumer(root):
        root.mkdir(parents=True)
        for directory in (".git", "context", "tasks", "works", "reviews"):
            (root / directory).mkdir()
        (root / "README.md").write_text("测试消费仓库，不是真实项目。\n", encoding="utf-8")
        (root / "AGENTS.md").write_text("测试任务，不提交或发布。\n", encoding="utf-8")
        (root / "context/input.md").write_text("仅用于测试的获准输入。\n", encoding="utf-8")

    def cli(self, *arguments, root=None, ok=True):
        # 每次调用都是新进程，避免测试无意依赖进程内缓存或旧会话。
        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment["PYTHONUTF8"] = "1"
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(root or self.root), *map(str, arguments)],
            capture_output=True, text=True, encoding="utf-8", env=environment,
        )
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                self.fail(f"命令未返回合法 JSON: {result.stdout!r}\n{result.stderr}")
        self.assertNotEqual(result.returncode, 0, "预期拒绝操作，但命令成功")
        return result

    def create(self):
        return self.cli("create", "--title", "测试表达任务", "--request", "先澄清目标。", "--test")

    def show(self, task):
        return self.cli("show", task["id"])

    def brief(self, task, **overrides):
        fields = {
            "audience": "测试评审者", "purpose": "验证工作循环", "scope": "仅测试内容",
            "output": "works/report-v1.html", "acceptance": "结构可评审，保留问题清单",
            "source": "context/input.md",
        }
        fields.update(overrides)
        args = ["brief", task["id"], "--expect-version", task["version"]]
        for key, value in fields.items():
            args.extend((f"--{key}", value))
        return self.cli(*args)

    def event(self, task, kind, **values):
        args = [
            "event", task["id"], "--expect-version", task["version"],
            "--type", kind, "--note", f"测试事件：{kind}",
        ]
        for key, value in values.items():
            args.extend((f"--{key.replace('_', '-')}", value))
        return self.cli(*args)

    def working_task(self):
        task = self.brief(self.create())
        task = self.event(task, "align", user_quote="测试用户：目标范围已确认。")
        self.assertEqual(task["status"], "ready")
        return self.event(task, "start")

    def artifact(self, name="report-v1.html", content="<h1>测试草稿</h1>"):
        path = self.root / "works" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path.relative_to(self.root).as_posix()

    def completed_task(self):
        task = self.working_task()
        task = self.event(task, "review", artifact=self.artifact())
        return self.event(task, "complete", user_quote="测试用户：认可本轮版本，不授权发布。")

    def canonical(self, task):
        return self.root / "tasks" / task["id"] / "task.json"

    def tree_snapshot(self):
        return {
            path.relative_to(self.root).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns)
            for path in self.root.rglob("*") if path.is_file()
        }

    def test_create_allows_unknowns_and_never_reuses_title_as_identity(self):
        first, second = self.create(), self.create()
        self.assertRegex(first["id"], r"^EXPR-\d{8}-[0-9a-f]{8}$")
        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual(first["mode"], "test")
        self.assertEqual(first["status"], "clarifying")
        self.assertEqual(first["version"], 1)
        self.assertEqual(first["revision"], 1)
        self.assertFalse(first["brief"]["audience"])
        self.assertEqual(self.show(first), first)
        self.assertTrue(self.canonical(first).exists())
        self.assertTrue(self.canonical(first).with_name("task.md").exists())

    def test_show_list_validate_are_read_only(self):
        task = self.create()
        before = self.tree_snapshot()
        self.assertEqual(self.show(task)["id"], task["id"])
        listed = self.cli("list")
        self.assertIn(task["id"], [entry["id"] for entry in listed])
        self.assertTrue(self.cli("validate", task["id"])["valid"])
        self.assertTrue(self.cli("validate")["valid"])
        self.assertEqual(before, self.tree_snapshot())

    def test_show_recovers_summary_when_source_is_missing_without_rewriting_state(self):
        task = self.brief(self.create())
        (self.root / "context/input.md").unlink()
        before = self.tree_snapshot()
        shown = self.show(task)
        self.assertEqual(shown["id"], task["id"])
        self.assertEqual(shown["next_action"], task["next_action"])
        self.assertIn({"kind": "missing_source", "path": "context/input.md"}, shown["_diagnostics"])
        self.assertEqual(before, self.tree_snapshot())
        self.cli("validate", task["id"], ok=False)
        self.cli("event", task["id"], "--expect-version", task["version"], "--type", "checkpoint",
                 "--note", "缺少来源时不得继续写入", "--next-action", "等待同步来源", ok=False)
        self.assertEqual(before, self.tree_snapshot())

    def test_show_reports_missing_or_changed_accepted_artifact_but_keeps_resume_context(self):
        task = self.completed_task()
        artifact = self.root / task["artifacts"][0]["path"]
        artifact.write_text("旧版本被外部程序替换", encoding="utf-8")
        before = self.tree_snapshot()
        shown = self.show(task)
        self.assertEqual(shown["status"], "completed")
        self.assertEqual(shown["next_action"], task["next_action"])
        self.assertIn({"kind": "artifact_hash_mismatch", "path": "works/report-v1.html", "accepted": True}, shown["_diagnostics"])
        self.assertEqual(before, self.tree_snapshot())
        self.cli("validate", task["id"], ok=False)
        self.cli("event", task["id"], "--expect-version", task["version"], "--type", "reopen",
                 "--note", "旧版本被替换时不能推进", ok=False)
        artifact.unlink()
        before_missing = self.tree_snapshot()
        shown = self.show(task)
        self.assertIn({"kind": "missing_artifact", "path": "works/report-v1.html"}, shown["_diagnostics"])
        self.assertEqual(before_missing, self.tree_snapshot())

    def test_list_reports_bad_record_without_hiding_healthy_tasks(self):
        healthy = self.create()
        broken = self.create()
        self.canonical(broken).write_text('{"broken":', encoding="utf-8")
        before = self.tree_snapshot()
        listed = self.cli("list")
        entries = {item["id"]: item for item in listed}
        self.assertEqual(entries[healthy["id"]], healthy)
        self.assertIn("error", entries[broken["id"]])
        self.assertNotIn("status", entries[broken["id"]])
        self.assertEqual(before, self.tree_snapshot())
        self.cli("validate", ok=False)

    def test_alignment_requires_brief_and_user_confirmation(self):
        task = self.create()
        before = self.canonical(task).read_bytes()
        self.cli("event", task["id"], "--expect-version", 1, "--type", "align",
                 "--note", "未对齐", "--user-quote", "测试确认", ok=False)
        self.assertEqual(before, self.canonical(task).read_bytes())
        task = self.brief(task)
        self.cli("event", task["id"], "--expect-version", task["version"],
                 "--type", "align", "--note", "没有用户确认", ok=False)
        self.assertEqual(self.show(task)["status"], "clarifying")

    def test_multiple_feedback_rounds_keep_one_identity_and_history(self):
        task = self.working_task()
        identity = task["id"]
        task = self.event(task, "checkpoint", next_action="检查第一版")
        task = self.event(task, "review", artifact=self.artifact())
        task = self.event(task, "feedback", user_quote="测试用户：缩短文字。", scope="minor")
        self.assertEqual((task["id"], task["revision"], task["status"]), (identity, 2, "working"))
        task = self.event(task, "review", artifact=self.artifact("report-v2.html", "<h1>短稿</h1>"))
        task = self.event(task, "feedback", user_quote="测试用户：放大标题。", scope="minor")
        self.assertEqual(task["revision"], 3)
        task = self.event(task, "review", artifact=self.artifact("report-v3.html", "<h1>最终测试稿</h1>"))
        task = self.event(task, "complete", user_quote="测试用户：本轮可以。")
        self.assertEqual(task["status"], "completed")
        self.assertEqual(task["id"], identity)
        self.assertEqual(len(task["artifacts"]), 3)
        self.assertIn("缩短文字", json.dumps(task, ensure_ascii=False))
        self.assertIn("本轮可以", json.dumps(task, ensure_ascii=False))

    def test_scope_change_requires_new_alignment(self):
        task = self.working_task()
        task = self.event(task, "review", artifact=self.artifact())
        task = self.event(task, "feedback", scope="scope", user_quote="测试用户：改为另一种受众。")
        self.assertEqual(task["status"], "clarifying")
        self.assertEqual(task["revision"], 2)
        self.cli("event", task["id"], "--expect-version", task["version"], "--type", "start",
                 "--note", "跳过重新对齐", ok=False)
        task = self.brief(task, audience="另一类测试受众", output="works/report-v2.html")
        task = self.event(task, "align", user_quote="测试用户：新的范围已确认。")
        self.assertEqual(self.event(task, "start")["status"], "working")

    def test_scope_feedback_before_first_artifact_reopens_alignment(self):
        for initial_status in ("ready", "working"):
            with self.subTest(initial_status=initial_status):
                task = self.brief(self.create())
                task = self.event(task, "align", user_quote="测试用户：先按原范围。")
                if initial_status == "working":
                    task = self.event(task, "start")
                self.assertEqual(task["artifacts"], [])
                task = self.event(task, "feedback", scope="scope", user_quote="测试用户：先改受众。")
                self.assertEqual((task["status"], task["revision"]), ("clarifying", 2))
                task = self.brief(task, audience="修订后的测试受众")
                task = self.event(task, "align", user_quote="测试用户：新的受众确认。")
                self.assertEqual(self.event(task, "start")["status"], "working")

    def test_minor_feedback_in_ready_does_not_start_work_implicitly(self):
        task = self.brief(self.create())
        task = self.event(task, "align", user_quote="测试用户：目标确认。")
        task = self.event(task, "feedback", scope="minor", user_quote="测试用户：标题简洁些。")
        self.assertEqual((task["status"], task["revision"]), ("ready", 2))
        self.assertEqual(task["artifacts"], [])
        self.assertEqual(self.event(task, "start")["status"], "working")

    def test_ready_brief_cannot_silently_replace_confirmed_agreement(self):
        task = self.brief(self.create())
        task = self.event(task, "align", user_quote="测试用户：确认这个受众。")
        before = self.canonical(task).read_bytes()
        self.cli("brief", task["id"], "--expect-version", task["version"],
                 "--audience", "尚未讨论的另一个受众", ok=False)
        self.assertEqual(before, self.canonical(task).read_bytes())

    def test_validate_detects_changed_unaccepted_historical_artifact(self):
        task = self.working_task()
        artifact = self.artifact()
        task = self.event(task, "review", artifact=artifact)
        task = self.event(task, "feedback", scope="minor", user_quote="测试用户：继续修改。")
        (self.root / artifact).write_text("被外部程序改写的旧草稿", encoding="utf-8")
        # 仍可读取当前任务来处理问题，但显式完整校验必须发现旧版本不再可复现。
        self.assertEqual(self.show(task)["revision"], 2)
        self.cli("validate", task["id"], ok=False)

    def test_pause_and_resume_preserve_progress_in_new_process(self):
        task = self.working_task()
        task = self.event(task, "checkpoint", next_action="继续处理第二部分")
        task = self.event(task, "pause", next_action="等待补充输入后处理第二部分")
        self.assertEqual(task["status"], "paused")
        restored = self.show(task)
        self.assertIn("第二部分", restored["next_action"])
        self.assertEqual(self.event(restored, "resume")["status"], "working")

    def test_review_then_changed_artifact_cannot_be_completed(self):
        task = self.working_task()
        artifact = self.artifact()
        task = self.event(task, "review", artifact=artifact)
        (self.root / artifact).write_text("未经过本轮评审的替换内容", encoding="utf-8")
        before = self.canonical(task).read_bytes()
        self.cli("event", task["id"], "--expect-version", task["version"], "--type", "complete",
                 "--note", "试图跳过版本核对", "--user-quote", "测试用户：认可。", ok=False)
        self.assertEqual(before, self.canonical(task).read_bytes())

    def test_reopen_preserves_confirmed_version_and_requires_new_artifact_path(self):
        task = self.completed_task()
        old_artifact = (self.root / "works/report-v1.html").read_bytes()
        old_records = json.loads(json.dumps(task["artifacts"]))
        task = self.event(task, "reopen", scope="minor", user_quote="测试用户：再优化标题。")
        self.assertEqual((task["revision"], task["status"]), (2, "working"))
        self.assertEqual(task["artifacts"], old_records)
        self.cli("event", task["id"], "--expect-version", task["version"], "--type", "review",
                 "--note", "复用旧路径", "--artifact", "works/report-v1.html", ok=False)
        task = self.event(task, "review", artifact=self.artifact("report-v2.html", "新标题"))
        task = self.event(task, "complete", user_quote="测试用户：确认第二轮。")
        self.assertEqual(len(task["artifacts"]), 2)
        self.assertEqual((self.root / "works/report-v1.html").read_bytes(), old_artifact)

    def test_stale_version_is_rejected_without_lost_update(self):
        old = self.create()
        current = self.event(old, "checkpoint", next_action="讨论受众")
        before = self.canonical(current).read_bytes()
        self.cli("event", old["id"], "--expect-version", old["version"], "--type", "checkpoint",
                 "--note", "旧会话试图覆盖", "--next-action", "忽略新状态", ok=False)
        self.assertEqual(before, self.canonical(current).read_bytes())

    def test_unsafe_sources_and_outputs_are_rejected(self):
        for path in ("../outside.md", "/outside.md", "C:/outside.md", "vendor/input.md", "context/../input.md"):
            with self.subTest(source=path):
                task = self.create()
                self.cli("brief", task["id"], "--expect-version", 1, "--source", path, ok=False)
        for path in ("../output.html", "/output.html", "D:/output.html", "vendor/report.html", "works/vendor/report.html", "context/report.html"):
            with self.subTest(output=path):
                task = self.create()
                self.cli("brief", task["id"], "--expect-version", 1, "--output", path, ok=False)

    def test_source_must_exist_but_future_output_may_not(self):
        task = self.create()
        self.cli("brief", task["id"], "--expect-version", 1,
                 "--source", "context/not-present.md", ok=False)
        task = self.brief(task, output="works/not-yet-created/index.html")
        self.assertEqual(task["brief"]["output"], "works/not-yet-created/index.html")

    def test_symlink_escape_is_rejected(self):
        outside = self.base / "outside"
        outside.mkdir()
        (outside / "source.md").write_text("外部内容", encoding="utf-8")
        link = self.root / "context/escape"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError) as error:
            self.skipTest(f"当前系统不允许创建符号链接：{error}")
        task = self.create()
        self.cli("brief", task["id"], "--expect-version", 1,
                 "--source", "context/escape/source.md", ok=False)
        link.unlink()
        (self.root / "works/escape").symlink_to(outside, target_is_directory=True)
        self.cli("brief", task["id"], "--expect-version", 1,
                 "--output", "works/escape/new.html", ok=False)

    def test_rejects_vendor_root_and_infrastructure_root(self):
        vendor_root = self.root / "vendor/nested-consumer"
        self.make_consumer(vendor_root)
        self.cli("create", "--title", "不允许写", "--request", "不允许写", "--test",
                 root=vendor_root, ok=False)
        infra = self.base / "infrastructure"
        self.make_consumer(infra)
        (infra / "manifest.yml").write_text(
            "repository: suanhai-team-external-expression-infrastructure\n", encoding="utf-8")
        self.cli("create", "--title", "不允许写", "--request", "不允许写", "--test", root=infra, ok=False)

    def test_rejects_task_id_traversal(self):
        self.cli("show", "../outside", ok=False)
        self.cli("event", "../../outside", "--expect-version", 1, "--type", "checkpoint",
                 "--note", "不允许", ok=False)

    def test_existing_lock_prevents_concurrent_mutation(self):
        task = self.create()
        lock = self.canonical(task).with_name(".lock")
        lock.write_text("另一个进程持有写锁", encoding="utf-8")
        before = self.canonical(task).read_bytes()
        self.cli("event", task["id"], "--expect-version", 1, "--type", "checkpoint",
                 "--note", "并发写", "--next-action", "不应成功", ok=False)
        self.assertEqual(before, self.canonical(task).read_bytes())
        self.assertTrue(lock.exists(), "不能擅自清除其他进程的锁")

    def test_render_recovers_view_without_changing_canonical_version(self):
        task = self.create()
        canonical = self.canonical(task)
        view = canonical.with_name("task.md")
        before = canonical.read_bytes()
        view.unlink()
        self.show(task)
        self.assertFalse(view.exists(), "只读命令不得擅自重建视图")
        self.cli("render", task["id"], "--expect-version", task["version"])
        self.assertTrue(view.exists())
        self.assertIn(task["id"], view.read_text(encoding="utf-8"))
        self.assertEqual(before, canonical.read_bytes())

    def test_view_failure_reports_saved_json_and_can_be_recovered(self):
        task = self.create()
        canonical = self.canonical(task)
        view = canonical.with_name("task.md")
        view.unlink()
        view.mkdir()  # 用临时测试目录模拟视图不可替换，不改变系统权限。
        result = self.cli(
            "event", task["id"], "--expect-version", 1, "--type", "checkpoint",
            "--note", "保存待讨论问题", "--next-action", "讨论受众", ok=False,
        )
        self.assertIn("JSON", result.stderr)
        self.assertIn("render", result.stderr)
        saved = self.show(task)
        self.assertEqual(saved["version"], 2)
        self.assertEqual(saved["next_action"], "讨论受众")
        before = canonical.read_bytes()
        view.rmdir()
        self.cli("render", task["id"], "--expect-version", 2)
        self.assertTrue(view.is_file())
        self.assertEqual(before, canonical.read_bytes())

    def test_corrupted_history_or_artifact_is_rejected_without_traceback_or_write(self):
        task = self.completed_task()
        canonical = self.canonical(task)
        healthy = canonical.read_text(encoding="utf-8")
        cases = (
            ("history", "at", None),
            ("history", "kind", []),
            ("history", "revision", "1"),
            ("history", "next_action", 42),
            ("history", "user_quote", 42),
            ("artifacts", "reviewed_at", None),
            ("artifacts", "accepted_at", 0),
            ("artifacts", "completion_quote", []),
            ("artifacts", "revision", 0),
        )
        for collection, key, invalid in cases:
            with self.subTest(collection=collection, field=key):
                damaged = json.loads(healthy)
                damaged[collection][-1][key] = invalid
                canonical.write_text(json.dumps(damaged, ensure_ascii=False), encoding="utf-8")
                before = self.tree_snapshot()
                commands = (
                    ("validate", task["id"]),
                    ("render", task["id"], "--expect-version", task["version"]),
                )
                for arguments in commands:
                    result = self.cli(*arguments, ok=False)
                    self.assertNotIn("Traceback", result.stderr)
                    self.assertEqual(before, self.tree_snapshot())


if __name__ == "__main__":
    unittest.main()
