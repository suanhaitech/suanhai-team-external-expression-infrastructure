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
- `html.container.presentation-deck-v1` 和七个 `html.single-page.*` 页面模板
- `html.semantic-components-v1`
- `html.responsive-layout-v1`
- `html.runtime-kit-v1`
- `html.materialize`
- `html.viewport-check`
- `html.pdf-export`

运行时包是可选项；没有选择它的页面不会自动带有公式渲染、显示模式、全屏或打印入口。`html.pdf-export` 是制作工具，不是页面内按钮。项目内容、事实核对、来源和发布授权始终由消费端维护。

`html.project-report-v1` 适合纵向连续阅读的长页报告；`html.presentation-deck-v1` 适合逐页讲解，底部提供页码、上一页/下一页和进度，支持键盘翻页、手动比例、讲者备注和逐页打印。两者位于 `templates/presets/`，作为完整组合预设由 `expression.html-production` 选择；逐页容器和单页模板也可以通过 `html.materialize` 按顺序组合。完整预设保留用于兼容旧任务和快速起稿。

详细的工作流与页面组合规则见 [`docs/html-framework.md`](../../docs/html-framework.md)。
