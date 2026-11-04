# `expression.html-production` 工作流入口

本入口是消费端 Agent 执行 HTML 制作任务的协议。它可以被公共模板仓库或既有仓库中的 Agent 读取；它不要求消费端采用固定目录，但要求遵守消费端根 `AGENTS.md` 的工作边界。

本入口作为独立顶层共享能力调用时，开始前按消费端总 Harness 和 [submodule 版本协议](../../../docs/submodule-consumer-versioning.md) 运行一次预检；若根 Harness 已为本次请求运行，则复用其快照。整条 HTML 制作工作流及它通过 `uses` 调用的任务循环、模板、组件、运行时和检查能力都固定使用该完整 SHA，不在节点间重复查询。用户在同一会话中另起独立任务/能力或新会话恢复时重新预检。远端 `main` 与 gitlink 不同且本地检查通过时报告两个 SHA，并暂停等待用户选择暂缓并继续固定版本，或进入受控更新；候选差异不代表已验收，不能在当前 HTML 工作流中途切换版本。

## 启动方式

用户可以直接向自己常用的 Agent 发送以下请求：

> 我需要制作一个 HTML 对外表达页面。请先读取当前仓库的 `AGENTS.md`、基础设施 submodule 的 `manifest.yml` 和 `workflows/html/production/WORKFLOW.md`，不要直接写 HTML。先登记任务，读取我提供的材料，向我提问并对齐受众、用途、范围、来源和完成标准；得到确认后再选择已实现模板和组件，按版本生成、预览、检查并等待我评审。

Agent 应把这段请求解释为“启动工作流”，而不是用户已经授权提交、推送或发布。

任务澄清时先从 [`scenarios/catalog.json`](../../../scenarios/catalog.json) 识别表达场景，再读取场景画像。当前包括课程学习与面向合作方的项目进展沟通；两者都走本 HTML 主工作流，但学习目标、内容组织和验收重点不同。选择页面资产前，Agent 必须把画像转成可审阅的逐页计划，说明页面目标、核心信息、来源/证据、候选资产和场景验收信号，并取得用户确认。场景 ID 传给物料化工具并记录在作品元数据中；场景不会自动决定 HTML 长页或逐页容器、主题样式或交互。

课程简报还要记录受众已有基础、理解深度和时间预算。逐页计划覆盖当前整稿，使用稳定页面 ID；问题与后文回应通过 `responds_to` 关联，目录和显示页码从顺序派生。正文、默认隐藏备注和附录分别组织，必要条件保留在正文，完整来源通过 source-map 追溯；不要强制每页显示来源小字。中性记录入口见 [records/README.md](../../../infrastructure/html/examples/records/README.md)。

项目周期汇报默认由项目经理统一主讲。读取各线授权材料和上期计划，先组织项目总体变化，再组织主线结果/证据/限制、跨线影响、协作请求和下期目标。各主线负责人核验专业事实，项目经理检查整体叙事与口径；缺少基线、未收到更新或未核验的内容显式标注。页面映射和验收要求以项目场景画像为准，不固定三条主线或总页数。

新任务默认采用 `html.container.presentation-deck-v1` + `page-plan.json` + `html.single-page.*` 分页组合，服务现场逐页讲解；用户明确要求连续阅读、传阅或查阅时考虑 `html.project-report-v1`；现场讲解或逐页呈现可以继续使用兼容预设 `html.presentation-deck-v1`，也可以选择 `html.container.presentation-deck-v1`，再按顺序传入 `--page-id html.single-page...` 组合封面、目录、章节过渡、内容页、结尾和附录。演示稿必须使用页面底部的页码选择、上一页和下一页控件，不能用顶部导航切换页。容器自身负责翻页和逐页打印；物料化默认装配 `html.runtime-kit-v1` 与 `html.image-viewer-v1`，将显示、比例、备注、全屏和 PDF 入口收拢为底部控制栏。

Agent 主动推荐资产，只提影响用途、范围或授权的关键问题，复用本轮已有认可。分页/长页与空白模板/已填写报告分别对齐；填写规则见[模板填写与复用协议](../../../infrastructure/html/templates/FILLING.md)。计划记录候选与选用资产、定制理由和验收信号。

整稿制作优先使用 `--page-plan <相对路径>`，与 `--page-id` 互斥。局部修订使用完整清单及 `--baseline-version v001 --replace-page <稳定 ID>`，先预览差异再应用；非目标页继承并检查，基线不能改写。局部认可不等于全稿验收；未制作内容明确占位，暂停复用任务循环的 `pause` / `resume`。

