"""HTML 工具的公共本机浏览器会话，不依赖测试模块或额外 pip 包。

CDP 传输、受限静态服务器及浏览器发现复用 PDF 工具已有实现；上层检查器
只依赖本模块。暂不搬动 PDF 的导出代码，避免为新增检查改变已验收导出行为。
"""
from __future__ import annotations

import base64
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import time
from typing import Any

_spec = importlib.util.spec_from_file_location("_suanhai_pdf_browser", Path(__file__).parent / "pdf-export/export_pdf.py")
assert _spec and _spec.loader
_pdf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_pdf)

LocalArtifactServer = _pdf.LocalArtifactServer


class BrowserUnavailable(RuntimeError):
    """浏览器缺失或无法启动；调用方应报告 not-run。"""


def find_browser(explicit: str | None = None) -> str | None:
    return _pdf._find_browser(explicit)


class ChromiumSession:
    """只启动独立临时 profile，不连接用户正在使用的浏览器或修改系统配置。"""

    def __init__(self, browser: str | None = None, timeout: float = 30):
        self.browser = find_browser(browser)
        self.timeout = timeout
        self.cdp = None
        self.process = None
        self.temporary = None
        self.version = None

    def __enter__(self) -> "ChromiumSession":
        if not self.browser:
            raise BrowserUnavailable("未发现本机 Chrome、Edge 或 Chromium")
        self.temporary = tempfile.TemporaryDirectory(prefix="suanhai-html-check-", ignore_cleanup_errors=True)
        profile = Path(self.temporary.name) / "profile"
        profile.mkdir()
        command = [self.browser, "--headless=new", "--disable-gpu", "--disable-dev-shm-usage",
                   "--disable-background-networking", "--disable-extensions", "--disable-sync",
                   "--disable-crash-reporter", "--no-first-run", "--no-default-browser-check",
                   "--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE localhost, EXCLUDE 127.0.0.1",
                   "--remote-debugging-address=127.0.0.1", "--remote-debugging-port=0",
                   f"--user-data-dir={profile}", "about:blank"]
        try:
            self.process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            active_port = profile / "DevToolsActivePort"
            deadline = time.monotonic() + min(self.timeout, 20)
            port = None
            while time.monotonic() < deadline:
                try:
                    lines = active_port.read_text(encoding="ascii").splitlines()
                    if lines and lines[0].isdigit():
                        port = int(lines[0])
                        break
                except (OSError, UnicodeError):
                    pass
                time.sleep(.1)
            if port is None:
                raise BrowserUnavailable("浏览器未在时限内启动 DevTools")
            self.version = _pdf._http_json(f"http://127.0.0.1:{port}/json/version").get("Browser")
            targets = _pdf._http_json(f"http://127.0.0.1:{port}/json/list")
            target = next(item for item in targets if item.get("type") == "page")
            self.cdp = _pdf.CDP(target["webSocketDebuggerUrl"], timeout=self.timeout)
            self.cdp.call("Page.enable")
            self.cdp.call("Runtime.enable")
            return self
        except Exception as exc:
            self.__exit__()
            raise BrowserUnavailable(f"浏览器启动失败：{type(exc).__name__}: {exc}") from exc

    def evaluate(self, expression: str) -> Any:
        result = self.cdp.call("Runtime.evaluate", {"expression": expression, "awaitPromise": True, "returnByValue": True})
        if result.get("exceptionDetails"):
            raise RuntimeError(f"页面检查脚本失败：{result['exceptionDetails']}")
        return result.get("result", {}).get("value")

    def navigate(self, url: str) -> None:
        self.cdp.call("Page.navigate", {"url": url})
        self.cdp.wait_event("Page.loadEventFired", timeout=self.timeout)
        self.evaluate("Promise.all([document.fonts ? document.fonts.ready : Promise.resolve(), ...Array.from(document.images).map(i => i.complete ? Promise.resolve() : new Promise(r => { i.addEventListener('load', r, {once:true}); i.addEventListener('error', r, {once:true}); setTimeout(r, 3000); }))]).then(() => true)")

    def viewport(self, width: int, height: int, media: str) -> None:
        self.cdp.call("Emulation.setDeviceMetricsOverride", {"width": width, "height": height, "deviceScaleFactor": 1, "mobile": False})
        self.cdp.call("Emulation.setEmulatedMedia", {"media": media})

    def screenshot(self, path: Path) -> None:
        result = self.cdp.call("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})
        path.write_bytes(base64.b64decode(result["data"]))

    def key(self, key: str) -> None:
        for event_type in ("keyDown", "keyUp"):
            self.cdp.call("Input.dispatchKeyEvent", {"type": event_type, "key": key, "code": key})

    def __exit__(self, *_exc: Any) -> None:
        if self.cdp:
            try:
                self.cdp.call("Browser.close")
            except Exception:
                pass
            self.cdp.close()
            self.cdp = None
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        if self.temporary:
            self.temporary.cleanup()
