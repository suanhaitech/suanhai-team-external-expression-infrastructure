#!/usr/bin/env python3
"""将消费端的自包含 HTML 页面导出为 PDF。仅依赖 Python 标准库和本机 Chromium。"""

from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import http.server
import json
import mimetypes
import os
from pathlib import Path
import random
import shutil
import socket
import socketserver
import struct
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any
from urllib.parse import quote, unquote, urlsplit
import urllib.error
import urllib.request


PAPER_SIZES_INCHES = {
    "a4": (8.2677165354, 11.6929133858),
    "letter": (8.5, 11.0),
    "legal": (8.5, 14.0),
}
WEBSOCKET_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


class ExportError(Exception):
    """输入无效、浏览器失败或 PDF 生成失败等可报告错误。"""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _inside(root: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


def _safe_file(root: Path, relative: str, *, must_exist: bool) -> Path:
    """将用户给出的相对路径限制在产物目录内，并拒绝符号链接逃逸。"""
    rel = Path(relative)
    if rel.is_absolute() or not rel.parts or any(part in {".", ".."} for part in rel.parts):
        raise ExportError(f"路径必须是产物目录内的安全相对路径：{relative}")
    candidate = root.joinpath(rel)
    resolved = candidate.resolve(strict=must_exist)
    if not _inside(root, resolved):
        raise ExportError(f"路径越出 HTML 产物目录：{relative}")
    if must_exist and not resolved.is_file():
        raise ExportError(f"输入文件不存在或不是普通文件：{relative}")
    if not must_exist:
        parent = candidate.parent.resolve(strict=True)
        if not _inside(root, parent):
            raise ExportError(f"输出目录越出 HTML 产物目录：{relative}")
        if candidate.exists() or candidate.is_symlink():
            raise ExportError(f"拒绝覆盖已有输出：{relative}")
    return resolved if must_exist else candidate


def _find_browser(explicit: str | None) -> str | None:
    candidates: list[str] = []
    if explicit:
        candidates.append(explicit)
    else:
        for name in ("msedge", "msedge.exe", "chrome", "chrome.exe", "chromium", "chromium-browser", "google-chrome"):
            found = shutil.which(name)
            if found:
                candidates.append(found)
        if os.name == "nt":
            roots = [os.environ.get("PROGRAMFILES"), os.environ.get("PROGRAMFILES(X86)"), os.environ.get("LOCALAPPDATA")]
            suffixes = (
                "Microsoft/Edge/Application/msedge.exe",
                "Google/Chrome/Application/chrome.exe",
                "Chromium/Application/chrome.exe",
            )
            for root in roots:
                if root:
                    candidates.extend(str(Path(root) / suffix) for suffix in suffixes)
    for item in candidates:
        path = shutil.which(item) if not Path(item).is_file() else item
        if path and Path(path).is_file():
            return str(Path(path).resolve())
    return None


def _read_exact(sock: socket.socket, size: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < size:
        part = sock.recv(size - len(chunks))
        if not part:
            raise ExportError("浏览器 DevTools WebSocket 已关闭")
        chunks.extend(part)
    return bytes(chunks)


class DevToolsSocket:
    """标准库实现的最小 CDP WebSocket 客户端，避免依赖额外 pip 包。"""

    def __init__(self, websocket_url: str, timeout: float = 30.0):
        parsed = urlsplit(websocket_url)
        if parsed.scheme != "ws" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ExportError("拒绝连接非本机 DevTools WebSocket")
        port = parsed.port or 80
        self.sock = socket.create_connection((parsed.hostname, port), timeout=timeout)
        self.sock.settimeout(timeout)
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        host = f"{parsed.hostname}:{port}"
        request = (
            f"GET {path} HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\n"
            f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(request.encode("ascii"))
        response = bytearray()
        while not response.endswith(b"\r\n\r\n"):
            chunk = self.sock.recv(1)
            if not chunk:
                self.sock.close()
                raise ExportError("DevTools WebSocket 握手未完成")
            response.extend(chunk)
            if len(response) > 16384:
                self.sock.close()
                raise ExportError("DevTools WebSocket 握手响应过大")
        lines = response.decode("latin1").split("\r\n")
        if " 101 " not in lines[0]:
            self.sock.close()
            raise ExportError(f"DevTools WebSocket 握手失败：{lines[0]}")
        headers = {}
        for line in lines[1:]:
            if ":" in line:
                name, value = line.split(":", 1)
                headers[name.strip().lower()] = value.strip()
        expected = base64.b64encode(__import__("hashlib").sha1((key + WEBSOCKET_GUID).encode("ascii")).digest()).decode("ascii")
        if headers.get("sec-websocket-accept") != expected:
            self.sock.close()
            raise ExportError("DevTools WebSocket 握手校验失败")

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass

    def _send_frame(self, opcode: int, payload: bytes) -> None:
        mask = os.urandom(4)
        length = len(payload)
        header = bytearray([0x80 | opcode])
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack("!Q", length))
        header.extend(mask)
        masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        self.sock.sendall(header + masked)

    def send_json(self, value: dict[str, Any]) -> None:
        self._send_frame(1, json.dumps(value, separators=(",", ":")).encode("utf-8"))

    def receive_json(self) -> dict[str, Any]:
        fragments = bytearray()
        message_opcode = None
        while True:
            first, second = _read_exact(self.sock, 2)
            fin = bool(first & 0x80)
            opcode = first & 0x0F
            masked = bool(second & 0x80)
            length = second & 0x7F
            if length == 126:
                length = struct.unpack("!H", _read_exact(self.sock, 2))[0]
            elif length == 127:
                length = struct.unpack("!Q", _read_exact(self.sock, 8))[0]
            mask = _read_exact(self.sock, 4) if masked else b""
            payload = _read_exact(self.sock, length) if length else b""
            if masked:
                payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
            if opcode == 8:
                raise ExportError("浏览器关闭了 DevTools WebSocket")
            if opcode == 9:
                self._send_frame(10, payload)
                continue
            if opcode == 10:
                continue
            if opcode in (1, 2):
                message_opcode = opcode
                fragments.extend(payload)
            elif opcode == 0:
                fragments.extend(payload)
            if fin:
                if message_opcode != 1:
                    raise ExportError("DevTools 返回了非文本 WebSocket 消息")
                try:
                    return json.loads(fragments.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise ExportError("DevTools 返回了无效 JSON") from exc


class CDP:
    def __init__(self, websocket_url: str, timeout: float = 30.0):
        self.ws = DevToolsSocket(websocket_url, timeout=timeout)
        self.timeout = timeout
        self.next_id = 0
        self.events: list[dict[str, Any]] = []

    def close(self) -> None:
        self.ws.close()

    def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self.next_id += 1
        request_id = self.next_id
        self.ws.send_json({"id": request_id, "method": method, "params": params or {}})
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            message = self.ws.receive_json()
            if message.get("id") == request_id:
                if "error" in message:
                    raise ExportError(f"DevTools {method} 失败：{message['error']}")
                return message.get("result", {})
            if "method" in message:
                self.events.append(message)
        raise ExportError(f"等待 DevTools {method} 超时")

    def wait_event(self, method: str, timeout: float) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for index, event in enumerate(self.events):
                if event.get("method") == method:
                    return self.events.pop(index)
            self.ws.sock.settimeout(max(0.1, deadline - time.monotonic()))
            message = self.ws.receive_json()
            if message.get("method") == method:
                return message
            if "method" in message:
                self.events.append(message)
        raise ExportError(f"等待浏览器事件 {method} 超时")


class LocalArtifactServer:
    """只暴露指定产物目录中的普通文件，并限制在 loopback 接口。"""

    def __init__(self, root: Path):
        self.root = root.resolve(strict=True)

        class Handler(http.server.BaseHTTPRequestHandler):
            server_version = "SuanhaiLocalArtifact/1"

            def log_message(self, _format: str, *_args: Any) -> None:
                return

            def do_HEAD(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
                self._serve(send_body=False)

            def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
                self._serve(send_body=True)

            def _serve(self, send_body: bool) -> None:
                raw_path = unquote(urlsplit(self.path).path).lstrip("/")
                if not raw_path:
                    raw_path = "index.html"
                try:
                    target = (self.server.artifact_root / raw_path).resolve(strict=True)  # type: ignore[attr-defined]
                except (FileNotFoundError, OSError):
                    self.send_error(404)
                    return
                if not _inside(self.server.artifact_root, target) or not target.is_file():  # type: ignore[attr-defined]
                    self.send_error(404)
                    return
                try:
                    content = target.read_bytes()
                except OSError:
                    self.send_error(404)
                    return
                content_type, encoding = mimetypes.guess_type(target.name)
                if content_type is None:
                    content_type = "application/octet-stream"
                if encoding:
                    content_type += f"; charset={encoding}"
                elif content_type.startswith("text/") or content_type in {"application/javascript", "image/svg+xml"}:
                    content_type += "; charset=utf-8"
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                if send_body:
                    self.wfile.write(content)

        class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
            daemon_threads = True
            allow_reuse_address = True

        self.server = Server(("127.0.0.1", 0), Handler)
        self.server.artifact_root = self.root  # type: ignore[attr-defined]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self) -> str:
        self.thread.start()
        return f"http://127.0.0.1:{self.server.server_port}"

    def __exit__(self, *_exc: Any) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


def _http_json(url: str, timeout: float = 1.0) -> Any:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _read_stream(cdp: CDP, stream_handle: str) -> bytes:
    chunks: list[bytes] = []
    while True:
        result = cdp.call("IO.read", {"handle": stream_handle, "size": 1024 * 1024})
        if result.get("data"):
            chunks.append(base64.b64decode(result["data"]) if result.get("base64Encoded") else result["data"].encode("utf-8"))
        if result.get("eof"):
            break
    cdp.call("IO.close", {"handle": stream_handle})
    return b"".join(chunks)


def _print_pdf(
    browser: str,
    page_url: str,
    *,
    paper: str,
    landscape: bool,
    margin_mm: float,
    scale: float,
    print_background: bool,
    prefer_css_page_size: bool,
    timeout: float,
) -> tuple[bytes, str]:
    # Chrome 的 Crashpad 目录可能在进程退出后仍短暂持有文件句柄；允许临时目录
    # 延迟清理，避免一次成功的导出因为 Windows 文件锁被报告为失败。
    with tempfile.TemporaryDirectory(prefix="suanhai-html-pdf-", ignore_cleanup_errors=True) as temp_name:
        profile = Path(temp_name) / "profile"
        active_port = profile / "DevToolsActivePort"
        profile.mkdir()
        command = [
            browser,
            "--headless=new",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--disable-background-networking",
            "--disable-extensions",
            "--disable-sync",
            "--disable-crash-reporter",
            "--no-first-run",
            "--no-default-browser-check",
            "--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE localhost, EXCLUDE 127.0.0.1",
            "--remote-debugging-address=127.0.0.1",
            "--remote-debugging-port=0",
            f"--user-data-dir={profile}",
            "about:blank",
        ]
        try:
            process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError as exc:
            raise ExportError(f"无法启动浏览器：{exc}") from exc
        cdp: CDP | None = None
        try:
            deadline = time.monotonic() + min(timeout, 20.0)
            port = None
            while time.monotonic() < deadline:
                if active_port.is_file():
                    try:
                        lines = active_port.read_text(encoding="ascii", errors="replace").splitlines()
                    except PermissionError:
                        # Windows 浏览器刚创建端口文件时可能仍持有独占句柄；
                        # 这属于启动竞态，继续轮询比直接把导出判为失败更准确。
                        lines = []
                    if lines and lines[0].isdigit():
                        port = int(lines[0])
                        break
                # Windows Edge 可能先退出兼容层启动器，再由子进程继续提供 DevTools。
                # 因此不能把父进程退出码 0 当作浏览器启动失败；只以 DevTools
                # 端口是否在时限内出现作为启动判据。
                if process.poll() is not None and not active_port.exists():
                    time.sleep(0.1)
                    continue
                time.sleep(0.1)
            if port is None:
                raise ExportError("浏览器未在时限内启动 DevTools")
            version = _http_json(f"http://127.0.0.1:{port}/json/version")
            targets = _http_json(f"http://127.0.0.1:{port}/json/list")
            target = next((item for item in targets if item.get("type") == "page"), None)
            if not target:
                raise ExportError("浏览器没有创建可用页面目标")
            cdp = CDP(target["webSocketDebuggerUrl"], timeout=timeout)
            cdp.call("Page.enable")
            cdp.call("Runtime.enable")
            cdp.call("Page.navigate", {"url": page_url})
            cdp.wait_event("Page.loadEventFired", timeout=min(timeout, 45.0))
            cdp.call(
                "Runtime.evaluate",
                {
                    "expression": "document.fonts ? document.fonts.ready.then(() => true) : Promise.resolve(true)",
                    "awaitPromise": True,
                    "returnByValue": True,
                },
            )
            width, height = PAPER_SIZES_INCHES[paper]
            if landscape:
                width, height = height, width
            margin_inches = margin_mm / 25.4
            result = cdp.call(
                "Page.printToPDF",
                {
                    "landscape": landscape,
                    "displayHeaderFooter": False,
                    "printBackground": print_background,
                    "scale": scale,
                    "paperWidth": width,
                    "paperHeight": height,
                    "marginTop": margin_inches,
                    "marginBottom": margin_inches,
                    "marginLeft": margin_inches,
                    "marginRight": margin_inches,
                    # 默认让 CLI 的 --paper 成为明确的输出契约；只有用户显式
                    # 选择 --prefer-css-page-size 时，页面内的 @page size 才覆盖它。
                    "preferCSSPageSize": prefer_css_page_size,
                    "transferMode": "ReturnAsStream",
                },
            )
            if result.get("stream"):
                pdf = _read_stream(cdp, result["stream"])
            elif result.get("data"):
                pdf = base64.b64decode(result["data"])
            else:
                raise ExportError("浏览器没有返回 PDF 数据")
            return pdf, str(version.get("Browser", "unknown"))
        except (urllib.error.URLError, TimeoutError, socket.timeout, OSError) as exc:
            if isinstance(exc, ExportError):
                raise
            raise ExportError(f"浏览器通信失败：{exc}") from exc
        finally:
            if cdp:
                try:
                    # 通过 DevTools 关闭浏览器进程树，避免 Windows 临时 profile 被
                    # Crashpad 子进程锁住，导致 TemporaryDirectory 清理失败。
                    cdp.call("Browser.close")
                except Exception:
                    pass
                cdp.close()
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


def _write_new_file(path: Path, content: bytes) -> None:
    """独占创建输出，避免静默覆盖用户已有 PDF 或审计记录。"""
    try:
        with path.open("xb") as stream:
            stream.write(content)
    except FileExistsError as exc:
        raise ExportError(f"拒绝覆盖已有文件：{path.name}") from exc
    except OSError as exc:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        raise ExportError(f"写入输出失败：{exc}") from exc


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="将消费端自包含 HTML 页面导出为 PDF")
    parser.add_argument("--root", required=True, help="HTML 产物目录，必须包含输入 HTML")
    parser.add_argument("--input", default="index.html", help="产物目录内的入口 HTML 相对路径，默认 index.html")
    parser.add_argument("--output", default="report.pdf", help="产物目录内的新 PDF 相对路径，默认 report.pdf")
    parser.add_argument("--browser", help="Chrome/Edge/Chromium 可执行文件路径；默认自动探测")
    parser.add_argument("--paper", choices=sorted(PAPER_SIZES_INCHES), default="a4", help="纸张尺寸，默认 a4")
    parser.add_argument("--landscape", action="store_true", help="横向打印")
    parser.add_argument("--margin-mm", type=float, default=12.0, help="四边统一页边距，单位 mm，默认 12")
    parser.add_argument("--scale", type=float, default=1.0, help="打印缩放比例，范围 0.1 到 2.0")
    parser.add_argument("--no-background", action="store_true", help="不打印背景图形")
    parser.add_argument(
        "--prefer-css-page-size",
        action="store_true",
        help="允许 HTML 的 @page size 覆盖 --paper；默认由 --paper 控制纸张",
    )
    parser.add_argument("--metadata", default="pdf-export.json", help="产物目录内的元数据 JSON 相对路径")
    parser.add_argument("--timeout", type=float, default=60.0, help="浏览器操作超时秒数，默认 60")
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    root_arg = Path(args.root)
    if not root_arg.is_dir():
        raise ExportError(f"HTML 产物目录不存在：{root_arg}")
    root = root_arg.resolve(strict=True)
    source = _safe_file(root, args.input, must_exist=True)
    output = _safe_file(root, args.output, must_exist=False)
    metadata = _safe_file(root, args.metadata, must_exist=False)
    if output == metadata:
        raise ExportError("PDF 输出与元数据路径不能相同")
    if args.margin_mm < 0 or args.margin_mm > 50:
        raise ExportError("页边距必须在 0 到 50 mm 之间")
    if not 0.1 <= args.scale <= 2.0:
        raise ExportError("缩放比例必须在 0.1 到 2.0 之间")
    if args.timeout < 1 or args.timeout > 600:
        raise ExportError("超时必须在 1 到 600 秒之间")
    browser = _find_browser(args.browser)
    html_relative = source.relative_to(root).as_posix()
    record: dict[str, Any] = {
        "schema_version": 1,
        "tool": "html.pdf-export",
        "status": "not-run",
        "created_at": _utc_now(),
        "input": html_relative,
        "output": None,
        "browser": None,
        "settings": {
            "paper": args.paper,
            "landscape": args.landscape,
            "margin_mm": args.margin_mm,
            "scale": args.scale,
            "print_background": not args.no_background,
            "prefer_css_page_size": getattr(args, "prefer_css_page_size", False),
        },
        "sha256": None,
        "bytes": None,
        "reason": None,
    }
    if browser is None:
        record["reason"] = "未检测到可用的 Chrome、Edge 或 Chromium；未安装或配置浏览器，因此未运行导出。"
        _write_new_file(metadata, (json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        return record
    # 浏览器版本由 DevTools 会话返回；不额外执行 --version，避免 Windows
    # 启动器阻塞或按系统代码页输出而影响真正的导出。
    with LocalArtifactServer(root) as origin:
        relative_url = "/".join(quote(part) for part in Path(html_relative).parts)
        page_url = f"{origin}/{relative_url}"
        pdf, browser_identification = _print_pdf(
            browser,
            page_url,
            paper=args.paper,
            landscape=args.landscape,
            margin_mm=args.margin_mm,
            scale=args.scale,
            print_background=not args.no_background,
            prefer_css_page_size=getattr(args, "prefer_css_page_size", False),
            timeout=args.timeout,
        )
    if not pdf.startswith(b"%PDF-"):
        raise ExportError("浏览器输出不是有效 PDF（缺少 PDF 文件头）")
    _write_new_file(output, pdf)
    record.update(
        {
            "status": "completed",
            "output": output.relative_to(root).as_posix(),
            "browser": {"path": browser, "version": browser_identification or "unknown"},
            "sha256": hashlib.sha256(pdf).hexdigest(),
            "bytes": len(pdf),
            "reason": None,
        }
    )
    try:
        _write_new_file(metadata, (json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    except ExportError:
        output.unlink(missing_ok=True)
        raise
    return record


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        result = run(args)
    except (ExportError, OSError, subprocess.SubprocessError, ValueError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
