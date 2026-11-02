# 多页 HTML 演示稿设计

`html.presentation-deck-v1` 从用户提供的八份历史 HTML 中归纳表达模式，并重新实现通用模板。样例仅作静态设计参考：项目事实、实验数据、图表图片、项目代码和机器路径均未进入共享资产。

## 从样例吸收什么

| 需求或模式 | 本轮实现 |
| --- | --- |
| 多页内容按讲解节奏呈现 | 一份 HTML 中多个 `data-deck-page` 逻辑页；可增删、重排 |
| 底部统一翻页 | 上一页、页码选择、当前页/总页数、下一页、进度条；首尾禁用 |
| 键盘操作 | 方向键、Page Up/Page Down、空格、Home/End；不截获表单等交互元素 |
| 结论先行、主画面保持简洁 | 封面、核心判断、主线进展、方法路径、证据边界、下一步六类页面结构 |
| 长说明按需查看 | 当前页讲者备注；详细证据也可另建附录页 |
| 来源与口径可追溯 | 每页来源脚注和资料日期插槽 |
| 屏幕与纸张各有阅读方式 | 窄画布单栏；屏幕仅显示当前页，打印显示全部逻辑页 |

全屏、公式、显示模式和浏览器保存 PDF 继续复用 `html.runtime-kit-v1`；确定性 PDF 文件继续由 `html.pdf-export` 生成。本轮没有再写一套同类控件。

## 与现有分层的关系

- `workflows/html/production/` 仍是统一主工作流，负责对齐“连续阅读”或“逐页讲解”的交付方式，没有新增子工作流。
- `infrastructure/html/templates/presets/presentation-deck-v1/` 提供页面骨架及本模板需要的视觉和分页逻辑。
- 已有语义组件、响应式样式、公式与工具栏运行时作为独立能力选配。
- `html.materialize` 保留 `html.presentation-deck-v1` 完整预设调用，并新增 `--container-id` 与有序重复 `--page-id` 的装配模式；公共模板仓与采用自定义目录的既有消费端都可使用。
- 内容、来源、事实核对与授权仍由消费端维护。

分页逻辑随 `html.container.presentation-deck-v1` 容器维护，完整预设保留自己的兼容副本。单页 CSS 依据演示画布宽度切换布局，普通视口的媒体断点也保留，便于页面独立预览和后续使用其他容器。

## 比例和打印的工程边界

画布比例是首选尺寸，不能通过缩小所有文字或隐藏溢出来凑比例。内容超长时页面自然增长，制作 Agent 应把多项组件分配到对应主题页，长证据移到续页或附录。

打印从每个逻辑页开始新纸页；超长内容允许继续到下一张纸。因此浏览器显示的逻辑页数不必等于 PDF 的纸张页数。要求一页一纸时，应在制作阶段拆页，并检查最终 PDF。

讲者备注会随 HTML 交付，不能作为隐藏机密资料的容器。备注使用 DOM 的 `textContent` 显示，没有复制样例中的 HTML 字符串恢复、内联项目大图或写死的本地存储逻辑。

## 检查入口

```text
python -m unittest tests.test_html_presentation_deck -v
python -m unittest tests.test_html_materialize tests.test_html_production_docs -v
ruby scripts/validate_manifest.rb
```

浏览器测试使用仓内 PDF 工具已有的本地 HTTP 和 DevTools 协议，对临时装配的完整页面检查翻页、边界、页码、键盘、备注、各视口及模式、打印和禁用 JavaScript 后的可读性。没有本机浏览器时明确跳过，不把文件契约检查当成视觉验收。
