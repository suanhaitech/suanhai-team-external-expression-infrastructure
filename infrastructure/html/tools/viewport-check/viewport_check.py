"""对自包含 HTML 做静态资源和多视口响应式检查。"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import os
from urllib.parse import quote, unquote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from browser_support import BrowserUnavailable, ChromiumSession, LocalArtifactServer


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
        self.page_ids: list[str | None] = []
        self.stylesheets: list[str] = []
        self.inline_css: list[str] = []
        self.components: list[dict] = []
        self.placeholders: list[str] = []
        self.author_hints = 0
        self._style = False

    def handle_data(self, value):
        if self._style:
            self.inline_css.append(value)
        elif re.search(r"\[[^\]\n]+\]", value):
            self.placeholders.append(value.strip()[:160])

    def handle_endtag(self, tag):
        if tag.lower() == "style":
            self._style = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = dict(attrs)
        self._style = self._style or tag.lower() == "style"
        if data.get("style"):
            self.inline_css.append(data["style"])
        if tag.lower() == "link" and "stylesheet" in data.get("rel", "").lower().split() and data.get("href"):
            self.stylesheets.append(data["href"])
        if data.get("data-component"):
            self.components.append(data)
        if "data-author-hint" in data:
            self.author_hints += 1
        if "data-deck-page" in data:
            self.page_ids.append(data.get("data-page-id") or data.get("id"))
        if tag.lower() == "meta" and data.get("name", "").lower() == "viewport":
            self.viewport_meta = True
        for key in ("href", "src", "poster", "data-source-image"):
            value = data.get(key)
            if value:
                # 文章出处的外部超链接不是自动加载的运行资源；仍核验本地链接。
                if tag.lower() == "a" and key == "href" and re.match(r"https?://", value, re.IGNORECASE):
                    continue
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
    if not re.fullmatch(r"[A-Za-z0-9_-]+", name) or not (0 < width <= 16384 and 0 < height <= 16384):
        raise argparse.ArgumentTypeError("视口名仅限英文字母/数字/下划线/短横线，宽高范围 1–16384")
    media = "print" if name.lower() in {"a4", "print-a4", "print"} else "screen"
    return name, width, height, media


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def static_check(html_path: Path, artifact_kind="template") -> dict[str, object]:
    """沿实际引用收集资源；不把物料化时复制的兼容文件当作运行依赖。

    摘要只覆盖 HTML 显式引用与 CSS url/@import 图，不分析 JS 动态加载。
    路径统一 URL 解码后 resolve，避免 CSS 或编码路径绕过作品目录边界。
    """
    html_path = html_path.resolve()
    root = html_path.parent
    parser = ReferenceParser()
    text = html_path.read_text(encoding="utf-8")
    parser.feed(text)
    errors, warnings = [], []
    files = {html_path}
    visited_css = set()
    if not parser.viewport_meta:
        errors.append("缺少 name=viewport 的 meta 标签")

    def resolve(reference, base):
        if reference.startswith(("#", "mailto:")):
            return None
        parsed = urlsplit(reference)
        if parsed.scheme or parsed.netloc:
            errors.append(f"发现远程或 data 运行时资源：{reference}")
            return None
        target = (base / unquote(parsed.path)).resolve()
        if not target.is_relative_to(root):
            errors.append(f"资源路径越出 HTML 目录：{reference}")
        elif not target.is_file():
            errors.append(f"资源文件不存在：{reference}")
        else:
            files.add(target)
            return target
        return None

    def css_references(content, base):
        # 去掉注释以免把说明示例识别为运行资源；同时覆盖 @import "x.css"。
        content = re.sub(r"/\*.*?\*/", "", content, flags=re.S)
        urls = re.findall(r"url\(\s*['\"]?([^)'\"]+)", content, flags=re.I)
        imports = re.findall(r"@import\s+['\"]([^'\"]+)", content, flags=re.I)
        for reference in urls + imports:
            target = resolve(reference.strip(), base)
            if target and (target.suffix.lower() == ".css" or reference in imports):
                visit_css(target)

    def visit_css(path):
        if path in visited_css:
            return
        visited_css.add(path)
        css_references(path.read_text(encoding="utf-8"), path.parent)

    for reference in parser.references:
        resolve(reference, root)
    for reference in parser.stylesheets:
        target = resolve(reference, root)
        if target:
            visit_css(target)
    for content in parser.inline_css:
        css_references(content, root)
    if not re.search(r"<html\b", text, flags=re.I):
        warnings.append("页面没有显式 html 根标签")
    # 使用现有组件契约中的状态枚举，避免在检查器维护第二套业务状态。
    component_root = Path(__file__).resolve().parents[2] / "components/core-v1/semantic"
    state_contracts = {}
    for contract in (component_root / "contracts").glob("*.json"):
        definition = json.loads(contract.read_text(encoding="utf-8"))
        if definition.get("states"):
            state_contracts[definition["id"]] = definition
    for component in parser.components:
        name, state = component["data-component"], component.get("data-state")
        contract = state_contracts.get(name)
        if contract and (state is not None or "state" in contract["required_slots"]) and state not in contract["states"]:
            errors.append(f"组件状态不在契约枚举中：{name} -> {state}")
    if artifact_kind == "report" and (parser.placeholders or parser.author_hints):
        errors.append("完整报告仍有方括号候选占位或 data-author-hint 编写提示，请人工核对并清理")
    if parser.placeholders:
        warnings.append(f"发现 {len(parser.placeholders)} 处方括号候选占位；模板允许，报告须核对")
    plan_path = root / "page-plan.json"
    if plan_path.exists():
        try:
            document = json.loads(plan_path.read_text(encoding="utf-8"))
            planned = [page["id"] for page in document["pages"]]
            if document.get("schema_version") != 1 or not planned or len(set(planned)) != len(planned) or planned != parser.page_ids:
                errors.append("page-plan 与 HTML 的页面 ID、数量或顺序不一致")
        except (OSError, UnicodeError, ValueError, KeyError, TypeError) as exc:
            errors.append(f"page-plan 无法核对：{exc}")
    resources = [{"path": path.relative_to(root).as_posix(), "sha256": sha256(path)} for path in sorted(files)]
    return {
        "status": "fail" if errors else "pass", "errors": errors, "warnings": warnings,
        "viewport_meta": parser.viewport_meta, "references": len(parser.references),
        "planned_pages": len(parser.page_ids) if plan_path.exists() else None,
        "artifact_kind": artifact_kind, "placeholder_candidates": parser.placeholders,
        "resources": resources,
        "resources_sha256": hashlib.sha256(json.dumps(resources, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest(),
        "resource_scope": "HTML 显式引用与 CSS url/@import；不含 JS 动态依赖和来源真实性验证",
    }


class PlaywrightSession:
    """将 Playwright 与标准库 CDP 后端适配为同一组操作，检查规则只维护一份。"""

    def __enter__(self):
        try:
            from playwright.sync_api import sync_playwright
            self.runtime = sync_playwright().start()
            try:
                self.browser = self.runtime.chromium.launch(headless=True)
            except Exception:
                self.runtime.stop()
                raise
            self.page = self.browser.new_page()
            self.version = self.browser.version
            return self
        except Exception as exc:
            raise BrowserUnavailable(f"Playwright 不可用：{exc}") from exc

    def __exit__(self, *_exc):
        self.browser.close()
        self.runtime.stop()

    def viewport(self, width, height, media):
        self.page.set_viewport_size({"width": width, "height": height})
        self.page.emulate_media(media=media)

    def navigate(self, url):
        self.page.goto(url, wait_until="load")
        self.evaluate("Promise.all([document.fonts ? document.fonts.ready : Promise.resolve(), ...Array.from(document.images).map(i => i.complete ? Promise.resolve() : new Promise(r => {i.onload=r;i.onerror=r;setTimeout(r,3000)}))])")

    def evaluate(self, expression):
        return self.page.evaluate(expression)

    def screenshot(self, path, *, full_page=False):
        self.page.screenshot(path=str(path), full_page=full_page)

    def key(self, key):
        self.page.keyboard.press(key)

    def click(self, selector):
        self.page.locator(selector).click()


def interaction_check(session) -> list[dict[str, object]]:
    """验证用户实际产物的交互；没有对应控件的项目明确为 not-run。"""
    checks = []
    count = session.evaluate("document.querySelectorAll('[data-deck-page]').length")
    if count and session.evaluate("!!document.querySelector('[data-page-select]')"):
        session.evaluate("SuanhaiPageChecks.choose(0)")
        checks.append({"id": "deck-first-boundary", "status": "pass" if session.evaluate("document.querySelector('[data-page-prev]').disabled") else "fail"})
        if count > 1:
            session.evaluate("document.querySelector('[data-page-next]').click()")
            checks.append({"id": "deck-next", "status": "pass" if session.evaluate("document.querySelector('[data-page-select]').value === '1'") else "fail"})
            session.evaluate("document.querySelector('[data-page-prev]').click()")
            checks.append({"id": "deck-previous", "status": "pass" if session.evaluate("document.querySelector('[data-page-select]').value === '0'") else "fail"})
            session.evaluate("document.activeElement.blur()")
            session.key("ArrowRight")
            forward = session.evaluate("document.querySelector('[data-page-select]').value === '1'")
            session.key("Home")
            home = session.evaluate("document.querySelector('[data-page-select]').value === '0'")
            checks.append({"id": "deck-keyboard", "status": "pass" if forward and home else "fail"})
        session.evaluate(f"SuanhaiPageChecks.choose({count - 1})")
        checks.append({"id": "deck-last-boundary", "status": "pass" if session.evaluate("document.querySelector('[data-page-next]').disabled") else "fail"})
        session.evaluate("SuanhaiPageChecks.choose(0)")
        notes = session.evaluate("!!document.querySelector('[data-notes-toggle]') && !!document.querySelector('[data-deck-notes-panel]') && !!document.querySelector('[data-deck-notes-content]')")
        if notes:
            initial_hidden = session.evaluate("document.querySelector('[data-deck-notes-panel]').hidden")
            session.evaluate("document.querySelector('[data-notes-toggle]').click()")
            correct = session.evaluate("!document.querySelector('[data-deck-notes-panel]').hidden && document.querySelector('[data-deck-notes-content]').textContent === (document.querySelector('[data-deck-page]').getAttribute('data-speaker-note') || '本页没有讲者备注。')")
            session.evaluate("document.querySelector('[data-notes-toggle]').click()")
            checks.append({"id": "speaker-notes", "status": "pass" if initial_hidden and correct else "fail"})
    else:
        checks.append({"id": "deck-navigation", "status": "not-run", "reason": "产物不包含演示稿导航"})
    anchors = session.evaluate("SuanhaiPageChecks.anchors()")
    checks.append({"id": "report-anchors", **anchors})
    if session.evaluate("!!document.querySelector('[data-runtime-mode-select]')"):
        result = session.evaluate("(() => {const s=document.querySelector('[data-runtime-mode-select]'), initial=s.value; let ok=true; for(const value of ['narrow','tablet','desktop','auto']) {s.value=value;s.dispatchEvent(new Event('change',{bubbles:true}));ok=ok && (document.documentElement.getAttribute('data-layout-mode') || 'auto')===value;}s.value=initial;s.dispatchEvent(new Event('change',{bubbles:true}));return ok;})()")
        checks.append({"id": "display-modes", "status": "pass" if result else "fail", "scope": "验证四种模式状态切换并恢复；布局由多视口检查覆盖"})
    else:
        checks.append({"id": "display-modes", "status": "not-run", "reason": "没有显示模式控件"})
    if session.evaluate("!!document.querySelector('[data-runtime-fullscreen]')"):
        supported = session.evaluate("!!document.fullscreenEnabled && typeof document.documentElement.requestFullscreen === 'function'")
        if supported:
            session.click("[data-runtime-fullscreen]")
            session.evaluate("new Promise(r => setTimeout(r, 200))")
            entered = session.evaluate("!!document.fullscreenElement && document.querySelector('[data-runtime-fullscreen]').getAttribute('aria-pressed') === 'true'")
            if session.evaluate("!!document.fullscreenElement"):
                session.click("[data-runtime-fullscreen]")
                session.evaluate("new Promise(r => setTimeout(r, 200))")
            exited = session.evaluate("!document.fullscreenElement && document.querySelector('[data-runtime-fullscreen]').getAttribute('aria-pressed') === 'false'")
            checks.append({"id": "fullscreen", "status": "pass" if entered and exited else "fail", "entered": entered, "exited": exited, "scope": "本次浏览器会话的真实鼠标操作；其他浏览器仍需核验"})
        else:
            checks.append({"id": "fullscreen", "status": "not-run", "reason": "本次浏览器未开放 Fullscreen API"})
    else:
        checks.append({"id": "fullscreen", "status": "not-run", "reason": "没有全屏控件"})
    checks.append({"id": "pdf-dialog", "status": "not-run", "reason": "浏览器打印对话框需人工选择保存位置；确定性文件使用 html.pdf-export 核验"})
    trigger = session.evaluate("(() => {let t=document.querySelector('[data-source-image]'); if(!t)return null;let p=t.closest('[data-deck-page]');return {page:p ? Array.from(document.querySelectorAll('[data-deck-page]')).indexOf(p) : 0};})()")
    if trigger:
        session.evaluate(f"SuanhaiPageChecks.choose({trigger['page']})")
        session.evaluate("(() => {let t=document.querySelector('[data-source-image]');t.focus();t.click();})()")
        opened = session.evaluate("!!document.querySelector('[data-source-viewer][open]')")
        if opened:
            loaded = session.evaluate("(() => {let i=document.querySelector('[data-source-viewer-image]');return new Promise(r=>{let done=()=>r(i.complete && i.naturalWidth>0);if(i.complete)done();else{i.addEventListener('load',done,{once:true});i.addEventListener('error',done,{once:true});setTimeout(done,3000);}});})()")
            if loaded and session.evaluate("!!document.querySelector('[data-source-zoom-in]')"):
                zoomed = session.evaluate("""(async () => {
                    const image = document.querySelector('[data-source-viewer-image]');
                    const area = document.querySelector('.source-viewer__image');
                    const fit = document.querySelector('[data-source-fit]');
                    async function waitFor(predicate) {
                        const end = performance.now() + 1500;
                        while (!predicate() && performance.now() < end) await new Promise(r => requestAnimationFrame(r));
                        return predicate();
                    }
                    // 先回到全图状态，避免初始 min-width 已在缩放上限而误判按钮失效。
                    fit.click();
                    await waitFor(() => image.getBoundingClientRect().width <= area.clientWidth + 1);
                    const width = image.getBoundingClientRect().width;
                    document.querySelector('[data-source-zoom-in]').click();
                    const grew = await waitFor(() => image.getBoundingClientRect().width > width);
                    fit.click();
                    const fitted = await waitFor(() => image.getBoundingClientRect().width <= area.clientWidth + 1);
                    return grew && fitted && fit.getAttribute('aria-pressed') === 'true';
                })()""")
                checks.append({"id": "source-image-zoom", "status": "pass" if zoomed else "fail"})
            before = session.evaluate("document.querySelector('[data-page-select]')?.value || null")
            session.key("ArrowRight")
            after = session.evaluate("document.querySelector('[data-page-select]')?.value || null")
            session.key("Escape")
            session.evaluate("new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
            closed = session.evaluate("!document.querySelector('[data-source-viewer]').open")
            focused = session.evaluate("document.activeElement === document.querySelector('[data-source-image]')")
            checks.append({"id": "source-image-viewer", "status": "pass" if before == after and closed and focused and loaded else "fail", "keyboard_isolated": before == after, "closed": closed, "focus_returned": focused, "image_loaded": loaded})
        else:
            checks.append({"id": "source-image-viewer", "status": "fail", "reason": "存在触发器但阅读器没有打开"})
    else:
        checks.append({"id": "source-image-viewer", "status": "not-run", "reason": "产物未选择原图阅读器"})
    session.evaluate("SuanhaiPageChecks.choose(0)")
    return checks


def _run_browser(session, html_path, viewports, screenshot_dir, all_pages, interactions, full_page=False):
    results = []
    script = Path(__file__).with_name("page_checks.js").read_text(encoding="utf-8")
    with LocalArtifactServer(html_path.parent) as origin:
        for name, width, height, media in viewports:
            session.viewport(width, height, media)
            session.navigate(f"{origin}/{quote(html_path.name)}")
            session.evaluate(script)
            count = session.evaluate("SuanhaiPageChecks.pageCount()") if all_pages else 1
            for index in range(count):
                session.evaluate(f"SuanhaiPageChecks.choose({index})")
                session.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
                metrics = session.evaluate("SuanhaiPageChecks.inspect()")
                failures = metrics["horizontalOverflow"] or metrics["textOverflow"] or metrics["pageVerticalOverflow"] or metrics["navigationOverlap"] or metrics["brokenImages"] or metrics["duplicateIds"]
                if metrics["pageOptions"] is not None and metrics["pageOptions"] != metrics["pageCount"]:
                    failures = True
                item = {"id": name, "width": width, "height": height, "media": media, "page": index + 1, "status": "fail" if failures else "pass", "metrics": metrics}
                session.evaluate("window.scrollTo(0, 0)")
                if screenshot_dir:
                    screenshot_dir.mkdir(parents=True, exist_ok=True)
                    target = screenshot_dir / f"{name}-p{index + 1:03d}.png"
                    session.screenshot(target, full_page=full_page)
                    item["screenshot_scope"] = "full-document" if full_page else "viewport"
                    item["screenshot"] = str(target.resolve())
                results.append(item)
        # 在屏幕媒体下独立检查按钮，避免打印媒体展示所有页导致误判。
        action_results = []
        if interactions:
            session.viewport(1366, 768, "screen")
            session.navigate(f"{origin}/{quote(html_path.name)}")
            session.evaluate(script)
            action_results = interaction_check(session)
    failed = any(item["status"] == "fail" for item in results + action_results)
    return {"status": "fail" if failed else "pass", "version": session.version, "viewports": results, "interactions": action_results}


def browser_check(html_path, viewports, screenshot_dir, *, backend="auto", browser=None, all_pages=False, interactions=False, sandbox=True, full_page=False):
    if backend == "none":
        return {"status": "not-run", "reason": "调用方选择 --backend none", "viewports": [], "interactions": []}
    reasons = []
    for choice in (["playwright", "cdp"] if backend == "auto" else [backend]):
        try:
            with (PlaywrightSession() if choice == "playwright" else ChromiumSession(browser, sandbox=sandbox)) as session:
                result = _run_browser(session, html_path, viewports, screenshot_dir, all_pages, interactions, full_page)
                result["backend"] = choice
                return result
        except BrowserUnavailable as exc:
            reasons.append(str(exc))
        except Exception as exc:
            # 已启动后的页面异常属于失败，不能伪装成缺少运行环境。
            return {"status": "fail", "backend": choice, "reason": f"检查失败：{type(exc).__name__}: {exc}", "viewports": [], "interactions": []}
    return {"status": "not-run", "reason": "; ".join(reasons), "viewports": [], "interactions": []}


def write_gallery(path: Path, current: dict, baseline: dict | None = None) -> None:
    """以离线 HTML 联系表替代额外图像库；对比仅展示证据，不伪称视觉差异通过。"""
    # Windows 临时目录可能使用 8.3 别名；根目录和截图须以相同规范路径计算相对引用。
    path = path.resolve()
    rows = []
    previous = {(item["id"], item["page"]): item for item in (baseline or {}).get("browser", {}).get("viewports", [])}
    def figure(item, title):
        if not item or not item.get("screenshot"):
            return "<p>无截图证据</p>"
        target = Path(item["screenshot"]).resolve()
        relative = os.path.relpath(target, path.parent).replace("\\", "/")
        return f'<figure><figcaption>{html.escape(title)}</figcaption><img loading="lazy" src="{html.escape(quote(relative, safe="/.."), quote=True)}" alt="{html.escape(title, quote=True)}"></figure>'
    for item in current["browser"].get("viewports", []):
        title = f'{item["id"]} / P{item["page"]:03d} / {item["status"]}'
        old = previous.get((item["id"], item["page"]))
        rows.append('<section>' + (figure(old, "上一版 " + title) if baseline else "") + figure(item, "当前版 " + title) + '</section>')
    content = '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>页面检查联系表</title><style>body{font:16px system-ui;margin:24px;background:#eef2f7}section{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:24px}figure{margin:0;flex:1;min-width:280px}img{width:100%;height:auto;border:1px solid #ccd}figcaption{padding:8px}</style><h1>页面检查证据</h1><p>逐页截图用于人工评审；并排对比不等于自动视觉验收通过。</p>' + ''.join(rows) + '</html>'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="检查自包含 HTML 的本地资源和多视口响应式行为")
    parser.add_argument("--html", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--viewport", action="append", type=parse_viewport)
    parser.add_argument("--screenshot-dir", type=Path)
    parser.add_argument("--full-page", action="store_true", help="截图包含整页滚动区域；不等于 PDF 分页检查")
    parser.add_argument("--artifact-kind", choices=("template", "report"), default="template", help="模板允许内容占位；完整报告拒绝候选占位与编写提示")
    parser.add_argument("--fail-on-overflow", action="store_true")
    parser.add_argument("--backend", choices=("auto", "playwright", "cdp", "none"), default="auto")
    parser.add_argument("--browser", help="CDP 后端使用的本机 Chromium 可执行文件")
    parser.add_argument("--all-pages", action="store_true", help="逐页检查整个演示稿，默认只检查首屏")
    parser.add_argument("--interactions", action="store_true", help="检查翻页、备注、原图阅读器等实际成品交互")
    parser.add_argument("--contact-sheet", type=Path, help="写入离线截图联系表 HTML，须同时指定截图目录")
    parser.add_argument("--compare-with", type=Path, help="上一版检查 JSON；与联系表一起生成截图并排对比")
    return parser


def main(argv: list[str] | None = None) -> int:
    # JSON 是跨进程协议，不能依赖 Windows 控制台的系统代码页输出中文。
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    args = build_parser().parse_args(argv)
    if args.contact_sheet and not args.screenshot_dir:
        print(json.dumps({"status": "fail", "error": "--contact-sheet 需要 --screenshot-dir"}, ensure_ascii=False))
        return 2
    if args.compare_with and not args.contact_sheet:
        print(json.dumps({"status": "fail", "error": "--compare-with 需要 --contact-sheet"}, ensure_ascii=False))
        return 2
    html_path = args.html.resolve()
    if not html_path.is_file() or html_path.suffix.lower() != ".html":
        print(json.dumps({"status": "fail", "error": f"HTML 文件不存在或扩展名不正确：{html_path}"}, ensure_ascii=False))
        return 2
    viewports = args.viewport or list(DEFAULT_VIEWPORTS)
    static = static_check(html_path, args.artifact_kind)
    browser = browser_check(html_path, viewports, args.screenshot_dir, backend=args.backend, browser=args.browser, all_pages=args.all_pages, interactions=args.interactions, full_page=args.full_page) if static["status"] == "pass" else {"status": "not-run", "reason": "静态检查失败，未打开含缺失或远程资源的页面", "viewports": [], "interactions": []}
    # 总结状态如实反映浏览器未执行；退出码兼容原先的 --fail-on-overflow 开关。
    status = "fail" if static["status"] == "fail" or browser["status"] == "fail" else browser["status"]
    result = {"schema_version": 1, "tool": "html.viewport-check", "created_at": datetime.now(timezone.utc).isoformat(), "html": str(html_path), "html_sha256": sha256(html_path), "viewports": [{"id": n, "width": w, "height": h, "media": m} for n, w, h, m in viewports], "static": static, "browser": browser, "status": status,
              "checks": [{"id": "static-resources", "status": static["status"], "evidence": static}, {"id": "browser-layout-and-interaction", "status": browser["status"], "evidence": browser}],
              "limits": ["自动几何/交互检查不等于人工视觉、专业内容或发布验收", "打印媒体几何检查不证明 PDF 页数或分页正确", "截图范围由 screenshot_scope 记录；未启用 --full-page 时只记录当前视口", "未自动执行完整无障碍、JS 动态依赖或专业事实核验", "方括号仅为占位候选检测，可能误报文献编号；须人工核对"]}
    try:
        if args.contact_sheet:
            baseline = json.loads(args.compare_with.read_text(encoding="utf-8")) if args.compare_with else None
            write_gallery(args.contact_sheet.resolve(), result, baseline)
            result["contact_sheet"] = str(args.contact_sheet.resolve())
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "fail", "error": f"联系表生成失败：{exc}"}, ensure_ascii=False))
        return 2
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 1 if static["status"] == "fail" or (args.fail_on_overflow and browser["status"] == "fail") else 0


if __name__ == "__main__":
    sys.exit(main())
