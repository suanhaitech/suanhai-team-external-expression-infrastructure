const examples = [
  { role: "content", variant: "project-status-v1", title: "正文 / 项目状态面板", description: "阶段、周期计划与带口径进度" },
  { role: "content", variant: "workstream-research-v1", title: "正文 / 研究主题与进展", description: "主题、本期结果与问题回答" },
  { role: "content", variant: "conclusion-evidence-v1", title: "正文 / 结论与证据", description: "逐条判断、证据入口及限制" },
  { role: "content", variant: "workstream-plan-v1", title: "正文 / 下周期计划", description: "任务、交付与核对方式" },
  { role: "cover", variant: "technical-editorial-v1", title: "插图封面 / Technical Editorial", description: "主题、问题、本地插图与署名" },
  { role: "content", variant: "stages-v1", title: "正文 / Stages", description: "2–4个阶段的演进" },
  { role: "content", variant: "observation-v1", title: "正文 / Observation", description: "观察、口径与问题" },
  { role: "content", variant: "definition-mapping-v1", title: "正文 / Definition Mapping", description: "定义与问题响应" },
  { role: "content", variant: "comparison-v1", title: "正文 / Comparison", description: "同维度并列分析" },
  { role: "content", variant: "figure-analysis-v1", title: "正文 / Figure Analysis", description: "本地图像与来源分析" },
  { role: "content", variant: "keyword-grid-v1", title: "正文 / Keyword Grid", description: "等权判断与关键词" },
  { role: "cover", variant: "editorial-v1", title: "封面 / Editorial", description: "主题、读者与核心判断" },
  { role: "agenda", variant: "route-v1", title: "目录 / Route", description: "静态内容路线，不切换页面" },
  { role: "transition", variant: "statement-v1", title: "章节过渡 / Statement", description: "章节标题与关键问题" },
  { role: "content", variant: "evidence-v1", title: "正文 / Evidence", description: "判断、依据与表达边界" },
  { role: "content", variant: "method-v1", title: "正文 / Method", description: "问题、方法、证据与判断" },
  { role: "content", variant: "project-overview-v1", title: "正文 / 项目总览", description: "总体判断、周期变化与里程碑影响" },
  { role: "content", variant: "workstream-update-v1", title: "正文 / 主线更新", description: "目标、结果、证据条件与下期结果" },
  { role: "content", variant: "dependencies-v1", title: "正文 / 跨线协作", description: "输入输出、项目影响与协作请求" },
  { role: "closing", variant: "action-v1", title: "结尾 / Action", description: "结论与后续行动" },
  { role: "appendix", variant: "source-register-v1", title: "附录 / Source Register", description: "来源、版本与引用范围" },
];

function addStylesheet(path) {
  const link = document.createElement("link"); link.rel = "stylesheet"; link.href = path;
  document.head.append(link);
}

async function loadExamples() {
  // 主题只替换令牌；页面结构保持一致。URL参数仅接受显式白名单。
  const requestedTheme = new URLSearchParams(location.search).get("theme");
  const theme = ["editorial-warm", "editorial-green"].includes(requestedTheme) ? requestedTheme : "editorial-warm";
  addStylesheet("../../../components/core-v1/foundations/tokens.css");
  addStylesheet(`../../../components/core-v1/themes/${theme}.css`);
  addStylesheet("../../../components/core-v1/semantic/semantic.css");
  addStylesheet("../../../styles/project-report-v1/styles.css");
  addStylesheet("../../../styles/presentation-v1/styles.css");
  const list = document.querySelector("#preview-list");
  list.replaceChildren();

  for (const example of examples) {
    const packagePath = `../${example.role}/${example.variant}`;
    const response = await fetch(`${packagePath}/page.html`);
    if (!response.ok) throw new Error(`载入失败：${example.role}/${example.variant}`);

    const markup = await response.text();
    const parsed = new DOMParser().parseFromString(markup, "text/html");
    const page = parsed.body.firstElementChild;
    if (!page || parsed.body.children.length !== 1) {
      throw new Error(`页面片段根节点不唯一：${example.role}/${example.variant}`);
    }

    // 动态插入片段后，URL原本会相对预览页解析；必须保留页面包的资源基准。
    const assetBase = new URL(`${packagePath}/`, window.location.href);
    for (const node of page.querySelectorAll("[src], [href]")) {
      for (const attribute of ["src", "href"]) {
        const value = node.getAttribute(attribute);
        if (value && !value.startsWith("#")) node.setAttribute(attribute, new URL(value, assetBase).href);
      }
    }
    const stylesheet = document.createElement("link");
    stylesheet.rel = "stylesheet";
    stylesheet.href = `${packagePath}/styles.css`;
    document.head.append(stylesheet);

    const item = document.createElement("article");
    item.className = "preview-item";
    const caption = document.createElement("p");
    caption.className = "preview-item__caption";
    const title = document.createElement("strong");
    title.textContent = example.title;
    const description = document.createElement("span");
    description.textContent = example.description;
    caption.append(title, description);

    const frame = document.createElement("div");
    frame.className = "preview-item__page";
    frame.append(document.importNode(page, true));
    item.append(caption, frame);
    list.append(item);
  }
}

loadExamples().catch((error) => {
  const status = document.createElement("p");
  status.className = "preview-status";
  status.setAttribute("role", "alert");
  status.textContent = `${error.message}。请通过本地 HTTP 服务打开预览页。`;
  document.querySelector("#preview-list").replaceChildren(status);
});
