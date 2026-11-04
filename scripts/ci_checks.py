"""CI 的两档检查：快速反馈与完整回归，不复制消费端的能力入口。

develop PR 先快速检查，集成提交再完整验证；main PR 与 CI 策略本身的改动
提前全量。普通说明可走快速档；不确定的差异按功能改动处理，不能默默漏测。
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
# 这些模块需要反复创建 Git 仓库/submodule，是全量回归耗时的主要来源。
# 新测试默认进入快速档；这里只显式排除已知的慢集成模块，不维护第二份测试清单。
FULL_ONLY = {
    "test_group_asset_bootstrap", "test_html_materialize",
    "test_infrastructure_adoption_harness", "test_submodule_preflight",
    "test_task_loop", "test_task_infrastructure_revision",
}


def choose_suite(event: str, base_branch: str, paths: list[str] | None) -> tuple[str, str]:
    if event == "workflow_dispatch":
        return "full", "手动完整回归"
    if event == "pull_request" and base_branch == "main":
        return "full", "进入稳定分支前完整回归"
    if not paths:
        return "full", "差异不可确定或为空，保守执行完整回归"
    if any(path.startswith((".github/", "scripts/")) or path == "tests/test_ci_checks.py" for path in paths):
        return "full", "CI 策略或校验脚本有变化，提前完整验证"
    # 窄白名单避免把可执行工作流、Harness 和版本协议都当普通文档跳过。
    docs_only = all(
        Path(path).name == "README.md"
        or path in {"docs/ci-validation.md", "docs/html-interaction-components.md"}
        for path in paths
    )
    if docs_only:
        return "quick", "仅普通说明文档，运行快速契约与组件检查"
    if event == "pull_request" and base_branch == "develop":
        return "quick", "develop PR 快速反馈，集成提交执行完整回归"
    return "full", "集成提交、未知路径或事件，执行完整回归"


def changed_paths(event: str, payload: dict) -> list[str] | None:
    if event == "pull_request":
        before = payload["pull_request"]["base"]["sha"]
        after = payload["pull_request"]["head"]["sha"]
    elif event == "push":
        before, after = payload["before"], payload["after"]
    else:
        return None
    # 新分支或旧对象不可读取时不猜测差异，让上层选全量。
    if before == "0" * 40:
        return None
    try:
        result = subprocess.run(
            # 关闭重命名合并：把脚本重命名为 README 时，也必须看到旧脚本的删除。
            ["git", "diff", "--no-renames", "--name-only", "-z", before, after, "--"], cwd=ROOT,
            capture_output=True, check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return [path for path in result.stdout.decode("utf-8").split("\0") if path]


def leaves(suite):
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            yield from leaves(test)
        else:
            yield test


def run_suite(name: str) -> int:
    sys.path.insert(0, str(ROOT / "tests"))
    discovered = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_*.py")
    if name == "quick":
        # 保留加载失败的测试，让导入错误真实失败，不能被选择逻辑过滤掉。
        tests = [test for test in leaves(discovered) if test.id().split(".")[0] not in FULL_ONLY]
        discovered = unittest.TestSuite(tests)
    count = discovered.countTestCases()
    print(f"CI suite: {name}; tests: {count}", flush=True)
    if count == 0:
        print("未发现测试，拒绝把空测试集当作成功", file=sys.stderr)
        return 1
    result = unittest.TextTestRunner(verbosity=2).run(discovered)
    return 0 if result.wasSuccessful() else 1


def checks_passed(suite: str, results: dict[str, str]) -> bool:
    """保留服务器要求的 manifest 名称，但让最终绿灯覆盖本次应跑的测试。"""
    required = {"quick": "quick", "full": "full"}.get(suite)
    other = "full" if required == "quick" else "quick"
    return bool(required and results.get("validation") == "success"
                and results.get(required) == "success" and results.get(other) == "skipped")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "run", "gate"))
    parser.add_argument("--suite", choices=("quick", "full"), default="full")
    args = parser.parse_args()
    if args.command == "run":
        return run_suite(args.suite)
    if args.command == "gate":
        results = {name: os.environ.get("CI_" + name.upper(), "") for name in ("validation", "quick", "full")}
        passed = checks_passed(os.environ.get("CI_SUITE", ""), results)
        print(json.dumps({"passed": passed, "jobs": results}))
        return 0 if passed else 1
    event = os.environ.get("GITHUB_EVENT_NAME", "workflow_dispatch")
    payload = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8")) if "GITHUB_EVENT_PATH" in os.environ else {}
    base = payload.get("pull_request", {}).get("base", {}).get("ref", "")
    paths = changed_paths(event, payload)
    suite, reason = choose_suite(event, base, paths)
    print(json.dumps({"suite": suite, "reason": reason, "changed_files": paths}, ensure_ascii=False))
    if output := os.environ.get("GITHUB_OUTPUT"):
        with Path(output).open("a", encoding="utf-8") as stream:
            stream.write(f"suite={suite}\n")
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(summary).open("a", encoding="utf-8") as stream:
            stream.write(f"### 验证范围\n\n- 检查档位：`{suite}`\n- 原因：{reason}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
