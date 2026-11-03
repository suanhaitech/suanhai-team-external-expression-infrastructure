/* 原图属于消费端内容；阅读器只负责完整展示、焦点和键盘边界。 */
(function () {
  "use strict";
  if (window.SuanhaiImageViewer) return;
  var dialog, image, caption, message, previousFocus;

  function ensureDialog() {
    if (dialog) return true;
    var candidate = document.createElement("dialog");
    if (typeof candidate.showModal !== "function") return false;
    candidate.className = "source-viewer";
    candidate.setAttribute("data-source-viewer", "");
    candidate.setAttribute("aria-label", "完整原图阅读器");
    candidate.innerHTML = '<div class="source-viewer__bar"><p data-source-viewer-caption></p><button type="button" data-source-close aria-label="关闭原图阅读器">关闭</button></div><p role="status" data-source-viewer-status></p><div class="source-viewer__image"><img data-source-viewer-image alt=""></div>';
    image = candidate.querySelector("[data-source-viewer-image]");
    caption = candidate.querySelector("[data-source-viewer-caption]");
    message = candidate.querySelector("[data-source-viewer-status]");
    candidate.querySelector("[data-source-close]").addEventListener("click", function () { dialog.close(); });
    // 让方向键、空格等留在阅读器内，避免背后的演示稿翻页；Escape 仍由原生 dialog 处理。
    candidate.addEventListener("keydown", function (event) {
      event.stopPropagation();
      if (event.key === "Escape") { event.preventDefault(); candidate.close(); }
    });
    candidate.addEventListener("close", function () {
      if (previousFocus && previousFocus.isConnected) previousFocus.focus();
    });
    image.addEventListener("load", function () { message.textContent = ""; });
    image.addEventListener("error", function () { message.textContent = "原图加载失败，请关闭后使用原图链接检查文件。"; });
    document.body.appendChild(candidate);
    dialog = candidate;
    return true;
  }

  function open(trigger) {
    var raw = trigger.getAttribute("data-source-image") || trigger.getAttribute("href");
    if (!raw) return false;
    var url;
    try { url = new URL(raw, document.baseURI); } catch (_) { return false; }
    // 自包含作品不从远端拉取原图；href 仍是无脚本和旧浏览器的后备访问入口。
    if (!/^(file:|https?:)$/.test(url.protocol) || url.origin !== window.location.origin || !ensureDialog()) return false;
    previousFocus = trigger;
    caption.textContent = trigger.getAttribute("data-source-caption") || trigger.getAttribute("aria-label") || "完整原图";
    image.alt = caption.textContent;
    message.textContent = "正在加载原图…";
    image.src = url.href;
    var minimum = Number(trigger.getAttribute("data-source-min-width"));
    image.style.minWidth = Number.isFinite(minimum) && minimum > 0 && minimum <= 12000 ? minimum + "px" : "";
    if (!dialog.open) dialog.showModal();
    dialog.scrollTop = 0;
    dialog.querySelector(".source-viewer__image").scrollLeft = 0;
    if (image.complete && image.naturalWidth > 0) message.textContent = "";
    return true;
  }

  // 委托监听允许后插入的页面复用同一阅读器，也使重复 init 不会重复绑定事件。
  function init() {
    if (document.documentElement.hasAttribute("data-source-viewer-ready")) return;
    document.documentElement.setAttribute("data-source-viewer-ready", "true");
    document.addEventListener("click", function (event) {
      var trigger = event.target instanceof Element ? event.target.closest("[data-source-image]") : null;
      if (trigger && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey && open(trigger)) event.preventDefault();
    });
  }
  window.SuanhaiImageViewer = { init: init, open: open };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
}());
