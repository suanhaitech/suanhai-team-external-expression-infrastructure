#!/usr/bin/env python3
"""消费端任务循环的文件记录工具；仅用 Python 标准库，不运行 Agent 或发布作品。"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from typing import Any
import uuid


TASK_ID = re.compile(r"EXPR-\d{8}-[0-9a-f]{8}\Z")
STATUSES = {"clarifying", "ready", "working", "review", "paused", "completed"}
EVENTS = {"create", "brief", "align", "start", "checkpoint", "review", "feedback", "pause", "resume", "complete", "reopen"}
# 新小组模板将报告任务产物放入 reports/；works/ 保留为旧消费端迁移期间的兼容入口。
# 自建消费端可通过 .suanhai/expression.json 显式增加自己的顶层作品目录。
DEFAULT_OUTPUT_ROOTS = {"reports", "works", "series", "courses", "books"}
OUTPUT_CONFIG = Path(".suanhai/expression.json")
BRIEF_FIELDS = ("audience", "purpose", "scope", "output", "acceptance")
INFRA_REPOSITORY = "suanhai-team-external-expression-infrastructure"


class LoopError(Exception):
    """面向用户的协议错误；不通过自动修复环境来掩盖失败。"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def consumer_root(value: str) -> Path:
    root = Path(value).expanduser().resolve()
    if not root.is_dir():
        raise LoopError("消费端根目录不存在")
    if any(part.casefold() == "vendor" for part in root.parts):
        raise LoopError("不能把 vendor 内的目录作为消费端根目录")
    manifest = root / "manifest.yml"
    if manifest.is_file() and INFRA_REPOSITORY in manifest.read_text(encoding="utf-8-sig"):
        raise LoopError("不能在共享基础设施仓库创建项目任务，请指定消费端根目录")
    required = (root / ".git", root / "README.md", root / "AGENTS.md", root / "context", root / "tasks")
    if not all(path.exists() for path in required):
        raise LoopError("消费端根目录应包含 .git、README.md、AGENTS.md、context/ 和 tasks/")
    if not (root / "context").is_dir() or not (root / "tasks").is_dir():
        raise LoopError("context/ 和 tasks/ 必须是目录")
    if (root / "tasks").is_symlink():
        raise LoopError("任务存储 tasks/ 不允许使用符号链接")
    safe_path(root, "tasks", must_exist=True)
    return root


def allowed_output_roots(root: Path) -> set[str]:
    """读取消费端声明的输出根；默认集合保持公共模板和旧仓兼容。

    配置只允许增加顶层目录名，不能把任务产物放入 vendor、.git、context 或
    tasks。把这项配置放在消费端而不是基础设施仓，避免共享 submodule 替项目
    决定事实和作品的存放位置。
    """
    config_path = root / OUTPUT_CONFIG
    config_directory = config_path.parent
    if config_directory.is_symlink() or config_path.is_symlink():
        raise LoopError(f"消费端输出配置不能通过符号链接定位：{OUTPUT_CONFIG.as_posix()}")
    if config_directory.exists() and not config_directory.is_dir():
        raise LoopError(f"消费端输出配置目录不是目录：{config_directory.relative_to(root).as_posix()}")
    if not config_path.exists():
        return set(DEFAULT_OUTPUT_ROOTS)
    if not config_path.is_file():
        raise LoopError(f"消费端输出配置必须是普通文件：{OUTPUT_CONFIG.as_posix()}")
    try:
        config_path.resolve().relative_to(root)
    except ValueError as error:
        raise LoopError("消费端输出配置不能通过符号链接越出仓库根目录") from error
    try:
        config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise LoopError(f"消费端输出配置无法解析：{error}") from error
    if not isinstance(config, dict) or set(config) != {"schema_version", "output_roots"}:
        raise LoopError("消费端输出配置只允许 schema_version 和 output_roots 字段")
    if type(config.get("schema_version")) is not int or config.get("schema_version") != 1:
        raise LoopError("消费端输出配置 schema_version 必须为 1")
    roots = config.get("output_roots")
    if not isinstance(roots, list) or not roots or not all(isinstance(item, str) for item in roots):
        raise LoopError("消费端输出配置 output_roots 必须是非空字符串数组")
    if len(roots) != len(set(roots)):
        raise LoopError("消费端输出配置 output_roots 不能重复")
    allowed = set(DEFAULT_OUTPUT_ROOTS)
    for item in roots:
        if not re.fullmatch(r"[a-z][a-z0-9_-]*", item):
            raise LoopError(f"消费端输出根必须是安全的顶层目录名：{item}")
        if item.casefold() in {"vendor", ".git", "context", "tasks"}:
            raise LoopError(f"消费端输出根不允许使用受保护目录：{item}")
        allowed.add(item)
    return allowed


