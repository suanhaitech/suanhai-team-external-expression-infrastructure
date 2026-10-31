# HTML 语义组件核心包 v1

状态：`implemented / experimental`

这是可被不同小组和不同页面模板复制使用的离线 HTML/CSS 基础包。它不绑定公共小组模板仓的目录结构，不包含项目事实，不需要 JavaScript、CDN 或构建步骤。包被放在网页 HTML 的 `formats/web/html/components/` 下，而不是某个具体页面模板目录下。

## 内容

- `package.yml`：包版本、入口、资源和离线约束；
- `index.yml`：Agent 按组件 ID 查找契约、定义和模板的机器可读目录；
- `foundations/`：设计令牌和 HTML 基线；
- `layout/`：容器、网格、章节和正文布局原语；
- `semantic/`：按领域分类的组件定义、模板和 JSON 契约；
- `themes/`：只覆盖设计令牌的主题；
- `examples/`：完整离线组合示例；
- `tests/`：组件检查夹具说明；
- `styles.css`：页面使用的稳定样式总入口。

| 组件 | 适用信息 |
| --- | --- |
| `content.summary` | 页面或章节摘要 |
| `status.phase` | 阶段、状态和依据 |
| `status.metric` | 有单位和口径的指标 |
| `evidence.claim` | 带核验状态的判断 |
| `evidence.source` | 来源和允许使用范围 |
| `action.next-step` | 下一步、责任人和完成标准 |

布局原语包括 `ex-container`、`ex-stack`、`ex-grid`、`ex-section` 和 `ex-prose`。样式使用 `ex-` 前缀，避免与消费端既有 CSS 类名冲突。

## 使用

将本目录复制到消费端任务的 `assets/html-components-v1/`，在 HTML 中只引入稳定的总入口：

```html
<link rel="stylesheet" href="assets/html-components-v1/styles.css" />
```

Agent 调用顺序固定为：读取 `package.yml` → 读取 `index.yml` → 按组件 ID 读取 `semantic/**/component.yml` → 读取对应 `template.html` → 按契约填充内容。复制后页面不依赖 submodule 路径，因而可以独立审阅、归档和发布。自建仓可以放在其已有的作品目录中，路径由消费端自己的规则决定。

## 适配约定

- 样式按 760px 和 1024px 固定断点调整，不用视口宽度连续缩放字体；
- 指标网格在窄屏单列；文本通过正常换行适配中英文；
- 组件保留语义 HTML，颜色不能作为唯一状态信号；
- 键盘焦点可见，用户偏好减少动画时不增加动效；
- 打印样式隐藏非必要导航，并尽量避免组件内部分页；
- 页面只引用本地 CSS，当前不提供数学公式引擎、图表运行时或自动浏览器截图。

具体契约见 `semantic/contracts/*.json`。包版本和资源入口见 `package.yml`，组件目录见 `index.yml`。
