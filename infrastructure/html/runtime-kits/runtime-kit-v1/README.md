# HTML Runtime Kit v1

能力 ID：`html.runtime-kit-v1`，当前包版本 1.1.0。

默认随新 HTML 物料化，提供本地 KaTeX 公式、自动/窄屏/平板/桌面布局、全屏与保存 PDF 入口。独立长页使用顶部工具栏；分页容器把同一组真实控件组合到底部。手机保留按钮文字与至少 44px 高度，不把功能藏成难辨的图标。

- 公式使用 `<span data-math="x^2">x^2</span>`，块公式加 `data-math-display="block"`。锁定 KaTeX 0.16.25，随包字体和 MIT 许可完全离线；失败保留 TeX。
- 全屏模式的状态跟随浏览器，支持进入/退出；权限拒绝或 API 缺失时显示原因和重试建议。
- 保存 PDF 打开浏览器打印对话框，演示稿默认打印全部页面、隐藏控件和备注。用户在对话框选择另存为 PDF；确定性文件继续使用 `html.pdf-export`。
- `window.SuanhaiRuntime.init()` 可重复调用，`renderMath()` 可处理新增公式，`setMode(mode)` 写入公开布局状态。模板自行解释 `data-layout-mode`，运行时不耦合正文类名。
- 通过 `suanhai:runtime-ready` 与 `suanhai:layout-change` 通知容器；容器可以移动现有 DOM 组合界面，不重写动作。

模板各声明一次 `<!-- SUANHAI_RUNTIME_STYLESHEETS -->`、`<!-- SUANHAI_RUNTIME_TOOLBAR -->`、`<!-- SUANHAI_RUNTIME_SCRIPTS -->`。物料化器负责相对资源路径与来源记录。底层不启用运行时的兼容 API 仍保留；新任务的默认策略由物料化入口决定。

[全部交互、默认装配与验收边界](../../../../docs/html-interaction-components.md) · [直接体验](../preview/index.html)