def safe_path(root: Path, relative: str, *, must_exist: bool = False, output: bool = False) -> Path:
    # 使用仓库相对 POSIX 路径，使同一份任务记录能在 Windows、Linux、macOS 上恢复。
    if not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative:
        raise LoopError("路径必须是非空仓库相对 POSIX 路径")
    parts = relative.split("/")
    if any(part in {"", ".", ".."} for part in parts) or PurePosixPath(relative).is_absolute():
        raise LoopError("路径不允许绝对路径、空片段、. 或 ..")
    if any(part.casefold() in {"vendor", ".git"} for part in parts):
        raise LoopError("任务路径不允许进入 vendor 或 .git")
    if output and parts[0] not in allowed_output_roots(root):
        raise LoopError("作品路径必须位于消费端声明的输出根目录下")
    result = root.joinpath(*parts)
    resolved = result.resolve()
    try:
        resolved_parts = resolved.relative_to(root).parts
    except ValueError as error:
        raise LoopError("路径通过符号链接越出消费端根目录") from error
    if any(part.casefold() in {"vendor", ".git"} for part in resolved_parts):
        raise LoopError("路径通过符号链接进入 vendor 或 .git")
    if output and (not resolved_parts or resolved_parts[0] not in allowed_output_roots(root)):
        raise LoopError("作品路径通过符号链接离开报告或作品目录")
    if must_exist and not result.exists():
        raise LoopError(f"路径不存在：{relative}")
    return result


def task_directory(root: Path, task_id: str) -> Path:
    if not TASK_ID.fullmatch(task_id):
        raise LoopError("任务编号格式错误，应为 EXPR-YYYYMMDD-8位小写十六进制")
    directory = safe_path(root, f"tasks/{task_id}")
    if directory.is_symlink():
        raise LoopError("任务存储目录不允许使用符号链接")
    return directory


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_hash(path: Path) -> str:
    """为单文件或自包含作品目录计算稳定 SHA-256。"""
    if path.is_symlink():
        raise LoopError(f"作品不能是符号链接：{path}")
    if path.is_file():
        return file_hash(path)
    if not path.is_dir():
        raise LoopError(f"作品必须是文件或目录：{path}")
    digest = hashlib.sha256()
    entries = sorted(path.rglob("*"), key=lambda item: item.relative_to(path).as_posix())
    for entry in entries:
        relative = entry.relative_to(path).as_posix()
        if entry.is_symlink():
            raise LoopError(f"作品目录不能包含符号链接：{relative}")
        if entry.is_dir():
            digest.update(f"D\0{relative}\0".encode("utf-8"))
        elif entry.is_file():
            digest.update(f"F\0{relative}\0{file_hash(entry)}\0".encode("utf-8"))
        else:
            raise LoopError(f"作品目录包含无法处理的文件类型：{relative}")
    return digest.hexdigest()


def require_text(value: Any, label: str, *, allow_empty: bool = False) -> None:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise LoopError(f"{label} 必须是{'字符串' if allow_empty else '非空字符串'}")


