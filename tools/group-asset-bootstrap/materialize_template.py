#!/usr/bin/env python3
"""将固定版本的小组资产仓模板安全铺设到消费端仓库；只用 Python 标准库。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
from typing import Iterable


REPOSITORY = "suanhai-team-external-expression-infrastructure"
SUBMODULE_PATH = Path("vendor") / REPOSITORY
TEMPLATE_PATH = Path("templates") / "group-asset-repository-v1"


class BootstrapError(Exception):
    """安全前置条件不满足或模板目标存在冲突。"""


def is_link(path: Path) -> bool:
    """同时识别符号链接和 Windows junction，避免目录重定向绕过边界。"""
    if path.is_symlink():
        return True
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except (FileNotFoundError, NotADirectoryError):
        return False
    return bool(attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise BootstrapError(f"git {' '.join(arguments)} 失败：{detail}")
    return result.stdout.strip()


def assert_submodule_lock(root: Path, infrastructure: Path) -> str:
    configured_paths = git(root, "config", "--file", ".gitmodules", "--get-regexp", r"^submodule\..*\.path$")
    configured = {}
    for line in configured_paths.splitlines():
        key, value = line.split(None, 1)
        if value == SUBMODULE_PATH.as_posix():
            configured[key[:-5]] = value
    if len(configured) != 1:
        raise BootstrapError(f".gitmodules 中必须唯一登记 {SUBMODULE_PATH.as_posix()} submodule")
    section = next(iter(configured))
    url = git(root, "config", "--file", ".gitmodules", "--get", f"{section}.url")
    expected_url = f"https://github.com/suanhaitech/{REPOSITORY}.git"
    if url != expected_url:
        raise BootstrapError(f"基础设施 submodule URL 应为 {expected_url}，实际为 {url}")

    index = git(root, "ls-files", "--stage", "--", SUBMODULE_PATH.as_posix())
    entries = [line for line in index.splitlines() if line]
    if len(entries) != 1 or not entries[0].startswith("160000 "):
        raise BootstrapError(f"{SUBMODULE_PATH.as_posix()} 尚未作为 Git submodule 固定在父仓 index 中")
    fields = entries[0].split()
    if fields[2] != "0":
        raise BootstrapError("基础设施 gitlink 尚有未解决的合并冲突")
    gitlink = fields[1]

    manifest = infrastructure / "manifest.yml"
    if not manifest.is_file() or REPOSITORY not in manifest.read_text(encoding="utf-8-sig"):
        raise BootstrapError("submodule 中找不到预期的基础设施 Manifest")
    checked_out = git(infrastructure, "rev-parse", "HEAD")
    if checked_out != gitlink:
        raise BootstrapError(f"submodule HEAD ({checked_out}) 与父仓 gitlink ({gitlink}) 不一致")
    dirty = git(infrastructure, "status", "--porcelain")
    if dirty:
        raise BootstrapError("基础设施 submodule 工作区不干净；请先恢复到固定提交，工具不会修改 submodule")
    expected_script = infrastructure / "tools/group-asset-bootstrap/materialize_template.py"
    if Path(__file__).resolve() != expected_script.resolve():
        raise BootstrapError("必须从当前固定 commit 的 submodule 内运行本工具")
    return gitlink


def template_files(template_root: Path) -> list[tuple[Path, bytes]]:
    if not template_root.is_dir():
        raise BootstrapError(f"小组资产仓模板不存在：{template_root}")
    result: list[tuple[Path, bytes]] = []
    for path in sorted(template_root.rglob("*")):
        if is_link(path):
            raise BootstrapError(f"模板不允许包含符号链接：{path}")
        if path.is_file():
            result.append((path.relative_to(template_root), path.read_bytes()))
    if not result:
        raise BootstrapError("模板目录没有可铺设文件")
    return result


def plan_files(root: Path, files: Iterable[tuple[Path, bytes]]) -> tuple[list[tuple[Path, bytes]], list[str], list[str]]:
    writes: list[tuple[Path, bytes]] = []
    unchanged: list[str] = []
    conflicts: list[str] = []
    for relative, content in files:
        if relative.is_absolute() or not relative.parts or ".." in relative.parts:
            raise BootstrapError(f"模板路径必须是仓库内相对路径：{relative}")
        destination = root / relative
        if any(part.casefold() in {".git", "vendor"} for part in relative.parts):
            raise BootstrapError(f"模板文件不允许写入 .git 或 vendor：{relative.as_posix()}")
        resolved = destination.resolve(strict=False)
        try:
            resolved.relative_to(root)
        except ValueError:
            conflicts.append(f"{relative.as_posix()}（目标路径通过符号链接越出仓库根目录）")
            continue
        parent = destination.parent
        while parent != root:
            if is_link(parent):
                conflicts.append(f"{relative.as_posix()}（父目录包含符号链接或 junction）")
                break
            if parent.exists() and not parent.is_dir():
                conflicts.append(f"{relative.as_posix()}（父路径不是目录）")
                break
            parent = parent.parent
        if is_link(destination):
            conflicts.append(f"{relative.as_posix()}（目标文件是符号链接）")
        elif destination.exists() and not destination.is_file():
            conflicts.append(f"{relative.as_posix()}（目标类型不是普通文件）")
        elif destination.is_file():
            if destination.read_bytes() == content:
                unchanged.append(relative.as_posix())
            else:
                conflicts.append(f"{relative.as_posix()}（已有不同内容）")
        else:
            writes.append((destination, content))
    return writes, unchanged, conflicts


def apply_files(root: Path, writes: list[tuple[Path, bytes]]) -> None:
    """以一次可清理的安装过程写入模板文件。

    先在临时 staging 目录备齐文件，再独占创建目标，拒绝覆盖预检之后
    新出现的文件。普通写入异常时只回滚本次创建的文件和空目录。
    这不是并发或断电事务；调用者应避免并行修改同一目标目录。
    """
    if not writes:
        return

    staging = Path(tempfile.mkdtemp(prefix=".group-asset-template-", dir=root))
    installed: list[Path] = []
    created_directories: list[Path] = []
    failure: Exception | None = None
    cleanup_errors: list[str] = []
    try:
        staged_files: list[tuple[Path, Path]] = []
        for destination, content in writes:
            relative = destination.relative_to(root)
            staged = staging / relative
            staged.parent.mkdir(parents=True, exist_ok=True)
            staged.write_bytes(content)
            staged_files.append((staged, destination))

        for staged, destination in staged_files:
            missing_parents: list[Path] = []
            parent = destination.parent
            while parent != root and not parent.exists():
                missing_parents.append(parent)
                parent = parent.parent
            for directory in reversed(missing_parents):
                directory.mkdir()
                created_directories.append(directory)
            # xb 是“必须不存在才创建”：其他进程在预检后新建的文件也不会被替换。
            with destination.open("xb") as output:
                installed.append(destination)
                with staged.open("rb") as source:
                    shutil.copyfileobj(source, output)
    except Exception as error:
        failure = error
        for destination in reversed(installed):
            try:
                destination.unlink(missing_ok=True)
            except OSError as cleanup_error:
                cleanup_errors.append(f"{destination.relative_to(root)}: {cleanup_error}")
        for directory in reversed(created_directories):
            try:
                directory.rmdir()
            except OSError as cleanup_error:
                cleanup_errors.append(f"{directory.relative_to(root)}: {cleanup_error}")
    try:
        shutil.rmtree(staging)
    except OSError as cleanup_error:
        cleanup_errors.append(f"{staging.relative_to(root)}: {cleanup_error}")
    if failure is not None:
        detail = "；清理未完成：" + "; ".join(cleanup_errors) if cleanup_errors else "；本次写入已回滚"
        raise BootstrapError(f"铺设失败：{failure}{detail}") from failure
    if cleanup_errors:
        raise BootstrapError("模板文件已写入，但临时文件清理未完成：" + "; ".join(cleanup_errors))


def main() -> int:
    parser = argparse.ArgumentParser(description="安全铺设小组资产仓模板，不覆盖已有文件")
    parser.add_argument("--root", default=".", help="消费端 Git 仓库根目录")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="只预览，不写文件")
    mode.add_argument("--apply", action="store_true", help="铺设不存在的模板文件")
    args = parser.parse_args()

    try:
        root = Path(args.root).expanduser().resolve(strict=True)
        if not root.is_dir() or not (root / ".git").exists():
            raise BootstrapError("--root 必须是已初始化的 Git 消费端仓库")
        if Path(git(root, "rev-parse", "--show-toplevel")).resolve() != root:
            raise BootstrapError("--root 必须是 Git 消费端仓库的根目录")
        if any(part.casefold() == "vendor" for part in root.parts):
            raise BootstrapError("不能把 vendor 内的目录作为消费端根目录")

        infrastructure = root / SUBMODULE_PATH
        if is_link(infrastructure.parent) or is_link(infrastructure):
            raise BootstrapError("基础设施路径不能通过符号链接或 junction 重定向")
        if not infrastructure.is_dir():
            raise BootstrapError(f"基础设施 submodule 尚未初始化：{SUBMODULE_PATH.as_posix()}")
        gitlink = assert_submodule_lock(root, infrastructure)

        manifest_at_root = root / "manifest.yml"
        if manifest_at_root.is_file() and REPOSITORY in manifest_at_root.read_text(encoding="utf-8-sig"):
            raise BootstrapError("当前根目录是基础设施仓库，不可铺设为消费端")

        source_root = Path(__file__).resolve().parents[2] / TEMPLATE_PATH
        files = template_files(source_root)
        writes, unchanged, conflicts = plan_files(root, files)
        if conflicts:
            raise BootstrapError("存在模板文件冲突；未写入任何文件：" + "; ".join(conflicts))
        if args.apply:
            apply_files(root, writes)

        print(json.dumps({
            "ok": True,
            "mode": "apply" if args.apply else "dry-run",
            "template": "group-asset-repository-v1",
            "submodule_commit": gitlink,
            "written": [path.relative_to(root).as_posix() for path, _ in writes] if args.apply else [],
            "would_write": [path.relative_to(root).as_posix() for path, _ in writes],
            "unchanged": unchanged,
            "conflicts": [],
            "note": "不会创建 submodule、提交或推送；身份与项目事实须由真人确认。",
        }, ensure_ascii=False, indent=2))
        return 0
    except (OSError, UnicodeError, BootstrapError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
