"""验证 CI 分流不把发布、共享协议或无法比较的改动漏掉。"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("ci_checks", ROOT / "scripts/ci_checks.py")
ci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ci)


class CiChecksTest(unittest.TestCase):
    def test_develop_pr_is_quick_and_integrated_function_change_is_full(self):
        for path in ("infrastructure/html/runtime-kits/runtime-kit-v1/runtime.js", "manifest.yml", "workflows/html/production/ENTRYPOINT.md", "new-domain/tool.py"):
            self.assertEqual(ci.choose_suite("pull_request", "develop", [path])[0], "quick")
            self.assertEqual(ci.choose_suite("push", "", [path])[0], "full")

    def test_docs_are_narrowly_allowlisted(self):
        for path in ("README.md", "infrastructure/html/README.md", "docs/ci-validation.md"):
            self.assertEqual(ci.choose_suite("push", "", [path])[0], "quick")
        for path in ("AGENTS.md", "docs/submodule-consumer-versioning.md", "docs/consumer-repository-harness-v0.1.md", "workflows/submodule-update/ENTRYPOINT.md"):
            self.assertEqual(ci.choose_suite("push", "", [path])[0], "full")
        self.assertEqual(ci.choose_suite("push", "", ["README.md", "manifest.yml"])[0], "full")

    def test_release_manual_policy_change_and_unknown_diff_are_full(self):
        self.assertEqual(ci.choose_suite("pull_request", "main", ["README.md"])[0], "full")
        self.assertEqual(ci.choose_suite("workflow_dispatch", "", ["README.md"])[0], "full")
        for path in (".github/workflows/validate-manifest.yml", "scripts/ci_checks.py", "tests/test_ci_checks.py"):
            self.assertEqual(ci.choose_suite("pull_request", "develop", [path])[0], "full")
        for paths in (None, []):
            self.assertEqual(ci.choose_suite("push", "", paths)[0], "full")

    def test_git_comparison_failure_and_new_branch_do_not_guess(self):
        payload = {"before": "a" * 40, "after": "b" * 40}
        with patch.object(ci.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "git")):
            self.assertIsNone(ci.changed_paths("push", payload))
        payload["before"] = "0" * 40
        self.assertIsNone(ci.changed_paths("push", payload))

    def test_real_git_diff_includes_deleted_and_unicode_paths(self):
        with tempfile.TemporaryDirectory(prefix="ci-diff-") as directory:
            root = Path(directory)
            def git(*args):
                return subprocess.check_output(["git", "-C", str(root), *args], text=True, encoding="utf-8").strip()
            git("init", "--initial-branch=main")
            git("config", "user.name", "CI Policy Test")
            git("config", "user.email", "ci-policy@example.invalid")
            (root / "deleted.py").write_text("before", encoding="utf-8")
            (root / "rename.py").write_text("rename me", encoding="utf-8")
            git("add", ".")
            git("commit", "-m", "baseline")
            before = git("rev-parse", "HEAD")
            (root / "deleted.py").unlink()
            (root / "rename.py").rename(root / "README.md")
            (root / "说明.md").write_text("通用测试", encoding="utf-8")
            git("add", ".")
            git("commit", "-m", "changed")
            after = git("rev-parse", "HEAD")
            with patch.object(ci, "ROOT", root):
                changed = ci.changed_paths("push", {"before": before, "after": after})
            self.assertEqual(set(changed), {"deleted.py", "rename.py", "README.md", "说明.md"})
            self.assertEqual(ci.choose_suite("push", "", changed)[0], "full")

    def test_action_outputs_match_the_selected_event_scope(self):
        with tempfile.TemporaryDirectory(prefix="ci-event-") as directory:
            root = Path(directory)
            payload, output, summary = root / "event.json", root / "outputs", root / "summary.md"
            payload.write_text(json.dumps({"pull_request": {"base": {"ref": "develop"}}}), encoding="utf-8")
            env = {"GITHUB_EVENT_NAME": "pull_request", "GITHUB_EVENT_PATH": str(payload), "GITHUB_OUTPUT": str(output), "GITHUB_STEP_SUMMARY": str(summary)}
            with patch.dict(os.environ, env), patch.object(ci, "changed_paths", return_value=["infrastructure/html/tool.py"]), patch.object(ci.sys, "argv", ["ci_checks.py", "plan"]):
                self.assertEqual(ci.main(), 0)
            self.assertEqual(output.read_text(encoding="utf-8"), "suite=quick\n")
            self.assertIn("develop PR", summary.read_text(encoding="utf-8"))

    def test_quick_filter_keeps_new_modules_and_load_failures(self):
        def case(module):
            definition = type("Example", (unittest.TestCase,), {"__module__": module, "test_run": lambda self: None})
            return definition("test_run")
        slow, new, broken = case("test_html_materialize"), case("test_new_capability"), case("unittest.loader")
        for name, expected in (("quick", [new.id(), broken.id()]), ("full", [slow.id(), new.id(), broken.id()])):
            suite = unittest.TestSuite([unittest.TestSuite([slow, new]), broken])
            with patch.object(ci.unittest.defaultTestLoader, "discover", return_value=suite), patch.object(ci.unittest, "TextTestRunner") as runner:
                runner.return_value.run.return_value.wasSuccessful.return_value = False
                self.assertEqual(ci.run_suite(name), 1)
                selected = runner.return_value.run.call_args.args[0]
                self.assertEqual([test.id() for test in ci.leaves(selected)], expected)

    def test_empty_discovery_is_not_a_success(self):
        with patch.object(ci.unittest.defaultTestLoader, "discover", return_value=unittest.TestSuite()):
            self.assertEqual(ci.run_suite("full"), 1)

    def test_final_gate_requires_selected_checks_not_just_manifest_validation(self):
        for suite in ("quick", "full"):
            results = {"validation": "success", "quick": "skipped", "full": "skipped", suite: "success"}
            self.assertTrue(ci.checks_passed(suite, results))
            for failure in ("failure", "cancelled", "skipped", ""):
                self.assertFalse(ci.checks_passed(suite, {**results, suite: failure}))
                self.assertFalse(ci.checks_passed(suite, {**results, "validation": failure}))
        self.assertFalse(ci.checks_passed("", {"validation": "success", "quick": "success", "full": "success"}))


if __name__ == "__main__":
    unittest.main()
