#!/usr/bin/env python3
"""幂等安装消费端基础设施 Harness；默认只预览，拒绝覆盖冲突规则。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tempfile

REPOSITORY = "suanhai-team-external-expression-infrastructure"
EXPECTED_URL = f"https://github.com/suanhaitech/{REPOSITORY}.git"
TOOL_ID = "consumer.infrastructure-adoption-harness"
REQUIRED_CAPABILITIES = {
    "consumer.submodule-preflight": {
        "kind": "tool",
        "path": "infrastructure/repository-management/tools/submodule-preflight",
        "entrypoint": "infrastructure/repository-management/tools/submodule-preflight/submodule_preflight.py",
    },
}
TOOL_PATH = "infrastructure/repository-management/tools/infrastructure-adoption-harness"
ENTRYPOINT = f"{TOOL_PATH}/install_harness.py"
BEGIN_V1 = "<!-- BEGIN suanhai-infrastructure-consumer-harness:v1 -->"
END_V1 = "<!-- END suanhai-infrastructure-consumer-harness:v1 -->"
BEGIN = "<!-- BEGIN suanhai-infrastructure-consumer-harness:v2 -->"
END = "<!-- END suanhai-infrastructure-consumer-harness:v2 -->"
GIT_SHA = re.compile(r"\A[0-9a-f]{40}\Z")


class HarnessInstallError(Exception):
    """仓库状态、版本锁或 AGENTS.md 内容不满足安全安装前提。"""


def is_link(path: Path) -> bool:
    """识别符号链接与 Windows reparse point，避免写入边界被重定向。"""
    if path.is_symlink():
        return True
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except (FileNotFoundError, NotADirectoryError):
        return False
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise HarnessInstallError(f"git {' '.join(arguments)} 失败：{detail}")
    return result.stdout.rstrip("\r\n")


def validate_submodule_path(value: str) -> str:
    if not value or "\\" in value or ":" in value:
        raise HarnessInstallError("submodule 路径必须是非空仓库相对 POSIX 路径")
    raw_parts = value.split("/")
    if any(part in {"", ".", ".."} for part in raw_parts):
        raise HarnessInstallError("submodule 路径不允许空片段、. 或 ..")
    path = PurePosixPath(value)
    if path.is_absolute():
        raise HarnessInstallError("submodule 路径不允许绝对路径、空片段、. 或 ..")
    return path.as_posix()


def parse_gitlink(root: Path, relative: str) -> str:
    output = git(root, "ls-files", "--stage", "-z", "--", relative)
    entries = [entry for entry in output.split("\0") if entry]
    if len(entries) != 1:
        raise HarnessInstallError(f"{relative} 必须在父仓 index 中恰好有一个 gitlink")
    header, separator, entry_path = entries[0].partition("\t")
    fields = header.split()
    if not separator or entry_path != relative or len(fields) != 3:
        raise HarnessInstallError(f"{relative} 在父仓 index 中不是合法 gitlink 记录")
    mode, gitlink, stage = fields
    if mode != "160000" or stage != "0" or not GIT_SHA.fullmatch(gitlink):
        raise HarnessInstallError("父仓 gitlink SHA 无效或仍有未解决的合并冲突")
    return gitlink


def assert_registered_tool(infrastructure: Path) -> None:
    manifest_path = infrastructure / "manifest.yml"
    if not manifest_path.is_file() or is_link(manifest_path):
        raise HarnessInstallError("固定 submodule 缺少普通文件 manifest.yml")
    try:
        manifest = manifest_path.read_text(encoding="utf-8-sig")
    except UnicodeError as error:
        raise HarnessInstallError("基础设施 manifest.yml 不是有效 UTF-8") from error
    if re.findall(r"(?m)^schema_version: (.+?)\s*$", manifest) != ["2"]:
        raise HarnessInstallError("固定版本 Manifest 的 schema_version 不是 2")
    if re.findall(r"(?m)^repository: (.+?)\s*$", manifest) != [REPOSITORY]:
        raise HarnessInstallError("固定版本 Manifest 的 repository 标识不正确")

    matches = list(re.finditer(
        rf"(?ms)^  - id: {re.escape(TOOL_ID)}\s*\n(.*?)(?=^  - id: |\Z)",
        manifest,
    ))
    if len(matches) != 1:
        message = "未注册" if not matches else "重复注册"
        raise HarnessInstallError(f"固定版本 Manifest {message} {TOOL_ID}")
    capability = matches[0].group(1)
    expected_fields = {
        "kind": "tool",
        "path": TOOL_PATH,
        "entrypoint": ENTRYPOINT,
    }
    for field, expected in expected_fields.items():
        values = re.findall(rf"(?m)^    {field}: (.*?)\s*$", capability)
        if values != [expected]:
            raise HarnessInstallError(f"{TOOL_ID} 的 {field} 不符合工具接口")

    for capability_id, expected in REQUIRED_CAPABILITIES.items():
        declarations = list(re.finditer(
            rf"(?ms)^  - id: {re.escape(capability_id)}\s*\n(.*?)(?=^  - id: |\Z)",
            manifest,
        ))
        if len(declarations) != 1:
            raise HarnessInstallError(
                f"固定版本 Manifest 必须唯一声明长期 Harness 依赖 {capability_id}"
            )
        dependency = declarations[0].group(1)
        for field, value in expected.items():
            values = re.findall(rf"(?m)^    {field}: (.*?)\s*$", dependency)
            if values != [value]:
                raise HarnessInstallError(
                    f"长期 Harness 依赖 {capability_id} 的 {field} 不符合接口约定"
                )

        # 不能只信 Manifest 声明：安装后的根 Harness 会直接依赖这个入口。
        # 同时拒绝符号链接，避免入口或目录跳出固定 submodule 边界。
        for relative in (expected["path"], expected["entrypoint"]):
            target = infrastructure.joinpath(*PurePosixPath(relative).parts)
            current = infrastructure
            for part in PurePosixPath(relative).parts:
                current = current / part
                if current.exists() and is_link(current):
                    raise HarnessInstallError(
                        f"长期 Harness 依赖 {capability_id} 的路径不能包含符号链接：{relative}"
                    )
            if relative == expected["path"]:
                valid_type = target.is_dir()
            else:
                valid_type = target.is_file()
            if not valid_type:
                raise HarnessInstallError(
                    f"长期 Harness 依赖 {capability_id} 的入口路径不存在或类型错误：{relative}"
                )
            try:
                target.resolve(strict=True).relative_to(infrastructure.resolve(strict=True))
            except (OSError, ValueError) as error:
                raise HarnessInstallError(
                    f"长期 Harness 依赖 {capability_id} 的路径越出固定 submodule：{relative}"
                ) from error

    # 安装后 Harness 引用的三个协议文件也必须随固定版本存在，避免接入成功后留下死链接。
    required_documents = (
        "docs/consumer-repository-bootstrap.md",
        "docs/consumer-repository-harness-v0.1.md",
        "docs/submodule-consumer-versioning.md",
    )
    for document in required_documents:
        path = infrastructure / document
        if is_link(path) or not path.is_file():
            raise HarnessInstallError(f"固定版本缺少 Harness 必需协议文件 {document}")
        try:
            path.resolve(strict=True).relative_to(infrastructure.resolve(strict=True))
        except (OSError, ValueError) as error:
            raise HarnessInstallError(f"协议文件通过符号链接越出固定 submodule：{document}") from error


def configured_submodule(root: Path, relative: str) -> None:
    modules_file = root / ".gitmodules"
    if not modules_file.is_file() or is_link(modules_file):
        raise HarnessInstallError("父仓库缺少普通文件 .gitmodules")

    # -z 配合 key\nvalue 记录，避免 --get-regexp 的空白分隔符误拆含空格路径。
    result = subprocess.run(
        ["git", "-C", str(root), "config", "--null", "--file", ".gitmodules", "--list"],
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise HarnessInstallError("无法解析父仓库 .gitmodules")
    entries: list[tuple[str, str]] = []
    try:
        for record in result.stdout.split(b"\0"):
            if not record:
                continue
            key, separator, value = record.partition(b"\n")
            if not separator:
                raise HarnessInstallError(".gitmodules 配置记录格式无效")
            key_text = key.decode("utf-8")
            value_text = value.decode("utf-8")
            entries.append((key_text, value_text))
    except UnicodeDecodeError as error:
        raise HarnessInstallError(".gitmodules 路径或键不是有效 UTF-8") from error

    matching = [key[:-5] for key, value in entries if key.lower().startswith("submodule.") and key.lower().endswith(".path") and value == relative]
    if len(matching) != 1:
        raise HarnessInstallError(f".gitmodules 必须唯一登记路径 {relative}")
    section = matching[0]
    urls = [value for key, value in entries if key.lower() == f"{section}.url".lower()]
    if len(urls) != 1 or urls[0] != EXPECTED_URL:
        raise HarnessInstallError(f"submodule URL 必须是 {EXPECTED_URL}")


def assert_submodule(root: Path, relative: str) -> tuple[Path, str]:
    configured_submodule(root, relative)
    gitlink = parse_gitlink(root, relative)

    infrastructure = root.joinpath(*relative.split("/"))
    current = root
    for part in relative.split("/"):
        current = current / part
        if current.exists() and is_link(current):
            raise HarnessInstallError("submodule 路径的任何组成部分都不能是符号链接或 junction")
    try:
        infrastructure.resolve(strict=True).relative_to(root.resolve(strict=True))
    except (OSError, ValueError) as error:
        raise HarnessInstallError("submodule 不存在或路径越出父仓库") from error
    if not infrastructure.is_dir():
        raise HarnessInstallError("submodule 尚未初始化")

    expected_script = infrastructure / ENTRYPOINT
    if is_link(expected_script) or not expected_script.is_file():
        raise HarnessInstallError(f"固定 submodule 缺少工具入口 {ENTRYPOINT}")
    try:
        expected_script.resolve(strict=True).relative_to(infrastructure.resolve(strict=True))
    except (OSError, ValueError) as error:
        raise HarnessInstallError("工具入口通过符号链接越出固定 submodule") from error
    if Path(__file__).resolve() != expected_script.resolve():
        raise HarnessInstallError("必须从父仓固定 gitlink 对应版本的 submodule 内运行本工具")
    assert_registered_tool(infrastructure)

    head = git(infrastructure, "rev-parse", "HEAD")
    if head != gitlink:
        raise HarnessInstallError(f"submodule HEAD ({head}) 与父仓 index gitlink ({gitlink}) 不一致")
    if git(infrastructure, "status", "--porcelain=v1", "--untracked-files=all"):
        raise HarnessInstallError("基础设施 submodule 工作区不干净；工具不会修改 submodule")
    return infrastructure, gitlink


def render_harness_v1(relative: str) -> str:
    """返回旧版安装器生成的精确文本，仅用于识别可安全迁移的段落。"""
    harness = f"""{BEGIN_V1}
