# 离线原图阅读器 v1

`html.image-viewer-v1` 是可选运行时包，可与 `html.runtime-kit-v1` 共同物料化。原图由消费端提供，不包含课程原文、商业图片或外部网络依赖。

引入 `runtime.css` 和 defer 脚本 `runtime.js`，将完整原图链接标记为：

```html
<a href="assets/diagram.svg" data-source-image="assets/diagram.svg"
   data-source-caption="系统结构原图" data-source-min-width="1000">查看完整原图</a>
```

`data-source-min-width` 可选，复杂图在手机上可保留阅读宽度并横向滚动。默认按窗口宽度完整展示，图片不裁切。关闭按钮、Escape、焦点返回与方向键隔离已实现；无原生 dialog 支持时保留链接行为。支持动态插入触发器和重复调用 `window.SuanhaiImageViewer.init()`；同一页面共用一个阅读器。

只接受与页面同源的 file/http/https 图片。加载失败会显示状态，不虚报成功。不提供编辑图片、图库、缩放按钮或版权授权；素材来源和使用边界应登记在消费端。自动检查可以验证阅读器打开/关闭及焦点、键盘行为，不能代替人工确认原图可读性。
