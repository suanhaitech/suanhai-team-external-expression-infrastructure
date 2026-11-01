(function () {
  "use strict";

  var root = document.documentElement;
  var toolbar = document.querySelector("[data-runtime-toolbar]");
  var fullscreenButton = null;

  function setMode(mode) {
    if (mode === "auto") {
      root.removeAttribute("data-layout-mode");
    } else {
      root.setAttribute("data-layout-mode", mode);
    }
    if (!toolbar) return;
    toolbar.querySelectorAll("[data-runtime-mode]").forEach(function (button) {
      button.setAttribute("aria-pressed", button.getAttribute("data-runtime-mode") === mode ? "true" : "false");
    });
    var select = toolbar.querySelector("[data-runtime-mode-select]");
    if (select) select.value = mode;
  }

  function renderMath() {
    var engine = window.katex;
    document.querySelectorAll("[data-math]").forEach(function (element) {
      var source = element.getAttribute("data-math") || "";
      var displayMode = element.getAttribute("data-math-display") === "block";
      var label = element.getAttribute("aria-label") || source;
      element.setAttribute("aria-label", label);
      if (element.getAttribute("data-math-rendered") === "true") return;
      if (!engine || typeof engine.render !== "function") {
        element.setAttribute("data-math-fallback", "true");
        element.textContent = source;
        return;
      }
      try {
        engine.render(source, element, { displayMode: displayMode, throwOnError: true, trust: false, strict: "ignore" });
        element.setAttribute("data-math-rendered", "true");
      } catch (error) {
        element.setAttribute("data-math-fallback", "true");
        element.textContent = source;
      }
    });
  }

  function createButton(label, mode) {
    var button = document.createElement("button");
    button.type = "button";
    button.className = "runtime-toolbar__button";
    button.innerHTML = iconFor(mode) + "<span class=\"runtime-toolbar__button-label\">" + label + "</span>";
    button.setAttribute("data-runtime-mode", mode);
    button.title = "切换到" + label + "布局";
    button.setAttribute("aria-pressed", "false");
    button.addEventListener("click", function () { setMode(mode); });
    return button;
  }

  function iconFor(name) {
    var paths = {
      auto: '<path d="M4 5.5h16v10H4zM8 19h8M12 15.5V19"/><path d="M7 8.5h4"/>',
      narrow: '<rect x="7" y="3" width="10" height="18" rx="1.5"/><path d="M11 18h2"/>',
      tablet: '<rect x="5" y="3" width="14" height="18" rx="1.5"/><path d="M11 18h2"/>',
      desktop: '<path d="M3 5.5h18v11H3zM8 20h8M12 16.5V20"/>',
      fullscreen: '<path d="M8 3H3v5M16 3h5v5M8 21H3v-5M16 21h5v-5"/>',
      pdf: '<path d="M6 2.75h8l4 4V21H6z"/><path d="M14 2.75v4h4M8.5 15.5h2a1.5 1.5 0 0 0 0-3h-2v5M13 17.5v-5h1.5a2.5 2.5 0 0 1 0 5H13"/>'
    };
    return '<span class="runtime-toolbar__button-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">' + (paths[name] || paths.auto) + '</svg></span>';
  }

  function createModeSelect() {
    var select = document.createElement("select");
    select.className = "runtime-toolbar__mode-select";
    select.setAttribute("data-runtime-mode-select", "true");
    select.setAttribute("aria-label", "选择页面显示模式");
    [["自动", "auto"], ["窄屏", "narrow"], ["平板", "tablet"], ["桌面", "desktop"]].forEach(function (item) {
      var option = document.createElement("option");
      option.value = item[1];
      option.textContent = item[0];
      select.appendChild(option);
    });
    select.addEventListener("change", function () { setMode(select.value); });
    return select;
  }

  function fullscreenSupported() {
    return Boolean(
      root &&
      typeof root.requestFullscreen === "function" &&
      typeof document.exitFullscreen === "function"
    );
  }

  function updateFullscreenState() {
    if (!fullscreenButton) return;
    var active = Boolean(document.fullscreenElement);
    fullscreenButton.setAttribute("aria-pressed", active ? "true" : "false");
    fullscreenButton.setAttribute("aria-label", active ? "退出全屏模式" : "进入全屏模式");
    fullscreenButton.title = active ? "退出全屏模式（Esc 也可以退出）" : "进入全屏模式";
    fullscreenButton.querySelector("[data-runtime-fullscreen-label]").textContent = active ? "退出全屏" : "全屏";
  }

  function toggleFullscreen() {
    if (!fullscreenSupported()) return;
    var action = document.fullscreenElement ? document.exitFullscreen() : root.requestFullscreen();
    if (action && typeof action.catch === "function") {
      action.catch(function () { updateFullscreenState(); });
    }
  }

  function createFullscreenButton() {
    var button = document.createElement("button");
    button.type = "button";
    button.className = "runtime-toolbar__button runtime-toolbar__fullscreen";
    button.setAttribute("data-runtime-fullscreen", "true");
    button.setAttribute("aria-pressed", "false");
    button.innerHTML = iconFor("fullscreen") + "<span class=\"runtime-toolbar__button-label\" data-runtime-fullscreen-label>全屏</span>";
    button.addEventListener("click", toggleFullscreen);
    if (!fullscreenSupported()) {
      button.disabled = true;
      button.title = "当前浏览器不支持全屏模式";
    }
    fullscreenButton = button;
    updateFullscreenState();
    return button;
  }

  function createPdfButton() {
    var button = document.createElement("button");
    button.type = "button";
    button.className = "runtime-toolbar__button runtime-toolbar__pdf";
    button.setAttribute("data-runtime-pdf", "true");
    button.setAttribute("aria-label", "保存 PDF：打开浏览器打印对话框");
    button.title = "打开浏览器打印对话框，可选择保存为 PDF";
    button.innerHTML = iconFor("pdf") + "<span class=\"runtime-toolbar__button-label\">保存 PDF</span>";
    button.addEventListener("click", function () { window.print(); });
    return button;
  }

  function installToolbar() {
    if (!toolbar || toolbar.getAttribute("data-runtime-ready") === "true") return;
    toolbar.setAttribute("data-runtime-ready", "true");
    var inner = document.createElement("div");
    inner.className = "runtime-toolbar__inner";
    var modes = document.createElement("div");
    modes.className = "runtime-toolbar__group runtime-toolbar__group--modes";
    modes.setAttribute("role", "group");
    modes.setAttribute("aria-label", "页面显示模式");
    var modeHeader = document.createElement("div");
    modeHeader.className = "runtime-toolbar__header";
    var label = document.createElement("span");
    label.className = "runtime-toolbar__label";
    label.textContent = "显示模式";
    modeHeader.appendChild(label);
    modeHeader.appendChild(createModeSelect());
    modes.appendChild(modeHeader);
    var modeButtons = document.createElement("div");
    modeButtons.className = "runtime-toolbar__mode-buttons";
    [["自动", "auto"], ["窄屏", "narrow"], ["平板", "tablet"], ["桌面", "desktop"]].forEach(function (item) {
      modeButtons.appendChild(createButton(item[0], item[1]));
    });
    modes.appendChild(modeButtons);
    var view = document.createElement("div");
    view.className = "runtime-toolbar__group runtime-toolbar__group--view";
    view.setAttribute("role", "group");
    view.setAttribute("aria-label", "页面视图操作");
    view.appendChild(createFullscreenButton());
    var actions = document.createElement("div");
    actions.className = "runtime-toolbar__group runtime-toolbar__group--output";
    actions.setAttribute("role", "group");
    actions.setAttribute("aria-label", "页面输出");
    actions.appendChild(createPdfButton());
    inner.appendChild(modes);
    inner.appendChild(view);
    inner.appendChild(actions);
    toolbar.appendChild(inner);
    setMode("auto");
    document.addEventListener("fullscreenchange", updateFullscreenState);
  }

  installToolbar();
  renderMath();
}());