## 共享 Suanhai 对外表达基础设施

本仓库通过 §{relative}§ 固定使用 Suanhai 团队对外表达基础设施。每次新会话从本仓根目录开始，先遵守本仓规则并读取根 §README.md§、§AGENTS.md§；再读取该路径下的 §manifest.yml§、§docs/consumer-repository-bootstrap.md§、§docs/consumer-repository-harness-v0.1.md§、§docs/submodule-consumer-versioning.md§ 和本次任务所需能力入口。

按本仓自己的目录和规则定位任务、上下文、来源、产物与评审记录，只读取当前请求相关的材料。既有仓库不要求迁移成公共模板结构；若本仓没有清楚说明这些对象放在哪里，先向负责人确认，不新建目录或移动文件来猜测约定。

用户提出新的对外表达任务时，若固定 Manifest 显式列出 §expression.task-loop§，读取其工作流入口；并仅在同时列出 §expression.task-record§ 时用该工具登记和推进任务。先将请求整理为任务草案，和用户澄清目标、受众、范围、来源、输出与完成条件；用户确认方向后再进入制作。用户给出任务编号时先用已声明的记录能力读取当前状态并续作，不重复建任务。若上述能力未列出，使用本仓已有任务协议；没有适用协议时先向负责人说明缺口，不伪称共享任务能力可用。

