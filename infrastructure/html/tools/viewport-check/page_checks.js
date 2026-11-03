/* 只注入检查函数；不改写成品 DOM 内容，不替代用户的人工视觉验收。 */
(function () {
  function pages() { return Array.from(document.querySelectorAll("[data-deck-page]")); }
  function visible(element) {
    var style = getComputedStyle(element), box = element.getBoundingClientRect();
    return style.display !== "none" && style.visibility !== "hidden" && box.width > 0 && box.height > 0;
  }
  function choose(index) {
    var select = document.querySelector("[data-page-select]");
    if (select) { select.value = String(index); select.dispatchEvent(new Event("change", { bubbles: true })); }
    return new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  }
  function inspect() {
    var active = pages().find(p => !p.hidden) || document.body;
    var elements = Array.from(active.querySelectorAll("*"));
    var controls = document.querySelector("[data-deck-controls]");
    var bar = controls && visible(controls) ? controls.getBoundingClientRect() : null;
    var overlaps = [], overflow = [];
    elements.filter(visible).forEach(function (element) {
      var style = getComputedStyle(element), box = element.getBoundingClientRect();
      if (element.clientWidth > 0 && element.scrollWidth > element.clientWidth + 2 && style.overflowX === "visible" && style.display !== "inline") overflow.push(element.tagName.toLowerCase() + (element.id ? "#" + element.id : ""));
      // 只测可读的叶子文字/图片，避免把包围整个页面的装饰容器当成被挡内容。
      var readable = element.tagName === "IMG" || (!element.children.length && element.textContent.trim());
      if (bar && readable && box.bottom > bar.top + 1 && box.top < bar.bottom - 1 && box.left < bar.right && box.right > bar.left) overlaps.push(element.tagName.toLowerCase() + (element.id ? "#" + element.id : ""));
    });
    var broken = Array.from(active.querySelectorAll("img")).filter(i => !i.complete || i.naturalWidth === 0).map(i => i.getAttribute("src"));
    var ids = Array.from(document.querySelectorAll("[id]")).map(e => e.id);
    return { innerWidth: innerWidth, scrollWidth: document.documentElement.scrollWidth, innerHeight: innerHeight, scrollHeight: document.documentElement.scrollHeight,
      horizontalOverflow: document.documentElement.scrollWidth > innerWidth + 1, textOverflow: overflow,
      navigationOverlap: overlaps, brokenImages: broken, duplicateIds: ids.filter((id, i) => ids.indexOf(id) !== i),
      pageId: active.id || null, pageCount: pages().length || 1,
      pageOptions: document.querySelector("[data-page-select]") ? document.querySelector("[data-page-select]").options.length : null };
  }
  window.SuanhaiPageChecks = { choose: choose, inspect: inspect, pageCount: function () { return pages().length || 1; } };
}());