复用公共页框 `html.presentation-foundation-v1` 和可选 `--theme editorial-warm`；原图阅读器默认就绪，为本地原图链接添加 `data-source-image` 即可使用。原图与衍生图按 `html.source-assets` 预览、登记、核验，不把来源描述等同使用授权。演示稿评审使用整稿检查和可选联系表，不只截图首页；具体参数与边界见主流程。

## 读取顺序

1. 消费端根 `AGENTS.md`；
2. 消费端 `README.md`、`context/`、`tasks/`、`reports/` 或仓库自身规定的作品目录；
3. submodule 的 `manifest.yml`；
4. 本工作流 `WORKFLOW.md`；
5. `scenarios/catalog.json` 及匹配场景画像；没有适用画像时说明未分类，不得将媒介或容器当作场景；
6. 被选择的模板、组件、运行时包和工具入口；组件包按 `package.yml` → `index.yml` → 组件 `component.yml` → `template.html` 的顺序读取，运行时包按 `package.yml` → `index.yml` → 入口和资源读取；物料化使用 `html.materialize`，先预览并核对计划摘要，再显式应用；
7. 当前任务的 `task.json`、`sources.yml` 和已有版本。

如果 Manifest、gitlink、submodule HEAD 或工作区状态不一致，先停止并报告，不修复或升级依赖。

## 阶段路由

```text
create/continue task
    ↓
clarify brief and sources
    ↓
align with user
    ↓
confirm full page plan and source boundaries
    ↓
choose template/components
    ↓
start task (working)
    ↓
html.materialize dry-run → review plan → apply exact plan
    ↓
fill content in materialized v001
    ↓
html.viewport-check → runtime interaction/preview/check → optional html.pdf-export
    ↓
review → feedback → v002/v003
    ↓
complete or pause for later
```

每次写入已有任务前先 `show` 获取最新 `version`，再携带 `--expect-version`。遇到版本冲突时重新读取并保留其他操作者的变更。

## 兼容性要求

- Agent 不得依赖特定厂商的隐藏能力；文件协议、相对路径和标准命令是最小运行基础；
- 标准模板仓库默认提供 `reports/`；任务简报登记稳定输出根 `reports/<task-id>`，每次修订由工具生成 `vNNN` 目录。既有仓库可通过根目录 `.suanhai/expression.json` 声明额外输出根目录，例如 `web/`，任务工具会校验该配置和路径边界；
- 自建仓需要让 `expression.task-record` 管理作品哈希时，可创建 `.suanhai/expression.json`，例如 `{"schema_version":1,"output_roots":["web"]}`；受保护目录 `vendor/`、`.git/`、`context/` 和 `tasks/` 永远不能作为作品输出根；
- 任何页面模板都必须声明入口、版本、离线要求、资源和组件依赖；组件包通过 `--component-package-id` 选择。完整预设的语义片段通过重复的 `--component-id` 选择，单页组合在页面计划中用 `components` 指定目标页面和插槽，工具只把已登记片段插入显式位置；
- 新页面默认配齐工具栏/公式与原图阅读器，`--runtime-kit-id` 只用于增量扩展；主动介绍现有交互，不要求用户逐项选择安装；模板必须声明运行时样式、工具栏和脚本三个插槽。运行时使用 `data-math` 标记，提供自动/窄屏/平板/桌面模式、Fullscreen API 全屏入口和浏览器打印保存 PDF 入口；窄屏控制栏自动换行，按钮保留文字和至少 44px 高度；确定性 PDF 仍调用 `html.pdf-export`。
- 组件包必须通过 `index.yml` 按稳定组件 ID 发现，Agent 不得扫描 CSS 猜测组件语义；
- 组件包可被模板复制到消费端报告目录，也可由已有仓库按相对路径引用，但交付页面必须自包含；
- 不能把 Manifest 未列出的交互式预览器或其他检查器当作已经可调用能力；已列出的 `html.runtime-kit-v1` 只提供页面内运行时，不替代浏览器视觉检查；`html.viewport-check` 与 `html.pdf-export` 仍须按其 `not-run` 语义执行。
- `html.viewport-check` 支持 Playwright 或本机 Chrome/Edge/Chromium 的 CDP 后端；整稿检查用 `--all-pages --interactions --full-page --fail-on-overflow` 并明确 `--artifact-kind template|report`，需要时输出截图和联系表。返回 `not-run` 时必须如实保留，不能宣称通过。
- `html.pdf-export` 只在用户确认纸张、方向和输出路径后调用；浏览器不可用时不伪造 PDF 或完成状态。

## 停止条件

缺少关键用户决定、来源无法定位或授权不清、输出目录冲突、模板/组件不在 Manifest、页面存在外部资源、检查失败、版本摘要不一致，或者用户没有确认下一步时，停在当前阶段并报告可继续的动作。