用户要求初始化小组或项目上下文时，若固定 Manifest 显式列出 §consumer.group-asset-onboarding§，读取并按该工作流推进；保留本仓现有结构和事实，不把初始化请求扩展成创建任务、作品或发布授权。

完成任务对齐后，结合本仓任务和上下文判断适合调用的共享能力。只有固定版本 Manifest 的 §capabilities§ 中显式列出的能力才可调用，并按 §uses§ 读取其入口和依赖；匹配能力时按能力 ID 路由，不匹配时继续遵循本仓既有流程。目录存在、占位说明或远端分支前进都不代表能力可用。

沿用本仓库自己的上下文、任务、产物、CI 和责任边界，不要求迁移成公共模板结构；只有任务适合且用户提出或同意时才调用共享工作流、工具或模板，不自动创建公共模板目录。首次使用共享能力前，若父仓 HEAD 已记录 gitlink，运行 Manifest 声明的 §consumer.submodule-preflight§ 并使用实际路径；同一会话中仓库状态未变化时不必重复远端查询。gitlink 尚未提交时按本地 index 协议检查，不把完整预检失败当作通过。记录本任务实际使用的能力 ID 和固定 submodule commit。项目事实、来源、任务、产物和评审留在父仓；默认不修改 submodule。发现 gitlink 漂移、脏 submodule、缺失对象或入口缺失时停止。版本更新必须使用 Manifest 中实际存在的 §consumer.submodule-update§ 工作流，固定完整 commit，不自动跟随远端。

