"""对自包含 HTML 做静态资源和多视口响应式检查。"""

from __future__ import annotations

import argparse
import hashlib
from html.parser import HTMLParser
import http.server
import json
from pathlib import Path
import re
import socketserver
import sys
import threading
from urllib.parse import quote


DEFAULT_VIEWPORTS = (
    ("narrow-portrait", 390, 844, "screen"),
    ("tablet", 768, 1024, "screen"),
    ("desktop", 1366, 768, "screen"),
    ("wide-landscape", 1920, 1080, "screen"),
    ("print-a4", 794, 1123, "print"),
)
REMOTE_RE = re.compile(r"(?:https?:)?//|data:", re.IGNORECASE)


class ReferenceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.references: list[str] = []
        self.viewport_meta = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = dict(attrs)
        if tag.lower() == "meta" and data.get("name", "").lower() == "viewport":
            self.viewport_meta = True
        for key in ("href", "src", "poster"):
            value = data.get(key)
            if value:
                self.references.append(value)


def parse_viewport(value: str) -> tuple[str, int, int, str]:
    if "=" in value:
        name, dimensions = value.split("=", 1)
    else:
        name, dimensions = value, value
    if "x" not in dimensions.lower():
        raise argparse.ArgumentTypeError("视口必须是 name=widthxheight 或 widthxheight")
    width_text, height_text = re.split("x", dimensions, maxsplit=1, flags=re.IGNORECASE)
    try:
        width, height = int(width_text), int(height_text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("视口宽高必须是整数") from exc
    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError("视口宽高必须大于零")
    media = "print" if name.lower() in {"a4", "print-a4", "print"} else "screen"
    return name, width, height, media


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def static_check(html_path: Path) -> dict[str, object]:
    parser = ReferenceParser()
    text = html_path.read_text(encoding="utf-8")
    parser.feed(text)
    errors: list[str] = []
    warnings: list[str] = []
    if not parser.viewport_meta:
        errors.append("缺少 name=viewport 的 meta 标签")
    for reference in parser.references:
        if REMOTE_RE.search(reference):
            errors.append(f"发现远程或 data 运行时资源：{reference}")
            continue
        if reference.startswith("#") or reference.startswith("mailto:"):
            continue
        target = (html_path.parent / reference.split("#", 1)[0].split("?", 1)[0]).resolve()
        try:
            target.relative_to(html_path.parent.resolve())
        except ValueError:
            errors.append(f"资源路径越出 HTML 目录：{reference}")
            continue
        if not target.is_file():
            errors.append(f"资源文件不存在：{reference}")
    for css in html_path.parent.rglob("*.css"):
        css_text = css.read_text(encoding="utf-8")
        for raw in re.findall(r"url\(\s*['\"]?([^)'\"]+)", css_text, flags=re.IGNORECASE):
            if REMOTE_RE.search(raw) or raw.startswith("#"):
                continue
            target = (css.parent / raw.split("?", 1)[0]).resolve()
            if not target.is_file():
                errors.append(f"CSS 资源文件不存在：{css.relative_to(html_path.parent)} -> {raw}")
    if not re.search(r"<html\b", text, flags=re.IGNORECASE):
        warnings.append("页面没有显式 html 根标签")
    return {
        "status": "fail" if errors else "pass",
        "errors": errors,
        "warnings": warnings,
        "viewport_meta": parser.viewport_meta,
        "references": len(parser.references),
    }


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return


class LocalServer:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.server: socketserver.TCPServer | None = None
        self.thread: threading.Thread | None = None

    def __enter__(self) -> "LocalServer":
        handler = lambda *args, **kwargs: QuietHandler(*args, directory=str(self.root), **kwargs)
        self.server = socketserver.TCPServer(("127.0.0.1", 0), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    @property
    def url(self) -> str:
        assert self.server is not None
        return f"http://127.0.0.1:{self.server.server_address[1]}"

    def __exit__(self, *args: object) -> None:
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        if self.thread:
            self.thread.join(timeout=2)


def browser_check(html_path: Path, viewports: list[tuple[str, int, int, str]], screenshot_dir: Path | None) -> dict[str, object]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"status": "not-run", "reason": "未安装 Python Playwright，未执行浏览器视口检查", "viewports": []}
    results: list[dict[str, object]] = []
    try:
        with LocalServer(html_path.parent) as server, sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                relative = quote(html_path.relative_to(html_path.parent).as_posix())
                for name, width, height, media in viewports:
                    page.set_viewport_size({"width": width, "height": height})
                    page.emulate_media(media=media)
                    page.goto(f"{server.url}/{relative}", wait_until="networkidle")
                    metrics = page.evaluate("""() => ({
                      innerWidth: window.innerWidth,
                      scrollWidth: document.documentElement.scrollWidth,
                      innerHeight: window.innerHeight,
                      scrollHeight: document.documentElement.scrollHeight,
                      horizontalOverflow: document.documentElement.scrollWidth > window.innerWidth + 1
                    })""")
                    item: dict[str, object] = {"id": name, "width": width, "height": height, "media": media, "status": "fail" if metrics["horizontalOverflow"] else "pass", "metrics": metrics}
                    if screenshot_dir:
                        screenshot_dir.mkdir(parents=True, exist_ok=True)
                        target = screenshot_dir / f"{name}.png"
                        page.screenshot(path=str(target), full_page=True)
                        item["screenshot"] = str(target)
                    results.append(item)
            finally:
                browser.close()
    except Exception as exc:  # browser absence, launch failure, or page failure is explicit
        return {"status": "not-run", "reason": f"浏览器检查未执行：{type(exc).__name__}: {exc}", "viewports": results}
    return {"status": "fail" if any(item["status"] == "fail" for item in results) else "pass", "viewports": results}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="检查自包含 HTML 的本地资源和多视口响应式行为")
    parser.add_argument("--html", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--viewport", action="append", type=parse_viewport)
    parser.add_argument("--screenshot-dir", type=Path)
    parser.add_argument("--fail-on-overflow", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    # JSON 是跨进程协议，不能依赖 Windows 控制台的系统代码页输出中文。
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    args = build_parser().parse_args(argv)
    html_path = args.html.resolve()
    if not html_path.is_file() or html_path.suffix.lower() != ".html":
        print(json.dumps({"status": "fail", "error": f"HTML 文件不存在或扩展名不正确：{html_path}"}, ensure_ascii=False))
        return 2
    viewports = args.viewport or list(DEFAULT_VIEWPORTS)
    static = static_check(html_path)
    browser = browser_check(html_path, viewports, args.screenshot_dir)
    result = {"schema_version": 1, "tool": "html.viewport-check", "html": str(html_path), "html_sha256": sha256(html_path), "viewports": [{"id": n, "width": w, "height": h, "media": m} for n, w, h, m in viewports], "static": static, "browser": browser, "status": "fail" if static["status"] == "fail" or (args.fail_on_overflow and browser["status"] == "fail") else "pass"}
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 1 if result["status"] == "fail" else 0


if __name__ == "__main__":
    sys.exit(main())
