#!/usr/bin/env python3
"""安全增补资产字节保护规则；不重写历史文件，不执行 Git 归一化。"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile


BEGIN = "# BEGIN suanhai-asset-bytes:v1"
END = "# END suanhai-asset-bytes:v1"


def is_link(path: Path) -> bool:
    return path.is_symlink() or bool(getattr(path.lstat(), "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def plan(root: Path, output_roots: list[str]) -> tuple[bytes | None, bytes, str]:
    """保留用户规则原文；用 git check-attr 验证最终效果，遇到冲突不抢覆盖权。"""
    result = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"], capture_output=True, text=True, encoding="utf-8")
    if result.returncode or Path(result.stdout.strip()).resolve() != root:
        raise ValueError("--root 必须是消费端 Git 仓库根目录")
    names = sorted(set(output_roots or ["reports", "courses", "series", "books", "tasks"]))
    if any(not re.fullmatch(r"[a-z][a-z0-9_-]*", name) or name in {"vendor", "context"} for name in names):
        raise ValueError("输出根必须是安全的顶层目录名，不能包含路径或受保护目录")
    path = root / ".gitattributes"
    if path.is_symlink() or (path.exists() and (is_link(path) or not path.is_file())):
        raise ValueError(".gitattributes 不能是符号链接、junction 或目录")
    original = path.read_bytes() if path.exists() else None
    text = (original or b"").decode("utf-8-sig")
    newline = "\r\n" if "\r\n" in text else "\n"
    block = newline.join([BEGIN, "# 已登记来源和作品按原始字节保存，避免换行转换改变评审摘要。", *[f"{name}/** -text" for name in names], END])
    if BEGIN in text or END in text:
        if text.count(BEGIN) != 1 or text.count(END) != 1:
            raise ValueError("资产保护标记重复或不成对")
        start, end = text.index(BEGIN), text.index(END) + len(END)
        if end < start or text[start:end] != block:
            raise ValueError("已有保护段与计划不同；请人工合并，不覆盖用户规则")
        updated = original or b""
    else:
        separator = b"" if not original else (newline if text.endswith(("\n", "\r")) else newline * 2).encode("utf-8")
        updated = (original or b"") + separator + (block + newline).encode("utf-8")
    digest = hashlib.sha256(json.dumps({"root": str(root), "before": hashlib.sha256(original).hexdigest() if original is not None else None, "after": hashlib.sha256(updated).hexdigest()}, sort_keys=True).encode()).hexdigest()
    return original, updated, digest


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--output-root", action="append", default=[])
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--expect-plan-sha256")
    args = parser.parse_args()
    temporary = None
    try:
        root = Path(args.root).resolve(strict=True)
        original, updated, digest = plan(root, args.output_root)
        if args.apply and args.expect_plan_sha256 != digest:
            raise ValueError("应用必须匹配 dry-run 的计划摘要")
        path = root / ".gitattributes"
        if args.apply and original != updated:
            with tempfile.NamedTemporaryFile(dir=root, prefix=".asset-bytes-", delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(updated)
            if (path.exists() and (is_link(path) or path.read_bytes() != original)) or (not path.exists() and original is not None):
                raise ValueError("预览后 .gitattributes 已变化，未写入")
            os.replace(temporary, path)
            temporary = None
        print(json.dumps({"ok": True, "mode": "apply" if args.apply else "dry-run", "plan_sha256": digest, "would_write": original != updated, "written": args.apply and original != updated, "planned_text": updated.decode("utf-8-sig"), "note": "只增补规则，不执行 git add --renormalize，不改变历史字节；嵌套规则请用 git check-attr 复核。"}, ensure_ascii=False, indent=2))
        return 0
    except (OSError, UnicodeError, ValueError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False))
        return 1
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