新 clone 如果父仓已有 gitlink、但 submodule 尚未初始化，在路径无冲突且无本地修改时按本仓规则运行 §git submodule update --init --recursive -- {relative}§ 恢复固定版本；这不是升级。能力发现不等于权限、专业事实确认或发布授权。遵循本仓规则和用户授权执行有副作用的动作。
{END_V1}"""
    return harness.replace("§", chr(96))


def render_harness(relative: str) -> str:
    harness = f"""{BEGIN}
## 共享 Suanhai 对外表达基础设施

本仓库通过 §{relative}§ 固定使用 Suanhai 团队对外表达基础设施。每次新会话从本仓根目录开始，先遵守本仓规则并读取根 §README.md§、§AGENTS.md§；再读取该路径下的 §manifest.yml§、§docs/consumer-repository-bootstrap.md§、§docs/consumer-repository-harness-v0.1.md§、§docs/submodule-consumer-versioning.md§ 和本次任务所需能力入口。

按本仓自己的目录和规则定位任务、上下文、来源、产物与评审记录，只读取当前请求相关的材料。既有仓库不要求迁移成公共模板结构；若本仓没有清楚说明这些对象放在哪里，先向负责人确认，不新建目录或移动文件来猜测约定。

用户询问“你是谁”“你在本仓库扮演什么角色”或“这个仓库是什么”时，先根据本规则说明 Agent 的仓库工作角色与边界，并读取根 §README.md§ 说明仓库定位。区分运行环境提供的模型/客户端身份、仓库工作角色、小组身份和项目身份；只有用户询问小组或项目时，才按本仓规则读取对应上下文。只问身份不创建任务、不扫描无关项目资料；未知或待确认的事实明确说明，不从仓库路径、Git 作者或当前操作者推断。

