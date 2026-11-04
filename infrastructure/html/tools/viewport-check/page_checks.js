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
    var controls = document.querySelector("[data-deck-controls], .report-nav, [data-report-nav]");
    // 底部翻页栏可在滚动到底后检查最终内容是否仍被挡住。
    // 顶部粘性导航在滚动途中覆盖正文是正常行为，不能据一次相交判为永久遮挡；
    // 长页只自动核对锚点存在，定位与焦点检查明确留给人工。
    var bar = controls && controls.matches("[data-deck-controls]") && visible(controls) ? controls.getBoundingClientRect() : null;
    var overlaps = [], overflow = [];
    elements.filter(visible).forEach(function (element) {
      var style = getComputedStyle(element), box = element.getBoundingClientRect();
      if (element.clientWidth > 0 && element.scrollWidth > element.clientWidth + 2 && style.overflowX === "visible" && style.display !== "inline") overflow.push(element.tagName.toLowerCase() + (element.id ? "#" + element.id : ""));
      // 只测可读的叶子文字/图片，避免把包围整个页面的装饰容器当成被挡内容。
      var readable = element.tagName === "IMG" || (!element.children.length && element.textContent.trim());
      if (bar && !controls.contains(element) && readable && box.bottom > bar.top + 1 && box.top < bar.bottom - 1 && box.left < bar.right && box.right > bar.left) overlaps.push(element.tagName.toLowerCase() + (element.id ? "#" + element.id : ""));
    });
    var broken = Array.from(active.querySelectorAll("img")).filter(i => !i.complete || i.naturalWidth === 0).map(i => i.getAttribute("src"));
    var ids = Array.from(document.querySelectorAll("[id]")).map(e => e.id);
    return { innerWidth: innerWidth, scrollWidth: document.documentElement.scrollWidth, innerHeight: innerHeight, scrollHeight: document.documentElement.scrollHeight,
      horizontalOverflow: document.documentElement.scrollWidth > innerWidth + 1, textOverflow: overflow,
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
