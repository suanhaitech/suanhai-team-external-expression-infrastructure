#!/usr/bin/env python3
"""从固定基础设施 submodule 安全复制 HTML 页面模板和组件包。"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from typing import Any


REPOSITORY = "suanhai-team-external-expression-infrastructure"
PUBLIC_URL = f"https://github.com/suanhaitech/{REPOSITORY}.git"
TASK_ID = re.compile(r"EXPR-\d{8}-[0-9a-f]{8}\Z")
VERSION = re.compile(r"v[0-9]{3}\Z")
OUTPUT_ROOT = re.compile(r"[a-z][a-z0-9_-]*\Z")
CAPABILITY_ID = re.compile(r"[a-z0-9][a-z0-9._-]*\Z")
DEFAULT_OUTPUT_ROOTS = {"reports", "works", "series", "courses", "books"}
PROTECTED_ROOTS = {"vendor", ".git", "context", "tasks"}
COMPONENT_MARKER = "<!-- SUANHAI_COMPONENT_STYLESHEETS -->"
COMPONENTS_MARKER = "<!-- SUANHAI_COMPONENTS -->"


class MaterializeError(Exception):
    """输入、来源或输出边界不满足物料化协议。"""


def is_link(path: Path) -> bool:
    """识别符号链接和 Windows junction，防止路径边界被重定向。"""
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
        raise MaterializeError(f"git {' '.join(arguments)} 失败：{detail}")
    return result.stdout.strip()


def safe_relative(value: str, label: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise MaterializeError(f"{label} 必须是非空仓库相对 POSIX 路径")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in value.split("/")):
        raise MaterializeError(f"{label} 不允许绝对路径、. 或 ..：{value}")
    return path


def assert_inside(root: Path, candidate: Path, label: str) -> Path:
    boundary = root.resolve()
    resolved = candidate.resolve(strict=True)
    try:
        resolved.relative_to(boundary)
    except ValueError as error:
        raise MaterializeError(f"{label} 越出仓库根目录") from error
    current = candidate
    while current != root:
        if is_link(current):
            raise MaterializeError(f"{label} 路径不能包含符号链接或 junction：{current}")
        current = current.parent
    return resolved


def parse_manifest(manifest_path: Path) -> dict[str, dict[str, str]]:
    """读取 Manifest schema v2 中固定缩进的能力标量字段。

    仓库运行时只依赖 Python 标准库，没有可用的标准库 YAML 解析器；因此这里只
    接受本仓 schema v2 的受限能力条目形式，遇到 ID/字段/缩进变化就失败关闭。
    完整 YAML 语义和 Schema 校验仍由 Ruby CI 校验器负责。
    """
    try:
        lines = manifest_path.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeError) as error:
        raise MaterializeError(f"无法读取基础设施 Manifest：{error}") from error

    repository = next((line.removeprefix("repository: ") for line in lines if line.startswith("repository: ")), None)
    if repository != REPOSITORY or "schema_version: 2" not in lines:
        raise MaterializeError("基础设施 Manifest 仓库标识或 schema_version 不受支持")

    capabilities: dict[str, dict[str, str]] = {}
    current: dict[str, str] | None = None

    def finish() -> None:
        if current is None:
            return
        required = {"id", "kind", "path", "entrypoint"}
        if required - current.keys():
            raise MaterializeError("Manifest 能力条目缺少必需的标量字段")
        capability_id = current["id"]
        if not CAPABILITY_ID.fullmatch(capability_id):
            raise MaterializeError(f"Manifest 能力 ID 不符合稳定格式：{capability_id}")
        if current["kind"] not in {"skill", "template", "tool", "harness", "check", "workflow"}:
            raise MaterializeError(f"Manifest 能力类型不受支持：{current['kind']}")
        safe_relative(current["path"], "Manifest path")
        safe_relative(current["entrypoint"], "Manifest entrypoint")
        if capability_id in capabilities:
            raise MaterializeError(f"Manifest 能力 ID 重复：{capability_id}")
        capabilities[capability_id] = current.copy()

    in_capabilities = False
    for line in lines:
        if line == "capabilities:":
            in_capabilities = True
            continue
        if not in_capabilities:
            continue
        if line.startswith("  - id: "):
            finish()
            current = {"id": line[len("  - id: "):].strip()}
            continue
        if current is not None:
            match = re.fullmatch(r"    (kind|path|entrypoint): ([^#]+?)\s*", line)
            if match:
                current[match.group(1)] = match.group(2).strip()
    finish()
    if not capabilities:
        raise MaterializeError("Manifest 中没有可读取的能力条目")
    return capabilities


def scalar_metadata(path: Path) -> dict[str, str]:
    """读取模板/组件元数据中的 id、version 和 entrypoint 顶层标量。"""
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeError) as error:
        raise MaterializeError(f"无法读取资产元数据 {path.name}：{error}") from error
    values: dict[str, str] = {}
    for line in lines:
        match = re.fullmatch(r"(id|version|entrypoint):\s*([^#]+?)\s*", line)
        if match:
            key, value = match.groups()
            if key in values:
                raise MaterializeError(f"{path.name} 中 {key} 字段重复")
            values[key] = value.strip()
    if not {"id", "version", "entrypoint"}.issubset(values):
        raise MaterializeError(f"{path.name} 必须定义顶层 id、version 和 entrypoint")
    return values


def component_catalog(index_path: Path, expected_package: str) -> dict[str, dict[str, str]]:
    """Parse the deliberately small index.yml contract without a YAML dependency."""
    try:
        lines = index_path.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeError) as error:
        raise MaterializeError(f"无法读取组件目录：{error}") from error
    if "schema_version: 1" not in lines or f"package: {expected_package}" not in lines or "components:" not in lines:
        raise MaterializeError("组件 index.yml 的 schema_version、package 或 components 无效")

    catalog: dict[str, dict[str, str]] = {}
    current: dict[str, str] | None = None

    def finish() -> None:
        if current is None:
            return
        required = {"id", "category", "contract", "definition", "template"}
        if required - current.keys():
            raise MaterializeError("组件目录条目缺少必需字段")
        component_id = current["id"]
        if not CAPABILITY_ID.fullmatch(component_id):
            raise MaterializeError(f"组件 ID 不符合稳定格式：{component_id}")
        for field in ("contract", "definition", "template"):
            safe_relative(current[field], f"组件目录 {field}")
        if component_id in catalog:
            raise MaterializeError(f"组件目录 ID 重复：{component_id}")
        catalog[component_id] = current.copy()

    for line in lines[lines.index("components:") + 1:]:
        if line.startswith("  - id: "):
            finish()
            current = {"id": line[len("  - id: "):].strip()}
            continue
        if current is None:
            continue
        match = re.fullmatch(r"    (category|contract|definition|template):\s*([^#]+?)\s*", line)
        if match:
            key, value = match.groups()
            if key in current:
                raise MaterializeError(f"组件目录字段重复：{key}")
            current[key] = value.strip()
    finish()
    if not catalog:
        raise MaterializeError("组件目录没有登记任何组件")
    return catalog


def component_definition(path: Path, expected_id: str, expected_template: str) -> dict[str, str]:
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeError) as error:
        raise MaterializeError(f"无法读取组件定义 {path.name}：{error}") from error
    values: dict[str, str] = {}
    for line in lines:
        match = re.fullmatch(r"(id|version|template):\s*([^#]+?)\s*", line)
        if match:
            key, value = match.groups()
            if key in values:
                raise MaterializeError(f"组件定义 {path.name} 中 {key} 字段重复")
            values[key] = value.strip()
    if values.get("id") != expected_id or not values.get("version") or not values.get("template"):
        raise MaterializeError(f"组件定义与 index.yml 不一致：{expected_id}")
    safe_relative(values["template"], "组件定义 template")
    if PurePosixPath(expected_template).name != PurePosixPath(values["template"]).name:
        raise MaterializeError(f"组件定义 template 与 index.yml 不一致：{expected_id}")
    return values


def package_files(source_root: Path) -> list[tuple[PurePosixPath, bytes]]:
    if not source_root.is_dir():
        raise MaterializeError(f"资产目录不存在：{source_root}")
    files: list[tuple[PurePosixPath, bytes]] = []
    for path in sorted(source_root.rglob("*")):
        if is_link(path):
            raise MaterializeError(f"共享资产包不允许包含符号链接：{path}")
        if path.is_file():
            relative = PurePosixPath(path.relative_to(source_root).as_posix())
            files.append((relative, path.read_bytes()))
    if not files:
        raise MaterializeError(f"共享资产包没有文件：{source_root}")
    return files


def capability_asset(
    infrastructure: Path,
    capability: dict[str, str],
    *,
    role: str,
) -> tuple[Path, dict[str, str]]:
    if capability["kind"] != "template":
        raise MaterializeError(f"只有 Manifest 中的 template 能力可物料化：{capability['id']}")
    relative = safe_relative(capability["path"], "Manifest path")
    if role == "template" and not relative.as_posix().startswith("formats/web/html/page-templates/"):
        raise MaterializeError(f"页面模板必须位于 formats/web/html/page-templates/：{capability['id']}")
    if role == "component" and not relative.as_posix().startswith("formats/web/html/components/"):
        raise MaterializeError(f"HTML 组件包必须位于 formats/web/html/components/：{capability['id']}")

    source_root = infrastructure.joinpath(*relative.parts)
    assert_inside(infrastructure, source_root, "Manifest path")
    metadata_path = source_root / ("template.yml" if role == "template" else "package.yml")
    if is_link(metadata_path) or not metadata_path.is_file():
        raise MaterializeError(f"能力元数据不存在或不是普通文件：{metadata_path}")
    metadata = scalar_metadata(metadata_path)
    if metadata["id"] != capability["id"]:
        raise MaterializeError(f"Manifest ID 与 {metadata_path.name} 不一致：{capability['id']}")

    entrypoint_rel = safe_relative(capability["entrypoint"], "Manifest entrypoint")
    expected_entrypoint = source_root / metadata["entrypoint"]
    if entrypoint_rel.as_posix() != expected_entrypoint.relative_to(infrastructure).as_posix():
        raise MaterializeError(f"Manifest entrypoint 与 {metadata_path.name} 不一致：{capability['id']}")
    assert_inside(infrastructure, expected_entrypoint, "Manifest entrypoint")
    if not expected_entrypoint.is_file():
        raise MaterializeError(f"能力入口不是普通文件：{expected_entrypoint}")
    return source_root, metadata


def is_infrastructure_root(root: Path) -> bool:
    manifest = root / "manifest.yml"
    if not manifest.is_file():
        return False
    return f"repository: {REPOSITORY}" in manifest.read_text(encoding="utf-8-sig")


def assert_consumer_lock(root: Path, infrastructure: Path, submodule_path: PurePosixPath) -> str:
    if not (root / ".git").exists() or Path(git(root, "rev-parse", "--show-toplevel")).resolve() != root:
        raise MaterializeError("--root 必须是已初始化的消费端 Git 仓库根目录")
    if is_infrastructure_root(root):
        raise MaterializeError("不能在基础设施仓库本身物料化消费端作品")
    if not infrastructure.is_dir():
        raise MaterializeError(f"基础设施 submodule 不存在或通过链接重定向：{submodule_path.as_posix()}")
    assert_inside(root, infrastructure, "基础设施 submodule")
    if Path(git(infrastructure, "rev-parse", "--show-toplevel")).resolve() != infrastructure.resolve():
        raise MaterializeError("基础设施路径不是独立 Git submodule 根目录")

    configured = git(root, "config", "--file", ".gitmodules", "--get-regexp", r"^submodule\..*\.path$")
    matching = []
    for line in configured.splitlines():
        key, value = line.split(None, 1)
        if value == submodule_path.as_posix():
            matching.append(key[:-5])
    if len(matching) != 1:
        raise MaterializeError(f".gitmodules 必须唯一登记当前基础设施路径：{submodule_path.as_posix()}")
    url = git(root, "config", "--file", ".gitmodules", "--get", f"{matching[0]}.url")
    if url != PUBLIC_URL:
        raise MaterializeError(f"基础设施 submodule URL 必须为 {PUBLIC_URL}")

    index_entry = git(root, "ls-files", "--stage", "--", submodule_path.as_posix()).splitlines()
    head_entry = git(root, "ls-tree", "HEAD", "--", submodule_path.as_posix()).splitlines()
    if len(index_entry) != 1 or not index_entry[0].startswith("160000 "):
        raise MaterializeError("基础设施尚未以 Git submodule gitlink 固定在父仓 index 中")
    if len(head_entry) != 1 or not head_entry[0].startswith("160000 commit "):
        raise MaterializeError("HEAD 中没有已提交的基础设施 submodule gitlink")
    gitlink = index_entry[0].split()[1]
    if gitlink != head_entry[0].split()[2]:
        raise MaterializeError("基础设施 gitlink 有未提交变更；请先提交后再运行物料化工具")
    if git(infrastructure, "rev-parse", "HEAD") != gitlink:
        raise MaterializeError("基础设施 submodule HEAD 与父仓 gitlink 不一致")
    if git(infrastructure, "status", "--porcelain"):
        raise MaterializeError("基础设施 submodule 工作区不干净；工具不会修改 submodule")
    expected_script = infrastructure / "tools/html-materialize/materialize_html.py"
    if Path(__file__).resolve() != expected_script.resolve():
        raise MaterializeError("必须从消费端当前固定 commit 的基础设施 submodule 内运行本工具")
    return gitlink


def resolve_submodule(root: Path, requested: str | None) -> tuple[PurePosixPath, Path]:
    """定位当前运行工具所属的基础设施 submodule。

    默认从工具入口的真实路径反推 submodule，因而既支持公共模板的
    ``vendor/...``，也支持既有仓库选择的其他安全相对路径。显式参数用于
    入口被包装、复制或工作区存在多个同仓 submodule 的场景；最终仍由
    ``assert_consumer_lock`` 校验 .gitmodules、gitlink 和入口文件一致。
    """
    root_resolved = root.resolve()
    if requested:
        relative = safe_relative(requested, "--submodule-path")
        infrastructure = root.joinpath(*relative.parts)
    else:
        try:
            infrastructure = Path(__file__).resolve().parents[2]
            relative = PurePosixPath(infrastructure.relative_to(root_resolved).as_posix())
        except (IndexError, ValueError) as error:
            raise MaterializeError("无法从当前工具入口推导消费端 submodule；请提供 --submodule-path") from error
    if not relative.parts or relative == PurePosixPath("."):
        raise MaterializeError("--submodule-path 必须指向消费端根目录下的独立 submodule")
    if any(part.casefold() in {".git", "context", "tasks"} for part in relative.parts):
        raise MaterializeError("--submodule-path 不能进入 .git、context 或 tasks")
    return relative, infrastructure


def allowed_output_roots(root: Path) -> set[str]:
    config_path = root / ".suanhai/expression.json"
    if is_link(config_path.parent) or is_link(config_path):
        raise MaterializeError("作品输出配置不能通过符号链接或 junction 定位")
    if not config_path.exists():
        return DEFAULT_OUTPUT_ROOTS.copy()
    if not config_path.is_file():
        raise MaterializeError(".suanhai/expression.json 必须是普通文件")
    assert_inside(root, config_path, "作品输出配置")
    try:
        config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise MaterializeError(f"无法解析 .suanhai/expression.json：{error}") from error
    if not isinstance(config, dict) or set(config) != {"schema_version", "output_roots"}:
        raise MaterializeError("作品输出配置只允许 schema_version 和 output_roots 字段")
    if type(config.get("schema_version")) is not int or config["schema_version"] != 1:
        raise MaterializeError("作品输出配置 schema_version 必须为 1")
    roots = config.get("output_roots")
    if not isinstance(roots, list) or not roots or not all(isinstance(item, str) for item in roots):
        raise MaterializeError("作品输出配置 output_roots 必须是非空字符串数组")
    allowed = DEFAULT_OUTPUT_ROOTS.copy()
    for item in roots:
        if not OUTPUT_ROOT.fullmatch(item) or item.casefold() in PROTECTED_ROOTS:
            raise MaterializeError(f"作品输出根不是允许的安全目录名：{item}")
        allowed.add(item)
    if len(roots) != len(set(roots)):
        raise MaterializeError("作品输出配置 output_roots 不能重复")
    return allowed


def output_directory(root: Path, output_root: str, task_id: str, version: str) -> Path:
    if not OUTPUT_ROOT.fullmatch(output_root) or output_root.casefold() in PROTECTED_ROOTS:
        raise MaterializeError("--output-root 必须是安全的单层目录名，且不能是受保护目录")
    if output_root not in allowed_output_roots(root):
        raise MaterializeError(f"消费端未允许使用作品目录 {output_root}；先更新 .suanhai/expression.json")
    if not TASK_ID.fullmatch(task_id):
        raise MaterializeError("--task-id 必须符合 EXPR-YYYYMMDD-xxxxxxxx 格式")
    if not VERSION.fullmatch(version):
        raise MaterializeError("--version 必须符合 vNNN 格式，例如 v001")
    destination = root / output_root / task_id / version
    resolved = destination.resolve(strict=False)
    try:
        resolved.relative_to(root.resolve())
    except ValueError as error:
        raise MaterializeError("作品输出路径越出消费端根目录") from error
    current = destination
    while current != root:
        if is_link(current):
            raise MaterializeError(f"作品输出路径不能包含符号链接或 junction：{current}")
        if current.exists() and not current.is_dir():
            raise MaterializeError(f"作品输出路径的父级不是目录：{current}")
        current = current.parent
    return destination


def read_task_context(root: Path, task_id: str, infrastructure_commit: str) -> dict[str, Any]:
    if not TASK_ID.fullmatch(task_id):
        raise MaterializeError("--task-id 必须符合 EXPR-YYYYMMDD-xxxxxxxx 格式")
    task_directory = root / "tasks" / task_id
    task_path = task_directory / "task.json"
    for path in (root / "tasks", task_directory, task_path):
        if is_link(path):
            raise MaterializeError(f"任务记录路径不允许使用符号链接或 junction：{path.relative_to(root).as_posix()}")
    assert_inside(root, task_path, "任务记录")
    try:
        task_bytes = task_path.read_bytes()
        task = json.loads(task_bytes.decode("utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise MaterializeError(f"无法读取任务记录 {task_path.relative_to(root).as_posix()}：{error}") from error
    if not isinstance(task, dict) or task.get("schema_version") != 1 or task.get("id") != task_id:
        raise MaterializeError("task.json 的 schema_version 或任务编号无效")
    if task.get("status") != "working":
        raise MaterializeError("任务必须已完成用户对齐并由 task-loop start 进入 working 状态")
    if type(task.get("revision")) is not int or task["revision"] < 1 or type(task.get("version")) is not int or task["version"] < 1:
        raise MaterializeError("task.json 的 revision 或 version 无效")
    if task.get("infrastructure_commit") != infrastructure_commit:
        raise MaterializeError("任务创建时固定的基础设施 commit 与当前 submodule 不一致")
    brief = task.get("brief")
    if (
        not isinstance(brief, dict)
        or not isinstance(brief.get("output"), str)
        or not isinstance(brief.get("audience"), str)
        or not brief["audience"].strip()
        or not isinstance(brief.get("purpose"), str)
        or not brief["purpose"].strip()
    ):
        raise MaterializeError("任务简报缺少已对齐的 audience、purpose 或 output")
    output = safe_relative(brief["output"].rstrip("/"), "任务简报 brief.output")
    if len(output.parts) not in {2, 3} or output.parts[1] != task_id:
        raise MaterializeError("brief.output 必须是 <输出根>/<任务编号>，也兼容带 vNNN 的旧记录")
    if len(output.parts) == 3:
        if not VERSION.fullmatch(output.parts[2]) or output.parts[2] != f"v{task['revision']:03d}":
            raise MaterializeError("brief.output 版本必须与任务当前修订一致")
        version = output.parts[2]
    else:
        version = f"v{task['revision']:03d}"
    output_root = output.parts[0]
    output_path = output_directory(root, output_root, task_id, version)
    return {
        "directory": task_directory,
        "path": task_path,
        "version": task["version"],
        "revision": task["revision"],
        "output_root": output_root,
        "output": output_path,
        "brief_output": brief["output"],
        "version_name": version,
        "title": task.get("title", ""),
        "audience": brief["audience"],
        "purpose": brief["purpose"],
        "record_sha256": hashlib.sha256(task_bytes).hexdigest(),
    }


@contextmanager
def task_record_lock(directory: Path):
    """复用任务循环的独占锁名，应用期间禁止并发推进同一任务记录。"""
    lock = directory / ".lock"
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise MaterializeError("任务正在写入或保留了未释放的 .lock；先人工核对，不自动清理") from error
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(f"pid={os.getpid()} at={datetime.now(timezone.utc).isoformat(timespec='seconds')}\n")
        yield
    finally:
        lock.unlink(missing_ok=True)


def component_slug(capability_id: str) -> str:
    if not CAPABILITY_ID.fullmatch(capability_id):
        raise MaterializeError(f"组件能力 ID 不符合稳定格式：{capability_id}")
    return capability_id.replace(".", "-")


def yaml_quote(value: str) -> str:
    """使用 JSON 字符串作为 YAML 双引号标量，避免项目中文和标点破坏结构。"""
    return json.dumps(value, ensure_ascii=False)


def report_metadata(
    task: dict[str, Any],
    task_id: str,
    version: str,
    infrastructure_commit: str,
    template: dict[str, Any],
    components: list[dict[str, Any]],
    semantic_components: list[dict[str, Any]],
    source_ids: list[str],
) -> bytes:
    lines = [
        "schema_version: 1",
        f"task_id: {yaml_quote(task_id)}",
        f"revision: {task['revision']}",
        f"title: {yaml_quote(task['title'] or 'HTML 页面')}",
        f"template: {yaml_quote(template['id'])}",
        f"template_version: {yaml_quote(template['version'])}",
        f"audience: {yaml_quote(task['audience'])}",
        f"purpose: {yaml_quote(task['purpose'])}",
        "status: draft",
        "components:",
    ]
    for component in components:
        lines.append(f"  - {yaml_quote(component['id'])}")
    lines.append("semantic_components:")
    for component in semantic_components:
        lines.append(f"  - {yaml_quote(component['id'])}")
    lines.append("source_ids:")
    for source_id in source_ids:
        lines.append(f"  - {yaml_quote(source_id)}")
    lines.extend([
        "authorization:",
        "  status: pending",
        f"  audience: {yaml_quote(task['audience'])}",
        "infrastructure_commit: " + yaml_quote(infrastructure_commit),
        "materialization:",
        "  tool: html.materialize",
        "  version: 1",
        f"  artifact_version: {yaml_quote(version)}",
        "  record: materialization.json",
        "  infrastructure_commit: " + yaml_quote(infrastructure_commit),
    ])
    return ("\n".join(lines) + "\n").encode("utf-8")


def inject_component_stylesheets(
    template_files: list[tuple[PurePosixPath, bytes]],
    components: list[dict[str, Any]],
) -> list[tuple[PurePosixPath, bytes]]:
    entrypoint = next((index for index, (path, _) in enumerate(template_files) if path.as_posix() == "index.html"), None)
    if entrypoint is None:
        raise MaterializeError("HTML 页面模板包根目录必须有 index.html")
    try:
        html = template_files[entrypoint][1].decode("utf-8")
    except UnicodeDecodeError as error:
        raise MaterializeError("模板 index.html 必须是 UTF-8") from error
    if html.count(COMPONENT_MARKER) != 1:
        raise MaterializeError(f"模板 index.html 必须恰有一个组件样式插槽：{COMPONENT_MARKER}")
    links = "".join(
        f'    <link rel="stylesheet" href="assets/{component_slug(item["id"])}/styles.css" />\n'
        for item in components
    )
    template_files[entrypoint] = (template_files[entrypoint][0], html.replace(COMPONENT_MARKER, links).encode("utf-8"))
    return template_files


def inject_semantic_components(
    template_files: list[tuple[PurePosixPath, bytes]],
    snippets: list[bytes],
) -> list[tuple[PurePosixPath, bytes]]:
    """将已选择的语义片段放入模板声明的稳定插槽。"""
    entrypoint = next((index for index, (path, _) in enumerate(template_files) if path.as_posix() == "index.html"), None)
    if entrypoint is None:
        raise MaterializeError("HTML 页面模板包根目录必须有 index.html")
    try:
        html = template_files[entrypoint][1].decode("utf-8")
    except UnicodeDecodeError as error:
        raise MaterializeError("模板 index.html 必须是 UTF-8") from error
    if html.count(COMPONENTS_MARKER) != 1:
        raise MaterializeError(f"模板 index.html 必须恰有一个语义组件插槽：{COMPONENTS_MARKER}")
    content = "\n".join(item.decode("utf-8") for item in snippets)
    template_files[entrypoint] = (
        template_files[entrypoint][0],
        html.replace(COMPONENTS_MARKER, content).encode("utf-8"),
    )
    return template_files


def plan_materialization(
    root: Path,
    destination: Path,
    files: dict[PurePosixPath, bytes],
) -> tuple[list[tuple[Path, bytes]], list[str], list[str]]:
    writes: list[tuple[Path, bytes]] = []
    unchanged: list[str] = []
    conflicts: list[str] = []
    boundary = root.resolve()
    for relative, content in sorted(files.items(), key=lambda item: item[0].as_posix()):
        target = destination.joinpath(*relative.parts)
        try:
            target.resolve(strict=False).relative_to(boundary)
        except ValueError:
            conflicts.append(f"{relative.as_posix()}（目标越出消费端根目录）")
            continue
        current = target.parent
        while current != root:
            if is_link(current):
                conflicts.append(f"{relative.as_posix()}（父目录包含符号链接或 junction）")
                break
            if current.exists() and not current.is_dir():
                conflicts.append(f"{relative.as_posix()}（父路径不是目录）")
                break
            current = current.parent
        if is_link(target):
            conflicts.append(f"{relative.as_posix()}（目标是符号链接或 junction）")
        elif target.exists() and not target.is_file():
            conflicts.append(f"{relative.as_posix()}（目标不是普通文件）")
        elif target.is_file():
            if target.read_bytes() == content:
                unchanged.append(relative.as_posix())
            else:
                conflicts.append(f"{relative.as_posix()}（已有不同内容）")
        else:
            writes.append((target, content))
    return writes, unchanged, conflicts


def apply_files(root: Path, writes: list[tuple[Path, bytes]]) -> None:
    """先暂存完整写入集，再用独占创建落盘；失败时回滚本次新建内容。"""
    if not writes:
        return
    staging = Path(tempfile.mkdtemp(prefix=".html-materialize-", dir=root))
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
            missing: list[Path] = []
            parent = destination.parent
            while parent != root and not parent.exists():
                missing.append(parent)
                parent = parent.parent
            for directory in reversed(missing):
                directory.mkdir()
                created_directories.append(directory)
            with destination.open("xb") as output:
                installed.append(destination)
                with staged.open("rb") as source:
                    shutil.copyfileobj(source, output)
    except Exception as error:
        failure = error
        for path in reversed(installed):
            try:
                path.unlink(missing_ok=True)
            except OSError as cleanup_error:
                cleanup_errors.append(str(cleanup_error))
        for directory in reversed(created_directories):
            try:
                directory.rmdir()
            except OSError as cleanup_error:
                cleanup_errors.append(str(cleanup_error))
    try:
        shutil.rmtree(staging)
    except OSError as cleanup_error:
        cleanup_errors.append(str(cleanup_error))
    if failure is not None:
        detail = "；清理未完成：" + "; ".join(cleanup_errors) if cleanup_errors else "；本次写入已回滚"
        raise MaterializeError(f"物料化写入失败：{failure}{detail}") from failure
    if cleanup_errors:
        raise MaterializeError("物料化完成，但临时文件清理未完成：" + "; ".join(cleanup_errors))


def build_plan(
    infrastructure: Path,
    manifest: dict[str, dict[str, str]],
    template_id: str,
    component_package_id: str,
    component_ids: list[str],
    task_id: str,
    version: str,
    task_revision: int,
    task_record_version: int,
    infrastructure_commit: str,
    task_context: dict[str, Any],
    source_ids: list[str],
) -> tuple[dict[PurePosixPath, bytes], dict[str, Any]]:
    if template_id not in manifest:
        raise MaterializeError(f"Manifest 没有登记页面模板：{template_id}")
    # 旧版本把 --component-id 用作组件包 ID；保留这个调用形态，避免已接入
    # 的消费端突然失效。新调用应使用 --component-package-id 配包，再用一个或
    # 多个 --component-id 选择语义片段。
    legacy_package_selection = component_ids == [component_package_id]
    if len(source_ids) != len(set(source_ids)) or any(not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", item) for item in source_ids):
        raise MaterializeError("--source-id 必须唯一且符合稳定来源 ID 格式")
    template_capability = manifest[template_id]
    template_root, template_metadata = capability_asset(infrastructure, template_capability, role="template")
    template_contents = package_files(template_root)
    package_capability = manifest.get(component_package_id)
    if package_capability is None:
        raise MaterializeError(f"Manifest 没有登记组件包：{component_package_id}")
    component_root, package_metadata = capability_asset(infrastructure, package_capability, role="component")
    package_metadata_path = component_root / "package.yml"
    package_lines = package_metadata_path.read_text(encoding="utf-8-sig").splitlines()
    catalog_relative = next((line.removeprefix("catalog: ").strip() for line in package_lines if line.startswith("catalog: ")), None)
    if not catalog_relative:
        raise MaterializeError(f"组件包未声明 catalog：{component_package_id}")
    catalog_path = component_root.joinpath(*safe_relative(catalog_relative, "组件包 catalog").parts)
    assert_inside(component_root, catalog_path, "组件包 catalog")
    catalog = component_catalog(catalog_path, component_package_id)
    if legacy_package_selection:
        component_ids = list(catalog)
    if not component_ids:
        raise MaterializeError("至少通过 --component-id 选择一个组件目录中的语义组件")

    selected_components: list[dict[str, Any]] = []
    snippets: list[bytes] = []
    copied: dict[PurePosixPath, bytes] = {}

    if len(component_ids) != len(set(component_ids)):
        raise MaterializeError("--component-id 不允许重复")
    if any(path.as_posix() == "styles.css" for path, _ in package_files(component_root)) is False:
        raise MaterializeError(f"组件包必须提供 styles.css：{component_package_id}")
    package_target = PurePosixPath("assets") / component_slug(component_package_id)
    for relative, content in package_files(component_root):
        output_path = package_target / relative
        if output_path in copied:
            raise MaterializeError(f"组件包内部输出路径冲突：{output_path.as_posix()}")
        copied[output_path] = content

    for component_id in component_ids:
        entry = catalog.get(component_id)
        if entry is None:
            raise MaterializeError(f"组件包 {component_package_id} 没有登记语义组件：{component_id}")
        definition_rel = safe_relative(entry["definition"], "组件定义路径")
        definition_path = component_root.joinpath(*definition_rel.parts)
        assert_inside(component_root, definition_path, "组件定义路径")
        definition = component_definition(definition_path, component_id, entry["template"])
        template_rel = safe_relative(entry["template"], "组件模板路径")
        snippet_path = component_root.joinpath(*template_rel.parts)
        assert_inside(component_root, snippet_path, "组件模板路径")
        if not snippet_path.is_file():
            raise MaterializeError(f"语义组件 HTML 模板不存在：{component_id}")
        snippets.append(snippet_path.read_bytes())
        selected_components.append({
            "id": component_id,
            "version": definition["version"],
            "category": entry["category"],
            "package": component_package_id,
            "source": package_capability["path"],
            "definition": entry["definition"],
            "template": entry["template"],
        })

    selected_packages = [{
        "id": component_package_id,
        "version": package_metadata["version"],
        "source": package_capability["path"],
        "entrypoint": package_capability["entrypoint"],
        "destination": package_target.as_posix(),
    }]
    template_contents = inject_component_stylesheets(template_contents, selected_packages)
    template_contents = inject_semantic_components(template_contents, snippets)
    # 组件样式插槽是显式模板契约，避免对 HTML 做不稳定的任意文本重写。
    for relative, content in template_contents:
        if relative in copied:
            raise MaterializeError(f"页面模板与组件包输出路径冲突：{relative.as_posix()}")
        copied[relative] = content

    if PurePosixPath("materialization.json") in copied:
        raise MaterializeError("页面模板不能预占保留文件名 materialization.json")

    materialization = {
        "schema_version": 1,
        "task_id": task_id,
        "version": version,
        "revision": task_revision,
        "task_record_version": task_record_version,
        "infrastructure": {
            "repository": REPOSITORY,
            "commit": infrastructure_commit,
        },
        "template": {
            "id": template_id,
            "version": template_metadata["version"],
            "source": template_capability["path"],
            "entrypoint": template_capability["entrypoint"],
            "destination": ".",
        },
        "components": selected_packages,
        "semantic_components": selected_components,
        "files": [],
    }
    copied[PurePosixPath("report.yml")] = report_metadata(
        task_context,
        task_id,
        version,
        infrastructure_commit,
        materialization["template"],
        materialization["components"],
        materialization["semantic_components"],
        source_ids,
    )
    # 报告元数据也属于物料化结果；记录文件自身不纳入清单，避免自引用哈希循环。
    materialization["files"] = [
        {"path": path.as_posix(), "sha256": hashlib.sha256(content).hexdigest()}
        for path, content in sorted(copied.items(), key=lambda item: item[0].as_posix())
    ]
    copied[PurePosixPath("materialization.json")] = (
        json.dumps(materialization, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    return copied, materialization


def plan_sha256(destination: Path, files: dict[PurePosixPath, bytes], root: Path) -> str:
    entries = [
        {
            "path": (destination / Path(*relative.parts)).relative_to(root).as_posix(),
            "sha256": hashlib.sha256(content).hexdigest(),
        }
        for relative, content in sorted(files.items(), key=lambda item: item[0].as_posix())
    ]
    encoded = json.dumps(entries, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description="安全复制 Manifest 中登记的 HTML 页面模板和组件包")
    parser.add_argument("--root", default=".", help="消费端 Git 仓库根目录")
    parser.add_argument("--submodule-path", help="基础设施 submodule 的消费端相对路径；默认从当前脚本位置推导")
    parser.add_argument("--task-id", required=True, help="已登记的 EXPR 任务编号")
    parser.add_argument("--template-id", required=True, help="Manifest 中登记的页面模板能力 ID")
    parser.add_argument("--component-package-id", default="html.semantic-components-v1", help="Manifest 中登记的 HTML 组件包能力 ID")
    parser.add_argument("--component-id", action="append", default=[], help="组件包 index.yml 中登记的语义组件 ID，可重复指定")
    parser.add_argument("--apply", action="store_true", help="写入文件；未指定时只输出 dry-run 计划")
    parser.add_argument("--expect-plan-sha256", help="必须与最近一次 dry-run 的 plan_sha256 一致，防止应用不同计划")
    parser.add_argument("--expect-task-version", type=int, help="--apply 时必须匹配 dry-run 读取的任务 version")
    parser.add_argument("--source-id", action="append", default=[], help="已登记来源 ID，可重复指定")
    args = parser.parse_args()

    try:
        root = Path(args.root).expanduser().resolve(strict=True)
        if not root.is_dir():
            raise MaterializeError("--root 必须是目录")
        submodule_path, infrastructure = resolve_submodule(root, args.submodule_path)
        commit = assert_consumer_lock(root, infrastructure, submodule_path)
        task = read_task_context(root, args.task_id, commit)
        destination = task["output"]
        version = task["version_name"]
        manifest = parse_manifest(infrastructure / "manifest.yml")
        relative_destination = destination.relative_to(root)
        package, materialization = build_plan(
            infrastructure,
            manifest,
            args.template_id,
            args.component_package_id,
            args.component_id,
            args.task_id,
            version,
            task["revision"],
            task["version"],
            commit,
            task,
            args.source_id,
        )
        digest = plan_sha256(destination, package, root)
        if args.apply and not args.expect_plan_sha256:
            raise MaterializeError("--apply 必须携带最近一次 dry-run 返回的 --expect-plan-sha256")
        if args.apply and args.expect_plan_sha256 != digest:
            raise MaterializeError(f"计划摘要不匹配：预期 {args.expect_plan_sha256}，当前计划 {digest}；请重新 dry-run")
        if args.apply and args.expect_task_version is None:
            raise MaterializeError("--apply 必须携带最近一次 dry-run 返回的 --expect-task-version")
        if args.apply and args.expect_task_version != task["version"]:
            raise MaterializeError(f"任务记录版本冲突：预期 {args.expect_task_version}，当前为 {task['version']}；请重新读取任务和 dry-run")
        if not args.apply and args.expect_plan_sha256:
            raise MaterializeError("--expect-plan-sha256 只能与 --apply 一起使用")
        if not args.apply and args.expect_task_version is not None:
            raise MaterializeError("--expect-task-version 只能与 --apply 一起使用")
        writes, unchanged, conflicts = plan_materialization(root, destination, package)
        if conflicts:
            raise MaterializeError("存在目标冲突；没有写入文件：" + "; ".join(conflicts))
        if args.apply:
            with task_record_lock(task["directory"]):
                latest_task = read_task_context(root, args.task_id, commit)
                if any(latest_task[key] != task[key] for key in (
                    "version", "revision", "output_root", "brief_output", "title", "audience", "purpose", "record_sha256",
                )):
                    raise MaterializeError("任务在 dry-run 后发生变化；没有写入，请重新读取任务并生成计划")
                latest_package, _ = build_plan(
                    infrastructure, manifest, args.template_id, args.component_package_id, args.component_id,
                    args.task_id, version, latest_task["revision"], latest_task["version"], commit,
                    latest_task, args.source_id,
                )
                latest_digest = plan_sha256(destination, latest_package, root)
                if latest_digest != digest:
                    raise MaterializeError("资产内容在 dry-run 后发生变化；没有写入，请重新生成计划")
                latest_writes, latest_unchanged, latest_conflicts = plan_materialization(root, destination, latest_package)
                if latest_conflicts:
                    raise MaterializeError("dry-run 后出现目标冲突；没有写入文件：" + "; ".join(latest_conflicts))
                apply_files(root, latest_writes)
                writes, unchanged = latest_writes, latest_unchanged
        print(json.dumps({
            "ok": True,
            "mode": "apply" if args.apply else "dry-run",
            "task_id": args.task_id,
            "version": version,
            "revision": task["revision"],
            "task_record_version": task["version"],
            "output": relative_destination.as_posix(),
            "infrastructure_commit": commit,
            "plan_sha256": digest,
            "template": materialization["template"],
            "components": materialization["components"],
            "semantic_components": materialization["semantic_components"],
            "written": [path.relative_to(root).as_posix() for path, _ in writes] if args.apply else [],
            "would_write": [path.relative_to(root).as_posix() for path, _ in writes],
            "unchanged": [f"{relative_destination.as_posix()}/{path}" for path in unchanged],
            "note": "不会覆盖已有内容、修改 submodule、填充项目事实或执行 Git 提交/推送。",
        }, ensure_ascii=False, indent=2))
        return 0
    except (OSError, UnicodeError, MaterializeError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
