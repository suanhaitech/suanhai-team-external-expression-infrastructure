(function () {
  "use strict";

  var root = document.documentElement;
  var pages = Array.prototype.slice.call(document.querySelectorAll("[data-deck-page]"));
  var stage = document.querySelector("[data-deck-stage]");
  var controls = document.querySelector("[data-deck-controls]");
  var tools = document.querySelector("[data-deck-tools]");
  if (!pages.length || !stage || !controls || !tools) return;

  var previousButton = controls.querySelector("[data-page-prev]");
  var nextButton = controls.querySelector("[data-page-next]");
  var pageSelect = controls.querySelector("[data-page-select]");
  var position = controls.querySelector("[data-page-position]");
  var progress = controls.querySelector("[data-page-progress]");
  var progressValue = controls.querySelector("[data-page-progress-value]");
  var notesButton = controls.querySelector("[data-notes-toggle]");
  var notesPanel = document.querySelector("[data-deck-notes-panel]");
  var notesContent = document.querySelector("[data-deck-notes-content]");
  var ratioSelect = tools.querySelector("[data-deck-ratio-select]");
  var currentPage = 0;
  var notesOpen = false;

  if (!previousButton || !nextButton || !pageSelect || !position || !progress || !progressValue || !notesButton || !notesPanel || !notesContent || !ratioSelect) return;
  if (controls.getAttribute("data-deck-ready") === "true") return;

  function pageTitle(page, index) {
    var titleSlot = page.getAttribute("data-page-title-slot");
    if (titleSlot) {
      var slots = page.querySelectorAll("[data-slot]");
      for (var slotIndex = 0; slotIndex < slots.length; slotIndex += 1) {
        if (slots[slotIndex].getAttribute("data-slot") === titleSlot) {
          var title = slots[slotIndex].textContent.trim();
          if (title) return title;
        }
      }
    }
    return page.getAttribute("data-page-title") || "第 " + (index + 1) + " 页";
  }

  pages.forEach(function (page, index) {
    var number = page.querySelector(".deck-page-number");
    if (number) number.textContent = String(index + 1).padStart(2, "0");
  });

  function setNotesOpen(open) {
    notesOpen = open;
    notesPanel.hidden = !open;
    notesButton.setAttribute("aria-expanded", open ? "true" : "false");
    notesButton.textContent = open ? "收起备注" : "备注";
    notesContent.textContent = pages[currentPage].getAttribute("data-speaker-note") || "本页没有讲者备注。";
  }

  function showPage(index, returnToTop) {
    currentPage = Math.max(0, Math.min(pages.length - 1, index));
    pages.forEach(function (page, pageIndex) {
      var active = pageIndex === currentPage;
      page.hidden = !active;
      page.setAttribute("aria-hidden", active ? "false" : "true");
      page.setAttribute("aria-label", "第 " + (pageIndex + 1) + " 页：" + pageTitle(page, pageIndex));
    });

    previousButton.disabled = currentPage === 0;
    nextButton.disabled = currentPage === pages.length - 1;
    pageSelect.value = String(currentPage);
    position.value = String(currentPage + 1).padStart(2, "0") + " / " + String(pages.length).padStart(2, "0");
    progress.setAttribute("aria-valuemax", String(pages.length));
    progress.setAttribute("aria-valuenow", String(currentPage + 1));
    progress.setAttribute("aria-valuetext", "第 " + (currentPage + 1) + " 页，共 " + pages.length + " 页");
    progressValue.style.width = ((currentPage + 1) / pages.length) * 100 + "%";
    if (notesOpen) setNotesOpen(true);
    // 用户可能在长页末尾点击底部控件；新页应从开头阅读，不能继承旧页滚动位置。
    if (returnToTop) stage.scrollIntoView({ block: "start", behavior: "instant" });
  }

  pages.forEach(function (page, index) {
    var option = document.createElement("option");
    option.value = String(index);
    option.textContent = String(index + 1).padStart(2, "0") + " · " + pageTitle(page, index);
    pageSelect.appendChild(option);
  });

  previousButton.addEventListener("click", function () { showPage(currentPage - 1, true); });
  nextButton.addEventListener("click", function () { showPage(currentPage + 1, true); });
  pageSelect.addEventListener("change", function () { showPage(Number(pageSelect.value), true); });
  notesButton.addEventListener("click", function () { setNotesOpen(!notesOpen); });
  ratioSelect.addEventListener("change", function () {
    root.setAttribute("data-deck-ratio", ratioSelect.value);
  });

  document.addEventListener("keydown", function (event) {
    if (event.defaultPrevented || event.isComposing || event.altKey || event.ctrlKey || event.metaKey) return;
    if (event.target instanceof Element && (event.target.isContentEditable || event.target.closest("input, select, textarea, button, a, [role='textbox']"))) return;

    if (event.key === "ArrowRight" || event.key === "PageDown" || event.key === " ") {
      event.preventDefault();
      showPage(currentPage + 1, true);
    } else if (event.key === "ArrowLeft" || event.key === "PageUp") {
      event.preventDefault();
      showPage(currentPage - 1, true);
    } else if (event.key === "Home") {
      event.preventDefault();
      showPage(0, true);
    } else if (event.key === "End") {
      event.preventDefault();
      showPage(pages.length - 1, true);
    }
  });

  // 在所有依赖都找到后才启用分页；脚本缺失或结构不完整时保留完整长文档。
  ratioSelect.value = root.getAttribute("data-deck-ratio") || "auto";
  tools.hidden = false;
  controls.hidden = false;
  root.classList.add("deck--ready");
  controls.setAttribute("data-deck-ready", "true");
  showPage(0);
}());
