# Agent 协作约定

本仓库是 Suanhai 团队共享的对外表达基础设施工程仓库。它提供可复用的工作流能力，以及工作流可消费的模板、工具、运行资源、技能和检查协议；不承载具体小组的项目事实或对外表达资产。

根 `AGENTS.md` 是本仓库自身的总 Harness，约束维护本基础设施仓库的 Agent。消费端可调用的完整工作流及其 Agent 执行入口统一放在 `workflows/`；入口承担该工作流的 Harness 职责。可复用模板、工具、运行资源、领域 Schema、技能和检查协议统一放在 `infrastructure/<领域>/`。一个目录层级只表示领域归属，不暗示必须把工作流再拆成子工作流。

## 当前状态

- 仓库提供 Agent 发现协议、任务循环（`expression.task-loop`）、网页 HTML 制作工作流（`expression.html-production`）、长页 HTML 项目汇报模板（`html.project-report-v1`）、多页 HTML 演示稿模板（`html.presentation-deck-v1`）、网页 HTML 语义组件包（`html.semantic-components-v1`）、HTML 响应式布局包（`html.responsive-layout-v1`）、HTML 页面运行时包（`html.runtime-kit-v1`）、HTML 模板与组件安全物料化工具（`html.materialize`）、小组资产仓模板铺设工具（`consumer.group-asset-bootstrap`）、仓库创建与初始化流程（`consumer.group-asset-create-and-initialize`）、仓内初始化流程（`consumer.group-asset-onboarding`）、既有仓库首次接入流程（`consumer.infrastructure-adoption`）及其 Harness 安装工具（`consumer.infrastructure-adoption-harness`），以及 submodule 更新流程（`consumer.submodule-update`）；
- `manifest.yml` 是能力发现的唯一入口；
- 各独立工作流位于 `workflows/`；HTML 制作工作流位于 `workflows/html/production/`，HTML 容器、单页模板、组合预设、组件、样式、运行时和专用工具位于 `infrastructure/html/`；资产仓建仓与初始化流程位于 `workflows/group-asset-repository-create-and-initialize/`、`workflows/group-asset-repository-onboarding/`，其模板和铺设工具位于 `infrastructure/group-asset-repository/`；
- `kind: workflow` 表示面向完整目标的复合能力；工作流入口负责约束 Agent，并通过 `uses` 声明依赖的能力；
- 实际能力以当前 `capabilities` 为准；任务循环、状态工具、HTML 网页制作工作流、长页项目汇报模板、多页演示稿模板、语义组件包、响应式布局包、`html.runtime-kit-v1`、`html.materialize`、`html.viewport-check` 和 `html.pdf-export` 属于 `implemented / experimental`；演示稿模板提供底部页码/前后页导航、键盘翻页、比例选择、讲者备注和逐页打印；运行时包的公式渲染、显示模式、全屏和浏览器保存 PDF 入口已实现，但真实浏览器视觉检查、确定性 PDF 导出和完整无障碍检查仍受本机运行时条件限制或为 `not-run / planned`；
- 不得因为目录存在，就把计划能力描述为已经可用。

## 开发边界

- Chaos 是当前仓库负责人和唯一开发者；
- 项目专属事实、客户资料、凭据、令牌和未经授权的数据不得进入本仓库；
- 不在这里实现项目任务、数据库、云端接口或部署流程；
- 不自动执行 Git commit、push、部署或正式发布。工作流入口可以指导 Agent 在用户明确确认后执行这些动作，但能力发现不等于授权；
- 工程检查通过不代表专业内容正确，也不代表对外发布已经获得授权。
- 任务循环的用户原话是追溯记录，不是身份认证；测试数据只在隔离目录创建，不进入本仓或消费端真实业务。

## 分支约定

- `main` 是稳定版本，禁止强制推送和删除；
- `develop` 是集成分支；
- 日常修改从 `develop` 创建 `codex/feat-*`、`codex/fix-*` 或 `codex/chore-*` 短期分支；
- 合入 `main` 前必须通过 Manifest CI；当前不要求人工评审；
- 分支规则受 GitHub 仓库设置约束，文档约定不能替代服务端权限控制。

## 修改前检查

1. 确认当前分支和工作区状态；
2. 阅读 `README.md`、`docs/architecture.md` 和相关能力目录说明；
3. 判断改动是否属于共享、可复用的基础设施；
4. 更新 Manifest、Schema、说明和检查时保持一致；
5. 运行 `ruby scripts/validate_manifest.rb`，并检查最终 diff 不含凭据、缓存或构建产物。

新增能力时，先实现并验证真实入口，再把它加入 `manifest.yml`。不能把占位目录提前暴露给 Agent。
