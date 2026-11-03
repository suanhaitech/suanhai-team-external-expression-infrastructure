# 单页模板契约

单页模板是可嵌入 HTML 容器的逻辑页面。当前十种模板均已登记为 Manifest 能力，可由 `html.materialize` 按顺序装入兼容容器。

```text
single-page/
├── cover/       封面：主题、对象、沟通场景与核心判断
├── agenda/      目录：阅读路线与章节顺序，不承载正文
├── transition/  章节过渡：章节标题、关键问题或阶段切换
├── content/     正文：证据、方法等内容版式变体
├── closing/     结尾：结论、下一步、负责人或确认事项
└── appendix/    附录：来源、术语、长证据与补充材料
```

指标、对比、流程/架构、公式和方法是正文版式变体，不提升为页面角色。连续滚动和逐页演示是容器，放在 `templates/containers/`；它们决定页面如何被阅读，不决定页面表达什么。

## 页面包契约

每个单页包应包含：

```text
<variant>/
├── template.yml
├── page.html
├── styles.css
└── README.md
```

`page.html` 必须恰有一个可识别的 `<section>` 根节点，不能包含 `<html>`、`<head>` 或 `<body>`。以稳定且唯一的 `data-slot` 标记消费端内容；不写入真实项目事实、外部图片、远程字体或本地机器路径。样式应限制在本变体的命名空间下，避免多个单页组合时互相污染。

`template.yml` 的 `id` 与 Manifest 能力 ID 一致，并记录角色、变体、插槽、离线属性和兼容容器族。物料化前会校验元数据、HTML 根节点、插槽、页码标记和远程资源边界。

页面在连续滚动容器中允许自然增高；逐页容器可设置首选比例，但不能为凑比例缩小文字、隐藏溢出或裁切内容。目录与附录都可以按实际内容增删条目。窄屏下布局应转为单列，来源和长标题必须可读。

## 能力元数据示例

```yaml
# 页面包元数据必须与 Manifest 能力 ID 一致。
id: html.single-page.content.example-v1
kind: single-page-template
version: 1.0.0
role: content
variant: evidence
entrypoint: page.html
stylesheet: styles.css
offline: true
network_dependencies: []
slots:
  - title
  - evidence-rows
compatible_container_families:
  - paged-deck
  - continuous-scroll
```

页面角色和变体是资产分类，不是独立工作流。当前 `html.container.presentation-deck-v1` 负责逐页组合、底部翻页、比例选择和打印；页面顺序由重复的 `--page-id` 参数决定。工具会复制每个页面的 CSS 并记录来源；项目内容仍由消费端 Agent 填充 `data-slot`。

当前 MVP 只支持 `paged-deck` 容器，不接受单页组合中的 `--component-id`。单页还没有通用组件插槽；若直接把语义组件片段插到页面外层，容易破坏页面布局，因此工具明确拒绝该组合。

项目经理统一主讲的周期汇报可组合 `content/project-overview-v1`、可重复的 `content/workstream-update-v1` 和 `content/dependencies-v1`，再复用封面、行动页和来源附录。它们承载总体判断、各线证据与跨线影响，不限定主线数量或总页数。内容映射和试用方法见 [项目总汇报设计](../../../../docs/project-progress-report-design.md)。

## 本地预览

预览入口位于 [`preview/index.html`](preview/index.html)。在仓库根运行 `python -m http.server 8000`，再访问 `/infrastructure/html/templates/single-page/preview/`。它用于设计比较，不是生产装配器。
