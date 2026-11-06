# 离线原图阅读器 v1

能力 ID：`html.image-viewer-v1`，当前包版本 1.1.0。默认与工具栏包共同物料化，源码与生命周期保持独立。原图由消费端提供。

```html
<a href="assets/diagram.svg" data-source-image="assets/diagram.svg"
   data-source-caption="系统结构原图">查看完整原图</a>
```

默认完整适应阅读区域，提供原始尺寸、加减缩放、滚动和鼠标拖动。普通加减键只缩放图片，浏览器 Ctrl/触摸缩放仍由浏览器负责。原生模态对话框管理焦点，Esc/关闭按钮返回触发器；方向键不会让背后的演示稿翻页。加载失败会显示原因并保留打开原图链接，关闭后可以重试。

可选 `data-source-min-width="1000"` 保留复杂图的初始阅读宽度；点击适应窗口恢复全图。缩放解除模板的物理/逻辑宽度限制；上限 8 倍且不超过 48000 CSS px，下限允许大图完整适配手机。

只接受与页面同源的 file/http/https 原图。无原生 dialog 支持时保留链接行为。支持动态触发器与幂等 `window.SuanhaiImageViewer.init()`，也可调用 `open(trigger)`。不提供图片编辑、图库或外部图片抓取。

[全部交互与验收边界](../../../../docs/html-interaction-components.md) · [直接体验](../preview/index.html)
