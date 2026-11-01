# Responsive Layout v1

这是网页呈现形式下可复用的响应式布局基础包。它只提供布局规则、设计令牌和机器可读契约，不包含项目事实、品牌内容或远程运行时依赖。

## 目标

- 在窄竖屏、平板、桌面宽屏和横屏短高度设备上保持内容可读；
- 用 CSS 媒体查询和容器约束适配视口比例，不要求页面脚本读取屏幕尺寸；
- 为长文本、图片、表格、代码和组件插槽提供不会把页面撑出视口的默认边界；
- 为打印媒体提供独立的分页和颜色规则。

## 使用

把 `styles.css` 复制到消费端 HTML 产物的本地资源目录，并在页面中引用：

```html
<meta name="viewport" content="width=device-width, initial-scale=1" />
<link rel="stylesheet" href="assets/html-responsive-layout-v1/styles.css" />
```

页面容器可以使用下列语义类：

- `.responsive-shell`：页面根容器和安全内边距；
- `.responsive-grid`：默认双栏、窄屏自动单栏的网格；
- `.responsive-media`：图片、视频和 SVG 的最大尺寸约束；
- `.responsive-table`：窄屏可横向查看的表格容器；
- `.responsive-code`：长代码或命令的可滚动容器；
- `.responsive-cluster`：窄屏下自动换行的操作或标签组。

组件仍需遵守自己的契约；这些类不能替代内容、事实、来源或发布评审。

## 适配策略

布局优先根据可用宽度和容器大小变化。`max-aspect-ratio` 只处理窄竖屏，`min-aspect-ratio` 和短高度规则处理宽屏或横屏设备；不能用固定的设备型号判断布局。CSS 中的 `min-width: 0`、`max-inline-size: 100%` 和 `overflow-wrap: anywhere` 用来阻止长标题、URL 和代码撑破网格。

`html.viewport-check` 可以在 390x844、768x1024、1366x768、1920x1080 和 A4 视口上检查水平溢出。检查工具不可用浏览器时会输出 `not-run`，不把静态结果写成视觉通过。

## 文件

- `package.yml`：包身份、离线约束和支持的视口；
- `index.yml`：布局契约和类目录；
- `styles.css`：可复制的 CSS 入口；
- `foundations.css`：令牌、基础容器和内容边界；
- `media.css`：宽度、比例、方向和打印规则。