def require_timestamp(value: Any, label: str) -> None:
    require_text(value, label)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise LoopError(f"{label} 不是 ISO 日期时间") from error
    if parsed.tzinfo is None:
        raise LoopError(f"{label} 必须包含时区")


def validate_task(task: Any, root: Path, task_id: str, *, check_files: bool = True) -> None:
    if not isinstance(task, dict) or type(task.get("schema_version")) is not int or task.get("schema_version") != 1 or task.get("id") != task_id:
        raise LoopError("任务 JSON 的 schema_version 或 id 不合法")
    for name in ("version", "revision"):
        if type(task.get(name)) is not int or task[name] < 1:
            raise LoopError(f"任务 {name} 必须是正整数")
    if task.get("status") not in STATUSES or task.get("mode") not in {"real", "test"}:
        raise LoopError("任务状态或模式不合法")
    for name in ("title", "request", "next_action", "infrastructure_commit"):
        require_text(task.get(name), f"任务 {name}")
    for name in ("created_at", "updated_at"):
        require_timestamp(task.get(name), f"任务 {name}")
    brief = task.get("brief")
    if not isinstance(brief, dict) or any(not isinstance(brief.get(key), str) for key in BRIEF_FIELDS):
        raise LoopError("任务 brief 结构不合法")
    if not isinstance(brief.get("sources"), list) or not all(isinstance(item, str) for item in brief["sources"]):
        raise LoopError("任务 sources 必须是路径数组")
    if brief["output"]:
        safe_path(root, brief["output"], output=True)
    for source in brief["sources"]:
        safe_path(root, source, must_exist=check_files)
    history = task.get("history")
    if not isinstance(history, list) or not history or not all(isinstance(item, dict) for item in history):
        raise LoopError("任务 history 结构不合法")
    if len(history) != task["version"]:
        raise LoopError("任务 history 与 version 不一致")
    previous_revision = 1
    for number, record in enumerate(history, 1):
        if type(record.get("version")) is not int or record.get("version") != number or not isinstance(record.get("note"), str):
            raise LoopError("任务历史版本序列不合法")
        if record.get("kind") not in EVENTS:
            raise LoopError("任务历史事件类型不合法")
        revision = record.get("revision")
        if type(revision) is not int or revision < 1 or revision > task["revision"] or revision not in {previous_revision, previous_revision + 1}:
            raise LoopError("任务历史修订序列不合法")
        previous_revision = revision
        require_text(record.get("note"), "历史 note")
        require_text(record.get("next_action"), "历史 next_action")
        require_timestamp(record.get("at"), "历史 at")
        if "user_quote" in record:
            require_text(record["user_quote"], "历史 user_quote")
    if history[-1]["revision"] != task["revision"]:
        raise LoopError("当前修订与最后历史记录不一致")
    if history[0]["kind"] != "create" or history[0]["revision"] != 1:
        raise LoopError("任务历史必须从第一个修订的 create 事件开始")
    artifacts = task.get("artifacts")
    if not isinstance(artifacts, list):
        raise LoopError("任务 artifacts 必须是数组")
    for item in artifacts:
        if not isinstance(item, dict) or type(item.get("revision")) is not int or not 1 <= item["revision"] <= task["revision"]:
            raise LoopError("作品记录结构不合法")
        if not isinstance(item.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"]):
            raise LoopError("作品记录缺少合法 SHA-256")
        path = safe_path(root, item.get("path"), output=True, must_exist=check_files)
        require_timestamp(item.get("reviewed_at"), "作品 reviewed_at")
        if "accepted_at" in item:
            require_timestamp(item["accepted_at"], "作品 accepted_at")
            require_text(item.get("completion_quote"), "作品 completion_quote")
        elif "completion_quote" in item:
            raise LoopError("未确认的作品不能保存 completion_quote")
        if check_files and not path.is_file() and not path.is_dir():
            raise LoopError("作品记录应指向文件或自包含目录")
        # 过去已确认版本不得被静默改写。这里验证哈希，不宣称提供文件访问控制。
        if check_files and item.get("accepted_at") and artifact_hash(path) != item["sha256"]:
            raise LoopError(f"已确认的历史作品被改动：{item['path']}")
    if task["status"] == "paused" and task.get("resume_status") not in STATUSES - {"paused", "completed"}:
        raise LoopError("暂停任务缺少有效恢复状态")


def load_task(root: Path, task_id: str, *, check_files: bool = True) -> dict[str, Any]:
    path = safe_path(root, f"tasks/{task_id}/task.json", must_exist=True)
    task_directory(root, task_id)
    try:
        task = json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, UnicodeError) as error:
        raise LoopError(f"任务 JSON 无法解析：{error}") from error
    validate_task(task, root, task_id, check_files=check_files)
    return task