用户提出新的对外表达任务时，若固定 Manifest 显式列出 §expression.task-loop§，读取其工作流入口；并仅在同时列出 §expression.task-record§ 时用该工具登记和推进任务。先将请求整理为任务草案，和用户澄清目标、受众、范围、来源、输出与完成条件；用户确认方向后再进入制作。用户给出任务编号时先用已声明的记录能力读取当前状态并续作，不重复建任务。若上述能力未列出，使用本仓已有任务协议；没有适用协议时先向负责人说明缺口，不伪称共享任务能力可用。

用户要求初始化小组或项目上下文时，若固定 Manifest 显式列出 §consumer.group-asset-onboarding§，读取并按该工作流推进；保留本仓现有结构和事实，不把初始化请求扩展成创建任务、作品或发布授权。

完成任务对齐后，结合本仓任务和上下文判断适合调用的共享能力。只有固定版本 Manifest 的 §capabilities§ 中显式列出的能力才可调用，并按 §uses§ 读取其入口和依赖；匹配能力时按能力 ID 路由，不匹配时继续遵循本仓既有流程。目录存在、占位说明或远端分支前进都不代表能力可用。

沿用本仓库自己的上下文、任务、产物、CI 和责任边界，不要求迁移成公共模板结构；只有任务适合且用户提出或同意时才调用共享工作流、工具或模板，不自动创建公共模板目录。每次准备调用一个独立的顶层共享能力前，若父仓 HEAD 已记录 gitlink，先运行 Manifest 声明的 §consumer.submodule-preflight§ 并使用实际路径；确认本地状态后再读取和调用该能力。gitlink 尚未提交时按本地 index 协议检查，不把完整预检失败当作通过。记录本任务实际使用的能力 ID 和固定 submodule commit。

一次顶层工作流从开始到结束固定使用预检得到的完整 SHA；它通过 §uses§ 调用的依赖能力沿用同一 SHA，不重复查询。新的独立顶层能力调用（包括同一会话里的另一个任务或报告）重新预检；仅继续当前尚未中断的工作流时复用快照。发现父仓 gitlink 与 submodule HEAD 不一致、父仓 submodule 路径或 submodule 工作区有改动、固定对象缺失或本地能力入口缺失时，停止相关调用。

若预检显示 §status=update-available§ 且本地检查通过，向用户同时报告当前 gitlink SHA 与远端 §main§ SHA，并说明这只是远端指针不同，不证明候选是快进提交、包含新能力或已验收。若用户本轮已明确要求更新，按其要求进入 §consumer.submodule-update§ 并展示计划、等待更新确认；否则暂停该顶层能力，请用户选择暂缓更新、继续使用当前固定 SHA，或立即进入该受控更新流程。更新工作流复用触发本次更新的预检快照，避免递归预检。只有用户已授权提交、更新后的 gitlink 已进入父仓 §HEAD§、父仓工作区干净且完整预检通过后，才能从新固定 SHA 重新开始原顶层能力；提交尚未获授权时保留现场并暂停原能力，等待授权提交和后续预检。若远端查询失败，明确标记为未知；本地检查通过时可继续使用当前固定 SHA，但不得声称已与远端同步。任何本地检查失败都必须停止。远端变化和用户选择都不能让正在进行的工作流中途切换版本。

