/* 运行时管理交互状态，页面模板通过 data 属性解释布局。 */
(function () {
  "use strict";
  if (window.SuanhaiRuntime) { window.SuanhaiRuntime.init(); return; }
  var root = document.documentElement, toolbar, fullscreenButton, status, statusTimer;
  var modes = [["自动", "auto"], ["窄屏", "narrow"], ["平板", "tablet"], ["桌面", "desktop"]];

  function announce(message) {
    if (!status) return;
    clearTimeout(statusTimer);
    status.textContent = message; status.hidden = false;
    statusTimer = setTimeout(function () { status.hidden = true; }, 6000);
  }
  function setMode(mode) {
    if (!modes.some(function (item) { return item[1] === mode; })) mode = "auto";
    if (mode === "auto") root.removeAttribute("data-layout-mode");
    else root.setAttribute("data-layout-mode", mode);
    if (!toolbar) return;
    toolbar.querySelectorAll("[data-runtime-mode]").forEach(function (button) {
      button.setAttribute("aria-pressed", String(button.getAttribute("data-runtime-mode") === mode));
    });
    toolbar.querySelector("[data-runtime-mode-select]").value = mode;
    document.dispatchEvent(new CustomEvent("suanhai:layout-change", { detail: { mode: mode } }));
  }
  function renderMath() {
    var engine = window.katex;
    document.querySelectorAll("[data-math]").forEach(function (element) {
      var source = element.getAttribute("data-math") || "";
      element.setAttribute("aria-label", element.getAttribute("aria-label") || source);
      if (element.getAttribute("data-math-rendered") === "true") return;
      try {
        if (!engine || typeof engine.render !== "function") throw new Error("math engine unavailable");
        engine.render(source, element, { displayMode: element.getAttribute("data-math-display") === "block", throwOnError: true, trust: false, strict: "ignore" });
        element.setAttribute("data-math-rendered", "true");
        element.removeAttribute("data-math-fallback");
      } catch (_) {
        element.setAttribute("data-math-fallback", "true"); element.textContent = source;
      }
    });
  }
  function iconFor(name) {
    var paths = {
      auto: '<rect x="3" y="4" width="18" height="13" rx="2"/><path d="M8 21h8M12 17v4"/>',
      narrow: '<rect x="7" y="2" width="10" height="20" rx="2"/><path d="M11 18h2"/>',
      tablet: '<rect x="4" y="2" width="16" height="20" rx="2"/><path d="M11 18h2"/>',
      desktop: '<rect x="2" y="4" width="20" height="13" rx="2"/><path d="M8 21h8M12 17v4"/>',
      fullscreen: '<path d="M8 3H3v5M16 3h5v5M8 21H3v-5M16 21h5v-5"/>',
      pdf: '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9zM14 3v6h6M12 12v6m-3-3 3 3 3-3"/>'
    };
    return '<span class="runtime-toolbar__button-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">' + (paths[name] || paths.auto) + '</svg></span>';
  }
  function button(label, name) {
    var element = document.createElement("button");
    element.type = "button"; element.className = "runtime-toolbar__button runtime-toolbar__" + name;
    element.innerHTML = iconFor(name) + '<span class="runtime-toolbar__button-label">' + label + '</span>';
    return element;
  }
  function fullscreenSupported() {
    return typeof root.requestFullscreen === "function" && typeof document.exitFullscreen === "function" && document.fullscreenEnabled !== false;
  }
  function updateFullscreenState() {
    if (!fullscreenButton) return;
    var active = Boolean(document.fullscreenElement);
    fullscreenButton.setAttribute("aria-pressed", String(active));
    fullscreenButton.setAttribute("aria-label", active ? "退出全屏模式" : "进入全屏模式");
    fullscreenButton.querySelector(".runtime-toolbar__button-label").textContent = active ? "退出全屏" : "全屏";
    fullscreenButton.title = fullscreenSupported() ? (active ? "退出全屏（Esc）" : "进入全屏") : "当前浏览器不支持全屏，可使用浏览器的全屏功能";
  }
  function toggleFullscreen() {
    if (!fullscreenSupported()) { announce("当前浏览器不支持全屏，可使用浏览器的全屏功能。"); return; }
    // 同步异常和 Promise 拒绝都需要可见反馈，不能让用户猜测操作结果。
    try {
      var action = document.fullscreenElement ? document.exitFullscreen() : root.requestFullscreen();
      Promise.resolve(action).catch(function () { announce("未能进入或退出全屏，请检查浏览器权限后重试。"); updateFullscreenState(); });
    } catch (_) { announce("全屏操作失败，请检查浏览器权限后重试。"); updateFullscreenState(); }
  }
  function init() {
    toolbar = document.querySelector("[data-runtime-toolbar]");
    if (toolbar && !toolbar.hasAttribute("data-runtime-ready")) {
      toolbar.setAttribute("data-runtime-ready", "true");
      toolbar.innerHTML = '<div class="runtime-toolbar__inner"><div class="runtime-toolbar__group runtime-toolbar__group--modes"><label class="runtime-toolbar__header"><span class="runtime-toolbar__label">布局</span><select class="runtime-toolbar__mode-select" data-runtime-mode-select aria-label="选择页面显示模式"></select></label><div class="runtime-toolbar__mode-buttons" role="group" aria-label="页面显示模式"></div></div><div class="runtime-toolbar__group runtime-toolbar__group--view"></div><div class="runtime-toolbar__group runtime-toolbar__group--output"></div></div>';
      var select = toolbar.querySelector("[data-runtime-mode-select]");
      modes.forEach(function (item) {
        var option = document.createElement("option");
        option.value = item[1]; option.textContent = item[0]; select.appendChild(option);
        var modeButton = button(item[0], item[1]);
        modeButton.setAttribute("data-runtime-mode", item[1]);
        modeButton.addEventListener("click", function () { setMode(item[1]); });
        toolbar.querySelector(".runtime-toolbar__mode-buttons").appendChild(modeButton);
      });
      select.addEventListener("change", function () { setMode(select.value); });
      fullscreenButton = button("全屏", "fullscreen");
      fullscreenButton.setAttribute("data-runtime-fullscreen", "true");
      fullscreenButton.addEventListener("click", toggleFullscreen);
      toolbar.querySelector(".runtime-toolbar__group--view").appendChild(fullscreenButton);
      var pdf = button("保存 PDF", "pdf");
      pdf.setAttribute("data-runtime-pdf", "true");
      pdf.title = "打开打印对话框，目标打印机选择「另存为 PDF」；默认打印全部页面";
      pdf.setAttribute("aria-label", "保存 PDF：打开浏览器打印对话框");
      pdf.addEventListener("click", function () {
        announce("在打印对话框中选择「另存为 PDF」。" + (document.querySelector("[data-deck-page]") ? "演示稿将输出全部页面。" : "页面按打印样式输出。"));
        // 先绘制提示，再打开阻塞式对话框；不承诺自动下载文件。
        setTimeout(function () { try { window.print(); } catch (_) { announce("无法打开打印对话框，请使用浏览器的打印菜单。"); } }, 100);
      });
      toolbar.querySelector(".runtime-toolbar__group--output").appendChild(pdf);
      status = document.createElement("p"); status.className = "runtime-status";
      status.setAttribute("data-runtime-status", ""); status.setAttribute("role", "status"); status.hidden = true;
      document.body.appendChild(status);
      document.addEventListener("fullscreenchange", updateFullscreenState);
      updateFullscreenState(); setMode(root.getAttribute("data-layout-mode") || "auto");
      document.dispatchEvent(new CustomEvent("suanhai:runtime-ready"));
    }
    renderMath();
  }
  window.SuanhaiRuntime = { init: init, setMode: setMode, renderMath: renderMath };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
}());