def readable_task(root: Path, task_id: str) -> dict[str, Any]:
    # 恢复会话首先要知道目标和下一步。同步缺少附件不能遮蔽任务摘要，
    # 但缺失不能被视作验证通过；诊断只添加到输出，不回写权威 JSON。
    task = load_task(root, task_id, check_files=False)
    diagnostics = []
    for source in task["brief"]["sources"]:
        if not safe_path(root, source).exists():
            diagnostics.append({"kind": "missing_source", "path": source})
    for artifact in task["artifacts"]:
        path = safe_path(root, artifact["path"], output=True)
        if not path.exists():
            diagnostics.append({"kind": "missing_artifact", "path": artifact["path"]})
        elif not path.is_file() and not path.is_dir():
            diagnostics.append({"kind": "artifact_not_file_or_directory", "path": artifact["path"]})
        else:
            try:
                actual = artifact_hash(path)
            except (LoopError, OSError) as error:
                diagnostics.append({"kind": "artifact_unreadable", "path": artifact["path"], "error": str(error)})
                continue
            if actual != artifact["sha256"]:
                diagnostics.append({"kind": "artifact_hash_mismatch", "path": artifact["path"], "accepted": bool(artifact.get("accepted_at"))})
    if diagnostics:
        task["_diagnostics"] = diagnostics
    return task


@contextmanager
def task_lock(directory: Path):
    # 锁只协调本工具的写入，不阻止编辑器或其他程序改文件；不自动删除他人的陈旧锁。
    lock = directory / ".lock"
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise LoopError("任务正在写入或保留了未释放的 .lock；先人工核对，不自动清理") from error
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(f"pid={os.getpid()} at={utc_now()}\n")
        yield
    finally:
        lock.unlink()


def atomic_text(path: Path, content: str) -> None:
    temporary = path.with_name(f".{path.name}.tmp-{uuid.uuid4().hex}")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def markdown_view(task: dict[str, Any]) -> str:
    lines = [
        f"# {task['title']}", "",
        "> 本文件由 task.json 生成，仅供阅读。不要直接编辑；task.json 是唯一事实源。",
        "> 用户确认与来源授权由实际责任主体负责，本工具只记录，不认证其真实性。", "",
        f"- 任务编号：`{task['id']}`", f"- 模式：`{task['mode']}`",
        f"- 状态：`{task['status']}`", f"- 当前修订：{task['revision']}",
        f"- 记录版本：{task['version']}", f"- 基础设施提交：`{task['infrastructure_commit']}`", "",
        "## 原始需求", "", task["request"], "", "## 任务共识", "",
    ]
    for key, label in (("audience", "受众"), ("purpose", "目的"), ("scope", "范围"), ("output", "输出"), ("acceptance", "完成标准")):
        lines.extend([f"### {label}", "", task["brief"][key] or "待讨论", ""])
    lines.extend(["### 来源", ""])
    lines.extend(f"- `{source}`" for source in task["brief"]["sources"])
    if not task["brief"]["sources"]:
        lines.append("待登记")
    lines.extend(["", "## 下一步", "", task["next_action"], "", "## 作品版本", ""])
    for item in task["artifacts"]:
        state = "已确认本轮版本（不代表发布授权）" if item.get("accepted_at") else "待评审"
        lines.append(f"- r{item['revision']}: `{item['path']}`；{state}；SHA-256 `{item['sha256']}`")
    lines.extend(["", "## 决定与进展", ""])
    for item in task["history"]:
        lines.extend([f"### v{item['version']} · {item['kind']} · {item['at']}", "", item["note"], ""])
        if item.get("user_quote"):
            lines.extend(["用户原话（记录者提供，工具未验证）：", "", item["user_quote"], ""])
        if item.get("next_action"):
            lines.extend([f"下一步：{item['next_action']}", ""])
    return "\n".join(lines) + "\n"


