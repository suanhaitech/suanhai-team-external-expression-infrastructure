/* 图片是消费端内容；阅读器独立管理缩放、加载状态和模态键盘边界。 */
(function () {
  "use strict";
  if (window.SuanhaiImageViewer) { window.SuanhaiImageViewer.init(); return; }
  var dialog, image, caption, message, viewport, zoomLabel, previousFocus, scale = 1, sizing = "fit", minimum = 0, oldOverflow, drag;
  function sizeImage(mode, nextScale) {
    sizing = mode || sizing;
    if (!image.naturalWidth) return;
    var fit = Math.min(viewport.clientWidth, viewport.clientHeight * image.naturalWidth / image.naturalHeight, image.naturalWidth);
    // 大扫描图在手机上可能低于 10%；最低缩放必须允许完整看见原图。
    var lowerScale = Math.min(.1, fit / image.naturalWidth);
    var width = sizing === "fit" ? fit : sizing === "reading" ? Math.max(fit, minimum) : image.naturalWidth * (nextScale || 1);
    width = Math.max(image.naturalWidth * lowerScale, Math.min(width, image.naturalWidth * 8, 48000));
    scale = width / image.naturalWidth;
    image.style.width = width + "px";
    zoomLabel.value = Math.round(scale * 100) + "%";
    dialog.querySelector("[data-source-fit]").setAttribute("aria-pressed", String(sizing === "fit"));
    dialog.querySelector("[data-source-actual]").setAttribute("aria-pressed", String(sizing === "actual" && Math.abs(scale - 1) < .001));
    dialog.querySelector("[data-source-zoom-out]").disabled = scale <= lowerScale + .0001;
    dialog.querySelector("[data-source-zoom-in]").disabled = scale >= 7.999 || width >= 48000;
  }
  function zoom(factor) { sizeImage("actual", scale * factor); }
  function ensureDialog() {
    if (dialog) return true;
    var candidate = document.createElement("dialog");
    if (typeof candidate.showModal !== "function") return false;
    candidate.className = "source-viewer"; candidate.setAttribute("data-source-viewer", "");
    candidate.setAttribute("aria-label", "完整原图阅读器");
    candidate.innerHTML = '<div class="source-viewer__bar"><p data-source-viewer-caption></p><button type="button" data-source-close aria-label="关闭原图阅读器">关闭 ×</button></div><div class="source-viewer__tools" role="group" aria-label="原图显示"><button type="button" data-source-fit>适应窗口</button><button type="button" data-source-actual>原始尺寸</button><span class="source-viewer__separator"></span><button type="button" data-source-zoom-out aria-label="缩小原图">−</button><output data-source-zoom aria-live="polite">100%</output><button type="button" data-source-zoom-in aria-label="放大原图">＋</button><a data-source-original target="_blank" rel="noopener">打开原图 ↗</a></div><p role="status" data-source-viewer-status></p><div class="source-viewer__image" tabindex="0" role="region" aria-label="原图阅读区域，可滚动查看"><img data-source-viewer-image alt="" draggable="false"></div><p class="source-viewer__hint">放大后可滚动或用鼠标拖动查看 · Esc 关闭</p>';
    dialog = candidate;
    image = dialog.querySelector("[data-source-viewer-image]");
    caption = dialog.querySelector("[data-source-viewer-caption]");
    message = dialog.querySelector("[data-source-viewer-status]");
    viewport = dialog.querySelector(".source-viewer__image");
    zoomLabel = dialog.querySelector("[data-source-zoom]");
    dialog.querySelector("[data-source-close]").addEventListener("click", function () { dialog.close(); });
    dialog.querySelector("[data-source-fit]").addEventListener("click", function () { sizeImage("fit"); viewport.scrollTo(0, 0); });
    dialog.querySelector("[data-source-actual]").addEventListener("click", function () { sizeImage("actual", 1); viewport.scrollTo(0, 0); });
    dialog.querySelector("[data-source-zoom-in]").addEventListener("click", function () { zoom(1.25); });
    dialog.querySelector("[data-source-zoom-out]").addEventListener("click", function () { zoom(.8); });
    // 不接管浏览器 Ctrl+加减/触摸缩放。阅读器内的普通加减键只缩放图片。
    dialog.addEventListener("keydown", function (event) {
      event.stopPropagation();
      if (event.key === "Escape") { event.preventDefault(); dialog.close(); }
      if (!event.ctrlKey && !event.metaKey && !event.altKey) {
        if (event.key === "+" || event.key === "=") { event.preventDefault(); zoom(1.25); }
        if (event.key === "-") { event.preventDefault(); zoom(.8); }
      }
    });
    dialog.addEventListener("close", function () {
      document.body.style.overflow = oldOverflow;
      if (previousFocus && previousFocus.isConnected) previousFocus.focus({ preventScroll: true });
      drag = null;
    });
    image.addEventListener("load", function () {
      message.textContent = ""; image.hidden = false;
      dialog.querySelectorAll(".source-viewer__tools button").forEach(function (button) { button.disabled = false; });
      sizeImage(sizing, 1);
    });
    image.addEventListener("error", function () { message.textContent = "原图加载失败。请使用「打开原图」检查文件，或关闭后重试。"; image.hidden = true; });
    // 鼠标拖动只是滚动的补充；手机使用浏览器原生触摸滚动，避免手势冲突。
    viewport.addEventListener("pointerdown", function (event) {
      if (event.pointerType !== "mouse" || event.button !== 0 || !image.naturalWidth) return;
      drag = { x: event.clientX, y: event.clientY, left: viewport.scrollLeft, top: viewport.scrollTop };
      viewport.setPointerCapture(event.pointerId); viewport.classList.add("is-dragging");
    });
    viewport.addEventListener("pointermove", function (event) {
      if (drag) { viewport.scrollLeft = drag.left - event.clientX + drag.x; viewport.scrollTop = drag.top - event.clientY + drag.y; }
    });
    ["pointerup", "pointercancel", "lostpointercapture"].forEach(function (type) {
      viewport.addEventListener(type, function () { drag = null; viewport.classList.remove("is-dragging"); });
    });
    document.body.appendChild(dialog);
    if (window.ResizeObserver) new ResizeObserver(function () { if (dialog.open && sizing !== "actual") sizeImage(sizing); }).observe(viewport);
    return true;
  }
  function open(trigger) {
    var raw = trigger.getAttribute("data-source-image") || trigger.getAttribute("href"), url;
    if (!raw) return false;
    try { url = new URL(raw, document.baseURI); } catch (_) { return false; }
    if (!/^(file:|https?:)$/.test(url.protocol) || url.origin !== window.location.origin || !ensureDialog()) return false;
    previousFocus = trigger;
    caption.textContent = trigger.getAttribute("data-source-caption") || trigger.getAttribute("aria-label") || "完整原图";
    image.alt = caption.textContent; message.textContent = "正在加载原图…";
    dialog.querySelector("[data-source-original]").href = url.href;
    dialog.querySelectorAll(".source-viewer__tools button").forEach(function (button) { button.disabled = true; });
    minimum = Number(trigger.getAttribute("data-source-min-width"));
    if (!Number.isFinite(minimum) || minimum < 0 || minimum > 12000) minimum = 0;
    sizing = minimum ? "reading" : "fit"; scale = 1;
    image.hidden = true; image.style.width = ""; image.src = url.href;
    if (!dialog.open) { oldOverflow = document.body.style.overflow; dialog.showModal(); document.body.style.overflow = "hidden"; }
    viewport.scrollTo(0, 0);
    if (image.complete && image.naturalWidth > 0) image.dispatchEvent(new Event("load"));
    else if (image.complete) image.dispatchEvent(new Event("error"));
    return true;
  }
  function init() {
    if (document.documentElement.hasAttribute("data-source-viewer-ready")) return;
    document.documentElement.setAttribute("data-source-viewer-ready", "true");
    document.addEventListener("click", function (event) {
      var trigger = event.target instanceof Element ? event.target.closest("[data-source-image]") : null;
      if (trigger && !event.defaultPrevented && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey && open(trigger)) event.preventDefault();
    });
  }
  window.SuanhaiImageViewer = { init: init, open: open };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
}());
