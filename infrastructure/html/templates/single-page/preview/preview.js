const examples = [
  { role: "cover", variant: "editorial-v1", title: "封面 / Editorial", description: "主题、读者与核心判断" },
  { role: "agenda", variant: "route-v1", title: "目录 / Route", description: "静态内容路线，不切换页面" },
  { role: "transition", variant: "statement-v1", title: "章节过渡 / Statement", description: "章节标题与关键问题" },
  { role: "content", variant: "evidence-v1", title: "正文 / Evidence", description: "判断、依据与表达边界" },
  { role: "content", variant: "method-v1", title: "正文 / Method", description: "问题、方法、证据与判断" },
  { role: "closing", variant: "action-v1", title: "结尾 / Action", description: "结论与后续行动" },
  { role: "appendix", variant: "source-register-v1", title: "附录 / Source Register", description: "来源、版本与引用范围" },
];

async function loadExamples() {
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
