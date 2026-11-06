/* 只注入检查函数；不改写成品 DOM 内容，不替代用户的人工视觉验收。 */
(function () {
  function pages() { return Array.from(document.querySelectorAll("[data-deck-page]")); }
  function visible(element) {
    var style = getComputedStyle(element), box = element.getBoundingClientRect();
    return style.display !== "none" && style.visibility !== "hidden" && Number(style.opacity) > 0 && box.width > 0 && box.height > 0;
  }
  function intersect(a, b) {
    return {left: Math.max(a.left, b.left), top: Math.max(a.top, b.top), right: Math.min(a.right, b.right), bottom: Math.min(a.bottom, b.bottom)};
  }
  // DOM 矩形包含滚动区外的内容；只有真正处于裁切区内的相交才算被导航遮挡。
  // fixed 元素通常相对视口定位，不受普通 overflow 祖先裁切；有 transform 等
  // 固定定位包含块时才从该包含块开始裁切，不能因此漏掉真正悬浮在底栏下的文字。
  function visibleBox(element) {
    var box = intersect(element.getBoundingClientRect(), {left: 0, top: 0, right: innerWidth, bottom: innerHeight});
    var fixed = element.closest ? element : null;
    while (fixed && getComputedStyle(fixed).position !== "fixed") fixed = fixed.parentElement;
    var clipFrom = null;
    if (fixed) {
      for (var parent = fixed.parentElement; parent; parent = parent.parentElement) {
        var ps = getComputedStyle(parent);
        if (ps.transform !== "none" || ps.perspective !== "none" || ps.filter !== "none" || /paint|layout|strict|content/.test(ps.contain)) { clipFrom = parent; break; }
      }
    }
    var clipping = !fixed;
    for (var ancestor = element.parentElement; ancestor; ancestor = ancestor.parentElement) {
      if (ancestor === clipFrom) clipping = true;
      var style = getComputedStyle(ancestor);
      if (style.display === "none" || style.visibility === "hidden" || Number(style.opacity) === 0) return {left: 0, top: 0, right: 0, bottom: 0};
      if (!clipping) continue;
      var rect = ancestor.getBoundingClientRect();
      var sx = ancestor.offsetWidth ? rect.width / ancestor.offsetWidth : 1;
      var sy = ancestor.offsetHeight ? rect.height / ancestor.offsetHeight : 1;
      var left = rect.left + ancestor.clientLeft * sx, top = rect.top + ancestor.clientTop * sy;
      if (/auto|scroll|hidden|clip/.test(style.overflowX)) { box.left = Math.max(box.left, left); box.right = Math.min(box.right, left + ancestor.clientWidth * sx); }
      if (/auto|scroll|hidden|clip/.test(style.overflowY)) { box.top = Math.max(box.top, top); box.bottom = Math.min(box.bottom, top + ancestor.clientHeight * sy); }
    }
    return box;
  }
  function choose(index) {
    var select = document.querySelector("[data-page-select]");
    if (select) { select.value = String(index); select.dispatchEvent(new Event("change", { bubbles: true })); }
    return new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  }
  function inspect() {
    var active = pages().find(p => !p.hidden) || document.body;
    var elements = Array.from(active.querySelectorAll("*"));
    var controls = document.querySelector("[data-deck-controls], .report-nav, [data-report-nav]");
    // 底部翻页栏可在滚动到底后检查最终内容是否仍被挡住。
    // 顶部粘性导航在滚动途中覆盖正文是正常行为，不能据一次相交判为永久遮挡；
    // 长页只自动核对锚点存在，定位与焦点检查明确留给人工。
    var bar = controls && controls.matches("[data-deck-controls]") && visible(controls) ? visibleBox(controls) : null;
    if (bar && (bar.right <= bar.left || bar.bottom <= bar.top)) bar = null;
    var overlaps = [], overflow = [];
    elements.filter(visible).forEach(function (element) {
      var style = getComputedStyle(element), box = element.getBoundingClientRect();
      if (element.clientWidth > 0 && element.scrollWidth > element.clientWidth + 2 && style.overflowX === "visible" && style.display !== "inline") overflow.push(element.tagName.toLowerCase() + (element.id ? "#" + element.id : ""));
      // 只测可读的叶子文字/图片，避免把包围整个页面的装饰容器当成被挡内容。
      var readable = element.tagName === "IMG" || (!element.children.length && element.textContent.trim());
      if (bar && !controls.contains(element) && readable) {
        var overlap = intersect(visibleBox(element), bar);
        if (overlap.bottom > overlap.top + 1 && overlap.right > overlap.left + 1) overlaps.push(element.tagName.toLowerCase() + (element.id ? "#" + element.id : ""));
      }
    });
    // 组合页的正文在内部单页滚动；仍报告阅读密度，不能通过转移滚动层制造全通过。
    var readingAreas = active.matches && active.matches("[data-deck-page]") ? [active].concat(Array.from(active.children).filter(e => e.hasAttribute("data-single-page-role"))) : [];
    var pageOverflow = readingAreas.filter(e => e.scrollHeight > e.clientHeight + 2).map(e => ({id: active.id || active.getAttribute("data-page-id") || null, scrollHeight: e.scrollHeight, clientHeight: e.clientHeight}));
    var broken = Array.from(active.querySelectorAll("img")).filter(i => !i.complete || i.naturalWidth === 0).map(i => i.getAttribute("src"));
    var ids = Array.from(document.querySelectorAll("[id]")).map(e => e.id);
    return { innerWidth: innerWidth, scrollWidth: document.documentElement.scrollWidth, innerHeight: innerHeight, scrollHeight: document.documentElement.scrollHeight,
      horizontalOverflow: document.documentElement.scrollWidth > innerWidth + 1, textOverflow: overflow,
      pageVerticalOverflow: pageOverflow,
      navigationOverlap: overlaps, navigationCoverage: bar ? "visible-navigation" : "not-run",
      navigationReason: bar ? null : "没有可检查的底部翻页栏；顶部粘性导航的滚动定位遮挡需人工核对",
      brokenImages: broken, duplicateIds: ids.filter((id, i) => ids.indexOf(id) !== i),
      pageId: active.id || null, pageCount: pages().length || 1,
      pageOptions: document.querySelector("[data-page-select]") ? document.querySelector("[data-page-select]").options.length : null };
  }
  function anchors() {
    var nav = document.querySelector(".report-nav, [data-report-nav]");
    if (!nav) return { status: "not-run", reason: "产物没有长页导航" };
    var links = Array.from(nav.querySelectorAll('a[href^="#"]'));
    if (!links.length) return { status: "not-run", reason: "长页导航没有本页锚点" };
    var missing = links.map(a => a.getAttribute("href").slice(1)).filter(id => !document.getElementById(decodeURIComponent(id)));
    return { status: missing.length ? "fail" : "pass", tested: links.length, missing: missing,
      scope: "核对导航目标存在；滚动定位、焦点与标题遮挡仍需人工检查" };
  }
  window.SuanhaiPageChecks = { choose: choose, inspect: inspect, anchors: anchors, pageCount: function () { return pages().length || 1; } };
}());
