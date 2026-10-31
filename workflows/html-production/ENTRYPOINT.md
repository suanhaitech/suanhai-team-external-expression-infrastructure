# `expression.html-production` 工作流入口

本入口是消费端 Agent 执行 HTML 制作任务的协议。它可以被公共模板仓库或既有仓库中的 Agent 读取；它不要求消费端采用固定目录，但要求遵守消费端根 `AGENTS.md` 的工作边界。

## 启动方式

用户可以直接向自己常用的 Agent 发送以下请求：

> 我需要制作一个 HTML 对外表达页面。请先读取当前仓库的 `AGENTS.md`、基础设施 submodule 的 `manifest.yml` 和 `workflows/html-production/WORKFLOW.md`，不要直接写 HTML。先登记任务，读取我提供的材料，向我提问并对齐受众、用途、范围、来源和完成标准；得到确认后再选择已实现模板和组件，按版本生成、预览、检查并等待我评审。

Agent 应把这段请求解释为“启动工作流”，而不是用户已经授权提交、推送或发布。

## 读取顺序

1. 消费端根 `AGENTS.md`；
2. 消费端 `README.md`、`context/`、`tasks/`、`reports/` 或仓库自身规定的作品目录；
3. submodule 的 `manifest.yml`；
4. 本工作流 `WORKFLOW.md`；
5. 被选择的模板、组件和工具入口；组件包按 `package.yml` → `index.yml` → 组件 `component.yml` → `template.html` 的顺序读取；物料化使用 `html.materialize`，先预览并核对计划摘要，再显式应用；
6. 当前任务的 `task.json`、`sources.yml` 和已有版本。

如果 Manifest、gitlink、submodule HEAD 或工作区状态不一致，先停止并报告，不修复或升级依赖。

## 阶段路由

```text
create/continue task
    ↓
clarify brief and sources
    ↓
align with user
    ↓
choose template/components
    ↓
html.materialize dry-run → review plan → apply exact plan
    ↓
start and materialize v001
    ↓
preview/check
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
- 任何页面模板都必须声明入口、版本、离线要求、资源和组件依赖；组件包通过 `--component-package-id` 选择，语义片段通过重复的 `--component-id` 选择，工具只把已登记片段插入显式插槽；
- 组件包必须通过 `index.yml` 按稳定组件 ID 发现，Agent 不得扫描 CSS 猜测组件语义；
- 组件包可被模板复制到消费端报告目录，也可由已有仓库按相对路径引用，但交付页面必须自包含；
- 不能把当前不存在的预览器、公式渲染器或检查器当作已经可调用能力。

## 停止条件

缺少关键用户决定、来源无法定位或授权不清、输出目录冲突、模板/组件不在 Manifest、页面存在外部资源、检查失败、版本摘要不一致，或者用户没有确认下一步时，停在当前阶段并报告可继续的动作。
