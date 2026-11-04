"""在真实临时 Git/submodule 中验证任务新修订的固定版本切换。"""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "infrastructure/task-loop/tools/task-record/task_loop.py"


class TaskInfrastructureRevisionTest(unittest.TestCase):
    def test_explicit_feedback_rebind_preserves_history_and_requires_committed_lock(self):
        with tempfile.TemporaryDirectory(prefix="task-infra-revision-") as folder:
            base = Path(folder)
            source, root = base / "source", base / "consumer"
            relative = "vendor/suanhai-team-external-expression-infrastructure"
            tool_relative = "infrastructure/task-loop/tools/task-record/task_loop.py"

            def git(directory, *args):
                result = subprocess.run(["git", "-C", str(directory), *args], capture_output=True, text=True, encoding="utf-8")
                self.assertEqual(result.returncode, 0, result.stderr)
                return result.stdout.strip()

            for directory in (source, root):
                directory.mkdir()
                git(directory, "init")
                git(directory, "config", "user.name", "Synthetic Test")
                git(directory, "config", "user.email", "synthetic@example.invalid")
            (source / tool_relative).parent.mkdir(parents=True)
            shutil.copy2(SCRIPT, source / tool_relative)
            git(source, "add", ".")
            git(source, "commit", "-m", "synthetic baseline")
            old = git(source, "rev-parse", "HEAD")
            for name in ("context", "tasks"):
                (root / name).mkdir()
            for name in ("README.md", "AGENTS.md", "context/source.md"):
                (root / name).write_text("中性测试输入，不是业务事实", encoding="utf-8")
            git(root, "-c", "protocol.file.allow=always", "submodule", "add", str(source), relative)
            git(root, "add", ".")
            git(root, "commit", "-m", "lock synthetic infrastructure")
            submodule = root / relative

            def cli(*args, ok=True):
                result = subprocess.run([sys.executable, str(submodule / tool_relative), "--root", str(root), *map(str, args)], capture_output=True, text=True, encoding="utf-8")
                self.assertEqual(result.returncode, 0 if ok else 1, result.stderr or result.stdout)
                return json.loads(result.stdout) if ok else result

            task = cli("create", "--title", "合成测试", "--request", "验证版本边界", "--test")
            identity = task["id"]
            task = cli("brief", identity, "--expect-version", 1, "--audience", "测试", "--purpose", "检查", "--scope", "合成", "--output", f"reports/{identity}", "--acceptance", "摘要一致", "--source", "context/source.md")
            cli("event", identity, "--expect-version", 2, "--type", "align", "--user-quote", "合成测试认可", "--note", "测试")
            cli("event", identity, "--expect-version", 3, "--type", "start", "--note", "测试")
            artifact = root / f"reports/{identity}/v001"
            artifact.mkdir(parents=True)
            (artifact / "index.html").write_text("合成旧版本", encoding="utf-8")
            task = cli("event", identity, "--expect-version", 4, "--type", "review", "--artifact", f"reports/{identity}/v001", "--note", "测试")
            old_artifacts = task["artifacts"]
            (source / "upgrade.md").write_text("合成升级", encoding="utf-8")
            git(source, "add", ".")
            git(source, "commit", "-m", "synthetic upgrade")
            new = git(source, "rev-parse", "HEAD")
            git(submodule, "fetch", "origin")
            git(submodule, "checkout", "--detach", new)
            args = ("event", identity, "--expect-version", 5, "--type", "feedback", "--infrastructure-commit", new, "--note", "合成换版")
            cli(*args, ok=False)  # 缺用户原话时拒绝。
            cli(*args, "--user-quote", "合成授权", ok=False)  # 未提交 gitlink 时拒绝。
            git(root, "add", relative)
            git(root, "commit", "-m", "lock synthetic upgrade")
            (submodule / "dirty.txt").write_text("合成脏文件", encoding="utf-8")
            cli(*args, "--user-quote", "合成授权", ok=False)
            (submodule / "dirty.txt").unlink()
            task = cli(*args, "--user-quote", "合成授权")
            self.assertEqual(task["revision"], 2)
            self.assertEqual(task["infrastructure_commit"], new)
            self.assertEqual(task["history"][-1]["infrastructure_change"], {"from": old, "to": new})
            self.assertEqual(task["artifacts"], old_artifacts)
            cli("validate", identity)


if __name__ == "__main__":
    unittest.main()
