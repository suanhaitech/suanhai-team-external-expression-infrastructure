# HTML 页面基础设施

这里存放 HTML 制作工作流会组合使用的页面资产和专用工具。主流程入口位于 [`workflows/html/production/`](../../workflows/html/production/ENTRYPOINT.md)，能力是否可调用以仓库根目录的 `manifest.yml` 为准。

```text
infrastructure/html/
├── templates/         容器、单页模板和完整组合预设
├── components/       语义组件包及其契约、示例和必要样式
├── styles/           跨页面复用的基础、响应式和打印样式包
├── runtime-kits/     页面内公式和交互运行时，随页面本地化
└── tools/            HTML 物料化、视口检查和 PDF 导出工具
```

这几类资源有明确职责，但不要求每个 CSS 或 JavaScript 文件都独立发包。组件可以携带它运行所需的样式，运行时包携带工具栏样式和脚本，页面模板保留模板专属视觉。物料化工具将所选能力复制到消费端作品版本目录，确保页面离线且不依赖读者工作区里的 submodule。

当前可调用包为：

- `html.project-report-v1`
- `html.presentation-deck-v1`
- `html.container.presentation-deck-v1` 和按角色登记的 `html.single-page.*` 页面模板
- `html.semantic-components-v1`
- `html.responsive-layout-v1`
- `html.runtime-kit-v1`
- `html.materialize`
- `html.viewport-check`
- `html.pdf-export`

新页面默认配齐工具栏/公式与原图阅读器，运行时参数只用于增量添加；分页容器将比例、备注与工具栏统一到底部悬浮控制栏。Agent 主动介绍功能与限制，无需用户逐项指定安装。`html.pdf-export` 是制作工具，不是页面内按钮。项目内容、事实核对、来源和发布授权始终由消费端维护。

`html.project-report-v1` 适合纵向连续阅读的长页报告；`html.presentation-deck-v1` 适合逐页讲解，底部提供页码、上一页/下一页和进度，支持键盘翻页、手动比例、讲者备注和逐页打印。两者位于 `templates/presets/`，作为完整组合预设由 `expression.html-production` 选择；逐页容器和单页模板也可以通过 `html.materialize` 按顺序组合。完整预设保留用于兼容旧任务和快速起稿。

详细的工作流与页面组合规则见 [`docs/html-framework.md`](../../docs/html-framework.md)。

当前由工作流识别的任务画像见 [`scenarios/catalog.json`](../../scenarios/catalog.json)：课程学习与面向合作方的项目进展沟通。场景会影响内容组织和验收标准；它不是 HTML 模板或新的工作流能力。

## 课程实践提炼的复用入口

新增技术插图封面、阶段演进、数字观察、定义映射、两栏对照、图文分析和关键词矩阵。`html.presentation-foundation-v1` 提供公共页框，`--theme editorial-warm` 选择暖白主题，`html.image-viewer-v1` 默认提供原图适配、缩放与拖动阅读。新稿使用完整 `page-plan.json` 保持稳定页面 ID、来源和目录页码一致；局部修订复用同任务只读基线。`html.viewport-check` 可使用本机 CDP 做整稿逐页检查、交互和联系表，`html.source-assets` 登记本地素材。规则与全部候选归属见 [课程资产提炼](../../docs/course-reusable-assets.md)。

[交互组件、默认装配与验收边界](../../docs/html-interaction-components.md) · [直接体验](runtime-kits/preview/index.html)
