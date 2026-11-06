#!/usr/bin/env python3
"""登记并核验消费端本地来源素材；来源 URL 只记录，不执行网络请求。"""
from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
from pathlib import Path, PurePosixPath
import re
import struct
import sys
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET


def _artifact_root(root: Path) -> Path:
    """边界和目标统一使用物理绝对路径，避免把同一目录的别名误判为越界。

    Windows 的 TEMP 可能是 8.3 短路径；目标 resolve 后会变成长路径。若根目录
    仍用短路径或相对路径比较，合法文件也会被拒绝。先规范化两侧，仍然拒绝
    素材符号链接逃出实际产物根，而不是通过放宽边界来兼容路径别名。
    """
    boundary = Path(root).resolve(strict=True)
    if not boundary.is_dir():
        raise ValueError("素材根必须是存在的目录")
    return boundary


def local_file(root: Path, relative: str) -> Path:
    root = _artifact_root(root)
    if not isinstance(relative, str) or "\\" in relative or ":" in relative:
        raise ValueError("素材路径必须为使用 / 的相对路径")
    rel = PurePosixPath(relative)
    if rel.is_absolute() or not rel.parts or any(part in {".", ".."} for part in rel.parts):
        raise ValueError(f"不安全素材路径：{relative}")
    target = (root / str(rel)).resolve(strict=True)
    if not target.is_relative_to(root) or not target.is_file():
        raise ValueError(f"素材越出产物目录或不是文件：{relative}")
    return target