def write_view(root: Path, task: dict[str, Any]) -> None:
    path = safe_path(root, f"tasks/{task['id']}/task.md")
    atomic_text(path, markdown_view(task))


def save_task(root: Path, task: dict[str, Any]) -> None:
    validate_task(task, root, task["id"])
    path = safe_path(root, f"tasks/{task['id']}/task.json")
    atomic_text(path, json.dumps(task, ensure_ascii=False, indent=2) + "\n")
    try:
        write_view(root, task)
    except (OSError, LoopError) as error:
        raise LoopError(f"任务 JSON 已保存（id={task['id']}, version={task['version']}），但 task.md 更新失败：{error}。核对问题后用 show 读取并用 render 恢复视图，不要重复创建任务或执行刚才的状态事件") from error


def infrastructure_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(Path(__file__).resolve().parents[3]), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5, check=False,
        )
        value = result.stdout.strip()
        return value if result.returncode == 0 and re.fullmatch(r"[0-9a-f]{40,64}", value) else "unknown"
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"


def add_history(task: dict[str, Any], kind: str, note: str, next_action: str, user_quote: str | None = None) -> None:
    task["updated_at"] = utc_now()
    task["next_action"] = next_action
    record = {"version": task["version"], "revision": task["revision"], "at": task["updated_at"], "kind": kind, "note": note, "next_action": next_action}
    if user_quote:
        record["user_quote"] = user_quote
    task["history"].append(record)


