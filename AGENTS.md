# Agent 协作约定

本仓库是 Suanhai 团队共享的对外表达基础设施工程仓库。它提供可复用的工作流能力、工具、技能、模板、Harness 和检查协议，不承载具体小组的项目事实或对外表达资产。

根 `AGENTS.md` 是本仓库自身的总 Harness：它约束维护本基础设施仓库的 Agent。`workflows/` 中的新入口和 `harness/` 中保留的既有入口，是提供给消费端仓库使用的工作流 Harness；不要把它们与根规则混为一谈。

## 当前状态

- 仓库提供 Agent 发现协议、任务循环（`expression.task-loop`）、网页 HTML 制作工作流（`expression.html-production`）、网页 HTML 页面模板（`html.project-report-v1`）、网页 HTML 语义组件包（`html.semantic-components-v1`）、HTML 模板与组件安全物料化工具（`html.materialize`）、小组资产仓模板铺设工具（`consumer.group-asset-bootstrap`）、仓库创建与初始化流程（`consumer.group-asset-create-and-initialize`）、仓内初始化流程（`consumer.group-asset-onboarding`）、既有仓库首次接入流程（`consumer.infrastructure-adoption`）及其 Harness 安装工具（`consumer.infrastructure-adoption-harness`），以及 submodule 更新流程（`consumer.submodule-update`）；
- `manifest.yml` 是能力发现的唯一入口；
- `kind: workflow` 表示面向完整目标的复合能力；工作流入口负责约束 Agent，并通过 `uses` 声明依赖的能力；
- 实际能力以当前 `capabilities` 为准；任务循环、状态工具、HTML 网页制作工作流、项目汇报页面模板、语义组件包和 `html.materialize` 物料化工具属于 `implemented / experimental`；浏览器预览、数学公式渲染和自动响应式/无障碍检查仍为 `planned / not implemented`；
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
