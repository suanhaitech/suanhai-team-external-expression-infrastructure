(function () {
  "use strict";
  var root = document.documentElement;
  var pages = Array.prototype.slice.call(document.querySelectorAll("[data-deck-page]"));
  var stage = document.querySelector("[data-deck-stage]");
  var controls = document.querySelector("[data-deck-controls]");
  var tools = document.querySelector("[data-deck-tools]");
  if (!pages.length || !stage || !controls || controls.hasAttribute("data-deck-ready")) return;

  var previousButton = controls.querySelector("[data-page-prev]");
  var nextButton = controls.querySelector("[data-page-next]");
  var pageSelect = controls.querySelector("[data-page-select]");
  var position = controls.querySelector("[data-page-position]");
  var progress = controls.querySelector("[data-page-progress]");
  var progressValue = controls.querySelector("[data-page-progress-value]");
  var notesButton = controls.querySelector("[data-notes-toggle]");
  var notesPanel = document.querySelector("[data-deck-notes-panel]");
  var notesContent = document.querySelector("[data-deck-notes-content]");
  var ratioSelect = document.querySelector("[data-deck-ratio-select]");
  var currentPage = 0, notesOpen = false;
  var normalPageSize = {width: 0, height: 0, paddingTop: "", paddingRight: "", paddingBottom: "", paddingLeft: ""};
  var controlsHideTimer = 0;
  if (notesPanel) {
    notesPanel.tabIndex = 0;
    notesPanel.setAttribute("aria-label", "当前页讲者备注");
  }
  // 翻页只依赖自己的必需控件。缺少备注或比例不应该拖垮阅读导航。
  if (!previousButton || !nextButton || !pageSelect) return;

  function pageTitle(page, index) {
    var slot = page.getAttribute("data-page-title-slot");
    var found = slot && Array.from(page.querySelectorAll("[data-slot]")).find(function (node) { return node.getAttribute("data-slot") === slot; });
    return (found && found.textContent.trim()) || page.getAttribute("data-page-title") || "第 " + (index + 1) + " 页";
  }
  // 在全屏改变视口之前保存设计坐标；仅改变外层倍率，避免文字、图片和页码各自重排。
  function rememberNormalPageSize() {
    if (document.fullscreenElement === root || window.innerWidth <= 760) return;
    var page = pages[currentPage];
    if (!page) return;
    var rect = page.getBoundingClientRect();
    if (rect.width > 0 && rect.height > 0) {
      var style = getComputedStyle(page);
      normalPageSize = {
        width: rect.width, height: rect.height,
        paddingTop: style.paddingTop, paddingRight: style.paddingRight,
        paddingBottom: style.paddingBottom, paddingLeft: style.paddingLeft
      };
    }
  }
  function updateFullscreenScale() {
    if (document.fullscreenElement !== root) return;
    var visible = root.classList.contains("deck-controls-visible");
    var notesHeight = notesPanel && !notesPanel.hidden ? Math.ceil(notesPanel.getBoundingClientRect().height) + 10 : 0;
    var reserved = visible || notesHeight ? Math.ceil(controls.getBoundingClientRect().height) + 32 + notesHeight : 0;
    // 手机不缩放文字，而是缩短可滚动的阅读区；底栏出现也不能盖住最后一行。
    root.style.setProperty("--deck-fullscreen-reserved", reserved + "px");
    if (window.innerWidth <= 760 || !normalPageSize.width || !normalPageSize.height) return;
    var availableHeight = Math.max(1, window.innerHeight - reserved);
    var scale = Math.min(window.innerWidth / normalPageSize.width, availableHeight / normalPageSize.height);
    var left = Math.max(0, (window.innerWidth - normalPageSize.width * scale) / 2);
    var top = Math.max(0, (availableHeight - normalPageSize.height * scale) / 2);
    pages.forEach(function (page) {
      page.style.setProperty("--deck-design-width", normalPageSize.width + "px");
      page.style.setProperty("--deck-design-height", normalPageSize.height + "px");
      page.style.setProperty("--deck-content-scale", String(scale));
      page.style.setProperty("--deck-content-left", left + "px");
      page.style.setProperty("--deck-content-top", top + "px");
      page.style.setProperty("--deck-source-padding-top", normalPageSize.paddingTop);
      page.style.setProperty("--deck-source-padding-right", normalPageSize.paddingRight);
      page.style.setProperty("--deck-source-padding-bottom", normalPageSize.paddingBottom);
      page.style.setProperty("--deck-source-padding-left", normalPageSize.paddingLeft);
    });
  }
  function measureControls() {
    // 控件高度会随屏幕宽度与工具状态变化；画布用它计算控制栏上方的可用空间。
    var rect = controls.getBoundingClientRect();
    var height = Math.ceil(rect.height);
    var notesHeight = notesPanel && !notesPanel.hidden ? Math.ceil(notesPanel.getBoundingClientRect().height) + 10 : 0;
    root.style.setProperty("--deck-controls-height", height + "px");
    root.style.setProperty("--deck-notes-height", notesHeight + "px");
    if (document.fullscreenElement === root) updateFullscreenScale();
    else rememberNormalPageSize();
  }
  function setNotesOpen(open) {
    if (!notesPanel || !notesContent || !notesButton) return;
    notesOpen = open; notesPanel.hidden = !open;
    notesButton.setAttribute("aria-expanded", String(open));
    notesButton.textContent = open ? "收起备注" : "备注";
    notesContent.textContent = pages[currentPage].getAttribute("data-speaker-note") || "本页没有讲者备注。";
    measureControls();
  }
  function showPage(index, returnToTop) {
    currentPage = Math.max(0, Math.min(pages.length - 1, index));
    pages.forEach(function (page, pageIndex) {
      page.hidden = pageIndex !== currentPage;
      page.setAttribute("aria-hidden", String(page.hidden));
      page.setAttribute("aria-label", "第 " + (pageIndex + 1) + " 页：" + pageTitle(page, pageIndex));
    });
    if (document.fullscreenElement === root) updateFullscreenScale();
    else rememberNormalPageSize();
    previousButton.disabled = currentPage === 0; nextButton.disabled = currentPage === pages.length - 1;
    pageSelect.value = String(currentPage);
    if (position) position.value = String(currentPage + 1).padStart(2, "0") + " / " + String(pages.length).padStart(2, "0");
    if (progress) {
      progress.setAttribute("aria-valuemax", String(pages.length));
      progress.setAttribute("aria-valuenow", String(currentPage + 1));
      progress.setAttribute("aria-valuetext", "第 " + (currentPage + 1) + " 页，共 " + pages.length + " 页");
    }
    if (progressValue) progressValue.style.width = ((currentPage + 1) / pages.length) * 100 + "%";
    if (notesOpen) setNotesOpen(true);
    if (returnToTop) stage.scrollIntoView({ block: "start", behavior: "instant" });
  }
  pages.forEach(function (page, index) {
    var number = page.querySelector(".deck-page-number");
    if (number) number.textContent = String(index + 1).padStart(2, "0");
    var singlePage = Array.from(page.children).find(function (child) { return child.hasAttribute("data-single-page-role"); });
    if (singlePage) {
      // 容器拥有画布与页码，单页拥有内容和背景。页码独占一行，避免用绝对
      // 定位覆盖长正文；打印及无脚本时仍保留完整内容，不强行一页一纸。
      page.classList.add("deck-page--composed");
      var folio = document.createElement("div");
      folio.className = "deck-page-folio";
      if (!number) {
        number = document.createElement("span");
        number.className = "deck-page-number";
        number.textContent = String(index + 1).padStart(2, "0");
      }
      var oldFooter = number.parentElement;
      folio.appendChild(number);
      page.appendChild(folio);
      if (oldFooter && !oldFooter.textContent.trim() && !oldFooter.children.length) oldFooter.classList.add("deck-empty-footer");
      // 深色过渡页和浅色内容页沿用各自主题，页码带不能露出另一张白纸。
      var singleStyle = getComputedStyle(singlePage);
      page.style.setProperty("--deck-canvas-background", singleStyle.backgroundColor);
      page.style.setProperty("--deck-folio-color", singleStyle.color);
    }
    var option = document.createElement("option");
    option.value = String(index);
    option.textContent = String(index + 1).padStart(2, "0") + " · " + pageTitle(page, index);
    pageSelect.appendChild(option);
  });
  previousButton.addEventListener("click", function () { showPage(currentPage - 1, true); });
  nextButton.addEventListener("click", function () { showPage(currentPage + 1, true); });
  pageSelect.addEventListener("change", function () { showPage(Number(pageSelect.value) || 0, true); });
  previousButton.title = "上一页（← / PageUp）"; nextButton.title = "下一页（→ / PageDown / 空格）";
  if (notesButton && notesPanel && notesContent) notesButton.addEventListener("click", function () { setNotesOpen(!notesOpen); });
  else if (notesButton) notesButton.hidden = true;
  if (ratioSelect) {
    ratioSelect.value = root.getAttribute("data-deck-ratio") || "auto";
    ratioSelect.addEventListener("change", function () { root.setAttribute("data-deck-ratio", ratioSelect.value); });
  }
  // 容器组合现有控件而不重写运行时动作；长页仍可单独使用同一运行时。
  if (tools) {
    tools.hidden = false;
    if (notesButton) tools.insertBefore(notesButton, tools.querySelector("[data-runtime-toolbar]"));
    controls.appendChild(tools);
  }
  function arrangeTools() {
    if (!tools) return;
    var inner = tools.querySelector(".runtime-toolbar__inner");
    if (inner) {
      var modes = inner.querySelector(".runtime-toolbar__group--modes");
      var ratio = tools.querySelector(".deck-ratio-control");
      if (ratio) inner.insertBefore(ratio, modes);
      if (notesButton) inner.insertBefore(notesButton, inner.querySelector(".runtime-toolbar__group--view"));
    }
    measureControls();
  }
  arrangeTools();
  document.addEventListener("suanhai:runtime-ready", arrangeTools);
  function controlsAreHeldOpen() {
    return controls.matches(":hover") || controls.contains(document.activeElement);
  }
  function hideControlsSoon(delay) {
    window.clearTimeout(controlsHideTimer);
    controlsHideTimer = window.setTimeout(function () {
      if (document.fullscreenElement === root && !controlsAreHeldOpen()) {
        root.classList.remove("deck-controls-visible");
        updateFullscreenScale();
      }
    }, delay);
  }
  function revealControls() {
    if (document.fullscreenElement !== root) return;
    window.clearTimeout(controlsHideTimer);
    root.classList.add("deck-controls-visible");
    updateFullscreenScale();
    hideControlsSoon(1800);
  }
  document.addEventListener("fullscreenchange", function () {
    var active = document.fullscreenElement === root;
    root.classList.toggle("deck-fullscreen", active);
    window.clearTimeout(controlsHideTimer);
    root.classList.remove("deck-controls-visible");
    if (active && controls.contains(document.activeElement)) document.activeElement.blur();
    measureControls();
  });
  root.addEventListener("click", function (event) {
    if (event.target.closest && event.target.closest("[data-runtime-fullscreen]") && document.fullscreenElement !== root) rememberNormalPageSize();
  }, true);
  controls.addEventListener("pointerenter", function () { window.clearTimeout(controlsHideTimer); });
  controls.addEventListener("pointerleave", function () { hideControlsSoon(700); });
  controls.addEventListener("focusin", function () { root.classList.add("deck-controls-visible"); updateFullscreenScale(); });
  controls.addEventListener("focusout", function () { hideControlsSoon(1800); });
  window.addEventListener("pointermove", function (event) {
    if (document.fullscreenElement !== root) return;
    if (event.clientY >= window.innerHeight - 110) revealControls();
    else hideControlsSoon(1800);
  });
  window.addEventListener("pointerdown", function (event) {
    if (event.pointerType === "touch" && event.clientY >= window.innerHeight - 140) revealControls();
  });
  document.addEventListener("keydown", function (event) {
    if (event.defaultPrevented || event.isComposing || event.altKey || event.ctrlKey || event.metaKey || document.querySelector("dialog[open]")) return;
    if (event.key === "Escape" && notesOpen) { setNotesOpen(false); if (notesButton) notesButton.focus(); return; }
    if (event.target instanceof Element && (event.target.isContentEditable || event.target.closest("input, select, textarea, button, a, [role='textbox']"))) return;
    if (event.key === "ArrowRight" || event.key === "PageDown" || event.key === " ") { event.preventDefault(); showPage(currentPage + (event.key === " " && event.shiftKey ? -1 : 1), true); }
    else if (event.key === "ArrowLeft" || event.key === "PageUp") { event.preventDefault(); showPage(currentPage - 1, true); }
    else if (event.key === "Home") { event.preventDefault(); showPage(0, true); }
    else if (event.key === "End") { event.preventDefault(); showPage(pages.length - 1, true); }
  });
  controls.hidden = false; root.classList.add("deck--ready"); controls.setAttribute("data-deck-ready", "true");
  if (window.ResizeObserver) {
    var observer = new ResizeObserver(measureControls);
    observer.observe(controls);
    if (notesPanel) observer.observe(notesPanel);
  }
  window.addEventListener("resize", measureControls);
  document.addEventListener("suanhai:runtime-ready", measureControls);
  showPage(0); measureControls();
}());