def dimensions(path: Path) -> tuple[int | None, int | None]:
    """读取常见原图尺寸；不解码执行 SVG，不安装图像处理库。"""
    with path.open("rb") as stream:
        head = stream.read(32)
        if head.startswith(b"\x89PNG\r\n\x1a\n") and len(head) >= 24:
            return struct.unpack(">II", head[16:24])
        if head.startswith((b"GIF87a", b"GIF89a")) and len(head) >= 10:
            return struct.unpack("<HH", head[6:10])
        if head.startswith(b"\xff\xd8"):
            stream.seek(2)
            while True:
                marker = stream.read(1)
                if not marker:
                    break
                if marker != b"\xff":
                    continue
                kind = stream.read(1)
                while kind == b"\xff":
                    kind = stream.read(1)
                if not kind or kind in {b"\xd9", b"\xda"}:
                    break
                if kind in {b"\x00", b"\x01"} or 0xd0 <= kind[0] <= 0xd7:
                    continue
                size_bytes = stream.read(2)
                if len(size_bytes) != 2:
                    break
                size = struct.unpack(">H", size_bytes)[0]
                if size < 2:
                    break
                if kind[0] in {0xc0, 0xc1, 0xc2, 0xc3, 0xc5, 0xc6, 0xc7, 0xc9, 0xca, 0xcb, 0xcd, 0xce, 0xcf}:
                    frame = stream.read(5)
                    if len(frame) == 5:
                        height, width = struct.unpack(">HH", frame[1:])
                        return width, height
                    break
                stream.seek(size - 2, 1)
    if path.suffix.lower() == ".svg":
        try:
            element = ET.fromstring(path.read_text(encoding="utf-8"))
            width, height = element.get("width", ""), element.get("height", "")
            if re.fullmatch(r"\d+(?:\.\d+)?(?:px)?", width) and re.fullmatch(r"\d+(?:\.\d+)?(?:px)?", height):
                return round(float(width.removesuffix("px"))), round(float(height.removesuffix("px")))
            box = re.split(r"[ ,]+", element.get("viewBox", "").strip())
            if len(box) == 4:
                return round(float(box[2])), round(float(box[3]))
        except (ValueError, ET.ParseError):
            pass
    return None, None


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def register(root: Path, specification: dict) -> dict:
    root = _artifact_root(root)
    assets = specification.get("assets")
    if not isinstance(assets, list) or not assets:
        raise ValueError("输入必须包含非空 assets 数组")
    result, ids, paths = [], set(), set()
    for item in assets:
        identifier = item.get("id")
        if not isinstance(identifier, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", identifier) or identifier in ids:
            raise ValueError(f"素材 ID 无效或重复：{identifier}")
        ids.add(identifier)
        relative = item.get("path")
        path = local_file(root, relative)
        normalized = path.relative_to(root).as_posix()
        if normalized in paths:
            raise ValueError(f"素材路径重复：{relative}")
        paths.add(normalized)
        role = item.get("role", "original")
        if role not in {"original", "derived"}:
            raise ValueError(f"role 必须是 original 或 derived：{identifier}")
        source_url = item.get("source_url")
        if source_url is not None:
            if not isinstance(source_url, str):
                raise ValueError(f"source_url 必须是字符串：{identifier}")
            parsed = urlsplit(source_url)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
                raise ValueError(f"来源 URL 必须是无凭据 HTTP(S) 地址：{identifier}")
        source = item.get("source", "")
        if not isinstance(source, str) or not (source.strip() or source_url):
            raise ValueError(f"必须声明 source 说明或 source_url：{identifier}")
        derived_from = item.get("derived_from")
        transformation = item.get("transformation", "none" if role == "original" else "")
        if not isinstance(item.get("usage_rights", "待确认"), str) or not isinstance(item.get("caption", ""), str):
            raise ValueError(f"usage_rights/caption 必须为字符串：{identifier}")
        if not isinstance(transformation, str) or not transformation.strip():
            raise ValueError(f"必须声明转换操作：{identifier}")
        if role == "original" and (derived_from is not None or transformation != "none"):
            raise ValueError(f"原始素材不能声明衍生或转换：{identifier}")
        width, height = dimensions(path)
        result.append({"id": identifier, "path": normalized, "role": role, "source": source, "source_url": source_url,
                       "derived_from": derived_from, "transformation": transformation,
                       "usage_rights": item.get("usage_rights", "待确认"), "caption": item.get("caption", ""),
                       "sha256": digest(path), "bytes": path.stat().st_size,
                       "content_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream", "width": width, "height": height})
    mapping = {item["id"]: item for item in result}
    for item in result:
        if item["role"] == "derived":
            parent = item["derived_from"]
            if not isinstance(parent, str) or parent not in mapping or parent == item["id"]:
                raise ValueError(f"衍生素材必须引用已登记的另一素材：{item['id']}")
            visited = {item["id"]}
            while parent:
                if parent in visited:
                    raise ValueError(f"素材衍生链存在循环：{item['id']}")
                visited.add(parent)
                parent = mapping[parent]["derived_from"]
    return {"schema_version": 1, "tool": "html.source-assets", "assets": result}


def validate(root: Path, record: dict) -> dict:
    errors = []
    if record.get("schema_version") != 1 or record.get("tool") != "html.source-assets":
        return {"status": "fail", "errors": ["不是 source-assets v1 记录"], "checked": 0}
    try:
        root = _artifact_root(root)
        actual = register(root, record)
        for old, new in zip(record["assets"], actual["assets"]):
            for key in ("path", "sha256", "bytes", "content_type", "width", "height"):
                if old.get(key) != new[key]:
                    errors.append(f"{old['id']} 的 {key} 与当前文件不一致")
    except (OSError, ValueError, TypeError, AttributeError, KeyError) as exc:
        errors.append(str(exc))
    return {"status": "fail" if errors else "pass", "errors": errors, "checked": len(record.get("assets", []))}


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("register", "validate"))
    parser.add_argument("--root", required=True, type=Path, help="素材所在产物目录")
    parser.add_argument("--input", required=True, type=Path, help="登记规格或已有记录 JSON")
    parser.add_argument("--output", default="source-assets.json", help="产物内的新登记文件相对路径")
    parser.add_argument("--apply", action="store_true", help="登记时明确创建文件；默认只预览")
    parser.add_argument("--expect-plan-sha256", help="应用时校验预览摘要")
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve(strict=True)
        if not root.is_dir():
            raise ValueError("--root 必须是目录")
        source = json.loads(args.input.read_text(encoding="utf-8"))
        if args.action == "validate":
            if args.apply:
                raise ValueError("validate 是只读命令，不接受 --apply")
            result = validate(root, source)
        else:
            record = register(root, source)
            target = root / args.output
            if Path(args.output).is_absolute() or not target.resolve().is_relative_to(root) or target.exists() or target.is_symlink():
                raise ValueError("输出必须是产物目录内不存在的文件；拒绝越界或覆盖")
            if not target.parent.is_dir():
                raise ValueError("输出父目录不存在")
            serialized = (json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            plan = hashlib.sha256(serialized + b"\0" + args.output.encode("utf-8")).hexdigest()
            if args.expect_plan_sha256 and args.expect_plan_sha256 != plan:
                raise ValueError("登记计划已变化，请重新预览")
            if args.apply and not args.expect_plan_sha256:
                raise ValueError("--apply 必须携带预览的 --expect-plan-sha256")
            if args.apply:
                with target.open("xb") as stream:
                    stream.write(serialized)
            result = {"status": "pass", "written": args.apply, "plan_sha256": plan, "record": record}
    except (OSError, ValueError, TypeError, AttributeError, KeyError, struct.error) as exc:
        print(json.dumps({"status": "fail", "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