新 clone 如果父仓已有 gitlink、但 submodule 尚未初始化，在路径无冲突且无本地修改时按本仓规则运行 §git submodule update --init --recursive -- {relative}§ 恢复固定版本；这不是升级。能力发现不等于权限、专业事实确认或发布授权。遵循本仓规则和用户授权执行有副作用的动作。
{END}"""
    return harness.replace("§", chr(96))


def plan_install(agents_file: Path, relative: str) -> tuple[bytes | None, bytes, str, str, str]:
    if is_link(agents_file):
        raise HarnessInstallError("消费端根 AGENTS.md 不能是符号链接或 junction")
    if agents_file.exists() and not agents_file.is_file():
        raise HarnessInstallError("消费端根 AGENTS.md 已存在但不是普通文件")

    original = agents_file.read_bytes() if agents_file.exists() else None
    if original is not None:
        try:
            original.decode("utf-8")
        except UnicodeDecodeError as error:
            raise HarnessInstallError("现有 AGENTS.md 不是 UTF-8；未写入任何内容") from error
    newline = "\r\n" if original and b"\r\n" in original else "\r" if original and b"\r" in original and b"\n" not in original else "\n"

    expected = render_harness(relative)
    original_bytes = original or b""
    marker_pairs = (
        (BEGIN_V1.encode("ascii"), END_V1.encode("ascii"), render_harness_v1(relative)),
        (BEGIN.encode("ascii"), END.encode("ascii"), expected),
    )
    present_versions = [
        (begin, end, legacy)
        for begin, end, legacy in marker_pairs
        if begin in original_bytes or end in original_bytes
    ]
    if not present_versions:
        if original is None or not original:
            separator = b""
        elif original.endswith((b"\n", b"\r")):
            separator = newline.encode("ascii")
        else:
            separator = (newline * 2).encode("ascii")
        addition = (expected.replace("\n", newline) + newline).encode("utf-8")
        updated = (original or b"") + separator + addition
        action = "create" if original is None else "append"
    else:
        if len(present_versions) != 1:
            raise HarnessInstallError("Harness 标记版本混用或重复；未改动 AGENTS.md")
        begin_marker, end_marker, old_harness = present_versions[0]
        if original_bytes.count(begin_marker) != 1 or original_bytes.count(end_marker) != 1:
            raise HarnessInstallError("Harness 标记重复或不成对；未改动 AGENTS.md")
        start = original_bytes.index(begin_marker)
        end_start = original_bytes.index(end_marker)
        if end_start < start:
            raise HarnessInstallError("Harness 结束标记位于开始标记之前；未改动 AGENTS.md")
        end = end_start + len(end_marker)
        existing = original_bytes[start:end].replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        if existing != old_harness.encode("utf-8"):
            raise HarnessInstallError("Harness 标记内存在不同内容；工具不会自动合并或覆盖")
        if begin_marker == BEGIN.encode("ascii"):
            return original, original_bytes, "unchanged", expected, ""

        replacement = expected.replace("\n", newline).encode("utf-8")
        updated = original_bytes[:start] + replacement + original_bytes[end:]
        old_display = existing.decode("utf-8").splitlines(keepends=True)
        new_display = expected.splitlines(keepends=True)
        diff = (
            "--- AGENTS.md\n+++ AGENTS.md (planned)\n@@ replace v1 Harness with v2 @@\n"
            + "".join(f"-{line}" if line.endswith("\n") else f"-{line}\n" for line in old_display)
            + "".join(f"+{line}" if line.endswith("\n") else f"+{line}\n" for line in new_display)
        )
        return original, updated, "upgrade", expected, diff

    encoded = updated
    fromfile = "AGENTS.md" if original is not None else "/dev/null"
    header = f"--- {fromfile}\n+++ AGENTS.md (planned)\n@@ append at EOF @@\n"
    appended = (separator + addition).decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    diff = header + "".join(f"+{line}" for line in appended.splitlines(keepends=True))
    return original, encoded, action, expected, diff


def plan_fingerprint(relative: str, gitlink: str, original: bytes | None, updated: bytes) -> str:
    """把dry-run 预览的计划绑定到原文、结果、submodule 路径和固定版本。"""
    payload = {
        "submodule_path": relative,
        "submodule_commit": gitlink,
        "original_sha256": hashlib.sha256(original).hexdigest() if original is not None else None,
        "planned_sha256": hashlib.sha256(updated).hexdigest(),
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def apply_bytes(path: Path, original: bytes | None, updated: bytes) -> None:
    """原子写临时文件，并在替换前再次比对原文以避免覆盖并发修改。"""
    if is_link(path):
        raise HarnessInstallError("AGENTS.md 在预览后变成符号链接或 junction；拒绝写入")
    if path.exists():
        current = path.read_bytes()
        if original != current:
            raise HarnessInstallError("AGENTS.md 在预览后已变化；拒绝覆盖新内容")
        mode = stat.S_IMODE(path.stat().st_mode)
    else:
        if original is not None:
            raise HarnessInstallError("AGENTS.md 在预览后被移除；拒绝重建")
        mode = 0o644

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("wb", prefix=".suanhai-harness-", suffix=".tmp", dir=path.parent, delete=False) as temporary:
            temp_path = Path(temporary.name)
            temporary.write(updated)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.chmod(temp_path, mode)
        if is_link(path):
            raise HarnessInstallError("AGENTS.md 在写入前变成符号链接或 junction；拒绝写入")
        if path.exists() and path.read_bytes() != original:
            raise HarnessInstallError("AGENTS.md 在写入前再次发生变化；拒绝覆盖")
        if original is None and path.exists():
            raise HarnessInstallError("AGENTS.md 在预览后新建；拒绝覆盖")
        if not path.exists() and original is not None:
            raise HarnessInstallError("AGENTS.md 在写入前被移除；拒绝重建")
        os.replace(temp_path, path)
        temp_path = None
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="消费端 Git 仓库根目录")
    parser.add_argument("--submodule-path", default=f"vendor/{REPOSITORY}", help="父仓中基础设施 submodule 的相对 POSIX 路径")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="只预览，不写入；默认")
    mode.add_argument("--apply", action="store_true", help="应用计划中的 AGENTS.md 变更")
    parser.add_argument("--expect-plan-sha256", help="必须等于本次 dry-run 计划的 SHA-256；--apply 必填")
    args = parser.parse_args(argv)

    try:
        if args.apply and not args.expect_plan_sha256:
            raise HarnessInstallError("--apply 必须携带 dry-run 返回的 --expect-plan-sha256")
        if args.expect_plan_sha256 and (not args.apply or not re.fullmatch(r"[0-9a-f]{64}", args.expect_plan_sha256)):
            raise HarnessInstallError("--expect-plan-sha256 仅用于 --apply，且必须是 64 位小写 SHA-256")
        root = Path(args.root).expanduser().resolve(strict=True)
        if not root.is_dir() or not (root / ".git").exists():
            raise HarnessInstallError("--root 必须是已初始化的消费端 Git 仓库")
        if Path(git(root, "rev-parse", "--show-toplevel")).resolve() != root:
            raise HarnessInstallError("--root 必须指向消费端仓库根目录")
        relative = validate_submodule_path(args.submodule_path)
        _, gitlink = assert_submodule(root, relative)
        agents_file = root / "AGENTS.md"
        original, updated, action, planned_harness, planned_diff = plan_install(agents_file, relative)
        plan_sha256 = plan_fingerprint(relative, gitlink, original, updated)
        if args.apply and args.expect_plan_sha256 != plan_sha256:
            raise HarnessInstallError("当前安装计划与 dry-run 的 SHA-256 不一致；请重新预览")
        if args.apply and action != "unchanged":
            apply_bytes(agents_file, original, updated)
        print(json.dumps({
            "ok": True,
            "mode": "apply" if args.apply else "dry-run",
            "submodule_path": relative,
            "submodule_commit": gitlink,
            "agents_action": action,
            "written": args.apply and action != "unchanged",
            "would_write": action != "unchanged",
            "planned_harness": planned_harness,
            "planned_diff": planned_diff,
            "plan_sha256": plan_sha256,
            "note": "仅管理带标记的共享 Harness；不暂存、不提交、不推送，也不修改 submodule。",
        }, ensure_ascii=False, indent=2))
        return 0
    except (OSError, UnicodeError, HarnessInstallError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