def create_task(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    now = utc_now()
    for _ in range(10):
        task_id = f"EXPR-{datetime.now(timezone.utc):%Y%m%d}-{uuid.uuid4().hex[:8]}"
        directory = task_directory(root, task_id)
        try:
            directory.mkdir()
            break
        except FileExistsError:
            continue
    else:
        raise LoopError("无法分配不冲突的任务编号")
    task = {
        "schema_version": 1, "id": task_id, "title": args.title, "mode": "test" if args.test else "real",
        "status": "clarifying", "revision": 1, "version": 1,
        "brief": {**{key: "" for key in BRIEF_FIELDS}, "sources": []},
        "request": args.request, "history": [], "next_action": "", "artifacts": [],
        "created_at": now, "updated_at": now, "infrastructure_commit": infrastructure_commit(),
    }
    add_history(task, "create", "登记任务草案；未知信息留待讨论，不替用户确认", "与用户澄清受众、目的、范围和完成标准")
    with task_lock(directory):
        save_task(root, task)
    return task


def require_status(task: dict[str, Any], *allowed: str) -> None:
    if task["status"] not in allowed:
        raise LoopError(f"当前状态 {task['status']} 不允许该事件；允许状态：{', '.join(allowed)}")


def require_quote(args: argparse.Namespace) -> str:
    quote = args.user_quote
    if not quote or not quote.strip():
        raise LoopError("此事件需要 --user-quote 记录实际用户确认；不得由 Agent 编造")
    return quote


def current_artifact(task: dict[str, Any]) -> dict[str, Any]:
    matching = [item for item in task["artifacts"] if item["revision"] == task["revision"]]
    if not matching:
        raise LoopError("当前修订没有已登记的待评审作品")
    return matching[-1]


def apply_event(root: Path, task: dict[str, Any], args: argparse.Namespace) -> None:
    event = args.type
    if not args.note.strip():
        raise LoopError("事件 --note 不能为空，应说明本次决定、进度或停止原因")
    quote = args.user_quote
    following = args.next_action
    if event == "align":
        require_status(task, "clarifying")
        quote = require_quote(args)
        if any(not task["brief"][key].strip() for key in BRIEF_FIELDS) or not task["brief"]["sources"]:
            raise LoopError("对齐前须登记受众、目的、范围、输出、完成标准及至少一个实际来源")
        task["status"] = "ready"
        following = following or "在已确认目标与授权范围内开始工作"
    elif event == "start":
        require_status(task, "ready")
        task["status"] = "working"
        following = following or "调用已登记能力，制作并检查本轮草稿"
    elif event == "review":
        require_status(task, "working")
        if not args.artifact:
            raise LoopError("进入评审需要 --artifact 指定实际作品文件或自包含目录")
        path = safe_path(root, args.artifact, output=True, must_exist=True)
        if not path.is_file() and not path.is_dir():
            raise LoopError("评审入口接受单个作品文件或自包含作品目录")
        if any(safe_path(root, item["path"], output=True).resolve() == path.resolve() and item["revision"] != task["revision"] for item in task["artifacts"]):
            raise LoopError("新修订不能复用过去版本的作品路径，请写入新版本路径")
        task["artifacts"].append({"revision": task["revision"], "path": args.artifact, "sha256": artifact_hash(path), "reviewed_at": utc_now()})
        task["status"] = "review"
        following = following or "向用户展示具体版本，收集反馈或本轮确认"
    elif event in {"feedback", "reopen"}:
        allowed = ("ready", "working", "review") if event == "feedback" else ("completed",)
        require_status(task, *allowed)
        original_status = task["status"]
        task["revision"] += 1
        task["status"] = "clarifying" if args.scope == "scope" else ("ready" if original_status == "ready" else "working")
        following = following or ("重新讨论改变后的目标或边界" if args.scope == "scope" else "按反馈修订，使用新的作品版本路径")
    elif event == "complete":
        require_status(task, "review")
        quote = require_quote(args)
        artifact = current_artifact(task)
        path = safe_path(root, artifact["path"], output=True, must_exist=True)
        if artifact_hash(path) != artifact["sha256"]:
            raise LoopError("待评审作品已变化，不能沿用此前确认；记录反馈并提交新的修订版本")
        artifact["accepted_at"] = utc_now()
        artifact["completion_quote"] = quote
        task["status"] = "completed"
        following = following or "本轮完成；以后可通过任务编号恢复优化，发布授权仍须单独确认"
    elif event == "pause":
        require_status(task, "clarifying", "ready", "working", "review")
        if not following or not following.strip():
            raise LoopError("暂停前需要 --next-action 保存恢复入口")
        task["resume_status"] = task["status"]
        task["status"] = "paused"
    elif event == "resume":
        require_status(task, "paused")
        task["status"] = task.pop("resume_status")
        following = following or task["next_action"]
    elif event == "checkpoint":
        require_status(task, "clarifying", "ready", "working", "review", "paused")
        if not following or not following.strip():
            raise LoopError("检查点需要 --next-action 保存下一步")
    add_history(task, event, args.note, following, quote)


def update_task(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    directory = task_directory(root, args.id)
    if not directory.is_dir():
        raise LoopError("任务不存在")
    with task_lock(directory):
        task = load_task(root, args.id)
        if task["version"] != args.expect_version:
            raise LoopError(f"记录版本冲突：预期 {args.expect_version}，实际 {task['version']}；先 show 重新读取，不能覆盖他人修改")
        if args.command == "render":
            write_view(root, task)
            return task
        task["version"] += 1
        if args.command == "brief":
            require_status(task, "clarifying")
            changed = False
            for key in BRIEF_FIELDS:
                value = getattr(args, key)
                if value is not None:
                    task["brief"][key] = value
                    changed = True
            if args.source is not None:
                task["brief"]["sources"] = args.source
                changed = True
            if not changed:
                raise LoopError("brief 至少需要一个更新字段")
            add_history(task, "brief", "更新任务草案；此操作不代表用户已确认", "讨论并记录实际用户确认")
        else:
            apply_event(root, task, args)
        save_task(root, task)
        return task


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--root", required=True, help="明确指定消费端资产仓库根目录")
    commands = result.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create", help="从用户需求建立任务草案")
    create.add_argument("--title", required=True)
    create.add_argument("--request", required=True)
    create.add_argument("--test", action="store_true", help="明确标记隔离验证任务，不作为真实项目任务")
    commands.add_parser("list", help="只读列出任务")
    show = commands.add_parser("show", help="只读显示任务、历史和下一步")
    show.add_argument("id")
    validate = commands.add_parser("validate", help="只读检查记录结构、来源与全部历史作品哈希")
    validate.add_argument("id", nargs="?")
    for name in ("brief", "event", "render"):
        command = commands.add_parser(name)
        command.add_argument("id")
        command.add_argument("--expect-version", required=True, type=int, help="最近一次 show 返回的 version")
        if name == "brief":
            for key in BRIEF_FIELDS:
                command.add_argument(f"--{key}")
            command.add_argument("--source", action="append", help="重复传入以替换全部来源路径")
        elif name == "event":
            command.add_argument("--type", required=True, choices=("align", "start", "checkpoint", "review", "feedback", "pause", "resume", "complete", "reopen"))
            command.add_argument("--note", required=True)
            command.add_argument("--next-action")
            command.add_argument("--artifact")
            command.add_argument("--scope", choices=("minor", "scope"), default="minor")
            command.add_argument("--user-quote")
    return result


def main(argv: list[str] | None = None) -> int:
    # task JSON 是跨进程协议；不同终端语言不应改变 Agent 收到的编码。
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    args = parser().parse_args(argv)
    try:
        root = consumer_root(args.root)
        if args.command == "create":
            if not args.title.strip() or not args.request.strip():
                raise LoopError("任务标题和原始需求不能为空")
            output = create_task(root, args)
        elif args.command == "show":
            output = readable_task(root, args.id)
        elif args.command == "list":
            output = []
            for task_id in sorted(path.name for path in (root / "tasks").iterdir() if TASK_ID.fullmatch(path.name)):
                try:
                    output.append(readable_task(root, task_id))
                except (LoopError, OSError, KeyError, TypeError) as error:
                    output.append({"id": task_id, "error": str(error)})
        elif args.command == "validate":
            task_ids = [args.id] if args.id else sorted(path.name for path in (root / "tasks").iterdir() if TASK_ID.fullmatch(path.name))
            tasks = [load_task(root, task_id) for task_id in task_ids]
            # 全量审计也检查未确认的旧修订，避免把已被覆盖的历史误作可追溯版本。
            for task in tasks:
                for artifact in task["artifacts"]:
                    if artifact_hash(safe_path(root, artifact["path"], output=True, must_exist=True)) != artifact["sha256"]:
                        raise LoopError(f"历史作品内容与记录 SHA-256 不一致：{artifact['path']}")
            output = {"valid": True, "tasks": task_ids}
        else:
            output = update_task(root, args)
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    except (LoopError, OSError) as error:
        print(f"Task loop failed: {error}", file=sys.stderr)
        return 1
    except (KeyError, TypeError) as error:
        print(f"Task loop failed: 任务记录结构损坏，请核对 task.json：{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
