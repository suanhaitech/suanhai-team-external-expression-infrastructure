"""submodule 预检只读行为和固定 gitlink 协议的回归测试。"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "tools/submodule-preflight/submodule_preflight.py"


class SubmodulePreflightTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="submodule-preflight-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.remote = self.base / "remote.git"
        self.infra = self.base / "infra"
        self.consumer = self.base / "consumer"
        self.git("init", "--bare", str(self.remote), cwd=self.base)
        self.git("init", str(self.infra), cwd=self.base)
        self.git("-C", str(self.infra), "config", "user.email", "test@example.invalid", cwd=self.base)
        self.git("-C", str(self.infra), "config", "user.name", "Preflight Test", cwd=self.base)
        (self.infra / "manifest.yml").write_text("schema_version: 1\n", encoding="utf-8")
        self.git("-C", str(self.infra), "add", "manifest.yml", cwd=self.base)
        self.git("-C", str(self.infra), "commit", "-m", "initial", cwd=self.base)
        self.git("-C", str(self.infra), "branch", "-M", "main", cwd=self.base)
        self.git("-C", str(self.infra), "remote", "add", "origin", str(self.remote), cwd=self.base)
        self.git("-C", str(self.infra), "push", "-u", "origin", "main", cwd=self.base)
        self.git("--git-dir", str(self.remote), "symbolic-ref", "HEAD", "refs/heads/main", cwd=self.base)
        self.git("--git-dir", str(self.remote), "symbolic-ref", "HEAD", "refs/heads/main", cwd=self.base)
        self.infra_sha = self.git("-C", str(self.infra), "rev-parse", "HEAD", cwd=self.base).stdout.strip()
        self.git("init", str(self.consumer), cwd=self.base)
        self.git("-C", str(self.consumer), "config", "user.email", "test@example.invalid", cwd=self.base)
        self.git("-C", str(self.consumer), "config", "user.name", "Preflight Test", cwd=self.base)
        (self.consumer / "README.md").write_text("test consumer\n", encoding="utf-8")
        self.git("-C", str(self.consumer), "add", "README.md", cwd=self.base)
        self.git("-C", str(self.consumer), "commit", "-m", "consumer", cwd=self.base)
        self.git("-c", "protocol.file.allow=always", "-C", str(self.consumer), "submodule", "add", str(self.remote), "vendor/infra", cwd=self.base)
        self.git("-C", str(self.consumer), "commit", "-am", "pin infra", cwd=self.base)

    @staticmethod
    def git(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
        # 测试使用临时 bare 仓库模拟远端；只给该测试进程开放 file 协议，
        # 生产预检工具仍不会修改 Git 协议配置或主动初始化 submodule。
        environment = {**__import__("os").environ, "GIT_ALLOW_PROTOCOL": "file"}
        return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True, encoding="utf-8", env=environment)

    def cli(self, *args: str, ok: bool = True, explicit_path: bool = True) -> tuple[int, dict]:
        command = [sys.executable, str(SCRIPT), "--root", str(self.consumer)]
        if explicit_path:
            command.extend(("--path", "vendor/infra"))
        command.extend(args)
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
        payload = json.loads(result.stdout)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        return result.returncode, payload

    def test_clean_fixed_gitlink_and_remote_main_pass(self):
        code, payload = self.cli("--require-remote-head")
        self.assertEqual(code, 0)
        self.assertTrue(payload["ok"])
        item = payload["submodules"][0]
        self.assertEqual(item["gitlink_committed"], self.infra_sha)
        self.assertEqual(item["submodule_head"], self.infra_sha)
        self.assertEqual(item["remote_sha"], self.infra_sha)
        self.assertEqual(item["status"], "locked")

    def test_path_defaults_to_gitmodules(self):
        code, payload = self.cli("--skip-remote", explicit_path=False)
        self.assertEqual(code, 0)
        self.assertEqual([item["path"] for item in payload["submodules"]], ["vendor/infra"])

    def test_dirty_submodule_fails_without_modifying_state(self):
        target = self.consumer / "vendor/infra" / "local.txt"
        target.write_text("uncommitted\n", encoding="utf-8")
        before = self.git("-C", str(self.consumer), "status", "--porcelain=v1", cwd=self.base).stdout
        code, payload = self.cli(ok=False)
        after = self.git("-C", str(self.consumer), "status", "--porcelain=v1", cwd=self.base).stdout
        self.assertEqual(code, 1)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["submodules"][0]["status"], "dirty")
        self.assertEqual(before, after)

    def test_remote_drift_is_warning_unless_required(self):
        (self.infra / "next.txt").write_text("next\n", encoding="utf-8")
        self.git("-C", str(self.infra), "add", "next.txt", cwd=self.base)
        self.git("-C", str(self.infra), "commit", "-m", "next", cwd=self.base)
        self.git("-C", str(self.infra), "push", cwd=self.base)
        code, payload = self.cli()
        self.assertEqual(code, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["submodules"][0]["status"], "update-available")
        checks = payload["submodules"][0]["checks"]
        self.assertEqual(next(item for item in checks if item["name"] == "remote_matches_expected")["status"], "warn")
        code, payload = self.cli("--require-remote-head", ok=False)
        self.assertEqual(code, 1)
        self.assertFalse(payload["ok"])

    def test_skip_remote_has_explicit_skip_result(self):
        code, payload = self.cli("--skip-remote")
        self.assertEqual(code, 0)
        remote_check = next(item for item in payload["submodules"][0]["checks"] if item["name"] == "remote_ref")
        self.assertEqual(remote_check["status"], "skip")


if __name__ == "__main__":
    unittest.main()
