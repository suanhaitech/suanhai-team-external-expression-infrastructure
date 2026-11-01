# HTML Runtime Kit v1

能力 ID：`html.runtime-kit-v1`

这是物料化到消费端 HTML 页面中的离线运行时包，提供四项页面内能力：

- **数学公式**：页面使用 `<span data-math="x^2" aria-label="x squared">x^2</span>` 或 `data-math-display="block"` 标记公式。随包锁定的 KaTeX 0.16.25 在本地渲染；引擎缺失或公式错误时保留 TeX 源文本，不伪造成功。
- **显示模式**：工具栏提供“自动、窄屏、平板、桌面”四种当前页面布局密度。自动模式遵循 CSS 媒体查询，手动模式只改变页面布局规则，不模拟浏览器 viewport。
- **全屏模式**：工具栏的“全屏”按钮调用浏览器 Fullscreen API；浏览器不支持时按钮会禁用，按 `Esc` 可以退出全屏。
- **PDF 入口**：工具栏的“保存 PDF”按钮打开浏览器 `window.print()` 对话框，用户可以选择“保存为 PDF”。确定性 PDF 文件仍使用 `html.pdf-export`，因为静态页面不能直接调用消费端 Python 工具。

桌面工具栏将显示模式、页面视图和页面输出分成三个区域；窄屏下改用模式下拉框，并将全屏和保存 PDF 操作排成两列，避免模式按钮挤压或产生横向溢出。
工具栏和报告页的视觉方向参考 [`docs/html-runtime-toolbar-ui-concept.png`](../../../../docs/html-runtime-toolbar-ui-concept.png)。

包不访问 CDN、不依赖网络，包含 KaTeX MIT 许可证和本地字体。`@media print` 会隐藏工具栏。`runtime.js` 初始化幂等，重复加载不会重复绑定。

物料化后页面入口会自动包含：

```html
<link rel="stylesheet" href="assets/html-runtime-kit-v1/runtime.css" />
<link rel="stylesheet" href="assets/html-runtime-kit-v1/math/katex.min.css" />
<script src="assets/html-runtime-kit-v1/math/katex.min.js"></script>
<script src="assets/html-runtime-kit-v1/runtime.js"></script>
```

启用运行时包的页面模板需要各声明一次 `<!-- SUANHAI_RUNTIME_STYLESHEETS -->`、`<!-- SUANHAI_RUNTIME_TOOLBAR -->` 和 `<!-- SUANHAI_RUNTIME_SCRIPTS -->` 插槽。物料化工具会把本地 CSS、工具栏容器和脚本填入页面；项目事实和公式源文本仍由消费端任务负责。未启用运行时包时，物料化工具会清空这些标记并保持旧模板兼容。
