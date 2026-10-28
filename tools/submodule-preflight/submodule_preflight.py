#!/usr/bin/env python3
"""只读核对消费端的 submodule gitlink、工作树和远端稳定分支。"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from typing import Any, Iterable
from urllib.parse import urlsplit, urlunsplit


SHA = re.compile(r"\A[0-9a-f]{40}\Z")
DEFAULT_REMOTE_REF = "refs/heads/main"
EXIT_CHECK_FAILED = 1
EXIT_USAGE_OR_ENVIRONMENT = 2


class PreflightError(Exception):
    """输入、Git 环境或只读命令失败；不会尝试修复。"""


@dataclass(frozen=True)
class GitResult:
    stdout: str
    stderr: str
    returncode: int


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_git(args: Iterable[str], *, cwd: Path, timeout: float) -> GitResult:
    """以参数数组调用 Git，避免 shell 解释；所有调用均为查询命令。"""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as error:
        raise PreflightError("找不到 git；预检没有执行任何写入操作") from error
    except subprocess.TimeoutExpired as error:
        raise PreflightError("git 查询超时；远端检查可能受网络或凭据助手影响") from error
    return GitResult(result.stdout, result.stderr, result.returncode)


def require_git(result: GitResult, description: str) -> str:
    if result.returncode != 0:
        raise PreflightError(f"{description}失败（git exit {result.returncode}）")
    return result.stdout


def validate_relative_path(value: str) -> str:
    if not value or "\\" in value or ":" in value:
        raise PreflightError("submodule 路径必须是非空仓库相对 POSIX 路径")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise PreflightError("submodule 路径不允许绝对路径、空片段、. 或 ..")
    return "/".join(path.parts)


def resolve_root(value: str) -> Path:
    root = Path(value).expanduser().resolve()
    if not root.is_dir():
        raise PreflightError("消费端根目录不存在")
    top = require_git(run_git(["rev-parse", "--show-toplevel"], cwd=root, timeout=5), "读取父仓库根目录").strip()
    if Path(top).resolve() != root:
        raise PreflightError("--root 必须指向父仓库根目录")
    return root


def configured_paths(root: Path, timeout: float) -> list[str]:
    modules = root / ".gitmodules"
    if not modules.is_file():
        raise PreflightError("未提供 --path，且父仓库没有 .gitmodules")
    result = run_git(
        ["config", "--file", ".gitmodules", "--get-regexp", r"^submodule\..*\.path$"],
        cwd=root,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise PreflightError(".gitmodules 中没有可读取的 submodule path")
    paths = []
    for line in result.stdout.splitlines():
        fields = line.split(None, 1)
        if len(fields) != 2:
            raise PreflightError(".gitmodules 的 submodule path 格式无法解析")
        paths.append(validate_relative_path(fields[1].strip()))
    if not paths:
        raise PreflightError(".gitmodules 中没有可读取的 submodule path")
    return paths


def path_in_root(root: Path, relative: str) -> Path:
    path = root.joinpath(*relative.split("/"))
    if path.is_symlink():
        raise PreflightError(f"submodule 路径不允许是符号链接：{relative}")
    try:
        path.resolve().relative_to(root)
    except ValueError as error:
        raise PreflightError(f"submodule 路径越出父仓库：{relative}") from error
    return path


def parse_tree_sha(stdout: str, relative: str) -> str:
    records = [record for record in stdout.split("\0") if record]
    matching = []
    for record in records:
        header, separator, path = record.partition("\t")
        fields = header.split()
        if separator and path == relative and len(fields) == 3:
            matching.append((fields[0], fields[1], fields[2]))
    if len(matching) != 1:
        raise PreflightError(f"父仓库 HEAD 中没有唯一的 gitlink：{relative}")
    mode, kind, sha = matching[0]
    if mode != "160000" or kind != "commit" or not SHA.fullmatch(sha):
        raise PreflightError(f"父仓库 HEAD 中的条目不是合法 gitlink：{relative}")
    return sha


def parse_index_sha(stdout: str, relative: str) -> tuple[str | None, bool]:
    records = [record for record in stdout.split("\0") if record]
    matching = []
    for record in records:
        header, separator, path = record.partition("\t")
        fields = header.split()
        if separator and path == relative and len(fields) == 3:
            matching.append((fields[0], fields[1], fields[2]))
    if len(matching) != 1:
        return None, False
    mode, sha, stage = matching[0]
    if mode != "160000" or stage != "0" or not SHA.fullmatch(sha):
        return None, False
    return sha, True


def check(name: str, status: str, message: str, **details: Any) -> dict[str, Any]:
    result: dict[str, Any] = {"name": name, "status": status, "message": message}
    if details:
        result["details"] = details
    return result


def redact_url(value: str) -> str:
    value = value.strip()
    try:
        parsed = urlsplit(value)
    except ValueError:
        return "<configured remote>"
    if parsed.scheme and parsed.netloc:
        return urlunsplit((parsed.scheme, parsed.hostname or "", parsed.path, "", ""))
    if "@" in value and ":" in value:
        return value.rsplit("@", 1)[-1]
    return value.split("?", 1)[0].split("#", 1)[0]


def remote_url(submodule: Path, remote_name: str, timeout: float) -> tuple[str | None, str | None]:
    result = run_git(["-C", str(submodule), "remote", "get-url", remote_name], cwd=submodule.parent, timeout=timeout)
    if result.returncode != 0:
        return None, None
    value = result.stdout.strip()
    return value, redact_url(value)


def inspect_submodule(
    root: Path,
    relative: str,
    *,
    remote_name: str,
    remote_ref: str,
    candidate: str | None,
    require_remote_head: bool,
    skip_remote: bool,
    timeout: float,
) -> dict[str, Any]:
    relative = validate_relative_path(relative)
    submodule = path_in_root(root, relative)
    result: dict[str, Any] = {
        "path": relative,
        "remote_name": remote_name,
        "remote_ref": remote_ref,
        "candidate": candidate,
        "checks": [],
    }
    checks: list[dict[str, Any]] = result["checks"]

    parent_head = require_git(run_git(["rev-parse", "HEAD"], cwd=root, timeout=timeout), "读取父仓库 HEAD").strip()
    result["parent_head"] = parent_head
    committed = parse_tree_sha(
        require_git(run_git(["ls-tree", "-z", "HEAD", "--", relative], cwd=root, timeout=timeout), "读取父仓库 gitlink"),
        relative,
    )
    result["gitlink_committed"] = committed

    index_sha, index_valid = parse_index_sha(
        require_git(run_git(["ls-files", "--stage", "-z", "--", relative], cwd=root, timeout=timeout), "读取父仓库 index"),
        relative,
    )
    result["gitlink_index"] = index_sha
    checks.append(check("index_matches_gitlink", "pass" if index_valid and index_sha == committed else "fail", "index gitlink 与 HEAD 一致" if index_valid and index_sha == committed else "index gitlink 缺失、冲突或与 HEAD 不一致", expected=committed, actual=index_sha))

    parent_status = run_git(["status", "--porcelain=v1", "--untracked-files=all", "--", relative], cwd=root, timeout=timeout)
    if parent_status.returncode != 0:
        raise PreflightError("读取父仓库 submodule 状态失败")
    parent_clean = not parent_status.stdout.strip()
    checks.append(check("parent_path_clean", "pass" if parent_clean else "fail", "父仓库中 submodule 路径干净" if parent_clean else "父仓库中 submodule gitlink 有未提交变化"))

    initialized = submodule.is_dir()
    result["initialized"] = initialized
    if not initialized:
        checks.append(check("submodule_initialized", "fail", "submodule 工作树不存在或尚未初始化"))
        result["status"] = "missing"
        result["ok"] = False
        return result
    try:
        head = require_git(run_git(["-C", str(submodule), "rev-parse", "HEAD"], cwd=root, timeout=timeout), "读取 submodule HEAD").strip()
    except PreflightError:
        checks.append(check("submodule_initialized", "fail", "submodule 目录不是可读取的 Git 工作树"))
        result["status"] = "missing"
        result["ok"] = False
        return result
    if not SHA.fullmatch(head):
        raise PreflightError("submodule HEAD 不是完整 commit SHA")
    result["submodule_head"] = head
    checks.append(check("submodule_initialized", "pass", "submodule HEAD 可读取"))
    checks.append(check("gitlink_matches_head", "pass" if head == committed else "fail", "submodule HEAD 与父仓库 gitlink 一致" if head == committed else "submodule HEAD 与父仓库 gitlink 不一致", expected=committed, actual=head))

    submodule_status = run_git(["-C", str(submodule), "status", "--porcelain=v1", "--untracked-files=all"], cwd=root, timeout=timeout)
    if submodule_status.returncode != 0:
        raise PreflightError("读取 submodule 工作树状态失败")
    submodule_clean = not submodule_status.stdout.strip()
    result["submodule_clean"] = submodule_clean
    checks.append(check("submodule_worktree_clean", "pass" if submodule_clean else "fail", "submodule 工作树干净" if submodule_clean else "submodule 工作树有未提交变化"))

    object_check = run_git(["-C", str(submodule), "cat-file", "-e", f"{committed}^{{commit}}"], cwd=root, timeout=timeout)
    object_ok = object_check.returncode == 0
    checks.append(check("gitlink_object_available", "pass" if object_ok else "fail", "gitlink commit 对象可读取" if object_ok else "gitlink commit 对象在 submodule 中不可读取", commit=committed))

    if candidate is not None:
        candidate_ok = bool(SHA.fullmatch(candidate))
        if candidate_ok:
            candidate_check = run_git(["-C", str(submodule), "cat-file", "-e", f"{candidate}^{{commit}}"], cwd=root, timeout=timeout)
            candidate_ok = candidate_check.returncode == 0
        checks.append(check("candidate_object_available", "pass" if candidate_ok else "fail", "候选 commit 对象可读取" if candidate_ok else "候选 commit 不是完整 SHA 或对象不可读取", candidate=candidate))
        result["candidate_available"] = candidate_ok

    raw_url, safe_url = remote_url(submodule, remote_name, timeout)
    result["remote_url"] = safe_url
    remote_sha: str | None = None
    if skip_remote:
        checks.append(check("remote_ref", "skip", "按参数跳过远端只读检查"))
    elif raw_url is None:
        checks.append(check("remote_ref", "fail", f"submodule 没有可读取的远端 {remote_name}"))
    else:
        remote_result = run_git(["-C", str(submodule), "ls-remote", "--refs", remote_name, remote_ref], cwd=root, timeout=timeout)
        if remote_result.returncode == 0:
            rows = [line.split() for line in remote_result.stdout.splitlines() if line.strip()]
            matches = [row for row in rows if len(row) >= 2 and row[1] == remote_ref and SHA.fullmatch(row[0])]
            if len(matches) == 1:
                remote_sha = matches[0][0]
                result["remote_sha"] = remote_sha
                checks.append(check("remote_ref", "pass", "远端稳定分支指针可读取", sha=remote_sha))
            else:
                checks.append(check("remote_ref", "fail", "远端稳定分支未返回唯一合法 commit SHA"))
        else:
            checks.append(check("remote_ref", "fail", "远端稳定分支只读查询失败"))

    expected_remote = candidate or committed
    if remote_sha is not None and remote_sha != expected_remote:
        status = "fail" if require_remote_head else "warn"
        checks.append(check("remote_matches_expected", status, "远端指针与固定版本不同；这不代表可自动升级" if status == "warn" else "远端指针不符合显式要求", expected=expected_remote, actual=remote_sha))
    elif remote_sha is not None:
        checks.append(check("remote_matches_expected", "pass", "远端指针与要求的 commit 一致", expected=expected_remote, actual=remote_sha))
    elif not skip_remote:
        checks.append(check("remote_matches_expected", "fail", "无法比较远端指针与固定版本"))

    failed_names = {item["name"] for item in checks if item["status"] == "fail"}
    if not initialized or "gitlink_object_available" in failed_names:
        result["status"] = "missing"
    elif {"parent_path_clean", "submodule_worktree_clean"} & failed_names:
        result["status"] = "dirty"
    elif candidate is not None and candidate != committed:
        result["status"] = "update-available"
    elif remote_sha is None:
        result["status"] = "unknown"
    elif remote_sha != expected_remote:
        result["status"] = "update-available"
    else:
        result["status"] = "locked"
    result["ok"] = not failed_names
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="消费端父仓库根目录")
    parser.add_argument("--path", action="append", help="submodule 仓库相对 POSIX 路径，可重复；默认从 .gitmodules 读取")
    parser.add_argument("--remote-name", default="origin", help="只读远端名称，默认 origin")
    parser.add_argument("--remote-ref", default=DEFAULT_REMOTE_REF, help="只读远端 ref，默认 refs/heads/main")
    parser.add_argument("--candidate", help="显式升级候选 commit 的完整 40 位 SHA；仅观察，不会 checkout")
    parser.add_argument("--require-remote-head", action="store_true", help="要求远端 ref 指向 candidate（无 candidate 时指向当前 gitlink）")
    parser.add_argument("--skip-remote", action="store_true", help="显式跳过远端查询；输出会标为 skip")
    parser.add_argument("--timeout", type=float, default=15.0, help="每个 Git 查询的超时时间（秒）")
    parser.add_argument("--format", choices=("json", "text"), default="json", help="输出格式，默认 json")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.timeout <= 0:
            raise PreflightError("--timeout 必须大于 0")
        if args.candidate is not None and not SHA.fullmatch(args.candidate):
            raise PreflightError("--candidate 必须是完整的 40 位小写 commit SHA")
        if not args.remote_name or any(char.isspace() for char in args.remote_name):
            raise PreflightError("--remote-name 必须是非空 Git 远端名称")
        if not args.remote_ref.startswith("refs/") or any(char.isspace() for char in args.remote_ref):
            raise PreflightError("--remote-ref 必须是 refs/ 下的完整 ref")
        root = resolve_root(args.root)
        paths = [validate_relative_path(path) for path in args.path] if args.path else configured_paths(root, args.timeout)
        if len(set(paths)) != len(paths):
            raise PreflightError("submodule 路径不能重复")
        modules = [inspect_submodule(root, path, remote_name=args.remote_name, remote_ref=args.remote_ref, candidate=args.candidate, require_remote_head=args.require_remote_head, skip_remote=args.skip_remote, timeout=args.timeout) for path in paths]
        payload: dict[str, Any] = {"schema_version": 1, "tool": "consumer.submodule-preflight", "observed_at": utc_now(), "root": str(root), "ok": all(item["ok"] for item in modules), "submodules": modules}
        if args.format == "json":
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"submodule preflight: {'PASS' if payload['ok'] else 'FAIL'}")
            for item in modules:
                print(f"- {item['path']}: {item.get('status', 'unknown')} ({item.get('gitlink_committed', 'unknown')})")
                for entry in item["checks"]:
                    print(f"  [{entry['status']}] {entry['name']}: {entry['message']}")
        return 0 if payload["ok"] else EXIT_CHECK_FAILED
    except PreflightError as error:
        payload = {"schema_version": 1, "tool": "consumer.submodule-preflight", "observed_at": utc_now(), "ok": False, "error": str(error)}
        if args.format == "json":
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"submodule preflight: ERROR: {error}")
        return EXIT_USAGE_OR_ENVIRONMENT


if __name__ == "__main__":
    sys.exit(main())
